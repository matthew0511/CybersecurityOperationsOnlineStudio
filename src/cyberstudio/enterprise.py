"""Extended governance: policy-driven approvals, evidence custody, calendar and board packets.

Single-operator local vault: identities/signatures cannot be independently verified.
"""
from __future__ import annotations
from datetime import datetime, date
from hashlib import sha256
from pathlib import Path
import json
from .governance import GovernanceService
from .service import ValidationError, NotFoundError, _required, _rows, uid, utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS enterprise_approval_policy (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 normal_quorum INTEGER NOT NULL DEFAULT 2 CHECK(normal_quorum BETWEEN 1 AND 10),
 emergency_quorum INTEGER NOT NULL DEFAULT 1 CHECK(emergency_quorum BETWEEN 1 AND 10),
 require_separation INTEGER NOT NULL DEFAULT 1,
 updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS enterprise_approval_votes (
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,change_id TEXT NOT NULL,
 reviewer TEXT NOT NULL,decision TEXT NOT NULL CHECK(decision IN ('approve','reject')),
 rationale TEXT NOT NULL,recorded_at TEXT NOT NULL,
 FOREIGN KEY(change_id,organization_id) REFERENCES governance_changes(id,organization_id),
 UNIQUE(organization_id,change_id,reviewer));
CREATE TABLE IF NOT EXISTS enterprise_evidence (
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,
 title TEXT NOT NULL,source_filename TEXT NOT NULL,mime_type TEXT NOT NULL,
 sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL,classification TEXT NOT NULL,
 collected_by TEXT NOT NULL,collection_notes TEXT NOT NULL DEFAULT '',
 captured_at TEXT NOT NULL,reviewed_by TEXT NOT NULL DEFAULT '',
 reviewed_at TEXT NOT NULL DEFAULT '',review_state TEXT NOT NULL DEFAULT 'pending'
 CHECK(review_state IN ('pending','verified','rejected')),
 expires_on TEXT NOT NULL DEFAULT '',blob BLOB NOT NULL,
 FOREIGN KEY(organization_id) REFERENCES organizations(id));
CREATE TABLE IF NOT EXISTS enterprise_evidence_links (
 organization_id TEXT NOT NULL,evidence_id TEXT NOT NULL,object_type TEXT NOT NULL,
 object_id TEXT NOT NULL,linked_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,evidence_id,object_type,object_id),
 FOREIGN KEY(evidence_id) REFERENCES enterprise_evidence(id));
CREATE TABLE IF NOT EXISTS enterprise_evidence_custody (
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,evidence_id TEXT NOT NULL,
 event TEXT NOT NULL,actor TEXT NOT NULL,notes TEXT NOT NULL,recorded_at TEXT NOT NULL,
 FOREIGN KEY(evidence_id) REFERENCES enterprise_evidence(id));
CREATE TRIGGER IF NOT EXISTS custody_no_update BEFORE UPDATE ON enterprise_evidence_custody
 BEGIN SELECT RAISE(ABORT,'evidence custody history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS custody_no_delete BEFORE DELETE ON enterprise_evidence_custody
 BEGIN SELECT RAISE(ABORT,'evidence custody history is immutable'); END;
"""

class EnterpriseGovernanceService(GovernanceService):
    def __init__(self,vault):
        super().__init__(vault)
        self.db.executescript(SCHEMA)
        self.vault._persist()

    def approval_policy(self,org):
        self._org(org)
        row=self.db.execute("SELECT * FROM enterprise_approval_policy WHERE organization_id=?",(org,)).fetchone()
        return dict(row) if row else {"normal_quorum":2,"emergency_quorum":1,"require_separation":1}

    def set_approval_policy(self,org,normal_quorum=2,emergency_quorum=1,require_separation=True):
        self._org(org)
        for q in (normal_quorum,emergency_quorum):
            if not isinstance(q,int) or isinstance(q,bool) or not 1<=q<=10:
                raise ValidationError("CAB quorum must be from 1 to 10")
        with self.vault.transaction() as c:
            c.execute("""INSERT INTO enterprise_approval_policy VALUES(?,?,?,?,?)
                 ON CONFLICT(organization_id) DO UPDATE SET normal_quorum=excluded.normal_quorum,
                 emergency_quorum=excluded.emergency_quorum,require_separation=excluded.require_separation,
                 updated_at=excluded.updated_at""",
                 (org,normal_quorum,emergency_quorum,int(bool(require_separation)),utc_now()))
            self._event(c,org,"approval_policy",org,"updated","CAB quorum changed","operator")

    def approval_votes(self,org,change_id):
        self._change(org,change_id)
        return _rows(self.db.execute("SELECT * FROM enterprise_approval_votes WHERE organization_id=? AND change_id=? ORDER BY recorded_at",(org,change_id)))

    def record_cab_vote(self,org,change_id,reviewer,decision,rationale):
        change=self._change(org,change_id)
        if change["status"] not in {"submitted","review","approved"}:
            raise ValidationError("Change is not open for approval")
        if decision not in {"approve","reject"}:raise ValidationError("Invalid CAB vote")
        reviewer=_required(reviewer,"Reviewer")
        if self.approval_policy(org)["require_separation"] and reviewer.casefold() in {
            change["requester"].casefold(),change["owner"].casefold()}:
            raise ValidationError("Requester/implementer cannot approve their own change")
        with self.vault.transaction() as c:
            if c.execute("SELECT 1 FROM enterprise_approval_votes WHERE organization_id=? AND change_id=? AND lower(reviewer)=lower(?)",
                         (org,change_id,reviewer)).fetchone():
                raise ValidationError("Reviewer has already voted")
            c.execute("INSERT INTO enterprise_approval_votes VALUES(?,?,?,?,?,?,?)",
                      (uid(),org,change_id,reviewer,decision,_required(rationale,"Rationale",5000),utc_now()))
            self._event(c,org,"change",change_id,"cab_vote_"+decision,rationale,reviewer)
            if decision=="reject":
                c.execute("UPDATE governance_changes SET status='cancelled',updated_at=? WHERE organization_id=? AND id=?",
                          (utc_now(),org,change_id))
            else:
                count=c.execute("SELECT count(*) FROM enterprise_approval_votes WHERE organization_id=? AND change_id=? AND decision='approve'",
                                (org,change_id)).fetchone()[0]
                needed=(self.approval_policy(org)["emergency_quorum"] if change["change_type"]=="emergency"
                        else self.approval_policy(org)["normal_quorum"])
                if count>=needed:
                    c.execute("UPDATE governance_changes SET status='approved',updated_at=? WHERE organization_id=? AND id=?",
                              (utc_now(),org,change_id))
                    self._event(c,org,"change",change_id,"cab_quorum_met",str(count)+" approvals",reviewer)

    def review_change(self,org,ident,reviewer,decision,rationale):
        """Existing button now records quorum votes instead of bypassing approval policy."""
        if decision=="changes_requested":
            change=self._change(org,ident)
            if change["status"] not in {"submitted","review"}:raise ValidationError("Not awaiting review")
            with self.vault.transaction() as c:
                c.execute("UPDATE governance_changes SET status='draft',updated_at=? WHERE organization_id=? AND id=?",
                          (utc_now(),org,ident))
                c.execute("DELETE FROM enterprise_approval_votes WHERE organization_id=? AND change_id=?",(org,ident))
                self._event(c,org,"change",ident,"changes_requested",_required(rationale,"Rationale"),_required(reviewer,"Reviewer"))
            return
        self.record_cab_vote(org,ident,reviewer,"approve" if decision=="approved" else "reject",rationale)

    def transition_change(self,org,ident,status,actor,note):
        change=self._change(org,ident)
        if status=="implementing" and change["change_type"] in {"normal","emergency"}:
            needed=(self.approval_policy(org)["emergency_quorum"] if change["change_type"]=="emergency"
                    else self.approval_policy(org)["normal_quorum"])
            if len([v for v in self.approval_votes(org,ident) if v["decision"]=="approve"])<needed:
                raise ValidationError("CAB quorum not satisfied")
        # GovernanceService checks legacy review records for normal changes; quorum votes replace it.
        if status=="implementing" and change["change_type"]=="normal":
            with self.vault.transaction() as c:
                if not c.execute("SELECT 1 FROM governance_change_reviews WHERE organization_id=? AND change_id=? AND decision='approved'",
                                 (org,ident)).fetchone():
                    c.execute("INSERT INTO governance_change_reviews VALUES(?,?,?,?,?,?,?)",
                              (uid(),org,ident,"CAB quorum (operator record)","approved",
                               "Threshold achieved; no independent identity verification",utc_now()))
        return super().transition_change(org,ident,status,actor,note)

    def add_custody_evidence(self,org,title,filename,blob,collected_by,classification="internal",
                             mime_type="application/octet-stream",notes="",expires_on=""):
        self._org(org)
        if not isinstance(blob,bytes) or not blob or len(blob)>5*1024*1024:
            raise ValidationError("Evidence must be nonempty bytes of at most 5 MiB")
        if classification not in {"public","internal","confidential","restricted"}:
            raise ValidationError("Invalid classification")
        if expires_on:date.fromisoformat(expires_on)
        digest=sha256(blob).hexdigest()
        ident=uid()
        with self.vault.transaction() as c:
            c.execute("INSERT INTO enterprise_evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (ident,org,_required(title,"Title"),Path(filename).name,mime_type,digest,len(blob),
                      classification,_required(collected_by,"Collector"),notes[:2000],utc_now(),
                      "","","pending",expires_on,blob))
            c.execute("INSERT INTO enterprise_evidence_custody VALUES(?,?,?,?,?,?,?)",
                      (uid(),org,ident,"collected",collected_by,"SHA-256 "+digest,utc_now()))
            self._event(c,org,"evidence",ident,"collected","SHA-256 "+digest,collected_by)
        return ident

    def evidence_inventory(self,org):
        self._org(org)
        return _rows(self.db.execute("""SELECT id,organization_id,title,source_filename,mime_type,
                        sha256,size_bytes,classification,collected_by,captured_at,reviewed_by,
                        reviewed_at,review_state,expires_on
                        FROM enterprise_evidence WHERE organization_id=? ORDER BY captured_at DESC""",(org,)))

    def review_custody_evidence(self,org,evidence_id,reviewer,decision,notes):
        self._org(org)
        row=self.db.execute("SELECT collected_by,blob,sha256 FROM enterprise_evidence WHERE organization_id=? AND id=?",
                            (org,evidence_id)).fetchone()
        if not row:raise NotFoundError("Evidence not found in organization")
        if reviewer.strip().casefold()==row["collected_by"].casefold():
            raise ValidationError("Collector cannot self-verify evidence")
        if decision not in {"verified","rejected"}:raise ValidationError("Invalid review decision")
        if sha256(row["blob"]).hexdigest()!=row["sha256"]:raise ValidationError("Evidence hash mismatch")
        with self.vault.transaction() as c:
            c.execute("UPDATE enterprise_evidence SET review_state=?,reviewed_by=?,reviewed_at=? WHERE id=? AND organization_id=?",
                      (decision,_required(reviewer,"Reviewer"),utc_now(),evidence_id,org))
            c.execute("INSERT INTO enterprise_evidence_custody VALUES(?,?,?,?,?,?,?)",
                      (uid(),org,evidence_id,"review_"+decision,reviewer,_required(notes,"Review notes"),utc_now()))
            self._event(c,org,"evidence",evidence_id,"review_"+decision,notes,reviewer)

    def evidence_content(self,org,evidence_id):
        self._org(org)
        row=self.db.execute("SELECT blob,sha256 FROM enterprise_evidence WHERE organization_id=? AND id=?",
                            (org,evidence_id)).fetchone()
        if not row:raise NotFoundError("Evidence not found in organization")
        if sha256(row["blob"]).hexdigest()!=row["sha256"]:raise ValidationError("Evidence integrity failure")
        return bytes(row["blob"])

    def link_custody_evidence(self,org,evidence_id,object_type,object_id):
        self._org(org)
        if object_type not in {"change","audit","finding"}:raise ValidationError("Invalid target type")
        mapping={"change":("governance_changes","id"),"audit":("governance_audits","id"),
                 "finding":("governance_findings","id")}
        table,_=mapping[object_type]
        if not self.db.execute(f"SELECT 1 FROM {table} WHERE id=? AND organization_id=?",(object_id,org)).fetchone():
            raise NotFoundError("Target not found in organization")
        if not self.db.execute("SELECT 1 FROM enterprise_evidence WHERE id=? AND organization_id=?",(evidence_id,org)).fetchone():
            raise NotFoundError("Evidence not in organization")
        with self.vault.transaction() as c:
            c.execute("INSERT OR IGNORE INTO enterprise_evidence_links VALUES(?,?,?,?,?)",
                      (org,evidence_id,object_type,object_id,utc_now()))
            c.execute("INSERT INTO enterprise_evidence_custody VALUES(?,?,?,?,?,?,?)",
                      (uid(),org,evidence_id,"linked","operator",object_type+":"+object_id,utc_now()))
            self._event(c,org,"evidence",evidence_id,"linked",object_type+":"+object_id,"operator")

    def calendar_month(self,org,year,month):
        self._org(org)
        if not 1<=month<=12:raise ValidationError("Invalid month")
        prefix=f"{year:04d}-{month:02d}"
        return [c for c in self.change_calendar(org) if c["start"][:7]==prefix]

    def board_snapshot(self,org):
        result=super().board_snapshot(org)
        evidence=self.evidence_inventory(org)
        today=date.today().isoformat()
        result["enterprise"]={"evidence_total":len(evidence),
            "evidence_verified":sum(e["review_state"]=="verified" and (not e["expires_on"] or e["expires_on"]>=today) for e in evidence),
            "evidence_expired":sum(bool(e["expires_on"] and e["expires_on"]<today) for e in evidence),
            "cab_policy":self.approval_policy(org)}
        return result
