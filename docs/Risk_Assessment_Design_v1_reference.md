# Cybersecurity Risk Assessment Studio
## Database schema and first ten screens — implementation specification v1.0
Date: 2026-10-28 | Status: Design specification, not implemented

### Design decisions
- Windows 11, single local operator, multiple isolated client organizations.
- Python/PySide6 UI; SQLAlchemy persistence; SQLCipher-encrypted SQLite; Alembic migrations.
- All organization-owned records have `organization_id`; services require an explicit organization context and verify parent/child organization matches. No unrestricted repository methods in the UI.
- UUID primary keys; UTC timestamps (`created_at`, `updated_at`); `version` integer for optimistic updates; no cascade deletion of evidence or audit history.
- Data is local by default. Evidence is encrypted at rest, with an authenticated integrity hash; backups are encrypted separately. Do not place encryption keys in the application binary.
- A framework mapping is an analytical cross-reference, not proof of compliance.
- Risk bands are configurable defaults: 1–4 low, 5–9 moderate, 10–16 high, 17–25 critical. Inherent and residual ratings must include rationale.

## A. Database tables and relationships
**Notation:** PK = primary key; FK = foreign key; UQ = unique constraint. Every tenant-scoped table has `organization_id FK organizations.id`, indexed. All listed tables have `id UUID PK`, timestamps, unless a different key is specified.

| Table | Essential columns beyond common fields | Relationships / constraints |
|---|---|---|
| organizations | name, slug, industry, timezone, status | UQ(slug) |
| organization_profiles | legal_name, address_json, contact_email, scope_notes | organization_id FK; UQ(organization_id) |
| business_units | name, parent_unit_id nullable | organization_id FK; parent must belong to same organization |
| local_users | display_name, username, password_hash, enabled | UQ(username); single-user v1, future expansion |
| roles | name, permissions_json | seed owner role; future RBAC |
| user_role_assignments | user_id, role_id, organization_id nullable | UQ(user_id,role_id,organization_id) |
| audit_events | actor_id, organization_id nullable, entity_type, entity_id, action, occurred_at, details_json, chain_hash | append-only; immutable from UI |
| frameworks | code, name, publisher | UQ(code) |
| framework_versions | framework_id, version, publication_date, source_url, license_notes | UQ(framework_id,version) |
| controls | framework_version_id, control_code, title, description, parent_control_id nullable | UQ(framework_version_id,control_code) |
| control_mappings | source_control_id, target_control_id, relationship, rationale, confidence, provenance | UQ(source_control_id,target_control_id); not compliance |
| question_bank | code, question_text, response_type, guidance, active | UQ(code) |
| question_control_links | question_id, control_id, coverage_type | UQ(question_id,control_id) |
| assessments | organization_id, title, framework_version_id, scope, status, started_at, finalized_at, owner_id | status: draft/in_progress/review/finalized |
| assessment_questions | assessment_id, question_id, display_order, required, snapshot_text | UQ(assessment_id,question_id) |
| assessment_responses | assessment_question_id, organization_id, response_value_json, applicability, rationale, answered_by, answered_at | UQ(assessment_question_id); same-org FK validation |
| assessment_reviews | assessment_id, reviewer_id, decision, comments, reviewed_at | immutable review record |
| assets | organization_id, asset_tag, name, type_id, owner, criticality, data_classification, lifecycle_status | UQ(organization_id,asset_tag) |
| asset_types | name, description | global catalog |
| risks | organization_id, title, description, category, status, owner_id, source_assessment_id nullable | index(organization_id,status) |
| risk_assessments | risk_id, organization_id, assessment_kind, likelihood, impact, score, methodology_version, rationale, assessed_at | score=likelihood*impact; kind inherent/residual |
| risk_treatments | risk_id, organization_id, treatment, decision_owner_id, justification, approved_at, review_due_at | acceptance requires owner/date |
| vulnerabilities | organization_id, external_id nullable, title, severity, cvss nullable, source, discovered_at, status | dedupe per source + identifier |
| asset_vulnerabilities | organization_id, asset_id, vulnerability_id, first_seen_at, last_seen_at | UQ(asset_id,vulnerability_id) |
| vendors | organization_id, name, service, data_access, criticality, review_due_at | UQ(organization_id,name) |
| vendor_assessments | organization_id, vendor_id, status, inherent_score, residual_score, assessed_at, next_review_at | vendor same-org |
| remediation_tasks | organization_id, risk_id nullable, vulnerability_id nullable, title, owner_id, priority, status, due_at, completed_at | at least one source or documented standalone |
| task_history | organization_id, task_id, actor_id, from_status, to_status, note, changed_at | append-only |
| evidence_records | organization_id, title, media_type, encrypted_blob_ref, sha256, collected_at, expires_at, classification | never store plaintext file paths in exports |
| evidence_links | organization_id, evidence_id, target_type, target_id, relevance, verified_at | validate target exists and same-org |
| report_templates | name, template_version, layout_json, enabled | global or organization-scoped |
| generated_reports | organization_id, assessment_id nullable, template_id, generated_at, file_sha256, snapshot_ref, generator_version | snapshot for reproducibility |
| app_settings | setting_key PK TEXT, encrypted_value nullable, value_json nullable | allowlisted keys only |
| backup_history | backup_id, created_at, destination_hint, checksum, restore_tested_at, status | no secrets in logs |

**Implementation note:** This logical schema contains 33 tables; physical design may add lookup and junction tables. SQLite foreign keys must be enabled per connection. Cross-organization references require service validation and, where feasible, composite foreign keys.

### Essential indexes
- `assessments(organization_id,status,updated_at)`
- `risks(organization_id,status,updated_at)`
- `remediation_tasks(organization_id,status,due_at)`
- `assets(organization_id,asset_tag)`
- `evidence_links(organization_id,target_type,target_id)`
- `audit_events(organization_id,occurred_at)`
- `assessment_responses(organization_id,assessment_question_id)`

## B. First ten application screens
| # | Screen | Main components | Primary actions | Acceptance test |
|---|---|---|---|---|
| 1 | First-run setup / unlock | local password, encryption initialization, recovery guidance | create vault; unlock | wrong password denied; secrets never logged |
| 2 | Organization switcher | searchable organization list, create wizard, demo badge | create/select/archive | data from Org A never shown under Org B |
| 3 | Executive dashboard | risk counts, severity chart, open tasks, recent assessments | navigate; filter | totals agree with underlying organization records |
| 4 | Organization profile | contacts, industry, business units, scope | edit/save | invalid email rejected; audit event written |
| 5 | Assessment list | status tabs, framework, dates, owner | new/duplicate/open | drafts persist and remain organization-scoped |
| 6 | Assessment setup | title, framework version, scope, question selection | create assessment | version pinned; required fields validated |
| 7 | Guided questionnaire | progress bar, response, applicability, evidence links | save draft; next/back | resume after restart without loss |
| 8 | Findings and risk register | risk matrix, filters, inherent/residual, owners | create/edit/score | 4×5=20, critical by default; rationale required |
| 9 | Remediation board | status, due dates, owners, priority | assign/update/close | every status transition has history |
| 10 | Reporting center | report type, sections, organization branding, preview | export PDF/XLSX | report reflects frozen snapshot, not later edits |

### Navigation flow
`Unlock → Organization switcher → Dashboard → Assessments → Setup → Questionnaire → Risk register → Remediation → Reporting`

Persistent sidebar: Dashboard, Organizations, Assessments, Risks, Assets, Vulnerabilities, Vendors, Evidence, Remediation, Reports, Settings. Screens 1–10 are the first implementation wave; other modules appear as disabled navigation only in internal builds, not as misleading promised features in commercial releases.

## C. Phase 1 implementation tickets
1. Create repository, `src/` package layout, dependency lockfile, lint/type/test CI.
2. Implement SQLCipher integration; verify actual file encryption and failed-open behavior.
3. Create initial Alembic migration for users, organizations, frameworks, assessments, responses, risks, tasks, evidence metadata, audit events.
4. Implement repository/service boundary with mandatory organization context.
5. Build first-run setup and unlock UI with secure key derivation.
6. Build organization switcher and organization profile screens.
7. Seed an explicitly fictional demo organization and synthetic example data.
8. Build assessment setup, question snapshots, autosave/resume.
9. Implement risk scoring with boundary tests and methodology versioning.
10. Implement PDF report and XLSX risk export, plus backup/restore smoke tests.

### Definition of done for first milestone
- Clean install on a Windows 11 test VM; no Python installation required.
- Encrypted vault cannot be read as ordinary SQLite; incorrect passphrase rejected.
- At least two organizations tested for cross-tenant leakage in every implemented workflow.
- One end-to-end assessment: create → answer → risk → remediation → PDF and XLSX.
- Restart, restore from backup, and regenerate reports successfully.
- Unit tests for scoring and permission boundaries; integration tests for persistence; no critical/high findings from dependency and application security review.
- User guide and privacy statement accurately describe what the software does and does not guarantee.

## D. Cross-model handoff protocol
**Shared source of truth:** this file plus the original blueprint; Git repository is authoritative for code. Each model proposes changes as a small diff with tests; do not merge three independent codebases.
- **ChatGPT:** repository scaffold, SQLAlchemy models, services, UI integration, migration reviews.
- **Claude:** independent security review, threat modeling, code-quality review, documentation.
- **Gemini:** edge-case test generation, UX review, independent validation.
- Require a change request with affected tables, migrations, tests, security considerations, and rollback strategy.
- No model may claim compliance certification or that a security control is implemented without an executable test or documented verification.

## E. Open product decisions
- Select a redistributable SQLCipher Python binding and confirm licensing.
- Define commercial license terms (one purchaser, unlimited organizations, permitted installs).
- Decide whether local password recovery means backup recovery only (recommended) or managed recovery.
- Verify redistribution rights and currency of framework texts before bundling.
- Choose exact signed installer/update distribution process.
