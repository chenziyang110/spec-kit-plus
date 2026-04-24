#!/usr/bin/env pwsh
$scriptDir = Split-Path $MyInvocation.MyCommand.Definition -Parent
$entry = Join-Path $scriptDir "..\dist\cli\omx.js"

if (-not (Test-Path $entry)) {
  Write-Error "sp-team: missing runtime entrypoint at $entry"
  exit 1
}

if ($args.Count -eq 0) {
  & node $entry team api --help
  exit $LASTEXITCODE
}

$subcommand = $args[0].ToLowerInvariant()
$remaining = @()
if ($args.Count -gt 1) {
  $remaining = $args[1..($args.Count - 1)]
}

switch ($subcommand) {
  "status" { & node $entry team status @remaining; exit $LASTEXITCODE }
  "await" { & node $entry team await @remaining; exit $LASTEXITCODE }
  "resume" { & node $entry team resume @remaining; exit $LASTEXITCODE }
  "shutdown" { & node $entry team shutdown @remaining; exit $LASTEXITCODE }
  default { & node $entry team api @args; exit $LASTEXITCODE }
}
