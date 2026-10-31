"""Change governance and audit assurance services. Local operator assertions are not approvals."""
from __future__ import annotations
from datetime import date
from .vciso import VCISOService, _date
from .service import ValidationError, NotFoundError, _required, _rows, uid, utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS governance_changes (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 title TEXT NOT NULL, change_type TEXT NOT NULL CHECK(change_type IN ('standard','normal','emergency')),
 description TEXT NOT NULL DEFAULT '', requester TEXT NOT NULL, owner TEXT NOT NULL,
 risk_level TEXT NOT NULL CHECK(risk_level IN ('low','medium','high','critical')),
 impact TEXT NOT NULL DEFAULT '', implementation_plan TEXT NOT NULL DEFAULT '',
 rollback_plan TEXT NOT NULL DEFAULT '', start_at TEXT NOT NULL DEFAULT '',
 end_at TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'draft'
 CHECK(status IN ('draft','submitted','review','approved','scheduled','implementing','validation','completed','rolled_back','cancelled')),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(id,organization_id));
CREATE INDEX IF NOT EXISTS idx_changes_org ON governance_changes(organization_id,status,start_at);
CREATE TABLE IF NOT EXISTS governance_change_reviews (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, change_id TEXT NOT NULL,
 reviewer TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('approved','rejected','changes_requested')),
 rationale TEXT NOT NULL, recorded_at TEXT NOT NULL,
 FOREIGN KEY(change_id,organization_id) REFERENCES governance_changes(id,organization_id));
CREATE TABLE IF NOT EXISTS governance_change_checks (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, change_id TEXT NOT NULL,
 phase TEXT NOT NULL CHECK(phase IN ('pre','post','rollback')),
 check_name TEXT NOT NULL, result TEXT NOT NULL CHECK(result IN ('pending','pass','fail','not_applicable')),
 evidence_reference TEXT NOT NULL DEFAULT '', tester TEXT NOT NULL DEFAULT '',
 recorded_at TEXT NOT NULL, FOREIGN KEY(change_id,organization_id) REFERENCES governance_changes(id,organization_id));
CREATE TABLE IF NOT EXISTS governance_audits (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 title TEXT NOT NULL, audit_type TEXT NOT NULL CHECK(audit_type IN ('internal','external','regulatory','supplier')),
 framework TEXT NOT NULL DEFAULT '', scope TEXT NOT NULL DEFAULT '',
 lead TEXT NOT NULL, start_date TEXT NOT NULL DEFAULT '', end_date TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'planned'
 CHECK(status IN ('planned','fieldwork','review','closed','cancelled')),
 conclusion TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(id,organization_id));
CREATE TABLE IF NOT EXISTS governance_findings (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, audit_id TEXT NOT NULL,
 title TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('low','medium','high','critical')),
 description TEXT NOT NULL, owner TEXT NOT NULL,
 due_date TEXT NOT NULL DEFAULT '', corrective_action TEXT NOT NULL DEFAULT '',
 management_response TEXT NOT NULL DEFAULT '', evidence_reference TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'open'
 CHECK(status IN ('open','in_progress','ready_for_verification','closed','accepted')),
 verified_by TEXT NOT NULL DEFAULT '', verified_on TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL,
 FOREIGN KEY(audit_id,organization_id) REFERENCES governance_audits(id,organization_id));
CREATE INDEX IF NOT EXISTS idx_findings_org ON governance_findings(organization_id,status,due_date);
CREATE TABLE IF NOT EXISTS governance_events (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, object_type TEXT NOT NULL,
 object_id TEXT NOT NULL, event TEXT NOT NULL, detail TEXT NOT NULL,
 actor TEXT NOT NULL DEFAULT '', recorded_at TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS governance_events_no_update BEFORE UPDATE ON governance_events
 BEGIN SELECT RAISE(ABORT,'governance history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS governance_events_no_delete BEFORE DELETE ON governance_events
 BEGIN SELECT RAISE(ABORT,'governance history is immutable'); END;
"""

def _enum(value, allowed, field):
    if value not in allowed: raise ValidationError("Invalid "+field)
    return value

class GovernanceService(VCISOService):
    def __init__(self,vault):
        super().__init__(vault)
        self.db.executescript(SCHEMA)
        self.vault._persist()

    def _event(self,conn,org,typ,ident,event,detail,actor=""):
        conn.execute("INSERT INTO governance_events VALUES(?,?,?,?,?,?,?,?)",
                     (uid(),org,typ,ident,event,detail,actor,utc_now()))
        self._audit(conn,org,typ,ident,event,{"detail":detail,"actor":actor})

    def _change(self,org,ident):
        self._org(org)
        row=self.db.execute("SELECT * FROM governance_changes WHERE organization_id=? AND id=?",(org,ident)).fetchone()
        if not row: raise NotFoundError("Change not found in organization")
        return dict(row)

    def changes(self,org):
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM governance_changes WHERE organization_id=? ORDER BY created_at DESC",(org,)))

    def create_change(self,org,title,change_type,requester,owner,risk_level="medium",description="",
                      impact="",implementation_plan="",rollback_plan="",start_at="",end_at=""):
        self._org(org)
        _enum(change_type,{"standard","normal","emergency"},"change type")
        _enum(risk_level,{"low","medium","high","critical"},"risk level")
        if start_at:_date(start_at[:10])
        if end_at:_date(end_at[:10])
        if start_at and end_at and start_at>end_at:raise ValidationError("End must follow start")
        fields=(description,impact,implementation_plan,rollback_plan)
        if any(len(v)>10000 for v in fields):raise ValidationError("Text exceeds limit")
        ident=uid();stamp=utc_now()
        with self.vault.transaction() as c:
            c.execute("""INSERT INTO governance_changes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (ident,org,_required(title,"Title",500),change_type,description,
                       _required(requester,"Requester",250),_required(owner,"Owner",250),risk_level,
                       impact,implementation_plan,rollback_plan,start_at,end_at,"draft",stamp,stamp))
            self._event(c,org,"change",ident,"created",change_type,requester)
        return ident

    def set_change_plan(self,org,ident,implementation_plan,rollback_plan,impact="",start_at="",end_at=""):
        change=self._change(org,ident)
        if change["status"] in {"completed","rolled_back","cancelled"}:raise ValidationError("Change is terminal")
        for v in (implementation_plan,rollback_plan,impact):
            if len(v)>10000:raise ValidationError("Text exceeds limit")
        if start_at:_date(start_at[:10])
        if end_at:_date(end_at[:10])
        if start_at and end_at and start_at>end_at:raise ValidationError("Invalid maintenance window")
        with self.vault.transaction() as c:
            c.execute("""UPDATE governance_changes SET implementation_plan=?,rollback_plan=?,impact=?,start_at=?,end_at=?,
                         updated_at=? WHERE id=? AND organization_id=?""",
                      (implementation_plan,rollback_plan,impact,start_at,end_at,utc_now(),ident,org))
            self._event(c,org,"change",ident,"plan_updated","Maintenance window / implementation / rollback",change["owner"])

    def change_reviews(self,org,ident):
        self._change(org,ident)
        return _rows(self.db.execute("SELECT * FROM governance_change_reviews WHERE organization_id=? AND change_id=? ORDER BY recorded_at",(org,ident)))

    def review_change(self,org,ident,reviewer,decision,rationale):
        change=self._change(org,ident)
        if change["status"] not in {"submitted","review"}:raise ValidationError("Change is not awaiting CAB review")
        _enum(decision,{"approved","rejected","changes_requested"},"CAB decision")
        if change["change_type"]=="normal" and reviewer.strip().casefold()==change["requester"].casefold():
            raise ValidationError("Requester cannot self-review a normal change")
        new_status="approved" if decision=="approved" else "draft" if decision=="changes_requested" else "cancelled"
        with self.vault.transaction() as c:
            c.execute("INSERT INTO governance_change_reviews VALUES(?,?,?,?,?,?,?)",
                      (uid(),org,ident,_required(reviewer,"Reviewer"),decision,_required(rationale,"Rationale",5000),utc_now()))
            c.execute("UPDATE governance_changes SET status=?,updated_at=? WHERE id=? AND organization_id=?",
                      (new_status,utc_now(),ident,org))
            self._event(c,org,"change",ident,"cab_"+decision,rationale,reviewer)
        # A recorded reviewer name is not cryptographically authenticated.
    
    def add_change_check(self,org,ident,phase,check_name,result="pending",tester="",evidence_reference=""):
        self._change(org,ident)
        _enum(phase,{"pre","post","rollback"},"check phase")
        _enum(result,{"pending","pass","fail","not_applicable"},"check result")
        if result=="pass" and not tester.strip():raise ValidationError("Passed check requires tester")
        with self.vault.transaction() as c:
            cid=uid()
            c.execute("INSERT INTO governance_change_checks VALUES(?,?,?,?,?,?,?,?,?)",
                      (cid,org,ident,phase,_required(check_name,"Check"),result,evidence_reference[:2000],tester[:250],utc_now()))
            self._event(c,org,"change",ident,"check_"+phase,check_name+":"+result,tester)
        return cid

    def change_checks(self,org,ident):
        self._change(org,ident)
        return _rows(self.db.execute("SELECT * FROM governance_change_checks WHERE organization_id=? AND change_id=? ORDER BY recorded_at",(org,ident)))

    def transition_change(self,org,ident,status,actor,note):
        change=self._change(org,ident)
        allowed={"draft":{"submitted","cancelled"},"submitted":{"review","cancelled"},
                 "review":{"cancelled"},"approved":{"scheduled","cancelled"},
                 "scheduled":{"implementing","cancelled"},"implementing":{"validation","rolled_back"},
                 "validation":{"completed","rolled_back"}}
        if status not in allowed.get(change["status"],set()):raise ValidationError("Invalid change lifecycle transition")
        if status in {"submitted","scheduled","implementing"} and (not change["implementation_plan"].strip() or not change["rollback_plan"].strip()):
            raise ValidationError("Implementation and rollback plans are required")
        if status=="implementing" and change["change_type"]=="normal" and not any(
            r["decision"]=="approved" for r in self.change_reviews(org,ident)):
            raise ValidationError("Normal change requires recorded CAB approval")
        checks=self.change_checks(org,ident)
        if status=="implementing" and not any(x["phase"]=="pre" and x["result"]=="pass" for x in checks):
            raise ValidationError("Pre-implementation validation required")
        if status=="completed" and not any(x["phase"]=="post" and x["result"]=="pass" for x in checks):
            raise ValidationError("Post-implementation validation required")
        with self.vault.transaction() as c:
            c.execute("UPDATE governance_changes SET status=?,updated_at=? WHERE id=? AND organization_id=?",
                      (status,utc_now(),ident,org))
            self._event(c,org,"change",ident,"status_"+status,_required(note,"Transition note",5000),_required(actor,"Actor"))

    def create_audit(self,org,title,audit_type,lead,framework="",scope="",start_date="",end_date=""):
        self._org(org)
        _enum(audit_type,{"internal","external","regulatory","supplier"},"audit type")
        _date(start_date);_date(end_date)
        if start_date and end_date and start_date>end_date:raise ValidationError("Invalid audit dates")
        ident=uid();stamp=utc_now()
        with self.vault.transaction() as c:
            c.execute("INSERT INTO governance_audits VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (ident,org,_required(title,"Audit title",500),audit_type,framework[:250],scope[:5000],
                       _required(lead,"Audit lead",250),start_date,end_date,"planned","",stamp,stamp))
            self._event(c,org,"audit",ident,"created",audit_type,lead)
        return ident

    def audits(self,org):
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM governance_audits WHERE organization_id=? ORDER BY created_at DESC",(org,)))

    def _audit_record(self,org,ident):
        self._org(org)
        row=self.db.execute("SELECT * FROM governance_audits WHERE organization_id=? AND id=?",(org,ident)).fetchone()
        if not row:raise NotFoundError("Audit not found in organization")
        return dict(row)

    def update_audit_status(self,org,ident,status,actor,conclusion=""):
        record=self._audit_record(org,ident)
        next_status={"planned":{"fieldwork","cancelled"},"fieldwork":{"review","cancelled"},
                     "review":{"closed","fieldwork"}}
        if status not in next_status.get(record["status"],set()):raise ValidationError("Invalid audit transition")
        if status=="closed" and not conclusion.strip():raise ValidationError("Audit conclusion required")
        with self.vault.transaction() as c:
            c.execute("UPDATE governance_audits SET status=?,conclusion=?,updated_at=? WHERE organization_id=? AND id=?",
                      (status,conclusion[:5000],utc_now(),org,ident))
            self._event(c,org,"audit",ident,"status_"+status,conclusion,_required(actor,"Actor"))

    def add_finding(self,org,audit_id,title,severity,description,owner,due_date="",corrective_action="",management_response=""):
        record=self._audit_record(org,audit_id)
        if record["status"] in {"closed","cancelled"}:raise ValidationError("Audit closed")
        _enum(severity,{"low","medium","high","critical"},"severity");_date(due_date)
        ident=uid()
        with self.vault.transaction() as c:
            c.execute("INSERT INTO governance_findings VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (ident,org,audit_id,_required(title,"Finding",500),severity,
                       _required(description,"Description",5000),_required(owner,"Owner",250),due_date,
                       corrective_action[:5000],management_response[:5000],"","open","","",utc_now()))
            self._event(c,org,"finding",ident,"created",severity,owner)
        return ident

    def findings(self,org,audit_id=None):
        self._org(org)
        if audit_id:self._audit_record(org,audit_id)
        q="SELECT * FROM governance_findings WHERE organization_id=?";args=[org]
        if audit_id:q+=" AND audit_id=?";args.append(audit_id)
        return _rows(self.db.execute(q+" ORDER BY updated_at DESC",args))

    def update_finding(self,org,ident,status,actor,corrective_action="",management_response="",evidence_reference="",verified_by=""):
        self._org(org)
        row=self.db.execute("SELECT * FROM governance_findings WHERE organization_id=? AND id=?",(org,ident)).fetchone()
        if not row:raise NotFoundError("Finding not found")
        steps={"open":{"in_progress","accepted"},"in_progress":{"ready_for_verification","accepted"},
               "ready_for_verification":{"closed","in_progress"}}
        if status not in steps.get(row["status"],set()):raise ValidationError("Invalid finding transition")
        if status=="closed" and (not verified_by.strip() or not evidence_reference.strip()):
            raise ValidationError("Closure requires verification reviewer and evidence reference")
        with self.vault.transaction() as c:
            c.execute("""UPDATE governance_findings SET status=?,corrective_action=?,management_response=?,
                evidence_reference=?,verified_by=?,verified_on=?,updated_at=? WHERE id=? AND organization_id=?""",
                (status,corrective_action[:5000],management_response[:5000],evidence_reference[:2000],
                 verified_by[:250],date.today().isoformat() if status=="closed" else "",utc_now(),ident,org))
            self._event(c,org,"finding",ident,"status_"+status,corrective_action,_required(actor,"Actor"))

    def governance_events(self,org):
        self._org(org)
        return _rows(self.db.execute("SELECT * FROM governance_events WHERE organization_id=? ORDER BY recorded_at DESC",(org,)))

    def governance_metrics(self,org):
        changes=self.changes(org);audits=self.audits(org);findings=self.findings(org);today=date.today().isoformat()
        return dict(changes_total=len(changes),changes_pending_cab=sum(c["status"] in {"submitted","review"} for c in changes),
                    changes_rolled_back=sum(c["status"]=="rolled_back" for c in changes),
                    emergency_changes=sum(c["change_type"]=="emergency" for c in changes),
                    changes_scheduled=sum(c["status"] in {"approved","scheduled","implementing"} for c in changes),
                    audits_open=sum(a["status"] not in {"closed","cancelled"} for a in audits),
                    findings_open=sum(f["status"] not in {"closed","accepted"} for f in findings),
                    findings_high_critical=sum(f["severity"] in {"high","critical"} and f["status"] not in {"closed","accepted"} for f in findings),
                    findings_overdue=sum(bool(f["due_date"] and f["due_date"]<today and f["status"] not in {"closed","accepted"}) for f in findings))

    def board_snapshot(self,org):
        snapshot=super().board_snapshot(org)
        snapshot["governance"]=self.governance_metrics(org)
        return snapshot

    def change_calendar(self,org):
        """Rows for schedule display and future calendar integration."""
        return [dict(id=c["id"],title=c["title"],start=c["start_at"],end=c["end_at"],
                     owner=c["owner"],status=c["status"],risk=c["risk_level"])
                for c in self.changes(org) if c["start_at"]]
