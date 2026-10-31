# Phase 3 Notion Migration — Administrator Guide

**Scope:** Local import of individual CSV exports into an encrypted Phase 3 vault. Notion remains the original system of record until the operator independently validates each migrated record. No automatic account connection, two-way sync, or ZIP-wide relational migration exists.

## Before beginning

1. Open Phase 3 and create an encrypted vault. Set a passphrase and back it up securely.
2. Create a dedicated destination organization. The field `Client` in the CSV, when populated, must match the chosen organization name ignoring case. If exports span several customers, **separate the records before importing**. Never change a customer name merely to bypass organization validation.
3. Make an encrypted vault backup and keep the original Notion export in secure storage. CSV, ZIP and report files are **not encrypted by CyberStudio**.
4. Inspect the CSV outside the app in a trusted editor. Be alert to spreadsheet formulas, imported external URLs, absent references, stale records, and personally identifiable information.
5. In Notion, export the main database or an unfiltered CSV containing all intended rows. It is safer to import the primary `.csv` export, **not both** the primary and `_all.csv` companion views.

## Supported source types

| Choose in desktop UI | Expected input | What is created | What is intentionally not trusted |
|---|---|---|---|
| Risk Register | `Risk Name`, `Probability`, `Impact`; optional `Risk Score`, `Client` | Risks with recomputed 1–25 inherent score | Historical risk acceptance, sign-off, risk treatment, references, attachments |
| Compliance Tracker | `Control Name`, `Control ID`, `Implementation Status`; optional Standard, URL, dates | *Imported control inventory*; not a control evaluation | Implementation and evidence claims, inferred NIST or CIS compliance |
| Security Policies | `Policy Name`, `Approval Status`; optional Version, Policy Owner, Review Date, Document Link | Policy entry with `unverified` status and source metadata | Notion `Approved` status does not become actual approval |
| Vendor Assessments | `Vendor Name`, `Assessment Status`; optional findings, service, criticality, BAA | Vendor with `moderate` default criticality and `unknown` data access/BAA; source annotations retained | Approved vendors, BAA completion and supplier risk determinations |
| Incident Response Tracker | `Incident Name`, `Status`; optional ID, Severity, Detected At, Resolved At, Root Cause | Incident inventory with source status and `imported_unverified=1` | Incident closure, clinical impact, forensic conclusions, resolution validity |

Note: source `Criticality Tier`, BAA labels, vendor findings and original vendor assessment status are retained in `vendor_import_annotations`, but need independent review. The imported control inventory is separate from `control_evaluation_current`; import does not silently increment tested-control counts.

## Walkthrough

1. Select the destination organization at the top of the Windows app.
2. Open **Notion Import** and choose the appropriate database type in the selector.
3. Click **Preview and import selected Notion CSV**.
4. Select the source CSV, not a Markdown page or ZIP file.
5. Review the displayed line-by-line preview: `ready`, `skip`, `previously_imported`. A score discrepancy in Risk Register indicates recalculation, not a rejected record.
6. If any row is skipped, **the whole import is blocked**. Correct the original CSV or export again; then start over. Case-insensitive duplicate names within the CSV or against existing records will block the import.
7. Read the confirmation message, including the warning that source approvals, evidence and relationships are not trusted.
8. Confirm the import. One database transaction inserts the records and append-only import-job metadata. A failure means no partial import of that file.
9. Inspect **Imported Inventory**, **Vendors**, **Risks**, and PDF/XLSX exports as appropriate. Compare names, counts, dates and any classification fields to Notion.
10. Reclassify vendors using the dedicated workflow in a future edit interface or by creating a reviewed record; record new vendor assessments and control evaluations with substantive testing, reviewer, and eligible evidence. The current GUI can add vendors and reviews but cannot yet edit all fields on an imported vendor.

## Row and file validation

- UTF-8 (`UTF-8 with BOM` accepted), well-formed CSV, <=4 MiB, <=5000 rows, <=80 header columns.
- Required source headers must be present. File naming is *not* used to infer type; the user's selected type decides validation.
- Names are required, 1–250 characters; optional text and dates are validated and length-limited.
- When a date is populated, ISO `YYYY-MM-DD` is required for date columns. Timestamps whose first ten characters are valid ISO dates are accepted where supported. Localized dates need pre-conversion.
- Unique file SHA-256 per organization and database type, and unique record names within the destination source table.
- `Client`, if populated, must equal the selected destination organization's name. Empty `Client` fields are allowed, so **operator review remains essential**.
- External source URLs are inert text only; the app does not fetch them or trust any remotely hosted attachment.

## Troubleshooting

**Wrong CSV headers:** Change the UI's source type or export the correct Notion database.

**Client mismatch:** Confirm the selected organization; if mixed-tenancy data is present, split by organization and verify source ownership before import.

**Duplicate name:** Do not import `_all.csv` after its parent dataset. Preview the existing destination. Duplicate detection is case insensitive and conservative; there is no merge/overwrite option in v0.3.

**Invalid date:** Convert date strings in a copied CSV to ISO dates, then re-preview. Preserve the original export unchanged.

**Some rows ready, some skipped:** No records are imported until **all** rows validate. Correct all rows and try again.

**Missing relationships:** Current adapters cannot reconstruct Notion relation properties, linked pages, formulas, rollups or file attachments. Maintain a manual source-to-destination reconciliation sheet; do not assume linked controls or evidence migrated.

## Actual export validation (October 28, 2026)

The matching exported CSVs were tested in a **temporary disposable vault** only. Results: Compliance Tracker 2 ready / 0 skipped; Security Policies 2 / 0; fictional demo Vendor Assessments 1 / 0; Incident Response Tracker 2 / 0. The prior Phase 2 Risk Register test imported 14 source risks with zero skips. The temporary validation vault and source CSV contents are **not included** in the distribution ZIP.

**Risk note:** An unverified Notion claim of compliance, BAA execution, incident resolution or approval is not verification. Always re-evaluate before relying on imported records for decisions, attestations or patient-data processing.
