# Custom HTTPS domain

Primary workspace: https://cybersecurityoperationstudio.com/

Configured October 31, 2026. This registered domain differs from the earlier planned `cybersecurityoperationsonlinestudio.com`.

- Route 53 public hosted zone: `Z0193260QCLT3F5B237L`.
- Nameservers: `ns-278.awsdns-34.com`, `ns-1260.awsdns-29.org`, `ns-1859.awsdns-40.co.uk`, `ns-874.awsdns-45.net`. A reusable delegation set preserves the existing registrar delegation.
- ACM certificate in Ohio: `arn:aws:acm:us-east-2:891377316941:certificate/b61862d8-1d31-48a2-b930-442a8d1f89cd`; ISSUED.
- Keep the `_e4543b012604c5685e0f5c0727c0f4f1` validation CNAME for automatic renewal.
- API Gateway regional custom domain: `cybersecurityoperationstudio.com`; TLS_1_2 minimum; AVAILABLE.
- Empty-path API mapping `ldmqyw` targets API `rxhza763j4`, stage `$default`.
- Apex A alias targets `d-4j27dpon14.execute-api.us-east-2.amazonaws.com`, AWS alias zone `ZOJJZC49E0EPZ`.
- ECS and PostgreSQL stay private. The original API Gateway HTTPS endpoint remains available.

Validation from AWS CodeBuild `cyber-ops-online-studio-web:3f50c796-9de8-4eeb-a393-fb58e722efc5` succeeded. Certificate chain and hostname verification passed; TLS 1.3 was negotiated. The login HTML, JavaScript, `/healthz`, and `/readyz` were retrieved successfully over the custom domain; readiness confirmed the database connected. No user credentials were used. Google and Cloudflare public DNS resolved the apex A records. Local resolver caches can retain the previous failure temporarily.

These DNS, reusable delegation set, certificate and API custom-domain resources were created through the AWS APIs and are managed outside the runtime CloudFormation stack. Preserve or import them into IaC deliberately; do not assume deleting the runtime stack removes them. This configuration covers the exact apex HTTPS hostname, not the `www` hostname or an HTTP redirect.
