from ..request_security import safe_compare
"""TOTP enrollment, recovery, sessions and tenant-pinned OIDC. Secrets never enter logs."""
import base64,hashlib,hmac,json,os,re,secrets,time
from datetime import datetime,timezone
from urllib.parse import urlencode
from cryptography.fernet import Fernet,InvalidToken
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import JSONResponse,RedirectResponse
import httpx,jwt,pyotp
from .store import fail,bounded
from .schema import actor
from ..database import connect

router=APIRouter()
HASH=lambda s:hashlib.sha256(s.encode()).hexdigest()
GUID=r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

def crypt():
    key=os.getenv('AUTH_ENCRYPTION_KEY','')
    if not key:fail('Security encryption key is not configured; contact the installation owner',503)
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))
def seal(value):return crypt().encrypt(value.encode()).decode()
def unseal(value):
    try:return crypt().decrypt(value.encode()).decode()
    except InvalidToken:fail('Encrypted configuration could not be opened; check the security key version',503)

def reauthenticate(db,user,body):
    from ..app import verify_password
    row=db.execute('SELECT password_hash FROM web_users WHERE username=%s AND enabled',(user['username'],)).fetchone()
    if body.get('password') and row and verify_password(row['password_hash'],str(body['password'])):return
    if body.get('mfa_code') and verify_factor(db,user['username'],str(body['mfa_code'])):return
    fail('Re-enter your current password or a fresh authenticator code',403)

def verify_factor(db,username,code):
    row=db.execute('SELECT * FROM pl_mfa WHERE username=%s FOR UPDATE',(username,)).fetchone()
    if not row or not row['enabled']:return False
    if re.fullmatch(r'\d{6}',code):
        secret=unseal(row['secret_cipher']);step=int(time.time())//30
        accepted=next((v for v in (step-1,step,step+1) if v>row['last_step'] and safe_compare(pyotp.TOTP(secret).at(v*30),code)),None)
        if accepted is not None:
            db.execute('UPDATE pl_mfa SET last_step=%s WHERE username=%s',(accepted,username));return True
    used=db.execute("UPDATE pl_recovery SET used_at=CURRENT_TIMESTAMP WHERE code_hash=%s AND username=%s AND purpose='mfa' AND used_at IS NULL RETURNING code_hash",(HASH(code),username)).fetchone()
    return bool(used)

def login_factor(db,row,body):
    factor=db.execute('SELECT enabled FROM pl_mfa WHERE username=%s',(row['username'],)).fetchone()
    if factor and factor['enabled']:
        with db.transaction():
            if not verify_factor(db,row['username'],str(body.get('mfa_code',''))):fail('Authenticator or recovery code required',401)

def current(db,request,write=False):
    from ..app import principal
    return principal(db,request,write=write)

def recovery_codes(db,username,purpose):
    db.execute('DELETE FROM pl_recovery WHERE username=%s AND purpose=%s',(username,purpose))
    codes=[secrets.token_urlsafe(24) for _ in range(8)]
    for value in codes:db.execute('INSERT INTO pl_recovery(code_hash,username,purpose) VALUES (%s,%s,%s)',(HASH(value),username,purpose))
    return codes

@router.get('/api/security')
def overview(request:Request):
    with connect() as db:
        user=current(db,request)
        factor=db.execute('SELECT enabled FROM pl_mfa WHERE username=%s',(user['username'],)).fetchone()
        sessions=db.execute('SELECT s.token_hash AS id,s.expires_at,m.created_at,m.user_agent,m.auth_method FROM web_sessions s LEFT JOIN pl_session_meta m ON m.token_hash=s.token_hash WHERE s.username=%s AND s.expires_at>%s ORDER BY s.expires_at DESC',(user['username'],int(time.time()))).fetchall()
        return dict(username=user['username'],role=user['role'],mfa_enabled=bool(factor and factor['enabled']),security_key_ready=bool(os.getenv('AUTH_ENCRYPTION_KEY')),sessions=[{**dict(s),'current':s['id']==user['token_hash']} for s in sessions],entra_configured=bool(db.execute("SELECT 1 FROM pl_installation WHERE key='entra' AND value->>'enabled'='true'").fetchone()))

@router.post('/api/security/{action}')
def manage(action:str,body:dict,request:Request):
    from ..experience import audit,require_owner
    with connect() as db,db.transaction():
        user=current(db,request,True);username=user['username']
        if action=='revoke_session':
            ident=bounded(body.get('id',''),100)
            if not db.execute('DELETE FROM web_sessions WHERE token_hash=%s AND username=%s RETURNING token_hash',(ident,username)).fetchone():fail('Session not found',404)
        elif action=='revoke_others':db.execute('DELETE FROM web_sessions WHERE username=%s AND token_hash<>%s',(username,user['token_hash']))
        elif action=='mfa_begin':
            reauthenticate(db,user,body)
            row=db.execute('SELECT enabled FROM pl_mfa WHERE username=%s',(username,)).fetchone()
            if row and row['enabled']:fail('Disable the current authenticator before replacing it',409)
            secret=pyotp.random_base32()
            db.execute('INSERT INTO pl_mfa(username,secret_cipher) VALUES (%s,%s) ON CONFLICT(username) DO UPDATE SET secret_cipher=EXCLUDED.secret_cipher,enabled=FALSE,last_step=-1,updated_at=CURRENT_TIMESTAMP',(username,seal(secret)))
            audit(db,username,'mfa:begin')
            return {'secret':secret,'otpauth_uri':pyotp.TOTP(secret).provisioning_uri(username,issuer_name='Cyber Security Operations Online Studio'),'message':'Add the setup key to your authenticator, then verify a code. Setup expires when replaced or enabled.'}
        elif action=='mfa_enable':
            row=db.execute('SELECT * FROM pl_mfa WHERE username=%s FOR UPDATE',(username,)).fetchone()
            if not row or row['enabled'] or (datetime.now(timezone.utc)-row['updated_at']).total_seconds()>600:fail('Enter a valid code from the pending authenticator')
            step=int(time.time())//30;totp=pyotp.TOTP(unseal(row['secret_cipher']))
            accepted=next((v for v in (step-1,step,step+1) if safe_compare(totp.at(v*30),str(body.get('code','')))),None)
            if accepted is None:fail('Enter a valid code from the pending authenticator')
            db.execute('UPDATE pl_mfa SET enabled=TRUE,last_step=%s,updated_at=CURRENT_TIMESTAMP WHERE username=%s',(accepted,username))
            codes=recovery_codes(db,username,'mfa');db.execute('DELETE FROM web_sessions WHERE username=%s AND token_hash<>%s',(username,user['token_hash']));audit(db,username,'mfa:enabled')
            return {'enabled':True,'recovery_codes':codes,'message':'Save these one-time codes offline. They will not be shown again.'}
        elif action=='mfa_disable':
            reauthenticate(db,user,body)
            if not verify_factor(db,username,str(body.get('code',''))):fail('A fresh authenticator or unused recovery code is also required',403)
            db.execute('DELETE FROM pl_mfa WHERE username=%s',(username,));db.execute("DELETE FROM pl_recovery WHERE username=%s AND purpose='mfa'",(username,))
        elif action=='recovery_kit':
            reauthenticate(db,user,body);codes=recovery_codes(db,username,'password');audit(db,username,'recovery:issued')
            return {'recovery_codes':codes,'message':'Password recovery codes reset only the password; enabled MFA is retained. Save offline.'}
        elif action=='mfa_policy':
            require_owner(user);reauthenticate(db,user,body)
            factor=db.execute('SELECT enabled FROM pl_mfa WHERE username=%s',(username,)).fetchone()
            if body.get('required') is True and (not factor or not factor['enabled'] or not db.execute("SELECT 1 FROM pl_recovery WHERE username=%s AND purpose='mfa' AND used_at IS NULL",(username,)).fetchone()):fail('Enroll and verify your own authenticator and save recovery codes before requiring MFA for all accounts',409)
            db.execute("INSERT INTO pl_installation(key,value) VALUES ('security_policy',%s::jsonb) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value",(json.dumps({'require_mfa':body.get('required') is True}),))
        elif action=='entra':
            require_owner(user);reauthenticate(db,user,body)
            tenant=bounded(body.get('tenant_id',''),36).lower();client=bounded(body.get('client_id',''),36).lower()
            if not re.fullmatch(GUID,tenant) or not re.fullmatch(GUID,client):fail('Use tenant and application GUIDs')
            cfg={'tenant_id':tenant,'client_id':client,'enabled':body.get('enabled') is True}
            old=db.execute("SELECT secret_cipher FROM pl_installation WHERE key='entra'").fetchone()
            secret=seal(bounded(body['client_secret'],8000)) if body.get('client_secret') else old['secret_cipher'] if old else ''
            if not secret:fail('Enter the confidential application secret')
            db.execute("INSERT INTO pl_installation(key,value,secret_cipher) VALUES ('entra',%s::jsonb,%s) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value,secret_cipher=EXCLUDED.secret_cipher",(json.dumps(cfg),secret))
        elif action=='entra_map':
            require_owner(user);reauthenticate(db,user,body)
            cfg=db.execute("SELECT value FROM pl_installation WHERE key='entra'").fetchone()
            if not cfg:fail('Configure the Entra application first')
            oid=bounded(body.get('object_id',''),36).lower();account=bounded(body.get('username',''),100)
            if not re.fullmatch(GUID,oid) or not db.execute('SELECT 1 FROM web_users WHERE username=%s AND enabled',(account,)).fetchone():fail('Map a tenant object GUID to an existing enabled account')
            db.execute('INSERT INTO pl_oidc_accounts VALUES (%s,%s,%s) ON CONFLICT(tenant_id,object_id) DO UPDATE SET username=EXCLUDED.username',(cfg['value']['tenant_id'],oid,account))
        else:fail('Unknown security action',404)
        audit(db,username,'security:'+action)
        return {'saved':True}

@router.post('/api/recovery/password')
def recover(body:dict,request:Request):
    from ..app import limit,hasher
    username=str(body.get('username','')).lower();code=str(body.get('recovery_code',''));password=str(body.get('password',''))
    if not 16<=len(password)<=256:fail('Use a password of 16–256 characters')
    with connect() as db:
        with db.transaction():limit(db,'recovery:'+username)
        with db.transaction():
            row=db.execute("UPDATE pl_recovery SET used_at=CURRENT_TIMESTAMP WHERE username=%s AND code_hash=%s AND purpose='password' AND used_at IS NULL RETURNING code_hash",(username,HASH(code))).fetchone()
            if not row:fail('Invalid or consumed recovery code',403)
            db.execute('UPDATE web_users SET password_hash=%s WHERE username=%s AND enabled',(hasher.hash(password),username));db.execute('DELETE FROM web_sessions WHERE username=%s',(username,))
            from ..experience import audit
            audit(db,username,'password:recovered')
    return {'message':'Password reset. Sign in again; configured MFA is still required.'}

@router.get('/api/sso/start')
def sso_start():
    with connect() as db,db.transaction():
        row=db.execute("SELECT * FROM pl_installation WHERE key='entra' AND value->>'enabled'='true'").fetchone()
        if not row:fail('Microsoft sign-in has not been configured',503)
        cfg=row['value'];state=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
        db.execute('INSERT INTO pl_oidc VALUES (%s,%s,%s,%s,FALSE)',(HASH(state),nonce,seal(verifier),int(time.time())+600))
        callback=os.environ['PUBLIC_ORIGIN'].rstrip('/')+'/api/sso/callback'
        query=dict(client_id=cfg['client_id'],response_type='code',redirect_uri=callback,scope='openid profile',state=state,nonce=nonce,code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('='),code_challenge_method='S256',response_mode='query')
        response=RedirectResponse('https://login.microsoftonline.com/'+cfg['tenant_id']+'/oauth2/v2.0/authorize?'+urlencode(query))
        response.set_cookie('__Host-studio-oidc',state,secure=True,httponly=True,samesite='lax',max_age=600,path='/');return response

@router.get('/api/sso/callback')
def sso_callback(request:Request,code:str='',state:str=''):
    from ..app import COOKIE
    if not state or len(state)>200 or len(code)>12000 or not safe_compare(state,request.cookies.get('__Host-studio-oidc','')):fail('Sign-in state did not match',403)
    with connect() as db,db.transaction():
        pending=db.execute('UPDATE pl_oidc SET used=TRUE WHERE state_hash=%s AND NOT used AND expires_at>%s RETURNING *',(HASH(state),int(time.time()))).fetchone()
        configured=db.execute("SELECT * FROM pl_installation WHERE key='entra' AND value->>'enabled'='true'").fetchone()
        if not pending or not configured:fail('Sign-in expired or was already used',403)
        cfg=configured['value'];tenant=cfg['tenant_id'];callback=os.environ['PUBLIC_ORIGIN'].rstrip('/')+'/api/sso/callback'
        with httpx.Client(timeout=15,follow_redirects=False) as client:
            response=client.post('https://login.microsoftonline.com/'+tenant+'/oauth2/v2.0/token',data=dict(client_id=cfg['client_id'],client_secret=unseal(configured['secret_cipher']),grant_type='authorization_code',code=code,redirect_uri=callback,code_verifier=unseal(pending['verifier_cipher'])))
            if response.status_code!=200:fail('Microsoft did not authorize this sign-in',403)
            token=response.json().get('id_token','')
            if len(token)>20000:fail('Invalid identity token',403)
            keys=client.get('https://login.microsoftonline.com/'+tenant+'/discovery/v2.0/keys');keys.raise_for_status()
        try:
            header=jwt.get_unverified_header(token)
            key=next(k for k in keys.json()['keys'] if k.get('kid')==header.get('kid'))
            claims=jwt.decode(token,jwt.PyJWK.from_dict(key).key,algorithms=['RS256'],audience=cfg['client_id'],issuer='https://login.microsoftonline.com/'+tenant+'/v2.0',options={'require':['exp','iat','nonce','oid','tid','sub']})
            if claims['tid']!=tenant or not safe_compare(claims['nonce'],pending['nonce']):raise ValueError()
        except (jwt.PyJWTError,StopIteration,ValueError,KeyError):fail('Microsoft token validation failed',403)
        mapping=db.execute('SELECT a.username,u.enabled FROM pl_oidc_accounts a JOIN web_users u ON u.username=a.username WHERE tenant_id=%s AND object_id=%s',(tenant,claims['oid'])).fetchone()
        if not mapping or not mapping['enabled']:fail('This tenant identity has not been mapped to an enabled Studio account',403)
        username=mapping['username']
        factor=db.execute('SELECT enabled FROM pl_mfa WHERE username=%s',(username,)).fetchone()
        policy=db.execute("SELECT value FROM pl_installation WHERE key='security_policy'").fetchone()
        if factor and factor['enabled']:
            challenge=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(32)
            db.execute('INSERT INTO pl_sso_challenges(token_hash,username,csrf,expires_at) VALUES (%s,%s,%s,%s)',(HASH(challenge),username,csrf,int(time.time())+300))
            response=RedirectResponse('/?sso_mfa=1',status_code=303);response.set_cookie('__Host-studio-sso-factor',challenge,secure=True,httponly=True,samesite='strict',max_age=300,path='/');response.delete_cookie('__Host-studio-oidc',path='/');return response
        token=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(32);expires=int(time.time())+28800
        db.execute('INSERT INTO web_sessions VALUES (%s,%s,%s,%s)',(HASH(token),username,csrf,expires))
        db.execute('INSERT INTO pl_session_meta VALUES (%s,%s,%s,%s,%s)',(HASH(token),username,int(time.time()),bounded(request.headers.get('user-agent',''),500),'entra'))
        from ..experience import audit
        audit(db,username,'sso:login')
        response=RedirectResponse('/',status_code=303);response.set_cookie(COOKIE,token,max_age=28800,secure=True,httponly=True,samesite='strict',path='/');response.delete_cookie('__Host-studio-oidc',path='/');return response


@router.get('/api/sso/factor')
def sso_factor_state(request:Request):
    with connect() as db:
        row=db.execute('SELECT csrf FROM pl_sso_challenges WHERE token_hash=%s AND expires_at>%s AND attempts<5',(HASH(request.cookies.get('__Host-studio-sso-factor','')),int(time.time()))).fetchone()
        if not row:fail('Microsoft authenticator challenge expired',401)
        return {'csrf':row['csrf']}

@router.post('/api/sso/factor')
def sso_factor(body:dict,request:Request):
    from ..app import COOKIE
    with connect() as db:
        hashed=HASH(request.cookies.get('__Host-studio-sso-factor',''))
        with db.transaction():
            row=db.execute('UPDATE pl_sso_challenges SET attempts=attempts+1 WHERE token_hash=%s AND expires_at>%s AND attempts<5 RETURNING *',(hashed,int(time.time()))).fetchone()
        if not row or not safe_compare(request.headers.get('x-csrf-token',''),row['csrf']):fail('Microsoft authenticator challenge expired or invalid',403)
        with db.transaction():
            if not db.execute('SELECT 1 FROM web_users WHERE username=%s AND enabled',(row['username'],)).fetchone():fail('Account is disabled',403)
            if not verify_factor(db,row['username'],str(body.get('code',''))):fail('Enter a fresh authenticator or unused MFA recovery code',403)
            db.execute('DELETE FROM pl_sso_challenges WHERE token_hash=%s',(hashed,))
            token=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(32)
            db.execute('INSERT INTO web_sessions VALUES (%s,%s,%s,%s)',(HASH(token),row['username'],csrf,int(time.time())+28800))
            db.execute('INSERT INTO pl_session_meta VALUES (%s,%s,%s,%s,%s)',(HASH(token),row['username'],int(time.time()),request.headers.get('user-agent','')[:500],'entra+mfa'))
            response=JSONResponse({'username':row['username'],'csrf':csrf});response.set_cookie(COOKIE,token,secure=True,httponly=True,samesite='strict',max_age=28800,path='/');response.delete_cookie('__Host-studio-sso-factor',path='/');return response

def enrollment_required(db,username):
    policy=db.execute("SELECT value FROM pl_installation WHERE key='security_policy'").fetchone()
    if not policy or policy['value'].get('require_mfa') is not True:return False
    factor=db.execute('SELECT enabled FROM pl_mfa WHERE username=%s',(username,)).fetchone()
    return not (factor and factor['enabled'])

