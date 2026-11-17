<#
.SYNOPSIS
    Runs the full VLTD automation suite in panel-by-panel batches and prints a consolidated summary.

.DESCRIPTION
    Each "batch" is one panel/module of the application. Batches run sequentially (so one batch's xdist
    workers never contend with another's against the shared staging environment); each batch still runs its
    own tests in parallel via pytest-xdist as usual. -KnownBugs also re-runs every tracked regression test for
    a confirmed defect (bug_report.md) - an XFAIL means the bug is still present, an XPASS means it looks fixed.

    Logs: one file per batch under .\regression-logs\<timestamp>\<batch-name>.log, plus a summary at the end.

.PARAMETER KnownBugs
    Include the known-defect regression tests (xfail; see bug_report.md). Default: included.

.PARAMETER SkipCleanup
    Pass --keep-test-data to every batch (skip the end-of-run test-data cleanup sweep).

.EXAMPLE
    .\run_regression_batches.ps1
    .\run_regression_batches.ps1 -KnownBugs:$false   # only the default (non-xfail) suite
#>

param(
    [bool]$KnownBugs = $true,
    [switch]$SkipCleanup
)

$ErrorActionPreference = "Stop"

# ── Batches: one per panel, in a sensible dependency order ────────────────────
# (login/dashboard first since everything depends on being able to sign in; shared Admin-side modules next;
#  then each role's own panel)
$batches = [ordered]@{
    "01-login-and-dashboard" = @("tests/test_login.py", "tests/test_dashboard.py", "tests/test_dashboard_extended.py", "tests/test_admin_panel_health.py")
    "02-administration"      = @("tests/administration")
    "03-permissions"         = @("tests/permissions")
    "04-configuration"       = @("tests/configuration")
    "05-oem-management"      = @("tests/oem_management")
    "06-oem-panel"           = @("tests/oem_panel")
    "07-fitment-centre-panel"= @("tests/fc_panel")
    "08-role-panels"         = @("tests/role_panels")
}

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logDir = Join-Path $PSScriptRoot "regression-logs\$stamp"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$results = @()

foreach ($name in $batches.Keys) {
    $paths = $batches[$name]
    $logFile = Join-Path $logDir "$name.log"

    $args = @($paths)
    if ($KnownBugs) { $args += "--known-bugs" }
    if ($SkipCleanup) { $args += "--keep-test-data" }

    Write-Host ""
    Write-Host "=== Batch: $name ===" -ForegroundColor Cyan
    Write-Host "    pytest $($args -join ' ')"
    Write-Host "    log: $logFile"

    $start = Get-Date
    & python -m pytest @args 2>&1 | Tee-Object -FilePath $logFile | Out-Null
    $exitCode = $LASTEXITCODE
    $duration = (Get-Date) - $start

    $summaryLine = Select-String -Path $logFile -Pattern "^=+ .* =+$" | Select-Object -Last 1
    $summaryText = if ($summaryLine) { $summaryLine.Line.Trim(' =') } else { "(no summary line found - see log)" }

    $results += [pscustomobject]@{
        Batch    = $name
        ExitCode = $exitCode
        Duration = "{0:mm\:ss}" -f $duration
        Summary  = $summaryText
    }

    $color = if ($exitCode -eq 0) { "Green" } else { "Red" }
    Write-Host "    -> $summaryText (exit $exitCode, $('{0:mm\:ss}' -f $duration))" -ForegroundColor $color
}

Write-Host ""
Write-Host "=========================== REGRESSION SUMMARY ===========================" -ForegroundColor Cyan
$results | Format-Table -AutoSize | Out-String | Write-Host

$overallFailed = ($results | Where-Object { $_.ExitCode -ne 0 }).Count
$summaryPath = Join-Path $logDir "_summary.txt"
$results | Format-Table -AutoSize | Out-String | Set-Content -Path $summaryPath -Encoding UTF8

Write-Host "Full logs: $logDir"
if ($overallFailed -gt 0) {
    Write-Host "$overallFailed of $($results.Count) batches had a non-zero exit code - check their logs above." -ForegroundColor Yellow
} else {
    Write-Host "All $($results.Count) batches completed with exit code 0 (xfail/xpass is reported inside each batch's summary line, not as a failing exit code unless strict=True)." -ForegroundColor Green
}
