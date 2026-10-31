# Windows validation runbook — Cybersecurity Operations Studio v0.3 validation candidate

**Prepared:** 2026-10-28. **Evidence status:** Not executed on native Windows in this ChatGPT environment. No Windows VM, Wine, PowerShell, or Windows runner was available. The previously completed 38 pytest cases ran on Linux and must not be labeled Windows passes.

This runbook provides executable test automation for a real Windows environment. It uses **synthetic data only** and is not a penetration test, HIPAA compliance certification, signed installer, or proof of Windows 11 user-experience compatibility.

## Route A: Run directly on Windows 11 (best match to product target)

1. Use an isolated Windows 11 x64 device or VM. Install official **64-bit Python 3.12** and the Python Launcher (`py`). Use a standard local test account. Do not copy any production `.csvault`, PHI, client CSVs, or sensitive data into the test machine.
2. Extract the ZIP to a simple local folder such as `C:\CyberStudioValidation`, not OneDrive or a network-mounted directory.
3. **Simplest option:** double-click `scripts\test_windows.bat`. Alternatively, open **PowerShell** inside the extracted folder and run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1
   ```

   The first execution needs internet access to fetch PySide6, PyInstaller, and the other Python dependencies. The test script builds a dedicated `.venv-winvalidation`, runs pytest and compiled Python checks, starts the 15-tab Qt interface in headless/offscreen mode, verifies synthetic organization isolation, generates a screenshot, builds an **unsigned** PyInstaller folder, then tests the frozen executable with its self-test entrypoint. The self-test never opens the real user's vault.
4. Open `artifacts\windows-validation\windows_validation_results.json`. Only a `"result": "PASS"` and all four corresponding statuses set to PASS mean that **automated Windows testing** passed. An unexpected failure is reported in the JSON and tool logs.
5. Validate the **interactive GUI** separately, on the same Windows 11 device: start `dist\CybersecurityOperationsStudio\CybersecurityOperationsStudio.exe` without arguments. Follow `docs/PHASE3_WINDOWS_QA_CHECKLIST.md`. Record the OS build (Settings > System > About), display scaling (100%, 125%, 150%), screen-reader and keyboard access, Windows Defender/SmartScreen handling, backup/restore, and first-run behavior under a new Windows account. Do not skip this step based on passing offscreen tests.
6. Do not sign or distribute commercially until the build, installation, privacy, licensing, backup/restore, and independent security checks are completed. The PyInstaller `onedir` output is not an installer.

## Route B: Automated Microsoft Windows Server run in GitHub Actions

1. Create a **private** GitHub repository and upload the extracted **project contents** to its root (not just the outer ZIP). Do not commit `.csvault` vaults, private Notion exports, customer reports, or generated test files.
2. The supplied `.github/workflows/windows-validation.yml` workflow runs on `windows-2022` (a **Windows Server 2022 runner**, NOT Windows 11). Trigger it from the **Actions > Windows automated validation > Run workflow** control, or push a source change.
3. Review the build log and download the `cyberstudio-windows-ci` artifact. Inspect `windows_validation_results.json`, screenshots, test logs, executable folder, and SHA-256 digest. Only the actual job result establishes that the Windows Server run passed.
4. Use Route A for the Windows 11-specific manual acceptance gate. A Windows Server CI pass never replaces a Windows 11 interactive test.

## What each automated gate checks

| Gate | Checks | Evidence |
|---|---|---|
| Python / dependencies | Python 3.12 x64 and dependency installation | `python_version.txt`, job logs |
| Python regression | Existing encryption, organizations, scoring, migrations, imports, and exports | `pytest.txt` |
| Qt headless GUI | 15 tabs, MainWindow creation, native Qt rendering, synthetic organization scoping, record display | `qt_gui_smoke.txt`, `qt_smoke_result.txt`, PNG |
| PyInstaller | Win32 binary created with bundled dependencies | `pyinstaller.txt`, `.exe`, SHA-256 |
| Frozen binary | Built `.exe --self-test` can instantiate and exercise GUI in Windows headless mode | `frozen_gui_smoke.txt`, `qt_smoke_result.txt` |
| Interactive Windows 11 QA | Touch/keyboard/DPI, file dialogs, OS integration, backups, usability, first-use | **Manual; not automated by this harness** |

## Known limitations

- CI runs in a Windows Server environment and cannot attest to a native Windows 11 desktop experience.
- GUI smoke tests use the Qt offscreen platform, not physical monitor/display drivers or accessibility services.
- The package downloads dependencies within the test environment; no pinned hashes or SBOM have been generated, and no independent dependency/security review is represented.
- `--self-test` has no impact on real vaults. It creates and deletes synthetic vaults under a system temporary folder.
- The supplied PyInstaller developer build is **unsigned**, not a real installer or distributable commercial product.
- Report exports are unencrypted. Evidence in these tests is fictional and must not be confused with compliance evidence.

## Test record template

Record `run_date`, `tester`, Windows edition/build, Python version, SHA-256 of exact source ZIP, `windows_validation_results.json`, failed checks, repairs/retests, screenshot and logs. Distinguish **PASS**, **FAIL**, **BLOCKED**, and **NOT RUN**. Do not transform NOT RUN into PASS because the source compiled on Linux.
