# Studio interface refresh — 31 October 2026

The existing owner-authenticated application now uses a consistent navy and teal interface across its dashboard, navigation, records, forms, and management report downloads.

- Executive overview: risk heatmap, open remediation aging, items needing attention, six-month risk record creation activity, and vendor review coverage.
- Navigation: grouped sections, consistent SVG icons, collapse preference, keyboard focus and a skip link.
- Records: combined search/status filtering, numeric sorting, pagination, column selection, compact density, and explicitly saved browser view preferences.
- Forms: labeled groups, related-record dropdowns, score bounds, framework/control selectors, contextual help, pending states, and inline save errors.
- Details: readable fields and narrative sections, related review/decision history, assessment answers, and evidence download links.
- Frameworks: enabled/scoped cards, tracked-item progress, owner and target dates. Verified-item progress excludes not-applicable tracked items and does not represent full framework compliance.
- Feedback: loading placeholders, actionable empty states, save notifications, responsive layouts, and reduced-motion support.
- Downloads: shared report colors, PDF page headers/footers, banded tables, Excel print settings and summary bar charts. Existing disclosures and formula-injection protections remain.

Charts use stored management records. Monthly risk activity counts creation dates; it is not a historical exposure trend. Saved view preferences stay in the browser and contain presentation settings, not passwords or session tokens.

## Validation

Four Node tests cover filter/sort behavior, scoped progress, date aging, and calendar-month counts. An isolated synthetic DOM integration check covered the dashboard, table search, form constraints, framework progress, and report links, and the merged third-party questionnaire template selector. Local Python regression: 47 passed, six PostgreSQL tests deferred to CodeBuild. Synthetic executive and board PDF pages were rendered and inspected; workbook schemas and formula-safety regression checks passed.

AWS CodeBuild `cyber-ops-online-studio-web:68f69a0f-08e8-42f1-8cc3-55233b8e27e2` passed all 53 backend tests (including PostgreSQL and the merged questionnaire tests), all four Node tests, and the read-only non-root container smoke test. ECR scan completed with no findings for `cosmetic-20261031-v2` (`sha256:ccefba969bcb7caecf6eea806faa94068a6616425a64f7c9e3d0d2968b3daa6a`). Two healthy running tasks use `cyber-ops-online-studio-web:5`; both ALB targets are healthy. Public health and readiness endpoints return HTTP 200, with the database connected. Live JavaScript, helper script, and CSS bytes match the tested build; the live sign-in page was visually inspected. The existing owner is configured; authenticated live browser acceptance requires that owner's session. No owner credentials were retrieved, and no production demo mode or authentication bypass was added.
