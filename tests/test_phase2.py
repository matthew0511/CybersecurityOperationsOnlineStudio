from __future__ import annotations

import csv
from io import StringIO
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from cyberstudio.phase2 import Phase2Service, NIST_CATEGORIES, CIS_CONTROLS
from cyberstudio.service import NotFoundError, ValidationError
from cyberstudio.vault import Vault

PW="unit-tests-dont-use-production-data"


@pytest.fixture
def setup(tmp_path):
    with Vault(tmp_path/'vault.csvault',PW,create=True) as vault:
        svc=Phase2Service(vault)
        a=svc.create_organization('Alpha')
        b=svc.create_organization('Bravo')
        yield svc,a,b,vault


def csv_bytes(rows):
    stream=StringIO()
    writer=csv.DictWriter(stream,fieldnames=['Risk Name','Description','Probability','Impact','Risk Score','Client','Treatment Status','Sign Off Authorization'])
    writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode()


def sample(name="Insecure admins",**updates):
    r=dict(zip(['Risk Name','Description','Probability','Impact','Risk Score','Client','Treatment Status','Sign Off Authorization'],
               [name,'Admin access risk','4','5','20','','Accepted','Yes']))
    r.update(updates);return r


def test_framework_catalog_metadata_only(setup):
    svc,a,b,_=setup
    assert len(svc.framework_controls('NIST-CSF-2.0'))==len(NIST_CATEGORIES)==22
    assert len(svc.framework_controls('CIS-CONTROLS-8.1'))==len(CIS_CONTROLS)==18
    with pytest.raises(ValidationError):svc.framework_controls('unsupported')


def test_custom_templates_snapshot_mapping_isolation_and_update(setup):
    svc,a,b,_=setup
    t=svc.create_template(a,'Quarterly vendor risk')
    with pytest.raises(ValidationError):svc.create_template(a,'Quarterly vendor risk')
    q=svc.add_template_question(a,t,'V-01','Are vendor contracts reviewed?','Govern',('NIST-CSF-2.0','GV.SC'))
    with pytest.raises(ValidationError):svc.add_template_question(a,t,'V-01','Duplicate','Govern')
    with pytest.raises(ValidationError):svc.add_template_question(a,t,'V-02','Unknown','Govern',('NIST-CSF-2.0','NOPE'))
    with pytest.raises(NotFoundError):svc.template_questions(b,t)
    with pytest.raises(NotFoundError):svc.create_assessment(b,'Cross tenant',template_id=t)
    aid=svc.create_assessment(a,'Spring check',template_id=t)
    assert [x['code'] for x in svc.questions(a,aid)]==['V-01']
    assert [(x['framework_key'],x['control_code']) for x in svc.assessment_mappings(a,aid)]==[('NIST-CSF-2.0','GV.SC')]
    svc.add_template_question(a,t,'V-02','Have providers been reassessed?','Govern')
    assert len(svc.questions(a,aid))==1
    assert len(svc.questions(a,svc.create_assessment(a,'Summer check',template_id=t)))==2
    with pytest.raises(NotFoundError):svc.assessment_mappings(b,aid)


def test_seed_template(setup):
    svc,a,b,_=setup
    template=svc.create_starter_template(a)
    assert len(svc.template_questions(a,template))==8
    assert len(svc.template_mappings(a,template))==16
    assessment=svc.create_assessment(a,'Annual baseline',template_id=template)
    assert len(svc.assessment_mappings(a,assessment))==16
    assert len(svc.questions(a,assessment))==8


def test_residual_acceptance_expiry_and_invalidation(setup):
    svc,a,b,_=setup
    risk=svc.add_risk(a,'Data leaks','',5,4,'High inherent risk')
    with pytest.raises(ValidationError):svc.record_risk_decision(a,risk,'approved','CEO','Accepted',
        (date.today()+timedelta(days=30)).isoformat(),attested=True)
    assert svc.set_residual_risk(a,risk,2,3,'Controls installed')==6
    assert svc.residual_risk(a,risk)['score']==6
    with pytest.raises(NotFoundError):svc.set_residual_risk(b,risk,1,1,'cross org')
    with pytest.raises(ValidationError):svc.record_risk_decision(a,risk,'approved','CEO','Accepted',
        (date.today()+timedelta(days=30)).isoformat(),attested=False)
    with pytest.raises(ValidationError):svc.record_risk_decision(a,risk,'approved','CEO','Accepted',date.today().isoformat(),attested=True)
    decision=svc.record_risk_decision(a,risk,'approved','CEO','Risk is within tolerance',
        (date.today()+timedelta(days=30)).isoformat(),attested=True)
    assert svc.acceptance_state(a,risk)=='active'
    assert svc.list_risks(a)[0]['status']=='accepted'
    svc.set_residual_risk(a,risk,3,4,'Controls reassessed')
    assert svc.acceptance_state(a,risk)=='invalidated'
    assert svc.list_risks(a)[0]['status']=='open'
    assert len(svc.risk_decisions(a,risk))==1
    with pytest.raises(sqlite3.IntegrityError):
        with svc.vault.transaction() as conn:
            conn.execute('DELETE FROM risk_acceptance_decisions WHERE id=?',(decision,))
    svc.record_risk_decision(a,risk,'rejected','CEO','Not yet acceptable',attested=True)
    assert svc.acceptance_state(a,risk)=='not_approved'


def test_evidence_vault_integrity_review_links_and_isolation(setup):
    svc,a,b,v=setup
    risk=svc.add_risk(a,'Weak authentication','',3,4,'Observed')
    ass=svc.create_assessment(a,'Assessment')
    evidence=svc.add_evidence(a,'MFA config','settings.txt',b'redacted example')
    assert svc.evidence_bytes(a,evidence)==b'redacted example'
    assert len(svc.evidence(a))==1
    with pytest.raises(NotFoundError):svc.evidence_bytes(b,evidence)
    with pytest.raises(NotFoundError):svc.link_evidence(b,evidence,'risk',risk)
    with pytest.raises(ValidationError):svc.link_evidence(a,evidence,'arbitrary',risk)
    with pytest.raises(ValidationError):svc.add_evidence(a,'Empty','no.txt',b'')
    with pytest.raises(ValidationError):svc.add_evidence(a,'Huge','huge.bin',b'x'*(5*1024*1024+1))
    svc.link_evidence(a,evidence,'risk',risk)
    svc.link_evidence(a,evidence,'assessment',ass)
    assert len(svc.evidence_links(a,evidence))==2
    with pytest.raises(ValidationError):svc.link_evidence(a,evidence,'risk',risk)
    svc.review_evidence(a,evidence,'verified','Security reviewer','Reviewed date and source')
    assert svc.evidence(a)[0]['review_status']=='verified'
    assert any(x['action']=='review' for x in svc.audit_events(a))
    assert b'redacted example' not in v.path.read_bytes()


def test_import_preview_and_atomic_import(setup):
    svc,a,b,_=setup
    payload=csv_bytes([sample(),sample('Pending logs',**{'Risk Score':'5','Probability':'3','Impact':'3'})])
    preview=svc.preview_notion_csv(a,payload)
    assert preview['ready']==2 and preview['skipped']==0
    assert preview['normalized'][1]['mismatch'] is True
    assert svc.list_risks(a)==[]
    with pytest.raises(ValidationError):svc.import_notion_csv(a,payload,'Risk Register.csv')
    result=svc.import_notion_csv(a,payload,'Risk Register.csv',confirmed=True)
    assert result['imported']==2 and result['source_score_discrepancies']==1
    risks=svc.list_risks(a)
    assert {r['score'] for r in risks}=={20,9}
    assert all(r['status']=='open' for r in risks)
    assert len(svc.import_history(a))==1
    with pytest.raises(ValidationError):svc.import_notion_csv(a,payload,'Risk Register.csv',confirmed=True)
    assert svc.list_risks(b)==[]


def test_import_invalid_rows_never_partially_write(setup):
    svc,a,b,_=setup
    bad=csv_bytes([sample(),sample('Wrong tenant',**{'Client':'Bravo'})])
    preview=svc.preview_notion_csv(a,bad)
    assert preview['ready']==1 and preview['skipped']==1
    with pytest.raises(ValidationError):svc.import_notion_csv(a,bad,'bad.csv',confirmed=True)
    assert svc.list_risks(a)==[] and svc.import_history(a)==[]
    dup=csv_bytes([sample(),sample()])
    assert svc.preview_notion_csv(a,dup)['skipped']==1
    with pytest.raises(ValidationError):svc.import_notion_csv(a,dup,'dup.csv',confirmed=True)
    with pytest.raises(ValidationError):svc.preview_notion_csv(a,b'other,bad,headers\nx,y,z')
    assert svc.preview_notion_csv(a,b'Risk Name,Probability,Impact\nA,0,5')['skipped']==1


def test_phase1_vault_migrates_to_phase2_without_loss(tmp_path):
    from cyberstudio.service import StudioService
    path=tmp_path/'upgrade.csvault'
    with Vault(path,PW,create=True) as v:
        s=StudioService(v);org=s.create_organization('Old Org');aid=s.create_assessment(org,'Old assessment')
        risk=s.add_risk(org,'Old Risk','',3,3,'Basis')
    with Vault(path,PW) as v:
        s=Phase2Service(v)
        assert len(s.questions(org,aid))==8
        assert len(s.list_risks(org))==1
        assert s.set_residual_risk(org,risk,2,2,'Updated controls')==4
    with Vault(path,PW) as v:
        s=Phase2Service(v)
        assert s.residual_risk(org,risk)['score']==4
        assert len(s.framework_controls('CIS-CONTROLS-8.1'))==18


def test_evidence_persists_and_detects_integrity_corruption(tmp_path):
    path=tmp_path/'evidence.csvault'
    with Vault(path,PW,create=True) as vault:
        svc=Phase2Service(vault);org=svc.create_organization('Evidence Org')
        evidence=svc.add_evidence(org,'Synthetic receipt','receipt.txt',b'Example synthetic evidence')
        assert svc.evidence_bytes(org,evidence)==b'Example synthetic evidence'
    with Vault(path,PW) as vault:
        svc=Phase2Service(vault)
        assert svc.evidence_bytes(org,evidence)==b'Example synthetic evidence'
        with vault.transaction() as conn:
            conn.execute("UPDATE evidence_records SET contents=? WHERE id=?",(b'altered',evidence))
        with pytest.raises(ValidationError):svc.evidence_bytes(org,evidence)


def test_notion_import_non_ascii_title_duplicate_detection(setup):
    svc,a,b,_=setup
    risk=svc.add_risk(a,'Straße control gap','',2,2,'Example')
    payload=csv_bytes([sample('STRASSE CONTROL GAP')])
    preview=svc.preview_notion_csv(a,payload)
    assert preview['skipped']==1
    with pytest.raises(ValidationError):svc.import_notion_csv(a,payload,'risk.csv',confirmed=True)
