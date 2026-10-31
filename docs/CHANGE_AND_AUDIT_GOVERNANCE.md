# Change Control and Audit & Assurance

Both desktop modules use the application's encrypted single-operator vault and organization-scoped SQLite records.

## Change Control workflow
1. Create a change: standard, normal or emergency; record requester, owner, risk and description.
2. Edit the implementation/rollback plans and maintenance window (ISO-style dates or datetimes).
3. Submit, move to review, and record a CAB reviewer decision.
4. When approved, schedule the change and record a passing pre-implementation check before implementation.
5. Execute, move into validation, record a passing post-implementation check, and close or roll back.
6. All activity is recorded in append-only governance events and the existing audit table.

A named reviewer is manually entered and is **not** independently authenticated. Emergency/standard change pathways share lifecycle mechanics; organization-specific authorization policies and multi-approver quorum are not implemented. Calendar is displayed via start/end columns, not yet a graphical month-view. Validation checks capture evidence references, not content verification.

## Audit & Assurance workflow
1. Create internal, external, regulatory or supplier audit engagement; record framework/scope and lead.
2. Progress planned -> fieldwork -> review -> closed.
3. Record findings with severity, description, remediation owner, due date.
4. Move findings through remediation and verification. Closure requires reviewer name and evidence reference.
5. Review metrics and lifecycle history.

Management acceptance in this initial module is a status entry rather than a signed risk acceptance workflow. Audit fieldwork checklists, evidence requests, auditor portal, independent attestation, testing procedures, attachment linking, graphical change calendar, PDF/Excel exports, full event hash-chain and actual CAB authentication are not yet implemented. No claim of compliance certification should be inferred.

## Windows verification
Run `python -m pytest -q` and `scripts/run_windows_validation.ps1`; confirm navigation, edits, close/reopen persistence, and organization isolation. Until verified and security reviewed, use synthetic data only.
