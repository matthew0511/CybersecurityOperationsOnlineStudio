import pytest
from cyberstudio.vault import Vault
from cyberstudio.vciso import VCISOService, FRAMEWORKS
from cyberstudio.service import ValidationError, NotFoundError

PW="synthetic-long-passphrase-123"

def test_framework_activation_tracking_and_isolation(tmp_path):
    with Vault(tmp_path/"demo.csvault",PW,create=True) as vault:
        s=VCISOService(vault)
        a=s.create_organization("Synthetic Alpha")
        b=s.create_organization("Synthetic Bravo")
        assert len(FRAMEWORKS)==24
        assert sum(f["enabled"] for f in s.frameworks(a))==0
        with pytest.raises(ValidationError):
            s.upsert_implementation(a,"nist-csf","GV.OC","Governance","planned")
        s.configure_framework(a,"nist-csf",True,edition="2.0",owner="Analyst")
        s.upsert_implementation(a,"nist-csf","GV.OC","Governance","planned",owner="Analyst")
        assert s.implementations(b)==[]
        with pytest.raises(ValidationError):
            s.upsert_implementation(a,"nist-csf","GV.OC","Governance","verified")
        s.upsert_implementation(a,"nist-csf","GV.OC","Governance","verified",
                                evidence_reference="synthetic-evidence",verified_by="Reviewer")
        snap=s.board_snapshot(a)
        assert snap["implementation_counts"]["verified"]==1
        assert snap["verified_percent"]==100
        assert snap["overdue_items"]==0
        assert snap["initiatives_overdue"]==0
        s.configure_framework(a,"nist-csf",False)
        assert len(s.implementations(a))==1
        assert s.board_snapshot(a)["assessed_items"]==0
        s.configure_framework(a,"nist-csf",True)
        ident=s.publish_board_snapshot(a,"2026-Q4","Reviewer","Synthetic summary")
        assert s.board_reports(a)[0]["id"]==ident
        with pytest.raises(NotFoundError):
            s.add_board_decision(b,ident,"Invalid cross-organization decision")
        s.add_board_decision(a,ident,"Review roadmap",owner="Board secretary")
        assert len(s.board_decisions(a))==1

def test_vciso_initiatives_and_snapshot_persistence(tmp_path):
    p=tmp_path/"app.csvault"
    with Vault(p,PW,create=True) as vault:
        s=VCISOService(vault)
        org=s.create_organization("Synthetic Org")
        iid=s.upsert_initiative(org,"Implement MFA",owner="IT",due_date="2026-12-01",budget_amount=1000)
        s.upsert_initiative(org,"Implement MFA",owner="IT",status="completed",initiative_id=iid)
        assert s.board_snapshot(org)["initiatives_completed"]==1
        assert s.board_snapshot(org)["initiatives_overdue"]==0
        s.publish_board_snapshot(org,"Q4","vCISO","Synthetic report")
    with Vault(p,PW) as vault:
        s=VCISOService(vault)
        assert len(s.board_reports(org))==1
        assert s.board_snapshot(org)["initiatives_completed"]==1
