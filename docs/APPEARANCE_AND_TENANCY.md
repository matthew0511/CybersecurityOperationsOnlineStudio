# Appearance and team architecture

Program Owner - Matthew Harris

Implementation review: 2026-11-01T13:23:32Z (07:23:32 America/Chicago).

## Appearance

Choose **Theme** in the workspace header, or **Appearance** on sign-in, documentation, password recovery, invitations and scoped audit pages. Light and Dark use an explicit choice; System follows the device preference, including changes while the page is open. The browser remembers the choice and synchronizes it between tabs. The workspace also saves its existing per-user, per-organization preference. A browser that blocks local storage still permits switching for the current page. Printing documentation uses paper colors independently of the screen theme.

`appearance.js` executes from the same origin before styles load, applying the preference before the first paint. It validates stored values and handles denied storage access without interrupting login. `appearance.css` supplies consistent dark surfaces for authentication, standalone pages, dialogs, menus, status indicators, forms and documentation. It does not recolor client logos or issued reports. Workspace branding and Program Owner attribution remain independent of appearance.

## Team and tenant model

The service uses a shared application and PostgreSQL database. An organization is the tenant boundary; it is not a dedicated database, schema, container or AWS account. `xp_memberships` assigns editor, reviewer or viewer access to specific organizations. The installation owner is a privileged platform administrator with access across organizations; there is no separate self-service tenant-administrator role.

Use **+ Organization**, choose the organization, then open **Workspace hub → Team & invitations**. Create a scoped invitation and choose the member's role. Existing accounts receive memberships without resetting their passwords. Ordinary users see only authorized organizations in the selector and portfolio. Changing or removing membership affects subsequent requests. Invitations and external audit rooms are bounded, revocable access mechanisms; an audit-room link does not grant general organization membership.

Server authorization checks organization membership, role and capability restrictions. PostgreSQL row-level policies provide an additional organization boundary for customer records. The normal runtime role is not a superuser and has no BYPASSRLS or schema-management privileges. Tests exercise fail-closed unscoped reads, permitted reads, rejected cross-organization writes, role restrictions and portfolio scoping. Identity lookup tables and the documented legacy rollback role have separate treatment; see PLATFORM_GUIDE.md and PLATFORM_VALIDATION.md.

This is owner-managed, shared-database multi-tenancy. It does not establish independent customer infrastructure, per-tenant encryption keys, a customer identity directory, self-service signup, subscription billing or tenant-specific backup restoration. Installation/deployment administrators remain trusted. Independent security and privacy review is still required before introducing PHI.

## Validation

`tests/appearance.test.cjs` checks saved/system preferences, invalid values, blocked storage, operating-system changes and tab synchronization. `tests/appearance-ui.cjs` uses real HTML/CSS/JavaScript for five page entry points in Light and Dark at desktop and mobile widths, plus reload, System and storage behavior. The existing workflow browser acceptance checks workspace navigation, questionnaires, branding, security and automated accessibility. Deployment must wait for the full build gates, including isolated PostgreSQL tests and hardened-container smoke testing.


## Release evidence and pending maintenance

- Application commit: `7ec9826c35d8ad0a80f584070aaa8d43104f2ae1`.
- Image: `appearance-20261101-v1`; digest `sha256:729fde1ef537fa4a8a66b28beb1110e4e9415362df57920ddbf8dd60a27e029e`.
- CodeBuild: `cyber-ops-online-studio-web:2134c3fe-44f4-4451-b9df-c7bea52573c2`, SUCCEEDED. 83 backend tests (one existing test-client deprecation warning), seven interface logic tests, appearance and workflow browser suites, automated accessibility, dependency audit, static analysis and the hardened non-root/read-only container smoke test passed. ECR scan completed without reported findings.
- ECS deployment completed at `2026-11-01T13:32:46Z` (07:32:46 America/Chicago). Runtime task revision: `cyber-ops-online-studio-web:12`; desired/running count: two. CloudFormation runtime stack reached UPDATE_COMPLETE. All seven Studio alarms were OK.
- Public HTTPS checks confirmed database readiness and byte-for-byte equality with the tested sign-in, documentation, account-recovery, audit-room, invitation (`/join` and `/portal`) and shared appearance assets. Authenticated workflow acceptance used synthetic fixtures; operator checks did not use owner credentials.
- The runtime replacement retired restore verifier revision `:3`; revision `:4` is ACTIVE. The operations stack still references `:3`. The web application is healthy, but the scheduled restore check needs this reference repaired before it can run successfully. Automated database backups are separate from this check.
- Automatic approval review rejected executing the initial secondary operations update because it changed the restore project, permissions and schedule outside the appearance request. A narrower prepared change set, `restore-active-revision-only-20261101`, changes only the `RestoreTaskArn` parameter to revision `:4`; it preserves the source commit and schedule expression/state. CloudFormation also lists dependent project, role and schedule-target reevaluations. This plan passed pre-deployment validation but has not been executed; explicit approval is needed. No new restore exercise was run in this appearance release.


## Subsequent security release

The November 1 security release preserves these appearance assets and tests. It repaired the operations restore-task reference to active revision 5, superseding the pending revision 3/4 maintenance note above. The source commit and monthly schedule were preserved. See [security validation and remediation](SECURITY_VALIDATION_2026-11-01.md) for the deployment and policy-verification evidence.
