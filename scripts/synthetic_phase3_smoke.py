"""Use fictional data to validate Phase 3 end-to-end services and report exports."""
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import date,timedelta

from cyberstudio.vault import Vault
from cyberstudio.phase3 import Phase3Service
from cyberstudio.reports_phase3 import export_executive_pdf,export_executive_xlsx


def main():
    with TemporaryDirectory(prefix='cyberstudio-synthetic-') as temp:
        root=Path(temp)
        with Vault(root/'synthetic.csvault','temporary-demo-password-23456',create=True) as vault:
            svc=Phase3Service(vault)
            org=svc.create_organization('Fictional Cedar Dental Group',industry='Dental health services — synthetic')
            assessment=svc.create_assessment(org,'Synthetic baseline',scope='Illustration only')
            svc.answer_question(org,assessment,'PR-01','Partial','Synthetic devices require additional MFA review')
            risk=svc.add_risk(org,'Privileged MFA inconsistent','Fictional finding only',4,4,'Synthetic scenario',assessment)
            svc.set_residual_risk(org,risk,2,3,'Synthetic corrective action estimate')
            svc.add_task(org,risk,'Deploy phishing resistant MFA','Synthetic Admin',(date.today()+timedelta(days=14)).isoformat())
            evid=svc.add_evidence(org,'Synthetic screenshot','demo.txt',b'No real patient data. Synthetic demonstration.',expires_on=(date.today()+timedelta(days=45)).isoformat())
            svc.review_evidence(org,evid,'verified','Synthetic reviewer','Synthetic demonstration content reviewed')
            svc.evaluate_control(org,'NIST-CSF-2.0','PR.AA','implemented','pass','Synthetic reviewer',
                                 'Example operator-reported test only',evid)
            vendor=svc.create_vendor(org,'Fictional SaaS Provider','SaaS','high','regulated','unknown')
            svc.record_vendor_review(org,vendor,'Synthetic Reviewer','Sample findings: confirmation of continuity plan pending',4,4,
                                     (date.today()+timedelta(days=90)).isoformat(),'needs_remediation')
            svc.add_vulnerability(org,'Synthetic unsupported service','manual','DEMO-2026-001','high',8.1,
                                  'Demo workstation',(date.today()+timedelta(days=21)).isoformat())
            output=Path(__file__).resolve().parents[1]/'examples'
            output.mkdir(exist_ok=True)
            pdf=export_executive_pdf(svc,org,output/'SYNTHETIC_PHASE3_EXECUTIVE_REPORT.pdf')
            excel=export_executive_xlsx(svc,org,output/'SYNTHETIC_PHASE3_EXECUTIVE_REPORT.xlsx')
            print('Synthetic phase3 verified: org, assessment, risk, task, evidence, control, vendor, vulnerability')
            print('Metrics:',svc.executive_metrics(org))
            print('Output:',pdf,excel)

if __name__=='__main__':main()
