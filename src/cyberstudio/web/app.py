"""Authenticated browser/API service with organization-scoped team roles."""
from contextlib import contextmanager
import hashlib
import hmac
import inspect
import io
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
import typing

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from cyberstudio.service import ValidationError, NotFoundError
from cyberstudio.enterprise import EnterpriseGovernanceService
from cyberstudio.web.database import connect, service
from cyberstudio.web.experience import router as experience_router, authorize, require_owner, tick
from cyberstudio.web.platform.router import router as platform_router
from cyberstudio.web.platform.security import router as security_router
from cyberstudio.web.platform.auditor import router as auditor_router
import threading
from contextlib import asynccontextmanager
import logging


@asynccontextmanager
async def lifespan(app):
    stop = threading.Event()
    def scheduled_work():
        while not stop.is_set():
            try:
                with connect() as db, db.transaction():
                    from .platform.schema import system_actor
                    from .platform.jobs import tick as platform_tick
                    system_actor(db)
                    tick(db)
                    platform_tick(db)
            except Exception:
                logging.getLogger(__name__).warning('Scheduled snapshot/reminder pass failed; retrying next minute')
            stop.wait(60)
    thread = None
    if os.getenv('DB_HOST') and not os.getenv('TEST_DATABASE_URL'):
        thread = threading.Thread(target=scheduled_work, daemon=True)
        thread.start()
    yield
    stop.set()


app = FastAPI(lifespan=lifespan, title='Cyber Security Operations Online Studio', docs_url=None, redoc_url=None, openapi_url=None)
hasher = PasswordHasher()
COOKIE = '__Host-studio'
STATIC = Path(__file__).parent / 'static'

# Deliberate public-operation surface; no arbitrary attribute access or SQL API.
READS = set('list_organizations organization overview list_assessments questions list_risks list_tasks task_history audit_events framework_catalogs framework_controls list_templates template_questions template_mappings assessment_mappings residual_risk risk_decisions acceptance_state evidence evidence_links import_history control_evaluations vendors imported_vendor_annotations vendor_reviews vulnerabilities executive_metrics imported_control_inventory policies incidents import_history_p3 frameworks implementations initiatives board_snapshot board_reports board_decisions changes change_reviews change_checks audits findings governance_events governance_metrics change_calendar approval_policy approval_votes evidence_inventory calendar_month'.split())
WRITES = set('save_questionnaire_response create_organization create_assessment answer_question add_risk add_task update_task_status create_template add_template_question create_starter_template set_residual_risk record_risk_decision link_evidence review_evidence set_evidence_expiration evaluate_control create_vendor record_vendor_review add_vulnerability update_vulnerability configure_framework upsert_implementation upsert_initiative publish_board_snapshot add_board_decision create_change set_change_plan review_change add_change_check transition_change create_audit update_audit_status add_finding update_finding set_approval_policy record_cab_vote review_custody_evidence link_custody_evidence'.split())
ALLOWED = READS | WRITES


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def now():
    return int(time.time())


@app.middleware('http')
async def headers(request, call_next):
    if int(request.headers.get('content-length', '0') or '0') > 7 * 1024 * 1024:
        return JSONResponse({'detail': 'Request exceeds 7 MiB'}, status_code=413)
    response = await call_next(request)
    response.headers.update({
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
        'Strict-Transport-Security': 'max-age=31536000',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'})
    return response


@app.exception_handler(ValidationError)
async def validation(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=422)


@app.exception_handler(NotFoundError)
async def missing(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=404)


def limit(db, key):
    key = digest(key)
    db.execute("INSERT INTO web_attempts VALUES (%s,%s,0) ON CONFLICT(key) DO NOTHING", (key, now()))
    row = db.execute('SELECT * FROM web_attempts WHERE key=%s FOR UPDATE', (key,)).fetchone()
    if now() - row['started_at'] >= 900:
        db.execute('UPDATE web_attempts SET started_at=%s, failures=0 WHERE key=%s', (now(), key))
    elif row['failures'] >= 5:
        raise HTTPException(429, 'Too many attempts. Try again in 15 minutes.')
    db.execute('UPDATE web_attempts SET failures=failures+1 WHERE key=%s', (key,))


def principal(db, request, *, write=False):
    token = request.cookies.get(COOKIE, '')
    row = db.execute('SELECT s.*,u.role FROM web_sessions s JOIN web_users u ON u.username=s.username WHERE s.token_hash=%s AND s.expires_at>%s AND u.enabled', (digest(token), now())).fetchone()
    if not row:
        raise HTTPException(401, 'Sign in required')
    if write and not hmac.compare_digest(request.headers.get('x-csrf-token', ''), row['csrf']):
        raise HTTPException(403, 'Refresh your session and retry')
    from .platform.security import enrollment_required
    if enrollment_required(db,row['username']) and not (request.url.path.startswith('/api/security') or request.url.path in {'/api/me','/api/logout'}):
        raise HTTPException(403,'Enroll an authenticator in Account security before accessing organization data')
    from .platform.schema import actor
    actor(db,row['username'])
    return row


def verify_password(encoded, password):
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, ValueError):
        return False


@app.get('/healthz')
def health():
    return {'status': 'ok'}


@app.get('/readyz')
def ready():
    try:
        with connect() as db:
            row = db.execute("SELECT version FROM web_schema WHERE name='web'").fetchone()
            if not row or row['version'] != 1 or not db.execute("SELECT 1 FROM web_schema WHERE name='platform' AND version=1").fetchone():
                raise RuntimeError('Schema unavailable')
        return {'status': 'ready', 'database': 'connected'}
    except Exception:
        raise HTTPException(503, 'Database or schema unavailable') from None


@app.get('/api/status')
def status():
    with connect() as db:
        return {'setup_required': not bool(db.execute('SELECT 1 FROM web_users LIMIT 1').fetchone())}


@app.post('/api/setup')
def setup(body: dict, request: Request):
    with connect() as db:
        with db.transaction():
            limit(db, 'setup')
        with db.transaction():
            db.execute('SELECT pg_advisory_xact_lock(747103092)')
            if db.execute('SELECT 1 FROM web_users LIMIT 1').fetchone():
                raise HTTPException(409, 'Owner account already configured')
            expected = os.environ.get('SETUP_TOKEN', '')
            if not expected or not hmac.compare_digest(str(body.get('code', '')), expected):
                raise HTTPException(403, 'Invalid setup code')
            username, password = str(body.get('username', '')).lower(), str(body.get('password', ''))
            if not re.fullmatch(r'[a-z0-9_.@-]{3,100}', username) or not 16 <= len(password) <= 256:
                raise HTTPException(422, 'Use a valid username and a password of 16–256 characters')
            db.execute("INSERT INTO web_users(username,password_hash,created_at,role) VALUES (%s,%s,%s,'owner')", (username, hasher.hash(password), now()))
    return {'status': 'Owner created. Sign in to continue.'}


@app.post('/api/login')
def login(body: dict, request: Request):
    username, password = str(body.get('username', '')).lower(), str(body.get('password', ''))
    if len(username)>100 or len(password)>256:
        raise HTTPException(401, 'Invalid username or password')
    with connect() as db:
        with db.transaction():
            limit(db, 'login:' + username)
        row = db.execute('SELECT * FROM web_users WHERE username=%s', (username,)).fetchone()
        if not row or not row['enabled'] or not verify_password(row['password_hash'], password):
            raise HTTPException(401, 'Invalid username or password')
        from .platform.security import login_factor
        login_factor(db,row,body)
        token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        with db.transaction():
            db.execute('DELETE FROM web_attempts WHERE key=%s', (digest('login:' + username),))
            db.execute('DELETE FROM web_sessions WHERE expires_at<=%s', (now(),))
            db.execute('INSERT INTO web_sessions VALUES (%s,%s,%s,%s)', (digest(token), username, csrf, now()+28800))
            db.execute('INSERT INTO pl_session_meta VALUES (%s,%s,%s,%s,%s)',(digest(token),username,now(),request.headers.get('user-agent','')[:500],'password+mfa' if body.get('mfa_code') else 'password'))
        from .platform.security import enrollment_required
        response = JSONResponse({'username': username, 'csrf': csrf,'enrollment_required':enrollment_required(db,username)})
        response.set_cookie(COOKIE, token, max_age=28800, secure=True, httponly=True, samesite='strict', path='/')
        return response


@app.get('/api/me')
def me(request: Request):
    with connect() as db:
        user = principal(db, request)
        from .platform.security import enrollment_required
        return {'username': user['username'], 'csrf': user['csrf'], 'role': user['role'],'enrollment_required':enrollment_required(db,user['username'])}


@app.post('/api/logout')
def logout(request: Request):
    with connect() as db:
        user = principal(db, request, write=True)
        db.execute('DELETE FROM web_sessions WHERE token_hash=%s', (user['token_hash'],))
    response = JSONResponse({'status': 'Signed out'})
    response.delete_cookie(COOKIE, path='/', secure=True, httponly=True, samesite='strict')
    return response


def fields(name):
    fn = getattr(EnterpriseGovernanceService, name)
    result = []
    hints = typing.get_type_hints(fn)
    for p in inspect.signature(fn).parameters.values():
        if p.name in {'self', 'operator_passphrase'}:
            continue
        annotation = hints.get(p.name)
        kind = 'boolean' if annotation is bool or isinstance(p.default, bool) or p.name in {'enabled','attested','require_separation'} else 'integer' if annotation is int or p.name in {'likelihood','impact','year','month','normal_quorum','emergency_quorum'} else 'number' if p.name in {'budget_amount','actual_amount','cvss'} else 'string'
        default = None if p.default is inspect.Parameter.empty else p.default
        result.append({'name': p.name, 'kind': kind, 'required': p.default is inspect.Parameter.empty, 'default': default})
    return result


@app.get('/api/operations')
def operations(request: Request):
    with connect() as db:
        principal(db, request)
    return {name: {'write': name in WRITES, 'fields': fields(name)} for name in sorted(ALLOWED)}


@app.post('/api/call/{operation}')
def call(operation: str, body: dict, request: Request):
    if operation not in ALLOWED:
        raise HTTPException(404, 'Unknown operation')
    with connect() as db:
        user = principal(db, request, write=True)
        arguments = body.get('arguments', {})
        if not isinstance(arguments, dict):
            raise HTTPException(422, 'Arguments must be an object')
        definitions = fields(operation)
        if set(arguments) - {f['name'] for f in definitions}:
            raise HTTPException(422, 'Unsupported argument')
        for field in definitions:
            name = field['name']
            if name not in arguments:
                if field['required']:
                    raise HTTPException(422, 'Missing field: '+name)
                continue
            value = arguments[name]
            if field['kind']=='boolean' and not isinstance(value, bool):
                raise HTTPException(422, name+' must be boolean')
            if field['kind'] in {'integer','number'} and (isinstance(value,bool) or not isinstance(value,(int,float)) or (field['kind']=='integer' and not isinstance(value,int))):
                raise HTTPException(422, name+' must be numeric')
            if field['kind']=='string' and value is not None and not isinstance(value,(str,list)):
                raise HTTPException(422, name+' must be text')
            if isinstance(value,str) and len(value)>12000:
                raise HTTPException(422, name+' is too long')
        if operation=='create_organization':
            require_owner(user)
        elif arguments.get('org'):
            authorize(db,user,arguments['org'],operation in WRITES,operation)
        elif operation not in {'list_organizations','framework_catalogs','framework_controls'}:
            require_owner(user)
        svc = service(db)
        if operation == 'record_risk_decision':
            row = db.execute('SELECT password_hash FROM web_users WHERE username=%s',(user['username'],)).fetchone()
            svc.vault.reauthenticated = verify_password(row['password_hash'], str(body.get('reauth_password','')))
            arguments['operator_passphrase'] = 'authenticated-web-operator'
        try:
            with db.transaction():
                if operation in {'save_questionnaire_response','answer_question'}:
                    aid=arguments.get('assessment','')
                    locked=db.execute("SELECT state FROM xp_assessments WHERE assessment_id=%s AND organization_id=%s",(aid,arguments.get('org',''))).fetchone()
                    if locked and locked['state'] in {'submitted','approved'}:
                        raise HTTPException(409,'Reopen this questionnaire before changing answers')
                if operation=='update_task_status' and arguments.get('new_status')=='done':
                    if db.execute("SELECT 1 FROM xp_dependencies d JOIN remediation_tasks t ON t.id=d.depends_on WHERE d.task_id=%s AND d.organization_id=%s AND t.status<>'done'",(arguments.get('tid',''),arguments.get('org',''))).fetchone():
                        raise HTTPException(409,'Finish prerequisite tasks first')
                result = getattr(svc, operation)(**arguments)
                if operation=='list_organizations' and user['role']!='owner':
                    allowed={r['organization_id'] for r in db.execute('SELECT organization_id FROM xp_memberships WHERE username=%s',(user['username'],)).fetchall()}
                    result=[r for r in result if r['id'] in allowed]
                if operation in {'save_questionnaire_response','answer_question'}:
                    db.execute('INSERT INTO xp_response_versions(assessment_id,code,version) VALUES (%s,%s,1) ON CONFLICT(assessment_id,code) DO UPDATE SET version=xp_response_versions.version+1',(arguments['assessment'],arguments['code']))
                if operation in WRITES:
                    db.execute('INSERT INTO web_request_audit(username,operation) VALUES (%s,%s)', (user['username'],operation))
        except (TypeError, ValueError) as exc:
            if isinstance(exc, ValidationError):
                raise
            raise HTTPException(422, 'Invalid operation arguments') from None
        return {'result': result}


@app.post('/api/upload/{kind}')
async def upload(kind: str, request: Request):
    # Bound the complete body before multipart parsing (API Gateway limit is 10 MiB).
    raw = await request.body()
    if len(raw) > 7*1024*1024:
        raise HTTPException(413, 'Upload too large')
    form = await request.form(max_files=1, max_fields=12, max_part_size=6*1024*1024)
    file = form.get('file')
    if not file or not hasattr(file,'read'):
        raise HTTPException(422, 'Select a file')
    content = await file.read(5*1024*1024+1)
    if len(content)>5*1024*1024:
        raise HTTPException(413, 'File exceeds 5 MiB')
    with connect() as db:
        user = principal(db, request, write=True)
        svc = service(db)
        org = str(form.get('org',''))
        authorize(db,user,org,True,'link_evidence' if kind=='evidence' else 'import')
        with db.transaction():
            if kind=='evidence':
                from .platform.quarantine import submit
                assessment=str(form.get('assessment',''));code=str(form.get('code',''))
                if assessment:
                    svc._exists('assessments',assessment,org)
                    if not db.execute('SELECT 1 FROM assessment_questions WHERE organization_id=%s AND assessment_id=%s AND code=%s',(org,assessment,code)).fetchone():raise HTTPException(422,'Select a question in this assessment')
                result=submit(db,org,user['username'],file.filename or 'evidence',content,{'title':str(form.get('title','')),'mime_type':file.content_type or 'application/octet-stream','expires_on':str(form.get('expires_on','')),'assessment':assessment,'code':code,'group_id':str(form.get('group_id',''))})
            elif kind in {'preview','import'}:
                module = str(form.get('module','risks'))
                if kind=='import' and form.get('confirmed')!='true':
                    raise HTTPException(422, 'Confirm the preview before importing')
                if module=='risks':
                    result=svc.preview_notion_csv(org,content) if kind=='preview' else svc.import_notion_csv(org,content,file.filename or 'import.csv',confirmed=True)
                else:
                    result=svc.preview_notion_module(org,content,module) if kind=='preview' else svc.import_notion_module(org,content,module,file.filename or 'import.csv',confirmed=True)
            else:
                raise HTTPException(404,'Unsupported upload')
            db.execute('INSERT INTO web_request_audit(username,operation) VALUES (%s,%s)',(user['username'],'upload:'+kind))
        return {'result':result}


@app.get('/api/evidence/{org}/{eid}')
def download_evidence(org: str, eid: str, request: Request):
    with connect() as db:
        user=principal(db,request)
        authorize(db,user,org)
        content=service(db).evidence_bytes(org,eid)
        return Response(content,media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="evidence.bin"'})


@app.get('/api/report-branding/{org}')
def report_branding(org: str, request: Request):
    with connect() as db:
        user=principal(db,request)
        authorize(db,user,org)
        brand=service(db).report_branding(org)
        return {**{k:v for k,v in brand.items() if k!='logo'},'has_logo':bool(brand['logo']),'can_edit':user['role']=='owner'}


@app.get('/api/report-branding/{org}/logo')
def report_logo(org: str, request: Request):
    with connect() as db:
        user=principal(db,request)
        authorize(db,user,org)
        content=service(db).report_branding(org)['logo']
        if not content:raise HTTPException(404,'No report logo uploaded')
        return Response(content,media_type='image/png')


@app.post('/api/report-branding/{org}')
async def save_report_branding(org: str, request: Request):
    # Authenticate before accepting multipart uploads; the global body limit also applies.
    with connect() as db:
        user=principal(db,request,write=True)
        authorize(db,user,org,True)
        require_owner(user)
        raw=await request.body()
        if len(raw)>3*1024*1024:raise HTTPException(413,'Branding upload exceeds 3 MiB')
        form=await request.form(max_files=1,max_fields=8,max_part_size=2*1024*1024)
        if set(form)-{'display_name','tagline','primary_color','accent_color','footer_note','logo','remove_logo'}:
            raise HTTPException(422,'Unsupported branding field')
        file=form.get('logo');content=None
        if file and hasattr(file,'read') and file.filename:
            content=await file.read(2*1024*1024+1)
            if len(content)>2*1024*1024:raise HTTPException(413,'Logo exceeds 2 MiB')
        with db.transaction():
            result=service(db).save_report_branding(org,
                str(form.get('display_name','')),str(form.get('tagline','')),
                str(form.get('primary_color','')),str(form.get('accent_color','')),
                str(form.get('footer_note','')),logo=content,remove_logo=form.get('remove_logo')=='true')
            db.execute('INSERT INTO web_request_audit(username,operation) VALUES (%s,%s)',(user['username'],'report_branding:update'))
        return {'status':'saved',**result,'has_logo':bool(service(db).report_branding(org)['logo'])}


@app.get('/api/report/{org}/{kind}/{extension}')
def report(org: str, kind: str, extension: str, request: Request):
    from cyberstudio.reports_phase3 import export_executive_pdf, export_executive_xlsx
    from cyberstudio.governance_reports import board_packet
    if extension not in {'pdf','xlsx'} or kind not in {'executive','board'}:
        raise HTTPException(404,'Unknown report')
    with connect() as db:
        user=principal(db,request)
        authorize(db,user,org,operation='reports:export')
        svc=service(db)
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/('report.'+extension)
            with db.transaction():
                if kind=='board':board_packet(svc,org,dest)
                elif extension=='pdf':export_executive_pdf(svc,org,dest)
                else:export_executive_xlsx(svc,org,dest)
            data=dest.read_bytes()
    mime='application/pdf' if extension=='pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return Response(data,media_type=mime,headers={'Content-Disposition':f'attachment; filename="{kind}.{extension}"'})


app.include_router(experience_router)
app.include_router(platform_router)
app.include_router(security_router)
app.include_router(auditor_router)

app.mount('/static', StaticFiles(directory=STATIC), name='static')


@app.get('/')
def home():
    return FileResponse(STATIC/'index.html')

@app.exception_handler(__import__('httpx').HTTPError)
async def provider_unavailable(request,exc):
    return JSONResponse({'detail':'The identity or integration provider is unavailable. Retry later; no provider response bodies or credentials are exposed.'},status_code=503)
