import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cyberstudio.web.app import app, ALLOWED, fields
from cyberstudio.web.database import connect, migrate, service

PW='Synthetic-only-password-2026!'


def test_operation_contracts():
    assert len(ALLOWED)>80
    for name in ALLOWED:
        assert fields(name) is not None


def test_public_static_and_health():
    with TestClient(app,base_url='https://testserver') as client:
        assert client.get('/healthz').json()=={'status':'ok'}
        r=client.get('/')
        assert r.status_code==200 and 'Online Studio' in r.text
        assert "frame-ancestors 'none'" in r.headers['content-security-policy']
        assert client.get('/static/app.js').status_code==200
        assert client.get('/docs').status_code==404


@pytest.fixture
def web(monkeypatch):
    if not os.getenv('TEST_DATABASE_URL'):
        pytest.skip('PostgreSQL integration is run in CodeBuild against an isolated test database')
    monkeypatch.setenv('SETUP_TOKEN','synthetic-one-use-code')
    with connect() as db:
        # TEST_DATABASE_URL must point to the disposable postgres test container.
        assert db.info.dbname=='studio_test', 'Refusing destructive test reset outside studio_test'
        db.execute('DROP SCHEMA IF EXISTS studio CASCADE')
        migrate(db)
    with TestClient(app,base_url='https://testserver') as client:
        yield client


def login(client):
    assert client.post('/api/setup',json={'code':'synthetic-one-use-code','username':'owner','password':PW}).status_code==200
    response=client.post('/api/login',json={'username':'owner','password':PW})
    assert response.status_code==200,response.text
    client.headers['x-csrf-token']=response.json()['csrf']
    return client


def call(client,operation,**args):
    r=client.post('/api/call/'+operation,json={'arguments':args})
    assert r.status_code==200,r.text
    return r.json()['result']


def test_authentication_setup_csrf_and_logout(web):
    assert web.get('/readyz').status_code==200
    assert web.get('/api/me').status_code==401
    assert web.post('/api/setup',json={'code':'wrong','username':'owner','password':PW}).status_code==403
    login(web)
    assert web.post('/api/setup',json={'code':'synthetic-one-use-code','username':'other','password':PW}).status_code==409
    assert web.get('/api/me').json()['username']=='owner'
    headers=dict(web.headers);web.headers.pop('x-csrf-token')
    assert web.post('/api/call/create_organization',json={'arguments':{'name':'Blocked'}}).status_code==403
    web.headers.update(headers)
    assert web.post('/api/logout').status_code==200
    assert web.get('/api/me').status_code==401


def test_login_lockout(web):
    login(web)
    for _ in range(5):
        assert web.post('/api/login',json={'username':'owner','password':'wrong'}).status_code==401
    assert web.post('/api/login',json={'username':'owner','password':PW}).status_code==429


def test_domain_workflows_and_reports(web):
    login(web)
    org=call(web,'create_organization',name='Synthetic Online Alpha',industry='Testing')
    other=call(web,'create_organization',name='Synthetic Online Bravo')
    assessment=call(web,'create_assessment',org=org,title='Baseline')
    question=call(web,'questions',org=org,assessment=assessment)[0]
    call(web,'answer_question',org=org,assessment=assessment,code=question['code'],answer='Partial',rationale='Synthetic rationale')
    risk=call(web,'add_risk',org=org,title='MFA coverage',description='Synthetic',likelihood=4,impact=4,rationale='Documented exposure')
    task=call(web,'add_task',org=org,risk=risk,title='Enforce MFA',owner='owner')
    call(web,'update_task_status',org=org,tid=task,new_status='in_progress')
    call(web,'set_residual_risk',org=org,risk=risk,likelihood=2,impact=2,rationale='Compensating controls')
    call(web,'configure_framework',org=org,key='nist-csf',enabled=True)
    call(web,'upsert_implementation',org=org,key='nist-csf',reference='GV.OC',title='Organizational context',status='in_progress')
    vendor=call(web,'create_vendor',org=org,name='Synthetic Supplier')
    call(web,'record_vendor_review',org=org,vendor=vendor,reviewer='owner',findings='Synthetic review',likelihood=2,impact=3,next_review_date='2099-01-01')
    assert call(web,'vendors',org=org)[0]['risk_score']==6
    vid=call(web,'add_vulnerability',org=org,title='Synthetic finding',source='Manual',severity='high')
    call(web,'update_vulnerability',org=org,vid=vid,status='mitigated',actor='owner',reason='Verified fix')
    call(web,'upsert_initiative',org=org,title='Security roadmap',budget_amount=100)
    audit=call(web,'create_audit',org=org,title='Internal review',audit_type='internal',lead='owner')
    call(web,'add_finding',org=org,audit_id=audit,title='Synthetic observation',severity='low',description='Example',owner='owner')
    change=call(web,'create_change',org=org,title='Synthetic change',change_type='normal',requester='owner',owner='operator')
    call(web,'set_change_plan',org=org,ident=change,implementation_plan='Apply change',rollback_plan='Revert change')
    eid=web.post('/api/upload/evidence',data={'org':org,'title':'Synthetic evidence'},files={'file':('example.txt',b'Example evidence','text/plain')})
    assert eid.status_code==200,eid.text
    eid=eid.json()['result']
    assert web.get('/api/evidence/'+org+'/'+eid).content==b'Example evidence'
    assert web.get('/api/evidence/'+other+'/'+eid).status_code==404
    assert web.post('/api/call/questions',json={'arguments':{'org':other,'assessment':assessment}}).status_code==404
    for method in ['board_snapshot','executive_metrics','governance_metrics','evidence','control_evaluations','policies','incidents','imported_control_inventory','imported_vendor_annotations','import_history','import_history_p3','board_reports','board_decisions','changes','audits','findings','governance_events','audit_events','change_calendar']:
        call(web,method,org=org)
    for kind in ['executive','board']:
        for extension in ['pdf','xlsx']:
            response=web.get(f'/api/report/{org}/{kind}/{extension}')
            assert response.status_code==200,response.text
            assert len(response.content)>1000
    assert web.post('/api/call/_exists',json={'arguments':{}}).status_code==404
    assert web.post('/api/call/add_risk',json={'arguments':{'org':org,'sql':'DROP TABLE'}}).status_code==422


def test_postgres_constraints_and_immutable_history(web):
    login(web)
    org=call(web,'create_organization',name='Synthetic Unique')
    assert web.post('/api/call/create_organization',json={'arguments':{'name':'Synthetic Unique'}}).status_code==422
    with connect() as db:
        import psycopg
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute('DELETE FROM audit_events WHERE organization_id=%s',(org,))
        assert db.execute('SELECT count(*) AS n FROM audit_events').fetchone()['n']>0


def test_import_preview_and_confirmation(web):
    login(web)
    org=call(web,'create_organization',name='Synthetic Import')
    payload=Path('examples/SYNTHETIC_NOTION_RISKS.csv').read_bytes()
    response=web.post('/api/upload/preview',data={'org':org,'module':'risks'},files={'file':('risks.csv',payload,'text/csv')})
    assert response.status_code==200,response.text
    assert web.post('/api/upload/import',data={'org':org,'module':'risks'},files={'file':('risks.csv',payload,'text/csv')}).status_code==422


def test_default_third_party_questionnaire_api(web):
    login(web)
    org=call(web,'create_organization',name='Synthetic Questionnaire')
    assessment=call(web,'create_assessment',org=org,title='Third-party review',template_id='builtin:third-party-risk-v1')
    questions=call(web,'questions',org=org,assessment=assessment)
    assert len(questions)==60
    call(web,'save_questionnaire_response',org=org,assessment=assessment,code='TPR-001',response='Example Supplier\nSecurity contact')
    saved=call(web,'questions',org=org,assessment=assessment)[0]
    assert saved['rationale']=='Example Supplier\nSecurity contact'
    assert saved['answer']=='Unknown'
