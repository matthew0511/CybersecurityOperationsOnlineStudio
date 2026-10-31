from pathlib import Path
import pytest
from cyberstudio.vault import Vault
from cyberstudio.governance import GovernanceService
from cyberstudio.service import ValidationError,NotFoundError

PW="synthetic-password-very-long-123"

@pytest.fixture
def env(tmp_path):
    with Vault(tmp_path/"governance.csvault",PW,create=True) as vault:
        svc=GovernanceService(vault)
        a=svc.create_organization("Demo One")
        b=svc.create_organization("Demo Two")
        yield svc,a,b

def test_change_cab_validation_and_rollback(env):
    svc,a,b=env
    change=svc.create_change(a,"Synthetic firewall change","normal","Requester","Engineer","high")
    assert svc.changes(b)==[]
    with pytest.raises(NotFoundError):svc._change(b,change)
    with pytest.raises(ValidationError):svc.transition_change(a,change,"submitted","Requester","Request")
    svc.set_change_plan(a,change,"Test firewall rule","Restore backup","Limited outage","2026-12-01T02:00","2026-12-01T03:00")
    svc.transition_change(a,change,"submitted","Requester","Review requested")
    svc.transition_change(a,change,"review","Chair","CAB review")
    with pytest.raises(ValidationError):svc.review_change(a,change,"Requester","approved","Self approval")
    svc.review_change(a,change,"Independent CAB member","approved","Maintenance approved")
    svc.transition_change(a,change,"scheduled","Engineer","Scheduled")
    with pytest.raises(ValidationError):svc.transition_change(a,change,"implementing","Engineer","No precheck")
    svc.add_change_check(a,change,"pre","Configuration backup","pass","Tester","EVID-1")
    svc.transition_change(a,change,"implementing","Engineer","Started")
    svc.transition_change(a,change,"validation","Engineer","Implementation completed")
    with pytest.raises(ValidationError):svc.transition_change(a,change,"completed","Engineer","Missing postcheck")
    svc.add_change_check(a,change,"post","Connectivity test","pass","Tester","EVID-2")
    svc.transition_change(a,change,"completed","Engineer","Validated")
    assert svc.governance_metrics(a)["changes_total"]==1
    assert svc.change_reviews(a,change)[0]["decision"]=="approved"

def test_audit_findings_and_isolation(env):
    svc,a,b=env
    audit=svc.create_audit(a,"Synthetic assessment","internal","Lead","NIST CSF","Test scope")
    with pytest.raises(NotFoundError):svc.add_finding(b,audit,"Cross org","high","not allowed","Owner")
    finding=svc.add_finding(a,audit,"MFA gap","high","MFA not enforced","IT","2026-12-01")
    svc.update_audit_status(a,audit,"fieldwork","Lead")
    svc.update_audit_status(a,audit,"review","Lead")
    with pytest.raises(ValidationError):svc.update_audit_status(a,audit,"closed","Lead")
    svc.update_finding(a,finding,"in_progress","IT",corrective_action="MFA project")
    svc.update_finding(a,finding,"ready_for_verification","IT",corrective_action="MFA enabled")
    with pytest.raises(ValidationError):svc.update_finding(a,finding,"closed","Lead")
    svc.update_finding(a,finding,"closed","Reviewer",evidence_reference="MFA-test",verified_by="Independent reviewer")
    svc.update_audit_status(a,audit,"closed","Lead","Assessment concluded")
    assert svc.governance_metrics(a)["findings_open"]==0
    assert svc.findings(b)==[]
    assert len(svc.governance_events(a))>=7
