"""Deterministic, synthetic Qt UI smoke test for a native Windows runner.

This test can also run on other systems if Qt is installed; only execution on a
Windows machine constitutes Windows runtime evidence.  It does not replace a
human-operated Windows 11/DPI/accessibility or code-signing assessment.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile
import traceback


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline synthetic desktop smoke test")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    # Select Qt's headless platform unless a caller already chose another.
    # Native Qt still runs on Windows; this only avoids interactive prompts.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_OPENGL", "software")

    from PySide6.QtWidgets import QApplication
    from .app import MainWindow
    from .vault import Vault

    app = QApplication.instance() or QApplication([])
    output_dir = args.output_dir
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cyberstudio-qt-synthetic-") as temp:
        with Vault(Path(temp) / "synthetic.csvault", "synthetic-test-password-2026", create=True) as vault:
            # The product uses modal message boxes for errors. Override them
            # only in this test to fail immediately instead of blocking CI.
            class SmokeWindow(MainWindow):
                def message(self, title, message, *, error=False):
                    raise AssertionError(f"Unexpected GUI message ({title}): {message}")

            window = SmokeWindow(vault)
            assert window.tabs.count() == 15, f"Expected 15 tabs, found {window.tabs.count()}"
            expected = {"Dashboard", "Assessments", "Questionnaire", "Risks", "Remediation",
                        "Reports", "Frameworks", "Templates", "Evidence", "Notion Import",
                        "Controls", "Vendors", "Vulnerabilities", "Imported Inventory", "Settings"}
            found = {window.tabs.tabText(i) for i in range(window.tabs.count())}
            assert expected == found, f"GUI tab mismatch: {expected ^ found}"

            org_a = window.service.create_organization("Synthetic Alpha Dental")
            org_b = window.service.create_organization("Synthetic Bravo Dental")
            risk_id = window.service.add_risk(
                org_a, "Synthetic security finding", "No real client data", 3, 4, "Test scenario")
            window.service.add_task(org_a, risk_id, "Test corrective action", "Synthetic owner", "")
            window.service.create_vendor(org_a, "Synthetic SaaS Vendor")
            window.service.add_vulnerability(
                org_a, "Synthetic software issue", "manual", "SYNTH-GUI-001", "high")
            window.load_organizations()
            index_a = window.org_selector.findData(org_a)
            index_b = window.org_selector.findData(org_b)
            assert index_a >= 0 and index_b >= 0, "Organization selector omitted a client"

            window.org_selector.setCurrentIndex(index_a)
            app.processEvents()
            assert window.risk_table.rowCount() == 1, "Org A risk not visible"
            assert window.task_table.rowCount() == 1, "Org A remediation not visible"
            assert window.vendor_table.rowCount() == 1, "Org A vendor not visible"
            assert window.vulnerability_table.rowCount() == 1, "Org A vulnerability not visible"
            window.org_selector.setCurrentIndex(index_b)
            app.processEvents()
            assert window.risk_table.rowCount() == 0, "Org A risk leaked to Org B GUI"
            assert window.task_table.rowCount() == 0, "Org A task leaked to Org B GUI"
            assert window.vendor_table.rowCount() == 0, "Org A vendor leaked to Org B GUI"
            assert window.vulnerability_table.rowCount() == 0, "Org A vulnerability leaked to Org B GUI"

            window.org_selector.setCurrentIndex(index_a)
            window.resize(1280, 800)
            window.show()
            app.processEvents()
            if output_dir:
                image_path = output_dir / "synthetic_qt_dashboard.png"
                assert window.grab().save(str(image_path), "PNG"), "Qt screenshot could not be saved"
                assert image_path.stat().st_size > 1024, "Qt screenshot appears empty"
            window.close()
            app.processEvents()
            result = "PASS: 15 Qt tabs rendered; synthetic organization isolation; UI data refresh; screenshot"
            if output_dir:
                (output_dir / "qt_smoke_result.txt").write_text(result + "\n", encoding="utf-8")
            if sys.stdout is not None:
                print(result)
    app.quit()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        details = traceback.format_exc()
        if sys.stderr is not None:
            sys.stderr.write(details)
        # Also write diagnostics when PyInstaller --windowed has no console.
        try:
            if "--output-dir" in sys.argv:
                i = sys.argv.index("--output-dir")
                dest = Path(sys.argv[i + 1])
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "qt_smoke_failure.txt").write_text(details, encoding="utf-8")
        except Exception:
            pass
        raise SystemExit(1)
