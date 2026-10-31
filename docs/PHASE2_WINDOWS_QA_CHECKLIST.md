# Phase 2 Windows 11 GUI Quality Checklist — Not Yet Verified

Run on a clean Windows 11 VM and a representative consumer Windows device. Record actual evidence, date, tester, result, screenshots where permissible, and issue ticket for failure. Do not claim pass without running each step.

- [ ] Clean install Python 3.12 64-bit and `py -3.12 -m pip install -e '.[dev]'`.
- [ ] `py -3.12 -m pytest -q` passes Phase 1 + Phase 2 tests.
- [ ] Existing Phase 1 vault copied to encrypted backup; Phase 2 opens without data loss.
- [ ] New passphrase: create/confirm, cancel, invalid password, wrong password and simultaneous vault open.
- [ ] Create two organizations; verify no assessment, risk, evidence, or template leakage on switching.
- [ ] Framework tabs display **22 NIST CSF 2.0 category names** and **18 CIS v8.1 headings**; metadata-only disclaimer visible.
- [ ] Create custom template and map question; create assessment and record answers; add another template question; existing assessment remains unchanged.
- [ ] Seed starter template, verify eight sample questions and 16 suggested mappings.
- [ ] Create 4×5 inherent risk (20), then residual 2×3 (6); show distinct columns and correct bands.
- [ ] Attempt approval without expiration and without attestation (both fail); approve valid risk; reassess residual risk (acceptance invalidated).
- [ ] Import 3-risk synthetic CSV: preview, cancel, confirm; verify repeated import blocked and no cross-tenant records.
- [ ] Import corrupted file and duplicate rows: no partial writes; original file unchanged.
- [ ] Add redacted 1 KB evidence; link it to risk and assessment; verify review and integrity; export to chosen folder after warning.
- [ ] Reject >5 MiB evidence and show understandable error.
- [ ] PDF and Excel **Phase 1 snapshot** exports still function; exported files are unencrypted; no exported formula injection.
- [ ] Backup Phase 2 vault and successfully restore it on a clean test profile.
- [ ] Test interruption during save, limited disk space, read-only directory, antivirus and Defender policy.
- [ ] Rebuild with PyInstaller on Windows; verify all resources bundled; run on VM without system Python.
- [ ] Threat model/privacy/legal review before allowing production records or Gumroad release.
