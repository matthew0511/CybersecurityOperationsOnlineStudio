"""Bounded deterministic adversarial corpus. Disposable studio_test only."""
import io,json,multiprocessing,random,time
import pytest
from fastapi.testclient import TestClient
from cyberstudio.web.app import app
from cyberstudio.web.database import connect
from cyberstudio.web.platform.store import validate_rules
from test_web import web,login,call,PW

SQL_PAYLOADS=["' OR '1'='1", "' UNION SELECT NULL--", "'); DROP TABLE web_users;--", "' AND (SELECT pg_sleep(0)) IS NULL--", "\" OR 1=1--", "../%27%20OR%201=1--", "'; SELECT current_user;--", "\\';--", "%' OR TRUE--", "'/**/OR/**/1=1--"]
BAD_VALUES=[None,True,False,0,1,-1,1.5,'',[],{},[{}],[[]],{'nested':[]},'x'*12001,'\x00','\ud800']

def quiet(client):
    result=TestClient(app,base_url='https://testserver',raise_server_exceptions=False)
    result.cookies.update(client.cookies);result.headers.update(client.headers)
    return result

def test_request_boundary_without_database():
    with TestClient(app,base_url='https://testserver',raise_server_exceptions=False) as c:
        for value in ['invalid','-1','+4','1,1','9999999999999999999999999999999999999999']:
            r=c.get('/healthz',headers={'content-length':value})
            assert r.status_code in {400,413},(value,r.status_code)
        for payload in [b'{',b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1,"x":2}',b'{"x":"\\u0000"}',b'{"x":"\\ud800"}',b'['*40+b'0'+b']'*40]:
            r=c.post('/api/login',content=payload,headers={'content-type':'application/json'})
            assert r.status_code in {400,413,422},(payload[:40],r.status_code)
        chunks=(b'x'*1024*1024 for _ in range(8))
        r=c.post('/api/login',content=chunks,headers={'content-type':'application/json'})
        assert r.status_code==413
        assert 'content-security-policy' in r.headers

def test_typed_route_mutation_corpus(web):
    login(web);org=call(web,'create_organization',name='Fuzz fixture')
    c=quiet(web);failures=[];checks=0
    site=c.post(f'/api/platform/{org}/records/site',json={'title':'Mutation target','data':{}}).json()
    cases=[
      (f'/api/platform/{org}/rooms',{'allowed':[{'kind':'program','id':'missing'}]},'allowed'),
      (f'/api/platform/{org}/tokens',{'password':PW,'scopes':['records:read']},'scopes'),
      (f'/api/platform/{org}/editions',{'template':'board','format':'pdf'},'template'),
      (f'/api/platform/{org}/editions',{'template':'board','format':'pdf'},'format'),
      (f'/api/platform/{org}/capabilities',{'password':PW,'username':'nobody','denied':[]},'denied'),
      (f'/api/experience/{org}/preferences',{'theme':'dark'},'theme'),
      (f'/api/experience/{org}/settings',{'accent':'#123456'},'accent'),
      (f'/api/experience/{org}/reports/preview',{'sections':['summary']},'sections'),
      (f'/api/platform/{org}/records/site',{'title':'safe','data':{}},'id'),
      (f'/api/platform/{org}/records/site',{'title':'safe','data':{}},'title'),
      (f'/api/platform/{org}/records/site',{'title':'safe','data':{}},'data'),
      (f'/api/call/list_risks',{'arguments':{'org':org}},'arguments'),
      (f'/api/platform/{org}/record/{site["id"]}/status',{'version':1,'status':'in_progress'},'status'),
      (f'/api/platform/{org}/bulk-tasks',{'ids':['missing'],'changes':{'owner':'test'}},'ids'),
      (f'/api/platform/{org}/bulk-tasks',{'ids':[],'changes':{'owner':'test'}},'changes'),
      (f'/api/platform/{org}/integrations',{'provider':'github','config':{},'credentials':{}},'credentials'),
      (f'/api/platform/{org}/integrations',{'provider':'github','config':{},'credentials':{}},'provider'),
      (f'/api/experience/{org}/comment',{'type':'site','id':'missing','body':'test'},'type'),
      (f'/api/experience/{org}/invite',{'kind':'team','username':'testuser','role':'viewer'},'kind'),
      (f'/api/experience/{org}/invite',{'kind':'team','username':'testuser','role':'viewer'},'role'),
      (f'/api/experience/{org}/membership',{'username':'missing','role':'viewer'},'role'),
    ]
    for path,body,field in cases:
        for value in BAD_VALUES:
            # No malformed Unicode in the HTTP encoder: encode deliberately as JSON escapes.
            payload={**body,field:value}
            r=c.post(path,content=json.dumps(payload),headers={'content-type':'application/json'})
            checks+=1
            if r.status_code>=500:failures.append((path,field,repr(value)[:60],r.status_code))
    for offset in ['-1',str(2**100),'1e100','null','1;SELECT 1']:
        r=c.get(f'/api/platform/{org}/records/site',params={'offset':offset});checks+=1
        if r.status_code>=500:failures.append(('offset',offset,r.status_code))
    print('SECURITY_FUZZ_CASES',checks)
    assert not failures,failures

def test_nested_typed_entries_reject_objects(web):
    login(web);org=call(web,'create_organization',name='Nested corpus')
    c=quiet(web)
    cases=[(f'/api/platform/{org}/rooms',{'allowed':[None]}),
      (f'/api/platform/{org}/rooms',{'allowed':[[]]}),
      (f'/api/platform/{org}/rooms',{'allowed':[{'kind':[],'id':'x'}]}),
      (f'/api/platform/{org}/tokens',{'password':PW,'scopes':[{}]}),
      (f'/api/platform/{org}/capabilities',{'password':PW,'denied':[{}]}),
      (f'/api/platform/{org}/editions',{'sections':[{}]}),
      (f'/api/platform/{org}/records/site',{'title':'x','id':{'x':1},'data':{}})]
    errors=[]
    for path,body in cases:
        r=c.post(path,json=body)
        if r.status_code not in {400,403,404,409,413,422}:errors.append((path,r.status_code))
    assert not errors,errors

def test_sql_injection_remains_literal_and_tenant_scoped(web):
    login(web);org=call(web,'create_organization',name='SQL corpus');other=call(web,'create_organization',name='SQL other')
    c=quiet(web)
    secret=c.post(f'/api/platform/{other}/records/site',json={'title':'Other organization sentinel','data':{}}).json()
    for i,payload in enumerate(SQL_PAYLOADS):
        before=time.monotonic()
        r=c.post('/api/login',json={'username':payload,'password':'synthetic-invalid'})
        assert r.status_code in {401,422}
        assert time.monotonic()-before<5
        r=c.post(f'/api/platform/{org}/records/site',json={'title':payload,'data':{}})
        assert r.status_code==200,r.text
        assert r.json()['title']==payload.strip()
        search=c.get(f'/api/platform/{org}/records/site',params={'q':payload})
        assert search.status_code==200,search.text
        assert all(row['organization_id']==org for row in search.json())
        assert all(row['id']!=secret['id'] for row in search.json())
        operation=c.post('/api/call/'+payload,json={'arguments':{'org':org}})
        assert operation.status_code in {404,405}
    assert c.get('/api/me').json()['username']=='owner'
    with connect() as db:
        assert db.execute("SELECT count(*) AS n FROM web_users WHERE username='owner'").fetchone()['n']==1
        assert db.execute('SELECT count(*) AS n FROM pl_records WHERE organization_id=%s',(other,)).fetchone()['n']==1

def _dense_dag():
    rules=[]
    for i in range(30):
        for jump in (1,2,3):rules.append({'parent':str(i),'child':str(i+jump)})
    validate_rules(rules)

def test_questionnaire_graph_has_bounded_validation_cost():
    process=multiprocessing.get_context('fork').Process(target=_dense_dag)
    process.start();process.join(2)
    if process.is_alive():process.terminate();process.join();pytest.fail('90-edge acyclic questionnaire graph exceeded two-second validation budget')
    assert process.exitcode==0
    with pytest.raises(Exception) as exc:validate_rules([{'parent':'a','child':'b'},{'parent':'b','child':'a'}])
    assert getattr(exc.value,'status_code',None)==422

def test_seeded_json_tree_corpus(web):
    login(web);org=call(web,'create_organization',name='Seeded fuzz')
    c=quiet(web);rng=random.Random(20261101);bad=[]
    for _ in range(1000):
        field=rng.choice(['title','owner','due_on','data','id','version'])
        body={'title':'bounded','data':{}}
        body[field]=rng.choice(BAD_VALUES[:-3])
        r=c.post(f'/api/platform/{org}/records/site',json=body)
        if r.status_code>=500:bad.append((field,repr(body[field]),r.status_code))
    assert not bad,bad[:12]


def test_unicode_tokens_and_query_encoding_fail_closed(web):
    login(web);org=call(web,'create_organization',name='Encoding corpus')
    c=quiet(web)
    r=c.post('/api/call/list_risks',json={'arguments':{'org':org}},headers={'x-csrf-token':b'\xe9'})
    assert r.status_code==403
    for key,value in [('q','\x00'),('offset',str(2**100))]:
        assert c.get(f'/api/platform/{org}/records/site',params={key:value}).status_code==422
    assert c.get('/api/sso/callback',params={'state':'\u00e9','code':'synthetic'}).status_code==403


def test_spreadsheet_and_html_payloads_are_data(web):
    from openpyxl import load_workbook
    login(web);org=call(web,'create_organization',name='Export corpus')
    payloads=['=1+1','+SUM(1,1)','-1+1','@SUM(1,1)','  =1+1','<img src=x onerror=alert(1)>']
    for payload in payloads:call(web,'add_risk',org=org,title=payload,description='Synthetic export corpus',likelihood=2,impact=2,rationale='Synthetic test')
    result=web.get(f'/api/report/{org}/executive/xlsx')
    assert result.status_code==200
    wb=load_workbook(io.BytesIO(result.content))
    for sheet in wb:
        for row in sheet:
            assert all(cell.data_type!='f' for cell in row),'Unexpected executable formula'
    pdf=web.get(f'/api/report/{org}/executive/pdf')
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
