"""Organization-scoped vCISO governance and framework implementation tracking.

Catalog labels are metadata, not licensed control text, certification, or regulatory advice.
All write operations are audited and stored through the existing encrypted vault.
"""
from __future__ import annotations

from datetime import date
from .phase3 import Phase3Service
from .service import ValidationError, NotFoundError, _required, _rows, uid, utc_now

FRAMEWORKS = (
    ("nist-csf", "NIST Cybersecurity Framework", "governance", "2.0"),
    ("iso-27001", "ISO/IEC 27001", "certification", "2022"),
    ("iso-27002", "ISO/IEC 27002", "guidance", "2022"),
    ("cobit", "COBIT", "governance", "2019"),
    ("cis", "CIS Controls", "controls", "8.1"),
    ("c2m2", "Cybersecurity Capability Maturity Model", "maturity", "2.1"),
    ("nist-800", "NIST SP 800 Series", "collection", "select publication"),
    ("cmmc", "Cybersecurity Maturity Model Certification", "certification", "2.0"),
    ("fedramp", "FedRAMP", "authorization", "select baseline/revision"),
    ("disa-stig", "DISA Security Technical Implementation Guides", "configuration", "select benchmark"),
    ("ascs", "ASCS (edition/authority confirmation required)", "custom", "unverified"),
    ("pci-dss", "PCI DSS", "compliance", "4.0.1"),
    ("soc-2", "SOC 2 Trust Services Criteria", "attestation", "select criteria"),
    ("hipaa", "HIPAA Security Rule", "regulatory", "verify effective edition"),
    ("hitrust", "HITRUST CSF", "certification", "licensed/current edition"),
    ("ffiec-cat", "FFIEC Cybersecurity Assessment Tool (retired)", "legacy", "retired 2025"),
    ("nerc-cip", "NERC CIP", "regulatory", "select enforceable standards"),
    ("iec-62443", "IEC 62443", "industrial", "select part/edition"),
    ("tisax", "TISAX / VDA ISA", "assessment", "select version"),
    ("mitre-attack", "MITRE ATT&CK", "threat-coverage", "select release"),
    ("mitre-d3fend", "MITRE D3FEND", "countermeasure-coverage", "select release"),
    ("cyber-kill-chain", "Lockheed Martin Cyber Kill Chain", "threat-model", "methodology"),
    ("nice", "NICE Workforce Framework", "workforce", "select version"),
    ("scf", "Secure Controls Framework", "controls", "select licensed edition"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS vciso_frameworks(
 organization_id TEXT NOT NULL, framework_key TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
 edition TEXT NOT NULL DEFAULT '', scope TEXT NOT NULL DEFAULT '',
 owner TEXT NOT NULL DEFAULT '', target_date TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL, PRIMARY KEY(organization_id, framework_key),
 FOREIGN KEY(organization_id) REFERENCES organizations(id));
CREATE TABLE IF NOT EXISTS vciso_items(
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL,
 framework_key TEXT NOT NULL, reference TEXT NOT NULL, title TEXT NOT NULL,
 owner TEXT NOT NULL DEFAULT '', due_date TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'not_started'
 CHECK(status IN ('not_started','planned','in_progress','implemented','verified','gap','not_applicable')),
 evidence_reference TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
 verified_by TEXT NOT NULL DEFAULT '', verified_on TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL,
 FOREIGN KEY(organization_id,framework_key) REFERENCES vciso_frameworks(organization_id,framework_key),
 UNIQUE(organization_id,framework_key,reference));
CREATE INDEX IF NOT EXISTS vciso_items_org ON vciso_items(organization_id,framework_key,status);
CREATE TABLE IF NOT EXISTS vciso_initiatives(
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL,
 title TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'strategy',
 owner TEXT NOT NULL DEFAULT '', due_date TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'planned'
 CHECK(status IN ('planned','in_progress','blocked','completed','cancelled')),
 budget_amount REAL NOT NULL DEFAULT 0 CHECK(budget_amount>=0),
 actual_amount REAL NOT NULL DEFAULT 0 CHECK(actual_amount>=0),
 outcome TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
 FOREIGN KEY(organization_id) REFERENCES organizations(id));
CREATE TABLE IF NOT EXISTS vciso_board_reports(
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, period_label TEXT NOT NULL,
 prepared_by TEXT NOT NULL, executive_summary TEXT NOT NULL,
 snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(organization_id) REFERENCES organizations(id));
CREATE TABLE IF NOT EXISTS vciso_board_decisions(
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, report_id TEXT NOT NULL,
 decision TEXT NOT NULL, owner TEXT NOT NULL DEFAULT '',
 due_date TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'open'
 CHECK(status IN ('open','in_progress','closed')),
 recorded_at TEXT NOT NULL,
 FOREIGN KEY(organization_id) REFERENCES organizations(id));
CREATE INDEX IF NOT EXISTS vciso_board_org ON vciso_board_reports(organization_id,created_at);
"""

def _date(value: str) -> str:
    if value:
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError()
        except ValueError as exc:
            raise ValidationError("Date must be YYYY-MM-DD") from exc
    return value

class VCISOService(Phase3Service):
    def __init__(self, vault):
        super().__init__(vault)
        self.db.executescript(SCHEMA)
        self.vault._persist()

    def frameworks(self, org):
        self._org(org)
        saved={r["framework_key"]:r for r in _rows(self.db.execute(
            "SELECT * FROM vciso_frameworks WHERE organization_id=?",(org,)))}
        return [dict(key=k,name=n,kind=kind,default_edition=edition,
                     enabled=bool(saved.get(k,{}).get("enabled",0)),
                     edition=saved.get(k,{}).get("edition",""),
                     scope=saved.get(k,{}).get("scope",""),
                     owner=saved.get(k,{}).get("owner",""),
                     target_date=saved.get(k,{}).get("target_date",""))
                for k,n,kind,edition in FRAMEWORKS]

    def configure_framework(self,org,key,enabled,edition="",scope="",owner="",target_date=""):
        self._org(org)
        if key not in {r[0] for r in FRAMEWORKS}: raise ValidationError("Unknown framework")
        if not isinstance(enabled,bool): raise ValidationError("enabled must be a boolean")
        _date(target_date)
        for value in (edition,scope,owner):
            if len(value)>2000: raise ValidationError("Framework property too long")
        with self.vault.transaction() as c:
            c.execute("""INSERT INTO vciso_frameworks VALUES(?,?,?,?,?,?,?,?)
                 ON CONFLICT(organization_id,framework_key) DO UPDATE SET
                 enabled=excluded.enabled,edition=excluded.edition,
                 scope=excluded.scope,owner=excluded.owner,
                 target_date=excluded.target_date,updated_at=excluded.updated_at""",
                 (org,key,int(enabled),edition.strip(),scope.strip(),owner.strip(),target_date,utc_now()))
            self._audit(c,org,"vciso_framework",key,"configure",{"enabled":enabled,"edition":edition})
    
    def upsert_implementation(self,org,key,reference,title,status,owner="",due_date="",evidence_reference="",notes="",verified_by=""):
        self._org(org)
        row=self.db.execute("SELECT enabled FROM vciso_frameworks WHERE organization_id=? AND framework_key=?",
                            (org,key)).fetchone()
        if not row or not row["enabled"]: raise ValidationError("Activate framework before tracking")
        if status not in {"not_started","planned","in_progress","implemented","verified","gap","not_applicable"}:
            raise ValidationError("Invalid implementation status")
        _date(due_date)
        reference=_required(reference,"Reference",200)
        title=_required(title,"Title",500)
        if status=="verified" and (not verified_by.strip() or not evidence_reference.strip()):
            raise ValidationError("Verification requires reviewer and evidence reference")
        for val in (owner,evidence_reference,notes,verified_by):
            if len(val)>5000: raise ValidationError("Field exceeds maximum length")
        with self.vault.transaction() as c:
            old=c.execute("SELECT id FROM vciso_items WHERE organization_id=? AND framework_key=? AND reference=?",
                          (org,key,reference)).fetchone()
            ident=old["id"] if old else uid()
            c.execute("""INSERT INTO vciso_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                     ON CONFLICT(organization_id,framework_key,reference) DO UPDATE SET
                     title=excluded.title,owner=excluded.owner,due_date=excluded.due_date,
                     status=excluded.status,evidence_reference=excluded.evidence_reference,
                     notes=excluded.notes,verified_by=excluded.verified_by,
                     verified_on=excluded.verified_on,updated_at=excluded.updated_at""",
                (ident,org,key,reference,title,owner.strip(),due_date,status,
                 evidence_reference.strip(),notes.strip(),verified_by.strip(),
                 date.today().isoformat() if status=="verified" else "",utc_now()))
            self._audit(c,org,"vciso_item",ident,"upsert",{"framework":key,"reference":reference,"status":status})
        return ident

    def implementations(self,org,key=None):
        self._org(org)
        if key and key not in {r[0] for r in FRAMEWORKS}: raise ValidationError("Unknown framework")
        query="SELECT * FROM vciso_items WHERE organization_id=?"
        args=[org]
        if key: query+=" AND framework_key=?"; args.append(key)
        return _rows(self.db.execute(query+" ORDER BY framework_key,reference",args))

    def upsert_initiative(self,org,title,category="strategy",owner="",due_date="",status="planned",
                          budget_amount=0,actual_amount=0,outcome="",initiative_id=None):
        self._org(org)
        title=_required(title,"Initiative",500)
        _date(due_date)
        if status not in {"planned","in_progress","blocked","completed","cancelled"}:
            raise ValidationError("Invalid initiative status")
        for amount in (budget_amount,actual_amount):
            if isinstance(amount,bool) or not isinstance(amount,(int,float)) or not 0<=amount<1e12:
                raise ValidationError("Invalid budget value")
        if initiative_id:
            if not self.db.execute("SELECT 1 FROM vciso_initiatives WHERE organization_id=? AND id=?",
                                   (org,initiative_id)).fetchone():
                raise NotFoundError("Initiative not found in organization")
        ident=initiative_id or uid()
        with self.vault.transaction() as c:
            c.execute("""INSERT INTO vciso_initiatives VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title,category=excluded.category,
                owner=excluded.owner,due_date=excluded.due_date,status=excluded.status,
                budget_amount=excluded.budget_amount,actual_amount=excluded.actual_amount,
                outcome=excluded.outcome,updated_at=excluded.updated_at""",
                (ident,org,title,category[:100],owner[:250],due_date,status,
                 budget_amount,actual_amount,outcome[:5000],utc_now()))
            self._audit(c,org,"vciso_initiative",ident,"upsert",{"status":status})
        return ident

    def initiatives(self,org):
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM vciso_initiatives WHERE organization_id=? ORDER BY due_date,title",(org,)))

    def board_snapshot(self,org):
        self._org(org)
        frameworks=self.frameworks(org)
        active=[f for f in frameworks if f["enabled"]]
        items=self.implementations(org)
        enabled={f["key"] for f in active}
        counts={s:sum(i["status"]==s and i["framework_key"] in enabled for i in items)
                for s in ("not_started","planned","in_progress","implemented","verified","gap","not_applicable")}
        eligible=sum(counts[s] for s in counts if s!="not_applicable")
        initiatives=self.initiatives(org)
        today=date.today().isoformat()
        existing=self.overview(org)
        return {"as_of":utc_now(),"organization_id":org,"frameworks_enabled":len(active),
                "frameworks_total":len(frameworks),"implementation_counts":counts,
                "assessed_items":eligible,
                "verified_percent":round(100*counts["verified"]/eligible,1) if eligible else None,
                "overdue_items":sum(1 for i in items if i["due_date"] and i["due_date"] < today
                   and i["status"] not in ("verified","not_applicable")
                   and i["framework_key"] in enabled),
                "initiatives_total":len(initiatives),
                "initiatives_overdue":sum(1 for i in initiatives if i["due_date"] and i["due_date"] < today
                   and i["status"] not in ("completed","cancelled")),
                "initiatives_completed":sum(i["status"]=="completed" for i in initiatives),
                "initiative_budget":round(sum(i["budget_amount"] for i in initiatives),2),
                "initiative_actual":round(sum(i["actual_amount"] for i in initiatives),2),
                "operations":existing,
                "framework_details":[{"key":f["key"],"name":f["name"],
                    "tracked":sum(i["framework_key"]==f["key"] for i in items),
                    "verified":sum(i["framework_key"]==f["key"] and i["status"]=="verified" for i in items)}
                    for f in active],
                "disclaimer":"Operator-recorded evidence and statuses, not an audit or certification."}

    def publish_board_snapshot(self,org,period_label,prepared_by,executive_summary):
        import json
        self._org(org)
        values=[_required(period_label,"Period",100),_required(prepared_by,"Prepared by",250),
                _required(executive_summary,"Executive summary",10000)]
        snapshot=self.board_snapshot(org)
        ident=uid()
        with self.vault.transaction() as c:
            c.execute("INSERT INTO vciso_board_reports VALUES(?,?,?,?,?,?,?)",
                      (ident,org,*values,json.dumps(snapshot,sort_keys=True),utc_now()))
            self._audit(c,org,"vciso_board_report",ident,"publish",{"period":period_label})
        return ident

    def board_reports(self,org):
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM vciso_board_reports WHERE organization_id=? ORDER BY created_at DESC",(org,)))

    def add_board_decision(self,org,report_id,decision,owner="",due_date=""):
        self._org(org); _date(due_date)
        if not self.db.execute("SELECT 1 FROM vciso_board_reports WHERE id=? AND organization_id=?",
                               (report_id,org)).fetchone():
            raise NotFoundError("Board report not found in organization")
        ident=uid()
        with self.vault.transaction() as c:
            c.execute("INSERT INTO vciso_board_decisions VALUES(?,?,?,?,?,?,?,?)",
                      (ident,org,report_id,_required(decision,"Decision",5000),owner[:250],due_date,"open",utc_now()))
            self._audit(c,org,"vciso_board_decision",ident,"create",{"report_id":report_id})
        return ident

    def board_decisions(self,org):
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM vciso_board_decisions WHERE organization_id=? ORDER BY recorded_at DESC",(org,)))
