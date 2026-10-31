"""Phase 2 framework, template, evidence, risk-treatment and Notion import services.

This adds tables without changing Phase 1 storage formats or overwriting records.
Framework metadata and mappings are reference aids, not assessments or compliance claims.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from .service import StudioService, _required, _rows, uid, utc_now, ValidationError, NotFoundError

FRAMEWORKS = {
    "NIST-CSF-2.0": ("NIST Cybersecurity Framework", "2.0", "https://www.nist.gov/cyberframework"),
    "CIS-CONTROLS-8.1": ("CIS Critical Security Controls", "8.1", "https://www.cisecurity.org/controls/v8-1"),
}
# Only short official identifiers/titles, not outcome statements or Safeguard texts.
NIST_CATEGORIES = [
    ("GV.OC", "Organizational Context", "Govern"), ("GV.RM", "Risk Management Strategy", "Govern"),
    ("GV.RR", "Roles, Responsibilities, and Authorities", "Govern"), ("GV.PO", "Policy", "Govern"),
    ("GV.OV", "Oversight", "Govern"), ("GV.SC", "Cybersecurity Supply Chain Risk Management", "Govern"),
    ("ID.AM", "Asset Management", "Identify"), ("ID.RA", "Risk Assessment", "Identify"),
    ("ID.IM", "Improvement", "Identify"),
    ("PR.AA", "Identity Management, Authentication, and Access Control", "Protect"),
    ("PR.AT", "Awareness and Training", "Protect"), ("PR.DS", "Data Security", "Protect"),
    ("PR.PS", "Platform Security", "Protect"), ("PR.IR", "Technology Infrastructure Resilience", "Protect"),
    ("DE.CM", "Continuous Monitoring", "Detect"), ("DE.AE", "Adverse Event Analysis", "Detect"),
    ("RS.MA", "Incident Management", "Respond"), ("RS.AN", "Incident Analysis", "Respond"),
    ("RS.CO", "Incident Response Reporting and Communication", "Respond"),
    ("RS.MI", "Incident Mitigation", "Respond"),
    ("RC.RP", "Incident Recovery Plan Execution", "Recover"),
    ("RC.CO", "Incident Recovery Communication", "Recover"),
]
CIS_CONTROLS = [
    "Inventory and Control of Enterprise Assets", "Inventory and Control of Software Assets", "Data Protection",
    "Secure Configuration of Enterprise Assets and Software", "Account Management", "Access Control Management",
    "Continuous Vulnerability Management", "Audit Log Management", "Email and Web Browser Protections",
    "Malware Defenses", "Data Recovery", "Network Infrastructure Management", "Network Monitoring and Defense",
    "Security Awareness and Skills Training", "Service Provider Management", "Application Software Security",
    "Incident Response Management", "Penetration Testing",
]

P2_SCHEMA = """
CREATE TABLE IF NOT EXISTS framework_catalogs (
    key TEXT PRIMARY KEY, title TEXT NOT NULL, version TEXT NOT NULL, source_url TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS framework_controls (
    framework_key TEXT NOT NULL REFERENCES framework_catalogs(key), code TEXT NOT NULL,
    title TEXT NOT NULL, domain TEXT NOT NULL, PRIMARY KEY(framework_key,code)
);
CREATE TABLE IF NOT EXISTS question_templates (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE(id,organization_id), UNIQUE(organization_id,name)
);
CREATE TABLE IF NOT EXISTS template_questions (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, template_id TEXT NOT NULL,
    code TEXT NOT NULL, prompt TEXT NOT NULL, domain TEXT NOT NULL, sort_order INTEGER NOT NULL,
    UNIQUE(template_id,code),
    FOREIGN KEY(template_id,organization_id) REFERENCES question_templates(id,organization_id)
);
CREATE TABLE IF NOT EXISTS template_control_links (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, template_question_id TEXT NOT NULL,
    framework_key TEXT NOT NULL, control_code TEXT NOT NULL, rationale TEXT NOT NULL DEFAULT '',
    UNIQUE(template_question_id,framework_key,control_code),
    FOREIGN KEY(framework_key,control_code) REFERENCES framework_controls(framework_key,code),
    FOREIGN KEY(template_question_id) REFERENCES template_questions(id)
);
CREATE TABLE IF NOT EXISTS assessment_template_sources (
    assessment_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, template_id TEXT NOT NULL,
    template_version INTEGER NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(assessment_id,organization_id) REFERENCES assessments(id,organization_id),
    FOREIGN KEY(template_id,organization_id) REFERENCES question_templates(id,organization_id)
);
CREATE TABLE IF NOT EXISTS assessment_control_links (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
    question_code TEXT NOT NULL, framework_key TEXT NOT NULL, control_code TEXT NOT NULL,
    rationale TEXT NOT NULL DEFAULT '',
    UNIQUE(assessment_id,question_code,framework_key,control_code),
    FOREIGN KEY(assessment_id,organization_id) REFERENCES assessments(id,organization_id),
    FOREIGN KEY(framework_key,control_code) REFERENCES framework_controls(framework_key,code)
);
CREATE TABLE IF NOT EXISTS residual_risk_current (
    risk_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL,
    likelihood INTEGER NOT NULL CHECK(likelihood BETWEEN 1 AND 5),
    impact INTEGER NOT NULL CHECK(impact BETWEEN 1 AND 5),
    score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 25),
    rationale TEXT NOT NULL, assessed_at TEXT NOT NULL,
    FOREIGN KEY(risk_id,organization_id) REFERENCES risks(id,organization_id)
);
CREATE TABLE IF NOT EXISTS residual_risk_history (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, risk_id TEXT NOT NULL,
    likelihood INTEGER NOT NULL, impact INTEGER NOT NULL, score INTEGER NOT NULL,
    rationale TEXT NOT NULL, assessed_at TEXT NOT NULL,
    FOREIGN KEY(risk_id,organization_id) REFERENCES risks(id,organization_id)
);
CREATE TABLE IF NOT EXISTS risk_acceptance_decisions (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, risk_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('approved','rejected','revoked')),
    approver TEXT NOT NULL, rationale TEXT NOT NULL, expires_on TEXT NOT NULL DEFAULT '',
    attested INTEGER NOT NULL CHECK(attested IN (0,1)), recorded_at TEXT NOT NULL,
    FOREIGN KEY(risk_id,organization_id) REFERENCES risks(id,organization_id)
);
CREATE TABLE IF NOT EXISTS evidence_records (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    title TEXT NOT NULL, filename TEXT NOT NULL, mime_type TEXT NOT NULL,
    sha256 TEXT NOT NULL, contents BLOB NOT NULL, collected_at TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending','verified','rejected')),
    reviewed_by TEXT NOT NULL DEFAULT '', review_note TEXT NOT NULL DEFAULT '', reviewed_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, UNIQUE(id,organization_id)
);
CREATE TABLE IF NOT EXISTS evidence_links (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL, target_type TEXT NOT NULL CHECK(target_type IN ('risk','assessment')),
    target_id TEXT NOT NULL, relevance TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
    UNIQUE(evidence_id,target_type,target_id),
    FOREIGN KEY(evidence_id,organization_id) REFERENCES evidence_records(id,organization_id)
);
CREATE TABLE IF NOT EXISTS notion_import_jobs (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
    filename TEXT NOT NULL, sha256 TEXT NOT NULL, source_type TEXT NOT NULL,
    imported_count INTEGER NOT NULL, skipped_count INTEGER NOT NULL, report_json TEXT NOT NULL,
    created_at TEXT NOT NULL, UNIQUE(organization_id,sha256)
);
CREATE TABLE IF NOT EXISTS notion_import_rows (
    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, job_id TEXT NOT NULL,
    source_row INTEGER NOT NULL, target_id TEXT, status TEXT NOT NULL, message TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES notion_import_jobs(id)
);
CREATE INDEX IF NOT EXISTS idx_p2_templates_org ON question_templates(organization_id,name);
CREATE INDEX IF NOT EXISTS idx_p2_evidence_org ON evidence_records(organization_id,created_at);
CREATE INDEX IF NOT EXISTS idx_p2_links_org ON evidence_links(organization_id,target_type,target_id);
CREATE INDEX IF NOT EXISTS idx_p2_decisions_org ON risk_acceptance_decisions(organization_id,risk_id,recorded_at);
CREATE TRIGGER IF NOT EXISTS immutable_residual BEFORE UPDATE ON residual_risk_history BEGIN SELECT RAISE(ABORT,'history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_residual_del BEFORE DELETE ON residual_risk_history BEGIN SELECT RAISE(ABORT,'history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_decisions BEFORE UPDATE ON risk_acceptance_decisions BEGIN SELECT RAISE(ABORT,'decisions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_decisions_del BEFORE DELETE ON risk_acceptance_decisions BEGIN SELECT RAISE(ABORT,'decisions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_jobs BEFORE UPDATE ON notion_import_jobs BEGIN SELECT RAISE(ABORT,'imports are immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_jobs_del BEFORE DELETE ON notion_import_jobs BEGIN SELECT RAISE(ABORT,'imports are immutable'); END;
"""

# Original, independently authored starter questionnaire; mapping is a suggested
# topic association only. It is not an official framework assessment.
STARTER_ITEMS = [
    ("GOV-01", "Is the security risk management policy documented and periodically reviewed?", "Govern", "GV.PO", "5"),
    ("ID-01", "Are organization-owned systems and devices inventoried?", "Identify", "ID.AM", "1"),
    ("PR-01", "Is multi-factor authentication required for privileged access?", "Protect", "PR.AA", "6"),
    ("PR-02", "Are sensitive information and backups protected with appropriate encryption?", "Protect", "PR.DS", "3"),
    ("DE-01", "Are meaningful security events centrally logged and reviewed?", "Detect", "DE.CM", "8"),
    ("RS-01", "Is an incident response plan practiced and updated after exercises?", "Respond", "RS.MA", "17"),
    ("RC-01", "Are restorations regularly tested against recovery objectives?", "Recover", "RC.RP", "11"),
    ("GV-01", "Are critical service providers reviewed for cybersecurity risk?", "Govern", "GV.SC", "15"),
]


def _csv_data(payload: bytes) -> tuple[list[dict[str, str]], list[str]]:
    if len(payload) > 4 * 1024 * 1024:
        raise ValidationError("CSV exceeds the 4 MiB preview limit")
    if b"\x00" in payload:
        raise ValidationError("Binary data is not supported in CSV import")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("Only UTF-8 CSV is supported") from exc
    reader = csv.DictReader(StringIO(text), strict=True)
    if not reader.fieldnames or len(reader.fieldnames) > 80:
        raise ValidationError("Missing or excessive CSV headers")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValidationError("Duplicate CSV headers")
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise ValidationError("Malformed CSV; correct quoting or export again") from exc
    if len(rows) > 5000:
        raise ValidationError("Import preview limited to 5000 rows")
    if any(None in row for row in rows):
        raise ValidationError("CSV has malformed rows")
    return rows, reader.fieldnames


def _validate_import_row(row: dict[str, str], line: int, org_name: str) -> dict[str, Any]:
    title = (row.get("Risk Name") or "").strip()
    client = (row.get("Client") or "").strip()
    if client and client.casefold() != org_name.casefold():
        raise ValidationError(f"Client field '{client}' does not match selected organization")
    _required(title, "Risk Name")
    try:
        likelihood = int((row.get("Probability") or "").strip())
        impact = int((row.get("Impact") or "").strip())
    except (ValueError, TypeError) as exc:
        raise ValidationError("Probability and Impact must be integers 1–5") from exc
    score, _ = StudioService.score(likelihood, impact)
    old_score = (row.get("Risk Score") or "").strip()
    mismatch = old_score not in ("", str(score))
    description = (row.get("Description") or "").strip()
    if len(description) > 10000:
        raise ValidationError("Description too long")
    # Never copy Notion approvals as approved decisions. Preserve former approval info
    # in preview notes only, not authorization metadata.
    return {"source_row":line,"title":title,"description":description,
            "likelihood":likelihood,"impact":impact,"score":score,"mismatch":mismatch,
            "source_score":old_score,"source_status":(row.get("Treatment Status") or "").strip()}


class Phase2Service(StudioService):
    def __init__(self, vault):
        super().__init__(vault)
        self.db.executescript(P2_SCHEMA)
        with self.vault.transaction() as conn:
            conn.execute("PRAGMA user_version=2")
            for key,(title,version,url) in FRAMEWORKS.items():
                conn.execute("INSERT OR IGNORE INTO framework_catalogs VALUES(?,?,?,?)",(key,title,version,url))
            for code,title,domain in NIST_CATEGORIES:
                conn.execute("INSERT OR IGNORE INTO framework_controls VALUES(?,?,?,?)",("NIST-CSF-2.0",code,title,domain))
            for index,title in enumerate(CIS_CONTROLS,1):
                conn.execute("INSERT OR IGNORE INTO framework_controls VALUES(?,?,?,?)",("CIS-CONTROLS-8.1",str(index),title,"CIS Control"))

    def list_risks(self,org: str) -> list[dict[str,Any]]:
        risks=super().list_risks(org)
        residuals={r['risk_id']:r for r in _rows(self.db.execute(
            "SELECT risk_id,likelihood,impact,score,assessed_at FROM residual_risk_current WHERE organization_id=?",(org,)))}
        for risk in risks:
            residual=residuals.get(risk['id'])
            risk['residual_score']=residual['score'] if residual else None
            risk['acceptance_state']=self.acceptance_state(org,risk['id'])
        return risks

    def framework_catalogs(self) -> list[dict[str,Any]]:
        return _rows(self.db.execute("SELECT * FROM framework_catalogs ORDER BY key"))

    def framework_controls(self, key: str) -> list[dict[str,Any]]:
        if key not in FRAMEWORKS:
            raise ValidationError("Unsupported framework")
        return _rows(self.db.execute("SELECT * FROM framework_controls WHERE framework_key=? ORDER BY code",(key,)))

    def create_template(self, org: str, name: str, description: str = "") -> str:
        self._org(org)
        name = _required(name,"Template name")
        if len(description)>2000:
            raise ValidationError("Description too long")
        t=uid(); now=utc_now()
        try:
            with self.vault.transaction() as conn:
                conn.execute("INSERT INTO question_templates VALUES(?,?,?,?,?,?,?)",(t,org,name,description,1,now,now))
                self._audit(conn,org,"template",t,"create")
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Template name already exists") from exc
        return t

    def list_templates(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM question_templates WHERE organization_id=? ORDER BY name",(org,)))

    def _template(self,org: str, template: str) -> dict[str,Any]:
        self._org(org)
        row=self.db.execute("SELECT * FROM question_templates WHERE id=? AND organization_id=?",(template,org)).fetchone()
        if not row:
            raise NotFoundError("Template not found in this organization")
        return dict(row)

    def template_questions(self,org: str,template: str) -> list[dict[str,Any]]:
        self._template(org,template)
        return _rows(self.db.execute("SELECT * FROM template_questions WHERE organization_id=? AND template_id=? ORDER BY sort_order,id",(org,template)))

    def add_template_question(self,org: str,template: str,code: str,prompt: str,domain: str,
                              mapping: tuple[str,str] | None = None,rationale: str = "Topic-only, suggested mapping") -> str:
        self._template(org,template)
        code=_required(code,"Question code",60)
        prompt=_required(prompt,"Question",2500)
        domain=_required(domain,"Domain",100)
        if mapping:
            if not self.db.execute("SELECT 1 FROM framework_controls WHERE framework_key=? AND code=?",mapping).fetchone():
                raise ValidationError("Unknown framework/control identifier")
        q=uid()
        with self.vault.transaction() as conn:
            try:
                position=conn.execute("SELECT coalesce(max(sort_order),0)+1 FROM template_questions WHERE template_id=?",(template,)).fetchone()[0]
                conn.execute("INSERT INTO template_questions VALUES(?,?,?,?,?,?,?)",(q,org,template,code,prompt,domain,position))
                if mapping:
                    conn.execute("INSERT INTO template_control_links VALUES(?,?,?,?,?,?)",(uid(),org,q,mapping[0],mapping[1],rationale))
                conn.execute("UPDATE question_templates SET version=version+1,updated_at=? WHERE id=? AND organization_id=?",(utc_now(),template,org))
                self._audit(conn,org,"template",template,"question_add",{"question_code":code})
            except sqlite3.IntegrityError as exc:
                raise ValidationError("Duplicate question code in template") from exc
        return q

    def create_starter_template(self,org: str) -> str:
        t=self.create_template(org,"Original security baseline starter","Eight original example questions; mappings are not authoritative")
        for code,prompt,domain,nist,cis in STARTER_ITEMS:
            self.add_template_question(org,t,code,prompt,domain,("NIST-CSF-2.0",nist))
            # Add a second topic-only mapping for CIS at the same question.
            q=self.db.execute("SELECT id FROM template_questions WHERE template_id=? AND code=?",(t,code)).fetchone()[0]
            with self.vault.transaction() as conn:
                conn.execute("INSERT INTO template_control_links VALUES(?,?,?,?,?,?)",(uid(),org,q,"CIS-CONTROLS-8.1",cis,"Topic-only, suggested mapping"))
        return t

    def template_mappings(self,org: str,template: str) -> list[dict[str,Any]]:
        self._template(org,template)
        return _rows(self.db.execute("SELECT q.code, l.framework_key,l.control_code,l.rationale FROM template_control_links l JOIN template_questions q ON q.id=l.template_question_id WHERE l.organization_id=? AND q.template_id=? ORDER BY q.sort_order",(org,template)))

    def create_assessment(self,org: str,title: str,scope: str = "",template_id: str | None = None) -> str:
        if template_id is None:
            return super().create_assessment(org,title,scope)
        rec=self._template(org,template_id)
        questions=self.template_questions(org,template_id)
        if not questions:
            raise ValidationError("Add questions to the template first")
        title=_required(title,"Assessment title")
        if len(scope)>2000:
            raise ValidationError("Assessment scope is too long")
        aid,stamp=uid(),utc_now()
        links=self.template_mappings(org,template_id)
        with self.vault.transaction() as conn:
            conn.execute("INSERT INTO assessments VALUES(?,?,?,?,?,?,?,?)",(aid,org,title,scope,
                         "Custom template: "+rec['name']+" (v"+str(rec['version'])+")","draft",stamp,stamp))
            conn.execute("INSERT INTO assessment_template_sources VALUES(?,?,?,?,?)",(aid,org,template_id,rec['version'],stamp))
            for q in questions:
                conn.execute("INSERT INTO assessment_questions VALUES(?,?,?,?,?,?,?,?,?)",(uid(),org,aid,q['code'],q['prompt'],q['domain'],"Unanswered","",stamp))
            for link in links:
                conn.execute("INSERT INTO assessment_control_links VALUES(?,?,?,?,?,?,?)",(uid(),org,aid,link['code'],link['framework_key'],link['control_code'],link['rationale']))
            self._audit(conn,org,"assessment",aid,"create_from_template",{"template_id":template_id,"version":rec['version']})
        return aid

    def assessment_mappings(self,org: str,assessment: str) -> list[dict[str,Any]]:
        self._org(org);self._exists("assessments",assessment,org)
        return _rows(self.db.execute("SELECT question_code,framework_key,control_code,rationale FROM assessment_control_links WHERE organization_id=? AND assessment_id=? ORDER BY question_code",(org,assessment)))

    def set_residual_risk(self,org: str,risk: str,likelihood: int,impact: int,rationale: str) -> int:
        self._org(org);self._exists("risks",risk,org)
        rationale=_required(rationale,"Residual scoring rationale",3000)
        score,_=self.score(likelihood,impact)
        now=utc_now()
        with self.vault.transaction() as conn:
            conn.execute("INSERT INTO residual_risk_current VALUES(?,?,?,?,?,?,?) ON CONFLICT(risk_id) DO UPDATE SET likelihood=excluded.likelihood,impact=excluded.impact,score=excluded.score,rationale=excluded.rationale,assessed_at=excluded.assessed_at",(risk,org,likelihood,impact,score,rationale,now))
            conn.execute("INSERT INTO residual_risk_history VALUES(?,?,?,?,?,?,?,?)",(uid(),org,risk,likelihood,impact,score,rationale,now))
            # Any change to residual risk invalidates existing acceptance; explicit re-approval required.
            conn.execute("UPDATE risks SET status='open',updated_at=? WHERE id=? AND organization_id=? AND status='accepted'",(now,risk,org))
            self._audit(conn,org,"risk",risk,"residual_reassessed",{"score":score})
        return score

    def residual_risk(self,org: str,risk: str) -> dict[str,Any] | None:
        self._org(org);self._exists("risks",risk,org)
        row=self.db.execute("SELECT * FROM residual_risk_current WHERE organization_id=? AND risk_id=?",(org,risk)).fetchone()
        return dict(row) if row else None

    def risk_decisions(self,org: str,risk: str) -> list[dict[str,Any]]:
        self._org(org);self._exists("risks",risk,org)
        return _rows(self.db.execute("SELECT * FROM risk_acceptance_decisions WHERE organization_id=? AND risk_id=? ORDER BY rowid DESC",(org,risk)))

    def record_risk_decision(self,org: str,risk: str,decision: str,approver: str,rationale: str,
                             expires_on: str = "", attested: bool = False) -> str:
        self._org(org);self._exists("risks",risk,org)
        if decision not in {"approved","rejected","revoked"}:
            raise ValidationError("Unsupported acceptance decision")
        approver=_required(approver,"Recorded approver",200)
        rationale=_required(rationale,"Decision rationale",3000)
        if not attested:
            raise ValidationError("Explicit approval attestation required")
        if expires_on:
            try:
                d=date.fromisoformat(expires_on)
            except ValueError as exc:
                raise ValidationError("Expiration date must be YYYY-MM-DD") from exc
            if decision=="approved" and d<=date.today():
                raise ValidationError("Approved acceptance must expire in the future")
        if decision=="approved":
            if not expires_on:
                raise ValidationError("Risk acceptance approval requires expiration date")
            if not self.residual_risk(org,risk):
                raise ValidationError("Record residual risk before approving acceptance")
        did=uid()
        with self.vault.transaction() as conn:
            conn.execute("INSERT INTO risk_acceptance_decisions VALUES(?,?,?,?,?,?,?,?,?)",(did,org,risk,decision,approver,rationale,expires_on,1,utc_now()))
            conn.execute("UPDATE risks SET status=?,updated_at=? WHERE id=? AND organization_id=?",("accepted" if decision=="approved" else "open",utc_now(),risk,org))
            self._audit(conn,org,"risk",risk,"acceptance_"+decision,{"decision_id":did,"expires_on":expires_on,"approver":approver})
        return did

    def acceptance_state(self,org: str,risk: str) -> str:
        self._org(org);self._exists("risks",risk,org)
        row=self.db.execute("SELECT decision,expires_on FROM risk_acceptance_decisions WHERE risk_id=? AND organization_id=? ORDER BY rowid DESC LIMIT 1",(risk,org)).fetchone()
        if not row or row['decision']!='approved':
            return "not_approved"
        if row['expires_on'] and date.fromisoformat(row['expires_on'])<date.today():
            return "expired"
        status=self.db.execute("SELECT status FROM risks WHERE id=? AND organization_id=?",(risk,org)).fetchone()[0]
        return "active" if status=="accepted" else "invalidated"

    def add_evidence(self,org: str,title: str,filename: str,data: bytes,mime_type: str="application/octet-stream") -> str:
        self._org(org)
        title=_required(title,"Evidence title")
        filename=_required(Path(filename).name,"Evidence filename")
        if not isinstance(data,bytes) or not data or len(data)>5*1024*1024:
            raise ValidationError("Evidence must be 1 byte to 5 MiB")
        if len(mime_type)>100:
            raise ValidationError("Invalid media type")
        eid=uid();now=utc_now(); digest=sha256(data).hexdigest()
        with self.vault.transaction() as conn:
            conn.execute("INSERT INTO evidence_records(id,organization_id,title,filename,mime_type,sha256,contents,collected_at,review_status,reviewed_by,review_note,reviewed_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(eid,org,title,filename,mime_type,digest,data,now,"pending","","","",now))
            self._audit(conn,org,"evidence",eid,"upload",{"sha256":digest,"size":len(data)})
        return eid

    def evidence(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        return _rows(self.db.execute("SELECT id,organization_id,title,filename,mime_type,sha256,length(contents) AS size,collected_at,review_status,reviewed_by,review_note,reviewed_at,created_at FROM evidence_records WHERE organization_id=? ORDER BY created_at DESC",(org,)))

    def evidence_bytes(self,org: str,eid: str) -> bytes:
        self._org(org)
        row=self.db.execute("SELECT contents,sha256 FROM evidence_records WHERE organization_id=? AND id=?",(org,eid)).fetchone()
        if not row:
            raise NotFoundError("Evidence not found in this organization")
        contents=bytes(row['contents'])
        if sha256(contents).hexdigest()!=row['sha256']:
            raise ValidationError("Evidence integrity check failed")
        return contents

    def link_evidence(self,org: str,eid: str,target_type: str,target_id: str,relevance: str="") -> str:
        self._org(org)
        if not self.db.execute("SELECT 1 FROM evidence_records WHERE id=? AND organization_id=?",(eid,org)).fetchone():
            raise NotFoundError("Evidence not found in organization")
        if target_type not in {"assessment","risk"}:
            raise ValidationError("Unsupported evidence target")
        self._exists("assessments" if target_type=="assessment" else "risks",target_id,org)
        lid=uid()
        try:
            with self.vault.transaction() as conn:
                conn.execute("INSERT INTO evidence_links VALUES(?,?,?,?,?,?,?)",(lid,org,eid,target_type,target_id,relevance[:500],utc_now()))
                self._audit(conn,org,"evidence",eid,"link",{"target_type":target_type,"target_id":target_id})
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Evidence is already linked to the target") from exc
        return lid

    def evidence_links(self,org: str,eid: str) -> list[dict[str,Any]]:
        self._org(org)
        if not self.db.execute("SELECT 1 FROM evidence_records WHERE id=? AND organization_id=?",(eid,org)).fetchone():
            raise NotFoundError("Evidence not found")
        return _rows(self.db.execute("SELECT * FROM evidence_links WHERE organization_id=? AND evidence_id=?",(org,eid)))

    def review_evidence(self,org: str,eid: str,status: str,reviewer: str,note: str) -> None:
        self._org(org)
        if not self.db.execute("SELECT 1 FROM evidence_records WHERE id=? AND organization_id=?",(eid,org)).fetchone():
            raise NotFoundError("Evidence not found")
        if status not in {"pending","verified","rejected"}:
            raise ValidationError("Unsupported evidence status")
        reviewer=_required(reviewer,"Reviewer",200)
        note=_required(note,"Review note",3000)
        with self.vault.transaction() as conn:
            conn.execute("UPDATE evidence_records SET review_status=?,reviewed_by=?,review_note=?,reviewed_at=? WHERE id=? AND organization_id=?",(status,reviewer,note,utc_now(),eid,org))
            self._audit(conn,org,"evidence",eid,"review",{"status":status,"reviewer":reviewer})

    def preview_notion_csv(self,org: str,payload: bytes) -> dict[str,Any]:
        self._org(org)
        rows,headers=_csv_data(payload)
        needed={"Risk Name","Probability","Impact"}
        if not needed.issubset(set(headers)):
            raise ValidationError("Supported importer expects Notion Risk Register CSV with: Risk Name, Probability, Impact")
        org_name=self.organization(org)['name']
        seen=set(); preview=[]; accepted=[]
        existing_titles={r['title'].casefold() for r in self.list_risks(org)}
        for idx,row in enumerate(rows,2):
            try:
                result=_validate_import_row(row,idx,org_name)
                key=result['title'].casefold()
                if key in seen:
                    raise ValidationError("Duplicate risk name within the CSV")
                seen.add(key)
                if key in existing_titles:
                    raise ValidationError("Risk title already exists in selected organization")
                status="ready"; message="Recalculated score differs from source" if result['mismatch'] else "Validated"
                accepted.append(result)
            except ValidationError as exc:
                status="skip";message=str(exc)
                result={"source_row":idx,"title":(row.get('Risk Name') or '')[:250]}
            preview.append({**result,"status":status,"message":message})
        return {"sha256":sha256(payload).hexdigest(),"count":len(rows),"ready":len(accepted),
                "skipped":len(rows)-len(accepted),"preview":preview,"normalized":accepted,
                "previously_imported":bool(self.db.execute("SELECT 1 FROM notion_import_jobs WHERE organization_id=? AND sha256=?",(org,sha256(payload).hexdigest())).fetchone())}

    def import_notion_csv(self,org: str,payload: bytes,filename: str,*,confirmed: bool=False) -> dict[str,Any]:
        if not confirmed:
            raise ValidationError("Explicit import confirmation required")
        self._org(org)
        snapshot=self.preview_notion_csv(org,payload)
        if snapshot['previously_imported']:
            raise ValidationError("Identical source file was already imported into this organization")
        if snapshot['skipped']:
            raise ValidationError("Resolve or remove invalid/duplicate rows before import; zero partial imports")
        if not snapshot['ready']:
            raise ValidationError("No valid risk records to import")
        file_name=_required(Path(filename).name,"CSV filename",255)
        job=uid(); stamp=utc_now()
        with self.vault.transaction() as conn:
            report={"imported":snapshot['ready'],"source_score_discrepancies":sum(r['mismatch'] for r in snapshot['normalized']),
                    "disclaimer":"Source approval, acceptance, links and evidence are not imported"}
            conn.execute("INSERT INTO notion_import_jobs VALUES(?,?,?,?,?,?,?,?,?)",(job,org,file_name,snapshot['sha256'],"notion_risk_register_csv",snapshot['ready'],0,json.dumps(report),stamp))
            for row in snapshot['normalized']:
                rid=uid()
                conn.execute("INSERT INTO risks VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(rid,org,None,row['title'],row['description'],
                            row['likelihood'],row['impact'],row['score'],
                            f"Notion CSV import: user-entered source values, re-scored with matrix-1; source line {row['source_row']}",
                            "open",stamp,stamp))
                conn.execute("INSERT INTO risk_score_history VALUES(?,?,?,?,?,?,?,?,?)",(uid(),org,rid,row['likelihood'],row['impact'],row['score'],"Notion CSV import; risk assessment rationale requires review","matrix-1",stamp))
                conn.execute("INSERT INTO notion_import_rows VALUES(?,?,?,?,?,?,?)",(uid(),org,job,row['source_row'],rid,"imported","Recalculated; approval not transferred"))
            self._audit(conn,org,"import",job,"completed",report)
        return {"job_id":job,**report}

    def import_history(self,org: str) -> list[dict[str,Any]]:
        self._org(org)
        return _rows(self.db.execute("SELECT id,filename,sha256,imported_count,skipped_count,created_at FROM notion_import_jobs WHERE organization_id=? ORDER BY created_at DESC",(org,)))
