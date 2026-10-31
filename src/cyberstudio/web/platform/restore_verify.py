"""Read-only checks in an isolated restored DB; only aggregate operational results are recorded."""
import json,os,time
from datetime import datetime,timezone
from ..database import connect
from .store import uid
from .schema import system_actor


def main():
    target=os.environ['RESTORE_DB_ID'];source=os.environ['SOURCE_DB_ID']
    if not target.startswith('studio-restore-') or target==source or os.environ['RESTORE_DB_HOST']==os.environ['SOURCE_DB_HOST']:raise ValueError('An isolated restore endpoint is required')
    started=time.monotonic();os.environ['DB_HOST']=os.environ['RESTORE_DB_HOST']
    with connect(admin=True) as db,db.transaction():
        db.execute('SET TRANSACTION READ ONLY')
        if not system_actor(db):raise RuntimeError('Restored owner identity was not available')
        tables=['organizations','web_users','risks','assessment_questions','evidence_records','pl_records']
        from psycopg import sql
        counts={table:db.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(sql.Identifier(table))).fetchone()['n'] for table in tables}
        if not db.execute("SELECT 1 FROM web_schema WHERE name='platform' AND version=1").fetchone():raise RuntimeError('Restored web schema version was not available')
    result={'source_database':source,'restored_database':target,'result':'pass','checked_tables':counts,'verification_seconds':round(time.monotonic()-started,2),'verified_at':datetime.now(timezone.utc).isoformat(),'limits':'Read-only schema and aggregate-count validation, not an independent full application disaster-recovery exercise.'}
    os.environ['DB_HOST']=os.environ['SOURCE_DB_HOST']
    with connect(admin=True) as db,db.transaction():db.execute('INSERT INTO pl_operations(id,kind,result) VALUES (%s,%s,%s::jsonb)',(uid(),'restore_validation',json.dumps(result)))
    print(json.dumps({'restore_validation':'passed','tables_checked':len(counts),'duration_seconds':result['verification_seconds']}))

if __name__=='__main__':main()
