# Assurance and productivity: technical implementation and operating guide

Program Owner - Matthew Harris  
Date: November 1, 2026, America/Chicago  
Status: validated application release; detailed source, build and deployment observations appear in ASSURANCE_VALIDATION.md.

## Scope and navigation

The latest request asks for fifteen additions. The preceding recommendation contained twelve; this implementation includes those twelve and three supporting extensions: saved views/search, validated bulk program actions, and configurable metrics. Existing operations capabilities remain in place. Open **Operations workbench → Assurance & productivity** and choose a secondary page. **Open My Work Today** is available from the workbench overview.

| # | Capability | Operating surface / implementation |
|---|---|---|
| 1 | My Work Today | Assigned program and legacy task/vendor/assessment/finding/change work, pending independent approvals, failed/unknown checks and evidence follow-ups; direct source links |
| 2 | Data quality | Missing or unavailable owners, possible duplicate titles, required fields and unavailable typed references |
| 3 | Control coverage and confidence | Inventoried-control denominator, current recorded validation and verified/failed/unknown outcomes |
| 4 | Notification delivery assurance | Actual job states, provider-acceptance distinction, owner acknowledgment, explicit failed-send retry and internal backup escalation |
| 5 | Framework version management | Compare editions, preview added/removed/changed controls, version-bound migration of unchanged mappings and retained history |
| 6 | Scoped evidence reuse | Explicit control/system/period/scope linkage and current artifact validation |
| 7 | Detection engineering | Rule identifier, techniques, required log sources, reference query, test procedure, result, tuning and false positives |
| 8 | Security service coverage | Six service expectations per inventoried asset, dated observations, evidence and freshness |
| 9 | Export and recovery package | Program records, evidence bytes and catalogs; integrity validation, conflict preview and safe archived-record recovery |
| 10 | Role onboarding and demo reset | Four role checklists, progress register, isolated demo creation and previewed synthetic-program archival |
| 11 | Board decision follow-through | Request, decision, executive accountability, funding, dates and outcome evidence |
| 12 | Release readiness | Source/deployed commit fields, evidence-backed validation, migration, defects, rollback and acceptance gates |
| 13 | Saved views and search | Scoped title/status/owner filters, fixed sorting and 100-row pages; persistent organization views |
| 14 | Validated bulk actions | Atomic owner/due-date updates with version-bound preview; draft/in-progress only |
| 15 | Configurable metrics | Count, overdue count or completed percentage; numerator, denominator, target and interpretation |

## Getting started

1. Inventory offices and assets. Assign enabled organization members as owners. Unknown coverage remains visible until actual observations are recorded.
2. Link internal controls to imported authorized framework editions. Add reviewed evidence, test plans and validation checks.
3. Review My Work Today and Data quality before issuing a report. Resolve duplicate titles through manual reconciliation; the dashboard never merges records automatically.
4. Record service observations with explicit observation dates and freshness intervals. A passing observation requires currently verified evidence. Explain exclusions.
5. Use Evidence reuse to document the system, control, artifact, assessment period and review deadline. A reused artifact supports only the stated scope.
6. Add detection tests, board follow-through and release records. These are management records; detection queries are never executed and a release record does not deploy code.
7. Configure metrics and saved views for recurring work. Use bulk preview for owner/due changes, then apply the exact reviewed preview.
8. Administrators configure delivery providers in App integrations. Review an approved destination before an explicit test. Use delivery follow-up for acknowledgments and backup escalation.
9. Export a workbench package before archival work. Protect downloaded packages as plaintext confidential files. Use managed database backups for full disaster recovery.
10. Train in a marked synthetic DEMO organization. Demo reset archives only its program records and preserves immutable history and legacy demonstration data.

## Data model and ownership

Nine additive typed kinds are registered in `assurance_catalog.py`: `as_detection`, `as_coverage`, `as_reuse`, `as_decision`, `as_release`, `as_view`, `as_metric`, `as_onboarding`, `as_delivery`. Every record uses `pl_records` organization, identifier, title, owner, due date, status, version, actors and timestamps. New assurance records default owner to their authenticated creator. `catalog.modules()` exposes fields to the existing validated form renderer. Current schema requires no migration.

`store.validate` dispatches `as_` kinds through `assurance.validate`. Existing typed-field validation, same-organization reference checks, fixed choices, bounded text and numeric checks remain in force. User-supplied `calculated` and approval metadata are stripped by existing validation. Clinical records, provider credentials and identity data are not new import fields.

Data quality checks all live program records, including existing kinds. An owner may be a business label in legacy workflows; `owner_not_enabled_member` identifies that accountability gap without rewriting it. Duplicate titles are possible matches, not proof of duplicate identities. Archived references are flagged unavailable. It performs no destructive deduplication.

## Calculation contracts

**Control confidence:** one row per inventoried internal control. No checks or unknown/stale checks yields Unknown; failed checks take precedence; all passing current checks yields Verified. Denominator includes Unknown and Failed. Empty percentage is null. These are bounded recorded-source observations, not automatic discovery of every endpoint or security configuration.

**Service coverage:** six expected services for each inventoried asset: endpoint, encryption, patching, identity, logging, backup. Newest observation per asset/service by update order is used. Freshness expires after `valid_days` (1–3650). Verified evidence is rechecked at read time for passes. Missing observations are Unknown. Exclusions require a rationale, are counted separately and are removed from the percentage denominator. The application does not infer unrecorded assets or whether every protection is technically applicable.

**Evidence reuse:** Eligible requires current dates within the assessment period, an unexpired re-review deadline, a currently verified artifact and available scoped system/control. This register records reusable scope; it does not automatically overwrite control evidence or assert a licensed framework requirement is satisfied.

**Release readiness:** requires passing evidence-backed validation, migration pass/not-required, zero blocking defects, rollback, acceptance, observation date and current evidence. `matches_deployed` separately compares explicitly recorded full Git SHAs. Source/deployed fields are operator supplied; no automatic deployment attestation is implied.

**Metrics:** count is the number of live records in the chosen kind. Overdue excludes completed/closed/rejected and requires a due date before the current server date. Completion percentage counts status `completed` over all live records in that kind. Empty denominator returns null. Targets are compared as at-least or at-most. No arbitrary formulas, SQL or executable expressions are accepted.

## API contract

All routes require current session and authorized organization membership. Cookie writes require CSRF. The GET overview is `/api/platform/{org}/assurance/overview`. POST actions use `/api/platform/{org}/assurance/{action}`.

| Action | Inputs | Enforcement / result |
|---|---|---|
| search | module or view_id; query; status_filter; owner_filter; sort_by; direction; offset | Fixed identifiers, bound values; 100 results plus has_more |
| bulk | 1–100 unique IDs; changes owner/due_on; optional confirmed and confirmation_hash | Same-org locks, editable statuses, valid owner/date, exact version digest, atomic updates |
| catalog-preview | before, after | Scoped catalogs, code/title/parent differences and impacted internal controls |
| catalog-migrate | before, after, confirmed, confirmation_hash | Locks mappings, rechecks digest; removed/changed requirements block automatic migration |
| export | empty | Owner and reports:export; portable package with hash and evidence bytes |
| recovery-preview | package | Owner; validates format, organization, package hash and evidence integrity; reports conflicts |
| recover | package, confirmed, confirmation_hash | Owner and records:delete; archived records reopen as drafts; active records skipped |
| acknowledge | job_id, note | Owner; immutable acknowledgment event; no claim of recipient receipt |
| retry | job_id, confirmed | Owner; failed notification only; explicitly acknowledges ambiguous provider acceptance |
| demo-reset | confirmed; confirmation_hash on apply | Owner; marked demo only; preview-bound program archival |

Bulk operations never approve or complete records. Framework migrations update internal control mappings and retain prior versions in history. Removed or changed requirements require explicit manual reconciliation. Search interpolates only allowlisted identifier/order constants; all user filter values are SQL parameters.

## Delivery and escalation

Delivery assurance observes `pl_jobs` notification/report jobs. Queued/retry/dead-letter states remain distinct. A succeeded job is labeled **provider_accepted**, never delivered. No receipt webhook is installed. Use the existing integration UI for provider tests; no real test message is sent merely by deploying this feature.

Owners acknowledge job follow-up through immutable `assurance:acknowledged` history. An active `as_delivery` record with an overdue acknowledgment deadline and enabled backup member creates one in-app escalation per record version and UTC day. Acknowledged jobs stop escalation. The worker uses `pl_schedule_runs` atomic claims. A failed transaction rolls back both claim and notification.

External retries are explicit because a failed response can occur after provider acceptance. Retry requires owner confirmation, an existing dead-letter notification job and a non-demo organization. Existing connection/schedule validation remains the execution gate. This feature does not silently enable providers or distribute customer data.

## Export, conflict preview and recovery boundaries

The package is JSON `{payload, sha256}`. Canonical sorted JSON supplies the SHA-256. Evidence files are base64 with individual SHA-256 values. The package contains current program records, current evidence bytes and framework catalog metadata/rows. Limits: 2,000 program records, 2,000 evidence entries for preview, total 10 MiB decoded evidence. The browser limits selected packages to 20 MiB. Hashes detect accidental changes; they do not authenticate origin or replace digital signatures.

This is a **workbench portability and archival-recovery package**, not a complete database backup. It excludes legacy risk/vendor/task/assessment registers, identities, memberships, provider secrets, delivery settings, frozen editions and historical audit events. Use the existing isolated RDS restore process for complete recovery. Exported evidence and catalogs remain available for investigation, but missing database evidence/catalog rows are not automatically recreated.

Recovery is restricted to the package's original organization. Preview reports `conflict_existing`, `recoverable_archived`, or `missing_requires_database_restore`. Apply locks candidates and checks the exact conflict digest. Existing records are skipped. Archived program records retain current stored contents and relationships, reopen as draft, lose approval metadata and gain a version plus immutable recovery provenance. The package never executes queries, restores identities, overwrites current active records or replays trusted approvals. A later independent review is required before reactivation of approval-governed records.

## Demo reset and role onboarding

Getting started provides administrator, analyst, executive and auditor checklists. Progress is stored in `as_onboarding`; completing an item is an operator attestation. External auditors still use scoped audit-room invitations rather than internal organization membership.

A reset is permitted only with a `pl_demo` marker. Preview binds the current program record set. Apply archives current program records into the recycle bin and preserves history, legacy synthetic registers and the organization marker. It does not delete an organization, credentials or business data in another workspace. Separate demo creation uses the existing synthetic-only seed workflow.

## Code and verification map

- `platform/assurance_catalog.py`: typed definitions and fifteen-feature register.
- `platform/assurance.py`: calculations, search, migration, bulk, package, delivery and reset.
- `platform/router.py`: session/CSRF/capability/owner API gates.
- `platform/store.py`: typed validation dispatch and default ownership.
- `platform/jobs.py`: internal escalation worker integration.
- `static/assurance.js`: secondary-page interface and preview/apply dialogs.
- `tests/test_assurance.py`: tenant, role, version, integrity, migration, state and calculation acceptance.
- `tests/experience-ui.cjs`: real static interface with synthetic API responses, all assurance pages/register forms, mobile width and automated accessibility gate.

Validation evidence is recorded in [ASSURANCE_VALIDATION.md](ASSURANCE_VALIDATION.md). Synthetic tests do not establish customer-provider consent, a real restore drill or independent legal/compliance assurance.

## Branded assurance reporting

Use **Freeze assurance report** to generate immutable PDF, Excel or PowerPoint editions containing control confidence, service coverage, data quality, configured metrics, evidence reuse, release readiness and board decisions. The source payload, branding, hash and generation actor are retained by the existing report-edition pipeline. Program Owner - Matthew Harris remains independent of customer branding.

## Transport and recovery operating limits

The existing HTTPS gateway also imposes its request/response size ceiling. The 10 MiB decoded-evidence limit is an application upper bound, not a guarantee that every encoded package fits that gateway. Base64 expansion and record/catalog metadata add size. Large workspaces should use the managed database recovery process. Archived-record recovery deliberately preserves current stored contents and does not replay uploaded evidence or approvals.

## Accepted release

Runtime source `6a89522c234b315a21912650e7016c7e0b7e9a26` is deployed as ECS task definition `cyber-ops-online-studio-web:15`. At November 1, 2026, 15:28:22 CST, rollout was COMPLETED with two running tasks, no pending/failed tasks and two healthy targets. The unchanged backend passed 128 tests; seven interface tests, browser/mobile/accessibility acceptance, security checks and container smoke validation passed. See [release evidence](ASSURANCE_VALIDATION.md) for the precise validation-source boundaries and image digest.
