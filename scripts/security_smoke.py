"""Read-only production checks; fuzzing stays in disposable studio_test."""
import json,os,ssl,time,urllib.request,urllib.error
from datetime import datetime,timezone

origin=os.environ.get('STUDIO_ORIGIN','https://cybersecurityoperationstudio.com').rstrip('/')
if origin!='https://cybersecurityoperationstudio.com':raise ValueError('Use the approved Studio origin')
checks=[]
def check(path,expected,data=None):
    request=urllib.request.Request(origin+path,data=data,headers={'Content-Type':'application/json'} if data is not None else {})
    started=time.monotonic()
    try:
        response=urllib.request.urlopen(request,timeout=15,context=ssl.create_default_context())
    except urllib.error.HTTPError as e:response=e
    with response:
        body=response.read(2*1024*1024);status=response.status
        assert status==expected,(path,status)
        for header in ['Content-Security-Policy','Strict-Transport-Security','X-Content-Type-Options','Cache-Control']:
            assert response.headers.get(header),(path,header)
        if path=='/':assert b'Program Owner - Matthew Harris' in body
        if path=='/readyz':assert json.loads(body)['database']=='connected'
        checks.append({'path':path,'status':status,'seconds':round(time.monotonic()-started,3)})

for path in ['/healthz','/readyz','/','/static/app.js']:check(path,200)
for path in ['/api/me','/api/security','/api/platform/catalog','/api/platform/operations']:check(path,401)
# These syntactically invalid requests are rejected before login/database logic.
for raw in [b'{"x":NaN}',b'{"x":1,"x":2}',b'{"x":"\\u0000"}']:check('/api/login',422,raw)
print(json.dumps({'verified_at_utc':datetime.now(timezone.utc).isoformat(),'origin':origin,'checks':checks,'limitations':'No production credentials, business mutations or exploit payload fuzzing used.'}))
