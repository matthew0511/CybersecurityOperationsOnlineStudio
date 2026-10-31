"""Validated, versioned workflows. No client-authored SQL, templates or expressions."""
from datetime import date,datetime,timezone
import hashlib,json,re,uuid
from fastapi import HTTPException
from .catalog import MODULES,APPROVAL_KINDS,STATUSES
from .schema import actor

LEGACY={'risk':'risks','task':'remediation_tasks','vendor':'vendors','assessment':'assessments','evidence':'evidence_records','finding':'governance_findings','initiative':'vciso_initiatives','change':'governance_changes'}

def uid():return str(uuid.uuid4())
def fail(message,status=422):raise HTTPException(status,message)
def bounded(value,limit=5000):
    if not isinstance(value,str) or len(value)>limit or any(ord(c)<32 and c not in '\n\r\t' for c in value):fail(f'Enter text up to {limit} characters')
    return value.strip()
def rowdict(row):return dict(row) if row else None

def access(db,user,org,write=False,capability='records:write'):
    from ..experience import authorize
    role=authorize(db,user,org,write and capability not in {'records:read','reports:export','policy:acknowledge'},'review' if capability=='records:approve' else 'reports:export' if capability=='reports:export' else '')
    actor(db,user['username'],org)
    if user['role']!='owner':
        row=db.execute('SELECT denied FROM pl_capabilities WHERE organization_id=%s AND username=%s',(org,user['username'])).fetchone()
        if row and (capability in row['denied'] or '*' in row['denied']):fail('This capability is restricted for your account',403)
    return role

def get(db,org,ident,kind=None,deleted=False):
    row=db.execute('SELECT * FROM pl_records WHERE organization_id=%s AND id=%s'+('' if deleted else ' AND deleted_at IS NULL'),(org,ident)).fetchone()
    if not row or kind and row['kind']!=kind:fail('Record not found in this organization',404)
    return dict(row)

def reference(db,org,ident,kind):
    if kind.startswith('legacy:'):
        key=kind.split(':',1)[1];table=LEGACY.get(key)
        if not table:fail('Unsupported reference')
        from psycopg import sql
        row=db.execute(sql.SQL('SELECT * FROM {} WHERE organization_id=%s AND id=%s').format(sql.Identifier(table)),(org,ident)).fetchone()
        if not row:fail('Related record not found in this organization',404)
        return dict(row)
    return get(db,org,ident,kind)

def validate(db,org,kind,data):
    if kind not in MODULES or not isinstance(data,dict):fail('Choose a supported module')
    fields=MODULES[kind][1]
    if set(data)-set(fields)-{'calculated','approved_by','approved_at','approval_version'}:fail('Unsupported module field')
    result={}
    for name,field in fields.items():
        value=data.get(name)
        if field['required'] and (value is None or value=='' or value==[]):fail(field['label']+' is required')
        if value is None or value=='':continue
        typ=field['type']
        if typ in {'text','textarea','date','datetime','reference','select'}:
            value=bounded(value,12000 if typ=='textarea' else 500)
        if typ=='number':
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0<=value<=1e9:fail(field['label']+' must be a nonnegative number')
        if typ=='boolean' and not isinstance(value,bool):fail(field['label']+' must be boolean')
        if typ=='date':
            try:date.fromisoformat(value)
            except ValueError:fail('Use a valid date')
        if typ=='datetime':
            try:datetime.fromisoformat(value.replace('Z','+00:00'))
            except ValueError:fail('Use an ISO date and time')
        if typ=='select' and value not in field['options']:fail('Choose a supported '+field['label'])
        if typ=='reference':reference(db,org,value,field['ref'])
        if typ=='references':
            if not isinstance(value,list) or len(value)>100:fail('Choose up to 100 related records')
            if not all(isinstance(v,str) for v in value):fail('Related identifiers must be strings')
            value=list(dict.fromkeys(value))
            for ident in value:reference(db,org,ident,field['ref'])
        if typ in {'steps','rules','weights','scores','mappings'}:
            if not isinstance(value,list) or not 1<=len(value)<=200:fail('Add between one and 200 structured entries')
            allowed={'steps':{'title','owner','instructions','verification'},'rules':{'parent','operator','value','child'},'weights':{'code','weight','criteria'},'scores':{'code','score','rationale'},'mappings':{'catalog_id','code'}}[typ]
            for item in value:
                if not isinstance(item,dict) or set(item)-allowed:fail('Unsupported structured-entry field')
                for k,v in item.items():
                    if k in {'score','weight'}:
                        if isinstance(v,bool) or not isinstance(v,(int,float)) or not 0<=v<=100:fail('Scores and weights must be 0–100')
                    else:bounded(v,3000)
                if typ=='steps' and not item.get('title','').strip():fail('Each step needs a title')
                if typ=='rules' and (not item.get('parent') or not item.get('child') or item.get('operator') not in {'equals','not_equals','contains','not_empty'}):fail('Complete the parent, operator and child for each rule')
                if typ in {'weights','scores'} and not item.get('code'):fail('Each score or weight needs a question code')
                if typ=='mappings' and not db.execute('SELECT 1 FROM pl_controls WHERE organization_id=%s AND catalog_id=%s AND code=%s',(org,item.get('catalog_id'),item.get('code'))).fetchone():fail('Mapped framework control not found')
            if typ in {'weights','scores'} and len({v['code'] for v in value})!=len(value):fail('Question codes cannot be repeated')
            if typ in {'weights','scores'} and any(('weight' if typ=='weights' else 'score') not in v for v in value):fail('Enter an explicit number for every question')
            if typ=='scores' and any(not v.get('rationale','').strip() for v in value):fail('Explain every reviewer-entered score')
            if typ=='weights' and not sum(v.get('weight',0) for v in value):fail('At least one question weight must be positive')
            if typ=='rules':validate_rules(value)
        result[name]=value
    for required in {'policy':['content'],'answer':['response'],'exception':['rationale','compensating_controls'],'risk_approval':['rationale']}.get(kind,[]):
        if not result.get(required):fail(required.replace('_',' ').title()+' is required')
    if result.get('frequency_days') is not None and not 1<=result['frequency_days']<=3650:fail('Testing interval must be 1–3650 days')
    if kind=='questionnaire_logic':
        from ..database import service
        codes={q['code'] for q in service(db).questions(org,result['assessment_id'])}
        if any(r['parent'] not in codes or r['child'] not in codes for r in result.get('rules',[])):fail('Conditional rules must use question codes in this assessment')
    for field in ('approver','from_user','to_user'):
        if result.get(field) and not db.execute("SELECT 1 FROM web_users u WHERE username=%s AND enabled AND (role='owner' OR EXISTS(SELECT 1 FROM xp_memberships m WHERE m.username=u.username AND m.organization_id=%s))",(result[field],org)).fetchone():fail('Select an enabled organization member for '+field)
    if kind in {'delegation','exception','risk_approval'} and (not result.get('expires_on') or result['expires_on']<date.today().isoformat()):fail('Choose an expiration date today or later')
    if kind=='delegation' and (result['from_user']==result['to_user'] or result.get('starts_on','')>result['expires_on']):fail('Choose distinct accounts and a valid delegation interval')
    if kind=='vendor_tier':
        score={'low':1,'moderate':2,'high':3,'critical':4}.get(result.get('criticality'),1)+{'none':0,'internal':1,'confidential':2,'regulated':3}.get(result.get('data_access'),0)+{'low':1,'moderate':2,'high':3,'critical':4}.get(result.get('dependency'),1)
        tier='critical' if score>=9 else 'high' if score>=7 else 'moderate' if score>=4 else 'low'
        suggested={'critical':90,'high':180,'moderate':365,'low':730}[tier]
        if result.get('review_days') and result['review_days']!=suggested and not result.get('override_reason'):fail('Explain the review-frequency override')
        result['calculated']={'tier':tier,'suggested_review_days':suggested,'basis':'Operator-entered criticality, data access and dependency; not an independent risk assessment'}
    if kind=='assessment_score':
        rubric=get(db,org,result['rubric_id'],'rubric');weights={v['code']:v.get('weight',0) for v in rubric['data'].get('rules',[])}
        if any(v['code'] not in weights for v in result.get('scores',[])):fail('Scores must reference the selected rubric')
        weight=sum(weights[v['code']] for v in result.get('scores',[]));score=sum(v.get('score',0)*weights[v['code']] for v in result.get('scores',[]))/weight if weight else None
        result['calculated']={'weighted_score':round(score,2) if score is not None else None,'rubric_version':rubric['version'],'scored_questions':len(result.get('scores',[])),'scored_weight':weight,'total_weight':sum(weights.values()),'coverage_percent':round(100*weight/sum(weights.values()),2) if sum(weights.values()) else 0,'basis':'Explicit reviewer scores; narrative answers are not automatically judged as compliance'}
    if kind=='control_test' and result.get('result')=='pass':
        if not result.get('evidence_ids'):fail('A passing result requires supporting evidence')
        require_verified_evidence(db,org,result['evidence_ids'])
    return result

def validate_rules(rules):
    edges={}
    for rule in rules:
        edges.setdefault(rule['parent'],[]).append(rule['child'])
    def visit(node,path):
        if node in path:fail('Conditional rules cannot contain a cycle')
        for child in edges.get(node,[]):visit(child,path|{node})
    for node in edges:visit(node,set())

def require_verified_evidence(db,org,ids):
    from ..database import service
    evidence={r['id']:r for r in service(db).evidence(org)}
    for ident in ids:
        if ident not in evidence or evidence[ident].get('effective_status')!='verified':fail('Every linked artifact must have a current verified review')

def history(db,org,ident,username,action,snapshot):
    db.execute('INSERT INTO pl_history(organization_id,record_id,actor,action,snapshot) VALUES (%s,%s,%s,%s,%s::jsonb)',(org,ident,username,action,json.dumps(snapshot,default=str)))
    from ..experience import audit
    audit(db,username,'platform:'+action)

def save(db,user,org,kind,body):
    access(db,user,org,True)
    ident=body.get('id') or uid();previous=get(db,org,ident,kind) if body.get('id') else None
    if previous and previous['status'] in {'approved','submitted'} and kind in APPROVAL_KINDS:fail('Reopen the reviewed version before editing',409)
    if previous and body.get('version')!=previous['version']:fail('This record changed. Reload and reconcile your edit.',409)
    title=bounded(body.get('title',''),300)
    if not title:fail('Enter a record title')
    owner=bounded(body.get('owner',''),100)
    due=body.get('due_on') or None
    if due:
        try:date.fromisoformat(due)
        except (ValueError,TypeError):fail('Choose a valid due date')
    data=validate(db,org,kind,body.get('data',{}))
    if kind in {'site','asset'}:
        refs=[data['parent_id']] if kind=='site' and data.get('parent_id') else data.get('dependencies',[]) if kind=='asset' else []
        def walk(node,path):
            if node==ident or node in path:fail('Office / asset dependencies cannot contain a cycle')
            item=get(db,org,node,kind);nexts=[item['data']['parent_id']] if kind=='site' and item['data'].get('parent_id') else item['data'].get('dependencies',[]) if kind=='asset' else []
            for child in nexts:walk(child,path|{node})
        for node in refs:walk(node,set())
    if kind=='delegation' and user['role']!='owner' and data.get('from_user')!=user['username']:fail('You can delegate only your own responsibilities',403)
    status=previous['status'] if previous else 'draft'
    db.execute('''INSERT INTO pl_records(id,organization_id,kind,title,status,owner,due_on,data,created_by,updated_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
     ON CONFLICT(id) DO UPDATE SET title=EXCLUDED.title,owner=EXCLUDED.owner,due_on=EXCLUDED.due_on,data=EXCLUDED.data,updated_by=EXCLUDED.updated_by,updated_at=CURRENT_TIMESTAMP,version=pl_records.version+1''',(ident,org,kind,title,status,owner,due,json.dumps(data),user['username'],user['username']))
    record=get(db,org,ident);history(db,org,ident,user['username'],'save',record)
    return record

def transition(db,user,org,ident,body):
    access(db,user,org,True,'records:approve' if body.get('status') in {'approved','rejected'} else 'records:write')
    record=get(db,org,ident)
    if body.get('version')!=record['version']:fail('Record changed; reload before changing its status',409)
    status=body.get('status');old=record['status']
    if status not in STATUSES:fail('Choose a valid status')
    transitions={'draft':{'in_progress','submitted','active','closed'},'in_progress':{'submitted','completed','closed'},'submitted':{'approved','rejected','draft'},'approved':{'active','closed','draft'},'active':{'completed','closed','draft'},'completed':{'draft','closed'},'rejected':{'draft'},'closed':{'draft'}}
    if status not in transitions.get(old,set()):fail('This status transition is not permitted',409)
    data=record['data']
    if record['kind'] in APPROVAL_KINDS:
        if status in {'approved','rejected'}:
            if old!='submitted' or record['created_by']==user['username']:fail('An independent assigned reviewer must approve this version',403)
            permitted=data.get('approver')==user['username']
            if not permitted:
                permitted=bool(db.execute("SELECT 1 FROM pl_records WHERE organization_id=%s AND kind='delegation' AND status='active' AND deleted_at IS NULL AND data->>'from_user'=%s AND data->>'to_user'=%s AND data->>'scope'=%s AND COALESCE(NULLIF(data->>'starts_on','')::date,CURRENT_DATE)<=CURRENT_DATE AND (data->>'expires_on')::date>=CURRENT_DATE",(org,data.get('approver'),user['username'],record['kind'])).fetchone())
            if not permitted:fail('Only the assigned reviewer or active delegate may decide',403)
            from .security import reauthenticate
            reauthenticate(db,user,body)
            if status=='approved' and record['kind']=='answer':require_verified_evidence(db,org,data.get('evidence_ids',[]))
            if status=='approved' and data.get('expires_on') and data['expires_on']<date.today().isoformat():fail('The approval expiration has passed')
            data={**data,'approved_by':user['username'],'approved_at':datetime.now(timezone.utc).isoformat(),'approval_version':record['version']+1}
            if record['kind']=='risk_approval':
                from ..database import service
                svc=service(db);svc.vault.reauthenticated=True
                svc.record_risk_decision(org,data['risk_id'],data.get('decision','approved') if status=='approved' else 'rejected',user['username'],data.get('rationale',''),data.get('expires_on',''),attested=True,operator_passphrase='authenticated-step-up')
        elif status in {'active','completed','closed'} and old not in {'approved','active'}:fail('Submit and approve this version before activation')
        if status=='draft':data={k:v for k,v in data.items() if k not in {'approved_by','approved_at','approval_version'}}
    db.execute('UPDATE pl_records SET status=%s,data=%s::jsonb,version=version+1,updated_by=%s,updated_at=CURRENT_TIMESTAMP WHERE organization_id=%s AND id=%s',(status,json.dumps(data),user['username'],org,ident))
    updated=get(db,org,ident);history(db,org,ident,user['username'],'status:'+status,updated);return updated
