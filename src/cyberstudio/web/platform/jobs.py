"""Bounded background queue. Real provider results, retries, dead letters and idempotent schedules."""
from datetime import date,datetime,timezone,timedelta
import json,os,logging
from .schema import system_actor,actor
from .store import uid,history
from . import connectors,quarantine,reporting


def schedule(db,org,user):
    demo=db.execute('SELECT 1 FROM pl_demo WHERE organization_id=%s',(org,)).fetchone()
    rows=db.execute("SELECT * FROM pl_records WHERE organization_id=%s AND kind IN ('report_schedule','notification_rule') AND status='active' AND deleted_at IS NULL",(org,)).fetchall()
    for record in rows:
        data=record['data'];frequency=data.get('frequency','weekly');today=date.today();bucket=today.isoformat() if frequency=='daily' else today.strftime('%G-W%V') if frequency=='weekly' else today.strftime('%Y-%m')
        if demo or record['kind']=='report_schedule' and data.get('delivery_enabled') is not True or record['kind']=='notification_rule' and data.get('enabled') is not True:continue
        job=uid();created=db.execute('INSERT INTO pl_schedule_runs VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING job_id',(org,record['id'],bucket,job)).fetchone()
        if not created:continue
        payload={'record_id':record['id'],'record_version':record['version'],'actor':user}
        db.execute('INSERT INTO pl_jobs(id,organization_id,kind,payload) VALUES (%s,%s,%s,%s::jsonb)',(job,org,'schedule:'+record['kind'],json.dumps(payload)))


def run_job(db,job,user):
    org=job['organization_id'];payload=job['payload'];kind=job['kind'];actor(db,user,org)
    if kind.startswith('integration:'):
        row=db.execute('SELECT * FROM pl_integrations WHERE organization_id=%s AND id=%s AND enabled',(org,payload['integration_id'])).fetchone()
        if not row:raise ValueError('Connection was disabled or removed')
        with connectors.Adapter(dict(row)) as adapter:
            action=kind.split(':',1)[1]
            if action=='pull':
                items,truncated=adapter.pull();count=connectors.stage(db,dict(row),items);return {'staged':count,'more_available':truncated,'message':'Review staged records before promoting. A bounded pull may require a narrower source query.'}
            if action=='publish':
                result=adapter.publish(payload['title'],payload['message']);return {'accepted':True,'external_id':str(result.get('id',result.get('key',result.get('ticket',{}).get('id',''))))[:200]}
            if action=='notify':return adapter.notify(payload['title'],payload['message'],payload.get('recipients'))
    if kind.startswith('schedule:'):
        row=db.execute("SELECT * FROM pl_records WHERE organization_id=%s AND id=%s AND deleted_at IS NULL AND status='active'",(org,payload['record_id'])).fetchone()
        if not row or row['version']!=payload['record_version']:raise ValueError('Schedule changed; skipped to avoid an unreviewed distribution')
        data=row['data']
        if row['kind']=='report_schedule':
            edition=reporting.freeze(db,{'username':user,'role':'owner'},org,data)
            connection=db.execute("SELECT * FROM pl_integrations WHERE organization_id=%s AND provider='ses' AND enabled AND connection_status='authenticated' ORDER BY last_test_at DESC LIMIT 1",(org,)).fetchone()
            if not connection:raise ValueError('Configure, test and enable SES delivery first')
            recipients=[s.strip() for s in data.get('recipients','').splitlines() if s.strip()]
            url=os.environ['PUBLIC_ORIGIN'].rstrip('/')+edition['download_url']
            with connectors.Adapter(dict(connection)) as adapter:delivery=adapter.notify('Scheduled security program report','A frozen report is ready. Sign in with an authorized organization account to download it:\n'+url+'\nSHA-256: '+edition['sha256'],recipients)
            return {'edition_id':edition['id'],**delivery}
        from ..experience import action_items,notify
        actions=action_items(db,org);message='\n'.join(a['title']+' | due '+str(a.get('due','')) for a in actions[:50]) or 'No currently recorded follow-up actions.'
        channel=data.get('channel','in_app')
        if channel=='in_app':
            notify(db,org,user,'Program follow-up digest','digest',row['id'],job['id']);return {'in_app':True,'items':len(actions)}
        connection=db.execute('SELECT * FROM pl_integrations WHERE organization_id=%s AND id=%s AND enabled AND connection_status=%s',(org,data.get('integration_id'),'authenticated')).fetchone()
        if not connection:raise ValueError('Notification connection is not enabled')
        if connection['provider']!=('ses' if channel=='email' else channel):raise ValueError('Notification channel and connection provider must match')
        recipients=[s.strip() for s in data.get('recipients','').splitlines() if s.strip()]
        with connectors.Adapter(dict(connection)) as adapter:return adapter.notify('Security program digest',message,recipients)
    raise ValueError('Unsupported job kind')


def tick(db):
    if not db.execute('SELECT pg_try_advisory_xact_lock(747103196) AS locked').fetchone()['locked']:return
    user=system_actor(db)
    if not user:return
    # Only identifiers are read across organizations; each organization is scoped before work.
    organizations=db.execute('SELECT id FROM organizations').fetchall()
    for row in organizations:
        org=row['id'];actor(db,user,org)
        with db.transaction():schedule(db,org,user)
        if os.getenv('SCAN_BUCKET'):
            try:
                with db.transaction():quarantine.poll(db,org,user)
            except Exception:logging.getLogger(__name__).warning('Quarantine scan poll unavailable; artifacts remain closed')
        jobs=db.execute("SELECT * FROM pl_jobs WHERE organization_id=%s AND status IN ('queued','retry') AND available_at<=CURRENT_TIMESTAMP ORDER BY created_at LIMIT 5 FOR UPDATE SKIP LOCKED",(org,)).fetchall()
        for item in jobs:
            job=dict(item)
            try:
                with db.transaction():result=run_job(db,job,user)
            except Exception:
                attempts=job['attempts']+1
                db.execute("UPDATE pl_jobs SET status=%s,attempts=%s,result=%s::jsonb,available_at=CURRENT_TIMESTAMP+%s*INTERVAL '1 minute',updated_at=CURRENT_TIMESTAMP WHERE id=%s",('retry' if job['kind']=='integration:pull' and attempts<3 else 'dead_letter',attempts,json.dumps({'message':'Provider or job validation failed; credentials and remote response bodies are not logged. Review the connection and approved schedule.'}),2**attempts,job['id']))
                logging.getLogger(__name__).warning('Platform job failed; retry/dead-letter state recorded')
            else:
                db.execute("UPDATE pl_jobs SET status='succeeded',attempts=attempts+1,result=%s::jsonb,updated_at=CURRENT_TIMESTAMP WHERE id=%s",(json.dumps(result,default=str),job['id']))
                history(db,org,job['id'],user,'job:succeeded',{'kind':job['kind']})
    actor(db,user)
