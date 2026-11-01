"""Acceptance of assurance calculations, conflict handling and tenant boundaries."""
from datetime import date,timedelta
import copy
from test_web import web,login,call
from test_platform import post,save
from test_experience import invited
from test_ai_governance import packet
from cyberstudio.web.platform import assurance,catalog

SHA='a'*40

def setup(web):
    login(web);return call(web,'create_organization',name='Synthetic assurance'),call(web,'create_organization',name='Unrelated tenant')
def action(web,org,name,body=None,status=200):return post(web,org,'/assurance/'+name,body or {},status)
def state(web,org):
    r=web.get('/api/platform/'+org+'/assurance/overview');assert r.status_code==200,r.text;return r.json()

def test_assurance_contract():
    assert len(assurance.FEATURES)==15
    assert all(k in catalog.MODULES for k in ['as_detection','as_release','as_view','as_metric'])

def test_empty_coverage_is_unknown_and_tenant_isolation(web):
    org,other=setup(web);r=state(web,org);assert r['control_coverage']['verified_percent'] is None
    a=save(web,org,'asset','Protected service');c=save(web,org,'control','Unassessed control')
    r=state(web,org);assert r['service_coverage']['denominator']==6
    assert r['control_coverage']['counts']['unknown']==1
    assert not state(web,other)['service_coverage']['rows']
    post(web,other,'/records/as_coverage',{'title':'Cross scope','data':{'asset_id':a['id'],'service':'backup','result':'unknown','valid_days':7,'observed_on':date.today().isoformat()}},404)

def test_service_coverage_stale_and_evidence_revocation(web):
    org,_=setup(web);asset=save(web,org,'asset');eid=packet(web,org)
    data={'asset_id':asset['id'],'service':'endpoint','result':'pass','valid_days':7,'observed_on':date.today().isoformat(),'evidence_ids':[eid]}
    r=save(web,org,'as_coverage',data=data);s=state(web,org)['service_coverage'];assert s['counts']['pass']==1 and s['denominator']==6
    save(web,org,'as_coverage',data={**data,'observed_on':(date.today()-timedelta(days=9)).isoformat()},id=r['id'],version=1)
    assert state(web,org)['service_coverage']['counts']['stale']==1
    post(web,org,'/records/as_coverage',{'title':'Unproven','data':{**data,'evidence_ids':[]}},422)

def test_release_and_evidence_reuse_gates(web):
    org,_=setup(web);asset=save(web,org,'asset');control=save(web,org,'control');eid=packet(web,org)
    save(web,org,'as_release',data={'source_sha':SHA,'deployed_sha':SHA,'validation':'pass','migration':'not_required','defects':0,'rollback':'Deploy prior image','acceptance':'Synthetic verification','observed_on':date.today().isoformat(),'evidence_ids':[eid]})
    assert state(web,org)['releases'][0]['ready']
    data={'control_id':control['id'],'asset_id':asset['id'],'evidence_id':eid,'period_start':date.today().isoformat(),'period_end':(date.today()+timedelta(days=7)).isoformat(),'scope':'Named asset and assessment period','review_on':date.today().isoformat()}
    save(web,org,'as_reuse',data=data);assert state(web,org)['evidence_reuse'][0]['eligible']
    post(web,org,'/records/as_reuse',{'title':'Wrong interval','data':{**data,'period_start':'2099-01-01'}},422)
    post(web,org,'/records/as_release',{'title':'Bad source','data':{'source_sha':"'; DROP TABLE pl_records;--",'defects':0}},422)

def test_search_saved_filters_and_literal_sql(web):
    org,other=setup(web);title="Literal '; DROP TABLE pl_records;--";save(web,org,'control',title,owner='owner')
    view=save(web,org,'as_view',data={'module':'control','query':'DROP TABLE','status_filter':'draft','owner_filter':'owner','sort_by':'title','direction':'ascending'})
    assert len(action(web,org,'search',{'view_id':view['id']})['rows'])==1
    action(web,other,'search',{'view_id':view['id']},404)
    for body in [{'module':'control','sort_by':'id;delete'},{'module':'control','offset':True},{'module':'nope'}]:action(web,org,'search',body,422)

def test_bulk_preview_version_conflict_and_atomic_rollback(web):
    org,other=setup(web);a=save(web,org,'control','A');b=save(web,org,'control','B');ids=[a['id'],b['id']];body={'ids':ids,'changes':{'owner':'owner','due_on':'2099-01-01'}}
    p=action(web,org,'bulk',body);save(web,org,'control','Changed',id=a['id'],version=1)
    action(web,org,'bulk',{**body,'confirmed':True,'confirmation_hash':p['confirmation_hash']},409)
    p=action(web,org,'bulk',body);assert action(web,org,'bulk',{**body,'confirmed':True,'confirmation_hash':p['confirmation_hash']})['updated']==2
    p=action(web,org,'bulk',{'ids':[a['id']],'changes':{'due_on':'bad'}} ,422)
    action(web,other,'bulk',body,404)
    viewer=invited(web,org,'viewer','viewer');action(viewer,org,'bulk',body,403)

def test_metrics_denominators_and_my_work(web):
    org,_=setup(web);save(web,org,'control','Assigned',owner='owner',due_on='2020-01-01')
    save(web,org,'as_metric','Completion',{'module':'control','measure':'completed_percent','target':90,'direction':'at_least'})
    s=state(web,org);assert s['metrics'][0]['value']==0 and s['metrics'][0]['denominator']==1
    assert any(r['title']=='Assigned' and r['overdue'] for r in s['my_work'])
    assert s['quality']
    report=post(web,org,'/editions',{'template':'assurance','format':'xlsx'});assert report['bytes']>100

def test_catalog_compare_migrate_preserves_history(web):
    org,_=setup(web)
    def imp(edition,raw):
        r=web.post('/api/platform/'+org+'/catalogs',data={'name':'Synthetic framework','edition':edition,'source':'Synthetic','license_note':'Owner-authored','confirmed':'true'},files={'file':('controls.csv',raw,'text/csv')});assert r.status_code==200,r.text;return r.json()['id']
    a=imp('1',b'code,title\nA,First\n');b=imp('2',b'code,title\nA,First\nB,Second\n')
    c=save(web,org,'control',data={'catalog_mappings':[{'catalog_id':a,'code':'A'}]});body={'before':a,'after':b};p=action(web,org,'catalog-preview',body);assert len(p['added'])==1
    assert action(web,org,'catalog-migrate',{**body,'confirmed':True,'confirmation_hash':p['confirmation_hash']})['updated']==1
    d=web.get('/api/platform/'+org+'/record/'+c['id']).json();assert d['record']['data']['catalog_mappings'][0]['catalog_id']==b
    assert any(h['action']=='assurance:catalog_migrated' for h in d['history'])
    changed=imp('3',b'code,title\nA,Changed\n');body={'before':b,'after':changed};p=action(web,org,'catalog-preview',body)
    action(web,org,'catalog-migrate',{**body,'confirmed':True,'confirmation_hash':p['confirmation_hash']},409)

def test_package_hash_scope_conflicts_and_recovery(web):
    org,other=setup(web);r=save(web,org,'control','Recover me');packet(web,org)
    package=action(web,org,'export');p=action(web,org,'recovery-preview',{'package':package});assert p['evidence_integrity_verified']==1
    action(web,other,'recovery-preview',{'package':package},422)
    tampered=copy.deepcopy(package);tampered['payload']['program_owner']='Fake';action(web,org,'recovery-preview',{'package':tampered},422)
    action(web,org,'recover',{'package':package,'confirmed':True,'confirmation_hash':p['confirmation_hash']})
    post(web,org,'/record/'+r['id']+'/archive',{})
    p=action(web,org,'recovery-preview',{'package':package});assert p['records'][0]['state']=='recoverable_archived'
    result=action(web,org,'recover',{'package':package,'confirmed':True,'confirmation_hash':p['confirmation_hash']});assert result['recovered']==1
    recovered=web.get('/api/platform/'+org+'/record/'+r['id']).json()['record'];assert recovered['status']=='draft'
    editor=invited(web,org,'editor','editor');action(editor,org,'export',{},403)

def test_demo_reset_cannot_touch_normal_workspace(web):
    org,_=setup(web);action(web,org,'demo-reset',{'confirmed':True},403)
    response=web.post('/api/platform/demo',json={'confirmed':True});assert response.status_code==200;d=response.json()['organization_id']
    p=action(web,d,'demo-reset',{'confirmed':True});assert p['preview']>0
    assert action(web,d,'demo-reset',{'confirmed':True,'confirmation_hash':p['confirmation_hash']})['archived']>0

def test_notification_escalation_deduplication_and_ack(web):
    import json
    from cyberstudio.web.database import connect
    from cyberstudio.web.platform.schema import actor
    org,_=setup(web)
    with connect() as db:
        actor(db,'owner',org);db.execute("INSERT INTO pl_jobs(id,organization_id,kind,payload,status) VALUES ('synthetic-job',%s,'integration:notify','{}','dead_letter')",(org,))
    r=save(web,org,'as_delivery','Follow up',{'job_id':'synthetic-job','backup_owner':'owner','ack_due':'2020-01-01'})
    post(web,org,'/record/'+r['id']+'/status',{'version':1,'status':'active'})
    with connect() as db,db.transaction():
        actor(db,'owner',org);assurance.escalation_tick(db,'owner',org);assurance.escalation_tick(db,'owner',org)
        assert db.execute("SELECT count(*) AS n FROM pl_history WHERE organization_id=%s AND action='assurance:escalated'",(org,)).fetchone()['n']==1
    action(web,org,'acknowledge',{'job_id':'synthetic-job','note':'Reviewed failure'});assert state(web,org)['deliveries'][0]['acknowledged']
    action(web,org,'retry',{'job_id':'synthetic-job'},422)
    action(web,org,'retry',{'job_id':'synthetic-job','confirmed':True});assert state(web,org)['deliveries'][0]['delivery_state']=='queued'

def test_malformed_packages_and_invalid_bulk_inputs_fail_closed(web):
    org,_=setup(web)
    for payload in [None,[],{}, {'format':'studio-workbench-v1','organization_id':org,'records':[None],'evidence':[]}, {'format':'studio-workbench-v1','organization_id':org,'records':[],'evidence':[False],'scope':'Synthetic'}]:
        package={'payload':payload,'sha256':assurance.digest(payload)}
        action(web,org,'recovery-preview',{'package':package},422)
    r=save(web,org,'control')
    for changes in [{'owner':[]},{'due_on':[]},{'status':'approved'},{'owner':"'; DROP TABLE pl_records;--"}]:
        action(web,org,'bulk',{'ids':[r['id']],'changes':changes},422)
