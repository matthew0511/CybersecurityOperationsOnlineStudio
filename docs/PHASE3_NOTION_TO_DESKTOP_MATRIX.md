# Notion Cybersecurity Operations Hub to Desktop v0.3 — reconciliation matrix

This matrix is an architectural mapping from the exported Notion Hub documentation and CSV databases to the working code as of October 28, 2026. The Notion export contains 52 Markdown documents and 16 CSV files (including primary and `_all` view variants). It is a *reference source*, not code that can be assumed to run offline or to have verified relationships.

**Legend**: Implemented = service code and automated backend tests; Partial = intentionally limited scope; Planned = no working service code. **UI pending Windows verification** for every module.

| Notion module or capability | Desktop v0.3 status | Current implementation | Next dependency |
|---|---|---|---|
| Risk Register | Implemented (basic) | Encrypted per-org risk records, 5×5 scoring, risk history, CSV import | Risk owners, additional categories, risk methodology configuration |
| Risk Acceptance | Partial | Residual score, immutable decision record, expiry and vault-operator reauthentication | Authenticated distinct approver, RBAC, approval audit signature |
| Compliance Tracker | Partial | Control inventory importer; recorded heading-level evaluations | Safeguard/subcategory versioning, formal evidence criteria, control assessments |
| NIST CSF and CIS Controls | Partial | NIST CSF 2.0 categories and CIS v8.1 18 control headings | Full licensed control text/outcomes, crosswalk provenance |
| Security Policies | Partial | Import policy inventory, source metadata, `unverified` status | Policy review/approval workflow, versioning, controlled document repository |
| Incident Response Tracker | Partial | Source incident inventory with unverified status | Complete incident case lifecycle, timeline, runbooks, contacts, evidence and lessons learned |
| Asset Management | Planned | Free-text vulnerability asset label only | Asset register, ownership, CMDB, acquisition/disposal and links |
| Vulnerability Assessments | Partial | Manual vulnerability register, CVSS numeric input, severity, due/status history | CVSS vector scoring, asset links, scanner imports, recurring validations |
| Threat Intelligence | Planned | None | Indicators, source provenance, triage, intelligence feeds, false-positive review |
| Third-Party Risk Management | Partial | Vendor registry, BAA applicability field, documented reviews, CSV import | BAA proof, contracts, due diligence forms, findings/risk links, reassessment workflows |
| Business Continuity Planning | Planned | No operational BIA/DR module | BIA, RTO/RPO, dependency tracking, exercises and recovery runbooks |
| Disaster Recovery Hub | Planned | No automated recovery scenario or test tracking | Plan and exercise service, evidence/asset/vendor dependencies |
| AI Governance | Planned | No AI inventory or use-case approval in code | Use-case intake, models, data classification, risk treatment and monitoring |
| vCISO Executive Reporting | Partial | Counts, manual risk summaries, evidence/vendor/vulnerability metrics, PDF/XLSX | Historical trend snapshots, board briefing generators, signed baseline comparisons |
| Phishing/Training | Planned | None | Campaign tracking, awareness metrics, training records |
| Evidence Management | Partial | Files up to 5 MiB, SHA-256, review, expiration, risk/assessment links; control linkage | Rich chain of custody, retention policies, source verification, external store |
| Questionnaires and Templates | Implemented (basic) | Per-org custom question sets, versions, frozen snapshot per assessment | Bulk import/export, official question banks, reusable mapping review |
| Acquisition and Multi-client Support | Partial | Unlimited organizations logically separated in one vault | Multiuser tenancy, delegated roles, secure client sharing, portability |
| Notion Database Relationships | Planned | Source fields copied only where supported; no relation reconstruction | Explicit foreign-key mapping/reconciliation across exported CSVs |
| Notion Release QA / Buyer Setup | Documentation | Installation and manual test checklists, synthetic samples, release status | Real Windows acceptance execution, commercial onboarding, support automation |

## Priority advice

1. First fix any Windows UI and backup/migration problems. Existing backend tests cannot substitute for executing the app on the customer's desktop.
2. Strengthen authorization and storage before handling healthcare organization evidence.
3. Implement asset inventory and risk/vendor/control relationships before large additional feature catalogs: they are the core connections needed for accurate reporting.
4. Add full workflows for incidents, business continuity, AI governance, policies and executive vCISO trends only after shared data contracts are stable.
5. Verify and license any external framework material. Do not overstate compliance readiness or certified security capability in product descriptions.

The original Notion workspace and exports remain unchanged. This repository includes no original Notion CSV or MD user records; synthetic examples only.
