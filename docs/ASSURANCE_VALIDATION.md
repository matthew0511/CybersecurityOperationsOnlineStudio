# Assurance and productivity: release validation and deployment evidence

Program Owner - Matthew Harris  
Recorded: November 1, 2026, 15:28 CST (America/Chicago, UTC−06:00)  
Runtime source: `6a89522c234b315a21912650e7016c7e0b7e9a26`  
Backend regression source: `d6c7f212aa97d02131669327e4ec24aac76e4546`

## Accepted results

| Validation | Observed result | Evidence |
|---|---|---|
| PostgreSQL backend/security regression | 128 passed; one non-failing TestClient deprecation warning; 137.35 seconds | CodeBuild `cyber-ops-online-studio-web:9f2d71e0-0ed7-4ccf-b81f-66bf4956ca84`, backend command completed 2026-11-01 21:18:19 UTC |
| Final-source difference | Only `static/assurance.js` changed after backend acceptance: two explicit accessible selector names | GitHub comparison `d6c7f212...6a89522c` |
| Interface calculations and appearance unit checks | Seven passed | Final CodeBuild execution below |
| Browser appearance | Passed: five entry pages, light/dark/system, reload, OS changes, tabs, blocked storage, mobile | `APPEARANCE_BROWSER_ACCEPTANCE_PASSED` |
| Browser workflow acceptance | Passed: existing application workflows plus every assurance secondary page and all nine new typed-register forms | `EXPERIENCE_BROWSER_ACCEPTANCE_PASSED`; real HTML/JS/CSS with intercepted synthetic API responses |
| Mobile and automated accessibility | No horizontal overflow in tested mobile views; no serious/critical violations in configured WCAG tag checks | Extended `tests/experience-ui.cjs`; not a blanket accessibility certification |
| Static security and dependency audit | Bandit passed; dependency audit found no known vulnerabilities at execution time | Final CodeBuild pre-build commands |
| Infrastructure lint | Existing platform runtime template passed | Final CodeBuild pre-build command |
| Runtime container | Image built/pushed; read-only, non-root, dropped-capability database connection and temporary-volume smoke test passed | Final CodeBuild build commands |
| ECR image scan | COMPLETE; empty severity-count map | DescribeImageScanFindings, observed 2026-11-01 21:25:40 UTC |
| ECS rollout | COMPLETED; desired 2, running 2, pending 0, failed tasks 0 | DescribeServices, observed 2026-11-01 21:28:22.417168 UTC / 15:28:22.417168 CST |
| Load balancer | Both targets healthy | DescribeTargetHealth at the final service observation |
| Public page | HTTPS login page loaded and document references both `/static/operations.js` and `/static/assurance.js` | Read-only browser inspection of `https://cybersecurityoperationstudio.com/` after deployment |

## Final build and runtime identifiers

- Final CodeBuild execution: `cyber-ops-online-studio-web:91895f7e-a1e3-4955-9a50-8b35f67ce087`.
- Final build status: SUCCEEDED. Build/image push completed 2026-11-01 21:23:58 UTC / 15:23:58 CST.
- Runtime source commit: `6a89522c234b315a21912650e7016c7e0b7e9a26`.
- ECR tag: `assurance-20261101-v4`.
- Pinned runtime digest: `sha256:34975849f8a1990689e556b3976101f4e53d035ccaa631d19c085723248795e2`.
- ECS cluster: `cyber-ops-online-studio-dev` in `us-east-2`.
- Application service: `cyber-ops-online-studio-web`.
- Accepted task definition: `cyber-ops-online-studio-web:15`.
- Prior task definition / image rollback target: `cyber-ops-online-studio-web:14`.
- Deployment ID: `ecs-svc/1037177747294172878`.
- Existing rolling strategy, 100% minimum healthy / 200% maximum and automatic rollback circuit breaker were retained.
- Task networking, roles, secret references, read-only filesystem and container security settings were retained. No schema migration was required.

The final build used an invocation-only buildspec override to omit the unchanged backend suite. The complete 128-test suite had already passed on the exact same backend source; GitHub verified that the only subsequent source difference was the selector-label correction. The final build reran browser acceptance, accessibility, static/dependency checks, interface calculations and container smoke validation. This distinction avoids describing the earlier browser-failing build as globally successful.

## Validation coverage and practical limits

Backend acceptance covers organization separation, role/capability restrictions, unknown/stale coverage, evidence requirements, release/reuse gates, literal SQL input and fixed-sort validation, bulk preview/version conflicts, framework edition comparison and conservative mapping migration, package format/hash/conflict handling, archived-record recovery, non-demo reset refusal, notification acknowledgment/retry and escalation deduplication. Existing deterministic fuzz, SQL and AI-governance security tests remain in the full suite.

A first acceptance candidate contained an incorrect test expectation that clean data must produce a quality finding. The corrected test checks both an empty quality result for valid data and duplicate-title detection. Browser acceptance then identified the missing explicit accessible selector name; this was corrected before release.

Browser acceptance uses synthetic API responses separately from the real PostgreSQL-backed backend tests. The production browser observation was read-only and unauthenticated; it did not inspect customer records, sign in as the owner or execute production business changes. No customer-provider notification, external identity revocation, cryptographic migration or live disaster-recovery drill was performed.

The workbench package is scoped archival recovery, not a complete database backup. Missing database rows or evidence require the managed database recovery procedure. Service and control coverage reflect recorded inventory and observations, not universal live scanning. Provider acceptance does not prove recipient delivery. Full workflow semantics and limits are in [ASSURANCE_PRODUCTIVITY.md](ASSURANCE_PRODUCTIVITY.md).

## Ownership and maintenance

Matthew Harris remains the program owner and release sponsor. Technical maintainers must retain these source/build/image identifiers when investigating this release. Future documentation-only commits are not automatically deployed application revisions. Keep release validation, deployed image and current repository HEAD separate in operational reports.
