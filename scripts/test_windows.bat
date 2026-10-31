@echo off
setlocal
cd /d "%~dp0.."
echo Cybersecurity Operations Studio - Windows validation (synthetic data only)
echo ---------------------------------------------------------------
echo This process may download Python dependencies and take several minutes.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_windows_validation.ps1"
set "result=%errorlevel%"
echo.
if "%result%"=="0" (
  echo Automated Windows tests PASSED. Interactive Windows 11 QA is still required.
) else (
  echo Automated Windows tests DID NOT PASS. Review artifacts\windows-validation\windows_validation_results.json.
)
echo.
pause
exit /b %result%
