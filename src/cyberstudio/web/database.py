"""PostgreSQL persistence for the existing organization-scoped domain services.

The desktop SQLite engine remains unchanged. This narrow adapter translates its
fixed, application-authored SQL; client input is always bound as parameters.
Cloud records are native relational PostgreSQL rows, not serialized vault files.
"""
from contextlib import contextmanager
import os
import re
import sqlite3

import psycopg
from psycopg.rows import dict_row


class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Cursor:
    def __init__(self, cursor=None, rows=None):
        self.cursor = cursor
        self.rows = rows
        self.rowcount = cursor.rowcount if cursor is not None else len(rows or [])

    def fetchall(self):
        return [Row(r) for r in (self.cursor.fetchall() if self.cursor is not None else self.rows)]

    def fetchone(self):
        row = self.cursor.fetchone() if self.cursor is not None else (self.rows[0] if self.rows else None)
        return Row(row) if row is not None else None

    def __iter__(self):
        return iter(self.fetchall())


def connect(*, admin=False):
    if os.getenv('TEST_DATABASE_URL'):
        return psycopg.connect(os.environ['TEST_DATABASE_URL'], autocommit=True, row_factory=dict_row,
                               options='-c search_path=studio,public')
    return psycopg.connect(
        host=os.environ['DB_HOST'], port=int(os.getenv('DB_PORT', '5432')),
        dbname=os.getenv('DB_NAME', 'cyberops'),
        user=os.environ['DB_ADMIN_USER' if admin else 'DB_USER'],
        password=os.environ['DB_ADMIN_PASSWORD' if admin else 'DB_PASSWORD'],
        sslmode='verify-full', sslrootcert=os.getenv('DB_SSLROOTCERT', '/app/rds-ca.pem'),
        connect_timeout=10, autocommit=True, row_factory=dict_row,
        options='-c search_path=studio,public -c statement_timeout=20000 -c lock_timeout=10000')


class Database:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, query, args=()):
        if query.strip().lower().startswith('pragma user_version'):
            if '=' in query:
                self.raw.execute("INSERT INTO web_schema VALUES ('domain', %s) ON CONFLICT (name) DO UPDATE SET version=EXCLUDED.version", (int(query.split('=')[1]),))
                return Cursor(rows=[])
            return Cursor(rows=self.raw.execute("SELECT version FROM web_schema WHERE name='domain'").fetchall() or [{'version': 0}])
        match = re.fullmatch(r'PRAGMA table_info\((\w+)\)', query, re.I)
        if match:
            return Cursor(self.raw.execute("SELECT column_name AS name FROM information_schema.columns WHERE table_schema='studio' AND table_name=%s", (match[1],)))
        ignore = bool(re.match(r'\s*INSERT OR IGNORE', query, re.I))
        if 'rowid' in query:
            column = 'created_at' if 'FROM vendor_reviews' in query else 'recorded_at'
            query = query.replace('rowid', column)
        # SQLite accepts double-quoted literal strings; PostgreSQL does not.
        for literal in ('critical', 'high', 'medium'):
            query = query.replace('"'+literal+'"', "'"+literal+"'")
        query = re.sub(r'INSERT OR IGNORE', 'INSERT', query, flags=re.I)
        if ignore:
            query = query.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
        query = query.replace('%', '%%').replace('?', '%s') if args else query
        try:
            return Cursor(self.raw.execute(query, args if args else None))
        except psycopg.IntegrityError as exc:
            raise sqlite3.IntegrityError('Database constraint rejected this record') from exc

    def executescript(self, script):
        statement = ''
        for line in script.splitlines():
            statement += line + '\n'
            if not sqlite3.complete_statement(statement):
                continue
            statement = statement.strip()
            if not statement:
                continue
            trigger = re.fullmatch(r"CREATE TRIGGER IF NOT EXISTS (\w+) BEFORE (UPDATE|DELETE) ON (\w+)\s*BEGIN SELECT RAISE\(ABORT,\s*'[^']+'\); END;", statement, re.I | re.S)
            if trigger:
                name, event, table = trigger.groups()
                self.raw.execute(f'CREATE OR REPLACE TRIGGER {name} BEFORE {event} ON {table} FOR EACH ROW EXECUTE FUNCTION reject_history_change()')
            else:
                statement = re.sub(r'\bBLOB\b', 'BYTEA', statement)
                statement = re.sub(r'\bREAL\b', 'DOUBLE PRECISION', statement)
                self.raw.execute(statement)
            statement = ''
        if statement.strip():
            raise ValueError('Incomplete schema statement')


class PostgresVault:
    def __init__(self, raw):
        self.db = Database(raw)
        self.raw = raw
        self.reauthenticated = False

    @contextmanager
    def transaction(self):
        with self.raw.transaction():
            yield self.db

    def _persist(self):
        """PostgreSQL commits the transaction; no local vault file is written."""

    def verify_passphrase(self, candidate):
        return self.reauthenticated


def service(raw):
    from cyberstudio.enterprise import EnterpriseGovernanceService
    instance = EnterpriseGovernanceService.__new__(EnterpriseGovernanceService)
    instance.vault = PostgresVault(raw)
    return instance


AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS web_schema(name TEXT PRIMARY KEY, version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS web_users(username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, created_at BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS web_sessions(token_hash TEXT PRIMARY KEY, username TEXT NOT NULL REFERENCES web_users(username), csrf TEXT NOT NULL, expires_at BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS web_attempts(key TEXT PRIMARY KEY, started_at BIGINT NOT NULL, failures INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS web_request_audit(id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, username TEXT NOT NULL, operation TEXT NOT NULL, recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
"""


def migrate(raw):
    from cyberstudio.enterprise import EnterpriseGovernanceService
    with raw.transaction():
        raw.execute('SELECT pg_advisory_xact_lock(747103091)')
        raw.execute('CREATE SCHEMA IF NOT EXISTS studio')
        raw.execute('SET search_path=studio,public')
        raw.execute(AUTH_SCHEMA)
        raw.execute("""CREATE OR REPLACE FUNCTION reject_history_change() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Audit history is immutable' USING ERRCODE='23514'; END; $$""")
        EnterpriseGovernanceService(PostgresVault(raw))
        raw.execute("INSERT INTO web_schema VALUES ('web',1) ON CONFLICT (name) DO NOTHING")
        raw.execute('CREATE OR REPLACE TRIGGER web_audit_no_update BEFORE UPDATE OR DELETE ON web_request_audit FOR EACH ROW EXECUTE FUNCTION reject_history_change()')


def main():
    from psycopg import sql
    with connect(admin=True) as raw:
        migrate(raw)
        if not os.getenv('TEST_DATABASE_URL'):
            username = os.environ['DB_USER']
            if not raw.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (username,)).fetchone():
                raw.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(username), sql.Literal(os.environ['DB_PASSWORD'])))
            raw.execute(sql.SQL('GRANT USAGE ON SCHEMA studio TO {}').format(sql.Identifier(username)))
            raw.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA studio TO {}').format(sql.Identifier(username)))
            raw.execute(sql.SQL('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA studio TO {}').format(sql.Identifier(username)))
            raw.execute(sql.SQL('REVOKE CREATE ON SCHEMA public FROM PUBLIC'))
    print('PostgreSQL schema migration and application role grants completed')


if __name__ == '__main__':
    main()
