"""Authenticated program, integrations and reporting APIs with explicit capability gates."""
from datetime import date,datetime,timezone,timedelta
import hashlib,json,secrets,time,os
from pathlib import Path
from fastapi import APIRouter,Request
from fastapi.responses import Response,FileResponse
from . import catalog,store,workflows,connectors,reporting
from .schema import actor,system_actor
from .security import HASH,reauthenticate,current,seal
from ..database import connect,service

router=APIRouter()
STATIC=Path(__file__).parents[1]/'static'

def session(db,request,org=None,write=False,cap='records:read'):
    user=current(db,request,write)
    if org:store.access(db,user,org,write,cap)
    return user

def owner(user):
    from ..experience import require_owner
    require_owner(user)

def table_rows(db,query,args=()):return [dict(r) for r in db.execute(query,args).fetchall()]

def clean(row):return {k:v for k,v in dict(row).items() if k not in {'secret_cipher','content','token_hash'}}

@router.get('/documentation')
def documentation_page():return FileResponse(STATIC/'documentation.html')

@router.get('/audit-room')
def auditor_page():return FileResponse(STATIC/'audit-room.html')

@router.get('/api/platform/documentation')
def docs(request:Request):
    with connect() as db:
        session(db,request)
        from .documentation import documentation
        return documentation()

@router.get('/api/platform/catalog')
def platform_catalog(request:Request):
    with connect() as db:
        user=session(db,request)
        return {'features':catalog.features(),'modules':catalog.modules(),'providers':connectors.PROVIDERS,'report_templates':reporting.TEMPLATES,'role':user['role'],'security_key_ready':bool(os.getenv('AUTH_ENCRYPTION_KEY')),'scanner_ready':bool(os.getenv('SCAN_BUCKET'))}

@router.get('/api/platform/operations')
def operations(request:Request):
    with connect() as db:
        user=session(db,request);owner(user)
        return {'checks':table_rows(db,'SELECT kind,result,recorded_at FROM pl_operations ORDER BY recorded_at DESC LIMIT 30'),'runtime':{'security_key_configured':bool(os.getenv('AUTH_ENCRYPTION_KEY')),'scanner_bucket_configured':bool(os.getenv('SCAN_BUCKET'))},'note':'Configuration flags do not prove a scan, restore or external delivery succeeded. Check the dated validation results.'}

@router.get('/api/platform/portfolio')
def portfolio(request:Request):
    with connect() as db:
        user=session(db,request);svc=service(db);rows=svc.list_organizations();result=[]
        for org in rows:
            if user['role']!='owner' and not db.execute('SELECT 1 FROM xp_memberships WHERE username=%s AND organization_id=%s',(user['username'],org['id'])).fetchone():continue
            actor(db,user['username'],org['id']);metrics=svc.overview(org['id'])
            result.append({'id':org['id'],'name':org['name'],'metrics':metrics,'program_records':db.execute('SELECT count(*) AS n FROM pl_records WHERE organization_id=%s AND deleted_at IS NULL',(org['id'],)).fetchone()['n']})
        return result

@router.get('/api/platform/{org}/overview')
def overview(org:str,request:Request):
    with connect() as db:
        user=session(db,request,org)
        counts=table_rows(db,'SELECT kind,count(*) AS total,count(*) FILTER(WHERE due_on<CURRENT_DATE AND status NOT IN (\'completed\',\'closed\')) AS overdue FROM pl_records WHERE organization_id=%s AND deleted_at IS NULL GROUP BY kind',(org,))
        return {'counts':counts,'executions':table_rows(db,'SELECT id,title,status,version,updated_at FROM pl_executions WHERE organization_id=%s ORDER BY updated_at DESC LIMIT 30',(org,)),'quarantine':table_rows(db,'SELECT id,filename,status,indicators,result,created_at FROM pl_quarantine WHERE organization_id=%s ORDER BY created_at DESC LIMIT 50',(org,)),'editions':table_rows(db,'SELECT id,title,format,template,sha256,created_by,created_at FROM pl_editions WHERE organization_id=%s ORDER BY created_at DESC LIMIT 50',(org,)),'demo':bool(db.execute('SELECT 1 FROM pl_demo WHERE organization_id=%s',(org,)).fetchone()),'role':user['role']}

@router.get('/api/platform/{org}/records/{kind}')
def records(org:str,kind:str,request:Request,q:str='',offset:int=0):
    if kind not in catalog.MODULES:store.fail('Unsupported module',404)
    with connect() as db:
        session(db,request,org)
        if not 0<=offset<=2147483647 or len(q)>100:store.fail('Invalid search or page')
        return table_rows(db,'SELECT * FROM pl_records WHERE organization_id=%s AND kind=%s AND deleted_at IS NULL AND title ILIKE %s ORDER BY updated_at DESC LIMIT 100 OFFSET %s',(org,kind,'%'+q+'%',offset))

@router.get('/api/platform/{org}/record/{ident}')
def record_details(org:str,ident:str,request:Request):
    with connect() as db:
        session(db,request,org);record=store.get(db,org,ident)
        return {'record':record,'history':table_rows(db,'SELECT actor,action,snapshot,recorded_at FROM pl_history WHERE organization_id=%s AND record_id=%s ORDER BY id DESC LIMIT 100',(org,ident)),'acknowledgments':table_rows(db,'SELECT version,username,recorded_at FROM pl_attestations WHERE organization_id=%s AND record_id=%s ORDER BY recorded_at DESC',(org,ident))}

@router.post('/api/platform/{org}/records/{kind}')
def save_record(org:str,kind:str,body:dict,request:Request):
    with connect() as db,db.transaction():return store.save(db,session(db,request,org,True,'records:approve' if kind=='op_access' else 'records:write'),org,kind,body)

@router.post('/api/platform/{org}/record/{ident}/{action}')
def record_action(org:str,ident:str,action:str,body:dict,request:Request):
    with connect() as db,db.transaction():
        session(db,request,org)
        target=store.get(db,org,ident)
        user=session(db,request,org,True,'policy:acknowledge' if action=='acknowledge' else 'records:approve' if action=='status' and (target['kind']=='op_access' or body.get('status') in ('approved','rejected')) else 'records:write')
        if action=='status':return store.transition(db,user,org,ident,body)
        if action=='execute':return workflows.execute(db,user,org,ident)
        if action=='reuse_answer':return workflows.reuse(db,user,org,ident,str(body.get('assessment_id','')),str(body.get('code','')))
        if action=='acknowledge':
            record=store.get(db,org,ident,'policy')
            if record['status'] not in {'approved','active'} or body.get('version')!=record['version'] or body.get('confirmed') is not True:store.fail('Confirm acknowledgment of the current approved policy version')
            db.execute('INSERT INTO pl_attestations VALUES (%s,%s,%s,%s,CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING',(org,ident,record['version'],user['username']));store.history(db,org,ident,user['username'],'policy:acknowledged',{'version':record['version']});return {'saved':True}
        if action=='archive':return workflows.trash(db,user,org,'program',ident)
        store.fail('Unknown record action',404)

@router.get('/api/platform/{org}/choices/{kind}')
def choices(org:str,kind:str,request:Request):
    with connect() as db:
        session(db,request,org)
        if kind.startswith('legacy:'):
            from psycopg import sql
            name=kind.split(':',1)[1];table=store.LEGACY.get(name)
            if not table:store.fail('Unknown reference type')
            field='name' if name=='vendor' else 'title'
            return table_rows(db,sql.SQL('SELECT id,{} AS title FROM {} WHERE organization_id=%s ORDER BY {} LIMIT 1000').format(sql.Identifier(field),sql.Identifier(table),sql.Identifier(field)),(org,))
        if kind not in catalog.MODULES:store.fail('Unknown reference type')
        return table_rows(db,'SELECT id,title,status FROM pl_records WHERE organization_id=%s AND kind=%s AND deleted_at IS NULL ORDER BY title LIMIT 1000',(org,kind))

@router.get('/api/platform/{org}/executions/{ident}')
def execution(org:str,ident:str,request:Request):
    with connect() as db:
        session(db,request,org);row=db.execute('SELECT * FROM pl_executions WHERE organization_id=%s AND id=%s',(org,ident)).fetchone()
        if not row:store.fail('Execution not found',404)
        return dict(row)

@router.post('/api/platform/{org}/executions/{ident}')
def execution_step(org:str,ident:str,body:dict,request:Request):
    with connect() as db,db.transaction():return workflows.step(db,session(db,request,org,True,'records:write'),org,ident,body)

@router.post('/api/platform/{org}/compare')
def comparison(org:str,body:dict,request:Request):
    with connect() as db:session(db,request,org,True);return workflows.compare(db,org,str(body.get('before','')),str(body.get('after','')))

@router.post('/api/platform/{org}/bulk-tasks')
def bulk_tasks(org:str,body:dict,request:Request):
    with connect() as db,db.transaction():return workflows.bulk(db,session(db,request,org,True,'tasks:write'),org,body)

@router.get('/api/platform/{org}/trash')
def recycle_bin(org:str,request:Request):
    with connect() as db:session(db,request,org);return table_rows(db,'SELECT * FROM pl_trash WHERE organization_id=%s ORDER BY deleted_at DESC LIMIT 200',(org,))

@router.post('/api/platform/{org}/trash')
def archive(org:str,body:dict,request:Request):
    with connect() as db,db.transaction():return workflows.trash(db,session(db,request,org,True,'records:delete'),org,str(body.get('kind','')),str(body.get('id','')),body.get('restore') is True)

@router.get('/api/platform/{org}/catalogs')
def catalogs(org:str,request:Request):
    with connect() as db:session(db,request,org);return table_rows(db,'SELECT *, (SELECT count(*) FROM pl_controls c WHERE c.catalog_id=pl_catalogs.id AND c.organization_id=pl_catalogs.organization_id) AS control_count FROM pl_catalogs WHERE organization_id=%s ORDER BY created_at DESC',(org,))

@router.get('/api/platform/{org}/catalogs/{ident}')
def catalog_controls(org:str,ident:str,request:Request):
    with connect() as db:session(db,request,org);return table_rows(db,'SELECT code,title,parent_code FROM pl_controls WHERE organization_id=%s AND catalog_id=%s ORDER BY code',(org,ident))

@router.post('/api/platform/{org}/catalogs')
async def import_catalog(org:str,request:Request):
    with connect() as db,db.transaction():
        user=session(db,request,org,True);owner(user);form=await request.form(max_files=1,max_fields=6,max_part_size=2*1024*1024);file=form.get('file')
        if not file or not hasattr(file,'read'):store.fail('Choose a catalog CSV')
        raw=await file.read(2*1024*1024+1)
        return workflows.catalog_import(db,user,org,raw,str(form.get('name','')),str(form.get('edition','')),str(form.get('source','')),str(form.get('license_note','')),form.get('confirmed')=='true')

@router.get('/api/platform/{org}/variance')
def variance(org:str,request:Request):
    with connect() as db:session(db,request,org);return reporting.variance(db,org)

@router.post('/api/platform/{org}/editions')
def create_edition(org:str,body:dict,request:Request):
    with connect() as db,db.transaction():return reporting.freeze(db,session(db,request,org,True,'reports:export'),org,body)

@router.get('/api/platform/{org}/editions/{ident}')
def edition(org:str,ident:str,request:Request,inline:bool=False):
    with connect() as db:
        session(db,request,org,False,'reports:export');row=db.execute('SELECT * FROM pl_editions WHERE organization_id=%s AND id=%s',(org,ident)).fetchone()
        if not row:store.fail('Report edition not found',404)
        return Response(bytes(row['content']),media_type=reporting.MIMES[row['format']],headers={'Content-Disposition':('inline' if inline and row['format']=='pdf' else 'attachment')+'; filename="report-'+ident+'.'+row['format']+'"','X-Content-SHA256':row['sha256']})

@router.get('/api/platform/{org}/evidence-versions')
def versions(org:str,request:Request):
    with connect() as db:session(db,request,org);return table_rows(db,'SELECT * FROM pl_evidence_versions WHERE organization_id=%s ORDER BY created_at DESC LIMIT 200',(org,))

@router.post('/api/platform/{org}/quarantine/{ident}/release')
def release_artifact(org:str,ident:str,body:dict,request:Request):
    from .quarantine import release
    with connect() as db,db.transaction():
        user=session(db,request,org,True,'evidence:upload');owner(user);reauthenticate(db,user,body);row=db.execute('SELECT * FROM pl_quarantine WHERE organization_id=%s AND id=%s',(org,ident)).fetchone()
        if not row:store.fail('Upload not found',404)
        return {'evidence_id':release(db,dict(row),user['username'],str(body.get('reason','')))}

@router.get('/api/platform/{org}/integrations')
def integration_list(org:str,request:Request):
    with connect() as db:
        user=session(db,request,org);owner(user)
        return {'providers':connectors.PROVIDERS,'connections':[connectors.public(dict(r)) for r in db.execute('SELECT * FROM pl_integrations WHERE organization_id=%s ORDER BY name',(org,)).fetchall()],'jobs':table_rows(db,'SELECT id,kind,status,attempts,result,created_at,updated_at FROM pl_jobs WHERE organization_id=%s ORDER BY created_at DESC LIMIT 100',(org,))}

@router.post('/api/platform/{org}/integrations')
def configure_integration(org:str,body:dict,request:Request):
    with connect() as db,db.transaction():return connectors.save(db,session(db,request,org,True,'integrations:manage'),org,body)

@router.post('/api/platform/{org}/integrations/{ident}/{action}')
def integration_action(org:str,ident:str,action:str,body:dict,request:Request):
    with connect() as db,db.transaction():
        user=session(db,request,org,True,'integrations:manage');owner(user);row=db.execute('SELECT * FROM pl_integrations WHERE organization_id=%s AND id=%s FOR UPDATE',(org,ident)).fetchone()
        if not row:store.fail('Connection not found',404)
        row=dict(row)
        if action=='test':
            try:
                with connectors.Adapter(row) as adapter:result=adapter.identity()
            except Exception:
                # Never include response bodies, authorization headers or credential values in logs.
                db.execute("UPDATE pl_integrations SET connection_status='test_failed',enabled=FALSE,last_test_at=CURRENT_TIMESTAMP WHERE id=%s",(ident,))
                return {'authenticated':False,'message':'Provider connection test failed. Check credentials, provider availability and least-privilege consent.'}
            db.execute("UPDATE pl_integrations SET connection_status='authenticated',last_test_at=CURRENT_TIMESTAMP WHERE id=%s",(ident,));return result
        if action=='enable':
            if row['connection_status']!='authenticated':store.fail('A successful connection test is required before enabling',409)
            db.execute('UPDATE pl_integrations SET enabled=%s WHERE id=%s',(body.get('enabled') is True,ident));return {'saved':True}
        if action in {'pull','publish','notify'}:
            if not row['enabled'] or row['connection_status']!='authenticated':store.fail('Test and enable this connection first',409)
            if action in {'publish','notify'} and body.get('confirmed') is not True:store.fail('Review the destination and content, then explicitly confirm the external action')
            payload={'integration_id':ident,'title':store.bounded(body.get('title',''),250),'message':store.bounded(body.get('message',''),10000),'recipients':body.get('recipients',[])}
            job=store.uid();db.execute('INSERT INTO pl_jobs(id,organization_id,kind,payload) VALUES (%s,%s,%s,%s::jsonb)',(job,org,'integration:'+action,json.dumps(payload)));store.history(db,org,ident,user['username'],'integration:'+action+':queued',{'job_id':job});return {'job_id':job,'status':'queued'}
        store.fail('Unsupported integration action',404)

@router.get('/api/platform/{org}/integrations/{ident}/staged')
def staged(org:str,ident:str,request:Request):
    with connect() as db:
        user=session(db,request,org);owner(user)
        return table_rows(db,'SELECT external_id,payload,source_hash,promoted_id,updated_at FROM pl_external WHERE organization_id=%s AND integration_id=%s ORDER BY updated_at DESC LIMIT 100',(org,ident))

@router.post('/api/platform/{org}/integrations/{ident}/promote')
def promote(org:str,ident:str,body:dict,request:Request):
    with connect() as db,db.transaction():
        user=session(db,request,org,True,'integrations:manage');owner(user)
        row=db.execute('SELECT e.*,i.provider FROM pl_external e JOIN pl_integrations i ON i.id=e.integration_id WHERE e.organization_id=%s AND e.integration_id=%s AND e.external_id=%s FOR UPDATE OF e',(org,ident,str(body.get('external_id','')))).fetchone()
        if not row or row['source_hash']!=body.get('source_hash'):store.fail('The staged source changed; review it again',409)
        if row['promoted_id']:return {'id':row['promoted_id'],'already_imported':True}
        kind=connectors.PROVIDERS[row['provider']]['destination'];record=store.save(db,user,org,kind,{'title':body.get('title',''),'owner':body.get('owner',''),'data':body.get('data',{})})
        db.execute('UPDATE pl_external SET promoted_id=%s WHERE organization_id=%s AND integration_id=%s AND external_id=%s',(record['id'],org,ident,row['external_id']));return record

@router.post('/api/platform/{org}/capabilities')
def capabilities(org:str,body:dict,request:Request):
    allowed={'records:write','records:approve','records:delete','evidence:upload','reports:export','integrations:manage','tasks:write'}
    with connect() as db,db.transaction():
        user=session(db,request,org,True);owner(user);reauthenticate(db,user,body);username=str(body.get('username',''));denied=body.get('denied',[])
        if not isinstance(denied,list) or not all(isinstance(v,str) for v in denied) or set(denied)-allowed:store.fail('Choose supported capability restrictions')
        if not db.execute('SELECT 1 FROM xp_memberships WHERE organization_id=%s AND username=%s',(org,username)).fetchone():store.fail('Choose a current organization member')
        db.execute('INSERT INTO pl_capabilities VALUES (%s,%s,%s::jsonb) ON CONFLICT(organization_id,username) DO UPDATE SET denied=EXCLUDED.denied',(org,username,json.dumps(denied)));store.history(db,org,username,user['username'],'permissions:restricted',{'denied':denied});return {'saved':True}

@router.get('/api/platform/{org}/tokens')
def api_tokens(org:str,request:Request):
    with connect() as db:
        user=session(db,request,org);owner(user)
        return table_rows(db,'SELECT id,name,scopes,expires_at,revoked,last_used_at,created_by FROM pl_tokens WHERE organization_id=%s ORDER BY expires_at DESC',(org,))

@router.post('/api/platform/{org}/tokens')
def issue_token(org:str,body:dict,request:Request):
    with connect() as db,db.transaction():
        user=session(db,request,org,True);owner(user);reauthenticate(db,user,body)
        if body.get('revoke'):
            db.execute('UPDATE pl_tokens SET revoked=TRUE WHERE organization_id=%s AND id=%s',(org,str(body['revoke'])));return {'revoked':True}
        scopes=body.get('scopes',['records:read']);days=body.get('days',30)
        if not isinstance(scopes,list) or not scopes or not all(isinstance(v,str) for v in scopes) or set(scopes)-{'records:read','records:write'} or isinstance(days,bool) or not isinstance(days,int) or not 1<=days<=90:store.fail('Choose valid scopes and a 1–90 day lifetime')
        token='csos_i_'+secrets.token_urlsafe(40);ident=store.uid();db.execute('INSERT INTO pl_tokens(id,organization_id,token_hash,name,scopes,created_by,expires_at) VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s)',(ident,org,HASH(token),store.bounded(body.get('name','Integration token'),100),json.dumps(scopes),user['username'],int(time.time())+days*86400));store.history(db,org,ident,user['username'],'token:issued',{'scopes':scopes,'days':days});return {'id':ident,'token':token,'message':'Copy now. The token value will not be shown again.'}


def token_principal(db,request,org,scope):
    header=request.headers.get('authorization','')
    value=header.removeprefix('Bearer ')
    if not header.startswith('Bearer ') or len(value)>200:store.fail('Integration token required',401)
    row=db.execute('SELECT t.*,u.enabled,u.role FROM pl_tokens t JOIN web_users u ON u.username=t.created_by WHERE t.token_hash=%s AND t.organization_id=%s AND NOT t.revoked AND t.expires_at>%s AND u.enabled',(HASH(value),org,int(time.time()))).fetchone()
    if not row or scope not in row['scopes']:store.fail('Token is invalid, expired, revoked or lacks this scope',403)
    actor(db,row['created_by'],org);db.execute('UPDATE pl_tokens SET last_used_at=CURRENT_TIMESTAMP WHERE id=%s',(row['id'],));return {'username':row['created_by'],'role':row['role']}

@router.get('/api/v1/{org}/records/{kind}')
def api_read(org:str,kind:str,request:Request):
    with connect() as db:
        token_principal(db,request,org,'records:read')
        if kind not in catalog.MODULES:store.fail('Unsupported module')
        return table_rows(db,'SELECT * FROM pl_records WHERE organization_id=%s AND kind=%s AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT 100',(org,kind))

@router.post('/api/v1/{org}/records/{kind}')
def api_write(org:str,kind:str,body:dict,request:Request):
    with connect() as db,db.transaction():return store.save(db,token_principal(db,request,org,'records:write'),org,kind,body)

@router.post('/api/platform/demo')
def demo(body:dict,request:Request):
    with connect() as db,db.transaction():
        user=session(db,request,write=True);owner(user)
        if body.get('confirmed') is not True:store.fail('Confirm creation of an isolated synthetic demonstration organization')
        org=service(db).create_organization('DEMO - Synthetic Security Program','Synthetic examples only');actor(db,user['username'],org)
        db.execute('INSERT INTO pl_demo(organization_id,created_by) VALUES (%s,%s)',(org,user['username']))
        office=store.save(db,user,org,'site',{'title':'Synthetic dental office','data':{'criticality':'moderate','notes':'Fictional data; do not place customer records here.'}})
        asset=store.save(db,user,org,'asset',{'title':'Synthetic practice-management service','data':{'site_id':office['id'],'asset_type':'business_service','data_class':'regulated'}})
        store.save(db,user,org,'bia',{'title':'Synthetic continuity assessment','data':{'asset_id':asset['id'],'rto_hours':8,'rpo_hours':4,'impact':'Fictional planning example, not a clinical assessment.'}})
        service(db).add_risk(org,'Synthetic privileged-access backlog','',4,4,'Demonstration data only')
        return {'organization_id':org,'message':'Synthetic demonstration workspace created. Integrations and external deliveries are not enabled.'}

@router.get('/account-recovery')
def recovery_page():return FileResponse(STATIC/'account-recovery.html')



@router.get('/api/platform/ai/reference')
def ai_reference(request:Request):
    with connect() as db:
        session(db,request)
        from .ai_governance import reference
        return reference()

@router.get('/api/platform/{org}/ai/overview')
def ai_overview(org:str,request:Request):
    with connect() as db:
        user=session(db,request,org)
        from .ai_governance import overview
        return overview(db,user,org)


@router.get('/api/platform/{org}/operations/overview')
def operational_overview(org:str,request:Request):
    from .operations import summary
    with connect() as db:
        user=session(db,request,org)
        return summary(db,user,org)

@router.get('/api/platform/{org}/operations/impact/{ident}')
def operational_impact(org:str,ident:str,request:Request):
    from .operations import impact
    with connect() as db:
        session(db,request,org)
        return impact(db,org,ident)

@router.post('/api/platform/{org}/operations/{ident}/run')
def operational_action(org:str,ident:str,body:dict,request:Request):
    from .operations import action
    with connect() as db,db.transaction():
        session(db,request,org)
        target=store.get(db,org,ident)
        user=session(db,request,org,True,'records:approve' if target['kind']=='op_campaign' else 'records:write')
        return action(db,user,org,ident,body)

@router.get('/api/platform/{org}/assurance/overview')
def assurance_overview(org:str,request:Request):
    from .assurance import overview
    with connect() as db:return overview(db,session(db,request,org),org)

@router.post('/api/platform/{org}/assurance/{action}')
def assurance_action(org:str,action:str,body:dict,request:Request):
    from . import assurance
    with connect() as db,db.transaction():
        cap='reports:export' if action in {'export','recovery-preview'} else 'records:read' if action in {'search','catalog-preview'} else 'records:delete' if action in {'recover','demo-reset'} else 'records:write'
        user=session(db,request,org,True,cap)
        if action in {'export','recover','recovery-preview','demo-reset','retry','acknowledge'}:owner(user)
        if action=='search':return assurance.search(db,org,body)
        if action=='bulk':return assurance.bulk(db,user,org,body)
        if action=='catalog-preview':return assurance.catalog_diff(db,org,body)
        if action=='catalog-migrate':return assurance.migrate(db,user,org,body)
        if action=='export':
            result=assurance.export_package(db,user,org);store.history(db,org,org,user['username'],'assurance:exported',{'sha256':result['sha256']});return result
        if action=='recovery-preview':return assurance.package_preview(db,org,body.get('package'))
        if action=='recover':return assurance.recover(db,user,org,body)
        if action=='acknowledge':return assurance.acknowledge(db,user,org,body)
        if action=='retry':return assurance.retry(db,user,org,body)
        if action=='demo-reset':return assurance.demo_reset(db,user,org,body)
        store.fail('Unknown assurance action',404)
