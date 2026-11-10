# Update project context for Factory Droid through the shared renderer.
$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$fsRoot = [System.IO.Path]::GetPathRoot($repoRoot)
while ($repoRoot -and $repoRoot -ne $fsRoot -and -not (Test-Path (Join-Path $repoRoot '.specify'))) {
    $repoRoot = Split-Path -Parent $repoRoot
}

& "$repoRoot/.specify/scripts/powershell/update-agent-context.ps1" -AgentType droid
