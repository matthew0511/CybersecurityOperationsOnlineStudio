# Enterprise governance workflow extension (local operator preview)

## Features delivered
- Policy-driven CAB approval thresholds (normal and emergency); unique votes and requester/implementer separation by **entered display name**, not verifiable identity.
- Approval decision history, rejection, return-to-draft and existing pre/post-validation gates.
- Organization-scoped evidence custody records: encrypted vault BLOB, SHA-256 digest, 5 MiB file limit, classification, reviewer, expiry, append-only custody entries and validated association to changes/audits/findings.
- Calendar month view (QCalendarWidget) with a schedule table displaying changes beginning in the selected month.
- Governance PDF and Excel board packets: risk/change/audit/evidence summary, audit findings, inventories, disclaimers.
- Board snapshots now include new evidence and approval-policy metrics.

## Boundaries that matter
This remains an offline, single-operator **prototype**. Named reviewers and collectors are manually entered and can be impersonated. No RBAC, SSO, tamper-evident external seal, two-person independently authenticated voting, actual background schedulers, audit workpaper engine or external GRC integrations. A local vault administrator can alter the database and regenerate stored history; immutable triggers are not cryptographically tamperproof. Do not treat any action as a legally binding electronic signature or regulatory attestation.

Board reports exported in PDF/XLSX are unencrypted and must be protected. SHA-256 proves blob consistency against stored digest, not independent chain-of-custody authenticity. Calendar displays schedule starts, not spanning events in other months. Incident, vulnerability and canonical framework evidence auto-linking still require future work.

## Validation
Run the complete pytest suite on Windows, perform Qt UI smoke testing, test vault backup/restore, verify report output and independent security review before use with customer information. New tests are committed but GitHub writes do not run the test runner.
