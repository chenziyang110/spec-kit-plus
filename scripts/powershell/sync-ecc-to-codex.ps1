[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateSet('project', 'user')]
    [string]$Scope,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AdditionalArgs = @()
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Resolve-WorkspaceRoot {
    param(
        [string]$StartDir
    )

    $current = $StartDir
    while ($true) {
        if (Test-Path (Join-Path $current 'extensions\agent-teams\engine\package.json') -PathType Leaf) {
            return $current
        }
        if ((Test-Path (Join-Path $current '.specify')) -or (Test-Path (Join-Path $current 'pyproject.toml') -PathType Leaf)) {
            return $current
        }

        $parent = Split-Path -Parent $current
        if (-not $parent -or $parent -eq $current) {
            break
        }
        $current = $parent
    }

    return (Get-Location).Path
}

$repoRoot = Resolve-WorkspaceRoot -StartDir $scriptDir
$engineDir = Join-Path $repoRoot 'extensions\agent-teams\engine'
$distCli = Join-Path $engineDir 'dist\cli\index.js'

function Show-Usage {
    @'
Refresh Codex config and managed MCP servers using the bundled Specify runtime setup flow.

Usage:
  scripts/powershell/sync-ecc-to-codex.ps1 [-DryRun] [-Scope project|user] [additional runtime setup args]

Examples:
  scripts/powershell/sync-ecc-to-codex.ps1 -DryRun
  scripts/powershell/sync-ecc-to-codex.ps1 -Scope project
'@
}

if ($AdditionalArgs -contains '--help' -or $AdditionalArgs -contains '-h') {
    Show-Usage
    exit 0
}

$setupArgs = @('setup')
if ($DryRun) {
    $setupArgs += '--dry-run'
}
if ($Scope) {
    $setupArgs += @('--scope', $Scope)
}
if ($AdditionalArgs.Count -gt 0) {
    $setupArgs += $AdditionalArgs
}

$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCommand) {
    throw "node is required to run the bundled Specify runtime setup."
}

if (-not (Test-Path (Join-Path $engineDir 'package.json') -PathType Leaf)) {
    throw "No bundled runtime engine checkout was found near $repoRoot."
}

if (-not (Test-Path $distCli -PathType Leaf)) {
    $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npmCommand) {
        throw "Bundled runtime CLI is not built and npm is unavailable to build it."
    }

    Write-Host "Bundled runtime CLI not built; running npm build first..."
    & $npmCommand.Source --prefix $engineDir run build | Out-Null
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

& $nodeCommand.Source $distCli @setupArgs
exit $LASTEXITCODE
