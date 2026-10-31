# Notion Import Guide — Phase 2

1. **Back up your vault.** From Settings, use Create encrypted backup, keeping passphrase and backup safely separate. Never test a new importer directly on an irreplaceable production vault.
2. Open the export ZIP from Notion separately. Find `Cybersecurity Operations Hub/Risk Register/Risk Register ... .csv` (prefer the regular table export; do not choose `..._all.csv` unless needed).
3. In the desktop app, select the correct client organization. The importer **never auto-creates or auto-merges organizations** and does not interpret unrelated client labels as an alias.
4. Select **Notion Import → Preview and import Risk Register CSV**. Choose the extracted `.csv`, not the ZIP.
5. Review the preview counts. Any bad or duplicate row stops the whole import. Edit the CSV in a trusted tool to fix issues and preview again. Files must be UTF-8, <=4 MiB and 5,000 rows.
6. The preview indicates when `Risk Score` disagrees with recalculated `Probability × Impact`. The imported score always uses the app matrix (likelihood and impact each 1–5).
7. Choose **Confirm** only if the preview has no skipped rows and the target organization is correct. The importer records a SHA-256 source hash and rejects repeat imports of identical files to the same organization.
8. Verify the imported risks in the Risks tab and document the **real rationale, controls and current treatment decisions**. Old Notion sign-off text, risk acceptance, evidence URLs, assets and policy relationships are not migrated or authenticated.
9. Keep the original export in secure storage as your audit and rollback reference. This importer does not reverse the import; rollback is restoration of your pre-import encrypted vault backup.

**Troubleshooting:** If a file reports the wrong client, correct your organization selection or CSV values rather than overriding the check. If a duplicate title already exists, reconcile manually: the tool deliberately does not merge records based solely on text name. If the CSV contains malformed rows, export afresh or repair them offline. The app never retrieves linked evidence from Notion URLs.

**Developer example fixture:** `examples/SYNTHETIC_NOTION_RISKS.csv` contains fictional records suitable for a safe import test.
