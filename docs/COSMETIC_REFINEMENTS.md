# Interface refinements: ten requested improvements

Program Owner - Matthew Harris

Date: November 1, 2026 (America/Chicago). Status: published and deployed; see the production verification record below.

| Request | Implementation | Location |
|---|---|---|
| Simplify secondary navigation | Four categories with a Section selector instead of a wrapping wall of tabs; Overview remains directly accessible | Operations workbench |
| Increase mobile text | Mobile labels, notes and badges at least 12 px on affected surfaces, 14 px inputs, 44 px minimum controls and readable header attribution | Shared presentation stylesheet |
| Replace technical inventory forms | CSV chooser, explicit column mapping, ten-row preview and import confirmation | Campaign record → Import account inventory |
| Improve record detail presentation | Labeled sections, related record names/links, expanded business values and collapsed technical JSON | Program and Operations records |
| Strengthen action hierarchy | Primary create/edit/report actions, secondary follow-ups and a separate More actions disclosure for archive | Record drawers and module pages |
| Improve dashboard cards | Shared heights, aligned metrics, consistent icon sizes and supporting text; explicit outcome labels | Dashboard and Operations overview |
| Helpful empty states | Module-specific create guidance and viewer-aware presentation; neutral empty states for summary tables | Register and table views |
| Standardize tables | Consistent padding and labels, numeric alignment, readable dates/status badges, wrapped long names and focusable horizontal scrolling | Platform tables |
| Polish forms/dialogs | Basics, Scope & implementation, Ownership & review, Evidence & validation sections; consistent Save changes/Cancel bar and required indicators | Platform forms |
| Refine branding placement | Organization identity and logo lead the header; protected owner attribution remains in header and footer | Workspace header/footer |

## Navigation mapping

Assurance: validation/evidence, business impact, vulnerabilities, owner-only integration health, and Assurance & productivity.

Governance: access reviews, exceptions/changes, data governance, workflow rules, customer/auditor portal and automation history.

Resilience: acquisitions and recovery exercises.

Planning: investment scenarios and PQC readiness.

Desktop navigation uses keyboard-accessible category buttons with active-state labels and a Section dropdown. Mobile navigation uses compact Area and Section selectors to keep content closer to the top of the screen. Existing module keys and API routes remain unchanged. Category selection does not grant access to a page or record.

## CSV import runbook

1. Open Governance → Access reviews and select the campaign.
2. Choose Import account inventory, then select a UTF-8 CSV file up to 2 MiB with a header and 1–1,000 rows.
3. Map Account and System. Optionally map Privileged access and Last use. Each source column can be mapped only once.
4. Review the displayed count and first ten rows. An unmapped privileged field defaults to No; an unmapped last-use field is omitted and stays unknown. Map privileged data explicitly whenever available.
5. Select Import reviewed accounts. The existing server endpoint receives the campaign version and typed account objects. Stale versions and unauthorized reviewers still fail server-side. Repeated account/system pairs are skipped by the server rather than overwriting decisions.

```csv
Account,System,Privileged,Last seen
synthetic.user,Synthetic directory,false,2026-10-01
synthetic.admin,Synthetic application,true,2026-10-15
```

Privileged values: true/false, yes/no or 1/0, case-insensitive. Last-use dates: valid YYYY-MM-DD, with impossible calendar dates rejected. Required account/system values contain 1–140 characters in this wizard so generated record titles fit the existing server title limit.

The parser supports UTF-8 BOMs, CRLF/LF, quoted commas, escaped quotes and embedded newlines in quoted fields. It rejects unclosed quotes, unexpected text after a quoted value, ragged rows, duplicate/empty headers, excessive column counts and files/row counts beyond the limit. Empty lines are ignored. Source cells become text nodes and typed request values; they are never evaluated as HTML, SQL or JavaScript. No uploaded file is sent to an external provider by this wizard.

## Architecture and data boundaries

`polish-core.js` contains pure CSV parsing and account preview validation. `polish.js` supplies shared table/form/record presentation and the import wizard. `polish.css` follows existing appearance tokens and dark/light colors. These are loaded after Operations and existing application components. `platform.js` delegates record-field rendering when the presentation helper is available and separates archive actions; `operations.js` delegates grouped navigation when available. Existing API shapes, schema, ownership fields, permissions, evidence gates and record histories remain authoritative.

Related platform records open their scoped record details. Legacy risk/vendor/task/evidence references resolve through their existing authorized source register. Missing references show an unavailable state rather than a fabricated title. Technical IDs and original field values remain in a collapsed Technical details section for troubleshooting.

Dialogs retain native modal/focus behavior. Labels remain associated with controls, required fields retain native validation, save controls disable during submission, and errors stay visible in a role=alert region. Failed saves/imports keep the dialog open. File selection is asynchronous and invalidates the prior preview; stale file-read completions cannot enable an import for a newer selection. No control bypasses independent review or capability checks.

Branding presentation uses existing organization settings and logo routes. It neither changes the fixed Program Owner - Matthew Harris text nor permits its removal through branding settings. Customer branding is not treated as software ownership.

## Verification

Pure Node tests cover quoted CSV data, BOM/CRLF/newlines, malformed input, mapping ambiguity, explicit boolean/date parsing, resource limits and literal SQL/HTML-shaped values. Browser acceptance uses the real application files with synthetic API fixtures, covers each navigation category and register, mapping/preview/import submission, record sections, technical disclosure, separated archive action, mobile font sizes, overflow and automated WCAG serious/critical checks. Existing appearance lifecycle and calculation tests remain release gates. Browser fixtures are separate from backend authorization tests; the merged release passed the full 128-test backend suite.

Release identifiers and outcomes are recorded below.


## Historical local candidate validation record

Verified UTC: 2026-11-01T21:21:54.937901+00:00

Verified America/Chicago: 2026-11-01T15:21:54.937901-06:00

All ten requested refinements are implemented in the local candidate. Thirteen JavaScript tests passed (including six CSV boundary/mapping tests), two backend/static-catalogue smoke tests passed without skips, full-web Bandit completed without medium/high findings, and the dependency audit reported no known vulnerabilities. The application and appearance browser suites passed locally with synthetic API fixtures. The browser run covers both light/dark Operations views, populated pass/fail/unknown rows, CSV mapping/preview/import, module forms, record details and mobile layouts. Automated serious/critical accessibility gates passed in the exercised views. This is bounded automated/visual QA, not a claim of exhaustive accessibility conformance.

Desktop, mobile and import screenshots were visually inspected for internal QA only. Review corrected a responsive sidebar overlap and light-theme record-link/status contrast. Existing owner attribution remains in the DOM and visible header/footer. Browser tests can use an explicitly configured STUDIO_CHROMIUM_PATH in constrained development environments; normal CI continues to use its installed Playwright browser.

The attempted private AWS validation build was rejected by automatic approval review before execution because the build would transfer the source patch to CodeBuild. No alternative AWS upload was attempted. Local browser validation completed instead. No GitHub push, registry upload, production deployment or production database change was performed. The earlier public-publication approval block remains unresolved.

The preceding operations backend's 116-test acceptance record remains historical evidence. This cosmetic release did not rerun the entire database suite; its new behavior is in the browser CSV wizard and presentation components, and the existing server-side import/authorization contract is unchanged.


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
