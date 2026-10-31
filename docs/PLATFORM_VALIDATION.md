# Platform deployment and validation — 31 October 2026

Program Owner - Matthew Harris

## Deployed application

- Site: https://cybersecurityoperationstudio.com/
- Authenticated documentation: https://cybersecurityoperationstudio.com/documentation
- Tested application source: `4a88c12c3e6e6abefea80ffd49d9b6c1e857ea95`.
- Runtime image: `platform-20261031-v9`.
- Image digest: `sha256:ec672027d47efc0099f36f154b609fd22db17ff387de322f48cb780da3244e1f`.
- CodeBuild acceptance: `cyber-ops-online-studio-web:cccaaedf-c8ce-4976-9484-c842699c6c09` — 83 backend tests, four calculation tests, browser and mobile workflows, the automated WCAG serious/critical gate, dependency audit, static analysis and hardened non-root/read-only container smoke test passed. One test-client library deprecation warning was emitted.
- ECR image scan completed with no reported findings at validation time.
- Runtime ECS task definition `cyber-ops-online-studio-web:11` reached COMPLETED with two running tasks.

## Production verification

Public checks validated readiness, health, authentication requirements for security/catalog/documentation/operations APIs, documentation/auditor/recovery page delivery, the fixed owner attribution and the security header. Deployed platform JavaScript, CSS, index and documentation JavaScript matched the tested Git blob hashes. Owner credentials were not used for these checks.

The production runtime connects as `studioapp_platform`, without superuser, BYPASSRLS or schema-creation privileges. Unscoped reads are closed; the isolated PostgreSQL suite additionally verifies cross-organization reads and writes against populated fixtures. The wrapping key round-trip succeeded using runtime injection. No secret value was retrieved into the operator transcript.

The runtime IAM simulation allows upload and version-tag reads under the scanner prefix, but denies writing malware-verdict tags and reading Secrets Manager values. GuardDuty is ACTIVE. Independent version-specific verdicts were NO_THREATS_FOUND for a harmless synthetic file and THREATS_FOUND for the standard EICAR test file.

## AWS availability and release controls

- RDS Multi-AZ: enabled and available.
- Automated backup retention: 14 days. Deletion protection: enabled.
- Pre-migration snapshot: `studio-platform-pre-migration-20261031`, available and retained.
- Seven native CloudWatch alarms cover service CPU/memory, unhealthy/no healthy targets, target errors, database CPU and storage. All were OK at the recorded check.
- The encrypted SNS alert topic has **zero confirmed subscriptions**. External alert delivery is not active until an authorized recipient subscribes and confirms.
- The default CodeBuild project now uses GitHub and `infra/experience-buildspec.yml`, pinned to the tested application source. The default source checkout was checked independently. Historical S3 source archives are not the default build source.
- Operations/runtime generators matched checked templates. cfn-lint and AWS template validation passed. Infrastructure-only changes followed the application build and do not alter the deployed application bytes.

## Migration compatibility correction

The additive migration initially left the prior database role without SELECT on the new archive-marker table, causing old-image scheduled-worker reads to fail during transition. A narrow grant on `pl_trash` corrected this; legacy domain reads were then verified. The migration helper now retains that grant and a regression test covers the failure and correction. The new application role remains subject to organization policies. This record does not claim uninterrupted service during the transition.

The legacy `studioapp` role remains the documented rollback exception. Retirement of that credential should follow a deliberate rollback-window decision; normal runtime tasks receive only the new role's database credentials.

## Restore verification

- Successful execution: `cyber-ops-online-studio-restore:354d1d42-1d2f-44a5-ba4b-ce974ad69a36`.
- Isolated private target: `studio-restore-8a6cb1e25d2e4d96`; production traffic was never directed to it.
- Verifier task: `091969a3c5a34c6b85e3955c1b036bd8`; exit code 0.
- Six restored tables were read and the platform schema version was checked. The result was recorded in source `pl_operations` and is available in Program center → Operations.
- Temporary database deletion completed; a subsequent inventory found no `studio-restore-*` instances.
- Monthly validation is enabled for the first day of each month at 04:00 UTC. Its role can restore a bounded clone prefix, run only the pinned verifier task, and delete only tagged validation clones. Source database deletion is not allowed.
- The initial attempt was denied before creating a clone because the source database groups were missing from the resource scope. The policy was corrected to the specific subnet, option and parameter groups and the successful execution followed. No broad RDS administrator policy was added.

This validates a real private point-in-time restore plus read-only schema and aggregate-count checks. It does not establish application failover time, clinical continuity, or a complete independently witnessed disaster-recovery exercise.

## Activation still required from the organization

The application contains adapters for Microsoft Intune, Microsoft Defender, Notion, Jira Cloud, Zendesk, GitHub, Tenable, Slack, Teams through Graph, and Amazon SES. No customer provider credential was guessed, borrowed from an assistant connection or inserted into source. Configure credentials and scopes through **App integrations**, test authentication, then explicitly enable a connection. Inbound data is staged; outbound publication or messaging requires confirmation.

Microsoft Entra sign-in requires the organization's tenant application and existing-account mappings. MFA is ready for enrollment, but the owner must save recovery codes before enabling an installation-wide requirement. External email, Slack/Teams routing and scheduled report delivery require an authenticated provider plus approved destinations. Native AWS alert delivery needs a confirmed SNS subscriber. The feature catalog is not proof of an activated third-party connection.

## Review locations

- Application: Program center, App integrations, Account security and Documentation.
- Deep implementation and API guidance: [PLATFORM_GUIDE.md](PLATFORM_GUIDE.md).
- Runtime and security templates: `infra/platform-runtime.json`, `infra/platform-security.json`.
- Restore/alarms: `infra/platform-operations.json`.
- Database availability: `infra/platform-foundation.yaml`.
- Continuous checks: `.github/workflows/platform-validation.yml` and `infra/experience-buildspec.yml`.
