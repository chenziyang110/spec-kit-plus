#!/usr/bin/env pwsh
param(
    [string]$ProjectRoot = ".",
    [ValidateSet("init", "list", "status", "resume-context", "checkpoint", "write-handoff", "validate-handoff", "mark-ready", "mark-consumed", "close", "archive", "rebuild-index")]
    [string]$Mode = "list",
    [string]$Slug = "",
    [string]$Value = "",
    [string]$IncludeAll = "false"
)

$sharedHelper = Join-Path $PSScriptRoot "../shared/discussion-state.py"
if (-not (Test-Path $sharedHelper)) {
    Write-Error "shared discussion helper not found: $sharedHelper"
    exit 1
}

$pythonBin = if ($env:SPECIFY_PYTHON) { $env:SPECIFY_PYTHON } else { "python" }
& $pythonBin $sharedHelper $ProjectRoot $Mode $Slug $Value $IncludeAll
exit $LASTEXITCODE
