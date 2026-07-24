#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [ValidateSet("check", "status", "record-refresh", "complete-refresh", "mark-dirty", "clear-dirty", "refresh-topics")]
    [string]$Command = "check",
    [string]$Reason = "",
    [string]$OriginCommand = "",
    [string]$OriginFeatureDir = "",
    [string]$OriginLaneId = "",
    [string]$DirtyScopePathsJson = "[]"
)

. "$PSScriptRoot/common.ps1"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Get-RepoRoot
}

function Get-SpecifyRuntimeBin {
    $configPath = Join-Path $RepoRoot ".specify/config.json"
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        try {
            $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
            $configured = $config.runtime_launcher.argv[0]
            if (-not [string]::IsNullOrWhiteSpace($configured)) {
                $normalized = $configured.Replace('\', '/')
                if ($normalized.StartsWith('./')) {
                    $normalized = $normalized.Substring(2)
                }
                $prefix = '.specify/bin/'
                if (-not $normalized.StartsWith($prefix)) {
                    throw "runtime_launcher must use the project-local .specify/bin entrypoint"
                }
                $executableName = $normalized.Substring($prefix.Length)
                if ([string]::IsNullOrWhiteSpace($executableName) -or $executableName.Contains('/') -or $executableName -in @('.', '..')) {
                    throw "runtime_launcher must name one executable directly under .specify/bin"
                }
                $configured = Join-Path $RepoRoot $normalized
                if (Test-Path -LiteralPath $configured -PathType Leaf) {
                    return (Resolve-Path -LiteralPath $configured).Path
                }
            }
        } catch {
            # Invalid launcher config falls through only to the canonical project-local entrypoint.
        }
    }

    foreach ($runtimeName in @('specify-runtime.exe', 'specify-runtime')) {
        $projectRuntime = Join-Path $RepoRoot ".specify/bin/$runtimeName"
        if (Test-Path -LiteralPath $projectRuntime -PathType Leaf) {
            return (Resolve-Path -LiteralPath $projectRuntime).Path
        }
    }

    Write-Error "Cannot run project cognition: the project-local .specify/bin/specify-runtime.exe binding is unavailable. A human must rerun the trusted Specify bootstrap/upgrade flow; agent helpers do not fall back to SPECIFY_RUNTIME_BIN or PATH."
    exit 127
}

function Invoke-ProjectCognition {
    param([string[]]$ProjectCognitionArgs)

    $specifyRuntime = Get-SpecifyRuntimeBin

    Push-Location -LiteralPath $RepoRoot
    try {
        & $specifyRuntime cognition @ProjectCognitionArgs
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    } finally {
        Pop-Location
    }
}

function ConvertFrom-DirtyScopePathsJson {
    param([Parameter(Mandatory=$true)][string]$Json)

    $trimmed = $Json.Trim()
    if (-not $trimmed.StartsWith("[")) {
        throw "Dirty scope paths JSON must be an array of non-empty single-line strings."
    }

    try {
        $parsed = $Json | ConvertFrom-Json -ErrorAction Stop
    } catch {
        throw "Dirty scope paths JSON is invalid: $($_.Exception.Message)"
    }

    foreach ($item in @($parsed)) {
        if ($item -isnot [string] -or [string]::IsNullOrWhiteSpace($item) -or $item.Contains("`n") -or $item.Contains("`r")) {
            throw "Dirty scope paths JSON must be an array of non-empty single-line strings."
        }
        Write-Output $item
    }
}

switch ($Command) {
    "check" {
        Invoke-ProjectCognition -ProjectCognitionArgs @("check", "--format", "json")
    }
    "status" {
        Invoke-ProjectCognition -ProjectCognitionArgs @("status", "--format", "json")
    }
    "record-refresh" {
        $refreshReason = if ([string]::IsNullOrWhiteSpace($Reason)) { "manual" } else { $Reason }
        Invoke-ProjectCognition -ProjectCognitionArgs @("record-refresh", "--reason", $refreshReason, "--format", "json")
    }
    "complete-refresh" {
        Invoke-ProjectCognition -ProjectCognitionArgs @("complete-refresh", "--format", "json")
    }
    "mark-dirty" {
        if ([string]::IsNullOrWhiteSpace($Reason)) {
            Write-Error "mark-dirty requires a reason."
            exit 1
        }
        $commandArgs = @("mark-dirty", "--reason", $Reason)
        if (-not [string]::IsNullOrWhiteSpace($OriginCommand)) {
            $commandArgs += @("--origin-command", $OriginCommand)
        }
        if (-not [string]::IsNullOrWhiteSpace($OriginFeatureDir)) {
            $commandArgs += @("--origin-feature-dir", $OriginFeatureDir)
        }
        if (-not [string]::IsNullOrWhiteSpace($OriginLaneId)) {
            $commandArgs += @("--origin-lane-id", $OriginLaneId)
        }
        try {
            $dirtyScopePaths = @(ConvertFrom-DirtyScopePathsJson -Json $DirtyScopePathsJson)
        } catch {
            Write-Error $_.Exception.Message
            exit 2
        }
        foreach ($scopePath in $dirtyScopePaths) {
            $commandArgs += @("--scope", $scopePath)
        }
        $commandArgs += @("--format", "json")
        Invoke-ProjectCognition -ProjectCognitionArgs $commandArgs
    }
    "clear-dirty" {
        Invoke-ProjectCognition -ProjectCognitionArgs @("clear-dirty", "--format", "json")
    }
    "refresh-topics" {
        if ([string]::IsNullOrWhiteSpace($Reason)) {
            Write-Error "refresh-topics requires comma-separated topic names in -Reason."
            exit 1
        }
        $topics = @($Reason -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        Invoke-ProjectCognition -ProjectCognitionArgs (@("refresh-topics") + $topics + @("--format", "json"))
    }
}
