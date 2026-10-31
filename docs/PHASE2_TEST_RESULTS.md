# Phase 2 — Local Test Execution Report

**Date:** 2026-10-28  
**Build:** 0.2.0 source preview  
**Platform:** Non-Windows, headless Python 3.13 runtime  
**Windows PySide6 runtime:** unavailable (not installed)

## Executed validations

| Test | Result | Evidence |
|---|---|---|
| Existing Phase 1 backend regression suite | PASS | `tests/test_phase1.py` |
| Framework metadata, identifiers and unknown-identifier errors | PASS | `tests/test_phase2.py` |
| Custom templates, version increments and snapshot immutability | PASS | `tests/test_phase2.py` |
| Organization isolation for templates, assessments, ratings and evidence | PASS | `tests/test_phase2.py` |
| Residual scoring, acceptance expiration input, attestation, immutable decision records and invalidation | PASS | `tests/test_phase2.py` |
| Evidence byte encryption, integrity checking, size limit, review and links | PASS | `tests/test_phase2.py` |
| CSV import validation, duplicate detection, no partial writes, no approval inference | PASS | `tests/test_phase2.py` |
| Opening and upgrading a Phase 1 vault without losing assessments/risks | PASS | `tests/test_phase2.py` |
| Persisting encrypted evidence across restarts and detecting altered contents | PASS | `tests/test_phase2.py` |
| Casefold-based duplicate risk title validation | PASS | `tests/test_phase2.py` |
| Synthetic end-to-end create → assess → score → residual → accept → evidence → import → PDF/XLSX | PASS | `scripts/synthetic_phase2_smoke.py` |
| Main real Notion exported Risk Register CSV preview/import into an isolated throwaway vault | PASS | 14 source rows, 14 imported, 0 skipped, 0 score discrepancies; private data not distributed |
| Python source compilation | PASS | `python -m compileall -q src scripts` |
| Windows GUI and file dialogs | NOT TESTED | PySide6 missing; require Windows 11 VM |
| Windows installer, signing and SmartScreen | NOT TESTED | No installer built |
| Third-party penetration audit / HIPAA suitability review | NOT TESTED | Do not deploy production data |

**Final automated test output:** `28 passed` (`pytest -q`).  
**Smoke script output:** `PASS synthetic end-to-end: template, mapped assessment, risk, residual, acceptance, evidence, CSV import, PDF/XLSX`.

This report describes tests executed locally, not independent verification of security posture or regulatory compliance.
