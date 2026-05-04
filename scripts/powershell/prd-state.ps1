#!/usr/bin/env pwsh
param(
    [string]$ProjectRoot = ".",
    [ValidateSet("init", "status", "init-scan", "status-scan", "status-build")]
    [string]$Mode = "status",
    [string]$RunSlug = ""
)

$sharedHelper = Join-Path $PSScriptRoot "../shared/prd-state.py"
if (-not (Test-Path $sharedHelper)) {
    Write-Error "shared PRD helper not found: $sharedHelper"
    exit 1
}

$pythonBin = if ($env:SPECIFY_PYTHON) { $env:SPECIFY_PYTHON } else { "python" }
& $pythonBin $sharedHelper $ProjectRoot $Mode $RunSlug
exit $LASTEXITCODE
