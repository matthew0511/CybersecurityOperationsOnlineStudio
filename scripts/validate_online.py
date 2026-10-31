"""One-off synthetic live acceptance test, run inside the runtime Fargate task.

Uses an ephemeral owner only if installation has no owner yet. Never prints
credentials, cookies, setup code, or request bodies. Archives its synthetic
organization and removes only its own temporary login on completion.
"""
import http.cookiejar
import json
import os
import secrets
import urllib.error
import urllib.request

from cyberstudio.web.database import connect

base=os.environ['STUDIO_URL'].rstrip('/')
username='validation-'+secrets.token_hex(8)
password=secrets.token_urlsafe(32)
jar=http.cookiejar.CookieJar()
client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
csrf=''
org=None
checks=[]


def request(path,data=None,expect=200):
    headers={'Content-Type':'application/json'}
    if csrf:headers['X-CSRF-Token']=csrf
    body=json.dumps(data).encode() if data is not None else None
    req=urllib.request.Request(base+path,data=body,headers=headers)
    try:
        with client.open(req,timeout=25) as response:
            content=response.read()
            assert response.status==expect
            return content
    except urllib.error.HTTPError as exc:
        if exc.code==expect:return b''
        raise RuntimeError(f'HTTP {exc.code} on {path}') from None


def call(method,**args):
    result=json.loads(request('/api/call/'+method,{'arguments':args}))['result']
    checks.append(method)
    return result


try:
    assert json.loads(request('/readyz'))['status']=='ready'
    checks.append('database_readiness')
    assert b'Online Studio' in request('/')
    request('/api/me',expect=401)
    checks.append('unauthenticated_access_denied')
    assert json.loads(request('/api/status'))['setup_required'], 'Owner already configured; do not replace an existing owner'
    request('/api/setup',{'code':os.environ['SETUP_TOKEN'],'username':username,'password':password})
    session=json.loads(request('/api/login',{'username':username,'password':password}))
    csrf=session['csrf']
    checks.append('owner_setup_and_login')
    org=call('create_organization',name='Synthetic AWS acceptance '+secrets.token_hex(6),industry='Synthetic validation only')
    assessment=call('create_assessment',org=org,title='Synthetic baseline')
    question=call('questions',org=org,assessment=assessment)[0]
    call('answer_question',org=org,assessment=assessment,code=question['code'],answer='Partial',rationale='Synthetic acceptance test')
    risk=call('add_risk',org=org,title='Synthetic exposure',description='Synthetic record',likelihood=3,impact=4,rationale='Acceptance test')
    task=call('add_task',org=org,risk=risk,title='Synthetic remediation',owner=username)
    call('update_task_status',org=org,tid=task,new_status='in_progress')
    call('configure_framework',org=org,key='nist-csf',enabled=True)
    call('upsert_implementation',org=org,key='nist-csf',reference='TEST-1',title='Synthetic control',status='in_progress')
    call('create_vendor',org=org,name='Synthetic supplier')
    call('add_vulnerability',org=org,title='Synthetic vulnerability',source='Acceptance test',severity='low')
    call('create_audit',org=org,title='Synthetic audit',audit_type='internal',lead=username)
    call('create_change',org=org,title='Synthetic change',change_type='normal',requester=username,owner=username)
    call('upsert_initiative',org=org,title='Synthetic initiative')
    for method in ['board_snapshot','list_risks','list_tasks','vendors','vulnerabilities','frameworks','implementations','audits','changes','evidence','governance_events','policies','incidents']:
        call(method,org=org)
    for kind in ['executive','board']:
        for ext in ['pdf','xlsx']:
            data=request(f'/api/report/{org}/{kind}/{ext}')
            assert len(data)>1000
            assert data.startswith(b'%PDF' if ext=='pdf' else b'PK')
            checks.append(kind+'_'+ext)
    saved=csrf
    csrf='invalid'
    request('/api/call/create_organization',{'arguments':{'name':'CSRF should fail'}},expect=403)
    csrf=saved
    checks.append('csrf_rejection')
    request('/api/logout',{})
    request('/api/me',expect=401)
    checks.append('logout_revocation')
    print(json.dumps({'live_acceptance':'PASS','checks':checks,'synthetic_only':True}))
finally:
    with connect() as db:
        with db.transaction():
            if org:db.execute("UPDATE organizations SET status='archived' WHERE id=%s",(org,))
            db.execute('DELETE FROM web_sessions WHERE username=%s',(username,))
            db.execute('DELETE FROM web_users WHERE username=%s',(username,))
