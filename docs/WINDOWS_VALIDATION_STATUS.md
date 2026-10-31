# Windows validation evidence status — 2026-10-28

## Scope

The request was to test Cybersecurity Operations Studio v0.3 in a Windows environment. The environment accessible in this conversation is **Linux** (`x86_64`, Linux kernel 6.18.55), with **no installed Windows VM, Wine, PowerShell, Windows native runtime or available Windows CI account**. It therefore cannot provide native Windows test evidence. No claim of real Windows 11 execution is made.

## Results actually observed in this conversation

| Verification | Environment | Result | Detail |
|---|---|---|---|
| Existing Python pytest suite | Linux Python 3.13 | **PASS** | 38 of 38 tests |
| Python compileall (source, scripts, tests) | Linux Python 3.13 | **PASS** | No syntax errors |
| Windows-runner workflow YAML parsing | Linux / YAML parser | **PASS** | One job, four steps; structural parsing only |
| Runtime availability check | Linux container | **BLOCKED** | `wine`, `wine64`, `qemu-system-x86_64`, `powershell`, `pwsh`, and `docker` not installed |
| PySide6 Qt GUI on Windows | Windows native | **NOT RUN** | Requires Windows + PySide6 installation |
| PyInstaller .exe on Windows | Windows native | **NOT RUN** | Requires Windows build machine |
| Frozen .exe GUI smoke | Windows native | **NOT RUN** | Automated once Windows run begins |
| Windows 11 real GUI test | Windows 11 | **NOT RUN** | Requires interactive human/device testing |
| Signed installer and SmartScreen acceptance | Windows 11 | **NOT RUN** | Requires build/release signing and test environment |

## Delivered execution mechanism

- `scripts/run_windows_validation.ps1` automates the native Windows tests and generates `windows_validation_results.json` and logs.
- `src/cyberstudio/windows_smoke.py` verifies synthetic Qt screen rendering and organization isolation.
- `scripts/launcher.py --self-test` runs the same synthetic GUI smoke check in the frozen PyInstaller executable.
- `.github/workflows/windows-validation.yml` runs Windows Server 2022 CI when committed to a GitHub repository; only execution of the workflow provides any Windows CI result.
- `docs/WINDOWS_VALIDATION_RUNBOOK.md` explains both Windows 11 local and hosted Windows CI routes.

## Release gate

**Status: BLOCKED pending native Windows execution.** Passing Linux backend tests alone does not prove that the PySide6 GUI, Windows paths, frozen dependencies, installer, DPI and accessibility work correctly. Do not market or distribute this as Windows-validated or production-ready until corresponding native and manual acceptance records exist.
