"""Headless end-to-end Phase 2 smoke test using synthetic records only.

From repository root: python scripts/synthetic_phase2_smoke.py
Requires installed backend dependencies, but no graphical desktop.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cyberstudio.phase2 import Phase2Service
from cyberstudio.reports import export_pdf, export_xlsx
from cyberstudio.vault import Vault


def main() -> int:
    with TemporaryDirectory(prefix="cyberstudio-synthetic-") as d:
        root = Path(d)
        with Vault(root / "sample.csvault", "synthetic-only-passphrase-2026", create=True) as v:
            svc = Phase2Service(v)
            org = svc.create_organization("Synthetic Example Organization")
            template = svc.create_starter_template(org)
            ass = svc.create_assessment(org, "Synthetic Cybersecurity Review", template_id=template)
            svc.answer_question(org, ass, "PR-01", "Partial", "Synthetic example only")
            risk = svc.add_risk(org, "Synthetic Privileged Access Risk", "Example entry", 4, 5,
                                "Fictional evidence from a test scenario", ass)
            svc.set_residual_risk(org, risk, 2, 3, "Synthetic compensating controls")
            svc.record_risk_decision(org, risk, "approved", "Fictional Business Owner",
                                     "Fictional risk tolerance decision",
                                     (date.today() + timedelta(days=60)).isoformat(), attested=True)
            evidence = svc.add_evidence(org, "Synthetic control note", "control-note.txt", b"Synthetic evidence only")
            svc.link_evidence(org, evidence, "risk", risk)
            svc.review_evidence(org, evidence, "verified", "Synthetic Reviewer", "Demo review")
            csv_path = ROOT / "examples" / "SYNTHETIC_NOTION_RISKS.csv"
            preview = svc.preview_notion_csv(org, csv_path.read_bytes())
            assert preview["ready"] == 3 and preview["skipped"] == 0
            outcome = svc.import_notion_csv(org, csv_path.read_bytes(), csv_path.name, confirmed=True)
            pdf = export_pdf(svc, org, root / "sample.pdf")
            xlsx = export_xlsx(svc, org, root / "sample.xlsx")
            assert pdf.read_bytes().startswith(b"%PDF")
            assert xlsx.stat().st_size > 1000
            assert svc.acceptance_state(org, risk) == "active"
            assert len(svc.list_risks(org)) == 4
            assert outcome["imported"] == 3
            print("PASS synthetic end-to-end: template, mapped assessment, risk, residual, acceptance, evidence, CSV import, PDF/XLSX")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
