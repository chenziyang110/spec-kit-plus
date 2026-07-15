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

function Get-ProjectCognitionBin {
    if (-not [string]::IsNullOrWhiteSpace($env:PROJECT_COGNITION_BIN)) {
        return $env:PROJECT_COGNITION_BIN
    }

    $configPath = Join-Path $RepoRoot ".specify/config.json"
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        try {
            $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
            $configured = $config.project_cognition_launcher.argv[0]
            if (-not [string]::IsNullOrWhiteSpace($configured)) {
                if (-not [System.IO.Path]::IsPathRooted($configured)) {
                    $configured = Join-Path $RepoRoot $configured
                }
                if (Test-Path -LiteralPath $configured -PathType Leaf) {
                    return (Resolve-Path -LiteralPath $configured).Path
                }
            }
        } catch {
            # Invalid launcher config falls through to PATH and deterministic repair guidance.
        }
    }

    $projectCognition = Get-Command project-cognition -ErrorAction SilentlyContinue
    if ($projectCognition) {
        return $projectCognition.Source
    }

    Write-Error "Cannot run project-cognition: no usable project_cognition_launcher is pinned in .specify/config.json. Run the project-pinned Specify launcher with 'check', then 'integration repair'. Do not probe 'specify cognition' or 'specify project-cognition'."
    exit 127
}

function Invoke-ProjectCognition {
    param([string[]]$ProjectCognitionArgs)

    $projectCognition = Get-ProjectCognitionBin

    Push-Location -LiteralPath $RepoRoot
    try {
        & $projectCognition @ProjectCognitionArgs
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
