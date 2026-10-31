"""Organization-scoped application services and SQLite schema.

All queries for customer data are scoped by organization ID; association
validation prevents an assessment/risk/task in one organization being linked
to another. Business logic is UI independent for automated testing.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import sqlite3
from typing import Any
from uuid import uuid4

from .vault import Vault


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def uid() -> str:
    return str(uuid4())


QUESTIONS = (
    ("GOV-01", "Is there a documented security risk management policy?", "Govern"),
    ("ID-01", "Is an up-to-date inventory of systems and devices maintained?", "Identify"),
    ("PR-01", "Is multi-factor authentication enforced for privileged access?", "Protect"),
    ("PR-02", "Are sensitive data and backups encrypted appropriately?", "Protect"),
    ("DE-01", "Are security events logged and reviewed?", "Detect"),
    ("RS-01", "Is an incident response plan documented and exercised?", "Respond"),
    ("RC-01", "Are backups restored in periodic recovery tests?", "Recover"),
    ("GV-01", "Are critical third-party vendors assessed periodically?", "Govern"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, industry TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE(name)
);
CREATE TABLE IF NOT EXISTS assessments (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    title TEXT NOT NULL, scope TEXT NOT NULL DEFAULT '',
    framework_label TEXT NOT NULL DEFAULT 'Original sample questions (not certified)',
    status TEXT NOT NULL CHECK(status IN ('draft', 'in_progress', 'review', 'finalized')),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE(id, organization_id)
);
CREATE TABLE IF NOT EXISTS assessment_questions (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
    code TEXT NOT NULL, prompt TEXT NOT NULL, domain TEXT NOT NULL,
    answer TEXT NOT NULL DEFAULT 'Unanswered'
      CHECK(answer IN ('Unanswered', 'Yes', 'Partial', 'No', 'N/A', 'Unknown')),
    rationale TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
    UNIQUE(assessment_id, code),
    FOREIGN KEY(assessment_id, organization_id) REFERENCES assessments(id, organization_id)
);
CREATE TABLE IF NOT EXISTS risks (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    assessment_id TEXT, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
    likelihood INTEGER NOT NULL CHECK(likelihood BETWEEN 1 AND 5),
    impact INTEGER NOT NULL CHECK(impact BETWEEN 1 AND 5),
    score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 25),
    rationale TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open'
      CHECK(status IN ('open', 'mitigating', 'accepted', 'closed')),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE(id, organization_id),
    FOREIGN KEY(assessment_id, organization_id) REFERENCES assessments(id, organization_id)
);
CREATE TABLE IF NOT EXISTS risk_score_history (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, risk_id TEXT NOT NULL,
    likelihood INTEGER NOT NULL, impact INTEGER NOT NULL, score INTEGER NOT NULL,
    rationale TEXT NOT NULL, methodology_version TEXT NOT NULL DEFAULT 'matrix-1',
    recorded_at TEXT NOT NULL,
    FOREIGN KEY(risk_id, organization_id) REFERENCES risks(id, organization_id)
);
CREATE TABLE IF NOT EXISTS remediation_tasks (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, risk_id TEXT NOT NULL,
    title TEXT NOT NULL, owner TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL DEFAULT '', priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
      CHECK(status IN ('open', 'in_progress', 'blocked', 'done')),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    FOREIGN KEY(risk_id, organization_id) REFERENCES risks(id, organization_id)
);
CREATE TABLE IF NOT EXISTS task_history (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, task_id TEXT NOT NULL,
    old_status TEXT, new_status TEXT NOT NULL, note TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES remediation_tasks(id)
);
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY, organization_id TEXT, entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL, action TEXT NOT NULL, details_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assessments_org ON assessments(organization_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_questions_org ON assessment_questions(organization_id, assessment_id);
CREATE INDEX IF NOT EXISTS idx_risks_org ON risks(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_remediation_org ON remediation_tasks(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_org ON audit_events(organization_id, recorded_at);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS history_no_update BEFORE UPDATE ON task_history
BEGIN SELECT RAISE(ABORT, 'task history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS history_no_delete BEFORE DELETE ON task_history
BEGIN SELECT RAISE(ABORT, 'task history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS scoring_no_update BEFORE UPDATE ON risk_score_history
BEGIN SELECT RAISE(ABORT, 'risk score history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS scoring_no_delete BEFORE DELETE ON risk_score_history
BEGIN SELECT RAISE(ABORT, 'risk score history is immutable'); END;
"""


class ValidationError(ValueError):
    pass


class NotFoundError(LookupError):
    pass


def _required(value: str, name: str, max_len: int = 250) -> str:
    value = value.strip()
    if not value or len(value) > max_len:
        raise ValidationError(f"{name} must be between 1 and {max_len} characters")
    return value


def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


class StudioService:
    def __init__(self, vault: Vault):
        self.vault = vault
        # executescript commits on SQLite; schema creation is persisted once.
        self.vault.db.executescript(SCHEMA)
        self.vault._persist()

    @property
    def db(self) -> sqlite3.Connection:
        return self.vault.db

    def _exists(self, table: str, id_: str, org: str | None = None) -> None:
        allowed = {"organizations", "assessments", "risks", "remediation_tasks"}
        if table not in allowed:
            raise ValidationError("Unsupported table")
        if table == "organizations":
            row = self.db.execute("SELECT 1 FROM organizations WHERE id=? AND status='active'", (id_,)).fetchone()
        elif org is not None:
            row = self.db.execute(f"SELECT 1 FROM {table} WHERE id=? AND organization_id=?", (id_, org)).fetchone()
        else:
            raise ValidationError("Organization context required")
        if not row:
            raise NotFoundError(f"{table} record not found in this organization")

    def _org(self, org: str) -> None:
        self._exists("organizations", org)

    def _audit(self, conn: sqlite3.Connection, org: str | None, typ: str,
               entity: str, action: str, details: dict[str, Any] | None = None) -> None:
        conn.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?)", (
            uid(), org, typ, entity, action, json.dumps(details or {}, sort_keys=True), utc_now()))

    def list_organizations(self) -> list[dict[str, Any]]:
        return _rows(self.db.execute("SELECT * FROM organizations WHERE status='active' ORDER BY name"))

    def create_organization(self, name: str, industry: str = "") -> str:
        name = _required(name, "Organization name")
        if len(industry) > 100:
            raise ValidationError("Industry is too long")
        org = uid()
        stamp = utc_now()
        try:
            with self.vault.transaction() as conn:
                conn.execute("INSERT INTO organizations VALUES(?,?,?,?,?,?)", (
                    org, name, industry.strip(), "active", stamp, stamp))
                self._audit(conn, org, "organization", org, "create", {"name": name})
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Organization with this name already exists") from exc
        return org

    def overview(self, org: str) -> dict[str, int]:
        self._org(org)
        return {
            "assessments": self.db.execute("SELECT count(*) FROM assessments WHERE organization_id=?", (org,)).fetchone()[0],
            "risks_open": self.db.execute("SELECT count(*) FROM risks WHERE organization_id=? AND status<>'closed'", (org,)).fetchone()[0],
            "risks_high_critical": self.db.execute("SELECT count(*) FROM risks WHERE organization_id=? AND status<>'closed' AND score>=10", (org,)).fetchone()[0],
            "tasks_open": self.db.execute("SELECT count(*) FROM remediation_tasks WHERE organization_id=? AND status<>'done'", (org,)).fetchone()[0],
        }

    def create_assessment(self, org: str, title: str, scope: str = "") -> str:
        self._org(org)
        title = _required(title, "Assessment title")
        if len(scope) > 2000:
            raise ValidationError("Assessment scope is too long")
        aid, stamp = uid(), utc_now()
        with self.vault.transaction() as conn:
            conn.execute("INSERT INTO assessments(id,organization_id,title,scope,framework_label,status,created_at,updated_at) "
                         "VALUES(?,?,?,?,?,?,?,?)", (aid, org, title, scope, "Original sample questions (not certified)", "draft", stamp, stamp))
            for code, prompt, domain in QUESTIONS:
                conn.execute("INSERT INTO assessment_questions VALUES(?,?,?,?,?,?,?,?,?)",
                             (uid(), org, aid, code, prompt, domain, "Unanswered", "", stamp))
            self._audit(conn, org, "assessment", aid, "create", {"question_count": len(QUESTIONS)})
        return aid

    def list_assessments(self, org: str) -> list[dict[str, Any]]:
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM assessments WHERE organization_id=? ORDER BY updated_at DESC", (org,)))

    def questions(self, org: str, assessment: str) -> list[dict[str, Any]]:
        self._org(org)
        self._exists("assessments", assessment, org)
        return _rows(self.db.execute("SELECT * FROM assessment_questions WHERE organization_id=? AND assessment_id=? ORDER BY code", (org, assessment)))

    def answer_question(self, org: str, assessment: str, code: str, answer: str, rationale: str) -> None:
        self._org(org)
        self._exists("assessments", assessment, org)
        if answer not in {"Yes", "Partial", "No", "N/A", "Unknown", "Unanswered"}:
            raise ValidationError("Unsupported answer")
        if len(rationale) > 5000:
            raise ValidationError("Rationale is too long")
        with self.vault.transaction() as conn:
            cursor = conn.execute("UPDATE assessment_questions SET answer=?, rationale=?, updated_at=? "
                                  "WHERE organization_id=? AND assessment_id=? AND code=?",
                                  (answer, rationale.strip(), utc_now(), org, assessment, code))
            if not cursor.rowcount:
                raise NotFoundError("Question not in this assessment")
            conn.execute("UPDATE assessments SET status='in_progress', updated_at=? WHERE id=? AND organization_id=?",
                         (utc_now(), assessment, org))
            self._audit(conn, org, "question", assessment, "answer", {"code": code, "answer": answer})

    @staticmethod
    def score(likelihood: int, impact: int) -> tuple[int, str]:
        if not all(isinstance(x, int) and not isinstance(x, bool) and 1 <= x <= 5 for x in (likelihood, impact)):
            raise ValidationError("Likelihood and impact must both be integers from 1 to 5")
        s = likelihood * impact
        return s, "Low" if s <= 4 else "Moderate" if s <= 9 else "High" if s <= 16 else "Critical"

    def add_risk(self, org: str, title: str, description: str, likelihood: int,
                 impact: int, rationale: str, assessment_id: str | None = None) -> str:
        self._org(org)
        if assessment_id:
            self._exists("assessments", assessment_id, org)
        title = _required(title, "Risk title")
        rationale = _required(rationale, "Scoring rationale", 3000)
        score, band = self.score(likelihood, impact)
        if len(description) > 10000:
            raise ValidationError("Description is too long")
        rid, stamp = uid(), utc_now()
        with self.vault.transaction() as conn:
            conn.execute("INSERT INTO risks VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
                rid, org, assessment_id, title, description.strip(), likelihood, impact,
                score, rationale, "open", stamp, stamp))
            conn.execute("INSERT INTO risk_score_history VALUES(?,?,?,?,?,?,?,?,?)",
                         (uid(), org, rid, likelihood, impact, score, rationale, "matrix-1", stamp))
            self._audit(conn, org, "risk", rid, "create", {"score": score, "band": band})
        return rid

    def list_risks(self, org: str) -> list[dict[str, Any]]:
        self._org(org)
        rows = _rows(self.db.execute("SELECT * FROM risks WHERE organization_id=? ORDER BY score DESC, title", (org,)))
        for row in rows:
            row["band"] = self.score(row["likelihood"], row["impact"])[1]
        return rows

    def add_task(self, org: str, risk: str, title: str, owner: str = "", due_date: str = "") -> str:
        self._org(org)
        self._exists("risks", risk, org)
        title = _required(title, "Remediation title")
        if len(owner) > 200:
            raise ValidationError("Owner is too long")
        if due_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due_date):
            raise ValidationError("Due date must use YYYY-MM-DD")
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValidationError("Due date is invalid") from exc
        risk_score = self.db.execute("SELECT score FROM risks WHERE id=? AND organization_id=?", (risk, org)).fetchone()[0]
        priority = "urgent" if risk_score >= 17 else "high" if risk_score >= 10 else "normal"
        tid, stamp = uid(), utc_now()
        with self.vault.transaction() as conn:
            conn.execute("INSERT INTO remediation_tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (tid, org, risk, title, owner.strip(), due_date, priority, "open", stamp, stamp))
            conn.execute("INSERT INTO task_history VALUES(?,?,?,?,?,?,?)",
                         (uid(), org, tid, None, "open", "Task created", stamp))
            self._audit(conn, org, "task", tid, "create", {"risk_id": risk})
        return tid

    def list_tasks(self, org: str) -> list[dict[str, Any]]:
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM remediation_tasks WHERE organization_id=? "
                                     "ORDER BY CASE status WHEN 'done' THEN 1 ELSE 0 END, due_date, title", (org,)))

    def update_task_status(self, org: str, tid: str, new_status: str, note: str = "") -> None:
        self._org(org)
        if new_status not in {"open", "in_progress", "blocked", "done"}:
            raise ValidationError("Invalid task status")
        self._exists("remediation_tasks", tid, org)
        old = self.db.execute("SELECT status FROM remediation_tasks WHERE id=? AND organization_id=?", (tid, org)).fetchone()[0]
        if old == new_status:
            return
        stamp = utc_now()
        with self.vault.transaction() as conn:
            conn.execute("UPDATE remediation_tasks SET status=?,updated_at=? WHERE id=? AND organization_id=?",
                         (new_status, stamp, tid, org))
            conn.execute("INSERT INTO task_history VALUES(?,?,?,?,?,?,?)",
                         (uid(), org, tid, old, new_status, note[:1000], stamp))
            self._audit(conn, org, "task", tid, "status_change", {"from": old, "to": new_status})

    def task_history(self, org: str, tid: str) -> list[dict[str, Any]]:
        self._org(org)
        self._exists("remediation_tasks", tid, org)
        return _rows(self.db.execute("SELECT * FROM task_history WHERE organization_id=? AND task_id=? ORDER BY recorded_at", (org, tid)))

    def audit_events(self, org: str) -> list[dict[str, Any]]:
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM audit_events WHERE organization_id=? ORDER BY recorded_at,id", (org,)))

    def organization(self, org: str) -> dict[str, Any]:
        self._org(org)
        return dict(self.db.execute("SELECT * FROM organizations WHERE id=?", (org,)).fetchone())
