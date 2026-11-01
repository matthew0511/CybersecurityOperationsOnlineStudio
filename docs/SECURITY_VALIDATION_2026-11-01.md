# Cyber Security Operations Online Studio Security Validation

Program Owner - Matthew Harris

## Purpose and review boundary

This assessment records secure coding review, bounded fuzzing, SQL injection tests, confirmed fixes, regression results and AWS hardening performed November 1, 2026. Timestamps use UTC and America/Chicago with offsets where shown. The user authorized assessment, remediation and retesting of the owned application and AWS setup.

All destructive/resetting and authenticated exploit-corpus tests use the disposable PostgreSQL database studio_test inside isolated CodeBuild or GitHub runners. The fixture refuses to drop schemas in any other database. No production owner password or secret value was retrieved. Synthetic test passwords in source and logs belong to disposable fixtures, not the live database. Production verification is restricted to readiness, public resources, authentication requirements and input-boundary rejection before login logic.

The assessment is evidence of the stated code paths and configurations. It does not establish that all vulnerabilities are absent or replace an independent penetration test. The retained desktop code participates in regression tests; the primary target is the deployed online runtime.

## Confirmed findings and remediation

| Finding | Impact and preconditions | Reproduction | Resolution |
|---|---|---|---|
| SEC001 Request framing and body limits | Malformed Content-Length caused an unauthenticated 500; header-only length checks did not enforce the body cap uniformly | Baseline public-boundary regression failed on Content-Length=invalid with 500 | Raw ASGI middleware validates framing, caps actual streamed bytes at seven MiB, checks declared versus observed length and supplies security headers on rejection |
| SEC002 Questionnaire graph amplification | An authorized ruleset editor could submit a valid small DAG whose shared paths were recursively revalidated, consuming disproportionate CPU | A 90-edge acyclic graph exceeded the two-second subprocess budget and was terminated in isolation | Linear vertex/edge traversal with indegree accounting detects cycles without enumerating paths; office/asset traversal also uses visited states and a bounded graph size |
| SEC003 Malformed typed fields | Authenticated malformed nested objects and identifiers produced unhandled server errors in report, audit-room, scope/capability, preference and record operations | Baseline typed, nested and seeded mutation tests returned multiple 500s | Explicit type checks before hash lookups, SQL binding, configuration parsing and state transitions; strict identifiers/versions; bounded offsets; structured audit-room entries and list members |
| SEC004 Token encoding errors | Non-ASCII token comparisons could raise instead of denying the request | Unicode CSRF/state regression cases added during hardening | Byte-based constant-time comparison with malformed types/encodings rejected; JSON rejects NUL and surrogate text before persistence |
| SEC005 Pipeline initialization defect | GitHub Platform validation could not reach application/security tests | Runner logs showed Docker unknown shorthand flag U from the single-quoted health command | Correct Docker option quoting, pin existing action revisions, set a job timeout and preserve full validation steps |

The new request boundary also rejects duplicate JSON members, non-finite numbers, unsupported root JSON types, excessive nesting/member counts, oversized scalar text and out-of-range integers. Invalid inputs receive bounded client errors rather than broad exception suppression. SQL and HTML-shaped strings are not indiscriminately stripped: legitimate business text remains data, and output encoding and parameter binding retain their own responsibilities.

The first full retest caught a static-response sequencing regression introduced by the initial middleware and a missing required field in a newly added export-test fixture. The middleware now passes through untouched receive streams for unconsumed requests; the fixture supplies all required fields. Neither intermediate revision was deployed.

## SQL injection and export checks

The SQL corpus includes quote/boolean, UNION, stacked-statement, comment and function-call forms. Tests exercise authentication, literal stored titles, parameterized search, unknown operation paths and cross-organization sentinels. They assert that the owner account and another organization's sentinel remain intact. Payloads that resemble SQL remain stored literals and cannot select another organization. No successful SQL injection or authentication bypass was observed in this corpus.

Reviewed dynamic identifier paths are restricted by fixed allowlists and now compose identifiers with psycopg.sql.Identifier in web record/search and schema-trigger code. Values remain separate query parameters. The legacy SQLite-to-PostgreSQL adapter operates on application-authored statements; the public operation surface remains an explicit allowlist rather than arbitrary SQL or arbitrary method access.

Spreadsheet tests export formula-shaped titles including equals, plus, minus, at-sign and whitespace-prefixed forms and assert that no exported cell has formula data type. HTML-shaped text is exported through escaped PDF paths. Existing browser workflows and accessibility checks remain release gates. This is not a complete historical repository secret scan, all-browser XSS assessment or independent DAST certification.

## Fuzzing methodology

The committed tests use a reproducible seed of 20261101. They include one thousand seeded JSON field mutations plus a typed-route matrix, nested-entry cases, numeric paging extremes, malformed headers/JSON, unknown-length oversize bodies, Unicode token/query cases, graph amplification, SQL payloads and export checks. Each case has an explicit invariant such as no 5xx, no cross-organization data, no executable spreadsheet formula or a two-second graph validation budget.

Public boundary tests can run without a database. Database fixtures install a fake scanner through test-only dependency replacement; production code contains no scanner bypass. No live customer provider tokens are used. A successful mock-provider test does not establish real tenant consent or a successful customer integration.

## AWS configuration review and changes

Verified controls include private Fargate tasks and RDS, the VPC-link to ALB to task to PostgreSQL security-group chain, encrypted Multi-AZ PostgreSQL with deletion protection and fourteen-day retention, TLS-verifying database clients, rds.force_ssl=1 in the parameter metadata, S3 public-access blocks and versioning, immutable image tags/scanning and an active management-event CloudTrail.

All four active application CloudFormation stacks now have termination protection enabled. The old failed bootstrap stack is left unchanged. This is a reversible operational safeguard against accidental stack deletion; it does not modify database rows, replace resources or prevent authorized stack updates. The runtime still uses non-root UID/GID 10001, a read-only root filesystem, dropped Linux capabilities, a writable temporary volume and Secrets Manager injection.

A log group without an explicit customer-managed KMS key is not equivalent to plaintext CloudWatch storage. The metadata distinguishes explicit key association from service encryption. Active application, API and build log groups have the recorded customer key association; inherited foundation/metrics groups have separate configuration.

## Residual boundaries and follow-up ownership

Matthew Harris remains accountable pending named technical delegates. AWS root administrative context was previously observed and is not resolved by a code patch. Define and verify a scoped administration and recovery path separately. Native SNS alarms require an authorized confirmed recipient before external alert delivery can be asserted; no subscription or message is sent by this assessment. Customer integration activation, MFA enrollment coverage, licensing/privacy review and the legacy database rollback-role retirement require separate owner-controlled evidence.

Public TLS terminates at API Gateway; the private load-balancer hops remain HTTP and database traffic uses TLS. A WAF or complete encrypted internal ingress topology was not added during this patch. Those are architectural changes requiring their own implementation and validation. The review does not claim those controls are present.

The source and deployed environment advanced during this assessment with a separate appearance release. The security branch explicitly merges that commit and preserves all appearance assets and appearance tests. The final combined source passed both release paths before deployment; the earlier security-only image was not used to overwrite newer UI work.

## Reproducibility

Run tests/test_security_fuzz.py only against a disposable studio_test database, then run the complete pytest suite, full-web Bandit checks, dependency audit, UI calculation tests, appearance browser checks, experience/browser accessibility checks and non-root read-only container smoke test. Keep the Git SHA, build ID, image digest, scan timestamp, task revision and live result together. scripts/security_smoke.py performs the limited credential-free live checks against the approved origin. A documentation commit does not itself change application image bytes.

Exact source/build/deployment identifiers, final timestamps and observed results are appended when verification completes.

## Recorded test executions

| Execution | Source | Outcome |
|---|---|---|
| Baseline CodeBuild 64a556d1-5705-4e72-8014-9bd9870f5d96 | 1402d9ae471d07790ab7f5408d121d4b4a59622d | 5 failed and 1 passed; reproduced malformed-input and graph failures |
| First correction CodeBuild 84c50b98-337f-433d-8198-476562f504a7 | bf7276d27f0e2ab1ffdac0f5a6f620738e0a8ee8 | 89 passed and 2 failed; pre-deployment response-stream and test-fixture defects corrected |
| Initial full acceptance e8b99fdb-fc77-4d18-bc2a-485102ec6287 | e4e5a29b1ffda2ecb2aff5f8f97131d2b608669a | Successful security release candidate; not deployed because newer appearance changes required reconciliation |
| Combined full acceptance 6877e0d2-8d72-4aa8-819c-94ea6527a128 | 6c637b0ea117ea311c08d32225dde4b382d7926d | SUCCEEDED; 91 backend tests, 7 UI logic tests, appearance and workflow browser checks, accessibility, full-web Bandit, dependency audit and hardened container smoke |
| GitHub Platform validation 41311899772 | 6c637b0ea117ea311c08d32225dde4b382d7926d | SUCCEEDED |

Combined CodeBuild started 2026-11-01T13:34:31.099Z and finished 2026-11-01T13:38:14.361Z. Test runs emitted one existing Starlette/httpx test-client deprecation warning. The combined image digest is sha256:b644ee634b8cd919de60cda9a473e2a49cfe2935c7180b765f424b87fd22a963. Its ECR scan completed at 2026-11-01T13:41:47Z with no reported findings before deployment.

All four active stack deletion safeguards were verified enabled at 2026-11-01T13:28:14.123007Z. These safeguards do not remove the need for protected credentials and recovery evidence.

## Final deployed result

- Accepted application source: 6c637b0ea117ea311c08d32225dde4b382d7926d.
- Main merge containing that exact application source plus appearance release documentation: a9467ce579edb178caa0735fa0ab55c83639a9d3. Direct comparison with the accepted source changed only docs/APPEARANCE_AND_TENANCY.md; deployed application bytes were preserved.
- Image: security-20261101-v2, digest sha256:b644ee634b8cd919de60cda9a473e2a49cfe2935c7180b765f424b87fd22a963.
- Runtime change set: security-hardening-20261101; execution requested at 2026-11-01T13:42:52.829263Z. The change set updated task revisions, service and build metadata, without database or network resource replacement.
- ECS task definition: cyber-ops-online-studio-web:13. Deployment completed at 2026-11-01T13:45:52.817Z (07:45:52.817 CST). At 2026-11-01T13:47:02.204627Z, desired/running counts were two, pending was zero, and both AZ targets were healthy.
- Runtime and operations stacks both reached UPDATE_COMPLETE with termination protection enabled; all four active stacks retained protection.
- Live verification build: cyber-ops-online-studio-web:e5b91c48-ca3a-4487-8fd1-f0fadf608dc8, SUCCEEDED. Checks completed at 2026-11-01T13:46:07.141721Z (07:46:07.141721 CST). Four public resources returned 200, four protected APIs returned 401, and three malformed JSON inputs returned 422. TLS certificate validation and security response headers were checked. Program Owner - Matthew Harris remained present.
- GitHub main Platform validation run 41312624472 at a9467ce579edb178caa0735fa0ab55c83639a9d3 completed successfully. Earlier failed runs remain historical evidence rather than being relabeled successful.

## Restore reference repair

The previous operations configuration pinned retired restore verifier revision 3. The security release creates active verifier revision 5. Change set security-restore-active-revision-only-20261101 changes only RestoreTaskArn to revision 5. It preserves ReleaseCommit=4a88c12c3e6e6abefea80ffd49d9b6c1e857ea95, the existing schedule expression/state and every other parameter. Dependent CodeBuild environment, role and EventBridge target reevaluations are recorded in the change set.

Execution was requested at 2026-11-01T13:45:11.967255Z. Final verification at 2026-11-01T13:47:02.204627Z found the operations stack UPDATE_COMPLETE and the restore project's RESTORE_TASK environment reference at revision 5. IAM simulation allowed ecs:RunTask on that exact verifier and returned implicitDeny for rds:DeleteDBInstance on the source database. This simulation is scoped policy evidence, not a completed restore drill. A new point-in-time restore exercise was not executed during this security patch.

## Result and remaining assurance limits

Confirmed corpus failures were corrected and retested before release. No successful SQL injection, cross-organization access or executable spreadsheet formula was observed in these tests. The live input guard was checked after rollout. Source, runtime and test-result provenance are recorded separately.

Remaining owner actions include establishing a scoped AWS administration path and a confirmed authorized external alarm recipient. No account-wide administrator identity migration, regulatory/privacy assessment, third-party tenant activation, complete historical secret scan, internal-hop TLS redesign, WAF deployment or independent penetration test is claimed. Further tests should extend coverage as modules, adapters and data flows change.

Report generated UTC: 2026-11-01T13:48:46.397167+00:00

Report generated America/Chicago: 2026-11-01T07:48:46.397167-06:00

Accountable Program Owner: Matthew Harris. Prepared by ChatGPT under the user-authorized security assessment and remediation request. Owner approval of residual organizational decisions is not implied.


## Revalidation after the AI Governance release

This section supersedes the current-release identifiers in the earlier baseline section while preserving its remediation history. The application advanced to accepted source 9e89998bfc155db6827b29c7e25af8fdc85aa1b8 and image ai-governance-20261101-v3, digest sha256:8768334d0d90fb3ad81e9eb65fa464236b24f8f00ba4bdfa7f47f4a356600097. ECS revision 14 completed rollout at 2026-11-01T14:29:37.589Z. At 2026-11-01T14:36:17.051046Z, two tasks were running, zero pending, all seven alarms were OK, and all four active stacks retained termination protection. The active image scan completed at 2026-11-01T14:25:37Z without reported findings. Non-root user, read-only root filesystem and dropped capabilities remain configured.

Expanded test source 009b17ea81e4fd8ae4dccb2d82c2d8a9a9bccffb adds tests/test_ai_security_fuzz.py. Compared with the deployed application source, only README, documentation and this test file differ; no runtime code change or new deployment was necessary for this revalidation.

CodeBuild cyber-ops-online-studio-web:083c2298-5b99-47fa-86c6-2d5ae888f91b started 2026-11-01T14:38:44.431Z and finished 2026-11-01T14:41:26.228Z (08:41:26.228 CST), SUCCEEDED. All 100 backend tests passed, with one existing test-client deprecation warning. The corpus includes 1,696 AI field mutations, 341 prior typed/paging cases and 1,000 prior seeded JSON mutations, plus SQL, nested-object, graph, export, token and tenant-boundary tests. The new checks reject forged approval metadata, maintain viewer restrictions and ensure SQL-shaped titles/configuration remain literal and organization scoped. Full-web Bandit and the dependency audit completed successfully, with no known dependency vulnerabilities reported.

Credential-free live checks completed 2026-11-01T14:41:25.791801Z (08:41:25.791801 CST). Readiness, entry/static delivery, authentication requirements, owner attribution, response security headers and invalid-JSON rejection passed. The pre-existing acceptance build and green GitHub workflows separately cover browser, accessibility and image packaging for the deployed AI release; this test-only revalidation did not rebuild the production image.

No additional confirmed exploit was found in this expanded corpus. Earlier malformed-input and graph amplification fixes remain present. Fuzzing is bounded deterministic testing and does not establish the absence of all vulnerabilities.

AWS root caller identity remains observed. Alert-topic metadata at 2026-11-01T14:42:02.639293Z reports zero confirmed and zero pending subscriptions. Scoped AWS administration and an authorized confirmed external alert recipient therefore remain owner actions. No messages or subscription requests were sent. Restore verifier revision 5 and its existing schedule remain unchanged by this revalidation.
