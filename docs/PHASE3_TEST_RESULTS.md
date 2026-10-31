# Phase 3 automated test and smoke verification

**Date:** 2026-10-28  
**Platform:** Headless Linux/Python development container (not Windows 11)  
**Source:** `src/cyberstudio/`, `tests/`, and `scripts/synthetic_phase3_smoke.py`

## Executed results

```
python -m pytest -q
.....................................
38 passed
```

**Additional executed workflows:**

- `python -m compileall -q src tests` completed without syntax errors.
- Synthetic Phase 3 smoke script created an encrypted temporary vault; one organization, one assessment, risk, remediation, reviewed evidence, control evaluation, vendor review, vulnerability; exported PDF and XLSX snapshots. Both files created in `examples/` and begin with expected PDF / workbook signatures.
- Phase 2 vault upgrade test reopened pre-upgrade synthetic records using Phase 3, kept risk and evidence bytes, then reopened the upgraded vault a second time.
- Evidence expiration test recorded a reviewed item, linked a control, then set expiration in the past; evidence-supported passing indicator was recomputed from current freshness.
- Risk approval test verified rejection of missing/incorrect vault passphrase, and a success path with a correct passphrase.
- Cross-org tests rejected foreign evidence and vendor/vulnerability references; report data remained organization-scoped.
- CSV import tests rejected partial files with invalid rows, prevented duplicate imports, and maintained source-unverified status.
- Spreadsheet injection tests confirmed specially crafted titles beginning with `=` and `+` are not interpreted as formulas in workbook cells.

### Actual Notion CSV format validation — temporary vault only

| Export category | Rows imported | Skipped |
|---|---:|---:|
| Compliance Tracker | 2 | 0 |
| Security Policies | 2 | 0 |
| Fictional demo Vendor Assessments | 1 | 0 |
| Incident Response Tracker | 2 | 0 |
| **Total new Phase 3 adapters** | **7** | **0** |

The separate Phase 2 Risk Register adapter previously validated 14 risks. These records were read from the user-supplied ZIP in a disposable test environment and **are not in this package or example exports**.

## Not executed / not proven

- PySide6 is not installed in the current test environment. No live desktop rendering, button-event, keyboard-navigation, or Windows 11 UI acceptance testing was performed.
- No PyInstaller executable was generated and no signed Windows installer exists.
- No formal threat-model review, external penetration test, cryptographic audit, independent compliance evaluation, software composition analysis, or license audit was performed.
- No real customer data or PHI was used, and the app is not validated for any HIPAA-regulated workload.
- Test data volume is small; no realistic stress, power-failure, backup-restore migration, or large evidence workload tests were conducted on Windows.
- Local vault passphrase verification is **not** identity verification of a separate approver. Human review/evidence verification remains operator asserted.

## Regression focus for next build

Model refactoring, migration serialization, vulnerability findings import, strong multiuser approvals, evidence lifecycle policy, performance under many attachments, framework full control licensing, secure update distribution, and independent build verification. See `PHASE3_RELEASE_ROADMAP.md`.
