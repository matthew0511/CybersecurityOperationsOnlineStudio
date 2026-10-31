"""One-use, expiring external audit rooms; never a normal workspace session."""
import secrets,time,json,hmac
from fastapi import APIRouter,Request
from fastapi.responses import JSONResponse,Response
from .store import fail,uid,bounded,reference,get,history
from .security import HASH
from .schema import system_actor
from .router import session,owner,table_rows
from ..database import connect,service

router=APIRouter();COOKIE='__Host-studio-auditor'

@router.get('/api/platform/{org}/rooms')
def rooms(org:str,request:Request):
    with connect() as db:
        user=session(db,request,org);owner(user)
        return table_rows(db,'SELECT id,title,allowed,expires_at,revoked,redeemed,created_by FROM pl_rooms WHERE organization_id=%s ORDER BY expires_at DESC',(org,))

@router.post('/api/platform/{org}/rooms')
def create(org:str,body:dict,request:Request):
    with connect() as db,db.transaction():
        user=session(db,request,org,True);owner(user)
        if body.get('revoke'):
            db.execute('UPDATE pl_rooms SET revoked=TRUE WHERE organization_id=%s AND id=%s',(org,str(body['revoke'])));return {'revoked':True}
        allowed=body.get('allowed',[]);days=body.get('days',7)
        if not isinstance(allowed,list) or not 1<=len(allowed)<=100 or isinstance(days,bool) or not isinstance(days,int) or not 1<=days<=30:fail('Choose 1–100 records and a 1–30 day lifetime')
        normalized=[]
        for entry in allowed:
            kind=entry.get('kind');ident=entry.get('id')
            if kind=='program':get(db,org,ident)
            elif kind=='edition':
                if not db.execute('SELECT 1 FROM pl_editions WHERE organization_id=%s AND id=%s',(org,ident)).fetchone():fail('Report edition not found',404)
            elif kind in {'vendor','risk','task','evidence','finding','assessment','initiative','change'}:reference(db,org,ident,'legacy:'+kind)
            else:fail('Unsupported audit-room record')
            normalized.append({'kind':kind,'id':ident})
        token=secrets.token_urlsafe(48);ident=uid();db.execute('INSERT INTO pl_rooms VALUES (%s,%s,%s,%s::jsonb,%s,%s,FALSE,FALSE,%s)',(ident,org,bounded(body.get('title','Audit review'),200),json.dumps(normalized),HASH(token),int(time.time())+days*86400,user['username']))
        history(db,org,ident,user['username'],'audit_room:created',{'allowed_records':len(normalized),'days':days})
        return {'id':ident,'token':token,'path':'/audit-room#token='+token,'message':'Share only with the intended auditor. This one-use link grants access to exactly the selected records, not the organization.'}


def auditor(db,request,write=False):
    token=request.cookies.get(COOKIE,'')
    row=db.execute('SELECT s.*,r.organization_id,r.title,r.allowed,r.revoked,r.expires_at AS room_expires FROM pl_auditor_sessions s JOIN pl_rooms r ON r.id=s.room_id WHERE s.token_hash=%s AND s.expires_at>%s',(HASH(token),int(time.time()))).fetchone()
    if not row or row['revoked'] or row['room_expires']<=int(time.time()):fail('Audit access expired or was revoked',401)
    if write and not hmac.compare_digest(request.headers.get('x-csrf-token',''),row['csrf']):fail('Refresh the audit-room session',403)
    system_actor(db,row['organization_id']);return row

@router.post('/api/audit-room/redeem')
def redeem(body:dict):
    from ..app import limit
    token=str(body.get('token',''))
    if len(token)>200:fail('Invalid audit-room link',403)
    with connect() as db:
        with db.transaction():limit(db,'audit-room:'+HASH(token))
        with db.transaction():
            room=db.execute('UPDATE pl_rooms SET redeemed=TRUE WHERE token_hash=%s AND NOT redeemed AND NOT revoked AND expires_at>%s RETURNING *',(HASH(token),int(time.time()))).fetchone()
            if not room:fail('Audit-room link expired or was already redeemed',403)
            value=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(32);expires=min(room['expires_at'],int(time.time())+28800)
            db.execute('INSERT INTO pl_auditor_sessions VALUES (%s,%s,%s,%s)',(HASH(value),room['id'],csrf,expires));response=JSONResponse({'csrf':csrf})
            response.set_cookie(COOKIE,value,secure=True,httponly=True,samesite='strict',max_age=expires-int(time.time()),path='/');return response

@router.get('/api/audit-room')
def data(request:Request):
    with connect() as db:
        room=auditor(db,request);org=room['organization_id'];records=[]
        for allowed in room['allowed']:
            if allowed['kind']=='program':
                record=get(db,org,allowed['id']);record={k:record[k] for k in ['id','kind','title','status','owner','due_on','version','data']}
            elif allowed['kind']=='edition':
                record=dict(db.execute('SELECT id,title,format,sha256,created_at FROM pl_editions WHERE organization_id=%s AND id=%s',(org,allowed['id'])).fetchone() or {})
            elif allowed['kind']=='evidence':
                full=reference(db,org,allowed['id'],'legacy:evidence');record={k:full.get(k) for k in ['id','title','sha256','review_status','expires_on']}
            else:
                full=reference(db,org,allowed['id'],'legacy:'+allowed['kind']);record={k:v for k,v in full.items() if k in {'id','title','name','status','owner','due_date','severity','score','review_state','scope'}}
            records.append({'kind':allowed['kind'],'record':record})
        return {'title':room['title'],'expires_at':room['room_expires'],'csrf':room['csrf'],'records':records,'questions':table_rows(db,'SELECT body,actor,recorded_at FROM pl_room_questions WHERE room_id=%s AND organization_id=%s ORDER BY recorded_at',(room['room_id'],org)),'identity_note':'Access proves possession of this scoped invitation; it is not an independently authenticated auditor identity.'}

@router.post('/api/audit-room/questions')
def question(body:dict,request:Request):
    with connect() as db,db.transaction():
        room=auditor(db,request,True);text=bounded(body.get('body',''),3000)
        if not text:fail('Enter an audit question')
        db.execute('INSERT INTO pl_room_questions VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)',(uid(),room['organization_id'],room['room_id'],text,'External invited auditor'));return {'saved':True}

@router.get('/api/audit-room/download/{kind}/{ident}')
def download(kind:str,ident:str,request:Request):
    with connect() as db:
        room=auditor(db,request)
        if {'kind':kind,'id':ident} not in room['allowed']:fail('Artifact is not included in this audit room',403)
        if kind=='evidence':content=service(db).evidence_bytes(room['organization_id'],ident);mime='application/octet-stream';filename='evidence.bin'
        elif kind=='edition':
            row=db.execute('SELECT content,format FROM pl_editions WHERE organization_id=%s AND id=%s',(room['organization_id'],ident)).fetchone()
            if not row:fail('Report edition not found',404)
            from .reporting import MIMES
            content=bytes(row['content']);mime=MIMES[row['format']];filename='report.'+row['format']
        else:fail('Only selected evidence and frozen reports can be downloaded')
        return Response(content,media_type=mime,headers={'Content-Disposition':'attachment; filename="'+filename+'"'})
