@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo First-time setup: Installing required Python packages in a virtual environment.
  where py >nul 2>nul
  if errorlevel 1 (
    echo Python launcher not detected. Install Python 3.12, then run this script again.
    pause
    exit /b 1
  )
  py -3.12 -m venv .venv
  if errorlevel 1 goto fail
  ".venv\Scripts\python.exe" -m pip install -e "."
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m cyberstudio
if errorlevel 1 goto fail
exit /b 0
:fail
echo Setup or launch failed. See README.md for troubleshooting and dependencies.
pause
exit /b 1
