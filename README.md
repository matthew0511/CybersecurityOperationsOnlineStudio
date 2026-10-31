Cybersecurity Operations Studio — Phase 3

Desktop source preview v0.3.0 | Windows 11 target | October 28, 2026
An offline-first, single-operator, multi-organization desktop application with assessments, risks, remediation, reference framework controls, custom templates, encrypted evidence, and Phase 3 compliance and operations management.
This is a source-code deliverable, not a signed Windows .exe, HIPAA-certified platform, or production-ready security product. All 38 automated backend tests passed in the development environment. Windows 11 GUI and executable smoke tests remain outstanding because PySide6 was not available in the headless environment. Do not load actual PHI, production passwords, or confidential customer records before Windows testing, independent security review, and a data-protection assessment.
Windows validation kit (added after Phase 3)
Native Windows tests have not been executed in the ChatGPT container. The new scripts/run_windows_validation.ps1 performs native Windows regression testing, Qt offscreen UI smoke tests, an unsigned PyInstaller build, and the frozen executable self-test. The .github/workflows/windows-validation.yml workflow can run this automation on a Windows Server hosted runner; Windows 11 interactive acceptance is still required. Full step-by-step instructions are in docs/WINDOWS_VALIDATION_RUNBOOK.md. The observed results (including the Windows testing blocker) are in docs/WINDOWS_VALIDATION_STATUS.md.
On a Windows 11 x64 machine with Python 3.12 and the Python Launcher installed, double-click scripts\test_windows.bat, or run:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1
​
Review artifacts\windows-validation\windows_validation_results.json. Nothing in this package should be described as passing Windows testing until that script actually runs and reports PASS on Windows.
Features
Module
Implemented functionality
Critical limitation
Local vault
AES-256-GCM encrypted serialized SQLite, Argon2id key derivation, atomic writes, backups
Not SQLCipher; full in-memory serialization, unencrypted PDF/XLSX exports
Organizations
Many client workspaces within one vault, organization-scoped read/write validation
No independent per-client user accounts or cloud multiuser access
Assessments
Versioned custom templates; 8 synthetic baseline questions; basic questionnaire
No official certified questionnaire or control outcome coverage
Frameworks
NIST CSF 2.0 category IDs/headings, CIS Controls v8.1 top-level headings
No full NIST outcomes or licensed CIS safeguard texts
Risk and remediation
Inherent and residual scores, acceptance history, expiration, action tracking
Approver name is operator-attested, not independently authenticated
Evidence
Files <= 5 MiB, hash verification, evidence review, optional expiration and linked control tests
Review is manual; no independent artifact validation
Control evaluations
Per-organization assessment of framework headings, append-only versions, evidence-aware counts
Not proof of framework compliance; no safeguard/subcategory-level assessments
Vendors
Register, criticality, data access, BAA applicability, review history, renewal due
BAA is manually classified; no legal evaluation
Vulnerabilities
Manual findings, CVSS user input, severity, asset label, due date, status history
No scanner or CVE feed integration
Notion migration
Risk Register plus Compliance Tracker, Security Policies, Vendor Assessments, Incident Tracker CSV; dry-run and atomic import
No API sync, relationship reconstruction, bulk ZIP importer, or historical approval trust
Executive reports
PDF and multi-tab Excel snapshot with risk, control, evidence, vendor, vulnerability and imported data
Not certified compliance scores; plaintext reports must be protected
Approvals
Re-enter vault passphrase when recording an acceptance decision
Verifies current vault operator only; not identity/authorization of named approver
Setup on Windows
Install 64-bit Python 3.12 from python.org, choosing the Python Launcher during setup. Extract this archive to a local non-synced directory.
In PowerShell within the extracted folder:
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m cyberstudio
​
Alternatively, double-click scripts/start_windows.bat; it creates a virtual environment on first run, downloads dependencies, and launches the application. An internet connection is required for initial dependency installation, not for normal offline use.
Create or unlock a local vault with a passphrase of at least 12 characters. No recovery service exists. Store an encrypted backup and passphrase securely.
Create an organization and complete the synthetic exercise before using any business data.
In Frameworks, select NIST CSF or CIS Controls metadata; in Controls, record implementation/test results and optional linked evidence. No source metadata implies success.
In Vendors, add suppliers and record dated reviews. In Vulnerabilities, enter findings and track status and due dates.
In Evidence, upload/review artifacts and optionally set an expiration date. Effective status changes to expired in reports when the date passes.
In Notion Import, choose a source type and select an individual CSV from the exported Notion ZIP, inspect the preview, then confirm. Do not select the ZIP directly or mistake imported source statuses for approvals.
In Reports, export executive PDF or Excel snapshots. These are unencrypted plaintext files.
Migrating from Phase 2
Back up the Phase 2 .csvault using Phase 2 Settings, then close the Phase 2 app.
Keep that verified encrypted backup outside the application directory. Protect its passphrase.
Launch Phase 3 with the same OS user account and vault path. The upgrade is additive: the existing evidence table gains expires_on; new v3 tables are created; PRAGMA user_version becomes 3.
Verify existing organizations, questionnaire responses, risks, attachments, exports, acceptance dates, and audit history.
Do not reopen a v3 vault using Phase 1/2 binaries. Forward compatibility is not guaranteed. If a migration fails, restore the original backup only after closing the app.
The default vault is stored in the OS user data folder from platformdirs, usually under the Windows profile, not alongside the source ZIP. A malicious device administrator, malware, unlocked session, system swap file, or plaintext export may still expose information.
Package contents
src/cyberstudio/phase3.py: Phase 3 schema and services; phase2.py, service.py, vault.py are preserved and migrated.
src/cyberstudio/app.py: PySide6 desktop tabs and forms; reports_phase3.py: expanded exports.
tests/: Phase 1, 2 and 3 regression tests.
scripts/synthetic_phase3_smoke.py: fictional sample flow and report generation.
docs/PHASE3_IMPLEMENTATION_SPEC.md: technical schema and data semantics.
docs/PHASE3_NOTION_MIGRATION_GUIDE.md: import mapping and approval limitations.
docs/PHASE3_WINDOWS_QA_CHECKLIST.md: real-device validation gates.
docs/PHASE3_TEST_RESULTS.md: test results and evidence boundaries.
docs/PHASE3_RELEASE_ROADMAP.md: hardening/release tasks.
examples/SYNTHETIC_PHASE3_EXECUTIVE_REPORT.pdf and .xlsx: synthetic examples only.
scripts/build_windows.ps1: local unsigned PyInstaller onedir developer build (not a signed installer).
Building an unsigned developer executable
On a verified Windows workstation, after passing GUI acceptance tests:
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
​
The output is dist\CybersecurityOperationsStudio\, an unsigned developer build. It must be checked on clean Windows 11 VMs, reviewed for dependencies/licenses, and code-signed before release. The current ZIP does not contain a built executable.
Design and safety notes
The app is designed for one local operator. It scopes records by organization, but does not provide cryptographically separate organizational vaults, multiuser identity, RBAC, SSO, background scheduling, automatic vulnerability scanning, or independently verified sign-offs. Imported vendor data and policies are deliberately normalized to unverified; original source claims are preserved in separate notes for review where supported. Framework mappings are topic associations only. Treat this as a working prototype to iterate and verify, not a compliance attestation or suitable clinical data repository.
Authoritative implementation details: docs/PHASE3_IMPLEMENTATION_SPEC.md and code under src/. Older phase-specific documents are retained for history and may describe functionality that was incomplete when written.
