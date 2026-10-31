# Release hardening and Phase 4 roadmap

The first three phases produce a functional **source prototype**, not a validated commercial security application. Plan work by risk rather than simply by feature quantity.

## Priority 0 — Release blockers

1. **Independent Windows QA:** Run the full `PHASE3_WINDOWS_QA_CHECKLIST.md` on clean 64-bit Windows 11 VMs with Python and without Python. Fix all UI/workflow defects with regression tests.
2. **Encrypted database architecture:** Replace full-memory SQLite serialization with a vetted, actively maintained per-page encrypted store (e.g., audited SQLCipher build with verified licensing), strong migration and backup/restore testing, and meaningful large-file performance benchmarks. Never describe the current AES-GCM vault as SQLCipher.
3. **Migration safety:** Implement numbered migrations with an atomic restore plan and explicit older-version refusal for upgraded vaults; add disk-space/rollback/corruption tests.
4. **Independent security review:** Threat model for local secrets, backups, file import, evidence, Python packaging, clipboard/export exposure, update supply chain, and malicious local users. Obtain independent code review and remediate findings.
5. **Source/compliance licensing:** Verify terms for NIST/CIS reference metadata, avoid claiming that short identifiers are comprehensive framework coverage, and review all marketing/legal claims.
6. **Privacy/data controls:** Decide on protected information, establish data retention/export/deletion policies, confirm that application design is appropriate for any intended customer use of PHI; obtain HIPAA counsel review if marketed for regulated clinical data.
7. **Commercial Windows packaging:** Pin and hash dependencies, build reproducibly, run antivirus/SmartScreen checks, sign binary/installer, package uninstall/update mechanism, document EULA, support and refund handling.

## Priority 1 — Domain integrity and UX

8. **Authenticated approvals:** Add real local identities or an offline signing workflow with separate authenticated approver credentials, immutable approval payloads, role policies, and segregation of duties. The current vault reauthentication is insufficient for governance approvals.
9. **Evidence chain of custody:** Add timestamps, origin/custodian, retention rules, review expiry, test association, and immutable audit-log verification (event hash chain and tamper-evident exports).
10. **Complete framework control model:** Implement versioned official outcomes and safeguard catalog with legally redistributable source, crosswalk provenance and review, gap/capability scoring. Make mappings explicit, not inferred compliance.
11. **Import reconciliation:** Row-level source IDs, mapped relationships and manual review queue for Notion references/rollups, rollback and selective update. Extend to assets and other missing source databases only after mapping is verified.
12. **Vendor workflow:** Permit controlled editing/import reconciliation, document BAA review without claiming legal compliance, add contract expiry, criticality score methodology, findings-to-risk links, follow-up and evidence expiration.
13. **Vulnerability workflow:** Asset inventory linkage, CVSS vector capture, scanner file adapters, remediation SLAs, approved risk exception linking, history exports and false-positive approvals.
14. **Operations modules:** Full incident response handling, policy lifecycle, tabletop and DR exercises, AI governance, user awareness/training and executive vCISO trend reporting.

## Priority 2 — Commercial usability

15. Professional design system, accessibility and multi-resolution support, keyboard navigation, onboarding and bundled fictional demo vault.
16. User-selectable backups, restore UI, protected export destinations, retention and secure deletion warnings.
17. Guided self-contained installer and detailed buyer support docs, signed updates and optional opt-in anonymous diagnostics.
18. Realistic performance and usability study with cybersecurity consultants and small businesses; collect willingness-to-pay signals before finalizing the one-time price.
19. Licensing: one fully featured application for every purchaser; clarify number of installs and client organizations without artificial feature tiers.
20. Integration tests across three LLM-assisted reviews (ChatGPT implementation, Claude security review, Gemini edge-case QA) with human final approval and a single version-controlled repository.

## Recommended release gates

**Gate A:** End-to-end GUI tested on Windows; schema migrations + restore demonstrably safe.  
**Gate B:** Independent security and privacy reviews complete; critical/high issues fixed.  
**Gate C:** Documentation accurate; signed installer and EULA ready.  
**Gate D:** Beta customers validate critical workflows and reports using synthetic or explicitly authorized low-risk test data.  
**Gate E:** First paid distribution (Gumroad) with support/change-management processes defined.

The next immediate work item is **Windows validation plus storage migration**, before adding further large modules or using real clinical records.
