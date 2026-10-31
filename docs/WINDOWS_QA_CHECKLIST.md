# Windows 11 Acceptance Checklist — Pending

This worksheet should be completed on a **clean, supported Windows 11 machine or virtual machine**, separate from the developer workstation. Check the actual outcome. Do not treat a successful Python syntax check as proof that Qt is functional.

| ID | Test | Expected result | Status |
|---|---|---|---|
| WIN-01 | Launch from a fresh Python 3.12 x64 virtual environment | No missing Qt/cryptography dynamic library; GUI opens | NOT TESTED |
| WIN-02 | First-run welcome and passphrase confirmation | New vault created; short/mismatched passphrases rejected | NOT TESTED |
| WIN-03 | Close/reopen with correct password | Previous data restored | NOT TESTED |
| WIN-04 | Reopen with wrong password | Authentication rejected without data leak | NOT TESTED |
| WIN-05 | Add two distinct organizations; switch repeatedly | No cross-organization UI data leak | NOT TESTED |
| WIN-06 | Add assessment, answer 8 questions, restart and reopen | Answers saved and restored | NOT TESTED |
| WIN-07 | Add risks with likelihood/impact 1,1; 2,5; 4,5; 5,5 | 1 Low, 10 High, 20 Critical, 25 Critical | NOT TESTED |
| WIN-08 | Create remediation task; edit status | History and counts update | NOT TESTED |
| WIN-09 | Export PDF and Excel; open files | Correct org, no formula execution, professional presentation | NOT TESTED |
| WIN-10 | Create encrypted backup; open backup on another test profile | Backup decrypts using original passphrase, contains correct records | NOT TESTED |
| WIN-11 | Launch two instances targeting same vault | Second instance denied without corruption | NOT TESTED |
| WIN-12 | Abrupt power loss during save in a disposable test VM | Current or previous complete vault opens, no silent data loss | NOT TESTED |
| WIN-13 | Build with `scripts/build_windows.ps1`, run on clean VM without Python | Packaged GUI launches without missing DLLs | NOT TESTED |
| WIN-14 | Windows SmartScreen/signature, install/uninstall, backup during updates | Appropriate signed installer and rollback | NOT TESTED |
| WIN-15 | Screen reader, keyboard navigation, 125%/200% DPI and resize | Usable without obscured actions | NOT TESTED |

**Release policy:** All P0 tests need evidence (OS build, Python/build versions, tester, date, expected/observed output, logs scrubbed of sensitive data). Independently assess cryptographic persistence and perform full threat model before accepting clinical or commercial data. Release state remains **HOLD**.
