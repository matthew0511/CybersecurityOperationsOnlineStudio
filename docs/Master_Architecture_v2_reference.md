# Cybersecurity Operations Studio
## Master Architecture, Notion Integration Assessment, Technical Documentation and Build Roadmap
**Version:** 2.0 (design baseline)  
**Date:** October 28, 2026  
**Product:** Cybersecurity Operations Studio — incorporating Cybersecurity Risk Assessment Studio  
**Target:** Windows 11 desktop; one fully featured commercial edition; single local operator with multiple organizations; offline-first  
**Status:** Documentation and design only. No desktop software has yet been implemented or validated.

> **Source provenance.** Based on the uploaded Notion export `Cybersecurity Operations Hub` (52 Markdown documents, 16 CSV files) and the prior `Cybersecurity_Risk_Assessment_Studio_Data_Model_and_Screens_v1.md` specification. The export is a snapshot, not live Notion access. The Notion hub's own Release QA and Buyer Acceptance Checklist records a **HOLD** decision, unresolved validation, and untested permission isolation. This document does not reverse that finding or imply that desktop features exist.

---

# 1. Executive product decision

Build **one premium Windows desktop product** with a unified data model, not a collection of disconnected utilities. Its central user journey is: organization → scope → asset/vendor/control inventory → assessment → finding/risk → evidence → remediation/exception → executive report → reassessment. Additional operational workflows (incident response, vulnerability management, business continuity, AI governance, and threat intelligence) connect to this journey.

**Commercial principles:** no feature-gated tiers, no required subscription, no mandatory cloud account, unlimited organization records subject to device capacity, exportable customer data, and transparent limitations. A one-time license does not imply perpetual free major-version upgrades or free support; publish explicit terms. Suggested initial retail price of **$149** is a hypothesis requiring customer research and unit economics validation.

**Non-goals for first release:** continuous endpoint monitoring, SIEM, automated scanning/exploitation, automatic failover, HIPAA certification, legal conclusions, real-time regulatory monitoring, cloud collaboration, or claims that framework mappings prove compliance. These may be future integrations or separate validated capabilities.

# 2. Source review and what changes

The Notion hub's top-level page describes incident response, compliance/evidence, policies, assets, vulnerabilities, risk decisions, vendor oversight, threat intelligence, recovery, AI governance, and vCISO reporting. The technical specification distinguishes **nine identifiable live databases within an eleven-module target lineup** and **two proposed modules** (Regulatory Requirements Watchlist, Security Training Tracker). It also describes eight **target** bidirectional relation pairs, not eight verified working reciprocal pairs. Its QA checklist documents limited smoke tests and outstanding blockers.

| Notion source | Evidence in export | Desktop implementation decision | Priority |
|---|---|---|---|
| Risk Register + Risk Acceptance | Separate registers; manual approval is not equivalent to authorization | Unified risk record plus independently auditable, time-bound acceptance decisions | P0/P1 |
| Compliance Tracker + Security Policies | Controls, policies, evidence freshness; manual and formula fields | Versioned framework catalog; organization control implementations; policy lifecycle; validated evidence | P0/P1 |
| Asset Management | Asset inventory and links to risks | Assets, owners, classifications, criticality, and link tables | P1 |
| Vulnerability Assessments | Assessment/finding records, asset/control relationships | Import-first vulnerability findings and remediation; no built-in scanner initially | P1 |
| Third-Party Risk Management | Vendor register and BAA applicability separate from execution | Vendor profiles, assessments, contracts, data access, BAA applicability/status, reassessment | P1 |
| Incident Response Tracker | Incidents, status, severity, asset links | Incident lifecycle, timelines, affected assets, lessons learned | P2 |
| BC Planning + BC/DR Hub | Governance inventory distinct from recovery runbooks | Two linked record types; RTO/RPO, exercises, plan approvals, runbooks | P2 |
| Threat Intelligence | Context and indicator records; no automatic feed ingestion | Curated indicators with source, confidence, expiration, related assets/incidents | P2 |
| AI Governance | Extensive governance guidance and operating model | AI system inventory, use-case approval, data-use review, model/vendor risk, exceptions | P2 |
| vCISO Executive Reporting | Framework/posture scorecards requiring configuration | Explainable scorecards with denominators, exclusions, source drill-down, snapshots | P1 |
| Regulatory Requirements Watchlist | Explicitly proposed, not installed | Manual obligations/change register; optional feed integration only after verification | P3 |
| Security Training Tracker | Explicitly proposed, not installed | Assignments, attestations, evidence, completion history | P3 |
| Fictional Demo | Vendor → risk → control → evidence worked example | Clearly labeled synthetic seed dataset, never mixed into production reports | P0 |
| Release QA Checklist | Release HOLD; permissions, rollups, boundary tests unresolved | Adopt as test backlog; do not inherit unsupported “passed” claims | P0 |

**Preserve important distinctions:** implementation status ≠ operating effectiveness; evidence age ≠ evidence validity; risk approval ≠ risk acceptance; applicability ≠ compliance; a link ≠ permission; a calculated score ≠ independently verified security posture.

# 3. Proposed architecture

```text
Windows 11 / PySide6 UI
  ├─ Organization switcher and dashboards
  ├─ Assessment / risk / compliance workflows
  ├─ Operations modules and reporting
  └─ Settings / backup / import / diagnostics
                ↓ typed application services
Domain layer: org context, assessment, controls, risks, tasks, evidence,
              policy, vendor, incident, recovery, AI governance
                ↓ repositories + validation + audit events
SQLAlchemy + migrations → SQLCipher SQLite database
Encrypted evidence store → per-file authenticated encryption
Report engine → PDF / XLSX / CSV; snapshot manifest
Import adapters → Notion-export CSV / CSV / XLSX (optional later APIs)
```

**Implementation choices:** Python 3.12+ (pin tested runtime), PySide6, SQLAlchemy 2.x, Alembic, Pydantic for import validation, pytest, Ruff, mypy/pyright, ReportLab, openpyxl, and a tested SQLCipher-capable Python binding. Validate package licenses and installer redistribution rights before selecting the binding. Use a reproducible build and signed Windows installer when available. Never ship hard-coded keys or claim encryption until tested against actual installed binaries.

**Local user model:** v1 is one local operator with multiple organizations. The earlier schema's `local_users`, `roles`, and `user_role_assignments` remain future-ready; they do not create true multi-user collaboration or an authorization boundary by themselves. Do not advertise team access. The organization context is mandatory in every organization-owned service call.

# 4. Canonical data model and key changes from v1

Retain the 33 logical tables defined in the v1 specification as the initial reference, subject to migration review. **Do not implement all tables at once.** Add or refine the following normalized entities before building modules:

| Entity / table | Important fields and rules | Core relationships |
|---|---|---|
| `control_implementations` | organization_id, control_id, applicability, implementation_status, effectiveness_status, owner_id, reviewed_at | organization → framework control; independent of catalog |
| `control_evaluations` | implementation_id, assessor, result, rationale, evaluated_at, assessment_id | many evaluations per implementation |
| `evidence_reviews` | evidence_id, reviewer, validity, scope, review_date, expiry_date, rationale | separate review from file metadata |
| `risk_acceptance_decisions` | risk_id, decision, approver, authority_basis, rationale, effective_at, expires_at, review_due_at | distinct from risk treatment and sign-off field |
| `risk_asset_links` | risk_id, asset_id, relevance | enforce same organization |
| `risk_control_links` | risk_id, control_implementation_id, relationship | enforce same organization |
| `vendor_risk_links` | vendor_id, risk_id, relationship | enforce same organization |
| `policy_versions` | policy_id, version, status, effective_at, approved_by, approved_at, artifact_id | immutable approved version |
| `recovery_plans` | organization_id, business_service_id, rto_hours, rpo_hours, owner, approval_status | service → recovery plan |
| `recovery_exercises` | plan_id, tested_at, achieved_rto, achieved_rpo, outcome, evidence_id | tests, not claims of actual recovery |
| `incidents` | organization_id, severity, status, detected_at, resolved_at, commander_id | assets, indicators, tasks, evidence |
| `ai_use_cases` | organization_id, sponsor, tool/vendor, purpose, data_categories, decision_status, review_due_at | vendor, risk, evidence, approval |
| `regulatory_obligations` | jurisdiction, source, version, effective_date, applicability_decision | mapped to controls with provenance |
| `training_assignments` | organization_id, training_item, assigned_to, due_at, completed_at, verification | owner or participant; P3 |
| `import_jobs` / `import_rows` | source, filename_hash, run_id, mapping_version, status, errors | staging, deduplication, rollback |
| `metric_snapshots` | organization_id, metric_id, numerator, denominator, exclusions, methodology_version, as_of | historical comparison and auditability |

**Constraints:** UUID keys, foreign keys on, indexed `organization_id`, uniqueness within organization, explicit timestamps in UTC, audit trail for sensitive transitions, and same-organization validation for all polymorphic and junction links. Prevent accidental hard deletion of accepted risks, finalized assessments, approved policies, and referenced evidence. Version records rather than silently overwriting them. Use migrations with preflight backup and rollback instructions.

**Canonical relationship examples:**
- Organization 1→many assessments, assets, vendors, risks, incidents, policies, recovery plans.
- Framework 1→many versions 1→many controls; organization control implementation references an exact framework version/control.
- Assessment 1→many question snapshots and responses; one response may yield multiple findings/risks with traceable source references.
- Risk many↔many assets, control implementations, vendors; risk 1→many treatments, decisions, and remediation tasks.
- Evidence many↔many controlled targets through validated typed links; evidence 1→many reviews; only reviewed evidence may count as valid.
- Business service 1→many recovery plans; plan 1→many exercises; recovery plans link to assets and vendors.

# 5. Assessment and risk calculation specification

## 5.1 Workflow and states
`draft → in_progress → ready_for_review → finalized`; finalized assessments are immutable snapshots. Reassessment creates a new assessment linked to the prior one. Required questions cannot be bypassed without a recorded N/A reason. Store question text, guidance, framework version, scoring methodology version, and source provenance at assessment creation.

## 5.2 Default risk method (configurable)
- Likelihood integer **1–5** and impact integer **1–5**. Missing, zero, fractional, negative, or >5 inputs are invalid; never silently score them as zero.
- `score = likelihood × impact`; default bands: 1–4 Low, 5–9 Moderate, 10–16 High, 17–25 Critical. These are product defaults, not NIST-prescribed universal thresholds.
- Inherent and residual scores are **separate dated evaluations**; require rationale and assessor.
- Acceptance requires an authorized approver, documented justification, effective date, expiration/review date, and decision history. Expired acceptance returns to review; it never automatically means remediation is complete.
- Risk score alone does not establish legal compliance, likelihood of real-world loss, or a quantified financial exposure.

## 5.3 Framework and scoring accuracy
Use versioned, sourced mappings with relationship types (`exact`, `partial`, `supporting`, `contextual`) and reviewer provenance. Framework applicability is per organization/assessment. Do not redistribute copyrighted or restricted standard text without checking terms; link to authoritative references and store short licensed/authorized metadata. HIPAA workflows require explicit applicability selection; BAA applicability and signed-BAA status must remain distinct. PCI DSS versions must be explicitly identified and maintained.

**Readiness percentage:** eligible applicable controls with reviewed satisfactory evidence / all eligible applicable controls; show excluded, unknown, N/A, expired, and unreviewed counts separately. Do not treat missing data as a pass. Allow methodology/weighting selection, record it with every snapshot, and disclose that a readiness score is not certification.

# 6. Evidence vault, privacy, and security controls

- **At rest:** SQLCipher for database; authenticated encryption (e.g. AES-GCM via reviewed cryptography library) for file blobs; derive master key from user passphrase with a modern memory-hard KDF (Argon2id) and per-vault salt. Protect in-memory secrets as reasonably possible; never log passphrases or keys.
- **Backup:** independent encrypted archive with manifest, integrity verification, restore dry-run, and explicit version/migration checks. Test failure and recovery scenarios.
- **Evidence record:** source, collection date, classification, SHA-256, related scope, reviewer, reviewed date, validity, expiration, and provenance. A hash verifies file integrity, not the truth of the evidence.
- **Privacy:** local-first; no telemetry or uploads by default; no PHI/PII in synthetic demo. Support redacted reports, evidence omission, and secure deletion policy caveats (SSD/backup realities).
- **Isolation:** never trust UI filters as access control; enforce organization scope at service/repository boundaries; cross-organization relation creation must fail.
- **Audit:** append-only logical events with tamper-evidence where practical, acknowledging a local device administrator can still alter local files. Do not market local logs as tamper-proof.
- **Reporting:** snapshots, generation timestamp, selected framework versions, calculation method, author/reviewer, exclusions, evidence validity, and explicit limitations.

# 7. Module specifications and build acceptance

| Module | Minimum commercial-ready behavior | Acceptance focus |
|---|---|---|
| Organizations | create/archive/switch, profile, scope, contacts, demo isolation | zero cross-org record leakage |
| Assessments | templates, question snapshots, autosave, applicability, review/finalize | resume after restart; immutable finalization |
| Risk | inherent/residual, treatment, acceptance, register, matrix | boundary tests; expired decisions flagged |
| Controls/compliance | framework versions, applicability, status, evaluations, mappings | missing/unreviewed excluded from passing |
| Evidence | encrypted attachments, review, freshness, links, export rules | invalid/expired evidence excluded |
| Remediation | owners, due dates, status history, priority, dependencies | overdue state accurate, audit recorded |
| Assets | owner, type, data class, criticality, import, risk links | dedupe and cross-org validation |
| Vulnerabilities | CSV import, source identifiers, CVSS optional, assets, tasks | idempotent import; no false scan claims |
| Vendors | criticality, data access, BAA status, risk links, reassessment | applicability ≠ executed BAA |
| Executive reporting | summary, trend snapshots, branded PDF/XLSX, drill-down | totals reconcile to raw records |
| Incidents | timeline, severity, affected assets, containment/recovery, postmortem | chronological consistency |
| BC/DR | governance plans, runbooks, exercises, RTO/RPO | targets vs achieved results separate |
| Threat intel | indicators, provenance, confidence, expiry, incident link | stale indicators flagged |
| AI governance | use-case inventory, approval, data-use assessment, exceptions | approval traceability |
| Requirements watchlist | manual change register, applicability, control links | no claim of automatic regulatory updates |
| Training | assignments, evidence, due dates, completion | no assumed completion |

# 8. First 10 screens (revised)

| # | Screen | Required panels/actions | Exit criteria |
|---|---|---|---|
| 1 | First-run vault setup/unlock | passphrase, key derivation, recovery/backup guidance | failed unlock handled securely |
| 2 | Organization manager | create/select/archive, demo marker | strict organization isolation |
| 3 | Executive dashboard | risk distribution, due tasks, readiness caveats, trends | reconcile counts |
| 4 | Organization profile & scope | industry, frameworks, data classification, roles | audit changes |
| 5 | Assessment library | templates, framework versions, status, duplication | stable snapshots |
| 6 | Assessment wizard | scope, question bank, applicability, owners | validation |
| 7 | Guided assessment | save/resume, evidence, N/A rationale, progress | no data loss |
| 8 | Risk & finding register | inherent/residual, links, rationale, matrix | correct boundaries |
| 9 | Remediation & decisions | tasks, history, risk acceptance workflow | approval not inferred |
| 10 | Reporting & exports | PDF/XLSX, exclusions, snapshot, branding | reproducible report |

Later navigation: Controls, Assets, Vulnerabilities, Vendors, Evidence, Incidents, BC/DR, Threat Intelligence, AI Governance, Requirements, Training, Settings. Do not expose unfinished modules as usable in a commercial build.

# 9. Notion export import and migration plan

**Do not import the ZIP directly into production records.** The export mixes Markdown documentation, CSV database exports, duplicated `_all.csv` files, and fictional demo records. Build a previewable staging importer:
1. Inspect archive paths safely (block `../` traversal and zip bombs), record file manifest/checksums.
2. Detect CSV encodings, headers, row counts, and duplicate `_all`/non-`_all` sources; allow explicit selection.
3. Map Notion source IDs and relation text to stable internal UUIDs through a two-pass import; never match on display name alone without collision handling.
4. Validate enums, dates, URLs, owners, numeric score inputs, and relationship targets. Preserve source values as import provenance.
5. Separate documentation from operational records; demo data enters a dedicated fictional organization only.
6. Show dry-run summary: create/update/skip/conflict/error counts and per-field mapping.
7. Require confirmation; execute transactionally per organization; retain job log and rollback backup.
8. Verify counts, relation integrity, risk scoring, evidence references, and organization isolation after import.

**Notion-specific limitations:** Markdown/CSV export may not preserve all view filters, automation definitions, permission models, formula execution, relation IDs, or attachment accessibility. Treat source formulas and documentation as reference material, not proof of live behavior. No bidirectional Notion synchronization is planned for v1; do not promise it.

# 10. Release blockers inherited from source and new verification gates

| ID | Source issue / risk | Desktop mitigation and test | Gate |
|---|---|---|---|
| QA-01 | risk boundary/invalid inputs not fully regression-tested | automated tests for 1–5, blanks, zero, fractions, negatives, >5, 4×5=20 | P0 |
| QA-02 | critical-risk rollup uses questionable select aggregation | compute from normalized linked risks; test add/remove/status changes | P0 |
| QA-03 | sign-off person field may be mistaken for approval | independent acceptance decision workflow and audit evidence | P0 |
| QA-04 | evidence view may show extra columns | explicit export field allowlist and redaction tests | P0 |
| QA-05 | auditor permissions not tested | organization scope + role/export threat model; no team-sharing claim | P0 |
| QA-06 | relations/recalculation not fully exercised | referential integrity and recalculation tests | P0 |
| QA-07 | clean starter parity not verified | independent demo and empty-vault tests | P1 |
| QA-08 | external ingestion not deployed | mark as future; import-only claims for v1 | P1 |
| QA-09 | recovery runbook not exercised | demo runbook and manual exercise records, no automatic recovery | P2 |
| QA-10 | release marked HOLD | desktop release remains HOLD until all required gates pass | P0 |

**Desktop-specific gates:** installer on clean Windows 11 VM, encryption verification using file inspection, wrong-password denial, backup/restore including corrupted archive, no cross-organization leakage, signed binary where feasible, dependency/license review, accessibility/keyboard testing, performance on representative data, CSV injection mitigation in exports, report reconciliation, and customer documentation.

# 11. Phased engineering plan

**Phase 0 — Source audit and design freeze (this document):** canonical schema, module map, product boundaries, threat model, licensing review, acceptance backlog. *Current status: documentation drafted; not approved or implemented.*

**Phase 1 — Functional vertical slice:** repository scaffold, encrypted vault, migrations, organization switcher, demo data, assessment wizard, question responses, risk scoring, remediation, PDF/XLSX, backup/restore. Target is a working end-to-end workflow, not feature completeness.

**Phase 2 — Compliance foundation:** versioned controls, implementation/evaluation records, evidence vault, evidence review, policy versions, control-risk crosswalk, readiness snapshots, imports.

**Phase 3 — Operational integration:** asset inventory, vulnerability imports, vendor oversight, risk acceptance, incident tracker, vCISO reporting and branded templates.

**Phase 4 — Governance and resilience:** BC/DR, threat intelligence, AI governance, regulatory watchlist, training, historical comparison, reminders. Offline reminders run only while the app is open unless an explicit OS scheduler integration is built and tested.

**Phase 5 — Commercial hardening:** QA matrix, performance, security review, signed installer, end-user guide, troubleshooting, license/activation decision, privacy notice, refund/support policy, product screenshots, Gumroad listing and release checklist.

# 12. Implementation backlog (prioritized)

| Ticket | Description | Dependencies | Done when |
|---|---|---|---|
| ARC-001 | repository layout, pinned dependencies, CI, lint/type/test | none | clean CI passes |
| SEC-001 | threat model, passphrase KDF, SQLCipher binding selection | ARC-001 | security review and encrypted file verified |
| DB-001 | orgs/users/audit/framework/assessment/risk/task migration | ARC-001 | migration roundtrip tests pass |
| SEC-002 | organization context enforcement | DB-001 | cross-org integration tests pass |
| UI-001 | setup/unlock and org switcher | SEC-001, SEC-002 | clean VM manual test |
| ASM-001 | framework/question seed + assessment snapshots | DB-001 | version pin and resume tests |
| RSK-001 | risk calculations, history, acceptance boundaries | ASM-001 | full scoring matrix tests |
| TASK-001 | remediation lifecycle and history | RSK-001 | transitions audited |
| RPT-001 | PDF/XLSX and immutable report manifest | ASM-001, RSK-001 | figures reconcile |
| BAK-001 | encrypted backup/restore | SEC-001, DB-001 | corruption and restore tests |
| IMP-001 | Notion CSV staging importer | DB-001 | dry-run and dedupe tests |
| CMP-001 | controls, implementations, evaluations, evidence reviews | DB-001 | readiness denominator verified |
| VEN-001 | vendors, BAA applicability, risk linkage | CMP-001 | linked workflows verified |
| QA-001 | release evidence matrix and regression suite | all shipped tickets | signed release checklist |

# 13. Documentation set and audience

| Document | Audience | Content |
|---|---|---|
| This master architecture | engineering/product | decisions, data model, module map, build gates |
| v1 data model and first 10 screens | engineering | initial logical tables and UI specification; superseded where v2 differs |
| Buyer Getting Started (to author with build) | customer | install, unlock, create organization, sample workflow, backups |
| Administrator and Security Guide (to author) | technical customer | data storage, encryption, access limits, retention, incident response |
| Import/Export Guide (to author) | customer | CSV mapping, warnings, dedupe, evidence handling |
| Framework Mapping Methodology (to author) | auditor/consultant | applicability, crosswalk provenance, scoring limitations |
| Test and Release Evidence (to maintain) | QA | test IDs, expected/actual, version, reviewer, screenshots/logs |
| Commercial License and Privacy Notice (legal review) | buyer | permitted installations, updates, support, data handling |

# 14. Cross-model collaboration protocol

**Single source of truth:** Git repository + this architecture version. Do not let ChatGPT, Claude, and Gemini independently modify the same branch and then manually merge whole projects.
- **ChatGPT:** architecture, migrations, implementation of vertical slice, integration tests.
- **Claude:** independent threat model and security/code review; identify contradictions and unsafe defaults.
- **Gemini:** UX critique, test scenarios, import edge cases, Windows packaging checklist.
- Every contribution must identify changed files, ticket ID, tests executed, observed results, and unresolved issues. A model's assertion that code works is not test evidence.
- Change control: architecture decision record (ADR) for schema/security/product-scope changes; migration and rollback plan for every schema change; update user and technical docs with release changes.

# 15. Decisions requiring validation before code freeze

1. Product name: retain **Cybersecurity Risk Assessment Studio** externally or adopt **Cybersecurity Operations Studio** to reflect broader scope.
2. Offline commercial licensing and number of permitted devices; avoid invasive DRM.
3. SQLCipher binding and its commercial redistribution license; choose after packaging proof-of-concept.
4. Recovery policy: passphrase cannot be reset without a recovery key or recoverable backup; define and test customer-facing procedure.
5. Framework content distribution rights and update maintenance responsibility.
6. Whether the first commercial release contains only Phase 1–3 or all listed modules; **never market unfinished modules as included**.
7. Security and privacy review for regulated data; do not imply HIPAA compliance solely from local encryption.

# 16. Immediate next engineering action

Create `cybersecurity-operations-studio/` with `src/cos/{ui,domain,services,persistence,security,reports,imports}`, `tests/{unit,integration,security}`, `docs/`, `migrations/`, and a lockfile. Implement **SEC-001 + DB-001 + SEC-002** before rich UI. Demonstrate encrypted organization creation and isolation in automated tests, then build Screens 1–3. Do not proceed to sales launch until release gates pass.

---

## Source document register (inside uploaded Notion ZIP)
- `Cybersecurity Operations Hub df00be5631338303ac1781ee4baff573.md` — top-level inventory, source/clean/demo distinction.
- `Cybersecurity Operations Hub — Technical Specifica 399f55f6111c42379ce2cad8de7bcc6b.md` — target 11 modules, eight proposed relation pairs, formula catalog, harmonization, integration design.
- `Start Here — Buyer Setup Guide 0dd0be56313383f1b66d01e2edc7b397.md` — operational workflow and manual/calculated behavior.
- `Release QA and Buyer Acceptance Checklist 0640be56313383e5b73101c98ef4f743.md` — observed tests, unresolved blockers, HOLD release decision.
- `AI Governance 2710be56313383029852016a4e6cb6e7.md` — detailed governance model.
- `VCISO Executive Reporting 4050be56313380239292ce64656c977f.md` — executive reporting approach.
- `Fictional Demo — Vendor to Evidence 1750be563133822ea93e811fa54b604d.md` — synthetic workflow.
- `Comparison Standard Page 4880be56313383f2b9af815c3fb6eeab.md` — standards overview.

**Document control:** v2.0 replaces earlier high-level product scope; v1 database specification remains a draft appendix. Reconcile the exact table count after schema migrations are implemented; the v2 additions are not claimed to exist in software.
