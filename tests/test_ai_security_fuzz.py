"""Adversarial input coverage for the AI governance extension; isolated studio_test only."""
import json,random
from test_web import web,PW
from test_experience import invited
from test_ai_governance import setup,case_data,values,FUTURE
from test_platform import save
from test_security_fuzz import quiet,BAD_VALUES,SQL_PAYLOADS
from cyberstudio.web.platform.ai_catalog import AI_MODULES


def base_data(kind,case):
    if kind=='ai_use_case':return case_data()
    result=values(kind,case)
    if kind in {'ai_decision','ai_exception'}:result.update(approver='owner',expires_on=FUTURE)
    return result


def test_ai_catalog_field_mutation_corpus(web):
    org,_=setup(web);case=save(web,org,'ai_use_case','Fuzz baseline',case_data())
    c=quiet(web);errors=[];checks=0
    for kind,(_,fields) in AI_MODULES.items():
        baseline=base_data(kind,case['id'])
        for name in fields:
            for value in BAD_VALUES:
                response=c.post(f'/api/platform/{org}/records/{kind}',content=json.dumps({'title':'Synthetic AI input mutation','data':{**baseline,name:value}}),headers={'content-type':'application/json'})
                checks+=1
                if response.status_code>=500:errors.append((kind,name,repr(value)[:50],response.status_code))
    print('AI_FUZZ_CASES',checks)
    assert not errors,errors[:20]


def test_ai_sql_payloads_remain_literal_and_scoped(web):
    org,other=setup(web);c=quiet(web)
    secret=save(web,other,'ai_use_case','Other organization AI sentinel',case_data())
    for payload in SQL_PAYLOADS:
        r=c.post(f'/api/platform/{org}/records/ai_use_case',json={'title':payload,'data':{**case_data(),'product':payload,'configuration':payload}})
        assert r.status_code==200,r.text
        assert r.json()['title']==payload.strip() and r.json()['data']['product']==payload.strip()
        state=c.get(f'/api/platform/{org}/ai/overview')
        assert state.status_code==200,state.text
        assert all(row['id']!=secret['id'] for row in state.json()['cases'])
        found=c.get(f'/api/platform/{org}/records/ai_use_case',params={'q':payload})
        assert found.status_code==200 and all(row['organization_id']==org for row in found.json())


def test_ai_malformed_approval_metadata_is_never_trusted(web):
    org,_=setup(web);c=quiet(web)
    body={'title':'Synthetic untrusted metadata','data':{**case_data(),'calculated':{'readiness_hash':'forged'},'approved_by':'owner','approved_at':FUTURE,'approval_version':1}}
    r=c.post(f'/api/platform/{org}/records/ai_use_case',json=body)
    assert r.status_code==200,r.text
    assert not {'approved_by','approved_at','approval_version','calculated'}&set(r.json()['data'])
    ident=r.json()['id']
    for value in BAD_VALUES:
        response=c.post(f'/api/platform/{org}/record/{ident}/status',content=json.dumps({'version':1,'status':value,'password':PW}),headers={'content-type':'application/json'})
        assert response.status_code<500,(repr(value),response.status_code)
    assert c.get(f'/api/platform/{org}/ai/overview').json()['cases'][0]['authorization']=='not_authorized'


def test_ai_viewer_cannot_mutate_or_cross_organizations_with_injection(web):
    org,other=setup(web);save(web,other,'ai_use_case','Other scope',case_data())
    viewer=invited(web,org,'fuzz_viewer','viewer')
    for payload in SQL_PAYLOADS:
        assert viewer.post(f'/api/platform/{org}/records/ai_use_case',json={'title':payload,'data':case_data()}).status_code==403
    assert viewer.get(f'/api/platform/{other}/ai/overview').status_code==403
