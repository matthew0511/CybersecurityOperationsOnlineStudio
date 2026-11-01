# AI Governance — original Notion Hub to AWS

Program Owner - Matthew Harris

## Source and authority

This implementation uses **AI Governance**, page `2710be56313383029852016a4e6cb6e7`, under **Cybersecurity Operations Hub**, page `df00be5631338303ac1781ee4baff573`. The source is the user's 28 October 2026 Notion export, Library identity `libfile_ac4f239fdba08191b824295aeeda5d40`. The current Notion connection returned object-not-found for both original pages. The separate AI Use-Case Approval & Governance Hub and Vendor Risk Management Hub were excluded as implementation sources.

The complete original Markdown is retained in [AI_GOVERNANCE_SOURCE_NOTION_2026-10-28.md](AI_GOVERNANCE_SOURCE_NOTION_2026-10-28.md). Its SHA-256, source IDs, snapshot date and provenance accompany the structured application reference. The source has 17 numbered sections, an overview and primary references. It remains a working reference, not an approved organizational policy or a current legal determination. Linked legal and framework guidance must be rechecked before adoption. No live Notion synchronization or production-record migration is claimed.

## Where to work

Select the organization, then **Governance → AI Governance**. The **Overview** shows inventory, current scoped authorizations, release holds and high/critical exposure. **Registers** provides eleven linked record types. **Source reference** contains the full captured guidance with searchable sections, readable tables and original external reference links. Screen appearance follows the shared Light/Dark/System setting.

| Register | Source coverage |
|---|---|
| AI charter & decision authority | Charter, jurisdiction, delegation, concurrence, quorum, conflicts, emergency authority and recordkeeping |
| AI use-case inventory | Product feature, purpose, owner, patient/clinical exposure, data categories, local risk tier, autonomy, configuration, oversight, review and exit |
| AI data flows & dependencies | Data/authority hops, suppliers, subprocessors, tenancy/geography, secondary use, retention, contract/BAA review and evidence quality |
| AI lifecycle & professional reviews | Intake, diligence, design/contract, pilot, production, ongoing operation and retirement; business/vendor/security/privacy/clinical/operations reviews |
| AI validation & test results | Representative workflow, boundaries, clinical failures, authorization, adversarial inputs, human review, resilience and regression; explicit criteria and limitations |
| AI decisions & release authorization | Separate sponsorship, professional review, residual-risk acceptance and release decisions; scope, stage, authority, conditions, expiry and authenticated sign-off |
| AI exceptions & compensating controls | Defined deviation, justification, tested compensating controls, independent approval, expiry and exit |
| AI agent authority & safeguards | Identities, permission scopes, tool/destination/volume limits, approval enforcement, replay protection, retrieval boundaries, fail-closed behavior and revocation |
| AI monitoring & periodic review | Defined metrics/denominators, observation period, benefit/review effort, thresholds, owner and next checkpoint |
| AI incidents, changes & retirement | Scope/impact, containment, queued actions, evidence preservation, downstream reconciliation, restart or decommission verification |
| AI workforce readiness | Audience, role-specific competency, practical demonstration, limitations and refresher |

The source's dental/healthcare playbooks, eight suggested local controls, 90-day roadmap, NIST organizing crosswalk and executive decision-brief guidance remain available in full in Source reference. These are recommendations and examples, not preapproved live deployments, installed external controls or automatically generated tasks.

## Operating workflow

1. Create a charter if applicable and record actual delegated authority. Create a specific use case and assign an enabled organization member as business owner. State the product feature, configuration, intended/prohibited uses, human review, stop/fallback, data exposure and review date.
2. Create the data/dependency map and any agent-authority records before completing reviews or evaluations. Unknown PHI/clinical/patient-facing exposure cannot use the Lower or Moderate pathway; consequential autonomy requires Critical / special review. These are conservative Studio defaults, not classifications prescribed by HSCC or NIST.
3. Record professional reviews and local evaluations against the current configuration. Create records in Draft, move them to In progress and then Completed when their work is actually finished. Evidence must exist, belong to the organization and have a current verified review to count toward readiness. Operator-entered professional conclusions remain management records; history separately records the authenticated actor.
4. Create the appropriate decision type. A sponsorship or residual-risk decision is not a release authorization. Set the precise permitted scope, pilot/production stage, designated approver, authority basis, operating conditions, risk rationale, evidence and expiration. Submit the draft. An independent assigned reviewer must reauthenticate to approve; the creator cannot self-approve.
5. Monitor the resulting current authorization in Overview. Reassess configuration, scope, dependencies, events and evidence changes. Closing the latest release decision removes it from current authorization; an older decision is not silently reactivated. Record external shutdown/revocation and retirement actions in their real systems and retain the evidence here.

### Release gate semantics

The default checklist requires current completed business, vendor, security, privacy, contract and operations reviews; clinical/patient-facing exposure adds clinical review, and Critical adds special-authority review. It requires passing ordinary-workflow, human-review and resilience evaluation families; higher exposure or additional authority adds authorization/adversarial tests, and clinical scope adds clinical tests. Every counted review/evaluation needs verified evidence and a matching configuration baseline.

Missing data/dependency mapping, unknown sensitive/clinical exposure, overdue governance review, missing agent safeguards, unresolved material changes/high-impact events, current high-impact failed evaluations and expired active exceptions impose holds. The application does not convert a completion percentage or vendor assurance claim into approval. Exceptions are independently reviewed records and do not automatically waive release holds or legal obligations.

The authorization indicator requires an independently approved release decision, permitted/restricted outcome, unexpired authorization, current evidence, no holds and a matching configuration/evidence digest. It does not claim an external AI service actually enforces these conditions. Pilot and production are distinct authorization stages. Configuration updates invalidate the indicator; prior reviews and approvals remain in history rather than being erased or retrospectively rewritten.

## Data, APIs and security

The eleven module keys are `ai_charter`, `ai_use_case`, `ai_dataflow`, `ai_review`, `ai_evaluation`, `ai_decision`, `ai_exception`, `ai_agent`, `ai_monitor`, `ai_event` and `ai_training`. They reuse `pl_records` and `pl_history` with existing tenant policies, version checks and immutable history triggers. No table, policy, owner credential or production business record is replaced by this release.

- Authenticated reference: `GET /api/platform/ai/reference`.
- Scoped operating summary: `GET /api/platform/{org}/ai/overview`.
- Existing typed CRUD: `/api/platform/{org}/records/{kind}` and `/record/{id}/status`.
- Branded frozen reports: existing editions API with `template=ai_governance` and `format=pdf|xlsx|pptx`.

Organization membership, roles, capability restrictions and CSRF rules apply. Reference IDs and related evidence are validated in the same organization; UI filtering is not the access boundary. The server derives baseline digests rather than trusting client-supplied approval metadata. Retrieved source text is rendered using text nodes and allowlisted HTTPS links, never injected as HTML or evaluated as code. Source/reference fields must not contain credentials or sensitive original patient material.

AI board reports freeze the current inventory, release holds and register counts with source payload, organization branding, file hash, generation actor and fixed Program Owner attribution. The snapshot is current as of export and does not reconstruct historical authorization. Spreadsheet text uses the existing formula-injection defenses. Export permissions and scoped edition downloads remain enforced.

## Deployment and rollback

This change adds an optional `ApplicationImageTag` parameter to the existing runtime template. It changes only the application image and default builder image target; migration and restore-verifier task definitions remain on the existing `ImageTag`. The source generator reproduces the checked template. This application-only release pattern prevents a UI/domain release from retiring a verifier referenced by the restore schedule.

Build and validate the exact Git SHA in isolated CodeBuild, inspect the CloudFormation change set, then update `ApplicationImageTag` and `SourceCommit` while preserving the other parameters. No privileged database migration is needed. Rollback sets `ApplicationImageTag` to the previously accepted application image; retain the additive record data. Verify readiness, task counts, alarms, exact public asset bytes and protected AI API authentication after rollout.

## Verification and limits

Tests cover source provenance, register availability, authentication, viewer denial, cross-organization reference rejection, malformed enums, sensitive/clinical risk escalation, independent approval, readiness without authorization, stale configuration, material-event holds, evidence invalidation, closed decisions, frozen report hashes and formula-safe exports. The browser suite checks AI navigation, source searching and decision forms in addition to the existing appearance, mobile and accessibility workflow checks. Full security/fuzz and regression gates remain required.

No source examples were loaded as live records. No vendor credential, model invocation, patient-data flow, notification, external suspension action or clinical/legal determination is created by this migration. The source snapshot is complete; each organization's actual adoption, role delegation, professional review, training and operational-control evidence must be established through its own records.
