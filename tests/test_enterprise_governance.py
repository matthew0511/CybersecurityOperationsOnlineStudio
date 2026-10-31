import pytest
from cyberstudio.vault import Vault
from cyberstudio.enterprise import EnterpriseGovernanceService
from cyberstudio.service import ValidationError, NotFoundError
from cyberstudio.governance_reports import board_packet

PW="long-synthetic-test-passphrase-123"

def test_quorum_and_evidence_custody(tmp_path):
    with Vault(tmp_path/"test.csvault",PW,create=True) as vault:
        s=EnterpriseGovernanceService(vault)
        org=s.create_organization("Synthetic Alpha")
        other=s.create_organization("Synthetic Bravo")
        s.set_approval_policy(org,normal_quorum=2)
        change=s.create_change(org,"Firewall change","normal","Requester","Implementer")
        s.set_change_plan(org,change,"Deploy and verify","Restore configuration",
                          start_at="2026-12-01T10:00",end_at="2026-12-01T11:00")
        s.transition_change(org,change,"submitted","Requester","For review")
        s.transition_change(org,change,"review","Coordinator","Review")
        with pytest.raises(ValidationError):
            s.record_cab_vote(org,change,"Requester","approve","Not independent")
        s.record_cab_vote(org,change,"Reviewer One","approve","Pass")
        assert s._change(org,change)["status"]=="review"
        with pytest.raises(ValidationError):
            s.record_cab_vote(org,change,"Reviewer One","approve","Duplicate")
        s.record_cab_vote(org,change,"Reviewer Two","approve","Pass")
        assert s._change(org,change)["status"]=="approved"
        s.transition_change(org,change,"scheduled","Implementer","Window approved")
        s.add_change_check(org,change,"pre","Backup verified","pass","Tester")
        s.transition_change(org,change,"implementing","Implementer","Start")
        evidence=s.add_custody_evidence(org,"Configuration backup","backup.txt",b"synthetic",
                                       "Collector","confidential")
        with pytest.raises(ValidationError):
            s.review_custody_evidence(org,evidence,"Collector","verified","Self review")
        s.review_custody_evidence(org,evidence,"Evidence Reviewer","verified","Hash checked")
        s.link_custody_evidence(org,evidence,"change",change)
        assert s.evidence_content(org,evidence)==b"synthetic"
        assert s.evidence_inventory(other)==[]
        with pytest.raises(NotFoundError):
            s.evidence_content(other,evidence)
        assert len(s.calendar_month(org,2026,12))==1
        assert s.board_snapshot(org)["enterprise"]["evidence_verified"]==1
        pdf=board_packet(s,org,tmp_path/"packet.pdf")
        xlsx=board_packet(s,org,tmp_path/"packet.xlsx")
        assert pdf.exists() and pdf.stat().st_size>0
        assert xlsx.exists() and xlsx.stat().st_size>0
