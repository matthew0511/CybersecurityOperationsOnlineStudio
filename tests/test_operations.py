"""Stateful acceptance for the fifteen operational enhancements and authorization boundaries."""
from datetime import date,datetime,timedelta,timezone
import pytest
from test_web import web,login,call,PW
from test_experience import invited
from test_platform import post,save
from test_ai_governance import packet,status,completed
from cyberstudio.web.database import connect,service
from cyberstudio.web.platform import operations,catalog
from cyberstudio.web.platform.schema import actor

FUTURE=(date.today()+timedelta(days=60)).isoformat()

def setup(web):
    login(web);return call(web,'create_organization',name='Synthetic operations'),call(web,'create_organization',name='Other tenant')

def run(web,org,record,**body):return post(web,org,'/operations/'+record['id']+'/run',{'version':record['version'],**body})

def overview(web,org):
    r=web.get(f'/api/platform/{org}/operations/overview');assert r.status_code==200,r.text;return r.json()

def test_operations_contract():
    assert len(operations.CAPABILITIES)==15
    assert all(k is None or k in catalog.MODULES for _,k in operations.CAPABILITIES)
    assert catalog.modules()['op_workflow']['approval']

def test_checks_unknown_evidence_revocation_and_scope(web):
    org,other=setup(web);eid=packet(web,org)
    control=save(web,org,'control','Control',{'evidence_ids':[eid]})
    check=save(web,org,'op_check','Current artifacts',{'control_id':control['id'],'check_type':'evidence_current','frequency_days':1})
    assert overview(web,org)['checks'][0]['outcome']=='unknown'
    assert run(web,org,check)['outcome']=='pass'
    assert overview(web,org)['checks'][0]['outcome']=='pass'
    with connect() as db:actor(db,'owner',org);service(db).review_evidence(org,eid,'rejected','owner','No longer supports scope')
    assert run(web,org,check)['outcome']=='fail'
    post(web,other,'/records/op_check',{'title':'Cross tenant','data':{'control_id':control['id'],'check_type':'evidence_current','frequency_days':1}},404)
    viewer=invited(web,org,'viewer','viewer');post(viewer,org,'/operations/'+check['id']+'/run',{'version':1},403)
    assert len(overview(web,org)['capabilities'])==15

def test_check_source_version_invalidates_result(web):
    org,_=setup(web);control=save(web,org,'control');check=save(web,org,'op_check',data={'control_id':control['id'],'check_type':'evidence_current','frequency_days':1})
    assert run(web,org,check)['outcome']=='unknown'
    save(web,org,'control','Changed baseline',id=control['id'],version=1)
    assert overview(web,org)['checks'][0]['outcome']=='unknown'

def test_access_campaign_import_decisions_and_completion(web):
    org,_=setup(web);reviewer=invited(web,org,'reviewer','reviewer')
    campaign=save(web,org,'op_campaign',data={'reviewer':'reviewer','review_on':FUTURE})
    post(web,org,'/operations/'+campaign['id']+'/run',{'version':1,'accounts':[{'account':'a','system':'test'}]},403)
    result=run(reviewer,org,campaign,accounts=[{'account':'a','system':'test','privileged':True}]);assert result['created']==1
    assert run(reviewer,org,campaign,accounts=[{'account':'a','system':'test'}])['created']==0
    ident=result['ids'][0];data={'campaign_id':campaign['id'],'account':'a','system':'test','decision':'revoke','rationale':'No longer required'}
    post(web,org,'/records/op_access',{'id':ident,'version':1,'title':'Review','data':data},403)
    review=save(reviewer,org,'op_access','Review',data,id=ident,version=1)
    post(reviewer,org,'/record/'+ident+'/status',{'version':2,'status':'closed'},422)
    eid=packet(web,org);review=save(reviewer,org,'op_access','Verified removal',{**data,'removed_at':datetime.now(timezone.utc).isoformat(),'evidence_ids':[eid]},id=ident,version=2)
    completed(reviewer,org,review);assert completed(web,org,campaign)['status']=='completed'

def test_dependency_impact_and_pqc_cycles(web):
    org,_=setup(web);a=save(web,org,'asset','Database');b=save(web,org,'asset','Clinical service',{'dependencies':[a['id']],'asset_type':'business_service'})
    risk=call(web,'add_risk',org=org,title='Service risk',description='',likelihood=3,impact=4,rationale='Synthetic planning risk')
    save(web,org,'op_link',data={'asset_id':b['id'],'risk_id':risk,'impact':'Clinical scheduling dependency'})
    impact=web.get(f'/api/platform/{org}/operations/impact/'+a['id']).json();assert len(impact['affected_assets'])==2 and len(impact['relationships'])==1
    crypto=save(web,org,'op_crypto','TLS',{'asset_id':a['id'],'algorithm':'RSA','data_lifetime_years':10,'migration_years':3})
    assert crypto['data']['calculated']['planning_horizon_years']==13
    post(web,org,'/records/op_crypto',{'id':crypto['id'],'version':1,'title':'Cycle','data':{**crypto['data'],'dependencies':[crypto['id']]}},422)

def test_vulnerability_retest_and_business_score(web):
    org,_=setup(web);asset=save(web,org,'asset',data={'data_class':'regulated'})
    data={'asset_id':asset['id'],'cvss':9,'exposure':'internet','criticality':'critical','exploited':True}
    vuln=save(web,org,'op_vulnerability',data=data);assert vuln['data']['calculated']['priority_score']==90
    post(web,org,'/record/'+vuln['id']+'/status',{'version':1,'status':'closed'},422)
    post(web,org,'/records/op_vulnerability',{'title':'False pass','data':{**data,'retest':'pass'}},422)
    eid=packet(web,org);vuln=save(web,org,'op_vulnerability','Retested',{**data,'retest':'pass','evidence_ids':[eid]},id=vuln['id'],version=1)
    assert completed(web,org,vuln)['status']=='completed'

def test_data_hold_evidence_schedule_and_investment(web):
    org,_=setup(web);asset=save(web,org,'asset');eid=packet(web,org)
    post(web,org,'/records/op_processing',{'title':'Held disposal','data':{'asset_id':asset['id'],'legal_hold':True,'disposal':'verified','evidence_ids':[eid]}},422)
    save(web,org,'op_evidence','Overdue review',{'evidence_id':eid,'review_on':date.today().isoformat()})
    record=save(web,org,'op_investment',data={'scenario':'Baseline','years':3,'one_time_cost':100,'annual_cost':50,'expected_reduction':20,'assumptions':'Synthetic inputs'})
    assert record['data']['calculated']['total_cost']==250
    state=overview(web,org);assert len(state['evidence_due'])==1 and state['scenarios'][0]['total_cost']==250
    result=post(web,org,'/editions',{'template':'operations','format':'xlsx'});assert result['bytes']>100

def test_acquisition_templates_are_dated_and_idempotent(web):
    org,_=setup(web);acq=save(web,org,'op_acquisition','Synthetic acquisition',{'close_on':date.today().isoformat()})
    assert run(web,org,acq)['created']==5
    post(web,org,'/operations/'+acq['id']+'/run',{'version':1},409)
    records=web.get(f'/api/platform/{org}/records/op_milestone').json();assert {r['data']['phase'] for r in records}=={'due_diligence','day_1','day_30','day_60','day_90'}

def test_measured_recovery_objectives_and_evidence(web):
    org,_=setup(web);asset=save(web,org,'asset');bia=save(web,org,'bia',data={'asset_id':asset['id'],'rto_hours':1,'rpo_hours':1});eid=packet(web,org)
    now=datetime.now(timezone.utc);data={'bia_id':bia['id'],'started_at':(now-timedelta(hours=4)).isoformat(),'completed_at':now.isoformat(),'recovery_point_at':(now-timedelta(hours=6)).isoformat(),'result':'pass','checks':'Application login and dependency checks','evidence_ids':[eid]}
    result=save(web,org,'op_recovery',data=data)['data']['calculated'];assert result['actual_recovery_hours']==4 and not result['rto_met'] and not result['rpo_met']
    post(web,org,'/records/op_recovery',{'title':'Impossible timestamp','data':{**data,'completed_at':(now-timedelta(hours=8)).isoformat()}},422)

def test_change_independent_approval_and_post_validation(web):
    org,_=setup(web);reviewer=invited(web,org,'reviewer','reviewer')
    change=save(web,org,'op_change',data={'risk':'Access change','test_plan':'Test roles','rollback':'Restore prior role','approver':'reviewer'})
    post(web,org,'/records/op_change_result',{'title':'Before approval','data':{'change_id':change['id'],'result':'fail'}},422)
    change=status(web,org,change,'submitted');status(web,org,change,'approved',403,password=PW)
    change=status(reviewer,org,change,'approved',password=PW);eid=packet(web,org)
    result=save(web,org,'op_change_result',data={'change_id':change['id'],'result':'pass','observations':'Roles checked','evidence_ids':[eid]})
    assert result['data']['calculated']['change_version']==change['version']

def test_workflow_approval_execution_and_deduplication(web):
    org,_=setup(web);reviewer=invited(web,org,'reviewer','reviewer');eid=packet(web,org)
    save(web,org,'op_evidence',data={'evidence_id':eid,'review_on':date.today().isoformat()})
    risk=call(web,'add_risk',org=org,title='Evidence risk',description='',likelihood=2,impact=2,rationale='Synthetic planning risk')
    rule=save(web,org,'op_workflow','Evidence escalation',{'trigger':'evidence_due','action':'remediation','risk_id':risk,'assignee':'owner','approver':'reviewer'})
    with connect() as db:actor(db,'owner',org);operations.tick(db,org,'owner')
    assert len(call(web,'list_tasks',org=org))==0
    rule=status(web,org,rule,'submitted');rule=status(reviewer,org,rule,'approved',password=PW);rule=status(web,org,rule,'active')
    with connect() as db,db.transaction():actor(db,'owner',org);operations.tick(db,org,'owner');operations.tick(db,org,'owner')
    assert len(call(web,'list_tasks',org=org))==1
    assert len(overview(web,org)['automation_runs'])==1

def test_integration_health_no_secrets_and_missing_data_unknown(web):
    org,_=setup(web)
    with connect() as db:
        actor(db,'owner',org)
        db.execute("INSERT INTO pl_integrations(id,organization_id,provider,name,secret_cipher,created_by) VALUES ('connection',%s,'intune','Synthetic connection','never-return-this','owner')",(org,))
    state=overview(web,org);assert state['integrations'][0]['age_hours'] is None
    assert 'never-return-this' not in str(state)
    control=save(web,org,'control');check=save(web,org,'op_check',data={'control_id':control['id'],'check_type':'integration_fresh','integration_id':'connection','max_age_hours':24,'frequency_days':1})
    assert run(web,org,check)['outcome']=='unknown'

def test_operations_malformed_and_sql_literal_fields(web):
    org,_=setup(web);asset=save(web,org,'asset')
    for field,value in [('algorithm',{}),('key_bits',True),('dependencies',[{}]),('certificate_expires','not-a-date'),('vendor_readiness',[]),('data_lifetime_years',-1)]:
        post(web,org,'/records/op_crypto',{'title':'Invalid','data':{'asset_id':asset['id'],'algorithm':'RSA',field:value}},422)
    record=save(web,org,'op_crypto',"'; DROP TABLE pl_records; --",{'asset_id':asset['id'],'algorithm':"RSA'; SELECT 1 --"})
    assert record['title']=="'; DROP TABLE pl_records; --"


def test_portal_review_gate_questions_and_download_audit(web):
    from fastapi.testclient import TestClient
    from cyberstudio.web.app import app
    org,_=setup(web);draft=save(web,org,'op_acquisition','Draft')
    post(web,org,'/rooms',{'approved_only':True,'allowed':[{'kind':'program','id':draft['id']}]},422)
    eid=packet(web,org);room=post(web,org,'/rooms',{'approved_only':True,'allowed':[{'kind':'evidence','id':eid}]})
    external=TestClient(app,base_url='https://testserver');assert external.post('/api/audit-room/redeem',json={'token':room['token']}).status_code==200
    assert external.get('/api/audit-room/download/evidence/'+eid).status_code==200
    activity=web.get(f'/api/platform/{org}/rooms/'+room['id']+'/activity').json();assert activity['downloads'][0]['snapshot']['id']==eid
    viewer=invited(web,org,'viewer','viewer');assert viewer.get(f'/api/platform/{org}/rooms/'+room['id']+'/activity').status_code==403


def test_integration_freshness_partial_coverage_and_failed_pull(web):
    import json
    org,_=setup(web)
    with connect() as db:
        actor(db,'owner',org)
        db.execute("INSERT INTO pl_integrations(id,organization_id,provider,name,secret_cipher,created_by,enabled,connection_status) VALUES ('fresh',%s,'intune','Synthetic','secret','owner',TRUE,'authenticated')",(org,))
        db.execute("INSERT INTO pl_jobs(id,organization_id,kind,payload,status,result) VALUES ('job',%s,'integration:pull',%s::jsonb,'succeeded',%s::jsonb)",(org,json.dumps({'integration_id':'fresh'}),json.dumps({'more_available':True})))
    control=save(web,org,'control');check=save(web,org,'op_check',data={'control_id':control['id'],'check_type':'integration_fresh','integration_id':'fresh','max_age_hours':24,'frequency_days':1})
    assert run(web,org,check)['outcome']=='fail'
    with connect() as db:actor(db,'owner',org);db.execute("UPDATE pl_jobs SET result='{}' WHERE id='job'")
    assert run(web,org,check)['outcome']=='pass'
    with connect() as db:actor(db,'owner',org);db.execute("INSERT INTO pl_jobs(id,organization_id,kind,payload,status) VALUES ('failed',%s,'integration:pull',%s::jsonb,'dead_letter')",(org,json.dumps({'integration_id':'fresh'})))
    assert run(web,org,check)['outcome']=='fail'


def test_archived_validation_source_is_unknown(web):
    org,_=setup(web);control=save(web,org,'control');check=save(web,org,'op_check',data={'control_id':control['id'],'check_type':'evidence_current','frequency_days':1})
    post(web,org,'/record/'+control['id']+'/archive',{})
    assert run(web,org,check)['outcome']=='unknown'
    assert overview(web,org)['checks'][0]['outcome']=='unknown'
