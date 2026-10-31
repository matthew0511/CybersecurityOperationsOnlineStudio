# Phase 1 Implementation Specification / Change Log

**Version:** 0.1.0-preview · **Date:** 2026-10-28 · **Status:** Code implemented; backend tests passed; Windows interface, packaged executable and release approval not validated.

## 1. Deliverable and version relationship

This document supplements `Master_Architecture_v2_reference.md` and `Risk_Assessment_Design_v1_reference.md`. Unlike those forward-looking specs, it records exactly what the source ZIP contains. The commercial aspiration remains one premium offline-first Windows product with a central risk assessment workflow, augmented by operations modules. The Phase 1 prototype does NOT implement the 33-table logical model; it implements a narrow foundational subset to prove UI-to-service-to-encrypted-storage-to-reporting.

## 2. Security design decision: encrypted in-memory vault (prototype)

The approved roadmap specified SQLCipher. SQLCipher-compatible bindings and redistribution rights are not yet validated in this environment. Instead of shipping unencrypted customer files under an encryption claim, Phase 1 implements **encrypted serialized SQLite**. SQLite is opened in RAM, an Argon2id-derived 256-bit key encrypts serialized database bytes with AES-256-GCM, and each committed transaction creates a new nonce and atomically replaces the encrypted vault. Integrity is authenticated before deserialization. Incorrect passwords and ciphertext tampering reject unlock. Backups copy the encrypted committed vault, requiring the same passphrase.

This is a **design deviation**, not a hidden implementation of SQLCipher. It requires OS-level privacy, crash resilience, scale testing, dependency review, passphrase security review, full restore rehearsals, and a future migration strategy. AES-GCM nonces are random 96-bit for each full-database rewrite; with very high write frequency a key-rotation plan is needed. Keep data sets small while prototyping.

**Known limitations:** unlocked data lives in process memory; OS pagefile / memory snapshots may contain it; full-database encryption per write is inefficient; reports are unencrypted; audit triggers only deter ordinary application edits; a person with application access and the passphrase can rebuild data; no enterprise identity provider or RBAC exists; no emergency password recovery exists. Vault backups are not automatically scheduled.

## 3. Current physical schema (8 tables)

| Table | Cardinality and relationship | Implemented features |
|---|---|---|
| `organizations` | root, organization ID PK | Name, industry, active status; unique organization name |
| `assessments` | many per organization | Title, scope, fixed sample framework label, draft/in_progress status |
| `assessment_questions` | many per assessment; composite FK organization | Eight snapshotted original questions, answer, rationale |
| `risks` | many per organization, optional assessment; composite FK | 1–5 likelihood and impact, derived score, rationale, status |
| `risk_score_history` | many per risk; composite FK; immutable by trigger | Initial immutable scoring entry / methodology version |
| `remediation_tasks` | many per risk; composite FK | Title, owner, priority, due date, status |
| `task_history` | many per task; immutable by trigger | Status transition history |
| `audit_events` | organization-scoped; immutable by trigger | Creation and question/status change events |

There are **8 implemented physical tables**, compared with the 33 conceptual tables in the reference blueprint. Their existence does not imply other modules are implemented.

### Database foreign keys and validation

Foreign keys are enabled on each SQLite in-memory connection. Assessment questions, risk links to assessments, and remediation links to risks use composite `(id, organization_id)` references where applicable. Every public organization-specific service call validates organization ownership before fetching or writing. The tests check isolation against cross-org reads, joins, and writes.

**Index definitions:** assessments(organization_id, updated_at), questions(organization_id, assessment_id), risks(organization_id,status), remediation_tasks(organization_id,status), audit_events(organization_id,recorded_at). Physical migrations and rollback are not implemented; schema initialization is idempotent but does not establish robust versioned migration support.

## 4. Working UI tabs and workflow

1. **First-run passphrase / unlock dialog** — create encrypted vault or unlock existing; retry limit in UI (not rate-limiting against offline brute force).
2. **Organization selector** — create and switch organizations, basic industry metadata.
3. **Dashboard** — assessment count, non-closed risk count, open task count.
4. **Assessments** — create with name/scope, list and open.
5. **Questionnaire** — eight original manually answered questions across Govern/Identify/Protect/Detect/Respond/Recover; save and reopen.
6. **Risks** — 5×5 inherent risk matrix with scoring rationale; no residual risk acceptance approval yet.
7. **Remediation** — create tasks linked to risks, update status.
8. **Reports** — export PDF/XLSX organization snapshots.
9. **Settings** — encrypted vault backup.

Tabs 2–9 appear in the main window; first-run passphrase is a modal before the window. The UI includes **seven main tabs**: Dashboard, Assessments, Questionnaire, Risks, Remediation, Reports, Settings. Organization selection occurs in the header. The original 'first ten screens' was a target specification, **not a claim that ten complete screens exist**.

## 5. Risk scoring demonstration methodology

Likelihood and impact are integers in [1,5], with score = likelihood × impact. Bands: 1–4 Low, 5–9 Moderate, 10–16 High, 17–25 Critical. This is a designed example, not a standard NIST-mandated risk rating. Both the scored values and rationale must be captured on risk creation. There is no organizational scoring profile, inherent/residual comparison, or impact-dimension normalization yet.

## 6. Reporting and data export limitations

PDF risk snapshot provides organization, generated time, record totals, risk table, and disclaimers. XLSX offers Overview, Risks, Remediation, and Assessments sheets. User text is spreadsheet-escaped to mitigate formula injection. PDFs and spreadsheets are **not encrypted**. There is no template builder, branding, signature, watermark, evidence attachments, framework readiness, report snapshot manifest, or report provenance signatures yet. Test reports use synthetic records.

## 7. Phase 1 acceptance matrix

| Check | Current result | Evidence |
|---|---|---|
| Create/unlock encrypted vault | PASS automated | `test_vault_encryption_and_reopen` |
| Wrong passphrase / tamper rejection | PASS automated | `test_tamper_detection` plus unlock test |
| Prevent concurrent open and overwrites | PASS automated | vault and collision tests |
| Organization isolation read/write | PASS automated | `test_organization_isolation_and_relationships` |
| Save/reopen questionnaire responses | PASS automated | `test_answers_persist_and_reports` |
| Risk band boundary / invalid inputs | PASS automated | parameterized scoring tests |
| Remediation history and audit event immutability | PASS automated | isolation workflow test |
| Generate PDF and Excel | PASS automated | export test; tests confirm formats |
| Encrypted backup and restore open | PASS automated | export/backup/reopen test |
| Windows 11 native GUI workflow | NOT TESTED | PySide6 not installed in development test container |
| PyInstaller Windows build | NOT TESTED | Must run on Windows |
| Penetration/security review | NOT TESTED | Required before commercialization |
| Notion CSV import and relationship reconciliation | NOT IMPLEMENTED | Next milestones |
| SQLCipher production datastore migration | NOT IMPLEMENTED | Pending engineering decision |
| Full physical 33-table schema and modules | NOT IMPLEMENTED | Roadmap only |

## 8. Priority tickets for next development increment

1. **P0** Windows 11 desktop manual QA and automated Qt interaction tests; fix UX and errors.
2. **P0** Select final encryption architecture (SQLCipher binding/license/Windows build vs reviewed encrypted in-memory vault) and validate file durability at scale.
3. **P0** Create Alembic-grade versioned migration approach and restore preflight validation.
4. **P0** Design password reset expectations, backup rotation and restoration instructions; conduct privacy/security threat model.
5. **P1** Canonical frameworks catalog with version/licensing metadata; do not mislabel original questions as official NIST/HIPAA requirements.
6. **P1** Add organization profile, business units, and explicit assessment scope/boundary selection.
7. **P1** Implement risk decision workflow including treatment, **separate** approval/acceptance, expiration and reassessment.
8. **P1** Add control implementation status vs effectiveness evaluation; evidence validation/freshness and relations.
9. **P1** Implement staged Notion CSV import with field mapping, provenance, validation, deduplication, partial failure recovery, and relation repair.
10. **P1** Expand automated security tests, GUI tests, load tests, and malicious spreadsheet payload tests.
11. **P1** Produce signed Windows installer, release notes and support/license terms after release gates pass.
12. **P2** Build asset, vulnerability, vendor, incident, recovery and AI governance modules using shared normalized entities.

## 9. Cross-model task handoff

ChatGPT owns baseline code and integration tests; Claude independently reviews threat model, data validation and storage risks; Gemini proposes edge-case tests and UI acceptance scenarios. Use Git pull requests, reproducible builds, and evidence-backed acceptance; do not equate AI review with security certification. Never send real customer data or confidential Notion exports to unapproved models or services.

## 10. Release decision

**HOLD for commercial distribution.** This is a real source-code implementation, but GUI execution on Windows, code signing, install/uninstall, backup disaster recovery, security audit, privacy/legal review and production data model maturity are unverified. Do not advertise it as HIPAA compliant or ready for handling patient records.
