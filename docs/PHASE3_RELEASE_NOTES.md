# Phase 3 Release Notes — v0.3.0 (2026-10-28)

**Product:** Cybersecurity Operations Studio  
**Distribution:** Developer source ZIP, not a packaged Windows installer  
**Testing:** 38 automated Python tests passed; synthetic domain workflow with PDF and XLSX export passed; Windows GUI and signed executable not tested.

## What's new

- Operator-entered NIST CSF 2.0 and CIS Controls v8.1 heading-level evaluations with evidence-aware current status, immutable historical evaluations and compliance-limitation disclosures.
- Organization-scoped vendor registry and periodic vendor review workflows, risk score and due-date indicators.
- Manual vulnerability register with severity, CVSS numeric field, affected asset name, due dates, immutable status history and overdue indicators.
- Evidence expiration and recalculation of effective review status, without deleting stored artifacts or silently overwriting human review history.
- Local passphrase reauthentication for risk acceptance decisions; not verification of the named approver's identity.
- New Notion CSV import adapters: compliance controls, security policies, vendor assessments and incident tracker. Preview, input validation, organization comparison, duplicate detection and atomic import; source claims remain unverified.
- Enhanced PDF executive snapshot and 10-tab Excel workbook, with conservative raw-count indicators and clear disclaimers.
- Additional desktop tabs for Controls, Vendors, Vulnerabilities and Imported Inventory.
- `PRAGMA user_version=3`, additive schema upgrade, future-version refusal.
- Original user Notion data not included in distribution; synthetic examples included.

## Known limitations / next phase

Windows graphical UI is unverified; PySide6 was not available in the headless development environment. Full security review and code signing remain outstanding. Vault uses in-memory serialized SQLite encrypted at rest, not SQLCipher; attachments enlarge the whole-vault writes. Compliance assessment is not certified; framework libraries contain headings, not all official control statements. The current design is single-operator and not safe to claim as multiuser authenticated signoff. API synchronization, Notion relational mapping, asset CMDB, incident case tracking, cloud sync, scanner imports, full policy governance, full business-continuity and AI governance workflows remain future enhancements.

**Required before commercial distribution:** Windows QA, dependency/license audit, storage/migration hardening, independent security assessment, approval authorization architecture, signed build and reviewed privacy terms.
