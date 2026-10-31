# Phase 3 Windows 11 acceptance checklist

**Status: NOT YET EXECUTED ON WINDOWS.** This checklist is a test plan; checking an item requires execution evidence, ideally including date, device image version, OS build, app commit hash, tester and screenshots/logs sanitized of confidential data.

## A. First-launch and dependencies

- [ ] Fresh Windows 11 64-bit VM, no Python preinstalled: verify instructions and error messaging for `start_windows.bat`.
- [ ] Windows 11 64-bit with Python 3.12: install package, launch `python -m cyberstudio`, confirm 15 tabs render; scroll when narrow.
- [ ] Verify Windows user vault path under `%LOCALAPPDATA%` or OS profile selected by `platformdirs`.
- [ ] New vault accepts >=12-char password; rejects shorter passphrase; wrong password cannot unlock.
- [ ] UI remains usable at 100%, 125% and 150% DPI; keyboard navigation and screen-reader labels evaluated.
- [ ] No network required after dependencies have been installed.

## B. Upgrade and recovery

- [ ] Back up real **test** Phase 2 vault; record synthetic organization/risk/evidence identifiers.
- [ ] Launch Phase 3 and unlock; verify all preserved records and attached evidence integrity.
- [ ] Restart app; confirm `PRAGMA user_version=3` and records survive after closing.
- [ ] Backup created; restore to a new Windows user profile in an isolated VM; confirm passphrase and records.
- [ ] Simulate crash or storage failure during commit; check no lost/corrupted encrypted vault and reasonable error messages.
- [ ] App refuses concurrent writes to the same vault by two processes; test lock behavior on unexpected shutdown.
- [ ] Test with removable disk/limited free space (do not use real customer data).

## C. Organization scope and roles

- [ ] Create Org A and Org B; create assessment, evidence, risk, vendor, vulnerability and imports in Org A.
- [ ] Switch to Org B; all tables, counts, history and exports must omit Org A records.
- [ ] Attempt cross-org risk/evidence link and control evidence linking through service calls: must fail.
- [ ] Confirm this is a **single-user owner model**, not multiuser RBAC or identity-integrated approval.

## D. Workflows and human factors

- [ ] Assessments and custom templates: add questions, snapshot, answer, restart, preserve state.
- [ ] Inherent vs residual score math and risk band boundaries; acceptance expiration behavior.
- [ ] Named acceptance decision requires operator's current vault passphrase; wrong password rejected.
- [ ] Record and re-test a control; older evaluations remain immutable; current pointer updates.
- [ ] Expire reviewed evidence; internal evidence-supported pass count decreases without retroactively rewriting evaluation history.
- [ ] Vendor has missing review state initially; review creates proper due date and score; overdue behavior tested via a controlled system date.
- [ ] Vulnerability status transition creates immutable history; high/critical open metrics update.
- [ ] UI supports input error messages; cancel actions leave no writes; partial dialogs do not create malformed entries.

## E. Notion CSV import

- [ ] Import synthetic risk CSV and all four Phase 3 supported CSV types individually.
- [ ] Simulate blank/duplicate column names, bad dates, wrong Client name, repeated record name, duplicate file hash, oversized file, malformed CSV.
- [ ] Review preview before import; invalid row prevents **any** insert, including import-job record.
- [ ] Verify source approved/compliant/resolved statuses remain **unverified**, and no evidence file is copied from a URL.
- [ ] Verify real Notion companion `_all.csv` would be rejected if duplicating primary import.
- [ ] Inspect imported vendor source annotations against original row, including BAA and tier. Confirm they do not become approved fields.

## F. Reports, security and packaging

- [ ] PDF snapshot opens in a supported PDF viewer; tables and Unicode titles display/escape correctly, no clipped rows.
- [ ] Excel workbook opens in Microsoft Excel; ten sheets show correct selected-org data; formulas from input are inert text.
- [ ] Reports and extracted evidence are plaintext — verify file dialogs and user messaging.
- [ ] Confirm SHA-256 integrity rejection on altered encrypted evidence contents.
- [ ] Static dependency audit with pinned versions, license/attribution review, and third-party code review.
- [ ] Build PyInstaller `onedir`; run on clean Windows VMs without Python, then antivirus and SmartScreen checks.
- [ ] Independent penetration/security review and privacy/data-handling review; resolve critical/high issues.
- [ ] Authenticode code-sign installer and binary, clean setup/uninstall, reproducible release artifact checksums.
- [ ] Verify actual framework metadata redistribution rights and claims in UI/marketing.

## Acceptance blockers

Until this checklist is actually executed and documented, the ZIP remains a **developer source preview** and should not be sold as independently assured security/compliance software or entrusted with clinical information.
