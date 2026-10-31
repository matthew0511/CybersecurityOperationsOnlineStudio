"""Workflow operations shared by the program center, legacy questionnaire and APIs."""
import csv,io,json,hashlib
from datetime import date,datetime,timezone
from .store import get,reference,fail,uid,history,access,LEGACY,bounded
from ..database import service


def apply_rules(db,org,assessment,questions):
    row=db.execute("SELECT data FROM pl_records WHERE organization_id=%s AND kind='questionnaire_logic' AND status='active' AND deleted_at IS NULL AND data->>'assessment_id'=%s ORDER BY updated_at DESC LIMIT 1",(org,assessment)).fetchone()
    if not row:return questions
    by_code={q['code']:q for q in questions};rules=row['data'].get('rules',[]);groups={}
    for rule in rules:groups.setdefault(rule['child'],[]).append(rule)
    cache={}
    def visible(code,path):
        if code in cache:return cache[code]
        if code in path:return False
        if code not in groups:return by_code.get(code,{}).get('visible',False)
        answers=[]
        for rule in groups[code]:
            parent=by_code.get(rule['parent']);left=str((parent or {}).get('rationale','')).strip().casefold();right=rule.get('value','').strip().casefold()
            match={'equals':left==right,'not_equals':left!=right,'contains':right in left,'not_empty':bool(left)}[rule['operator']]
            answers.append(bool(parent) and visible(rule['parent'],path|{code}) and match)
        cache[code]=all(answers);return cache[code]
    for code in groups:
        if code in by_code:by_code[code]['visible']=visible(code,set())
    return questions



def compare(db,org,left,right):
    svc=service(db);a={q['code']:q for q in svc.questions(org,left)};b={q['code']:q for q in svc.questions(org,right)}
    return [dict(code=code,state='added' if code not in a else 'removed' if code not in b else 'changed' if any(a[code].get(k)!=b[code].get(k) for k in ['prompt','answer','rationale']) else 'unchanged',before=a.get(code),after=b.get(code)) for code in sorted(set(a)|set(b))]


def reuse(db,user,org,source_id,assessment,code):
    access(db,user,org,True);source=get(db,org,source_id,'answer')
    if source['status'] not in {'approved','active'} or source['data'].get('expires_on','9999')<date.today().isoformat():fail('Use a current approved answer library version',409)
    from .store import require_verified_evidence
    require_verified_evidence(db,org,source['data'].get('evidence_ids',[]))
    svc=service(db);svc.save_questionnaire_response(org,assessment,code,source['data'].get('response',''))
    db.execute('INSERT INTO pl_answer_uses(organization_id,source_id,source_version,assessment_id,code,actor) VALUES (%s,%s,%s,%s,%s,%s)',(org,source_id,source['version'],assessment,code,user['username']))
    history(db,org,source_id,user['username'],'answer:reused',{'assessment':assessment,'code':code,'version':source['version']});return {'saved':True}


def execute(db,user,org,ident):
    access(db,user,org,True);record=get(db,org,ident)
    if record['kind'] not in {'runbook','exercise'}:fail('Choose a runbook or tabletop exercise')
    if not record['data'].get('steps'):fail('Add execution steps before starting')
    steps=[dict(**s,status='pending',notes='',completed_by='',completed_at='') for s in record['data']['steps']]
    run_id=uid();db.execute('INSERT INTO pl_executions(id,organization_id,record_id,record_version,kind,title,steps,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s)',(run_id,org,ident,record['version'],record['kind'],record['title'],json.dumps(steps),user['username']))
    history(db,org,ident,user['username'],'execution:start',{'execution_id':run_id,'version':record['version']});return {'id':run_id}


def step(db,user,org,run_id,body):
    access(db,user,org,True)
    row=db.execute('SELECT * FROM pl_executions WHERE organization_id=%s AND id=%s FOR UPDATE',(org,run_id)).fetchone()
    if not row:fail('Execution not found',404)
    if body.get('version')!=row['version']:fail('Execution changed; reload before updating',409)
    index=body.get('index');status=body.get('status');steps=row['steps']
    if not isinstance(index,int) or isinstance(index,bool) or not 0<=index<len(steps) or status not in {'pending','in_progress','blocked','completed'}:fail('Choose a valid step and status')
    if status=='completed' and any(v['status']!='completed' for v in steps[:index]):fail('Complete prior steps first',409)
    if status!='completed' and any(v['status']=='completed' for v in steps[index+1:]):fail('Reopen later steps before an earlier step',409)
    steps[index].update(status=status,notes=bounded(body.get('notes','')),completed_by=user['username'] if status=='completed' else '',completed_at=datetime.now(timezone.utc).isoformat() if status=='completed' else '')
    db.execute('UPDATE pl_executions SET steps=%s::jsonb,version=version+1,status=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s',(json.dumps(steps),'completed' if all(v['status']=='completed' for v in steps) else 'running',run_id))
    history(db,org,row['record_id'],user['username'],'execution:step',{'execution_id':run_id,'index':index,'status':status,'notes':steps[index]['notes']});return {'saved':True}


def trash(db,user,org,kind,ident,restore=False):
    access(db,user,org,True,'records:delete')
    if kind=='program':
        record=get(db,org,ident,deleted=True)
        if not restore and record['kind'] in {'policy','answer','risk_approval','exception'} and record['status'] in {'approved','active'}:fail('Close the approved record before archiving it',409)
        db.execute('UPDATE pl_records SET deleted_at='+('NULL' if restore else 'CURRENT_TIMESTAMP')+',version=version+1,updated_by=%s WHERE organization_id=%s AND id=%s',(user['username'],org,ident))
    else:
        if kind not in LEGACY:fail('Unsupported archive type')
        if restore:
            if not db.execute('SELECT 1 FROM pl_trash WHERE organization_id=%s AND kind=%s AND record_id=%s',(org,kind,ident)).fetchone():fail('Archived record not found',404)
        else:reference(db,org,ident,'legacy:'+kind)
        if kind=='evidence':
            hold=db.execute("SELECT 1 FROM pl_records WHERE organization_id=%s AND kind='evidence_policy' AND deleted_at IS NULL AND data->>'evidence_id'=%s AND ((data->>'legal_hold')::boolean IS TRUE OR NULLIF(data->>'retain_until','')::date>=CURRENT_DATE)",(org,ident)).fetchone()
            if hold:fail('A retention obligation or hold prevents evidence archival',409)
    if restore:db.execute('DELETE FROM pl_trash WHERE organization_id=%s AND kind=%s AND record_id=%s',(org,kind,ident))
    else:db.execute('INSERT INTO pl_trash(organization_id,kind,record_id,deleted_by) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',(org,kind,ident,user['username']))
    history(db,org,ident,user['username'],'restore' if restore else 'archive',{'kind':kind});return {'saved':True}


def catalog_import(db,user,org,raw,name,edition,source,license_note,confirmed):
    from ..experience import require_owner
    access(db,user,org,True);require_owner(user)
    if not confirmed:fail('Confirm that you are authorized to import this control content')
    if len(raw)>2*1024*1024:fail('Catalog exceeds 2 MiB',413)
    try:rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    except (UnicodeError,csv.Error):fail('Use a UTF-8 control catalog CSV')
    if not 1<=len(rows)<=5000 or not {'code','title'}<=set(rows[0]):fail('Use 1–5000 rows with code,title and optional parent_code columns')
    codes=[bounded(r['code'],100) for r in rows]
    if len(set(codes))!=len(codes) or any(not c for c in codes):fail('Control codes must be nonempty and unique')
    for r in rows:
        if r.get('parent_code') and r['parent_code'] not in codes:fail('Parent control code must exist in the imported version')
    ident=uid();db.execute('INSERT INTO pl_catalogs(id,organization_id,name,edition,source,license_note,sha256,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(ident,org,bounded(name,200),bounded(edition,100),bounded(source,1000),bounded(license_note,2000),hashlib.sha256(raw).hexdigest(),user['username']))
    with db.cursor() as cursor:cursor.executemany('INSERT INTO pl_controls VALUES (%s,%s,%s,%s,%s)',[(org,ident,bounded(r['code'],100),bounded(r['title'],3000),bounded(r.get('parent_code',''),100)) for r in rows])
    history(db,org,ident,user['username'],'catalog:imported',{'name':name,'edition':edition,'controls':len(rows),'source':source,'license_note':license_note});return {'id':ident,'controls':len(rows)}


def bulk(db,user,org,body):
    access(db,user,org,True,'tasks:write');ids=body.get('ids',[])
    if not isinstance(ids,list) or not 1<=len(ids)<=100 or len(set(ids))!=len(ids):fail('Choose 1–100 unique remediation tasks')
    records=[reference(db,org,ident,'legacy:task') for ident in ids];changes=body.get('changes',{})
    if not changes or set(changes)-{'owner','due_date','status'}:fail('Choose supported bulk fields')
    if changes.get('status') and changes['status'] not in {'open','in_progress','blocked','done'}:fail('Invalid task status')
    if changes.get('due_date'):
        try:date.fromisoformat(changes['due_date'])
        except ValueError:fail('Use a valid due date')
    digest=hashlib.sha256(json.dumps({'records':records,'changes':changes},sort_keys=True,default=str).encode()).hexdigest()
    if not body.get('confirmed'):return {'preview':records,'changes':changes,'confirmation_hash':digest}
    if body.get('confirmation_hash')!=digest:fail('Records changed since preview; review again',409)
    svc=service(db)
    for record in records:
        if changes.get('status')=='done' and db.execute("SELECT 1 FROM xp_dependencies d JOIN remediation_tasks t ON t.id=d.depends_on WHERE d.organization_id=%s AND d.task_id=%s AND t.status<>'done'",(org,record['id'])).fetchone():fail('Complete prerequisites before a dependent task',409)
        if 'status' in changes:svc.update_task_status(org,record['id'],changes['status'])
        if 'owner' in changes:db.execute('UPDATE remediation_tasks SET owner=%s WHERE organization_id=%s AND id=%s',(bounded(changes['owner'],200),org,record['id']))
        if 'due_date' in changes:db.execute('UPDATE remediation_tasks SET due_date=%s WHERE organization_id=%s AND id=%s',(changes['due_date'],org,record['id']))
        history(db,org,record['id'],user['username'],'task:bulk_updated',{'changes':changes,'confirmation_hash':digest})
    return {'updated':len(records)}
