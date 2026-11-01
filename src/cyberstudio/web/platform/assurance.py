"""Bounded, organization-scoped assurance tools. Export is a portable workbench
package, not a database backup; imported approvals never become trusted decisions.
"""
from datetime import date,datetime,timezone,timedelta
import base64,hashlib,json,re
from fastapi import HTTPException
from . import store,catalog,operations
from .assurance_catalog import FEATURES

CLOSED={'completed','closed','rejected'}
SERVICES=['endpoint','encryption','patching','identity','logging','backup']
MAX_RECORDS=2000

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
def today():return date.today().isoformat()
def records(db,org):return operations.rows(db,org)
def demo(db,org):return bool(db.execute('SELECT 1 FROM pl_demo WHERE organization_id=%s',(org,)).fetchone())
def current_evidence(db,org,ids):
    if not ids:return False
    try:store.require_verified_evidence(db,org,ids);return True
    except HTTPException:return False

def validate(db,org,kind,d):
    if kind in {'as_view','as_metric'} and d.get('module') not in catalog.MODULES:store.fail('Choose a supported module')
    if kind=='as_metric' and (not d.get('measure') or not d.get('direction')):store.fail('Choose a measure and target direction')
    if kind=='as_coverage':
        if not d.get('service') or not d.get('result') or not 1<=d['valid_days']<=3650:store.fail('Choose protection, outcome and a 1–3650 day interval')
        if d.get('observed_on','9999')>today():store.fail('Record a current or historical observation date')
        if d['result']=='pass' and not current_evidence(db,org,d.get('evidence_ids',[])):store.fail('A passing protection observation needs verified evidence')
        if d['result']=='excluded' and not d.get('rationale'):store.fail('Explain the exclusion')
    if kind=='as_detection' and d.get('result')=='pass':
        if not d.get('test_case') or not d.get('last_test') or not current_evidence(db,org,d.get('evidence_ids',[])):store.fail('Passing detection tests require a dated procedure and verified evidence')
    if kind=='as_reuse':
        if not all(d.get(k) for k in ('period_start','period_end','scope','review_on')) or d['period_start']>d['period_end']:store.fail('Record scope and a valid assessment period and review deadline')
        if not current_evidence(db,org,[d['evidence_id']]):store.fail('Reuse needs a currently verified artifact')
    if kind=='as_release':
        for key in ('source_sha','deployed_sha'):
            if d.get(key) and not re.fullmatch('[0-9a-f]{40}',d[key]):store.fail('Use full lowercase Git commit hashes')
        if d.get('validation')=='pass' and (not d.get('observed_on') or not current_evidence(db,org,d.get('evidence_ids',[]))):store.fail('Passing release validation needs a date and verified evidence')
    for key in ('last_test','observed_on','completed_on','decided_on'):
        if d.get(key) and d[key]>today():store.fail('Observed dates cannot be in the future')
    if kind=='as_delivery':
        if not db.execute('SELECT 1 FROM pl_jobs WHERE organization_id=%s AND id=%s AND (kind=\'integration:notify\' OR kind LIKE \'schedule:%%\')',(org,d['job_id'])).fetchone():store.fail('Notification job not found',404)
        if d.get('backup_owner') and not member(db,org,d['backup_owner']):store.fail('Choose an enabled organization backup owner')
    return d

def member(db,org,username):return bool(db.execute("SELECT 1 FROM web_users u WHERE username=%s AND enabled AND (role='owner' OR EXISTS(SELECT 1 FROM xp_memberships m WHERE m.username=u.username AND m.organization_id=%s))",(username,org)).fetchone())

def quality(db,org,rs):
    issues=[];names={};active_members={r['username'] for r in db.execute("SELECT username FROM web_users u WHERE enabled AND (role='owner' OR EXISTS(SELECT 1 FROM xp_memberships m WHERE m.username=u.username AND m.organization_id=%s))",(org,)).fetchall()}
    for r in rs:
        if not r['owner']:issues.append(item(r,'missing_owner'))
        elif r['owner'] not in active_members:issues.append(item(r,'owner_not_enabled_member'))
        key=(r['kind'],r['title'].strip().casefold());names.setdefault(key,[]).append(r)
        fields=catalog.MODULES.get(r['kind'],('',{}))[1]
        for name,f in fields.items():
            v=r['data'].get(name)
            if f['required'] and (v is None or v=='' or v==[]):issues.append(item(r,'incomplete:'+name))
            if v and f['type'] in {'reference','references'}:
                for ident in v if isinstance(v,list) else [v]:
                    try:store.reference(db,org,ident,f['ref'])
                    except HTTPException:issues.append(item(r,'unavailable_reference:'+name))
    for group in names.values():
        if len(group)>1:issues.extend(item(r,'possible_duplicate_title') for r in group)
    return issues

def item(r,reason):return {'id':r['id'],'kind':r['kind'],'title':r['title'],'owner':r['owner'],'reason':reason}

def control_coverage(db,org,rs):
    checks=operations.summary(db,{'role':'viewer'},org)['checks'];by_id={r['id']:r for r in rs};groups={}
    for c in checks:
        raw=by_id[c['id']];groups.setdefault(raw['data']['control_id'],[]).append(c)
    result=[]
    for r in rs:
        if r['kind']!='control':continue
        cs=groups.get(r['id'],[]);outcomes=[c['outcome'] for c in cs]
        state='unknown' if not cs or 'unknown' in outcomes else 'failed' if 'fail' in outcomes else 'verified'
        if 'fail' in outcomes:state='failed'
        result.append({**item(r,''),'state':state,'checks':len(cs),'basis':'Latest recorded validation and configuration freshness; not live fleet coverage'})
    counts={s:sum(r['state']==s for r in result) for s in ('verified','failed','unknown')};n=len(result)
    return {'rows':result,'counts':counts,'denominator':n,'verified_percent':round(100*counts['verified']/n,2) if n else None}

def service_coverage(db,org,rs):
    assets=[r for r in rs if r['kind']=='asset'];observations={}
    for r in rs:
        if r['kind']=='as_coverage':
            key=(r['data']['asset_id'],r['data']['service'])
            if key not in observations:observations[key]=r
    output=[]
    for a in assets:
        for service in SERVICES:
            r=observations.get((a['id'],service));state='unknown';d=r['data'] if r else {}
            if r:
                state=d.get('result','unknown')
                if (date.today()-date.fromisoformat(d['observed_on'])).days>d['valid_days']:state='stale'
                elif state=='pass' and not current_evidence(db,org,d.get('evidence_ids',[])):state='unknown'
            output.append({'id':r['id'] if r else a['id'],'title':a['title'],'asset_id':a['id'],'site_id':a['data'].get('site_id'),'service':service,'state':state,'observed_on':d.get('observed_on')})
    counts={s:sum(r['state']==s for r in output) for s in ('pass','fail','stale','unknown','excluded')};den=len(output)-counts['excluded']
    return {'rows':output,'counts':counts,'denominator':den,'excluded':counts['excluded'],'verified_percent':round(100*counts['pass']/den,2) if den else None,'basis':'Six service expectations per inventoried asset. Missing assets are outside the known denominator. Exclusions remain visible.'}

def reuse_state(db,org,r):
    d=r['data'];valid=d['period_start']<=today()<=d['period_end'] and d['review_on']>=today() and current_evidence(db,org,[d['evidence_id']])
    for name,kind in [('control_id','control'),('asset_id','asset')]:
        try:store.get(db,org,d[name],kind)
        except HTTPException:valid=False
    return {**item(r,''),'eligible':valid,'scope':d['scope'],'period_start':d['period_start'],'period_end':d['period_end'],'basis':'Explicit system/control scope; no cross-organization or automatic framework-wide reuse'}

def release_state(db,org,r):
    d=r['data'];reasons=[]
    for ok,reason in [(d.get('validation')=='pass','Validation has not passed'),(d.get('migration') in {'pass','not_required'},'Migration unresolved'),(d.get('defects')==0,'Blocking defects remain'),(bool(d.get('rollback')),'Rollback missing'),(bool(d.get('acceptance')),'Acceptance missing'),(current_evidence(db,org,d.get('evidence_ids',[])),'Evidence unavailable or stale'),(bool(d.get('observed_on')),'Observation date missing')]:
        if not ok:reasons.append(reason)
    return {**item(r,''),'ready':not reasons,'blockers':reasons,'source_sha':d['source_sha'],'deployed_sha':d.get('deployed_sha'),'matches_deployed':bool(d.get('deployed_sha')) and d['source_sha']==d['deployed_sha'],'basis':'Operator-recorded release evidence, not automatic deployment attestation'}

def metric(rs,r):
    d=r['data'];scope=[x for x in rs if x['kind']==d['module']];n=len(scope);measure=d['measure']
    numerator=sum(x['status']=='completed' for x in scope) if measure=='completed_percent' else sum(bool(x['due_on']) and str(x['due_on'])<today() and x['status'] not in CLOSED for x in scope) if measure=='overdue' else n
    value=round(100*numerator/n,2) if measure=='completed_percent' and n else None if measure=='completed_percent' else numerator
    target=d.get('target');met=None if value is None or target is None else value>=target if d['direction']=='at_least' else value<=target
    return {'id':r['id'],'title':r['title'],'module':d['module'],'measure':measure,'numerator':numerator,'denominator':n,'value':value,'target':target,'target_met':met,'basis':'Current non-archived module records; empty percentage is Unknown'}

def deliveries(db,org):
    return [dict(r) for r in db.execute("SELECT id,kind,status,attempts,result,updated_at FROM pl_jobs WHERE organization_id=%s AND (kind='integration:notify' OR kind LIKE 'schedule:%%') ORDER BY created_at DESC LIMIT 200",(org,)).fetchall()]

def overview(db,user,org):
    rs=records(db,org);username=user['username'];work=[]
    for r in rs:
        if r['status'] in CLOSED:continue
        reason='assigned_approval' if r['status']=='submitted' and r['data'].get('approver')==username else 'assigned_work' if r['owner']==username else None
        if reason:work.append({**item(r,reason),'due_on':r['due_on'],'status':r['status'],'overdue':bool(r['due_on']) and str(r['due_on'])<today()})
    state=operations.summary(db,user,org)
    for c in state['checks']:
        if c['owner']==username and c['outcome']!='pass':work.append({**c,'reason':'validation:'+c['outcome']})
    for e in state['evidence_due']:
        if e['owner']==username:work.append({**e,'reason':'evidence_due'})
    jobs=deliveries(db,org) if user['role']=='owner' else []
    acks={r['record_id'] for r in db.execute("SELECT record_id FROM pl_history WHERE organization_id=%s AND action='assurance:acknowledged'",(org,)).fetchall()}
    for j in jobs:
        j['delivery_state']='provider_accepted' if j['status']=='succeeded' else j['status'];j['acknowledged']=j['id'] in acks
        j['receipt_note']='Job success establishes provider acceptance, not recipient delivery. No delivery webhook is configured.'
    return {'features':FEATURES,'my_work':work,'quality':quality(db,org,rs),'control_coverage':control_coverage(db,org,rs),'service_coverage':service_coverage(db,org,rs),'evidence_reuse':[reuse_state(db,org,r) for r in rs if r['kind']=='as_reuse'],'releases':[release_state(db,org,r) for r in rs if r['kind']=='as_release'],'metrics':[metric(rs,r) for r in rs if r['kind']=='as_metric'],'deliveries':jobs,'demo':demo(db,org),'observed_at':datetime.now(timezone.utc).isoformat()}

def search(db,org,body):
    view=store.get(db,org,body['view_id'],'as_view')['data'] if body.get('view_id') else body
    module=view.get('module');q=store.bounded(view.get('query',''),100);status=view.get('status_filter','all');owner=store.bounded(view.get('owner_filter',''),100)
    if module not in catalog.MODULES or status not in ['all',*catalog.STATUSES]:store.fail('Invalid module or status')
    sort=view.get('sort_by','updated_at');direction=view.get('direction','descending')
    if sort not in {'title','due_on','updated_at'} or direction not in {'ascending','descending'}:store.fail('Invalid sort')
    offset=body.get('offset',0)
    if type(offset) is not int or not 0<=offset<=100000:store.fail('Invalid offset')
    from psycopg import sql
    # Only fixed identifiers are interpolated. All user values remain bound.
    query=sql.SQL("SELECT * FROM pl_records WHERE organization_id=%s AND kind=%s AND deleted_at IS NULL AND title ILIKE %s AND (%s='all' OR status=%s) AND (%s='' OR owner=%s) ORDER BY {} {} NULLS LAST,id LIMIT 101 OFFSET %s").format(sql.Identifier(sort),sql.SQL('ASC' if direction=='ascending' else 'DESC'))
    rows=[dict(r) for r in db.execute(query,(org,module,'%'+q+'%',status,status,owner,owner,offset)).fetchall()]
    return {'rows':rows[:100],'has_more':len(rows)>100,'offset':offset}

def bulk(db,user,org,body):
    ids=body.get('ids');changes=body.get('changes')
    if not isinstance(ids,list) or not 1<=len(ids)<=100 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):store.fail('Choose 1–100 unique records')
    if not isinstance(changes,dict) or not changes or set(changes)-{'owner','due_on'}:store.fail('Bulk changes support owner and due date')
    if 'owner' in changes and not member(db,org,changes['owner']):store.fail('Choose an enabled organization owner')
    if changes.get('due_on'):
        try:date.fromisoformat(changes['due_on'])
        except (ValueError,TypeError):store.fail('Use a valid due date')
    rs=[store.get(db,org,i,lock=True) for i in sorted(ids)]
    for r in rs:
        if r['status'] not in {'draft','in_progress'}:store.fail('Bulk edits require draft or in-progress records',409)
        store.validate(db,org,r['kind'],r['data'])
        if r['kind'].startswith('op_'):operations.guard_save(db,user,org,r['kind'],r['data'])
    fingerprint=digest({'records':rs,'changes':changes})
    if body.get('confirmed') is not True:return {'preview':[{'id':r['id'],'title':r['title'],'version':r['version'],'owner':r['owner'],'due_on':r['due_on']} for r in rs],'changes':changes,'confirmation_hash':fingerprint}
    if body.get('confirmation_hash')!=fingerprint:store.fail('Records changed since preview',409)
    for r in rs:store.save(db,user,org,r['kind'],{**r,**changes})
    return {'updated':len(rs)}

def catalog_diff(db,org,body):
    ids=[store.bounded(body.get(k,''),100) for k in ('before','after')]
    if ids[0]==ids[1]:store.fail('Choose two different catalog editions')
    catalogs=[];sets=[]
    for ident in ids:
        row=db.execute('SELECT id,name,edition,sha256 FROM pl_catalogs WHERE organization_id=%s AND id=%s',(org,ident)).fetchone()
        if not row:store.fail('Catalog not found',404)
        catalogs.append(dict(row));sets.append({r['code']:dict(r) for r in db.execute('SELECT code,title,parent_code FROM pl_controls WHERE organization_id=%s AND catalog_id=%s',(org,ident)).fetchall()})
    a,b=sets;changed=[k for k in a.keys()&b.keys() if a[k]!=b[k]];rs=records(db,org);impacted=[r for r in rs if r['kind']=='control' and any(m['catalog_id']==ids[0] for m in r['data'].get('catalog_mappings',[]))]
    return {'catalogs':catalogs,'added':[b[k] for k in sorted(b.keys()-a.keys())],'removed':[a[k] for k in sorted(a.keys()-b.keys())],'changed':[{'before':a[k],'after':b[k]} for k in sorted(changed)],'unchanged':sorted(k for k in a.keys()&b.keys() if a[k]==b[k]),'impacted':[{'id':r['id'],'title':r['title'],'version':r['version']} for r in impacted],'confirmation_hash':digest({'catalogs':catalogs,'impacted':impacted})}

def migrate(db,user,org,body):
    # Lock every impacted control before deriving the reviewed preview.
    db.execute("SELECT id FROM pl_records WHERE organization_id=%s AND kind='control' AND deleted_at IS NULL ORDER BY id FOR UPDATE",(org,)).fetchall()
    p=catalog_diff(db,org,body)
    if body.get('confirmed') is not True:return p
    if body.get('confirmation_hash')!=p['confirmation_hash']:store.fail('Catalog mappings changed; preview again',409)
    if p['removed'] or p['changed']:store.fail('Changed or removed requirements require manual review; only unchanged mappings migrate automatically',409)
    for item in p['impacted']:
        r=store.get(db,org,item['id']);d=dict(r['data']);d['catalog_mappings']=[{**m,'catalog_id':body['after']} if m['catalog_id']==body['before'] else m for m in d.get('catalog_mappings',[])]
        store.save(db,user,org,'control',{**r,'data':d});store.history(db,org,r['id'],user['username'],'assurance:catalog_migrated',{'before':body['before'],'after':body['after'],'preview_hash':p['confirmation_hash']})
    return {'updated':len(p['impacted'])}

def export_package(db,user,org):
    from ..database import service
    rs=records(db,org)
    if len(rs)>MAX_RECORDS:store.fail('Package limit is 2,000 program records; use a database backup for larger recovery',413)
    evidence=[];size=0;svc=service(db)
    for e in svc.evidence(org):
        content=svc.evidence_bytes(org,e['id']);size+=len(content)
        if size>10*1024*1024:store.fail('Evidence package limit is 10 MiB; use managed database recovery for larger workspaces',413)
        evidence.append({'id':e['id'],'title':e['title'],'filename':e['filename'],'mime_type':e['mime_type'],'sha256':hashlib.sha256(content).hexdigest(),'content_base64':base64.b64encode(content).decode()})
    catalogs=[]
    for c in db.execute('SELECT id,name,edition,source,license_note,sha256 FROM pl_catalogs WHERE organization_id=%s',(org,)).fetchall():
        catalogs.append({**dict(c),'controls':[dict(r) for r in db.execute('SELECT code,title,parent_code FROM pl_controls WHERE organization_id=%s AND catalog_id=%s',(org,c['id'])).fetchall()]})
    payload={'format':'studio-workbench-v1','organization_id':org,'exported_at':datetime.now(timezone.utc).isoformat(),'program_owner':'Matthew Harris','records':rs,'evidence':evidence,'catalogs':catalogs,'scope':'Program records, evidence bytes and framework catalogs. Excludes legacy business registers, identities, credentials, delivery configuration, frozen editions and historical audit events. This is not a complete database backup.'}
    # JSON round-trip normalizes database dates before download/hash verification.
    payload=json.loads(json.dumps(payload,default=str));return {'payload':payload,'sha256':digest(payload)}

def package_preview(db,org,package):
    if not isinstance(package,dict) or set(package)!={'payload','sha256'}:store.fail('Choose a Studio workbench package')
    p=package['payload']
    if not isinstance(p,dict) or digest(p)!=package['sha256'] or p.get('format')!='studio-workbench-v1' or p.get('organization_id')!=org:store.fail('Package hash, format or organization does not match')
    rs=p.get('records');ev=p.get('evidence')
    if not isinstance(rs,list) or len(rs)>MAX_RECORDS or not isinstance(ev,list) or len(ev)>2000:store.fail('Invalid package limits')
    if len({r.get('id') for r in rs})!=len(rs):store.fail('Duplicate package record IDs')
    bytes_total=0
    for e in ev:
        try:raw=base64.b64decode(e['content_base64'],validate=True)
        except (ValueError,KeyError,TypeError):store.fail('Invalid evidence encoding')
        bytes_total+=len(raw)
        if bytes_total>10*1024*1024 or hashlib.sha256(raw).hexdigest()!=e.get('sha256'):store.fail('Evidence integrity check failed')
    output=[]
    for r in rs:
        if not isinstance(r,dict) or r.get('kind') not in catalog.MODULES or r.get('organization_id')!=org:store.fail('Invalid packaged record')
        existing=db.execute('SELECT version,deleted_at FROM pl_records WHERE organization_id=%s AND id=%s',(org,r['id'])).fetchone()
        state='conflict_existing' if existing and existing['deleted_at'] is None else 'recoverable_archived' if existing else 'missing_requires_database_restore'
        output.append({'id':r['id'],'title':r['title'],'state':state,'version':existing['version'] if existing else None})
    return {'records':output,'evidence_integrity_verified':len(ev),'scope':p['scope'],'confirmation_hash':digest({'package':package['sha256'],'records':output}),'note':'Recovery reopens archived program records in the original organization as drafts. Existing records are skipped. Missing records, evidence and catalogs require managed database restore; the package retains their contents for investigation.'}

def recover(db,user,org,body):
    package=body.get('package');p=package_preview(db,org,package)
    if body.get('confirmed') is not True:return p
    # Lock all candidates before re-deriving conflict state.
    for item in sorted(p['records'],key=lambda r:r['id']):
        db.execute('SELECT id FROM pl_records WHERE organization_id=%s AND id=%s FOR UPDATE',(org,item['id'])).fetchone()
    p=package_preview(db,org,package)
    if p['confirmation_hash']!=body.get('confirmation_hash'):store.fail('Recovery conflicts changed; preview again',409)
    restored=0
    for item in p['records']:
        if item['state']!='recoverable_archived':continue
        original=next(r for r in package['payload']['records'] if r['id']==item['id'])
        # Restore availability only, preserve current contents/history. Never replay approval metadata.
        r=store.get(db,org,item['id'],deleted=True)
        if r['kind']!=original['kind']:store.fail('Recovery kind mismatch',409)
        d={k:v for k,v in r['data'].items() if k not in {'approved_by','approved_at','approval_version'}}
        db.execute("UPDATE pl_records SET deleted_at=NULL,status='draft',data=%s::jsonb,version=version+1,updated_by=%s,updated_at=CURRENT_TIMESTAMP WHERE organization_id=%s AND id=%s",(json.dumps(d),user['username'],org,r['id']))
        db.execute("DELETE FROM pl_trash WHERE organization_id=%s AND kind='program' AND record_id=%s",(org,r['id']))
        store.history(db,org,r['id'],user['username'],'assurance:recovered',{'package_sha256':package['sha256'],'source_version':original['version'],'mode':'reopen_archived_as_draft'});restored+=1
    return {'recovered':restored,'skipped':len(p['records'])-restored}

def acknowledge(db,user,org,body):
    ident=store.bounded(body.get('job_id',''),100)
    if not any(j['id']==ident for j in deliveries(db,org)):store.fail('Notification job not found',404)
    if not db.execute("SELECT 1 FROM pl_history WHERE organization_id=%s AND record_id=%s AND action='assurance:acknowledged'",(org,ident)).fetchone():store.history(db,org,ident,user['username'],'assurance:acknowledged',{'note':store.bounded(body.get('note',''),2000)})
    return {'acknowledged':True}

def retry(db,user,org,body):
    r=db.execute('SELECT * FROM pl_jobs WHERE organization_id=%s AND id=%s FOR UPDATE',(org,store.bounded(body.get('job_id',''),100))).fetchone()
    if not r or r['status']!='dead_letter' or r['kind'] not in {'integration:notify','schedule:notification_rule','schedule:report_schedule'}:store.fail('Choose a failed notification job',409)
    if body.get('confirmed') is not True:store.fail('Confirm retry; the provider may already have accepted the first attempt')
    if demo(db,org):store.fail('Demonstration organizations cannot send external notifications',403)
    db.execute("UPDATE pl_jobs SET status='queued',available_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE organization_id=%s AND id=%s",(org,r['id']))
    store.history(db,org,r['id'],user['username'],'assurance:retry',{'duplicate_delivery_risk_acknowledged':True});return {'queued':True}

def escalation_tick(db,user,org):
    from ..experience import notify
    for r in db.execute("SELECT * FROM pl_records WHERE organization_id=%s AND kind='as_delivery' AND status='active' AND deleted_at IS NULL",(org,)).fetchall():
        d=r['data']
        if not d.get('backup_owner') or not d.get('ack_due') or d['ack_due']>=today() or not member(db,org,d['backup_owner']):continue
        if db.execute("SELECT 1 FROM pl_history WHERE organization_id=%s AND record_id=%s AND action='assurance:acknowledged'",(org,d['job_id'])).fetchone():continue
        key='assurance:'+r['id']+':'+str(r['version'])+':'+today()
        if not db.execute('INSERT INTO pl_schedule_runs VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING job_id',(org,r['id'],key,store.uid())).fetchone():continue
        notify(db,org,d['backup_owner'],'Notification acknowledgment overdue: '+r['title'],'assurance',r['id'],key)
        store.history(db,org,r['id'],user,'assurance:escalated',{'job_id':d['job_id'],'assignee':d['backup_owner']})

def demo_reset(db,user,org,body):
    if not demo(db,org):store.fail('Only a marked synthetic demonstration organization can be reset',403)
    if body.get('confirmed') is not True:store.fail('Confirm resetting synthetic program records')
    rs=records(db,org);fingerprint=digest(rs)
    if body.get('confirmation_hash')!=fingerprint:return {'preview':len(rs),'confirmation_hash':fingerprint,'note':'Archives active synthetic program records. Preserves history and legacy demonstration registers.'}
    for r in rs:
        db.execute('UPDATE pl_records SET deleted_at=CURRENT_TIMESTAMP,version=version+1,updated_by=%s WHERE organization_id=%s AND id=%s',(user['username'],org,r['id']))
        db.execute("INSERT INTO pl_trash(organization_id,kind,record_id,deleted_by) VALUES (%s,'program',%s,%s) ON CONFLICT DO NOTHING",(org,r['id'],user['username']))
        store.history(db,org,r['id'],user['username'],'assurance:demo_reset',{'synthetic':True})
    return {'archived':len(rs)}
