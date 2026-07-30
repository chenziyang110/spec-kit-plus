#!/usr/bin/env pwsh
param(
    [string]$ProjectRoot = ".",
    [ValidateSet("init", "status", "init-scan", "status-scan", "finalize", "finalize-scan", "status-build")]
    [string]$Mode = "status",
    [string]$RunSlug = ""
)

$runtimeBin = $env:SPECIFY_RUNTIME_BIN
if (-not $runtimeBin) {
    $runtimeCandidates = @(
        (Join-Path $ProjectRoot ".specify/bin/specify-runtime.exe"),
        (Join-Path $ProjectRoot ".specify/bin/specify-runtime")
    )
    $runtimeBin = $runtimeCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if (-not $runtimeBin) {
    $runtimeCommand = Get-Command specify-runtime -ErrorAction SilentlyContinue
    if ($runtimeCommand) {
        $runtimeBin = $runtimeCommand.Source
    }
}
if (-not $runtimeBin) {
    Write-Error "specify-runtime not found; install the project-local runtime first"
    exit 1
}

if ($Mode -eq "status-build") {
    & $runtimeBin prd-build status-build $RunSlug --project-root $ProjectRoot --format json
} else {
    & $runtimeBin prd-scan $Mode $RunSlug --project-root $ProjectRoot --format json
}
exit $LASTEXITCODE
