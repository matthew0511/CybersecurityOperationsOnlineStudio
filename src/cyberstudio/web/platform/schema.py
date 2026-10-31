"""Additive PostgreSQL schema. Application principals are set per connection."""
SCHEMA="""
CREATE TABLE IF NOT EXISTS pl_records(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),kind TEXT NOT NULL,title TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'draft',owner TEXT NOT NULL DEFAULT '',due_on DATE,data JSONB NOT NULL DEFAULT '{}',version INTEGER NOT NULL DEFAULT 1,created_by TEXT NOT NULL,updated_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,deleted_at TIMESTAMPTZ,UNIQUE(organization_id,id));
CREATE INDEX IF NOT EXISTS pl_records_org_kind ON pl_records(organization_id,kind,deleted_at);
CREATE TABLE IF NOT EXISTS pl_history(id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,organization_id TEXT NOT NULL,record_id TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,snapshot JSONB NOT NULL,recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_capabilities(organization_id TEXT NOT NULL,username TEXT NOT NULL,denied JSONB NOT NULL DEFAULT '[]',PRIMARY KEY(organization_id,username));
CREATE TABLE IF NOT EXISTS pl_mfa(username TEXT PRIMARY KEY REFERENCES web_users(username),secret_cipher TEXT NOT NULL,enabled BOOLEAN NOT NULL DEFAULT FALSE,last_step BIGINT NOT NULL DEFAULT -1,updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_recovery(code_hash TEXT PRIMARY KEY,username TEXT NOT NULL REFERENCES web_users(username),purpose TEXT NOT NULL,used_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_session_meta(token_hash TEXT PRIMARY KEY,username TEXT NOT NULL,created_at BIGINT NOT NULL,user_agent TEXT NOT NULL DEFAULT '',auth_method TEXT NOT NULL DEFAULT 'password');
CREATE TABLE IF NOT EXISTS pl_oidc(state_hash TEXT PRIMARY KEY,nonce TEXT NOT NULL,verifier_cipher TEXT NOT NULL,expires_at BIGINT NOT NULL,used BOOLEAN NOT NULL DEFAULT FALSE);
CREATE TABLE IF NOT EXISTS pl_sso_challenges(token_hash TEXT PRIMARY KEY,username TEXT NOT NULL,csrf TEXT NOT NULL,expires_at BIGINT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS pl_oidc_accounts(tenant_id TEXT NOT NULL,object_id TEXT NOT NULL,username TEXT NOT NULL REFERENCES web_users(username),PRIMARY KEY(tenant_id,object_id));
CREATE TABLE IF NOT EXISTS pl_installation(key TEXT PRIMARY KEY,value JSONB NOT NULL DEFAULT '{}',secret_cipher TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS pl_integrations(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),provider TEXT NOT NULL,name TEXT NOT NULL,config JSONB NOT NULL DEFAULT '{}',secret_cipher TEXT NOT NULL,enabled BOOLEAN NOT NULL DEFAULT FALSE,connection_status TEXT NOT NULL DEFAULT 'not_tested',last_test_at TIMESTAMPTZ,created_by TEXT NOT NULL,updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(organization_id,id));
CREATE TABLE IF NOT EXISTS pl_external(organization_id TEXT NOT NULL,integration_id TEXT NOT NULL,external_id TEXT NOT NULL,payload JSONB NOT NULL,source_hash TEXT NOT NULL,promoted_id TEXT,updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(organization_id,integration_id,external_id));
CREATE TABLE IF NOT EXISTS pl_jobs(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,kind TEXT NOT NULL,payload JSONB NOT NULL,status TEXT NOT NULL DEFAULT 'queued',attempts INTEGER NOT NULL DEFAULT 0,result JSONB NOT NULL DEFAULT '{}',available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_tokens(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,token_hash TEXT UNIQUE NOT NULL,name TEXT NOT NULL,scopes JSONB NOT NULL,created_by TEXT NOT NULL,expires_at BIGINT NOT NULL,revoked BOOLEAN NOT NULL DEFAULT FALSE,last_used_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS pl_controls(organization_id TEXT NOT NULL,catalog_id TEXT NOT NULL,code TEXT NOT NULL,title TEXT NOT NULL,parent_code TEXT NOT NULL DEFAULT '',PRIMARY KEY(organization_id,catalog_id,code));
CREATE TABLE IF NOT EXISTS pl_catalogs(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,name TEXT NOT NULL,edition TEXT NOT NULL,source TEXT NOT NULL,license_note TEXT NOT NULL,sha256 TEXT NOT NULL,created_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_attestations(organization_id TEXT NOT NULL,record_id TEXT NOT NULL,version INTEGER NOT NULL,username TEXT NOT NULL,recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(organization_id,record_id,version,username));
CREATE TABLE IF NOT EXISTS pl_executions(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,record_id TEXT NOT NULL,record_version INTEGER NOT NULL,kind TEXT NOT NULL,title TEXT NOT NULL,steps JSONB NOT NULL,version INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'running',created_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_answer_uses(id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,organization_id TEXT NOT NULL,source_id TEXT NOT NULL,source_version INTEGER NOT NULL,assessment_id TEXT NOT NULL,code TEXT NOT NULL,actor TEXT NOT NULL,recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_evidence_versions(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,group_id TEXT NOT NULL,evidence_id TEXT NOT NULL,sha256 TEXT NOT NULL,supersedes TEXT,created_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_trash(organization_id TEXT NOT NULL,kind TEXT NOT NULL,record_id TEXT NOT NULL,deleted_by TEXT NOT NULL,deleted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(organization_id,kind,record_id));
CREATE TABLE IF NOT EXISTS pl_quarantine(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,filename TEXT NOT NULL,content BYTEA NOT NULL,sha256 TEXT NOT NULL,object_key TEXT NOT NULL,object_version TEXT NOT NULL DEFAULT '',context JSONB NOT NULL DEFAULT '{}',status TEXT NOT NULL DEFAULT 'pending',indicators JSONB NOT NULL DEFAULT '[]',created_by TEXT NOT NULL,result TEXT NOT NULL DEFAULT '',created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_editions(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,title TEXT NOT NULL,format TEXT NOT NULL,template TEXT NOT NULL,source JSONB NOT NULL,sha256 TEXT NOT NULL,content BYTEA NOT NULL,created_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_rooms(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,title TEXT NOT NULL,allowed JSONB NOT NULL,token_hash TEXT UNIQUE NOT NULL,expires_at BIGINT NOT NULL,revoked BOOLEAN NOT NULL DEFAULT FALSE,redeemed BOOLEAN NOT NULL DEFAULT FALSE,created_by TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pl_auditor_sessions(token_hash TEXT PRIMARY KEY,room_id TEXT NOT NULL REFERENCES pl_rooms(id),csrf TEXT NOT NULL,expires_at BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS pl_room_questions(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,room_id TEXT NOT NULL,body TEXT NOT NULL,actor TEXT NOT NULL,recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_schedule_runs(organization_id TEXT NOT NULL,schedule_id TEXT NOT NULL,bucket TEXT NOT NULL,job_id TEXT NOT NULL,PRIMARY KEY(organization_id,schedule_id,bucket));
CREATE TABLE IF NOT EXISTS pl_operations(id TEXT PRIMARY KEY,kind TEXT NOT NULL,result JSONB NOT NULL,recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pl_demo(organization_id TEXT PRIMARY KEY,created_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TRIGGER pl_history_immutable BEFORE UPDATE OR DELETE ON pl_history FOR EACH ROW EXECUTE FUNCTION reject_history_change();
CREATE TRIGGER pl_editions_immutable BEFORE UPDATE OR DELETE ON pl_editions FOR EACH ROW EXECUTE FUNCTION reject_history_change();
CREATE TRIGGER pl_attestations_immutable BEFORE UPDATE OR DELETE ON pl_attestations FOR EACH ROW EXECUTE FUNCTION reject_history_change();
CREATE TRIGGER pl_evidence_versions_immutable BEFORE UPDATE OR DELETE ON pl_evidence_versions FOR EACH ROW EXECUTE FUNCTION reject_history_change();
"""
# DROP/CREATE is migration-idempotent and executed only by the migration principal.
def migrate(db):
    for name,table in [('pl_history_immutable','pl_history'),('pl_editions_immutable','pl_editions'),('pl_attestations_immutable','pl_attestations'),('pl_evidence_versions_immutable','pl_evidence_versions')]:
        if db.execute('SELECT to_regclass(%s) AS name',('studio.'+table,)).fetchone()['name']:
            db.execute(f'DROP TRIGGER IF EXISTS {name} ON {table}')
    db.execute(SCHEMA)
    db.execute("""CREATE OR REPLACE FUNCTION studio_scope_ok(oid TEXT) RETURNS BOOLEAN LANGUAGE SQL STABLE AS $$
      SELECT current_user='studioapp' OR ((COALESCE(current_setting('studio.organization',true),'')='' OR current_setting('studio.organization',true)=oid)
      AND EXISTS(SELECT 1 FROM web_users u WHERE u.username=current_setting('studio.actor',true) AND u.enabled
       AND (u.role='owner' OR EXISTS(SELECT 1 FROM xp_memberships m WHERE m.username=u.username AND m.organization_id=oid)))) $$""")
    from psycopg import sql
    tables=db.execute("SELECT table_name FROM information_schema.columns WHERE table_schema='studio' AND column_name='organization_id'").fetchall()
    # Memberships are the trusted authorization lookup, never exposed as a general SQL API.
    for row in tables:
        table=row['table_name']
        if table in {'xp_memberships','xp_invites','pl_tokens','pl_rooms','pl_auditor_sessions'}:continue
        ident=sql.Identifier(table)
        db.execute(sql.SQL('ALTER TABLE {} ENABLE ROW LEVEL SECURITY').format(ident))
        db.execute(sql.SQL('ALTER TABLE {} FORCE ROW LEVEL SECURITY').format(ident))
        db.execute(sql.SQL('DROP POLICY IF EXISTS studio_org_scope ON {}').format(ident))
        legacy={'risks':'risk','remediation_tasks':'task','vendors':'vendor','assessments':'assessment','evidence_records':'evidence','governance_findings':'finding','vciso_initiatives':'initiative','governance_changes':'change'}
        using=sql.SQL('studio_scope_ok(organization_id)')
        if table in legacy:
            using=sql.SQL('studio_scope_ok(organization_id) AND NOT EXISTS(SELECT 1 FROM pl_trash z WHERE z.organization_id={}.organization_id AND z.kind={} AND z.record_id={}.id)').format(ident,sql.Literal(legacy[table]),ident)
        db.execute(sql.SQL('CREATE POLICY studio_org_scope ON {} USING ({}) WITH CHECK (studio_scope_ok(organization_id))').format(ident,using))


def actor(db,username,org=''):
    db.execute("SELECT set_config('studio.actor',%s,false),set_config('studio.organization',%s,false)",(username,org))


def system_actor(db,org=''):
    row=db.execute("SELECT username FROM web_users WHERE role='owner' AND enabled ORDER BY created_at LIMIT 1").fetchone()
    if row:actor(db,row['username'],org)
    return row['username'] if row else None
