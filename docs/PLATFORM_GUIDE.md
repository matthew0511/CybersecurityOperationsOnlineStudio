# Platform implementation and operations guide

Program Owner - Matthew Harris

Authenticated documentation subpage: `/documentation`. External services require customer-owned credentials, consent and a successful provider operation.

## 50-feature implementation index

| # | Enhancement | Workflow and activation |
|---|---|---|
| 1 | Multifactor authentication | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 2 | Microsoft Entra single sign-on | Use the security, integration, reporting or operational area described in the guides below. Entra app registration and approved account mappings |
| 3 | Session management | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 4 | Secure account recovery | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 5 | Granular permissions | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 6 | Database organization isolation | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 7 | Malware scanning and quarantine | Use the security, integration, reporting or operational area described in the guides below. GuardDuty scan bucket and runtime IAM |
| 8 | Sensitive-data upload checks | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 9 | Restore verification | Program center → Restore verification records; create a typed record, review its current version and use the available workflow actions. Restore executor and approved isolated restore resources |
| 10 | Database high availability | Use the security, integration, reporting or operational area described in the guides below. AWS database Multi-AZ configuration |
| 11 | Operational alerting | Use the security, integration, reporting or operational area described in the guides below. Configured alarm destinations |
| 12 | Security release gates | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 13 | Scoped integration API | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 14 | Microsoft Intune integration | Use the security, integration, reporting or operational area described in the guides below. Microsoft tenant, app registration and device-management consent |
| 15 | Vulnerability scanner integration | Use the security, integration, reporting or operational area described in the guides below. Scanner account and API credentials |
| 16 | Notion synchronization | Use the security, integration, reporting or operational area described in the guides below. Notion integration token and shared data source |
| 17 | Ticketing integrations | Use the security, integration, reporting or operational area described in the guides below. Ticketing account and scoped API credentials |
| 18 | Email notifications | Use the security, integration, reporting or operational area described in the guides below. SES verified sender / notification provider |
| 19 | Notification preferences | Program center → Notification routing; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 20 | Bulk remediation actions | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 21 | Visual questionnaire logic | Program center → Questionnaire logic; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 22 | Versioned scoring methods | Program center → Assessment scoring methods; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 23 | Approved answer library | Program center → Approved answer library; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 24 | Reassessment comparisons | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 25 | Vendor tiering | Program center → Vendor tiering; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 26 | Authenticated risk approvals | Program center → Authenticated risk approvals; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 27 | Temporary delegation | Program center → Temporary delegations; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 28 | Office and business-unit hierarchy | Program center → Offices & business units; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 29 | Asset and dependency inventory | Program center → Assets & service dependencies; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 30 | Business impact assessments | Program center → Business impact assessments; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 31 | Incident case management | Program center → Incident cases; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 32 | Recovery runbooks | Program center → Recovery runbooks; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 33 | Tabletop exercises | Program center → Tabletop exercises; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 34 | Policy approval and acknowledgment | Program center → Policies & acknowledgments; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 35 | Control exceptions | Program center → Control exceptions; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 36 | Versioned framework catalogs | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 37 | Control crosswalks | Program center → Internal controls & crosswalks; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 38 | Repeatable control testing | Program center → Control test plans; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 39 | Evidence lifecycle management | Program center → Evidence retention & holds; create a typed record, review its current version and use the available workflow actions. Available in the application; user configuration may be required |
| 40 | Scoped auditor workspace | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 41 | Report template gallery | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 42 | Frozen report editions | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 43 | Scheduled report delivery | Program center → Scheduled reports; create a typed record, review its current version and use the available workflow actions. Approved recipient list and delivery provider |
| 44 | Period variance explanations | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 45 | PowerPoint exports | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 46 | Paginated report preview | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 47 | Accessibility verification | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 48 | Synthetic demonstration workspace | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 49 | Authorized portfolio dashboard | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |
| 50 | Recycle bin and restoration | Use the security, integration, reporting or operational area described in the guides below. Available in the application; user configuration may be required |

## Getting started

Open Program center, choose a module, and create a draft with a title, responsible owner, due date and the module-specific fields. Saved records have an organization, immutable creation identity, current version and append-only change history. A stale edit returns HTTP 409 instead of overwriting a newer version.

Program center contains live workflows, execution runs, quarantined uploads, framework catalogs, assessment comparisons, bulk remediation, frozen reports, audit rooms, capability restrictions, the recycle bin, portfolio and a synthetic demonstration workspace. App integrations is a separate navigation entry. Account security manages your own authenticator, recovery kit and sessions; installation identity settings are owner-only.

Configure the tenant first, then import authorized framework content and register offices and assets. Complete BIAs before drafting recovery procedures. Create test plans for internal controls, link evidence, and submit policies, reusable answers, exceptions and risk decisions for independent review. New assessments remain narrative and unscored unless a reviewer explicitly creates a scorecard.

Use a separate DEMO organization for training. Demonstration records are clearly marked synthetic, and scheduled external deliveries are not enabled for demonstration organizations. The demonstration does not copy real organizations, credentials, contacts or evidence.


## Authentication, MFA and recovery

Passwords retain the existing Argon2 verification and secure HttpOnly session cookie. An authenticator uses six-digit TOTP with a 30-second interval and a one-step clock window. Each accepted time step can be used only once. Enrollment requires current-password or existing-factor reauthentication, then a code from the new authenticator. Other sessions are revoked on activation.

Authenticator secrets and provider credentials are Fernet-encrypted with a dedicated runtime security key supplied by AWS Secrets Manager through ECS secret injection. They are never stored in source, returned in ordinary configuration reads or written to application logs. Rotating this wrapping key requires a planned re-encryption migration; replacing it without re-encryption makes existing encrypted settings unavailable.

Authenticator recovery codes and password recovery-kit codes are distinct, randomly generated, one-time secrets stored only as SHA-256 hashes. Save the displayed codes offline when issued; the app cannot show them again. A password reset through an unused recovery-kit code revokes every web session but retains enabled MFA. Losing both your password/recovery kit and your authenticator/recovery codes requires an independently authorized administrative recovery process.

Microsoft Entra sign-in uses a tenant-specific authorization-code flow, PKCE, single-use state, a nonce and signature/issuer/audience/expiration validation. Register the exact PUBLIC_ORIGIN plus /api/sso/callback URI in a confidential Entra application. Map the tenant object GUID to an existing enabled Studio account. Matching an email address does not create or link an account. Client credentials alone do not activate sign-in or grant Graph permissions.

Account security lists active sessions with current-session status, expiry, creation metadata and authentication method. Revoke one session or all other sessions. Organization membership revocation is checked on every request. An owner is an administrative role and can still modify deployment infrastructure; fixed Program Owner - Matthew Harris attribution is protected from ordinary application settings, not from source-code administrators.


## Permissions and database isolation

The installation owner manages memberships, integration credentials, API tokens, audit invitations and branding. Editors create and edit business records. Reviewers perform permitted assigned reviews. Viewers read and export authorized data and acknowledge approved policy versions. Capability restrictions can remove records:write, records:approve, records:delete, evidence:upload, reports:export, integrations:manage or tasks:write from a member; they never grant powers beyond the underlying role.

Organization checks remain on the original APIs as well as the new platform APIs. PostgreSQL row-level policies add defense against omitted tenant filters. The authenticated principal sets connection-local studio.actor and studio.organization values; a request body cannot choose the actor. The prior studioapp database role remains an explicitly documented rollback exception; the new platform runtime uses a separate role subject to fail-closed scope policies. Membership and hashed invitation/token lookup tables are excluded from customer-record RLS because they establish identity before a tenant can be known. They are accessible only through constrained server routes.

This is defense in depth for an application with a shared runtime database role. It does not claim that an attacker with arbitrary SQL execution, migration credentials, BYPASSRLS privileges or AWS administrator access is contained by a client-supplied setting. Integration API tokens are separately scoped to one organization, named permissions and an expiration of 1–90 days. Only a hash is retained; revocation and disabled issuing accounts are checked on every call.

Approval records follow draft → submitted → approved/rejected, with reopening to draft for changes. The creator cannot approve their own record, even when that creator is the installation owner. The assigned enabled reviewer or a current scoped delegate must reauthenticate before deciding. The authenticated actor, version, timestamp and delegation are retained in history. Earlier operator-entered reviewer labels are not retroactively converted into authenticated approvals.


## Evidence, malware scanning and sensitive information

New opaque evidence is first placed in a private encrypted, versioned scan bucket and an organization-scoped quarantine record. The runtime may upload and read version-specific scan tags, but cannot write the malware-result tags. GuardDuty owns the independent verdict. Only NO_THREATS_FOUND becomes clean; pending, unsupported, failed and threat-found results remain unavailable for release.

Uploads are limited to 5 MiB. An EICAR test signature is rejected immediately. Text heuristics flag private-key markers, possible Social Security numbers and combined patient/date-of-birth terminology. This is a conservative upload guard, not a comprehensive PHI classifier or legal determination. A clean scan with sensitivity flags additionally requires owner reauthentication and a recorded justification of at least 20 characters.

When a clean artifact has no sensitivity hold, the background worker releases it to the existing encrypted evidence store and attaches it to the originating questionnaire question where applicable. Asynchronous uploads return a quarantine identifier rather than claiming an evidence record already exists. Check Program center → Upload security. Do not repeatedly re-upload a pending file.

Evidence version groups preserve artifact hashes and superseded-version references. A redacted replacement is a separately uploaded artifact linked by an evidence-retention record; the system does not silently overwrite the original. Retention dates and legal holds block archival. The recycle bin archives rather than purges business data; permanent deletion and legal retention judgments require a separately controlled policy.

Logos use a separate bounded PNG/JPEG decode and pixel-only normalization path. Brand logos are at most 2 MiB and eight million source pixels, proportionally normalized within 1200×400. They are not executable templates, remote URLs or arbitrary SVG content.


## Program modules and validation

Office hierarchy and asset prerequisite references are restricted to the same organization and checked for cycles. BIAs record RTO/RPO values in hours and explain clinical, operational and financial impacts. Values are planning inputs, not measured recovery guarantees. Vendor tiering derives a suggested review interval from entered criticality, data access and replacement difficulty; an override requires a rationale.

Incident cases track severity, detection/occurrence time, affected assets, scope, containment, communication records and lessons learned. Notification review is a documented management/legal workflow; the app does not decide whether a reportable breach occurred or send regulatory notices automatically. Append-only record history retains changes and actors.

Runbooks and tabletop exercises contain ordered structured steps. Starting a run copies the exact source version. Each step records state, notes, authenticated completion identity and completion time. Prerequisites must be completed in sequence; reopening an earlier step requires reopening later completed steps first. The app coordinates human recovery actions; it does not execute arbitrary shell commands against production systems.

Policies, exceptions, reusable answers and risk acceptance requests require independent assigned review. Policy acknowledgments identify the exact approved version and account. Exception and risk acceptance expiration is explicit. Reusing a current approved answer records its source version, target assessment and question; evidence must still be currently verified. This does not make the response independently certified.

Control catalogs are imported from UTF-8 CSV using code,title and optional parent_code columns. The owner records framework name, edition, source and license/provenance note and confirms the right to import the content. Imports are capped at 2 MiB and 5000 rows with unique control codes. The application does not ship unlicensed full ISO/CIS control text or pretend a partial reference catalog is a complete framework.

Internal controls map to one or more catalog controls and supporting evidence. Test plans capture procedure, sampling, frequency and pass criteria. A passing recorded test needs current verified evidence. Catalog coverage, implementation status, test results and independently verified assurance are distinct measures.


## Questionnaires, scores and bulk changes

Conditional logic uses explicit parent/child question codes and a small allowlist of equals, not_equals, contains and not_empty operators. No expression is evaluated as code. Cycles are rejected. Rules target an assessment and become effective only when the rule record is active. Hidden answers remain stored and are not silently erased.

Scoring methods have a named method version and question weights. Scorecards require explicit reviewer-entered 0–100 scores and rationale. Narrative statements are not automatically classified as Yes/No or compliance success. The calculated weighted value describes the scored questions and the selected method, not full compliance with an entire framework.

Reassessment comparisons show question codes added, removed, changed or unchanged between two authorized assessments, including prompt changes. Stable codes support comparisons; a changed prompt is not treated as the same question merely because a code matches.

Bulk remediation updates require a preview of the selected tasks and changed fields. A SHA-256 confirmation digest covers the preview state and requested changes. If a task changes before confirmation, the update returns 409 and the preview must be repeated. Cross-organization IDs, unsupported statuses and invalid dates are rejected; status completion still respects prerequisites.


## App integration setup and lifecycle

App integrations provides adapters for Intune, Defender, Notion, Jira Cloud, Zendesk, GitHub, Tenable, Slack, Teams via Graph and Amazon SES. Saving credentials leaves a connection disabled and not tested. The owner must test authentication and then explicitly enable it. A successful test does not certify every optional provider permission. Unavailable credentials, missing consent, provider restrictions and failed tests are displayed instead of being labeled connected.

Credentials are encrypted with the installation security key. Configuration reads return field names and a credentials-saved flag, not secret values. Provider origins are fixed in code; tenant/subdomain/repository identifiers are validated. Pagination redirects cannot move Graph requests to another origin. External provider response bodies and authorization headers are not logged as error messages.

Inbound synchronization stages up to ten pages / 1000 records per pull. A bounded result indicates more_available rather than claiming a full account sync. The owner reviews staged source data, the source hash and the typed destination mapping before promotion. Promotion is idempotent for an unchanged source item; an updated source requires another review. No imported response is marked independently verified.

Publishing an issue/page or sending a notification requires explicit confirmation of the destination and content. This is an external action. Read-only pulls may retry with backoff; outbound outcomes that are uncertain require manual provider verification before a repeated attempt. A configured integration is not permission to send arbitrary messages to people.

Intune and Defender use Graph application credentials and require appropriate tenant admin consent. Notion needs an integration token and a shared data source. Jira Cloud uses a selected project, an account email and API token. Zendesk uses the selected subdomain and agent token. GitHub uses a fine-grained token restricted to one repository. Tenable imports are staged from the scoped account. The exact endpoint and required fields are listed on each adapter card.

Slack requires a bot token authorized for the selected channel. Teams app-only message permissions can be restricted by Microsoft; a successful tenant token alone is insufficient to prove channel publishing permission. SES needs a verified sender identity, runtime SendEmail permission and compliance with sandbox/production recipient rules. No external provider credentials are created, guessed or copied from the assistant’s connected apps.


## Reports, editions and scheduled delivery

Choose an executive, board, audit, technical or client template, period and commentary. Templates select supported sections; period filters retain the existing distinction between the current summary and dated record/snapshot history. Empty periods are shown as empty, not filled with invented history.

Freezing a report stores the exact generated bytes, SHA-256 hash, selected source data, generation actor and branding manifest including the logo hash. Frozen editions are append-only. Changing live records or branding later does not rewrite an issued edition. A PDF preview opens the actual frozen bytes in a new tab, so the preview and download are the same edition.

PDF and Excel reports use the shared organization identity. PowerPoint exports are editable 16:9 slide decks with logo, section summaries, commentary and page labels. Program Owner - Matthew Harris remains on report footers independently of the organization’s branding. Exported files are plaintext business artifacts; protect them after download.

Scheduled reports must be explicitly active, delivery-enabled and have an approved recipient list. The scheduler deduplicates a daily/weekly/monthly bucket and creates a background job. SES delivers a sign-in-protected link to the frozen edition, not an anonymous public artifact. Recipients must still have organization access. Demo organizations never send scheduled external reports.

Variance explanations compare two actual daily snapshots and show supporting recorded activity. The app does not claim that coincident activity proves causation. Before two snapshots exist, it reports insufficient history. Owners can add management commentary for interpretation.


## Auditor workspace, archival and portfolio

An owner can create an expiring one-use audit-room invitation containing 1–100 selected program records, legacy records, evidence artifacts or frozen editions. The room is not an organization membership and does not provide internal navigation, integration credentials or unrestricted evidence access. Copy and share the fragment-based link through your approved channel.

An invited auditor session lasts at most eight hours and cannot outlive the room. Revoking the room blocks already redeemed sessions. Only selected evidence and editions can be downloaded; other IDs are rejected. External questions are appended to the room with an invited-auditor label. Possession of a bearer invitation is not independent proof of the auditor’s legal identity.

Archiving places records in the organization recycle bin. Program records retain their versions and histories; supported legacy rows remain stored and are hidden by archive-aware access policies. Restore removes the archive marker. Evidence holds and retention constraints prevent archival, and approved records must be closed before archival. The application does not expose a general permanent-purge button.

The portfolio dashboard enumerates only organizations the authenticated account may access and scopes each aggregation before reading records. Office hierarchies and assets remain within their parent organization. A consultant’s portfolio is not permission to access another consultant’s clients.


## AWS operations, release gates and recovery validation

The production web runtime remains private ECS Fargate behind the existing HTTPS gateway and private database network. The platform adds an encrypted secret for MFA/integration wrapping and a private versioned GuardDuty scan bucket. The runtime does not have permission to set clean scan tags. SQL migrations remain an explicitly privileged, additive task; the normal application role cannot change schema or policies.

Deploy the database migration image and verify exit 0 before updating the application image. The migration adds platform tables, immutable-history triggers and organization row-level policies; it does not replace customer records or owner credentials. Roll back the web image rather than deleting new tables. Backups and an approved migration rollback plan are required before production changes.

Release checks include backend tests against isolated PostgreSQL, organization and role isolation, token expiry/revocation, state transitions, file quarantine verdicts, provider request mocks, browser workflows, mobile layout and automated accessibility checks. Automated accessibility testing is evidence of specific checks, not a substitute for manual assistive-technology review or a blanket WCAG conformance claim.

Database Multi-AZ and restore execution are infrastructure states, not switches that a page can honestly claim are active merely because a button exists. Operational documentation records the validated AWS state. A restore check must identify an isolated restored resource, actual validation execution, timestamps and observed result. RTO/RPO objectives are separate from measured restore outcomes.

Operational alarms need configured destinations and confirmed subscriptions. Credential rotation must retain compatible key versions or re-encrypt ciphertext. Integration tokens have bounded lifetimes; revoked sessions and memberships are checked on each request. Failed background jobs remain visible in the job list; inspect provider consent, network access, quotas and verified sender state before retrying.


## API, schema and troubleshooting

Cookie-authenticated writes require X-CSRF-Token. Integration API requests use Authorization: Bearer <one-time-issued-token>, scoped to /api/v1/{organization}/records/{module}. The API token cannot call account, role, audit-room or integration-management routes. The actor is the enabled issuing account and every token has its own organization, scopes and expiration.

Typed record writes use {title, owner, due_on, data}; updates also require id and version. A read returns the current record and version. Unknown module fields, invalid dates, cross-organization references, reference cycles and unsupported state transitions return 422/403/409 as appropriate. Do not retry a 409 by discarding the user’s local edits.

Core tables: pl_records/pl_history for business versions; pl_integrations/pl_external/pl_jobs for connections, staging and execution; pl_mfa/pl_recovery/pl_session_meta/pl_oidc for security; pl_catalogs/pl_controls for imported controls; pl_editions for frozen report bytes; pl_quarantine/pl_evidence_versions for artifact custody; pl_rooms/pl_auditor_sessions for scoped external review; pl_trash for archival. Existing domain and experience tables remain the source for earlier features.

401 means authentication or an expired external invitation is required. 403 means the role, capability, CSRF token or scope does not authorize the action. 409 means a version, dependency, approval or scan gate requires reconciliation. 422 means input validation failed. 503 means a required provider or security configuration is not ready. Error responses do not include credential values or provider response bodies.

Program records, audit logs and exports can contain sensitive business data. This application does not constitute independent security assurance, a legal breach determination, a framework certification or a completed healthcare privacy assessment. Preserve the detailed activation and validation record for each feature rather than treating the feature catalog as an assurance statement.

## Provider reference

| Provider | Configuration fields | Credentials | Permission |
|---|---|---|---|
| Microsoft Intune | tenant_id, client_id | client_secret | DeviceManagementManagedDevices.Read.All |
| Microsoft Defender | tenant_id, client_id | client_secret | SecurityIncident.Read.All |
| Notion | data_source_id, title_property | token | Read selected shared data source; write only on explicit publish |
| Jira Cloud | subdomain, email, project | api_token | Read/create issues in the selected project |
| Zendesk | subdomain, email | api_token | Read/create tickets accessible to the scoped agent |
| GitHub | owner, repository | token | Fine-grained issues read/write for one repository |
| Tenable Vulnerability Management |  | access_key, secret_key | Vulnerability read in your Tenable account |
| Slack | channel | bot_token | chat:write to the approved channel |
| Microsoft Teams via Graph | tenant_id, client_id, team_id, channel_id | client_secret | Approved Graph channel message permission; provider consent may restrict app-only sends |
| Amazon SES | region, sender | Runtime IAM | Runtime IAM ses:SendEmail; verified identity and production/sandbox recipient rules |

## Deployment and rollback

1. Validate templates with cfn-lint and inspect change sets.
2. Create scanner and generated secrets. Never retrieve plaintext secret values into an operator transcript.
3. Stage runtime permissions and new database secret injection with EnablePlatform=false.
4. Build a pinned GitHub commit through isolated PostgreSQL tests, static analysis, dependency audit, browser and accessibility checks, and a non-root container smoke test.
5. Execute the new image as a privileged migration task using ECS secret injection. Verify exit 0.
6. Update ImageTag and EnablePlatform=true. Require two healthy tasks and stable readiness. Retain the old image and explicit legacy role for rollback. Do not delete additive tables on rollback.
7. Deploy native alarms and the isolated restore executor. Test an actual clone and verify cleanup. Confirm alarm destination subscriptions with authorized contacts.

Foundation stack policy permits only PostgreSQL Update:Modify. Replacement and deletion are denied; other foundation changes need deliberate policy revision. Runtime and platform stacks are separate.

## IAM derivation

IAM Policy Autopilot 0.4.0 analyzed the runtime and restore SDK calls. Optional broad actions were reduced to the operations actually used. Runtime can upload only under the scanner uploads prefix and read version-specific scan tags; it cannot write verdict tags or read secret values. The restore executor uses a separate role with a bounded clone prefix, tagged-clone deletion, one verifier task, and two exact passable roles.

## Validation boundaries

Provider mocks validate request construction and error handling, not actual tenant consent or a successful customer sync. Automated accessibility checks do not establish full WCAG conformance. Restore verification checks restored schema and aggregate record counts; it does not measure a full customer recovery exercise.

## Current release and infrastructure inputs

See [PLATFORM_VALIDATION.md](PLATFORM_VALIDATION.md) for the deployed image, exact acceptance build, live checks, restore result, compatibility correction and activation requirements.

The runtime template takes `SourceCommit` as an exact GitHub SHA and builds through `infra/experience-buildspec.yml`. Choose a new immutable image tag for each release and publish the tested image before updating the service. Inspect the change set and preserve the database migration/rollback ordering above. Updating `SourceCommit` changes the default builder source; it does not by itself publish or deploy an image.

The operations template additionally takes the source database's subnet-group, option-group and parameter-group names. These are infrastructure metadata returned by DescribeDBInstances, not passwords. Restore authorization is limited to those exact groups plus the source database and the `studio-restore-*` target prefix. Keep the verifier task ARN current when a runtime task-definition replacement occurs. Run a real restore after changing executor permissions. The monthly rule is enabled only after the first verified execution; cron is the first day of the month at 04:00 UTC.

Program Owner - Matthew Harris attribution remains independent of customer branding on the application, documentation and generated reports. Application settings cannot change it; source and deployment administrators retain control of the software.


## AI governance and application-only image releases — 1 November 2026

The original Cybersecurity Operations Hub AI Governance reference is available under Governance → AI Governance → Source reference. The eleven operating registers and configuration-bound independent release workflow are described in [AI_GOVERNANCE_IMPLEMENTATION.md](AI_GOVERNANCE_IMPLEMENTATION.md). This uses the 28 October 2026 export; it does not activate live Notion synchronization or treat illustrative cases as actual approvals.

For releases that need no database migration, set the optional `ApplicationImageTag` to the tested immutable application image and update `SourceCommit`. The default builder uses that same application image target. Keep `ImageTag` unchanged to preserve the accepted migration and restore-verifier task definitions and their scheduled references. An empty `ApplicationImageTag` retains the legacy shared-tag behavior. For an actual schema/restore change, plan and validate those image and reference changes explicitly rather than treating an application-only release as migration authorization.
