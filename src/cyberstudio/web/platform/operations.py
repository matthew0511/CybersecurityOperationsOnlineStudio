"""Organization-scoped operational calculations and bounded automation.

No arbitrary expressions, remote commands, credential reads or outbound messaging.
"""
from datetime import date,datetime,timedelta,timezone
import json
from . import store
from fastapi import HTTPException
from .operations_catalog import CAPABILITIES

ACTIVE={'active','approved','completed'}

def instant(value):
    if not value:return None
    dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

def validate(db,org,kind,data):
    d=dict(data)
    if kind=='op_check':
        if not d.get('check_type'):store.fail('Choose a validation check')
        if d['check_type']=='integration_fresh':
            if not d.get('integration_id') or not d.get('max_age_hours'):store.fail('Choose an integration and positive maximum age')
            if not db.execute('SELECT 1 FROM pl_integrations WHERE organization_id=%s AND id=%s',(org,d['integration_id'])).fetchone():store.fail('Integration not found in this organization',404)
    if kind in {'op_evidence','op_campaign'} and not d.get('review_on'):store.fail('A review date is required')
    if kind=='op_access':
        if d.get('decision') in {'retain','revoke'} and not d.get('rationale'):store.fail('Explain the access decision')
        if d.get('last_seen'):
            days=(date.today()-date.fromisoformat(d['last_seen'])).days
            if days<0:store.fail('Last observed use cannot be in the future')
            d['calculated']={'inactive_days':days,'inactive_90_days':days>=90}
        if d.get('removed_at'):
            if instant(d['removed_at'])>datetime.now(timezone.utc):store.fail('Removal verification cannot be in the future')
            if d.get('decision')!='revoke':store.fail('Removal verification requires a revoke decision')
            verified(db,org,d)
    if kind=='op_vulnerability':
        if not d.get('exposure') or not d.get('criticality'):store.fail('Record exposure and business criticality')
        if d['cvss']>10:store.fail('CVSS must be between zero and ten')
        if d.get('retest')=='pass':verified(db,org,d)
        asset=store.get(db,org,d['asset_id'],'asset')
        score=min(100,round(d['cvss']*5+{'internal':0,'partner':8,'internet':15}.get(d.get('exposure'),0)+{'low':0,'moderate':5,'high':10,'critical':15}.get(d.get('criticality'),0)+(10 if d.get('exploited') else 0)+(5 if asset['data'].get('data_class')=='regulated' else 0),2))
        d['calculated']={'priority_score':score,'priority':'critical' if score>=80 else 'high' if score>=60 else 'moderate' if score>=35 else 'low','basis':'Studio planning score; CVSS, exposure and business context are operator supplied, not an exploit prediction.'}
    if kind=='op_change':
        if not all(d.get(k) for k in ('risk','test_plan','rollback')):store.fail('Document security impact, testing and rollback')
        if d.get('post_result')=='pass':verified(db,org,d)
    if kind=='op_change_result':
        change=store.get(db,org,d['change_id'],'op_change')
        if change['status'] not in {'approved','active','completed'}:store.fail('Approve the change before post-change verification')
        d['calculated']={'change_version':change['version']}
        if d.get('result')=='pass':verified(db,org,d)
    if kind=='op_processing' and d.get('disposal')=='verified':
        if d.get('legal_hold'):store.fail('Held data cannot be marked disposed')
        verified(db,org,d)
    if kind=='op_recovery':
        started,completed,point=(instant(d.get(k)) for k in ('started_at','completed_at','recovery_point_at'))
        if any(instant(d[k])>datetime.now(timezone.utc) for k in ('started_at','completed_at','recovery_point_at') if d.get(k)):store.fail('Observed recovery timestamps cannot be in the future')
        if completed and (not started or completed<started):store.fail('Completion must follow the exercise start')
        if point and (not started or point>started):store.fail('Recovered data timestamp must be at or before the exercise start')
        if d.get('result')=='pass':
            if not all((started,completed,point,d.get('checks'))):store.fail('A passing exercise needs measured timestamps and application checks')
            verified(db,org,d)
        if all((started,completed,point)):
            bia=store.get(db,org,d['bia_id'],'bia')['data'];rto=(completed-started).total_seconds()/3600;rpo=(started-point).total_seconds()/3600
            d['calculated']={'actual_recovery_hours':round(rto,4),'actual_data_loss_hours':round(rpo,4),'rto_met':rto<=bia['rto_hours'],'rpo_met':rpo<=bia['rpo_hours'],'bia_version':store.get(db,org,d['bia_id'])['version']}
    if kind=='op_workflow':
        if d.get('action')=='remediation' and not d.get('risk_id'):store.fail('Select the risk to receive remediation tasks')
        if not d.get('trigger') or not d.get('action'):store.fail('Choose an explicit trigger and action')
        if d.get('lead_days',0)>365:store.fail('Advance warning cannot exceed 365 days')
    if kind=='op_investment':
        if not 1<=d['years']<=30 or d.get('expected_reduction',0)>100:store.fail('Use a 1–30 year horizon and 0–100 percent assumption')
        if not d.get('assumptions'):store.fail('Document the scenario assumptions')
        d['calculated']={'total_cost':round(d.get('one_time_cost',0)+d.get('annual_cost',0)*d['years'],2),'basis':'Undiscounted planning cost; risk reduction is an assumption, not guaranteed savings.'}
    if kind=='op_crypto':
        if d.get('vendor_readiness')=='ready':verified(db,org,d)
        d['calculated']={'planning_horizon_years':d.get('data_lifetime_years',0)+d.get('migration_years',0),'basis':'Confidentiality lifetime plus migration duration; no quantum arrival date or algorithm certification is inferred.'}
    for field in ('reviewer','assignee','remediation_owner'):
        if d.get(field) and not db.execute("SELECT 1 FROM web_users WHERE username=%s AND enabled AND (role='owner' OR EXISTS(SELECT 1 FROM xp_memberships WHERE username=web_users.username AND organization_id=%s))",(d[field],org)).fetchone():store.fail('Choose an enabled organization member for '+field)
    return d

def verified(db,org,data):
    if not data.get('evidence_ids'):store.fail('Verified supporting evidence is required')
    store.require_verified_evidence(db,org,data['evidence_ids'])

def guard_save(db,user,org,kind,data):
    if kind=='op_access':
        campaign=store.get(db,org,data['campaign_id'],'op_campaign')
        if user['username']!=campaign['data']['reviewer']:store.fail('Only the campaign reviewer may record access decisions',403)
    if kind=='op_workflow' and user['role']!='owner':store.fail('Only the installation owner may configure automation',403)

def guard_transition(db,user,org,record,status):
    if record['kind']=='op_access':guard_save(db,user,org,record['kind'],record['data'])
    if status in {'completed','closed'} and record['kind']=='op_vulnerability':
        if record['data'].get('retest')!='pass':store.fail('A passing retest is required before closure')
        verified(db,org,record['data'])
    if status in {'completed','closed'} and record['kind']=='op_access':
        d=record['data']
        if d.get('decision') not in {'retain','revoke'}:store.fail('Record an access decision first')
        if d['decision']=='revoke':
            if not d.get('removed_at'):store.fail('Verify removal before completing this review')
            verified(db,org,d)
    if status in {'completed','closed'} and record['kind']=='op_campaign':
        rows=db.execute("SELECT status FROM pl_records WHERE organization_id=%s AND kind='op_access' AND data->>'campaign_id'=%s AND deleted_at IS NULL",(org,record['id'])).fetchall()
        if not rows or any(r['status']!='completed' for r in rows):store.fail('Complete every imported access review first')

def rows(db,org):
    return [dict(r) for r in db.execute('SELECT * FROM pl_records WHERE organization_id=%s AND deleted_at IS NULL ORDER BY updated_at DESC',(org,)).fetchall()]

def integration_health(db,org,now=None):
    now=now or datetime.now(timezone.utc);result=[]
    for r in db.execute('SELECT id,name,provider,enabled,connection_status,last_test_at,config FROM pl_integrations WHERE organization_id=%s ORDER BY name',(org,)).fetchall():
        job=db.execute("SELECT status,result,updated_at FROM pl_jobs WHERE organization_id=%s AND kind='integration:pull' AND payload->>'integration_id'=%s ORDER BY updated_at DESC LIMIT 1",(org,r['id'])).fetchone()
        success=db.execute("SELECT result,updated_at FROM pl_jobs WHERE organization_id=%s AND kind='integration:pull' AND status='succeeded' AND payload->>'integration_id'=%s ORDER BY updated_at DESC LIMIT 1",(org,r['id'])).fetchone()
        staged=db.execute('SELECT count(*) AS total,count(*) FILTER(WHERE promoted_id IS NOT NULL) AS promoted FROM pl_external WHERE organization_id=%s AND integration_id=%s',(org,r['id'])).fetchone()
        from .connectors import PROVIDERS
        result.append({'permission_requirements':PROVIDERS.get(r['provider'],{}).get('permission','Unknown provider'),'id':r['id'],'title':r['name'],'provider':r['provider'],'enabled':r['enabled'],'authentication':r['connection_status'],'last_test_at':r['last_test_at'],'last_success_at':success['updated_at'] if success else None,'age_hours':round((now-instant(success['updated_at'])).total_seconds()/3600,2) if success else None,'latest_job':job['status'] if job else 'never_run','partial':bool(success and success['result'].get('more_available')),'staged':staged['total'],'promoted':staged['promoted'],'permissions':'Configured credentials and provider consent; successful authentication alone does not establish all permissions.'})
    return result

def control_version(db,org,ident):
    try:return store.get(db,org,ident,'control')['version']
    except HTTPException as exc:
        if exc.status_code!=404:raise
        return None

def evaluate(db,org,check,health=None):
    d=check['data']
    if control_version(db,org,d['control_id']) is None:
        return {'check_id':check['id'],'check_version':check['version'],'control_version':None,'outcome':'unknown','reason':'The source control is archived or unavailable','source_ids':[],'observed_at':datetime.now(timezone.utc).isoformat()}
    control=store.get(db,org,d['control_id'],'control');outcome='unknown';reason='No current evidence or completed source test';source=[]
    if d['check_type']=='evidence_current':
        from ..database import service
        evidence={r['id']:r for r in service(db).evidence(org)};ids=control['data'].get('evidence_ids',[])
        if ids:
            outcome='pass' if all(i in evidence and evidence[i].get('effective_status')=='verified' for i in ids) else 'fail';reason='Linked evidence reviewed for current verified state';source=ids
    elif d['check_type']=='integration_fresh':
        connection=next((r for r in (health if health is not None else integration_health(db,org)) if r['id']==d['integration_id']),None)
        if connection and connection['age_hours'] is not None:
            outcome='pass' if connection['enabled'] and connection['authentication']=='authenticated' and connection['age_hours']<=d['max_age_hours'] and connection['latest_job']=='succeeded' and not connection['partial'] else 'fail';reason='Latest pull, freshness and bounded-source coverage evaluated';source=[connection['id']]
    else:
        result=db.execute("SELECT r.id,r.data FROM pl_records r JOIN pl_records p ON p.id=r.data->>'plan_id' AND p.organization_id=r.organization_id WHERE r.organization_id=%s AND r.kind='control_test' AND p.data->>'control_id'=%s AND r.status IN ('completed','active') AND r.deleted_at IS NULL AND p.deleted_at IS NULL ORDER BY r.updated_at DESC LIMIT 1",(org,control['id'])).fetchone()
        if result:
            source=[result['id']];outcome={'pass':'pass','fail':'fail','partial':'fail'}.get(result['data'].get('result'),'unknown');reason='Latest completed control test with current supporting evidence'
            if outcome=='pass':
                try:verified(db,org,result['data'])
                except Exception as exc:
                    from fastapi import HTTPException
                    if not isinstance(exc,HTTPException):raise
                    outcome='fail';reason='Supporting evidence is no longer currently verified'
            if result['data'].get('next_test','9999-12-31')<date.today().isoformat():outcome='fail';reason='Control retest is overdue'
    return {'check_id':check['id'],'check_version':check['version'],'control_version':control['version'],'outcome':outcome,'reason':reason,'source_ids':source,'observed_at':datetime.now(timezone.utc).isoformat()}

def run_check(db,user,org,check):
    result=evaluate(db,org,check);store.history(db,org,check['id'],user['username'],'operations:validation',result)
    return result

def latest_results(db,org):
    return [dict(r['snapshot']) for r in db.execute("SELECT DISTINCT ON(record_id) snapshot FROM pl_history WHERE organization_id=%s AND action='operations:validation' ORDER BY record_id,id DESC",(org,)).fetchall()]

def summary(db,user,org):
    records=rows(db,org);today=date.today().isoformat();counts={}
    for r in records:counts[r['kind']]=counts.get(r['kind'],0)+1
    exceptions=[{'id':r['id'],'title':r['title'],'owner':r['owner'],'expires_on':r['data'].get('expires_on'),'effective_status':'expired' if r['data'].get('expires_on','9999')<today else r['status']} for r in records if r['kind']=='exception']
    evidence_due=[{'id':r['id'],'title':r['title'],'owner':r['owner'],'review_on':r['data'].get('review_on'),'expired':bool(r['data'].get('expires_on') and r['data']['expires_on']<today)} for r in records if r['kind']=='op_evidence' and (r['data'].get('review_on','9999')<=today or r['data'].get('expires_on','9999')<=today)]
    scenarios={}
    for r in records:
        if r['kind']=='op_investment':
            name=r['data']['scenario'];entry=scenarios.setdefault(name,{'scenario':name,'total_cost':0,'proposals':0});entry['total_cost']+=r['data'].get('calculated',{}).get('total_cost',0);entry['proposals']+=1
    checks=[]
    previous={r['check_id']:r for r in latest_results(db,org)}
    for r in records:
        if r['kind']!='op_check':continue
        last=previous.get(r['id']);stale=not last or last['check_version']!=r['version'] or last.get('control_version')!=control_version(db,org,r['data']['control_id']) or (datetime.now(timezone.utc)-instant(last['observed_at'])).total_seconds()>r['data']['frequency_days']*86400
        checks.append({'id':r['id'],'title':r['title'],'owner':r['owner'],'outcome':'unknown' if stale else last['outcome'],'reason':'Never run or configuration / interval changed' if stale else last['reason'],'observed_at':last['observed_at'] if last else None})
    campaigns=[]
    for campaign in (r for r in records if r['kind']=='op_campaign'):
        accounts=[r for r in records if r['kind']=='op_access' and r['data']['campaign_id']==campaign['id']]
        campaigns.append({'id':campaign['id'],'title':campaign['title'],'total':len(accounts),'completed':sum(r['status']=='completed' for r in accounts),'privileged':sum(r['data'].get('privileged') is True for r in accounts),'inactive':sum(bool(r['data'].get('last_seen')) and (date.today()-date.fromisoformat(r['data']['last_seen'])).days>=90 for r in accounts),'review_on':campaign['data']['review_on']})
    return {'campaigns':campaigns,'capabilities':[{'number':i,'title':t,'module':k} for i,(t,k) in enumerate(CAPABILITIES,1)],'counts':counts,'checks':checks,'evidence_due':evidence_due,'exceptions':exceptions,'scenarios':list(scenarios.values()),'integrations':integration_health(db,org) if user['role']=='owner' else [],'automation_runs':[dict(r) for r in db.execute("SELECT actor,action,snapshot,recorded_at FROM pl_history WHERE organization_id=%s AND action='operations:workflow' ORDER BY id DESC LIMIT 100",(org,)).fetchall()],'note':'Current organization snapshot. Unknown, overdue and expired states never count as passing validation.'}

def impact(db,org,ident):
    records=rows(db,org);assets={r['id']:r for r in records if r['kind']=='asset'}
    if ident not in assets:store.fail('Asset not found',404)
    reverse={}
    for r in assets.values():
        for dependency in r['data'].get('dependencies',[]):reverse.setdefault(dependency,[]).append(r['id'])
    seen=set();pending=[ident]
    while pending:
        item=pending.pop()
        if item in seen:continue
        seen.add(item);pending.extend(reverse.get(item,[]))
    return {'affected_assets':[{'id':k,'title':assets[k]['title'],'type':assets[k]['data'].get('asset_type')} for k in sorted(seen)],'relationships':[r for r in records if r['kind']=='op_link' and r['data']['asset_id'] in seen],'note':'Transitive recorded dependents only; missing inventory relationships are not inferred.'}

def action(db,user,org,ident,body):
    r=store.get(db,org,ident,lock=True)
    if body.get('version')!=r['version']:store.fail('Record changed; reload before running this action',409)
    if r['kind']=='op_check':return run_check(db,user,org,r)
    if r['kind']=='op_acquisition':
        if db.execute("SELECT 1 FROM pl_records WHERE organization_id=%s AND kind='op_milestone' AND data->>'acquisition_id'=%s AND deleted_at IS NULL",(org,ident)).fetchone():store.fail('Milestones already exist for this acquisition',409)
        close=date.fromisoformat(r['data']['close_on']) if r['data'].get('close_on') else None
        items=[]
        for phase,days,instructions in [('due_diligence',-14,'Reconcile office assets, inherited privileged access, vendor contracts, backups and security gaps.'),('day_1',0,'Verify support ownership, emergency access, MFA, endpoint coverage and recoverable backups.'),('day_30',30,'Review inherited access and vendors; reconcile assets and document segmentation dependencies.'),('day_60',60,'Complete priority remediation, standardize monitoring and validate recovery dependencies.'),('day_90',90,'Verify integration acceptance, residual exceptions, evidence and steady-state service ownership.')]:
            items.append(store.save(db,user,org,'op_milestone',{'title':r['title']+' / '+phase,'owner':r['owner'],'due_on':(close+timedelta(days=days)).isoformat() if close else None,'data':{'acquisition_id':ident,'phase':phase,'checklist':instructions}})['id'])
        store.history(db,org,ident,user['username'],'operations:acquisition_template',{'milestones':items});return {'created':len(items),'ids':items}
    if r['kind']=='op_campaign':
        accounts=body.get('accounts')
        if not isinstance(accounts,list) or not 1<=len(accounts)<=1000:store.fail('Import 1–1000 accounts')
        if user['username']!=r['data']['reviewer']:store.fail('Only the campaign reviewer may import the inventory',403)
        existing={(x['data']['account'],x['data']['system']) for x in rows(db,org) if x['kind']=='op_access' and x['data']['campaign_id']==ident};created=[]
        for entry in accounts:
            if not isinstance(entry,dict) or set(entry)-{'account','system','privileged','last_seen'}:store.fail('Use account, system, privileged and last_seen fields')
            key=(store.bounded(entry.get('account',''),500),store.bounded(entry.get('system',''),500))
            if key in existing:continue
            existing.add(key);created.append(store.save(db,user,org,'op_access',{'title':key[0]+' / '+key[1],'owner':r['data']['reviewer'],'due_on':r['data']['review_on'],'data':{**entry,'campaign_id':ident,'decision':'pending'}})['id'])
        store.history(db,org,ident,user['username'],'operations:access_import',{'created':len(created)});return {'created':len(created),'ids':created}
    store.fail('This record has no operations action',422)

def tick(db,org,username):
    """Called under the existing worker transaction/advisory lock. Internal actions only."""
    user={'username':username,'role':'owner'};records=rows(db,org);today=date.today();bucket=today.isoformat()
    for check in records:
        if check['kind']!='op_check' or check['status']!='active':continue
        last=db.execute("SELECT snapshot FROM pl_history WHERE organization_id=%s AND record_id=%s AND action='operations:validation' ORDER BY id DESC LIMIT 1",(org,check['id'])).fetchone()
        if not last or last['snapshot']['check_version']!=check['version'] or (datetime.now(timezone.utc)-instant(last['snapshot']['observed_at'])).total_seconds()>=check['data']['frequency_days']*86400:run_check(db,user,org,check)
    for rule in records:
        if rule['kind']!='op_workflow' or rule['status']!='active':continue
        d=rule['data']
        for member in (rule['created_by'],d['assignee']):
            if not db.execute("SELECT 1 FROM web_users WHERE username=%s AND enabled AND (role='owner' OR EXISTS(SELECT 1 FROM xp_memberships WHERE username=web_users.username AND organization_id=%s))",(member,org)).fetchone():break
        else:member=None
        if member is not None:continue
        deadline=(today+timedelta(days=d.get('lead_days',0))).isoformat();targets=[]
        for r in records:
            if r['status'] in {'closed','completed','rejected'}:continue
            if d['trigger']=='evidence_due' and r['kind']=='op_evidence' and min(r['data'].get('review_on','9999'),r['data'].get('expires_on','9999'))<=deadline:targets.append(r)
            if d['trigger']=='exception_expired' and r['kind']=='exception' and r['status'] in {'approved','active'} and r['data']['expires_on']<bucket:targets.append(r)
            if d['trigger']=='review_due' and r['kind']=='op_campaign' and r['data']['review_on']<=deadline:targets.append(r)
        if d['trigger']=='checks_fail':
            results={x['check_id']:x for x in latest_results(db,org)}
            targets=[r for r in records if r['kind']=='op_check' and r['status']=='active' and r['id'] in results and results[r['id']]['outcome']=='fail' and results[r['id']]['check_version']==r['version']]
        claimed_count=0
        for target in targets:
            if claimed_count>=200:break
            marker=f"{rule['version']}:{target['id']}:{bucket}";run=store.uid()
            claimed=db.execute('INSERT INTO pl_schedule_runs VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING job_id',(org,rule['id'],marker,run)).fetchone()
            if not claimed:continue
            claimed_count+=1
            title=(rule['title']+': '+target['title'])[:250]
            if d['action']=='in_app':
                from ..experience import notify
                notify(db,org,d['assignee'],title,'operations',target['id'],run)
            else:
                from ..database import service
                service(db).add_task(org,d['risk_id'],title,owner=d['assignee'],due_date=bucket)
            store.history(db,org,rule['id'],username,'operations:workflow',{'target_id':target['id'],'rule_version':rule['version'],'action':d['action'],'assignee':d['assignee'],'run_id':run,'instructions':d.get('instructions','')})
