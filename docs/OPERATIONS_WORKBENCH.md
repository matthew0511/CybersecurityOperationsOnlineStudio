# Operations workbench: technical implementation and operating guide

Program Owner - Matthew Harris

Document date: November 1, 2026, America/Chicago. Implementation status: published and deployed; the latest verification record supersedes the historical candidate evidence. This guide extends, rather than replaces, the AWS architecture, security validation, AI governance and platform guides.

## Navigation and scope

Open **Operations workbench** from the application navigation. The default Overview contains validation outcomes, evidence follow-ups, effective exception expiration and investment scenario totals. Detailed registers live on secondary pages so the main workspace does not gain fifteen competing navigation entries.

| Requested capability | Secondary page | Implementation |
|---|---|---|
| Continuous control validation | Validation & evidence | Evidence, integration freshness and completed-control-test checks; manual and background runs with dated history |
| Evidence freshness management | Validation & evidence | Evidence review owners, dates, expiration and replacement references alongside existing evidence review/retention controls |
| Asset-to-risk dependency mapping | Business impact | Typed asset/risk/control/vendor links and transitive dependent-asset inspection |
| Access certification campaigns | Access reviews | Inventory import, assigned reviewer decisions, removal evidence and campaign completion gate |
| Security exception lifecycle | Exceptions & changes | Existing independent approval, justification, compensating controls and expiration; effective expired state and internal escalation |
| Business vulnerability prioritization | Vulnerabilities | Explicit CVSS, exposure, criticality and data context; derived score and verified retest closure |
| Change security review | Exceptions & changes | Security impact, test plan, rollback and independent approval; linked post-change verification |
| Data processing and retention register | Data governance | Purpose, data categories, systems, locations, sharing, holds, retention and disposal verification |
| Acquisition security onboarding | Acquisitions | Linked acquisition workspace and dated due-diligence/Day 1/30/60/90 template generation |
| Recovery exercise verification | Recovery exercises | Measured application restoration and recovered-data timestamps compared with BIA objectives |
| Customer and auditor portal | Customer & auditor portal | Existing scoped expiring/revocable invitations, reviewed-content selection, questions and download history |
| Security workflow builder | Workflow builder | Allowlisted triggers, internal actions, independent approval, activation, deduplication and execution history |
| Integration health dashboard | Integration health | Authentication, last test/pull, source age, partial pull, failure and staging reconciliation; owner access |
| Security investment planning | Investment planning | Risk/control/service-linked proposals, cost assumptions, staffing/milestones and scenario totals |
| Post-quantum readiness register | PQC readiness | Cryptographic assets, vendors, protocols/libraries, certificates, confidentiality lifetime and migration dependencies |

## Persistence and authorization

This release uses existing additive platform tables without a schema migration. Typed definitions are in `operations_catalog.py`, registered in `catalog.MODULES`. Business objects use `pl_records`; immutable event snapshots use `pl_history`; per-rule execution claims use the existing unique `(organization_id,schedule_id,bucket)` key in `pl_schedule_runs`. Existing `pl_integrations`, `pl_jobs`, `pl_external`, `pl_rooms`, `pl_room_questions`, `pl_editions` and encrypted evidence storage remain authoritative for their respective functions.

Every business row retains its organization, ID, kind, title, owner, due date, status, integer version, creation/update actors and timestamps. New operations records default an omitted owner to the authenticated creator. Cross-object references are validated in the same organization. Dependencies reject cycles with the existing bounded graph traversal. Queries bind values independently of SQL text; clients cannot provide table names, SQL, shell commands or executable conditions.

The existing session, organization membership, capability restrictions, CSRF protection and PostgreSQL row-level policies apply. Viewers cannot mutate operations records or run checks. Only the assigned campaign reviewer can import accounts or save access decisions. Only the installation owner can configure workflow rules. An independent assigned reviewer with review privileges and reauthentication must approve a change or workflow version before activation. Ordinary settings cannot remove the fixed Program Owner attribution.

Updates require the last observed `id` and `version`; conflicting changes return 409. Finalized review/test records must reopen before editing. Approval metadata and calculated fields are server-owned: client submissions cannot forge an approver or calculated outcome. Related record deletion or loss of access fails closed rather than silently resolving to another organization.

## Continuous validation

Create an internal control, its evidence and/or test plan, then an `op_check` record. Choose:

* `evidence_current`: all artifacts linked to the control must currently have a verified evidence review. An empty evidence list is Unknown.
* `integration_fresh`: choose an existing same-organization integration and a positive maximum age in hours. A recorded successful inbound pull must exist; otherwise the outcome is Unknown. A successful recent pull passes only if the connection is enabled/authenticated, the latest pull succeeded and the bounded pull does not report additional pages omitted.
* `control_result`: find the latest completed/active control test through its linked test plan. Failed/partial results, overdue retest dates or evidence that is no longer verified fail. No completed test is Unknown.

Open the check and select **Run validation now**. A manual run records `operations:validation` history with check version, control version, source IDs, result, reason and UTC observation timestamp. Activate the record to run through the existing worker at its configured 1–3650 day interval. The worker does not scan an arbitrary network or run a customer script.

The overview reports Unknown when a check has never run, its version/control baseline changed or its execution interval expired. A source check is a dated observation; external configuration may change between executions. These checks validate recorded evidence, completed tests and connector freshness. They are not a universal live configuration collector for every vendor or security control.

## Evidence schedules and exception expiration

Create `op_evidence` with the actual evidence reference, review date, responsible owner and optional local expiration/replacement. The evidence follow-up queue includes due reviews and local expirations. Existing artifact review status, artifact expiration, legal holds and retention remain the enforcement sources for normal evidence access and deletion. A replacement is a separate artifact; the source is preserved.

Exceptions retain the existing justification, compensating controls, assigned independent approver, expiration and approval history. The overview calculates effective `expired` status without rewriting the historical approval. An active workflow with `exception_expired` creates an internal follow-up. Renew by reopening and submitting a new independently reviewed version; do not edit a historical approval in place.

## Dependency and business impact inspection

Create assets and prerequisite dependencies first. An `op_link` attaches a business-impact explanation to an asset and its risk, control and vendor references. Open any asset and select **Inspect business impact**. The server traverses reverse dependencies with a visited set and returns the original asset, all recorded downstream dependents and their impact relationships. Only recorded relationships are included; no automatic asset discovery or clinical causality inference is performed.

## Access review campaign runbook

Create `op_campaign` with a scope, inventory-source reference, review date and enabled organization reviewer. The assigned reviewer opens it and uses the CSV wizard to map and preview 1–1000 rows. The API retains this object shape:

```json
[{"account":"synthetic.user","system":"Synthetic directory","privileged":false,"last_seen":"2026-10-01"}]
```

Allowed import fields are `account`, `system`, `privileged` and `last_seen`. Existing `(account,system)` pairs within the campaign are skipped; importing does not overwrite prior decisions. The full import is transactional: an invalid entry rolls the operation back. Passwords, tokens and authentication factors are not import fields.

Each `op_access` decision references the campaign. Retain/revoke requires rationale. Revocation cannot complete or close until a removal timestamp and verified evidence are present. A campaign cannot complete/close until every imported account review is completed; an empty campaign is not counted complete. Recording a decision does not revoke access inside Entra, AWS or another external system. The operator performs removal using the authoritative identity platform and attaches verification.

## Vulnerability prioritization and closure

Create `op_vulnerability` with an affected asset, CVSS (0–10), explicit exposure and business criticality. Record exploitation only when supported by the finding source. The Studio planning score is:

`min(100, 5 × CVSS + exposure + criticality + exploitation + regulated_data)`

Exposure points: internal 0, partner 8, internet 15. Criticality points: low 0, moderate 5, high 10, critical 15. Confirmed exploitation adds 10; an asset classified regulated adds 5. Bands are critical at 80+, high at 60+, moderate at 35+, otherwise low. This is a transparent local prioritization method, not an exploit probability or replacement for the source severity method.

Use owner/due date for remediation accountability. Completing or closing a finding requires a passing retest with verified supporting evidence. A string saying “fixed” does not satisfy the gate. No new scanner subscription, vendor consent or network scan is implied by a register record.

## Change approval and post-change validation

An `op_change` requires security impact/checklist, test procedure, rollback procedure and an assigned independent approver. Link affected assets and controls. Submit, independently approve with reauthentication and activate using the existing status controls.

After implementation, create `op_change_result` against the approved/active/completed change. It records observations, result and the approved change version; a pass requires verified evidence. This separate record preserves pre-change approval and post-change verification as distinct events. Reopening the source approval does not erase the recorded historical verification; review its version before relying on it for a later change.

## Data processing, retention and disposal

`op_processing` records the system, categories, purpose, locations, sharing relationships, retention period, hold flag, planned deletion and disposal state. Marking disposal verified requires verified evidence and is prohibited while the record is on legal hold. It records proof of an operator-performed deletion; it does not issue deletion commands to external systems, determine legal retention or collect patient records. The existing evidence hold workflow continues to protect the actual evidence artifact.

## Acquisition milestones

Create an office and `op_acquisition`; record Day 1/closing date, scope and acceptance criteria. Open it and generate the template. Five linked milestone records are created atomically: due diligence (14 days before closing), Day 1, Day 30, Day 60 and Day 90. With no closing date, due dates remain unset rather than invented. The template covers inherited access, assets, contracts, monitoring, backup/recovery, remediation and service handoff. Existing unarchived milestones prevent accidental duplicate generation. Tailor checklist details and owners before execution.

## Measured recovery exercise

Create a BIA with RTO/RPO in hours, then `op_recovery` with the BIA and optional runbook. Record exercise/disruption start, application acceptance time and recovered-data timestamp. Observation times cannot be future values; completion must follow start, and recovered data must be at or before start.

Actual recovery time = application acceptance minus start. Actual data loss = start minus recovered-data timestamp. Calculations compare these hours with the referenced BIA objectives and preserve its version. An application-check pass requires all timestamps, documented application/dependency checks and verified evidence. A technically passing restoration can still miss RTO/RPO; the objective flags remain false. This does not start an AWS database restore or assert a new live restore drill occurred.

## Portal and integration health

The secondary portal uses existing one-use audit-room invitations, 1–30 day expiration, organization scope, revocation and separate auditor cookies. The operations portal requests reviewed-only creation: selected program records must be approved, active or completed; selected evidence must have a current verified review. Invitations grant only selected content. Possession of a link is not independent verification of a person's identity.

External users may ask questions and download selected evidence/frozen editions. New download events record room, artifact ID/type, actor label and UTC time in append-only history. Owners can open portal activity to read questions and download history. Previously issued rooms retain their original semantics and are not retroactively converted into a different approval process. Use frozen editions where an immutable report is needed; a program record invitation otherwise displays its authorized current record.

Integration health is owner-only and returns no credential fields. It shows enabled/authentication state, last authentication test, last successful inbound pull, age in hours, latest pull outcome, partial-source flag and staged/promoted counts. Authentication, freshness, coverage and promotion are separate measures. Staged/promoted counts are local reconciliation, not a promise that every remote row was imported. Configure/test/enable/pull through **App integrations**. This release does not provision customer vendor accounts or grant third-party consent.

## Workflow configuration, safe retries and limits

`op_workflow` uses four explicit triggers: `checks_fail`, `evidence_due`, `exception_expired`, `review_due`. Actions are `in_app` and `remediation`; remediation requires a same-organization risk reference. The rule includes assignee, instructions, advance warning (0–365 days), and independent approver. The installation owner configures it, another authorized reviewer approves it with reauthentication, and the owner activates the approved version.

The existing background worker runs checks and rules under its advisory lock and transaction. An atomic schedule claim deduplicates each `(organization, rule, rule version, target, UTC day)`. Each rule handles at most 200 matching targets per tick. Completed/closed targets are excluded. Rule creation/assignee accounts must remain enabled and authorized organization members. Workflow history records rule version, target, action, assignee and run ID. A failed operations transaction rolls back its claims and outputs, allowing a later tick to retry. Previously committed claims prevent duplicate work for that day.

An overdue unresolved target can produce another reminder/task on another UTC day. This is intentional recurring escalation, not unlimited per-tick duplication. There are no arbitrary expressions, shell execution, external chat/email actions or automatic approval. Changing a rule requires reopening and new independent approval. The application worker must be running; the UI alone is not a scheduler.

## Investment and PQC calculations

Investment proposals link a named scenario to risks, controls and services. Record one-time cost, annual recurring cost, a 1–30 year horizon, assumed risk reduction (0–100%), staffing/milestones and explicit assumptions. Total = one-time + annual × years, without discounting. Scenario totals add recorded proposals; avoid double-counting mutually exclusive options or mixing currencies. A reduction percentage is an operator assumption, not measured savings.

PQC records capture asset, algorithm/protocol/library, key size, certificate expiry, vendor, readiness, confidentiality lifetime, migration duration, prerequisites and evidence. Dependencies are scoped and acyclic. Marking vendor readiness `ready` requires verified evidence. Planning horizon = confidentiality lifetime + migration duration; it does not estimate a quantum arrival date, validate a cryptographic implementation or certify compliance. No cryptographic keys are uploaded or changed.

## API and reporting contract

New endpoints:

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/platform/{org}/operations/overview` | Scoped counts, checks, due evidence, exceptions, scenarios and execution history; owner-only connector details |
| GET | `/api/platform/{org}/operations/impact/{asset_id}` | Reverse dependency traversal and typed business-impact links |
| POST | `/api/platform/{org}/operations/{id}/run` | Version-bound check run, campaign import or acquisition template; allowlisted record kinds |
| GET | `/api/platform/{org}/rooms/{id}/activity` | Owner-only room questions and download history |

All operations registers use existing `/records/{kind}`, `/record/{id}`, `/record/{id}/status`, `/choices/{kind}` and history endpoints. Write examples include `{title,owner,due_on,data}`; updates include `{id,version}`. Campaign run additionally includes `accounts`. Unknown fields, malformed dates/numbers, cross-tenant references and unsupported transitions fail with bounded client errors. No 409 should be retried by silently overwriting current data.

Freeze an **Operational assurance and investment review** as PDF, XLSX or PPTX from Overview. Its source contains a current snapshot of validation, evidence follow-ups, effective exceptions and scenario totals plus normal branding/hash/owner attribution. It is an as-of snapshot, not retrospective compliance history. Existing technical/audit reports and source registers remain available for full detail.

## Validation, deployment and ownership

`tests/test_operations.py` exercises tenant scope, viewer denial, source/evidence invalidation, access reviewer restrictions, inventory idempotency, dependency mapping/cycles, vulnerability retest gates, legal holds, budget arithmetic, acquisition dates, measured recovery, independent change approval, workflow execution/deduplication and malformed/SQL-shaped data. Existing fuzz, security, AI governance, branding and browser acceptance remain required release gates.

Matthew Harris is accountable for product acceptance, named technical delegation, real integration consent, access removals, legal/retention decisions and recovery objectives. The release operator must retain accepted Git SHA, test/build IDs, container digest, task revision, deployment health and UTC/America/Chicago observation times. Do not describe a pushed commit as deployed or a test fixture as a real tenant integration.


## Generated field dictionary


### Continuous validation checks (`op_check`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `control_id` | reference | Yes | control |
| `check_type` | select | No | evidence_current, integration_fresh, control_result |
| `integration_id` | text | No | Typed server validation |
| `max_age_hours` | number | No | Typed server validation |
| `frequency_days` | number | Yes | Typed server validation |
| `remediation_owner` | text | No | Typed server validation |

### Evidence review schedules (`op_evidence`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `evidence_id` | reference | Yes | legacy:evidence |
| `review_on` | date | No | Typed server validation |
| `expires_on` | date | No | Typed server validation |
| `approver` | text | No | Typed server validation |
| `replacement_id` | reference | No | legacy:evidence |
| `notes` | textarea | No | Typed server validation |

### Business impact relationships (`op_link`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `asset_id` | reference | Yes | asset |
| `risk_id` | reference | No | legacy:risk |
| `control_id` | reference | No | control |
| `vendor_id` | reference | No | legacy:vendor |
| `impact` | textarea | No | Typed server validation |

### Access certification campaigns (`op_campaign`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `scope` | textarea | No | Typed server validation |
| `review_on` | date | No | Typed server validation |
| `reviewer` | text | Yes | Typed server validation |
| `source` | text | No | Typed server validation |

### Access review decisions (`op_access`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `campaign_id` | reference | Yes | op_campaign |
| `account` | text | Yes | Typed server validation |
| `system` | text | Yes | Typed server validation |
| `privileged` | boolean | No | Typed server validation |
| `last_seen` | date | No | Typed server validation |
| `decision` | select | No | pending, retain, revoke |
| `rationale` | textarea | No | Typed server validation |
| `removed_at` | datetime | No | Typed server validation |
| `evidence_ids` | references | No | legacy:evidence |

### Business vulnerability prioritization (`op_vulnerability`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `asset_id` | reference | Yes | asset |
| `cvss` | number | Yes | Typed server validation |
| `exposure` | select | No | internal, partner, internet |
| `exploited` | boolean | No | Typed server validation |
| `criticality` | select | No | low, moderate, high, critical |
| `source` | text | No | Typed server validation |
| `remediation` | textarea | No | Typed server validation |
| `retest` | select | No | not_tested, pass, fail |
| `evidence_ids` | references | No | legacy:evidence |

### Security change reviews (`op_change`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `asset_ids` | references | No | asset |
| `control_ids` | references | No | control |
| `risk` | textarea | No | Typed server validation |
| `test_plan` | textarea | No | Typed server validation |
| `rollback` | textarea | No | Typed server validation |
| `approver` | text | Yes | Typed server validation |
| `post_result` | select | No | not_tested, pass, fail |
| `evidence_ids` | references | No | legacy:evidence |

### Post-change verification (`op_change_result`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `change_id` | reference | Yes | op_change |
| `result` | select | No | pass, fail |
| `observations` | textarea | No | Typed server validation |
| `evidence_ids` | references | No | legacy:evidence |

### Data processing and retention register (`op_processing`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `asset_id` | reference | Yes | asset |
| `categories` | textarea | No | Typed server validation |
| `purpose` | textarea | No | Typed server validation |
| `locations` | textarea | No | Typed server validation |
| `sharing` | textarea | No | Typed server validation |
| `retention_days` | number | No | Typed server validation |
| `legal_hold` | boolean | No | Typed server validation |
| `delete_on` | date | No | Typed server validation |
| `disposal` | select | No | not_due, planned, verified |
| `evidence_ids` | references | No | legacy:evidence |

### Acquisition security workspaces (`op_acquisition`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `site_id` | reference | No | site |
| `close_on` | date | No | Typed server validation |
| `scope` | textarea | No | Typed server validation |
| `acceptance` | textarea | No | Typed server validation |

### Acquisition integration milestones (`op_milestone`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `acquisition_id` | reference | Yes | op_acquisition |
| `phase` | select | No | due_diligence, day_1, day_30, day_60, day_90 |
| `checklist` | textarea | No | Typed server validation |
| `evidence_ids` | references | No | legacy:evidence |

### Measured recovery exercises (`op_recovery`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `bia_id` | reference | Yes | bia |
| `runbook_id` | reference | No | runbook |
| `started_at` | datetime | No | Typed server validation |
| `completed_at` | datetime | No | Typed server validation |
| `recovery_point_at` | datetime | No | Typed server validation |
| `result` | select | No | planned, running, pass, fail |
| `checks` | textarea | No | Typed server validation |
| `corrective_actions` | textarea | No | Typed server validation |
| `evidence_ids` | references | No | legacy:evidence |

### Security workflow rules (`op_workflow`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `risk_id` | reference | No | legacy:risk |
| `trigger` | select | No | checks_fail, evidence_due, exception_expired, review_due |
| `action` | select | No | in_app, remediation |
| `assignee` | text | Yes | Typed server validation |
| `approver` | text | Yes | Typed server validation |
| `instructions` | textarea | No | Typed server validation |
| `lead_days` | number | No | Typed server validation |

### Security investment scenarios (`op_investment`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `scenario` | text | Yes | Typed server validation |
| `risk_id` | reference | No | legacy:risk |
| `control_id` | reference | No | control |
| `asset_id` | reference | No | asset |
| `one_time_cost` | number | No | Typed server validation |
| `annual_cost` | number | No | Typed server validation |
| `years` | number | Yes | Typed server validation |
| `expected_reduction` | number | No | Typed server validation |
| `assumptions` | textarea | No | Typed server validation |
| `milestones` | textarea | No | Typed server validation |

### Post-quantum readiness register (`op_crypto`)

| Field | Type | Required | Reference / allowed values |
|---|---|---|---|
| `asset_id` | reference | Yes | asset |
| `algorithm` | text | Yes | Typed server validation |
| `key_bits` | number | No | Typed server validation |
| `certificate_expires` | date | No | Typed server validation |
| `vendor_id` | reference | No | legacy:vendor |
| `vendor_readiness` | select | No | unknown, assessment, roadmap, testing, ready |
| `data_lifetime_years` | number | No | Typed server validation |
| `migration_years` | number | No | Typed server validation |
| `dependencies` | references | No | op_crypto |
| `plan` | textarea | No | Typed server validation |
| `evidence_ids` | references | No | legacy:evidence |


Documentation generated: 2026-11-01T15:42:19.714298+00:00 UTC / 2026-11-01T09:42:19.714388-06:00 America/Chicago. Accountable Program Owner: Matthew Harris.


## Release validation and publication status

Accountable Program Owner: Matthew Harris.

Recorded UTC: 2026-11-01T15:54:26.331049+00:00

Recorded America/Chicago: 2026-11-01T09:54:26.331049-06:00

The implementation is an unpublished release candidate based on GitHub main `aa54df7b80ecb403c46fdb6a26930e7d3ee73f09`. No GitHub publication, registry push, CloudFormation update, live database change or ECS rollout was performed for this candidate. Automatic approval review rejected the public branch push because it classified implementation authorization as insufficient for public publication of potentially sensitive source/documentation. Public publication and deployment require explicit follow-up authorization; private acceptance tests were completed separately.

The first private run identified an access-review permission mismatch (112 passed, one failed). The assigned-reviewer path was corrected. The next full run passed 115 backend checks and the appearance gate, while the new browser selector was ambiguous between the original Vulnerabilities navigation item and its new secondary-page tab. The selector was scoped to the secondary-page group. A source-import initialization issue was also corrected before final application acceptance.

Final application validation and browser results are recorded below. A combined historical job may retain a failed status for the earlier browser selector; its individual successful backend/container gates are recorded separately. A later browser-only run validates the corrected test against unchanged application bytes.

* Initial private integration run — cyber-ops-online-studio-web:3dc90687-8bb1-4e06-a289-d4b39be387a9; 112 backend passed, one access-review permission mismatch; corrected before final validation; 2026-11-01T15:43:07Z / 09:43:07 CST
* Corrected access review and full regression run — cyber-ops-online-studio-web:41e319ba-64a4-4c5e-9654-752637cb524b; 115 backend passed; seven UI calculation/appearance tests passed; appearance browser passed; combined job failed on ambiguous new browser test selector; 2026-11-01T15:49:14Z / 09:49:14 CST
* Final application, expanded backend and container validation — cyber-ops-online-studio-web:a6759034-15af-476d-99c6-a6c0dccac110; 116 backend passed (no skips); Bandit passed; dependency audit reported no known vulnerabilities; seven JavaScript tests passed; appearance browser passed; Docker image built and read-only/non-root/database/temporary-volume smoke passed. Aggregate job FAILED solely on the earlier ambiguous browser test selector. Local validation image ID sha256:17dae6d08ae7fb1022d8ce144af444904117202bed83fe4fefafd8d36bf13782; never pushed.; 2026-11-01T15:52:36.758Z / 09:52:36.758 CST
* Corrected browser selector and accessibility acceptance — cyber-ops-online-studio-web:6ca53f60-01c7-47d1-92f9-40b96f31df95; SUCCEEDED. Real application pages with synthetic APIs: all eleven secondary register groups, portal, integration health, mobile layout, existing user flows and automated WCAG serious/critical gate passed. Runtime source hashes match final application validation; only the test selector differs.; 2026-11-01T15:52:25.726Z / 09:52:25.726 CST

Static full-web Bandit and dependency vulnerability audit passed. Existing deterministic fuzz/SQL/tenant-boundary tests are included in the full backend suite. Browser acceptance uses synthetic API responses against real application HTML/JavaScript/CSS; it is separate from the PostgreSQL-backed endpoint tests. No live customer integration or real restore drill is asserted. Test-client deprecation warnings are retained as non-failing observations.

Release boundary: real provider consent, imported inventories, reviewer/assignee selection, workflow activation, business recovery objectives and evidence collection remain organization configuration tasks. The application never performs an external access removal, arbitrary shell action, cryptographic migration or external notification merely because a record exists.


## Cosmetic presentation extension

See [COSMETIC_REFINEMENTS.md](COSMETIC_REFINEMENTS.md). The CSV wizard and grouped navigation preserve the existing import and authorization contracts.


## Published release and production verification

Program Owner - Matthew Harris

This release supersedes the earlier candidate-only status and publication block recorded below. The user explicitly authorized public GitHub publication and AWS deployment. The merged release preserves the newer assurance/productivity capabilities and all fifteen Operations additions.

Verified UTC: `2026-11-01T21:44:09.244378+00:00`

Application source commit: `40364bf1405d1f3f879cb2dc39eaaac365af6629`

Release build: `cyber-ops-online-studio-web:24a7bb43-2111-4d42-a8e3-380445a148df`

Pinned container image: `891377316941.dkr.ecr.us-east-2.amazonaws.com/cyber-ops-online-studio-dev@sha256:627a65107e4caea45eafaec463416d5a7ed436f5c77f50946bee73a0e0691743`

Production task definition: `cyber-ops-online-studio-web:16`

Deployment: `ecs-svc/1717127098235749295`

Release gates passed: 128 PostgreSQL-backed Python tests, 13 JavaScript tests, appearance and experience browser acceptance, infrastructure lint, full-web Bandit, dependency audit, and the read-only non-root container/database/temporary-volume smoke check. Browser acceptance retains assurance/productivity coverage and adds grouped navigation, CSV mapping/preview/import, record sections, action hierarchy, themes, responsive layout and automated serious/critical accessibility checks. This is bounded test coverage, not exhaustive accessibility certification.

ECS reached a completed rolling deployment with two desired/running tasks and healthy load-balancer targets. Live HTTPS checks passed for health/readiness, database connectivity, protected API authentication, security headers and fixed Program Owner attribution. The deployed polish assets matched the accepted source bytes. Production checks used no customer credentials or business-record changes.

Runtime configuration, encryption/secret references, read-only filesystem, non-root user, permissions and rollback settings were preserved from task revision 15. No schema migration was required. Rollback target is revision 15. The earlier CloudFormation application-image/task metadata remains stale relative to the directly registered ECS revisions; future infrastructure updates must reconcile that metadata before applying an older task definition. Restore verification schedules were unchanged.
