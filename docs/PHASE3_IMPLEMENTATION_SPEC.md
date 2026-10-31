# Cybersecurity Operations Studio — Phase 3 Implementation Specification

**Version:** 0.3.0 — 2026-10-28  
**Baseline:** Phase 2 source, existing Notion Cybersecurity Operations Hub export, and prior architecture design.  
**Implementation status:** Source code implemented and 38 automated backend tests passing. **Windows GUI and release security validation not performed.**

## 1. Product and architectural scope

A single-user Windows 11 desktop prototype sold eventually as a one-time purchase, with an unlimited number of logically separated organizations. All functionality is included in one product; there is no feature-tier system. A single local vault operator can select any organization. Records are scoped by `organization_id` in service queries and foreign keys; organizational separation is not equivalent to separate vault users or strong multitenancy isolation. No online account, server, AI service, or subscription is necessary.

**Layers**

1. PySide6 UI (`app.py`): event-driven forms, tables and report/export controls. User inputs are validated in the service layer, not trusted based on UI widgets.
2. Domain services (`service.py`, `phase2.py`, `phase3.py`): deterministic calculations, constraints, organization checks, audit events and import validation.
3. SQLite in-memory database in `vault.py`: generated from decrypted authenticated vault bytes, `PRAGMA foreign_keys=ON`.
4. Encrypted persistence: serialize full SQLite state after each committed transaction; password+Argon2id yields an AES-256-GCM key; random nonce and authenticated headers; atomic replacement of encrypted file; separately copied encrypted backups.
5. Reports (`reports.py`, `reports_phase3.py`): static unencrypted PDF/XLSX snapshots with user-entered data and disclaimers.

This is **not SQLCipher**. Full-state serializing is inefficient with large stores and is not equivalent to page-level encryption. Memory, OS swap/crash dumps, plaintext CSV/PDF/XLSX, clipboard, operating-system malware, passphrase loss, and device administrator access are not addressed by the vault. Do not use real PHI before a dedicated security architecture revision and comprehensive validation.

## 2. Baseline tables preserved

All Phase 1/2 tables remain, including `organizations`, `assessments`, `assessment_questions`, `risks`, `risk_score_history`, `remediation_tasks`, `task_history`, `audit_events`, `framework_catalogs`, `framework_controls`, `question_templates`, `template_questions`, `assessment_control_mappings`, `residual_risk_current/history`, `risk_acceptance_decisions`, `evidence_records`, `evidence_links`, `notion_import_jobs/rows`. The source files remain authoritative for column names. The v3 upgrade adds `expires_on TEXT NOT NULL DEFAULT ''` to the existing `evidence_records` table, preserving old records.

## 3. Phase 3 new database entities

| Table | Key columns | Relationships / invariants |
|---|---|---|
| `control_evaluations` | UUID, org, framework_key, control_code, implementation, test_result, rationale, evaluator, evaluated_at, evidence_id nullable, evidence_verified | Append-only, FK to framework controls, optional same-org FK to evidence. Does not prove success |
| `control_evaluation_current` | (org, framework, code) PK, evaluation_id | One latest pointer to an immutable evaluation; FK enforces same-org |
| `vendors` | UUID, org, name, category, criticality, data_access, baa_applicability, owner, status | Unique (org,name); enum validations; no approved BAA inferred |
| `vendor_reviews` | UUID, org, vendor, reviewer, findings, risk_score, review_date, next_review_date, decision | Append-only; same-org FK; score uses 1–25 matrix; required future review date |
| `vendor_import_annotations` | vendor_id PK, org, source_findings, source_status, source_criticality, source_baa | External source claims preserved separately and **not** converted to trustworthy decisions |
| `vulnerabilities` | UUID, org, title, source, external_id, asset_name, CVSS optional, severity, status, identified_on, due_on, notes | Unique (org,source,external_id); statuses validated; CVSS entered manually |
| `vulnerability_history` | UUID, org, vulnerability_id, old/new status, actor, reason, time | Append-only same-org FK |
| `security_policies` | UUID, org, title, version, owner, next_review_on, status, source_url | Imports use `unverified` status, not Notion approval |
| `incident_records` | UUID, org, title, source incident id, severity/status source fields, timestamps, root cause, imported_unverified | A source inventory, NOT a full incident response orchestration module |
| `imported_control_inventory` | UUID, org, title, source ID/standard, source implementation, source evidence URL, source review date, verification | Distinct from actual `control_evaluations`; imported statuses are `unverified` |
| `notion_import_jobs_p3` | UUID, org, source_type, filename, SHA-256, imported count, created_at | Unique (org,type,hash); immutable; audit entry created on commit |

Indexes cover organization, status and join keys. History, evaluation and import tables have no-update/no-delete triggers. App transactions create audit entries for user actions. There is no production-grade actor authenticity verification: records are not digitally signed, and the same vault operator can enter arbitrary names as reviewers.

**Migration:** Phase 3 service initializes existing schemas, checks whether `evidence_records.expires_on` exists using `PRAGMA table_info`, adds it only if missing, creates v3 tables via `CREATE TABLE IF NOT EXISTS`, sets `PRAGMA user_version=3`, and persists. This is a best-effort additive migration, not a transactional Alembic/SQLCipher migration. Back up first; test failure and restore on Windows.

## 4. Control effectiveness — semantics

`evaluate_control(org, framework_key, control_code, implementation, test_result, evaluator, rationale, evidence_id?)` accepts:

- `implementation`: `not_assessed`, `planned`, `partial`, `implemented`, `not_applicable`.
- `test_result`: `not_tested`, `pass`, `partial`, `fail`, `not_applicable`.
- `test_result=pass` requires `implementation=implemented`; `implementation=not_applicable` requires matching not-applicable test.
- Framework ID/code must exist in the local reference catalog, which contains **headings/identifiers only**, not exhaustive requirements.
- Evidence, if supplied, must belong to the same organization. At review time, the evaluation stores whether its evidence was reviewed and unexpired; the **current** effective evidence status is recalculated when reporting.
- `verified_pass = operator-reported pass AND implemented AND currently reviewed/unexpired linked evidence`. This is an **internal indicator**, not a validation of the sufficiency, accuracy, or independence of evidence.

Each change adds an immutable evaluation record; `control_evaluation_current` points to the most recent evaluation. A declined or failed evaluation remains visible in historical database records but the UI currently lists current results only. No universal readiness percentage is calculated: the app has not loaded all official framework subcategory/safeguard outcome requirements.

## 5. Vendor oversight

A vendor registration captures name, service category, criticality `low|moderate|high|critical`, data access `unknown|none|internal|confidential|regulated`, BAA applicability `unknown|yes|no|not_applicable`, owner and status.

Each independent vendor review requires reviewer, findings, likelihood/impact (each integer 1–5), a future `next_review_date`, and disposition `pending|needs_remediation|reviewed`. Scores use `likelihood × impact`. `review_state` reports `missing` if no review exists, `overdue` if the most recent next-review date passed, otherwise the current review disposition. It does not schedule email reminders or automatically change decisions on disk.

Notion vendor imports deliberately set new vendor criticality to `moderate`, BAA applicability and data access to `unknown` even if the CSV asserts values. Original CSV findings, tier, BAA applicability and status are stored in `vendor_import_annotations` for an operator to inspect. This prevents unsafe transfer of historical approvals.

## 6. Vulnerability management

Vulnerability records capture a manual source, optional identifier, asset label, severity, optional numeric CVSS v3/v4 *user-entered score*, status, discovered date, remediation date and free-text notes. No CVE, NVD, EPSS or KEV data is fetched; user-entered CVSS is not scored or recalculated. Identifiers are deduplicated per organization and source. Blank identifiers receive unique internal placeholders to avoid false duplicate collisions.

Allowed statuses: `open`, `in_progress`, `mitigated`, `accepted`, `false_positive`. Changing status requires a named operator and rationale and writes immutable history. This `accepted` vulnerability status is not a formal risk acceptance in the separate risk module. A due date older than the current local date counts as overdue for all statuses except mitigated or false positive.

## 7. Evidence freshness

Evidence bytes remain in the authenticated encrypted vault with SHA-256 digest checks on retrieval. `expires_on` may be empty or ISO YYYY-MM-DD. Effective status is `expired` when expiration is **before** today's local calendar date, otherwise the preserved operator review status. An expired verified file no longer satisfies the internal evidence-supported passing-control indicator. The original review status is never silently rewritten. A file may remain retained after expiration; no background deletion or automatic retention policy exists.

## 8. Risk acceptance and local reauthentication

Phase 3 overrides the Phase 2 acceptance method to require `operator_passphrase`. The vault performs Argon2id derivation of the candidate and constant-time comparison against the unlocked key; acceptance rejects missing/incorrect passwords. When successful, the Phase 2 method retains its existing requirement for documented rationale, named approver, explicit attestation, residual risk and an expiration date for an approval. A new audit event records vault-operator reauthentication.

**Important:** This confirms only that the current operator knows the passphrase. It does not independently authenticate the **named approving authority**, prove RBAC, support second-person approval, non-repudiation or secure electronic signatures. User-supplied names are assertions. Stronger SoD/multiuser workflow is a release blocker for organizations requiring such approvals.

## 9. Notion import adapters

The existing Risk Register import is preserved (`phase2.py`). Phase 3 adds four individual CSV types:

| Source database | Required CSV headers | Destination | Trust policy |
|---|---|---|---|
| Compliance Tracker | Control Name, Control ID, Implementation Status | `imported_control_inventory` | Status and reference links remain unverified |
| Security Policies | Policy Name, Approval Status | `security_policies` | Imported policy status always `unverified` |
| Vendor Assessments | Vendor Name, Assessment Status | `vendors` + `vendor_import_annotations` | Original claims preserved separately; no approved vendor state |
| Incident Response Tracker | Incident Name, Status | `incident_records` | Status is a source label; `imported_unverified=1` |

The importer requires UTF-8, well-formed CSV <= 4 MiB and <= 5000 rows, validates required column names, required primary names, optional `Client` organization match, date format, lengths, case-insensitive title duplicates, and file hash duplicate per organization and source type. All source rows must be ready and the operator must confirm. Each import is a single vault transaction: a failure prevents partially imported data.

No APIs or URLs are followed, no Notion relational references are reconstructed, and no Notion attachment contents are copied. The CSV is an **incomplete export of Notion's relational/rollup semantics**. `*_all.csv` companions often contain duplicate views; importing both is intentionally rejected on duplicate titles.

## 10. Executive indicators and report structure

`executive_metrics(org)` returns raw counts only: open inherent/residual risk at threshold >=10, active/expired acceptance states, total/current controls tested, evidence-supported passes, expired/unverified evidence, missing/overdue vendor reviews, high/critical open vulnerabilities, overdue vulnerabilities, and overdue remediation.

`reports_phase3.py` generates:

- PDF: organization, UTC timestamp, 13 aggregate indicators, ten highest inherent risks, disclosure.
- XLSX: Executive Overview, Risks, Remediation, Control Evaluations, Vendors, Vulnerabilities, Evidence Inventory, Imported Controls, Policies, and Incident Inventory.

All free-text Excel values are escaped against formula execution. XML-sensitive PDF fields are escaped. The reports do **not** compute a certified percent ready or infer compliance from mapped questions. PDF/XLSX are unencrypted; secure them outside the app.

## 11. Desktop screens and interactions

Original tabs: Dashboard, Assessments, Questionnaire, Risks, Remediation, Reports, Frameworks, Templates, Evidence, Notion Import, Settings.

New tabs: Controls (framework title, implementation, testing, evaluator, optional evidence); Vendors (create, review); Vulnerabilities (manual entry, status changes); Imported Inventory (read-only view of migrated controls/policies/incidents). The Dashboard now shows high-risk vulnerabilities, missing/overdue vendor reviews and expired evidence. Evidence adds an expiration action. Risk acceptance adds masked vault-passphrase confirmation. Reports use the new Phase 3 exporters. Import adds a source-type selector.

**GUI testing remains outstanding**: PySide6 was not available on the headless development runner. Static compilation passes but does not establish that every dialog renders or behaves correctly on Windows.

## 12. Tests, migration and release acceptance

- Current automated suite: **38 tests passed** (Phase 1 + Phase 2 + Phase 3).
- Upgrade test: Phase 2 vault to Phase 3 retains existing risks and evidence across close/reopen.
- Domain tests: organization isolation, control mapping/acceptance constraints, evidence expiry and hash, vendor review history, vulnerability status, vault reauthentication, import atomicity, duplicate checks, report generation, spreadsheet-injection prevention.
- Private Notion export validation **performed only in disposable vault**: two compliance controls, two policies, one fictional demonstration vendor and two incidents imported successfully with zero skips. **No exported user data is bundled**.
- Synthetic end-to-end workflow and sample reports generated; on-device GUI, executable, signed installer and external security assessment remain pending.

See `PHASE3_WINDOWS_QA_CHECKLIST.md` and `PHASE3_RELEASE_ROADMAP.md` before real customer deployments or Gumroad distribution.

## 13. Collaboration guidance

The `src/` implementation and test suite are the source of executable truth. Assign ChatGPT implementation and migrations; Claude security/threat-model review; Gemini independent test generation, UX audit and Windows edge cases. Every change requires a diff, migration note, new tests, actual test output and updated documentation. None of the models is allowed to assert compliance or independent security review based on generated code alone. Keep framework license information separate from feature descriptions.
