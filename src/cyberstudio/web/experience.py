"""Organization-scoped collaboration, questionnaire workflow and experience services."""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import io
import json
import re
import secrets
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from .database import connect, service

router = APIRouter()
VCOOKIE = '__Host-studio-vendor'
SCHEMA = """
ALTER TABLE web_users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'member';
ALTER TABLE web_users ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE;
UPDATE web_users SET role='owner' WHERE username=(SELECT username FROM web_users ORDER BY created_at,username LIMIT 1) AND NOT EXISTS(SELECT 1 FROM web_users WHERE role='owner');
CREATE TABLE IF NOT EXISTS xp_memberships(username TEXT NOT NULL REFERENCES web_users(username), organization_id TEXT NOT NULL REFERENCES organizations(id), role TEXT NOT NULL CHECK(role IN ('editor','reviewer','viewer')), PRIMARY KEY(username,organization_id));
CREATE TABLE IF NOT EXISTS xp_settings(organization_id TEXT PRIMARY KEY REFERENCES organizations(id), settings JSONB NOT NULL DEFAULT '{}', logo BYTEA, logo_mime TEXT);
CREATE TABLE IF NOT EXISTS xp_preferences(username TEXT NOT NULL REFERENCES web_users(username), organization_id TEXT NOT NULL REFERENCES organizations(id), settings JSONB NOT NULL DEFAULT '{}', PRIMARY KEY(username,organization_id));
CREATE TABLE IF NOT EXISTS xp_assessments(assessment_id TEXT PRIMARY KEY REFERENCES assessments(id), organization_id TEXT NOT NULL REFERENCES organizations(id), vendor_id TEXT, reviewer TEXT NOT NULL DEFAULT '', due_date TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','submitted','needs_changes','approved')), notes TEXT NOT NULL DEFAULT '', reviewed_by TEXT NOT NULL DEFAULT '', updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS xp_question_evidence(organization_id TEXT NOT NULL REFERENCES organizations(id), assessment_id TEXT NOT NULL REFERENCES assessments(id), code TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence_records(id), PRIMARY KEY(assessment_id,code,evidence_id));
CREATE TABLE IF NOT EXISTS xp_response_versions(assessment_id TEXT NOT NULL REFERENCES assessments(id),code TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(assessment_id,code));
CREATE TABLE IF NOT EXISTS xp_links(id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id), source_type TEXT NOT NULL, source_id TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT NOT NULL, UNIQUE(organization_id,source_type,source_id,target_type,target_id));
CREATE TABLE IF NOT EXISTS xp_comments(id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id), object_type TEXT NOT NULL, object_id TEXT NOT NULL, author TEXT NOT NULL REFERENCES web_users(username), body TEXT NOT NULL, recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS xp_dependencies(organization_id TEXT NOT NULL REFERENCES organizations(id), task_id TEXT NOT NULL REFERENCES remediation_tasks(id), depends_on TEXT NOT NULL REFERENCES remediation_tasks(id), PRIMARY KEY(task_id,depends_on),CHECK(task_id<>depends_on));
CREATE TABLE IF NOT EXISTS xp_snapshots(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),day DATE NOT NULL, metrics JSONB NOT NULL, captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(organization_id,day));
CREATE TABLE IF NOT EXISTS xp_notifications(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),username TEXT NOT NULL REFERENCES web_users(username),title TEXT NOT NULL,object_type TEXT NOT NULL,object_id TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,read_at TIMESTAMPTZ,dedupe TEXT NOT NULL,UNIQUE(username,organization_id,dedupe));
CREATE TABLE IF NOT EXISTS xp_invites(token_hash TEXT PRIMARY KEY,kind TEXT NOT NULL CHECK(kind IN ('team','vendor')),organization_id TEXT NOT NULL REFERENCES organizations(id),assessment_id TEXT,username TEXT NOT NULL DEFAULT '',role TEXT NOT NULL DEFAULT 'viewer',expires_at BIGINT NOT NULL,revoked BOOLEAN NOT NULL DEFAULT FALSE,redeemed BOOLEAN NOT NULL DEFAULT FALSE,created_by TEXT NOT NULL REFERENCES web_users(username),created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS xp_vendor_sessions(token_hash TEXT PRIMARY KEY,invite_hash TEXT NOT NULL REFERENCES xp_invites(token_hash),csrf TEXT NOT NULL,expires_at BIGINT NOT NULL);
CREATE INDEX IF NOT EXISTS xp_notice_user ON xp_notifications(username,organization_id,created_at);
CREATE INDEX IF NOT EXISTS xp_comments_object ON xp_comments(organization_id,object_type,object_id);
CREATE OR REPLACE TRIGGER xp_comments_immutable BEFORE UPDATE OR DELETE ON xp_comments FOR EACH ROW EXECUTE FUNCTION reject_history_change();
CREATE OR REPLACE TRIGGER xp_snapshots_immutable BEFORE UPDATE OR DELETE ON xp_snapshots FOR EACH ROW EXECUTE FUNCTION reject_history_change();
INSERT INTO web_schema VALUES ('experience',1) ON CONFLICT(name) DO NOTHING;
"""
TABLES={'vendor':'vendors','assessment':'assessments','risk':'risks','task':'remediation_tasks','evidence':'evidence_records','finding':'governance_findings','initiative':'vciso_initiatives','change':'governance_changes'}
SECTIONS=[('Company profile',1,7),('HIPAA',8,15),('Sensitive data and testing',16,28),('Security program',29,35),('Subcontractors',36,40),('Physical security',41,43),('Incident response',44,48),('Training',49,52),('Compliance and insurance',53,59),('Follow-up',60,60)]
CONDITIONS={10:9,12:11,17:16,18:16,20:19,23:22,24:22,28:27,37:36,38:36,39:36,40:36,46:45,54:53,56:55}
REVIEW_WRITES={'save_questionnaire_response','answer_question','review_evidence','link_evidence','record_vendor_review','evaluate_control','add_finding','update_finding'}


def epoch():
    return int(datetime.now(timezone.utc).timestamp())


def hash_token(token):
    return sha256(token.encode()).hexdigest()


def audit(db, username, action):
    db.execute('INSERT INTO web_request_audit(username,operation) VALUES (%s,%s)',(username,'experience:'+action))


def session(db, request, write=False):
    from .app import principal
    return principal(db,request,write=write)


def require_owner(user):
    if user['role']!='owner':
        raise HTTPException(403,'Workspace owner permission required')


def authorize(db,user,org,write=False,operation=''):
    service(db)._org(org)
    if user['role']=='owner':return 'owner'
    member=db.execute('SELECT role FROM xp_memberships WHERE username=%s AND organization_id=%s',(user['username'],org)).fetchone()
    if not member:raise HTTPException(403,'You do not have access to this organization')
    role=member['role']
    if write and (role=='viewer' or (role=='reviewer' and operation not in REVIEW_WRITES|{'response','comment','review','question_evidence'})):
        raise HTTPException(403,'Your organization role cannot perform this action')
    return role


def record(db,org,kind,ident):
    table=TABLES.get(kind)
    if not table:raise HTTPException(422,'Unsupported record type')
    row=db.execute(f'SELECT * FROM {table} WHERE organization_id=%s AND id=%s',(org,ident)).fetchone()
    if not row:raise HTTPException(404,'Record not found in this organization')
    return dict(row)


def text(value,maximum=5000):
    if not isinstance(value,str) or len(value)>maximum:raise HTTPException(422,f'Enter text up to {maximum} characters')
    return value.strip()


def valid_date(value,empty=True):
    value=text(value,10)
    if not value and empty:return ''
    try:date.fromisoformat(value)
    except ValueError:raise HTTPException(422,'Use a valid date in YYYY-MM-DD format') from None
    return value


def settings(db,org):
    row=db.execute('SELECT settings FROM xp_settings WHERE organization_id=%s',(org,)).fetchone()
    return row['settings'] if row else {}


def meta(db,org,aid):
    record(db,org,'assessment',aid)
    db.execute('INSERT INTO xp_assessments(assessment_id,organization_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',(aid,org))
    return dict(db.execute('SELECT * FROM xp_assessments WHERE assessment_id=%s AND organization_id=%s',(aid,org)).fetchone())


def question_state(db,org,aid):
    qs=service(db).questions(org,aid)
    answers={q['code']:q['rationale'] for q in qs}
    versions={r['code']:r['version'] for r in db.execute('SELECT code,version FROM xp_response_versions WHERE assessment_id=%s',(aid,)).fetchall()}
    links=db.execute('SELECT l.code,e.id,e.title,e.review_status FROM xp_question_evidence l JOIN evidence_records e ON e.id=l.evidence_id AND e.organization_id=l.organization_id WHERE l.organization_id=%s AND l.assessment_id=%s',(org,aid)).fetchall()
    for q in qs:
        number=int(q['code'].split('-')[1]) if re.fullmatch(r'TPR-\d{3}',q['code']) else 0
        parent=CONDITIONS.get(number)
        q['visible']=not parent or answers.get(f'TPR-{parent:03}','').strip().lower().rstrip('.') not in {'no','not applicable','n/a'}
        q['section']=next((name for name,start,end in SECTIONS if start<=number<=end),'Questions')
        q['evidence']=[dict(r) for r in links if r['code']==q['code']]
        q['version']=versions.get(q['code'],0)
    return qs


def review_summary(db,org,aid):
    qs=question_state(db,org,aid)
    visible=[q for q in qs if q['visible']]
    return {'total':len(qs),'applicable':len(visible),'answered':sum(bool(q['rationale'].strip()) for q in visible),
            'unanswered':[q['code'] for q in visible if not q['rationale'].strip()],
            'without_evidence':[q['code'] for q in visible if not q['evidence']],
            'evidence_needing_review':[q['code'] for q in visible if any(e['review_status']!='verified' for e in q['evidence'])],
            'meta':meta(db,org,aid)}


def save_response(db,org,aid,body,actor,vendor=False):
    code=text(body.get('code',''),60);response=text(body.get('response',''))
    state=meta(db,org,aid)
    if state['state'] in {'submitted','approved'}:raise HTTPException(409,'Reopen this questionnaire before changing answers')
    version=body.get('version')
    if not isinstance(version,int) or isinstance(version,bool) or version<0:raise HTTPException(422,'A response version is required')
    db.execute('INSERT INTO xp_response_versions(assessment_id,code) VALUES (%s,%s) ON CONFLICT DO NOTHING',(aid,code))
    row=db.execute('SELECT version FROM xp_response_versions WHERE assessment_id=%s AND code=%s FOR UPDATE',(aid,code)).fetchone()
    if row['version']!=version:raise HTTPException(409,'This answer changed in another session. Reload before editing.')
    service(db).save_questionnaire_response(org,aid,code,response)
    db.execute('UPDATE xp_response_versions SET version=version+1 WHERE assessment_id=%s AND code=%s',(aid,code))
    # Vendor respondents are identified by invitation, never as internal reviewers.
    if not vendor:audit(db,actor,'response:'+aid+':'+code)
    return {'version':version+1,'saved':True}


def action_items(db,org):
    svc=service(db);today=date.today();items=[]
    def add(kind,ident,title,due,owner='',state=''):
        days=(date.fromisoformat(due)-today).days if due else None
        items.append({'type':kind,'id':ident,'title':title,'due':due,'owner':owner,'days':days,'status':state})
    for t in svc.list_tasks(org):
        if t['status']!='done':add('task',t['id'],t['title'],t['due_date'],t['owner'],t['status'])
    for v in svc.vendors(org):
        if v['status']=='active' and (not v['next_review'] or v['review_state']!='reviewed' or (date.fromisoformat(v['next_review'])-today).days<=30):add('vendor',v['id'],v['name'],v['next_review'],v['owner'],v['review_state'])
    for e in svc.evidence(org):
        if e.get('effective_status') in {'expired','pending'} or (e.get('expires_on') and (date.fromisoformat(e['expires_on'])-today).days<=30):add('evidence',e['id'],e['title'],e.get('expires_on',''),'',e.get('effective_status','pending'))
    for a in db.execute("SELECT x.*,a.title FROM xp_assessments x JOIN assessments a ON a.id=x.assessment_id WHERE x.organization_id=%s AND x.state<>'approved'",(org,)).fetchall():add('assessment',a['assessment_id'],a['title'],a['due_date'],a['reviewer'],a['state'])
    for f in svc.findings(org):
        if f['status'] not in {'closed','accepted'}:add('finding',f['id'],f['title'],f['due_date'],f['owner'],f['status'])
    for c in svc.changes(org):
        if c['status'] in {'submitted','review'}:add('change',c['id'],c['title'],'',c['owner'],c['status'])
    return sorted(items,key=lambda i:(i['due'] or '9999',i['title']))


def capture(db,org):
    svc=service(db);risks=[r for r in svc.list_risks(org) if r['status']!='closed'];tasks=svc.list_tasks(org);impl=svc.implementations(org)
    metrics={'open_risks':len(risks),'exposure_total':sum(r['score'] for r in risks),'high_critical':sum(r['score']>=10 for r in risks),'open_tasks':sum(t['status']!='done' for t in tasks),'done_tasks':sum(t['status']=='done' for t in tasks),'verified_controls':sum(i['status']=='verified' for i in impl),'applicable_controls':sum(i['status']!='not_applicable' for i in impl)}
    db.execute('INSERT INTO xp_snapshots(id,organization_id,day,metrics) VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(organization_id,day) DO NOTHING',(str(uuid4()),org,date.today(),json.dumps(metrics)))


def notify(db,org,username,title,kind,ident,dedupe):
    db.execute('INSERT INTO xp_notifications(id,organization_id,username,title,object_type,object_id,dedupe) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(str(uuid4()),org,username,title,kind,ident,dedupe))


def tick(db):
    if not db.execute('SELECT pg_try_advisory_xact_lock(747103095) AS locked').fetchone()['locked']:return
    owners=[r['username'] for r in db.execute("SELECT username FROM web_users WHERE role='owner' AND enabled").fetchall()]
    for orgrow in service(db).list_organizations():
        org=orgrow['id'];capture(db,org);cfg=settings(db,org)
        if cfg.get('reminders_enabled',True) is False:continue
        frequency=cfg.get('reminder_frequency','daily');bucket=date.today().isoformat() if frequency=='daily' else date.today().strftime('%G-W%V')
        lead=int(cfg.get('reminder_lead_days',7));escalate=int(cfg.get('escalation_days',7))
        members={r['username'] for r in db.execute('SELECT m.username FROM xp_memberships m JOIN web_users u ON u.username=m.username WHERE organization_id=%s AND u.enabled',(org,)).fetchall()}|set(owners)
        for item in action_items(db,org):
            if item['days'] is not None and item['days']>lead:continue
            recipients={item['owner']} if item['owner'] in members else set(owners)
            if item['days'] is not None and item['days']<=-escalate:recipients|=set(owners)
            for username in recipients:notify(db,org,username,('Overdue: ' if item['days'] is not None and item['days']<0 else 'Follow up: ')+item['title'],item['type'],item['id'],bucket+':'+item['type']+':'+item['id'])


@router.get('/api/experience/{org}')
def workspace(org:str,request:Request):
    with connect() as db,db.transaction():
        user=session(db,request);role=authorize(db,user,org)
        cfg=settings(db,org);cfg['has_logo']=bool(db.execute('SELECT 1 FROM xp_settings WHERE organization_id=%s AND logo IS NOT NULL',(org,)).fetchone())
        pref=db.execute('SELECT settings FROM xp_preferences WHERE username=%s AND organization_id=%s',(user['username'],org)).fetchone()
        members=db.execute("SELECT u.username,u.role AS installation_role,m.role FROM web_users u LEFT JOIN xp_memberships m ON m.username=u.username AND m.organization_id=%s WHERE u.enabled AND (u.role='owner' OR m.username IS NOT NULL) ORDER BY u.username",(org,)).fetchall()
        return {'role':role,'settings':cfg,'preferences':pref['settings'] if pref else {},'members':[dict(m) for m in members],
                'assessments':[dict(r) for r in db.execute('SELECT * FROM xp_assessments WHERE organization_id=%s',(org,)).fetchall()],
                'notifications':[dict(r) for r in db.execute('SELECT * FROM xp_notifications WHERE organization_id=%s AND username=%s ORDER BY created_at DESC LIMIT 100',(org,user['username'])).fetchall()],
                'actions':action_items(db,org),'snapshots':[dict(r) for r in db.execute('SELECT * FROM xp_snapshots WHERE organization_id=%s ORDER BY day DESC LIMIT 366',(org,)).fetchall()]}


@router.get('/api/experience/{org}/questionnaire/{aid}')
def questionnaire(org:str,aid:str,request:Request):
    with connect() as db,db.transaction():
        user=session(db,request);authorize(db,user,org)
        return {'questions':question_state(db,org,aid),'summary':review_summary(db,org,aid)}


@router.get('/api/experience/{org}/record/{kind}/{ident}')
def related(org:str,kind:str,ident:str,request:Request):
    with connect() as db:
        user=session(db,request);authorize(db,user,org);obj=record(db,org,kind,ident)
        links=[dict(r) for r in db.execute('SELECT * FROM xp_links WHERE organization_id=%s AND ((source_type=%s AND source_id=%s) OR (target_type=%s AND target_id=%s))',(org,kind,ident,kind,ident)).fetchall()]
        for l in links:
            target=(l['target_type'],l['target_id']) if l['source_type']==kind and l['source_id']==ident else (l['source_type'],l['source_id'])
            l['record']=record(db,org,*target);l['record_type']=target[0]
        if kind=='vendor':
            for a in db.execute('SELECT a.* FROM xp_assessments x JOIN assessments a ON a.id=x.assessment_id WHERE x.organization_id=%s AND x.vendor_id=%s',(org,ident)).fetchall():links.append({'record':dict(a),'record_type':'assessment'})
            reviews=service(db).vendor_reviews(org,ident)
        else:reviews=[]
        if kind=='risk':
            for t in service(db).list_tasks(org):
                if t['risk_id']==ident:links.append({'record':t,'record_type':'task'})
        return {'record':obj,'links':links,'reviews':reviews,'comments':[dict(r) for r in db.execute('SELECT * FROM xp_comments WHERE organization_id=%s AND object_type=%s AND object_id=%s ORDER BY recorded_at',(org,kind,ident)).fetchall()]}


@router.get('/api/experience/{org}/search')
def search(org:str,request:Request,q:str=''):
    with connect() as db:
        user=session(db,request);authorize(db,user,org);needle=text(q,100).casefold();results=[]
        if len(needle)<2:return {'results':[]}
        for kind,table in TABLES.items():
            # Search only explicit display fields; no evidence bytes or credentials.
            for row in db.execute(f'SELECT id,title FROM {table} WHERE organization_id=%s' if kind!='vendor' else 'SELECT id,name AS title FROM vendors WHERE organization_id=%s',(org,)).fetchall():
                if needle in row['title'].casefold():results.append({'type':kind,**dict(row)})
        return {'results':results[:100]}


@router.post('/api/experience/{org}/{action}')
def mutate(org:str,action:str,body:dict,request:Request):
    with connect() as db,db.transaction():
        user=session(db,request,True)
        role=authorize(db,user,org,action not in {'preferences','read_notification'},action)
        username=user['username'];svc=service(db);result={}
        if action=='preferences':
            prefs={k:v for k,v in body.items() if k in {'theme','widgets','onboarding_dismissed','last_questionnaire','last_question'}}
            if 'theme' in prefs and prefs['theme'] not in {'light','dark','system'}:raise HTTPException(422,'Invalid theme')
            if 'widgets' in prefs and (not isinstance(prefs['widgets'],list) or len(prefs['widgets'])>20 or any(not isinstance(x,str) or len(x)>60 for x in prefs['widgets'])):raise HTTPException(422,'Invalid widgets')
            if len(json.dumps(prefs))>4000:raise HTTPException(422,'Preferences too long')
            db.execute('INSERT INTO xp_preferences VALUES (%s,%s,%s::jsonb) ON CONFLICT(username,organization_id) DO UPDATE SET settings=xp_preferences.settings||EXCLUDED.settings',(username,org,json.dumps(prefs)))
        elif action=='settings':
            require_owner(user);cfg=settings(db,org)
            for key in ['brand_name','report_footer','accent','reminders_enabled','reminder_frequency','reminder_lead_days','escalation_days']:
                if key in body:cfg[key]=body[key]
            for key in ['brand_name','report_footer']:
                if key in cfg:cfg[key]=text(cfg[key],250)
            if not re.fullmatch(r'#[0-9a-fA-F]{6}',cfg.get('accent','#097f7a')):raise HTTPException(422,'Use a six-digit hex accent color')
            if cfg.get('reminder_frequency','daily') not in {'daily','weekly'}:raise HTTPException(422,'Choose daily or weekly')
            if not isinstance(cfg.get('reminders_enabled',True),bool):raise HTTPException(422,'Reminder setting must be boolean')
            for key in ['reminder_lead_days','escalation_days']:
                if not isinstance(cfg.get(key,7),int) or isinstance(cfg.get(key,7),bool) or not 0<=cfg.get(key,7)<=90:raise HTTPException(422,'Reminder days must be 0–90')
            db.execute('INSERT INTO xp_settings(organization_id,settings) VALUES (%s,%s::jsonb) ON CONFLICT(organization_id) DO UPDATE SET settings=EXCLUDED.settings',(org,json.dumps(cfg)))
        elif action=='assessment':
            aid=body.get('assessment','');state=meta(db,org,aid);vendor=body.get('vendor') or None
            if vendor:record(db,org,'vendor',vendor)
            reviewer=text(body.get('reviewer',''),100)
            if reviewer and not db.execute("SELECT u.username FROM web_users u LEFT JOIN xp_memberships m ON m.username=u.username AND m.organization_id=%s WHERE u.username=%s AND u.enabled AND (u.role='owner' OR m.role IN ('editor','reviewer'))",(org,reviewer)).fetchone():raise HTTPException(422,'Select an active reviewer in this organization')
            due=valid_date(body.get('due_date',''))
            db.execute('UPDATE xp_assessments SET vendor_id=%s,reviewer=%s,due_date=%s,updated_at=CURRENT_TIMESTAMP WHERE assessment_id=%s',(vendor,reviewer,due,aid))
            if vendor:db.execute('INSERT INTO xp_links VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(str(uuid4()),org,'assessment',aid,'vendor',vendor))
            if reviewer:notify(db,org,reviewer,'Assessment assigned: '+record(db,org,'assessment',aid)['title'],'assessment',aid,'assignment:'+aid+':'+str(epoch()))
        elif action=='response':
            result=save_response(db,org,body.get('assessment',''),body,username)
        elif action=='review':
            aid=body.get('assessment','');state=meta(db,org,aid);decision=body.get('state');notes=text(body.get('notes',''))
            if decision!='submitted' and role!='owner' and state['reviewer']!=username:raise HTTPException(403,'Only the assigned reviewer or owner may review this questionnaire')
            if decision not in {'submitted','needs_changes','approved','draft'}:raise HTTPException(422,'Unsupported review state')
            if decision in {'submitted','approved'} and review_summary(db,org,aid)['unanswered']:raise HTTPException(422,'Complete the applicable questions first')
            if decision=='submitted' and state['state'] not in {'draft','needs_changes'}:raise HTTPException(409,'Reopen before resubmitting')
            if decision=='approved' and state['state']!='submitted':raise HTTPException(409,'Submit before approving')
            if decision=='needs_changes' and not notes:raise HTTPException(422,'Explain the requested changes')
            db.execute('UPDATE xp_assessments SET state=%s,notes=%s,reviewed_by=%s,updated_at=CURRENT_TIMESTAMP WHERE assessment_id=%s',(decision,notes,username,aid))
            svc._audit(svc.db,org,'assessment',aid,'questionnaire_review',{'state':decision,'actor':username})
        elif action=='question_evidence':
            aid=body.get('assessment','');code=body.get('code','');record(db,org,'assessment',aid);record(db,org,'evidence',body.get('evidence',''))
            if not any(q['code']==code for q in svc.questions(org,aid)):raise HTTPException(404,'Question not found')
            db.execute('INSERT INTO xp_question_evidence VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',(org,aid,code,body['evidence']))
            svc.link_evidence(org,body['evidence'],'assessment',aid,'Question '+code)
        elif action=='link':
            source=body.get('source_type');target=body.get('target_type');record(db,org,source,body.get('source_id'));record(db,org,target,body.get('target_id'))
            db.execute('INSERT INTO xp_links VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(str(uuid4()),org,source,body['source_id'],target,body['target_id']))
        elif action=='comment':
            kind=body.get('type');ident=body.get('id');record(db,org,kind,ident);comment=text(body.get('body',''))
            if not comment:raise HTTPException(422,'Enter a comment')
            db.execute('INSERT INTO xp_comments(id,organization_id,object_type,object_id,author,body) VALUES (%s,%s,%s,%s,%s,%s)',(str(uuid4()),org,kind,ident,username,comment))
            for mentioned in set(re.findall(r'@([a-z0-9_.@-]{3,100})',comment.lower())):
                row=db.execute("SELECT u.* FROM web_users u WHERE u.username=%s AND u.enabled AND (u.role='owner' OR EXISTS(SELECT 1 FROM xp_memberships m WHERE m.username=u.username AND m.organization_id=%s))",(mentioned,org)).fetchone()
                if row:notify(db,org,mentioned,'Mention from '+username,kind,ident,'mention:'+str(uuid4()))
        elif action=='task':
            tid=body.get('id','');record(db,org,'task',tid)
            if 'status' in body:
                if body['status']=='done' and db.execute("SELECT 1 FROM xp_dependencies d JOIN remediation_tasks t ON t.id=d.depends_on WHERE d.task_id=%s AND d.organization_id=%s AND t.status<>'done'",(tid,org)).fetchone():raise HTTPException(409,'Finish prerequisite tasks before completing this task')
                svc.update_task_status(org,tid,body['status'],'Updated by '+username)
            if 'due_date' in body:db.execute('UPDATE remediation_tasks SET due_date=%s WHERE id=%s AND organization_id=%s',(valid_date(body['due_date']),tid,org))
            if 'owner' in body:db.execute('UPDATE remediation_tasks SET owner=%s WHERE id=%s AND organization_id=%s',(text(body['owner'],100),tid,org))
        elif action=='dependency':
            tid=body.get('id');parent=body.get('depends_on');record(db,org,'task',tid);record(db,org,'task',parent)
            if tid==parent or db.execute('WITH RECURSIVE ancestors(id) AS (SELECT depends_on FROM xp_dependencies WHERE task_id=%s AND organization_id=%s UNION SELECT d.depends_on FROM xp_dependencies d JOIN ancestors a ON d.task_id=a.id WHERE d.organization_id=%s) SELECT 1 FROM ancestors WHERE id=%s',(parent,org,org,tid)).fetchone():raise HTTPException(422,'Dependencies must not contain a cycle')
            db.execute('INSERT INTO xp_dependencies VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(org,tid,parent))
        elif action=='read_notification':
            db.execute('UPDATE xp_notifications SET read_at=CURRENT_TIMESTAMP WHERE id=%s AND username=%s AND organization_id=%s',(body.get('id',''),username,org))
        elif action=='capture':capture(db,org)
        elif action=='run_reminders':require_owner(user);tick(db)
        elif action=='invite':
            require_owner(user);kind=body.get('kind');aid=body.get('assessment') or None;uname=text(body.get('username',''),100).lower();member_role=body.get('role','viewer')
            if kind not in {'team','vendor'} or member_role not in {'editor','reviewer','viewer'}:raise HTTPException(422,'Invalid invitation type or role')
            if kind=='vendor':
                record(db,org,'assessment',aid)
                if not all(q['code'].startswith('TPR-') for q in svc.questions(org,aid)):raise HTTPException(422,'Vendor portal supports the default third-party questionnaire')
            elif not re.fullmatch(r'[a-z0-9_.@-]{3,100}',uname):raise HTTPException(422,'Enter a valid username')
            days=body.get('days',7)
            if not isinstance(days,int) or isinstance(days,bool) or not 1<=days<=30:raise HTTPException(422,'Invitation expires in 1–30 days')
            token=secrets.token_urlsafe(48)
            db.execute('INSERT INTO xp_invites(token_hash,kind,organization_id,assessment_id,username,role,expires_at,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(hash_token(token),kind,org,aid,uname,member_role,epoch()+days*86400,username))
            result={'token':token,'path':'/portal#'+token if kind=='vendor' else '/join#'+token,'expires_in_days':days}
        elif action=='revoke_invite':
            require_owner(user);db.execute('UPDATE xp_invites SET revoked=TRUE WHERE token_hash=%s AND organization_id=%s',(body.get('id',''),org))
        elif action=='membership':
            require_owner(user);uname=text(body.get('username',''),100);member_role=body.get('role')
            if member_role not in {'editor','reviewer','viewer','remove'}:raise HTTPException(422,'Invalid role')
            target=db.execute("SELECT username FROM web_users WHERE username=%s AND role<>'owner'",(uname,)).fetchone()
            if not target:raise HTTPException(422,'Select a non-owner account')
            if member_role=='remove':db.execute('DELETE FROM xp_memberships WHERE username=%s AND organization_id=%s',(uname,org))
            else:db.execute('INSERT INTO xp_memberships VALUES (%s,%s,%s) ON CONFLICT(username,organization_id) DO UPDATE SET role=EXCLUDED.role',(uname,org,member_role))
        else:raise HTTPException(404,'Unknown workspace action')
        audit(db,username,action)
        return result


@router.get('/api/experience/{org}/dependencies')
def dependencies(org:str,request:Request):
    with connect() as db:
        u=session(db,request);authorize(db,u,org)
        return [dict(r) for r in db.execute('SELECT * FROM xp_dependencies WHERE organization_id=%s',(org,)).fetchall()]


@router.get('/api/experience/{org}/invites')
def invitations(org:str,request:Request):
    with connect() as db:
        u=session(db,request);authorize(db,u,org);require_owner(u)
        return [dict(r) for r in db.execute('SELECT token_hash AS id,kind,assessment_id,username,role,expires_at,revoked,redeemed FROM xp_invites WHERE organization_id=%s ORDER BY created_at DESC',(org,)).fetchall()]


@router.post('/api/experience/{org}/branding/logo')
async def logo_upload(org:str,request:Request):
    from cyberstudio.report_branding import normalize_logo
    with connect() as db,db.transaction():
        u=session(db,request,True);authorize(db,u,org,True);require_owner(u)
        payload=await request.body()
        payload=normalize_logo(payload)
        db.execute("INSERT INTO xp_settings(organization_id,logo,logo_mime) VALUES (%s,%s,'image/png') ON CONFLICT(organization_id) DO UPDATE SET logo=EXCLUDED.logo,logo_mime=EXCLUDED.logo_mime",(org,payload));audit(db,u['username'],'logo')
    return {'saved':True}


@router.get('/api/experience/{org}/branding/logo')
def logo_download(org:str,request:Request):
    with connect() as db:
        u=session(db,request);authorize(db,u,org);r=db.execute('SELECT logo,logo_mime FROM xp_settings WHERE organization_id=%s',(org,)).fetchone()
        if not r or not r['logo']:raise HTTPException(404,'No logo configured')
        return Response(bytes(r['logo']),media_type=r['logo_mime'])


def vendor_session(db,request,write=False):
    import hmac
    r=db.execute('SELECT s.*,i.organization_id,i.assessment_id FROM xp_vendor_sessions s JOIN xp_invites i ON i.token_hash=s.invite_hash WHERE s.token_hash=%s AND s.expires_at>%s AND i.expires_at>%s AND NOT i.revoked',(hash_token(request.cookies.get(VCOOKIE,'')),epoch(),epoch())).fetchone()
    if not r:raise HTTPException(401,'Invitation session expired or revoked')
    if write and not hmac.compare_digest(request.headers.get('x-csrf-token',''),r['csrf']):raise HTTPException(403,'Refresh this invitation session')
    return r


@router.post('/api/invitation/redeem')
def redeem(body:dict,request:Request):
    from .app import hasher,limit
    token=text(body.get('token',''),100)
    with connect() as db:
        with db.transaction():limit(db,'invite:'+hash_token(token))
        with db.transaction():
            r=db.execute('SELECT * FROM xp_invites WHERE token_hash=%s AND expires_at>%s AND NOT revoked FOR UPDATE',(hash_token(token),epoch())).fetchone()
            if not r or r['redeemed']:raise HTTPException(403,'Invitation is invalid, expired, revoked, or already redeemed')
            if r['kind']=='team':
                password=text(body.get('password',''),256)
                if len(password)<16:raise HTTPException(422,'Use a password of at least 16 characters')
                if db.execute('SELECT 1 FROM web_users WHERE username=%s',(r['username'],)).fetchone():raise HTTPException(409,'Account already exists. The owner can grant membership without resetting its password.')
                db.execute('INSERT INTO web_users(username,password_hash,created_at,role) VALUES (%s,%s,%s,%s)',(r['username'],hasher.hash(password),epoch(),'member'))
                db.execute('INSERT INTO xp_memberships VALUES (%s,%s,%s)',(r['username'],r['organization_id'],r['role']))
                audit(db,r['created_by'],'team_invitation_redeemed')
                response=JSONResponse({'status':'Account created. Sign in with your invited username.','username':r['username']})
            else:
                session_token=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(32);expires=min(epoch()+28800,r['expires_at'])
                db.execute('INSERT INTO xp_vendor_sessions VALUES (%s,%s,%s,%s)',(hash_token(session_token),r['token_hash'],csrf,expires))
                response=JSONResponse({'status':'Invitation accepted','csrf':csrf})
                response.set_cookie(VCOOKIE,session_token,max_age=expires-epoch(),secure=True,httponly=True,samesite='strict',path='/')
            db.execute('UPDATE xp_invites SET redeemed=TRUE WHERE token_hash=%s',(r['token_hash'],))
            return response


@router.get('/api/portal')
def portal_data(request:Request):
    with connect() as db,db.transaction():
        r=vendor_session(db,request);org=r['organization_id'];aid=r['assessment_id'];a=record(db,org,'assessment',aid)
        qs=question_state(db,org,aid)
        # Never disclose internal evidence, internal review notes, identities, or record IDs.
        for q in qs:
            for key in list(q):
                if key not in {'code','prompt','rationale','visible','section','version'}:del q[key]
        return {'title':a['title'],'csrf':r['csrf'],'state':meta(db,org,aid)['state'],'questions':qs}


@router.post('/api/portal/{action}')
def portal_write(action:str,body:dict,request:Request):
    with connect() as db,db.transaction():
        r=vendor_session(db,request,True);org=r['organization_id'];aid=r['assessment_id']
        if action=='response':return save_response(db,org,aid,body,'vendor',True)
        if action=='submit':
            if review_summary(db,org,aid)['unanswered']:raise HTTPException(422,'Complete applicable questions before submitting')
            current=meta(db,org,aid)
            if current['state'] not in {'draft','needs_changes'}:raise HTTPException(409,'Questionnaire already submitted')
            db.execute("UPDATE xp_assessments SET state='submitted',updated_at=CURRENT_TIMESTAMP WHERE assessment_id=%s",(aid,))
            service(db)._audit(service(db).db,org,'assessment',aid,'vendor_submitted',{'invitation':r['invite_hash'][:12]})
            if current['reviewer']:notify(db,org,current['reviewer'],'Vendor questionnaire submitted','assessment',aid,'submitted:'+aid+':'+str(epoch()))
            return {'submitted':True}
        raise HTTPException(404,'Unsupported vendor action')


@router.post('/api/portal/evidence/{code}')
async def portal_evidence(code:str,request:Request):
    form=await request.form(max_files=1,max_fields=2,max_part_size=6*1024*1024);file=form.get('file')
    if not file or not hasattr(file,'read'):raise HTTPException(422,'Select an evidence file')
    payload=await file.read(5*1024*1024+1)
    if len(payload)>5*1024*1024:raise HTTPException(413,'File exceeds 5 MiB')
    with connect() as db,db.transaction():
        r=vendor_session(db,request,True);org=r['organization_id'];aid=r['assessment_id']
        if meta(db,org,aid)['state'] not in {'draft','needs_changes'}:raise HTTPException(409,'Questionnaire is locked')
        if code not in {q['code'] for q in service(db).questions(org,aid)}:raise HTTPException(404,'Question not found')
        eid=service(db).add_evidence(org,'Vendor submission: '+code,file.filename or 'evidence',payload,file.content_type or 'application/octet-stream')
        db.execute('INSERT INTO xp_question_evidence VALUES (%s,%s,%s,%s)',(org,aid,code,eid))
        service(db).link_evidence(org,eid,'assessment',aid,'Vendor submitted for '+code)
    return {'uploaded':True,'review_status':'pending'}


@router.get('/portal')
@router.get('/join')
def invitation_page():
    from .app import STATIC
    return FileResponse(STATIC/'invitation.html')


def report_payload(db,org,body):
    start=valid_date(body.get('start',''));end=valid_date(body.get('end',''))
    if start and end and start>end:raise HTTPException(422,'Report end must follow its start')
    selected=body.get('sections',['summary','risks','tasks','vendors','frameworks'])
    allowed={'summary','risks','tasks','vendors','frameworks','findings','history'}
    if not isinstance(selected,list) or not selected or any(s not in allowed for s in selected):raise HTTPException(422,'Select supported report sections')
    svc=service(db);sections={};cfg=settings(db,org)
    sources={'risks':svc.list_risks,'tasks':svc.list_tasks,'vendors':svc.vendors,'frameworks':svc.implementations,'findings':svc.findings}
    for key in selected:
        if key=='summary':sections[key]=[{'metric':k,'value':v} for k,v in svc.overview(org).items()]
        elif key=='history':sections[key]=[{'day':str(r['day']),**r['metrics']} for r in db.execute('SELECT day,metrics FROM xp_snapshots WHERE organization_id=%s AND (%s=%s OR day>=%s::date) AND (%s=%s OR day<=%s::date) ORDER BY day',(org,start,'',start or None,end,'',end or None)).fetchall()]
        else:
            records=sources[key](org)
            sections[key]=[{k:r.get(k,'') for k in ['title' if key!='vendors' else 'name','status','owner','score' if key=='risks' else 'due_date']} for r in records if (not start or str(r.get('created_at',r.get('updated_at','')))[:10]>=start) and (not end or str(r.get('created_at',r.get('updated_at','')))[:10]<=end)]
    return {'organization':svc.organization(org)['name'],'brand':cfg.get('brand_name',''),'accent':cfg.get('accent','#097f7a'),'footer':cfg.get('report_footer',''),'start':start,'end':end,'commentary':text(body.get('commentary','')),'sections':sections,'as_of':datetime.now(timezone.utc).isoformat(),'period_note':'Summary is current as of export. Period filters apply to record creation (or update when no creation date exists) and daily snapshots. No retrospective exposure is inferred.'}


@router.post('/api/experience/{org}/reports/{format}')
def custom_report(org:str,format:str,body:dict,request:Request):
    with connect() as db:
        u=session(db,request,True);authorize(db,u,org)
        payload=report_payload(db,org,body)
        brand=service(db).report_branding(org)
        if format=='preview':return payload
        if format not in {'pdf','xlsx'}:raise HTTPException(404,'Unsupported format')
        target=io.BytesIO()
        if format=='pdf':
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from xml.sax.saxutils import escape
            styles=getSampleStyleSheet();story=[]
            accent=colors.HexColor(payload['accent'])
            ink=colors.black if (accent.red*.299+accent.green*.587+accent.blue*.114)>.6 else colors.white
            header_style=ParagraphStyle('Branded table heading',parent=styles['BodyText'],textColor=ink)
            story.extend([Paragraph(escape(payload['brand'] or payload['organization']),styles['Title']),Paragraph('Security Program | Board Report',styles['Heading1']),Paragraph(escape(payload['period_note']),styles['BodyText']),Spacer(1,12)])
            if payload['commentary']:story.extend([Paragraph('Management commentary',styles['Heading2']),Paragraph(escape(payload['commentary']).replace('\n','<br/>'),styles['BodyText'])])
            for key,items in payload['sections'].items():
                story.append(Paragraph(key.title(),styles['Heading2']))
                if not items:story.append(Paragraph('No records in the selected period.',styles['BodyText']));continue
                columns=list(items[0]);data=[[Paragraph(escape(k.replace('_',' ').title()),header_style) for k in columns]]
                for r in items:data.append([Paragraph(escape(str(r.get(k,''))),styles['BodyText']) for k in columns])
                table=Table(data,colWidths=[490/len(columns)]*len(columns),repeatRows=1);table.setStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(payload['accent'])),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.lightgrey),('BOTTOMPADDING',(0,0),(-1,-1),8)])
                story.append(table);story.append(Spacer(1,12))
            story.append(Paragraph(escape(payload['footer'] or 'Management records; not an independent audit or certification.'),styles['BodyText']))
            from functools import partial
            from cyberstudio.report_style import pdf_page
            SimpleDocTemplate(target,title='Security Program Board Report',leftMargin=46,rightMargin=46,topMargin=112,bottomMargin=64).build(story,onFirstPage=partial(pdf_page,brand=brand),onLaterPages=partial(pdf_page,brand=brand))
            mime='application/pdf'
        else:
            from openpyxl import Workbook
            from cyberstudio.reports import _safe_excel
            from cyberstudio.report_style import style_workbook
            wb=Workbook();ws=wb.active;ws.title='Report';ws.append(['Security Program Board Report',_safe_excel(payload['brand'] or payload['organization'])]);ws.append(['As of',payload['as_of']]);ws.append(['Period',payload['start']+' to '+payload['end']]);ws.append(['Commentary',_safe_excel(payload['commentary'])]);ws.append(['Basis',payload['period_note']]);ws.append(['Footer',_safe_excel(payload['footer'])])
            for key,items in payload['sections'].items():
                sheet=wb.create_sheet(key.title());columns=list(items[0]) if items else ['No records'];sheet.append(columns)
                for row in items:sheet.append([_safe_excel(str(row.get(c,''))) for c in columns])
            style_workbook(wb,summary_header=1,brand=brand);ws.row_dimensions[4].height=90;wb.save(target);mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        audit(db,u['username'],'custom_report:'+format)
        return Response(target.getvalue(),media_type=mime,headers={'Content-Disposition':'attachment; filename="board-report.'+format+'"'})
