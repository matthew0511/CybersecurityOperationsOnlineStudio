# Notion Cybersecurity Operations Hub → Desktop Implementation Map

Source: User-provided ZIP export dated October 2026, containing 52 `.md` documents and 16 `.csv` files. The export is a point-in-time snapshot and has not been written back to Notion. The source's Release QA checklist explicitly recorded **HOLD** with unresolved permission and relation tests. The desktop prototype carries over conceptual workflows, not Notion credentials, real records, URLs, formulas or private files.

## Module-by-module migration inventory

| Notion source/module | Desktop target | Phase 1 status | Planned conversion / validation |
|---|---|---|---|
| Risk Register (`Risk Name`, `Probability`, `Impact`, `Risk Score`, `Calculated Criticality Tier`) | `risks`, `risk_score_history` | **Partial**, manually entered risks and fixed matrix | Staged import; validate integer inputs, recompute scores, compare tiers, preserve source IDs/provenance |
| Risk Acceptance | `risk_acceptance_decisions` | Not built | Treat signer field as metadata, NOT approval; require explicit decision, authority, timestamps and expiry |
| Compliance Tracker (`Control ID`, `Implementation Status`, `Evidence Freshness Status`) | Framework controls, implementation, reviews, evidence | Not built | Split implementation, effectiveness and evidence freshness into independent fields; preserve applicability |
| Security Policies | Policy and immutable policy versions | Not built | Preserve approved versions; owner, approval state, effective and review dates |
| Asset Management | Organizations, assets, data classification | Not built | Asset identity dedupe and link to risks with same-org validation |
| Vulnerability Assessments | Findings, asset relations, remediation | Not built | CSV ingestion with source/identifier, date and validated severity |
| Third-Party Risk / Vendor Oversight | Vendors, assessment and related risk | Not built | Preserve BAA *applicability* separately from signed/agreed status; provenance for evidence |
| Incident Response Tracker (`Detected At`, `Resolved At`, `Resolution Hours`) | Incidents, events, timeline | Not built | UTC normalization, close/reopen history, validation of negative/invalid intervals |
| Business Continuity Planning | Business services and governance plans | Not built | Separate governance BCP from operational runbook |
| Business Continuity and Disaster Recovery Hub | Recovery plans, runbooks, exercises | Not built | Explicit RTO/RPO units (hours), exercise results distinct from targets |
| Threat Intelligence | Indicators and alert context | Not built | Validate expiration, source trust, dedup; no live feed implied |
| AI Governance | AI system inventory, use-case approval, risk/exception | Not built | Link use case to vendor, data categories, approval and periodic review |
| vCISO Executive Reporting | Reporting engine + history | **Partial**, risk snapshot only | Create denominator-aware framework readiness, exclusions, historical score snapshots |
| Regulatory Requirements Watchlist | Obligations and manual change tracker | Not built (proposed in source) | Confirm licensed legal references and validation responsibility |
| Security Training Tracker | Training assignments and attestations | Not built (proposed in source) | Manual completions with evidence, cadence and accountability |
| Fictional Demo — Vendor to Evidence | Synthetic demo tenant | Not seeded in Phase 1 | Only import if clearly labeled synthetic and isolated from real reports |
| Buyer Getting Started and Technical Specification | Windows help and architecture | **Started**, README + implementation spec | Build accessible in-app guided onboarding and glossary |

## Observed Notion table headers for future import fixtures

- **Risk Register**: `Risk Name, Description, Category, Probability, Impact, Risk Score, Calculated Criticality Tier, Sign Off Authorization, Criticality Tier, Associated Assets, Client, Governing Policies and Controls, Treatment Status`.
- **Compliance Tracker**: `Control Name, Control ID, Evidence Artifact URL, Implementation Status, Review Date, Standard, Related Policies, Associated Risks, Linked Critical Risk Count, Unapproved Risk Count, Mitigation Exposure Indicator, Client, Domain, Evidence Freshness Status, Last Evidence Date`.
- **Incident Response**: `Incident Name, Incident ID, Severity, Status, Related Assets, Client, Detected At, Governing Policies, Resolution Hours, Resolved At, Root Cause`.
- **Security Policies**: `Policy Name, Version, Next Review Date, Approval Status, Policy Owner, Document Link, Related Incidents`.

These are mapping examples grounded in the export. The Phase 1 UI **does not currently import these files**. Future ingestion must not assume a Notion CSV's display-name relations reliably contain canonical IDs; page exports, CSV records and unique Notion identifiers must be reconciled.

## Import and data-quality contract (future work)

1. Select directory/ZIP, detect Notion export dialect, and preview selected entities before any write.
2. Stage data in `import_jobs` / `import_rows`; record SHA-256, filenames, field-level mapping and parser/version.
3. Identify sample/test/production records; reject unsafely mixed records until buyer chooses policy.
4. Build per-organization identity map; default to create new organizations, never auto-merge by display name only.
5. Validate timestamps, units, optionality, enum values, risk rating boundaries, text encoding and external IDs.
6. Recreate relationships in a second pass only when source/target identities and organizations are unambiguous.
7. Recalculate formula fields locally, compare to imported Notion values; report differences instead of silently overwriting.
8. Flag dangling links, expired evidence URLs, missing owner, missing approval, ambiguous client, duplicates and invalid rows.
9. Provide preview, explicit confirmation, transactional import, detailed failure report and rollback/restore procedure.
10. Prohibit external Notion link access without explicit user consent, and do not fetch evidence files automatically.

## Quality gates inherited from source QA

- Risk score type/range and threshold edge cases — automated score tests completed for new desktop logic.
- Reciprocal association consistency — native composite FK tests completed on minimal assessment and task relations; complete Notion relation coverage pending.
- Evidence publish filter vs auditor access — **not implemented**; do not assume a UI filter establishes authorization.
- Permission isolation — service-scoped organization isolation tested; operating-system file security and multi-user permissions NOT tested.
- Vendor BAA applicability vs status — unimplemented.
- Approval/sign-off semantic separation — unimplemented.
- Continuity runbook exercise tests — unimplemented.

## Implementation strategy

Retain the original Notion workspace as an independent sellable template. Develop a separately reviewed source-code application with its own database, documentation, licensing and maintenance. Only deliver features as "implemented" after code, UI, data migration, boundary tests and clean-device validation are completed. Prefer original descriptions and licensed standards metadata over copying potentially restricted framework passages.


## Phase 2 implementation update (2026-10-28)

The original Phase 1 status matrix above is retained for historical reference. The following capabilities have now been added to the **Phase 2 Python source**; automated backend tests pass, while Windows GUI/device acceptance remains pending:

- **Risk Register:** CSV preview and all-or-nothing import from the exported Notion Risk Register; score recalculation, client validation, duplicate protection and immutable import jobs. Original Notion approval statuses are never represented as approved decisions.
- **Frameworks:** metadata-only NIST CSF 2.0 categories (22), CIS Controls 8.1 headings (18), original example question bank with suggested topic mappings and immutable assessment snapshots. Not full proprietary texts or compliance certification.
- **Risk Acceptance:** residual scoring and explicitly recorded authority assertions, with expiring approvals and invalidation on residual re-assessment. Not authenticated approval signatures.
- **Evidence:** encrypted-in-vault attachment bytes up to 5 MiB each, integrity hashes, review metadata and risk/assessment links. Not the full Notion evidence relation/renewal model.
- **Documentation:** see `PHASE2_IMPLEMENTATION_SPEC.md`, `PHASE2_NOTION_IMPORT_GUIDE.md`, `PHASE2_WINDOWS_QA_CHECKLIST.md` for implementation details and verification status.

**Still not implemented:** other Notion CSV import adapters, preserving relation IDs, complete cross-domain workflows, executive readiness aggregation, BAA decisions, incident/continuity/AI governance modules, a real role/permission model or production scaling. Never treat the Notion export's aspirational specs as working desktop code.
