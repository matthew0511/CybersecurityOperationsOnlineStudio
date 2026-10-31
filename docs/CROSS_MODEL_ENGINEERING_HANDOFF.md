# Cybersecurity Operations Studio — ChatGPT / Claude / Gemini engineering handoff v0.3

**Code of record:** `src/cyberstudio/` in this package; future changes should go into one Git repo. **Documentation of record:** `PHASE3_IMPLEMENTATION_SPEC.md`, `PHASE3_RELEASE_ROADMAP.md` and tests. Previous Phase 1/2 docs are archival context only.

## Module ownership

- **ChatGPT**: domain service and UI integration, schema/migrations, risk/evidence/vendor/vulnerability relations, automated tests, report generation. Include tests and a focused description of modified files with each patch.
- **Claude**: independent threat-model and adversarial code review of `vault.py`, import parsers, unsafe file paths, data isolation, approval model, race conditions, backups, user-controlled input and dependency licensing. Output actionable findings with severity and reproducible attack/test cases where possible. Do not silently rewrite the codebase.
- **Gemini**: independent Windows usability plan and QA; generate edge-case tests for migration, CSV format variance, Unicode, date/time, table relationships, screen reader access, report integrity and installation on fresh VMs. Track expected vs observed behavior.

## Change-request contract

Every proposed update must include: requirement ID, affected modules/services/tables, migration direction and data protection considerations, expected UI changes, acceptance tests, backward compatibility and rollback strategy. Only one branch/change set should be integrated at a time. Never merge independent model-generated rewrites wholesale. If a reviewer spots an unverified claim, label it proposed or tested based on executed evidence.

## Regression commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\synthetic_phase3_smoke.py
.\.venv\Scripts\python.exe -m cyberstudio
```

**Known baseline:** 38 automated tests passed in the headless environment. The GUI command is a **required Windows test**, not a completed result. Do not claim Windows UI, signing, HIPAA suitability, vulnerability scanner integration, framework certified readiness, independent approval authenticity, or independent penetration test completion based on this repository.

## Security review prompts

1. Review encrypted whole-DB serialized SQLite and crash recovery compared with SQLCipher; propose a safer migration path including key management and backups.
2. Attempt to cross-link Org A evidence, vendor and control references into Org B through every public service method and direct UI boundary.
3. Test malicious CSV headers, duplicate/casefold titles, external formula strings, zip bombs, bad encodings, huge files, newline injection, untrusted source URLs, and dangerous attachments.
4. Evaluate the honesty of `verified_pass` terminology and executive indicators. Ensure missing reviews do not turn into positive coverage scores.
5. Test operator authentication replay and ensure named approval authority is not interpreted as an authenticated separate person.
6. Test PDF/XLSX exports for plaintext leakage and injection; verify report snapshots cannot aggregate another organization's records.

## Immediate next sprint

Complete Windows GUI validation and encrypted storage hardening. After that, tackle relational asset inventory, vendor/risk/control/evidence crosslinks, and full migration mapping. Maintain one full-featured license with no artificial subscription-tier feature differences as directed by product strategy.
