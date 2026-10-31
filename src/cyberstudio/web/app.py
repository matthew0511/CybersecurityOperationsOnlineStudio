"""Authenticated browser/API service. Single-owner installation, multiple organizations."""
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

app = FastAPI(title='Cyber Security Operations Online Studio', docs_url=None, redoc_url=None, openapi_url=None)
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
    row = db.execute('SELECT * FROM web_sessions WHERE token_hash=%s AND expires_at>%s', (digest(token), now())).fetchone()
    if not row:
        raise HTTPException(401, 'Sign in required')
    if write and not hmac.compare_digest(request.headers.get('x-csrf-token', ''), row['csrf']):
        raise HTTPException(403, 'Refresh your session and retry')
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
            if not row or row['version'] != 1:
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
            db.execute('INSERT INTO web_users VALUES (%s,%s,%s)', (username, hasher.hash(password), now()))
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
        if not row or not verify_password(row['password_hash'], password):
            raise HTTPException(401, 'Invalid username or password')
        token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        with db.transaction():
            db.execute('DELETE FROM web_attempts WHERE key=%s', (digest('login:' + username),))
            db.execute('DELETE FROM web_sessions WHERE expires_at<=%s', (now(),))
            db.execute('INSERT INTO web_sessions VALUES (%s,%s,%s,%s)', (digest(token), username, csrf, now()+28800))
        response = JSONResponse({'username': username, 'csrf': csrf})
        response.set_cookie(COOKIE, token, max_age=28800, secure=True, httponly=True, samesite='strict', path='/')
        return response


@app.get('/api/me')
def me(request: Request):
    with connect() as db:
        user = principal(db, request)
        return {'username': user['username'], 'csrf': user['csrf']}


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
        svc = service(db)
        if operation == 'record_risk_decision':
            row = db.execute('SELECT password_hash FROM web_users WHERE username=%s',(user['username'],)).fetchone()
            svc.vault.reauthenticated = verify_password(row['password_hash'], str(body.get('reauth_password','')))
            arguments['operator_passphrase'] = 'authenticated-web-operator'
        try:
            with db.transaction():
                result = getattr(svc, operation)(**arguments)
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
        with db.transaction():
            if kind=='evidence':
                result = svc.add_evidence(org,str(form.get('title','')),file.filename or 'evidence',content,file.content_type or 'application/octet-stream',str(form.get('expires_on','')))
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
        principal(db,request)
        content=service(db).evidence_bytes(org,eid)
        return Response(content,media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="evidence.bin"'})


@app.get('/api/report/{org}/{kind}/{extension}')
def report(org: str, kind: str, extension: str, request: Request):
    from cyberstudio.reports_phase3 import export_executive_pdf, export_executive_xlsx
    from cyberstudio.governance_reports import board_packet
    if extension not in {'pdf','xlsx'} or kind not in {'executive','board'}:
        raise HTTPException(404,'Unknown report')
    with connect() as db:
        principal(db,request)
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


app.mount('/static', StaticFiles(directory=STATIC), name='static')


@app.get('/')
def home():
    return FileResponse(STATIC/'index.html')
