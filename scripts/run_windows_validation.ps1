<#
  Native-Windows test harness. Run locally on Windows 11, or in Windows CI.
  Does not alter a user's existing CyberStudio vault; uses synthetic data.
  Needs internet for initial Python dependency / PyInstaller install.
  All build artifacts are UNSIGNED, developer/test-only.
#>
[CmdletBinding()]
param(
    [string]$ReportDirectory = "artifacts\windows-validation",
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repo
$reportDir = [System.IO.Path]::GetFullPath((Join-Path $repo $ReportDirectory))
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

$report = [ordered]@{
    started_utc = [DateTime]::UtcNow.ToString('o')
    runtime_os = [Environment]::OSVersion.VersionString
    platform = [Environment]::OSVersion.Platform.ToString()
    powershell_version = $PSVersionTable.PSVersion.ToString()
    runner_name = $env:RUNNER_NAME
    python_version = ''
    unit_tests = 'NOT_RUN'
    gui_smoke = 'NOT_RUN'
    frozen_executable_build = 'NOT_RUN'
    frozen_executable_smoke = 'NOT_RUN'
    executable_sha256 = $null
    result = 'FAIL'
    error = ''
    note = 'Windows-hosted CI can run on Windows Server rather than Windows 11. Real Windows 11 manual UX/DPI/installer/security testing is a separate gate.'
}

function Assert-Exit([string]$Action) {
    if ($LASTEXITCODE -ne 0) { throw "$Action failed with exit code $LASTEXITCODE" }
}

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw 'This validation script must run on a native Windows machine.'
    }
    & py -3.12 --version 2>&1 | Out-File (Join-Path $reportDir 'python_version.txt')
    Assert-Exit 'Python 3.12 version check'
    $report.python_version = (Get-Content (Join-Path $reportDir 'python_version.txt') -Raw).Trim()

    $venv = Join-Path $repo '.venv-winvalidation'
    & py -3.12 -m venv $venv
    Assert-Exit 'Create test virtual environment'
    $python = Join-Path $venv 'Scripts\python.exe'
    & $python -m pip install --upgrade pip
    Assert-Exit 'Upgrade pip'
    & $python -m pip install -e '.[dev]' 'pyinstaller>=6,<7'
    Assert-Exit 'Install application and validation dependencies'

    & $python -m compileall -q src scripts tests
    Assert-Exit 'Compile Python source'
    & $python -m pytest -q 2>&1 | Tee-Object -FilePath (Join-Path $reportDir 'pytest.txt')
    Assert-Exit 'Run regression tests'
    $report.unit_tests = 'PASS'

    $env:QT_QPA_PLATFORM = 'offscreen'
    $env:QT_OPENGL = 'software'
    & $python -m cyberstudio.windows_smoke --output-dir $reportDir 2>&1 | Tee-Object -FilePath (Join-Path $reportDir 'qt_gui_smoke.txt')
    Assert-Exit 'Synthetic Qt GUI smoke'
    $report.gui_smoke = 'PASS'

    if (-not $SkipBuild) {
        & $python -m PyInstaller --noconfirm --clean --name CybersecurityOperationsStudio --windowed --onedir --paths src scripts\launcher.py 2>&1 | Tee-Object -FilePath (Join-Path $reportDir 'pyinstaller.txt')
        Assert-Exit 'PyInstaller build'
        $report.frozen_executable_build = 'PASS'
        $exe = Join-Path $repo 'dist\CybersecurityOperationsStudio\CybersecurityOperationsStudio.exe'
        if (-not (Test-Path $exe)) { throw "Executable missing: $exe" }
        # --self-test operates solely on a temporary, synthetic vault.
        & $exe --self-test --output-dir $reportDir 2>&1 | Tee-Object -FilePath (Join-Path $reportDir 'frozen_gui_smoke.txt')
        Assert-Exit 'Frozen executable GUI smoke'
        $report.frozen_executable_smoke = 'PASS'
        $report.executable_sha256 = (Get-FileHash -Algorithm SHA256 $exe).Hash
    }
    $report.result = 'PASS'
}
catch {
    $report.error = $_.Exception.Message
    Write-Error $report.error -ErrorAction Continue
}
finally {
    $report.finished_utc = [DateTime]::UtcNow.ToString('o')
    $report | ConvertTo-Json -Depth 5 | Out-File -FilePath (Join-Path $reportDir 'windows_validation_results.json') -Encoding UTF8
    Write-Host "Results: $(Join-Path $reportDir 'windows_validation_results.json')"
}
if ($report.result -ne 'PASS') { exit 1 }
Write-Host 'PASS: Windows automated validation completed. Manual Windows 11 acceptance testing is still required.'
