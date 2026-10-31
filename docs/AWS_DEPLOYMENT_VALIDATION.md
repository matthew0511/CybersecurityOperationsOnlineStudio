# AWS deployment and observed validation

Validated October 31, 2026 in us-east-2 (Ohio).

## Deployment identities

| Item | Value |
| --- | --- |
| Managed HTTPS URL | https://rxhza763j4.execute-api.us-east-2.amazonaws.com/ |
| Foundation stack | cyber-ops-online-studio-dev-foundation-v2 |
| Runtime stack | cyber-ops-online-studio-web |
| ECS cluster | cyber-ops-online-studio-dev |
| ECS service | cyber-ops-online-studio-web |
| Application task definition | cyber-ops-online-studio-web:3 |
| Deployed image tag | online-20261031-v3 |
| Image digest | sha256:ae12bb1c00b738a429c5183c3cfeb4a77c3504b22d103d1279fe6e3a5a9e7f43 |
| Final CodeBuild run | cyber-ops-online-studio-web:20b1e138-c471-4492-9329-4f52b27dce4f |
| Source object version | .1DH3MoklG4YspuYIz01kmYjmxWxcikw |
| Migration task | ac59694369804da9b468b13950b8c006 |
| Live acceptance task | a26e3e2a43bd4416b3ccbf011f3d9746 |

ECR tags are immutable. The initial Debian image was used only for schema migration. The final service image uses Alpine with available package updates. Earlier image scans found high-severity base-package issues; the final tag's completed ECR basic scan returned an empty finding count. This is a point-in-time scanner result, not an independent vulnerability assessment or a guarantee of no vulnerabilities.

## Observed tests

- All **51 automated tests passed** in AWS CodeBuild, including native PostgreSQL 18 integration tests. A Starlette/httpx deprecation warning remains; it did not fail the suite.
- Container smoke test passed with a read-only root filesystem, all Linux capabilities dropped, the production non-root UID, a Docker volume matching `/tmp`, and a PostgreSQL connection.
- Migration container exited **0**, creating the native relational schema and restricted application login role. Runtime tasks do not receive the master database credentials.
- Both application target IPs became healthy in different availability zones. The task network configuration disables public IP assignment.
- Public `/readyz` returned HTTP **200** with `status=ready` and `database=connected`.
- The browser loaded the live sign-in page, stylesheet and JavaScript. Authenticated browser UAT across every form, keyboard path, and mobile layout has not been performed.
- Live HTTPS synthetic acceptance exited **0** and logged `live_acceptance=PASS`: unauthenticated rejection; owner bootstrap and login; organization, assessment and answers; risk and remediation; framework activation and implementation; vendor and vulnerability creation; audit/change/initiative creation; dashboard and inventory reads; executive PDF/XLSX; board PDF/XLSX; CSRF rejection; and session revocation after logout.
- After the live test, its temporary owner and sessions were deleted and its synthetic organization was archived. Immutable test audit records remain. The real owner must now perform first-time setup.

Evidence upload/download and cross-organization evidence rejection were verified in the PostgreSQL HTTP integration suite. Live acceptance read the evidence inventory but did not upload an attachment through the deployed public endpoint. Do not merge these two evidence scopes into an unsupported claim.

## Security configuration checked

The approved foundation uses six subnets in two availability zones, two available NAT gateways, private application routes and local-only database subnet routes. RDS is encrypted, not publicly accessible, with seven-day backup retention, deletion protection, an active RDS-managed master secret and a point-in-time recovery timestamp. The database parameter group has `rds.force_ssl=1`. An actual restore drill was not run.

The runtime adds an internal ALB, API Gateway HTTP API with a private VPC link, two non-root tasks, secret injection through restricted execution roles, KMS-encrypted 30-day operational log groups, and a multi-region CloudTrail management-event trail with log validation and private versioned storage. The application task IAM role has no application AWS policies. Business writes have database audit records and immutable PostgreSQL history triggers.

Runtime database data is stored as native PostgreSQL rows. Evidence is stored as BYTEA under encrypted RDS storage. Desktop `.csvault` files have not been migrated or decrypted by this deployment.

## Custom domain: action still required

The managed endpoint above is live. `cybersecurityoperationsonlinestudio.com` is **not yet mapped** to the application. ACM certificate `fecc5942-a7a1-4dcc-9f59-726de290dd27` is pending DNS validation in us-east-2.

Add the following ownership-validation record at the authoritative DNS provider, preserving all existing unrelated records:

| Type | Name | Target |
| --- | --- | --- |
| CNAME | _4f0a62043af73ffc2864f471232a24f4.cybersecurityoperationsonlinestudio.com. | _6777893dce0343a5ea1976bea7e940d1.wzccmgtwzk.acm-validations.aws. |

After ACM reports ISSUED, create an API Gateway regional custom domain using that certificate, map its root to API `rxhza763j4` and stage `$default`, then configure the domain's traffic record to the exact returned regional endpoint. Do not point the domain at the private ALB. GoDaddy's connected search tools do not manage DNS; the browser DNS-management flow is at sign-in. No existing DNS or nameserver records were changed.

## Repeat deployment

1. Review changes and run the appropriate tests. Create a source ZIP excluding `.git`, `.env*`, vaults, bytecode, and virtual environments.
2. Set a **new immutable ImageTag** on the runtime stack. Preserve the other parameters and the generated template. This updates the CodeBuild `IMAGE_URI` and task definitions. For schema changes, keep service rollout gated until the migration has passed.
3. Upload the source archive to the versioned build bucket's `source/studio-web.zip`. Start the `cyber-ops-online-studio-web` CodeBuild project and retain the exact source object version and build ID.
4. Inspect all build phases and tests. Check the ECR scan for the new tag and retain its digest.
5. For migrations, run the stack's `MigrationTask` on the foundation private app subnets and task security group, without a public IP. Verify container exit 0 and the migration logs. Do not inject master credentials into the application task.
6. Enable `DeployService=true` or deploy the new application task definition through the stack. Verify stable ECS deployment, desired/running task counts, ALB health, database readiness, authentication, representative operations and exports.
7. Update this validation record with observed results. The synthetic owner-bootstrap acceptance script must not replace an existing real owner; use an authorized account and a separate safe acceptance strategy after activation.

The source ZIP contains a full repository source snapshot; static files are copied into the image under `src/cyberstudio/web/static`. The CodeBuild project consumes S3 artifacts and is not automatically triggered by GitHub commits.

## Production gates and recovery

This is an operational development installation, not a production or HIPAA certification. RDS is Single-AZ; owner access has no MFA/SSO or user-role separation; no automatic desktop-vault migration, complete licensed framework libraries, incident/BCDR automation, restore drill, independent penetration test, application secret rotation, cost-budget notification or operational alarm routing was completed. Runtime and PostgreSQL access should be assessed before loading confidential customer records or PHI.

The original failed foundation stack remains ROLLBACK_COMPLETE. Its retained ECR repository is reused by the replacement stack. No destructive stack cleanup was authorized or performed. Stateful resources have retention/snapshot/deletion-protection behavior; deleting stacks is not a complete teardown and may leave billable resources. Review a resource inventory and recovery plan before deletion.
