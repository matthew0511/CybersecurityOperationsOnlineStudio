# Cybersecurity Operations Studio — Phase 2 Implementation Specification

**Version:** 0.2.0 preview | **As of:** October 28, 2026  
**Status:** Python source implemented; backend automated tests passing; Windows GUI end-to-end tests pending.  
**Sources:** Phase 1 source, Notion Cybersecurity Operations Hub export (68 files, 52 Markdown + 16 CSV), and official NIST/CIS catalog metadata.

## 1. Scope and important limitations

Phase 2 extends Phase 1 rather than replacing it. The project remains a **single local operator / multi-organization / offline-first prototype**. It is **not** an official NIST or CIS assessment tool, attestation platform, HIPAA certification, independent auditor, real-time monitor, enterprise IAM product, or commercially audited security application. Never handle production PHI, sensitive credentials, or unrestricted customer evidence before an independent security review, data lifecycle controls and Windows acceptance testing.

New executable capabilities:

| Function | Implemented in source | GUI workflow | Verification |
|---|---|---|---|
| NIST CSF 2.0 | 22 category identifiers and names grouped into six Functions | Frameworks tab | Unit test for catalog count and unknown key |
| CIS Controls v8.1 | 18 top-level Control IDs and names | Frameworks tab | Unit test for catalog count |
| Custom templates | Organization-scoped template/question creation; version bump; assessment snapshots and mappings | Templates / Assessments tabs | Version and cross-org tests |
| Initial topic crosswalk | Original 8-question starter with 16 **suggested, non-authoritative** mappings (one NIST, one CIS per question) | Starter button; mapping view in questionnaire | Snapshot/mapping test |
| Residual risk | Independent 5×5 likelihood × impact score, rationale, current and append-only history | Risk Register → Set residual rating | Score and isolation tests |
| Risk acceptance | Explicit recorded decision with approver name, rationale and expiry for approval; reassessment invalidates prior active acceptance | Risk Register → Record acceptance decision | Attestation, rejection, expiration, invalidation and immutable history tests |
| Evidence | File bytes and metadata inside encrypted vault; SHA-256, review metadata and relations to assessments or risks | Evidence tab: add, link, review, save plaintext copy | Isolation, integrity and size-limit tests |
| Notion CSV import | Preview, source hash, duplicate control, client matching, source score differences, all-or-nothing confirmed write | Notion Import tab | Malformed/duplicate, transactional and sample Notion export tests |
| Updated risk list | Displays inherent score, residual score, acceptance state independently | Risks tab | Service regression tests |

**Not implemented:** NIST subcategories or CIS Safeguards libraries; certified scoring or compliance determination; live Notion API integration; arbitrary Notion database import; AI recommendations; role-based access control; cryptographically verified approver identities; evidence retention/expiry, secure shredding, export encryption or external object storage; automatic framework-to-framework equivalence; PDF/XLSX report extensions for Phase 2 evidence, approvals and framework coverage; searchable full text; signed Windows installer.

## 2. Architecture

```text
Qt / PySide6 single-user interface
  ├── Organizations → Assessments → Original sample bank or Custom Template snapshot
  ├── Framework reference browser (metadata; no official Safeguard body)
  ├── Risks → Inherent rating → Residual rating → Decision / expiry
  ├── Evidence → Authenticated vault bytes → Review → Link to Risk or Assessment
  ├── Notion CSV import → Preview → Validate → Confirm → Atomic import job
  └── Phase 1 reports, dashboard, tasks and backup
                      ↓
               Phase2Service
                      ↓
      Phase 1 SQLite schema + additive Phase 2 tables
                      ↓
   Serialized in-memory SQLite → Argon2id + AES-256-GCM encrypted .csvault
```

The entire vault serializes and encrypts on every transaction. This is a prototype persistence strategy and may be slow for large evidence workloads. The default vault remains in the OS user-data directory, protected by the same Phase 1 passphrase. **Phase 2 does not claim SQLCipher compatibility.**

### 2.1 Additive schema

Phase 2 creates 14 additional tables:

| Table | Purpose / key relations |
|---|---|
| `framework_catalogs` | Framework key, version, title, official URL |
| `framework_controls` | PK (framework_key, code); short identifier, title, domain |
| `question_templates` | UUID PK, organization FK; name unique per organization; monotonic version |
| `template_questions` | Template + organization, unique code, question text and order |
| `template_control_links` | Template question → framework identifier, topic-only rationale |
| `assessment_template_sources` | Assessment → template and immutable version at creation |
| `assessment_control_links` | Assessment snapshot mappings, unaffected by template updates |
| `residual_risk_current` | One current residual score per risk and organization |
| `residual_risk_history` | Append-only residual assessment history |
| `risk_acceptance_decisions` | Append-only approval/rejection/revocation records, expiry |
| `evidence_records` | Organization-owned encrypted-vault evidence bytes and SHA-256 |
| `evidence_links` | Org-scoped evidence link to risk/assessment; target verified in service |
| `notion_import_jobs` + `notion_import_rows` | Source hash, import result, original row→target mapping, immutable job records |

The 14 new tables include both import audit tables. Creation is designed to be idempotent across vault reopenings. Existing Phase 1 assessments and records remain accessible. Formal ordered migrations and rollback procedures are required before commercial distribution.

### 2.2 Relationship rules

- **Organization boundary:** every client-specific query requires an organization ID. Every template, risk, evidence and assessment reference is validated against the current organization in the service layer.
- **Framework mapping:** `template_questions` → `template_control_links` → `framework_controls`. When creating an assessment: template questions and links are copied to Phase 1 `assessment_questions` and `assessment_control_links`; a later template edit increments the version and **does not mutate existing assessments**.
- **Risk ratings:** Phase 1 `risks.score` is always the inherent rating. Phase 2 `residual_risk_current.score` is the current residual rating; historical records remain append-only. Both use the documented non-regulatory default matrix: 1–4 Low, 5–9 Moderate, 10–16 High, 17–25 Critical.
- **Approvals:** free-text named authority + explicit user attestation is a documented operator assertion, **not identity proof or independent authorization**. Future releases require real signing, segregation of duties and expiration review.
- **Evidence:** evidence files are encrypted as part of the vault, but selecting **Save selected file** exports an unencrypted copy after an explicit warning; exports must be handled under the customer's security policy. A verified label is manually entered review metadata, not external cryptographic provenance.
- **Imported risks:** imported source approval fields do *not* result in acceptance records. User must separately assess residual risk and record a documented decision.

## 3. Notion Risk Register import contract

### Supported CSV source

Single CSV exported from your Notion Risk Register; the original export uses `Risk Name, Probability, Impact`, optionally `Description, Risk Score, Client, Treatment Status, Sign Off Authorization` and other unrelated columns.

| Notion column | Destination | Transformation |
|---|---|---|
| Risk Name | risks.title | Required nonblank, <= 250 chars, no duplicate title in org |
| Description | risks.description | Original text, max 10,000 chars |
| Probability | risks.likelihood | Integer, 1–5 |
| Impact | risks.impact | Integer, 1–5 |
| Risk Score | Validation only | Compare with recomputed value; mismatch **reported**, not imported |
| Client | Organization check | Blank allowed, otherwise must match selected organization name case-insensitively |
| Treatment Status | Preview only | **Not** copied to `risks.status` |
| Sign Off Authorization | Not imported | **Never** inferred to be an approved decision |
| Associated Assets / Policies | Not imported | Preserve relationship work for later explicit second-pass import |

Preview accepts UTF-8 CSV only; <=4 MiB, <=5,000 rows, <=80 columns, no duplicate column names or malformed rows. Rows are checked for valid names and score bounds, repeated risk names, conflicts with the existing organization, and nonmatching Client values. Import is refused if **any** rows are invalid; confirmed successful imports write in one transaction. Import job hashes prevent an identical file from being imported again for the same organization. Source text is not interpreted as code, and external URL fields are not fetched.

**Validation against the attached Notion export:** the main Risk Register file contained 14 rows; preview identified 14 ready, 0 skipped and 0 score discrepancies. An isolated test import persisted 14 risks. The ZIP distributed with the app does **not** contain the original Notion export or that validation vault.

**Unsupported currently:** preserving Notion relation IDs, copying control/evidence links, importing policies/incidents/vendor assessments, automated differential synchronization, or source rollback/reconciliation across renamed records. Back up before importing, especially if working with valuable customer data.

## 4. Risk treatment workflow

1. Record **inherent** risk in Risk Register with a reasoned 1–5 likelihood and impact.
2. Document remediation controls or treatment rationale in notes/tasks.
3. Choose **Set residual rating**, set independent 1–5 likelihood and impact, add controls-based rationale.
4. If the accountable authority actually agrees to accept the risk, select **Record acceptance decision**. Choose `approved`, supply authority name, rationale, a **future expiration date**, and affirm the explicit on-screen attestation.
5. `risks.status` becomes `accepted` and `acceptance_state` becomes `active` (until expiry). Rejection or revocation returns status to `open`.
6. Reassessment of residual score returns an accepted risk to `open` and `acceptance_state` becomes `invalidated`. The old decision remains in append-only history; a new approval is required.
7. An expired approval reports `expired` via `acceptance_state` even if `risks.status` still reflects historical accepted status. This must be resolved with an active automated expiry-enforcement job in a future phase.

## 5. Evidence security and workflow

- Max 5 MiB per evidence item in v0.2 (larger evidence workloads require a redesigned encrypted evidence store).
- The bytes are kept in the encrypted SQLite vault; SHA-256 is computed on ingest and verified on retrieval. A vault operator with application-code control may alter data: hashes are not an independent signature.
- Review states: `pending`, `verified`, `rejected`. Reviewer name/note required and audit logged; underlying evidence bytes remain unchanged when review changes.
- Evidence may be linked to an existing risk or assessment in the same organization. Attempts to link across organizations fail at service validation.
- Plaintext evidence exports, PDF/XLSX reports, and incidental OS crash/swap files require independent customer security controls.

## 6. Design changes vs original Phase 1

- `app.py` now loads `Phase2Service` (inherits Phase 1 `StudioService`). All existing Phase 1 methods remain compatible.
- A new `src/cyberstudio/phase2.py` holds additive schema, catalog metadata, extended services and the CSV validation/importer.
- UI adds tabs **Frameworks**, **Templates**, **Evidence**, **Notion Import** and additions to Assessments, Questionnaire and Risks.
- Risk list contains distinct residual/acceptance columns; all other Phase 1 tabs remain.
- `pyproject.toml` version changes to `0.2.0`.
- No dependency on Notion cloud API or OpenAI/Claude/Gemini for runtime operation.

## 7. Validation evidence and outstanding work

- Phase 1 + Phase 2 automated tests passed: **28 tests** in local non-Windows Python environment.
- Phase 2 tests include template immutability, multiple-org isolation, framework metadata, residual scoring/acceptance, evidence integrity/reviews, mixed-validity import atomicity, and Phase 1 vault upgrade/persistence.
- Static compile passes for Python source and Windows packaging scripts.
- Notion Risk Register CSV was run in a throwaway local vault (14/14 rows; no scoring discrepancies); not shipped.
- **PySide6 is not installed in this headless execution environment**: Windows UI clicks, file dialogs, file associations and font rendering are not yet verified.
- **Windows executable was not built or signed.** Independent security assessment, installer tests and software license review are outstanding.

### 7.1 Release and QA gates

1. Backup and restore vault before using Phase 2 with real data; verify Phase 1 → Phase 2 in a Windows 11 VM.
2. Run `py -3.12 -m pytest -q` including all Phase 1 and Phase 2 tests.
3. Run GUI smoke tests: org switch, template creation, mapped assessment, residual and acceptance, evidence export, import preview/cancel/confirm.
4. Test Windows code signing, Windows Defender / SmartScreen, installers, file permissions, crash recovery, large vaults and read-only disks.
5. Security review: encryption implementation, approval spoofing, audit mutability, memory handling, evidence exfiltration, oversized CSV, and dependent package CVEs.
6. Conduct privacy review: production PHI and other sensitive data explicitly unsupported until customer controls and validation.
7. Confirm third-party licenses and framework redistribution rights; avoid bundling full copyrighted standard text without permission.

## 8. Phase 3 recommended backlog

1. Formal schema migration/version engine and migration rollback procedure.
2. Official, versioned catalog importers (from authorized machine-readable sources) including provenance and change detection.
3. Per-organization custom assessment editors including required/optional questions, scoring, templates and read-only finalized snapshots.
4. Complete control testing/evidence sufficiency workflow, review expiration, structured evidence requests and secure external evidence store.
5. Role-based multi-user mode with authenticated approvals/segregation of duties, or retain single-user mode and accurately limit authority claims.
6. Bidirectional risk/control/vendor/asset relationships and validated control coverage reporting.
7. CSV import adapters for Compliance Tracker, Vendor Assessments, Assets and Incidents, with second-pass relation resolution.
8. Phase 2-aware PDF/Excel reports, report snapshots, signatures and branding.
9. Scalability tests with many organizations and >100 MB evidence (full-vault writes may become costly).
10. Windows installer and update signing, recovery tests, end-user onboarding, sales license and support policy.

## 9. Framework metadata provenance

- NIST CSF 2.0: <https://www.nist.gov/cyberframework> and NIST CSWP 29 (Feb 26, 2024), <https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=957258>.
- CIS Controls v8.1: <https://www.cisecurity.org/controls/v8-1> and <https://www.cisecurity.org/controls/cis-controls-list>.

The included metadata are labels and category/control identifiers, not an authoritative reproduction of standards, safeguard or subcategory text. The starter question bank and mapping rationales are original examples; do not treat mappings as normative crosswalks.
