# vCISO governance and multi-framework tracking — initial implementation

## Scope
The new **vCISO & Frameworks** desktop tab offers organization-scoped enable/disable toggles, metadata edition labels, manual implementation items, statuses, named reviewers, evidence *references*, basic initiatives, and retained board-report snapshots. It integrates via `VCISOService` (subclass of Phase3Service). All writes route through the encrypted vault transaction and its existing audit trail. Reports remain local to the vault.

## Framework catalog
NIST CSF, ISO 27001, ISO 27002, COBIT, CIS, C2M2, NIST 800 series, CMMC, FedRAMP, DISA STIG, ASCS (identity needs confirmation), PCI DSS, SOC 2, HIPAA, HITRUST, FFIEC CAT (retired; history only), NERC CIP, IEC 62443, TISAX, MITRE ATT&CK, MITRE D3FEND, Lockheed Martin Cyber Kill Chain, NICE, SCF. Each is selectable independently. Catalog stores references and user-entered items only; it does not redistribute licensed control text or pretend full official catalogs are loaded.

## Reporting definition
Current board snapshot aggregates enabled framework counts and operator-entered statuses, overdue items, strategy initiative counts and budgets, and existing risk/assessment/task metrics. Zero assessed items yields an **unknown** verified percentage (null), rather than misrepresenting 0% or 100% compliance. Deactivating a framework excludes it from *current* score calculations without deleting its history. Published board reports keep their point-in-time JSON snapshots. A reviewer name is only a user-entered claim; it is not an independently authenticated board approval.

## Known gaps / next production milestones
- Detailed licensed catalog import/version pinning, per-sector profiles, obligation applicability, SCF/common-control mappings and assessment scoring standards.
- UI edit screens for framework scope/owner/target, evidence-link validation, initiative status/budget updates, board decision closure, and detailed action/RACI tracking. Backend APIs cover several of these but UI remains basic.
- Board-quality PDF/PowerPoint exports, period-over-period comparisons, committee approvals and recurring report schedules are not yet implemented. Existing executive exports do **not** include this vCISO snapshot.
- Formal vCISO engagement/contract scope, risk appetite, KPIs/KRIs, BCP/IR exercise cadence, stakeholder register, exception register, budget forecast, roadmap dependencies, and evidence expiry reconciliation remain future enhancements.
- Single local operator, no SSO/RBAC, no true electronic signatures or multi-user review. External export files are unencrypted. Do not represent recorded statuses as certified compliance.
- Validate on Windows 11, run full pytest/GUI smoke/packaging and review technical accuracy and licensing before release. No tests were run by the GitHub connector when committing these changes.

## Suggested next sequence
1. Complete per-framework versioned control libraries with source attribution and licensed-import policy.
2. Add reusable canonical control IDs and explicit, curated crosswalks with confidence/source/version.
3. Build full vCISO program workspaces, ownership and board governance workflow, lifecycle management.
4. Add per-framework performance reports and export pipelines; test against synthetic cross-org data.
5. Harden permissions/identity and validate on real Windows device before production data.
