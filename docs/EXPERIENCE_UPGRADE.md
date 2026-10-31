# Experience and collaboration release

This release implements the twenty requested experience improvements in the existing AWS browser application. It adds PostgreSQL tables without replacing existing organizations, records, questions, responses, or the owner's password.

| # | Capability | Entry point / behavior |
|---|---|---|
|1|Questionnaire sections|Assessments: ten collapsible sections with applicable response counts.|
|2|Autosave and resume|Responses save after a short typing pause or blur, with save state, optimistic version checks, and last questionnaire/question preferences. Unsaved response navigation is confirmed.|
|3|Conditional follow-ups|Follow-ups hide only after an explicit No, N/A, or Not applicable parent response. Show skipped questions reveals all items. Existing hidden answers are retained.|
|4|Question-level evidence|Link existing evidence or upload a new artifact alongside each question. External respondents can upload but cannot download internal evidence.|
|5|Vendor-linked assessment|Assign the vendor, authenticated reviewer, and due date. Vendor relationship view includes assessments and dated review history.|
|6|Completion review|Shows unanswered applicable items, missing evidence, evidence awaiting review, reviewer notes, and submitted/approved/needs-changes states. Evidence is advisory; narrative completion is required for submission.|
|7|Vendor response portal|Owner creates an expiring, one-use invitation. A restricted HttpOnly vendor session exposes one assessment's prompts and answers. It never grants internal workspace access.|
|8|Action center|Workspace hub → Actions: tasks, vendor follow-up, evidence freshness, assessment reviews, audit findings and pending change decisions; filter assigned to me.|
|9|Relationships|Record details → Relationships & discussion connects vendors, assessments, risks, tasks, evidence, findings, initiatives and changes within the organization.|
|10|Reminders|Organization settings configure daily/weekly in-app notices, lead days and overdue escalation to owner. A background worker checks each minute with a database advisory lock and deduplicates delivery.|
|11|Dashboard customization|Toggle dashboard widgets and move visible widgets up/down. Preferences are persisted per authenticated user and organization.|
|12|Historical trends|Background service captures one immutable daily snapshot per active organization. Trends shows exposure, risk/task counts and scoped verified controls. No history before activation is invented.|
|13|Board report builder|Workspace hub → Report builder: select sections, record dates, commentary, preview, and branded PDF/XLSX exports. Current summary is labeled separately from period-filtered records.|
|14|Kanban / dependency timeline|Workspace hub → Work board: drag cards or use accessible status dropdowns; chronological schedule and prerequisites; cycle detection and completion gates apply to legacy APIs too.|
|15|Branding|Owner configures organization brand name, accent, logo and report footer. Validated PNG/JPEG logos are limited to 200 KB and 2000×2000 pixels.|
|16|Themes|Light, dark and system preference; persisted per user/organization with immediate local application.|
|17|Search / shortcuts|Header search or Ctrl/Cmd K searches display titles within the current authorized organization and offers quick actions.|
|18|Onboarding|Workspace hub → Onboarding displays organization, vendor, answered assessment and published snapshot milestones. Dashboard prompt can be dismissed.|
|19|Form feedback|Visible save states, preserved failed response input, conflict explanations, native field validation, invalid-field highlighting and confirmation before discarding action forms.|
|20|Collaboration|Organization roles, assignments, immutable authenticated comments, @username in-app mentions, and assigned-to-me queues. Owner manages access.|

## Roles and access

The existing owner remains the installation owner and retains access to all organizations. Team users receive only explicitly assigned organizations. The first existing account is promoted only if no owner already exists, and initial setup explicitly creates an owner.

- Owner: all organization records, settings, branding, team membership and invitation management.
- Editor: organization records and workflows; no access-management or organization-branding privileges.
- Reviewer: responses, questionnaire review when assigned, evidence linking/review, vendor reviews and findings. The reviewer cannot create invitations, change memberships or edit organization settings.
- Viewer: read and export authorized organization records, plus personal preferences and notification read state.

The role checks protect the original service API, uploads, evidence downloads and exports as well as the new endpoints. Client-side hiding is only a convenience. Reviewer-name fields in older workflows remain operator-entered; new comments and questionnaire reviews separately record the authenticated actor. This release adds neither MFA nor SSO.

Team invitations let a new user choose their own password. Existing accounts cannot have passwords reset by redeeming an invitation; grant those accounts organization membership through the owner interface/API instead. Removing membership immediately removes organization access even when a login session still exists.

Vendor invitation links use a URL fragment, not a query string. Only a hash is stored in the database. Links can be redeemed once, expire after 1–30 days, and can be revoked. A redeemed vendor session lasts at most eight hours and never outlives the invitation; after session expiry, the owner issues a new invitation. Revocation also blocks existing vendor sessions. Copy and share links through your chosen secure channel; the application does not send invitation email.

## Response and review semantics

All sixty source questions remain in their original sequence. Multiline narratives remain in the existing rationale field, with Unknown meaning unscored and Unanswered meaning blank. The conditional rules do not turn a vendor's statement into independently verified control compliance. Evidence remains pending until reviewed. Submitted and approved questionnaires are locked until an assigned reviewer or owner reopens them. Version mismatch returns HTTP 409 and retains the local edit for manual reconciliation.

Reminder notices and mentions are delivered in the application. No email/SMS provider is configured or contacted. Free-text task owners that do not match an authorized username route to the installation owner. Repeated checks in the same daily/weekly bucket do not duplicate reminders. Service startup failures in the scheduled pass are logged and retried next minute. Historical snapshots are immutable per day; current dashboard counters remain live.

## Operations and migration

The schema is in `web/experience.py`, applied by the existing privileged database migration task. Deploy the new migration image and verify exit 0 before rolling out the new web image. The migration grants the runtime database role access to the new tables and sequences using the existing grants. The previous web image remains compatible with the additive tables while the new deployment is gated. Do not roll back by deleting the new tables or modifying immutable audit history.

No external invitation emails, team accounts, vendors, or customer records are created automatically. The owner creates memberships and invitations through Workspace hub. Background daily snapshots and due-date notifications begin after deployment.

Tests cover role isolation across old and new endpoints, vendor token scope/CSRF/one-use/expiry/revocation, response conflicts and conditional completion, review locking, evidence scope, mentions, dependency cycles and completion guards, migration idempotence, report formats, logo validation and reminder/snapshot deduplication. Production owner credentials are not used by the test suite.
