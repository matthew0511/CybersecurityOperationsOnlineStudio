# Cyber Security Operations Online Studio: AWS web architecture

The online service is an additional runtime for the existing domain services. The PySide6 desktop entry point and encrypted local SQLite vault remain available. Cloud requests use native relational PostgreSQL tables; they do not read or write desktop vault files.

## Request and trust boundaries

Browser HTTPS → API Gateway HTTP API → VPC link → internal ALB → private Fargate tasks → isolated RDS PostgreSQL.

API Gateway terminates the public TLS connection. The VPC-link-to-ALB and ALB-to-task hops use HTTP on private VPC addresses. Database clients use `sslmode=verify-full` with the AWS RDS root trust bundle. There is no public ALB, public task IP, or public database endpoint.

The API Gateway VPC link security group can reach only the ALB listener. The ALB security group can reach only the ECS task port. The task security group permits database access and HTTPS egress through NAT. The foundation database group permits PostgreSQL ingress from the task group only; its default outbound allow-all remains constrained by local-only database subnet routes.

## Domain and database adapter

`cyberstudio.web.database` adapts the application's fixed SQLite-style statements to PostgreSQL parameter binding, `BYTEA` evidence storage, `ON CONFLICT` insertion, and PostgreSQL trigger functions. Client input is never used as a table or column identifier. Migration executes the existing service schemas in a transaction protected by a PostgreSQL advisory lock.

PostgreSQL triggers prevent changes to domain histories and the web request audit log. The migration task owns the schema. The runtime database role has table DML privileges but no schema creation or ownership privileges, so it cannot disable those triggers. Migrations are additive and rerunnable. They do not automatically import existing desktop vault contents.

The application clock records microsecond timestamps. PostgreSQL reads use creation/recording timestamps for the append-only histories whose desktop SQL uses SQLite row identifiers.

## Identity and access

This release is a single-owner installation with multiple organization workspaces. It is not a tenant-separated SaaS or a multiuser RBAC system. The owner has access to all organizations in this installation.

The initial owner must supply a one-time bootstrap code from the `cyber-ops-online-studio-dev/setup` secret and choose a username and password. A database advisory lock prevents simultaneous bootstrap claims. Bootstrap becomes unavailable as soon as an owner exists. Passwords are stored as Argon2id hashes. Sessions use random opaque tokens; only token hashes are stored in PostgreSQL. Cookies use the `__Host-` prefix, HTTPS-only, HttpOnly, SameSite=Strict, and an eight-hour expiry. Stateful API operations require a session-bound CSRF token. Login and setup attempts have shared PostgreSQL rate limits, independent of task count. API Gateway also throttles requests.

The web service exposes an explicit allowlist of domain operations. Private methods and SQL interfaces are not accessible. Organization and related-record checks remain in the existing domain services. Risk acceptance requires owner password re-entry. Named reviewers in management records remain operator-entered assertions, not independently authenticated identities or electronic signatures.

MFA, federated sign-in, multiple user roles, account recovery, and session-management UI are not implemented. Do not represent this release as a complete enterprise identity service.

## Features and limits

The workspace supports organizations, assessments, templates, risks, remediation, residual risk, risk decisions, reference control evaluations, framework activation and scoped implementation items, vendors/reviews, vulnerabilities, evidence, changes, CAB records, audits/findings, initiatives, board snapshots/decisions, CSV import preview/confirmation, and PDF/XLSX export.

Framework catalogs preserve the source application's scope: metadata/headings plus operator-defined implementation records. They are not complete licensed control libraries, certifications, or proof of compliance. Policies and incident records in this source version are imported inventories; full incident response and BCDR workflow automation are not part of this release.

Evidence uploads are limited to 5 MiB; the overall request cap is 7 MiB. Files are database `BYTEA` records protected by encrypted RDS storage, with existing hash verification and manual review semantics. Reports are sensitive plaintext downloads. They are generated in each task's temporary volume, returned without caching, and removed after generation. API Gateway has a 30-second integration timeout, so very large reports need a future asynchronous export design.

## Build, migration, and deployment

`infra/generate_runtime_template.py` generates `infra/web-stack.json`. The runtime stack creates private ingress, API Gateway, KMS-encrypted operational logs, a CodeBuild project, secrets, execution roles, task definitions, and a multi-region management-event CloudTrail trail with a private versioned S3 destination.

CodeBuild reads a versioned source ZIP from a private encrypted bucket. It runs the desktop regression suite and HTTP/PostgreSQL integration tests against a disposable PostgreSQL container before building and pushing the image to ECR. The runtime image uses a non-root user, read-only root filesystem, ephemeral `/tmp` volume, and no desktop GUI dependency.

The migration task is separately authorized to retrieve the RDS master secret and application database secret. It creates native tables, the login role, and scoped schema grants. Runtime tasks retrieve only application credentials and the bootstrap code; their task IAM role has no application AWS policies. Never use the migration task definition as the normal application service.

`DeployService=false` creates infrastructure without starting the web service. After a successful build and migration, updating it to `true` enables two Fargate tasks with rollback circuit breaker, minimum healthy percentage 100, maximum percentage 200, and ALB readiness checks on `/readyz`.

The managed API Gateway HTTPS endpoint works independently of a custom domain. A custom domain needs an ACM-issued certificate, ownership-validation DNS records, an API domain mapping, and DNS alias/CNAME changes at the authoritative provider. A certificate request alone does not configure the domain.

## Verification and operations

`/healthz` reports process health. `/readyz` connects to PostgreSQL and checks the web schema version. Neither exposes credentials. Normal business APIs require authentication.

`tests/test_web.py` covers web security boundaries, owner bootstrap, session invalidation, lockout, native PostgreSQL constraints, immutable histories, organization scoping, core operations, evidence, imports, and both report formats. PostgreSQL tests skip locally when `TEST_DATABASE_URL` is absent; an isolated `studio_test` database is required for the destructive test fixture.

`scripts/validate_online.py` is a synthetic acceptance test for the deployed HTTPS service. Run only before the real owner is configured. It creates a temporary validation owner, exercises live workflows, archives its synthetic organization, and removes its temporary user/session. Immutable synthetic audit history is retained. It never prints credentials. Passing API tests is not a browser accessibility or independent security assessment.

RDS backup configuration and recovery timestamps do not establish that a restore drill passed. Database instance availability is Single-AZ in the approved development foundation. Production HA, alarm routing, cost-budget notifications, application credential rotation, restore testing, penetration testing, and HIPAA/privacy review remain separate gates. Existing operational records and customer data have not been migrated automatically.
