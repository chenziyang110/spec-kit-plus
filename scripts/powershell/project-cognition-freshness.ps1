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

$ConfigPath = Join-Path $RepoRoot ".specify/config.json"

function Get-SpecifyLauncherArgv {
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        return @()
    }

    try {
        $payload = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    } catch {
        return @()
    }

    if (-not $payload.specify_launcher -or -not $payload.specify_launcher.argv) {
        return @()
    }

    $argv = @($payload.specify_launcher.argv | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    return $argv
}

function Invoke-ProjectCognition {
    param([string[]]$ProjectCognitionArgs)

    $launcher = @(Get-SpecifyLauncherArgv)
    if ($launcher.Count -eq 0) {
        $pathSpecify = Get-Command specify -ErrorAction SilentlyContinue
        if (-not $pathSpecify) {
            Write-Error "Cannot run project-cognition: no specify launcher is configured in .specify/config.json and PATH specify is unavailable."
            exit 127
        }
        $launcher = @("specify")
    }

    Push-Location -LiteralPath $RepoRoot
    try {
        $launcherArgs = @()
        if ($launcher.Count -gt 1) {
            $launcherArgs = @($launcher[1..($launcher.Count - 1)])
        }
        & $launcher[0] @launcherArgs project-cognition @ProjectCognitionArgs
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    } finally {
        Pop-Location
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
