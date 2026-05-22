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

    $projectCognition = Get-Command project-cognition -ErrorAction SilentlyContinue
    if ($projectCognition) {
        return $projectCognition.Source
    }

    Write-Error "Cannot run project-cognition: set PROJECT_COGNITION_BIN or install project-cognition on PATH."
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
