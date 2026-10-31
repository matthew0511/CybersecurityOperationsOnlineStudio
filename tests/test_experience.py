"""PostgreSQL workflow/security integration tests for the coordinated experience release."""
import io
import json
import pytest
from fastapi.testclient import TestClient
from test_web import web, login, call, PW
from cyberstudio.web.app import app
from cyberstudio.web.database import connect, migrate


def send(client,org,action,body=None,expected=200):
    r=client.post(f'/api/experience/{org}/{action}',json=body or {})
    assert r.status_code==expected,r.text
    return r.json()


def base(client):
    login(client)
    org=call(client,'create_organization',name='Experience test')
    other=call(client,'create_organization',name='Other org')
    vendor=call(client,'create_vendor',org=org,name='Example Supplier')
    aid=call(client,'create_assessment',org=org,title='Supplier assessment',template_id='builtin:third-party-risk-v1')
    return org,other,vendor,aid


def invited(client,org,username='viewer',role='viewer'):
    token=send(client,org,'invite',{'kind':'team','username':username,'role':role})['token']
    member=TestClient(app,base_url='https://testserver')
    r=member.post('/api/invitation/redeem',json={'token':token,'password':PW})
    assert r.status_code==200,r.text
    r=member.post('/api/login',json={'username':username,'password':PW})
    assert r.status_code==200,r.text
    member.headers['x-csrf-token']=r.json()['csrf']
    return member


def test_membership_isolation_and_legacy_routes(web):
    org,other,vendor,aid=base(web)
    viewer=invited(web,org)
    assert [x['id'] for x in call(viewer,'list_organizations')]==[org]
    assert viewer.get('/api/experience/'+other).status_code==403
    assert viewer.post('/api/call/questions',json={'arguments':{'org':other,'assessment':aid}}).status_code==403
    send(viewer,org,'settings',{'brand_name':'Forbidden'},403)
    send(viewer,org,'comment',{'type':'assessment','id':aid,'body':'Forbidden'},403)
    assert viewer.post('/api/call/create_organization',json={'arguments':{'name':'Forbidden'}}).status_code==403
    assert viewer.get(f'/api/report/{other}/executive/pdf').status_code==403
    eid=web.post('/api/upload/evidence',data={'org':org,'title':'Evidence'},files={'file':('sample.txt',b'hello','text/plain')}).json()['result']
    assert viewer.get(f'/api/evidence/{org}/{eid}').status_code==200
    assert viewer.get(f'/api/evidence/{other}/{eid}').status_code==403
    send(web,org,'membership',{'username':'viewer','role':'remove'})
    assert viewer.get('/api/experience/'+org).status_code==403


def test_narrative_autosave_version_conditions_and_review(web):
    org,other,vendor,aid=base(web)
    send(web,org,'assessment',{'assessment':aid,'vendor':vendor,'reviewer':'owner','due_date':'2099-01-01'})
    data=web.get(f'/api/experience/{org}/questionnaire/{aid}').json()
    assert len(data['questions'])==60
    send(web,org,'response',{'assessment':aid,'code':'TPR-009','response':'No','version':0})
    send(web,org,'response',{'assessment':aid,'code':'TPR-009','response':'stale','version':0},409)
    data=web.get(f'/api/experience/{org}/questionnaire/{aid}').json()
    assert next(q for q in data['questions'] if q['code']=='TPR-010')['visible'] is False
    assert 'TPR-010' not in data['summary']['unanswered']
    send(web,org,'review',{'assessment':aid,'state':'submitted'},422)
    for q in data['questions']:
        if q['code']!='TPR-009':send(web,org,'response',{'assessment':aid,'code':q['code'],'response':'Example response','version':q['version']})
    send(web,org,'review',{'assessment':aid,'state':'submitted'})
    send(web,org,'response',{'assessment':aid,'code':'TPR-001','response':'locked','version':1},409)
    assert web.post('/api/call/save_questionnaire_response',json={'arguments':{'org':org,'assessment':aid,'code':'TPR-001','response':'locked'}}).status_code==409
    send(web,org,'review',{'assessment':aid,'state':'approved'})
    send(web,org,'review',{'assessment':aid,'state':'needs_changes','notes':'Please clarify data storage'})
    send(web,org,'response',{'assessment':aid,'code':'TPR-001','response':'Corrected','version':1})


def test_vendor_portal_restricted_csrf_one_use_and_revocation(web):
    org,other,vendor,aid=base(web)
    invite=send(web,org,'invite',{'kind':'vendor','assessment':aid})
    vendor_client=TestClient(app,base_url='https://testserver')
    r=vendor_client.post('/api/invitation/redeem',json={'token':invite['token']})
    assert r.status_code==200,r.text
    assert vendor_client.post('/api/invitation/redeem',json={'token':invite['token']}).status_code==403
    assert vendor_client.get('/api/me').status_code==401
    assert vendor_client.get('/api/experience/'+org).status_code==401
    r=vendor_client.get('/api/portal');assert r.status_code==200,r.text
    data=r.json();assert len(data['questions'])==60
    assert 'evidence' not in data['questions'][0] and 'organization_id' not in data['questions'][0]
    assert vendor_client.post('/api/portal/response',json={'code':'TPR-001','response':'Example','version':0}).status_code==403
    vendor_client.headers['x-csrf-token']=data['csrf']
    assert vendor_client.post('/api/portal/response',json={'code':'TPR-001','response':'Example','version':0}).status_code==200
    assert vendor_client.post('/api/portal/submit',json={}).status_code==422
    r=vendor_client.post('/api/portal/evidence/TPR-001',files={'file':('example.txt',b'example','text/plain')})
    assert r.status_code==200,r.text
    invites=web.get(f'/api/experience/{org}/invites').json()
    send(web,org,'revoke_invite',{'id':next(i['id'] for i in invites if i['kind']=='vendor')})
    assert vendor_client.get('/api/portal').status_code==401


def test_links_comments_mentions_and_evidence_scoping(web):
    org,other,vendor,aid=base(web)
    reviewer=invited(web,org,'reviewer','reviewer')
    send(web,org,'assessment',{'assessment':aid,'vendor':vendor,'reviewer':'reviewer'})
    send(reviewer,org,'comment',{'type':'assessment','id':aid,'body':'@owner Please review this questionnaire.'})
    ownerdata=web.get('/api/experience/'+org).json()
    assert any('Mention' in n['title'] for n in ownerdata['notifications'])
    assert web.get(f'/api/experience/{org}/record/vendor/{vendor}').json()['links'][0]['record']['id']==aid
    evidence=web.post('/api/upload/evidence',data={'org':org,'title':'Security policy'},files={'file':('policy.txt',b'policy','text/plain')}).json()['result']
    send(reviewer,org,'question_evidence',{'assessment':aid,'code':'TPR-001','evidence':evidence})
    assert web.get(f'/api/experience/{org}/questionnaire/{aid}').json()['questions'][0]['evidence'][0]['id']==evidence
    other_aid=call(web,'create_assessment',org=other,title='Other assessment',template_id='builtin:third-party-risk-v1')
    send(web,org,'link',{'source_type':'assessment','source_id':aid,'target_type':'assessment','target_id':other_aid},404)
    send(reviewer,org,'invite',{'kind':'vendor','assessment':aid},403)
    send(reviewer,org,'review',{'assessment':aid,'state':'needs_changes','notes':'Need supporting evidence'})


def test_dependencies_and_legacy_completion_guard(web):
    org,other,vendor,aid=base(web)
    risk=call(web,'add_risk',org=org,title='Risk',description='',likelihood=2,impact=3,rationale='Example')
    a=call(web,'add_task',org=org,risk=risk,title='Prerequisite')
    b=call(web,'add_task',org=org,risk=risk,title='Dependent')
    send(web,org,'dependency',{'id':b,'depends_on':a})
    send(web,org,'dependency',{'id':a,'depends_on':b},422)
    send(web,org,'task',{'id':b,'status':'done'},409)
    assert web.post('/api/call/update_task_status',json={'arguments':{'org':org,'tid':b,'new_status':'done'}}).status_code==409
    send(web,org,'task',{'id':a,'status':'done','due_date':'2099-01-01'})
    send(web,org,'task',{'id':b,'status':'done'})


def test_snapshots_reminders_preferences_branding_and_reports(web):
    org,other,vendor,aid=base(web)
    send(web,org,'settings',{'brand_name':'Example Dental','accent':'#123456','reminders_enabled':True,'reminder_frequency':'weekly','reminder_lead_days':7,'escalation_days':3})
    send(web,org,'settings',{'accent':'javascript:alert(1)'},422)
    send(web,org,'preferences',{'theme':'dark','widgets':['history','exposure']})
    send(web,org,'run_reminders');send(web,org,'run_reminders')
    data=web.get('/api/experience/'+org).json()
    assert len(data['snapshots'])==1
    assert len([n for n in data['notifications'] if n['object_id']==vendor])==1
    assert data['preferences']['theme']=='dark'
    assert data['settings']['brand_name']=='Example Dental'
    for format in ['preview','pdf','xlsx']:
        r=web.post(f'/api/experience/{org}/reports/{format}',json={'sections':['summary','history','vendors'],'start':'2020-01-01','end':'2099-01-01','commentary':'Example board commentary'})
        assert r.status_code==200,r.text
        if format=='preview':assert r.json()['brand']=='Example Dental'
        else:assert len(r.content)>1000
    assert web.get(f'/api/experience/{org}/search?q=Example').json()['results']
    assert web.post(f'/api/experience/{org}/branding/logo',content=b'bad',headers={'content-type':'image/svg+xml'}).status_code==422
    from PIL import Image
    image=io.BytesIO();Image.new('RGB',(10,10),'blue').save(image,format='PNG')
    assert web.post(f'/api/experience/{org}/branding/logo',content=image.getvalue(),headers={'content-type':'image/png'}).status_code==200
    assert web.get(f'/api/experience/{org}/branding/logo').content==image.getvalue()


def test_migration_preserves_owner_and_records(web):
    org,other,vendor,aid=base(web)
    with connect() as db:migrate(db)
    assert web.get('/api/me').json()['role']=='owner'
    assert len(call(web,'questions',org=org,assessment=aid))==60
    assert len(call(web,'vendors',org=org))==1


def test_invitation_expiry_and_generic_read_only_protection(web):
    org,other,vendor,aid=base(web)
    viewer=invited(web,org)
    assert viewer.post('/api/call/add_risk',json={'arguments':{'org':org,'title':'blocked','description':'','likelihood':1,'impact':1,'rationale':'test'}}).status_code==403
    invite=send(web,org,'invite',{'kind':'vendor','assessment':aid})
    with connect() as db:db.execute("UPDATE xp_invites SET expires_at=1 WHERE kind='vendor'")
    assert TestClient(app,base_url='https://testserver').post('/api/invitation/redeem',json={'token':invite['token']}).status_code==403
    viewer.headers.pop('x-csrf-token')
    assert viewer.post(f'/api/experience/{org}/preferences',json={'theme':'light'}).status_code==403
