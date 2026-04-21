#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [ValidateSet("check", "record-refresh", "complete-refresh", "mark-dirty", "clear-dirty")]
    [string]$Command = "check",
    [string]$Reason = ""
)

. (Join-Path $PSScriptRoot "common.ps1")

if (-not $RepoRoot) {
    $RepoRoot = Get-RepoRoot
}

$projectMapDir = Get-ProjectMapDir -RepoRoot $RepoRoot
$statusPath = Get-ProjectMapStatusPath -RepoRoot $RepoRoot
$canonicalMapFiles = @(
    (Join-Path $RepoRoot "PROJECT-HANDBOOK.md"),
    (Join-Path $RepoRoot ".specify/project-map/ARCHITECTURE.md"),
    (Join-Path $RepoRoot ".specify/project-map/STRUCTURE.md"),
    (Join-Path $RepoRoot ".specify/project-map/CONVENTIONS.md"),
    (Join-Path $RepoRoot ".specify/project-map/INTEGRATIONS.md"),
    (Join-Path $RepoRoot ".specify/project-map/WORKFLOWS.md"),
    (Join-Path $RepoRoot ".specify/project-map/TESTING.md"),
    (Join-Path $RepoRoot ".specify/project-map/OPERATIONS.md")
)
New-Item -ItemType Directory -Path $projectMapDir -Force | Out-Null

function Assert-CanonicalMapFiles {
    $missing = @($canonicalMapFiles | Where-Object { -not (Test-Path -LiteralPath $_) })
    if (-not $missing -or $missing.Count -eq 0) {
        return
    }

    Write-Error "Cannot record a fresh project-map baseline because canonical map files are missing:`n - $($missing -join "`n - ")`nRun map-codebase first so PROJECT-HANDBOOK.md and .specify/project-map/*.md exist."
    exit 1
}

function Get-IsoNow {
    return [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
}

function Get-HeadCommit {
    if (Test-HasGit) {
        try {
            $value = git -C $RepoRoot rev-parse HEAD 2>$null
            if ($LASTEXITCODE -eq 0) { return $value }
        } catch {}
    }
    return ""
}

function Get-BranchName {
    if (Test-HasGit) {
        try {
            $value = git -C $RepoRoot rev-parse --abbrev-ref HEAD 2>$null
            if ($LASTEXITCODE -eq 0) { return $value }
        } catch {}
    }
    return ""
}

function Read-Status {
    if (-not (Test-Path -LiteralPath $statusPath)) {
        return @{}
    }
    try {
        $raw = Get-Content -LiteralPath $statusPath -Raw -ErrorAction Stop
        $parsed = $raw | ConvertFrom-Json -ErrorAction Stop
        $result = @{}
        foreach ($prop in $parsed.PSObject.Properties) {
            $result[$prop.Name] = $prop.Value
        }
        return $result
    } catch {
        return @{}
    }
}

function Get-StatusValue {
    param(
        [hashtable]$Status,
        [string]$Key,
        $Default = $null
    )

    if ($null -ne $Status -and $Status.ContainsKey($Key)) {
        return $Status[$Key]
    }
    return $Default
}

function Write-Status {
    param(
        [string]$LastMappedCommit,
        [string]$LastMappedAt,
        [string]$LastMappedBranch,
        [string]$Freshness,
        [string]$LastRefreshReason,
        [bool]$Dirty,
        [string[]]$DirtyReasons
    )

    $payload = [ordered]@{
        version = 1
        last_mapped_commit = $LastMappedCommit
        last_mapped_at = $LastMappedAt
        last_mapped_branch = $LastMappedBranch
        freshness = $Freshness
        last_refresh_reason = $LastRefreshReason
        dirty = $Dirty
        dirty_reasons = @($DirtyReasons)
    }

    $payload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statusPath -Encoding utf8
}

function Classify-Path {
    param([string]$Path)

    $lower = $Path.ToLowerInvariant()

    switch -Regex ($lower) {
        '^\.specify/project-map/status\.json$' { return "ignore" }
        '^project-handbook\.md$' { return "stale" }
        '^\.specify/project-map/' { return "stale" }
        '^\.specify/templates/project-map/' { return "stale" }
        '^\.specify/templates/project-handbook-template\.md$' { return "stale" }
        '^\.specify/memory/constitution\.md$' { return "stale" }
        '^\.specify/extensions\.yml$' { return "stale" }
        '^\.github/workflows/' { return "stale" }
        '^(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|pyproject\.toml|poetry\.lock|go\.mod|go\.sum|cargo\.toml|cargo\.lock|composer\.json|composer\.lock|gemfile|gemfile\.lock|dockerfile|docker-compose\.ya?ml|makefile)$' { return "stale" }
        '(^|/)(route|routes|router|routing|url|urls|endpoint|endpoints|api|schema|schemas|contract|contracts|type|types|interface|interfaces|registry|registries|manifest|manifests|config|configs|settings|workflow|workflows|command|commands|integration|integrations|adapter|adapters|middleware|export|exports|index)(/|\.|$)' { return "stale" }
        '(^|/)(src|app|apps|server|client|web|ui|frontend|backend|lib|libs|scripts|tests|docs|specs)(/|$)' { return "possibly_stale" }
        default { return "ignore" }
    }
}

function Emit-CheckResult {
    param(
        [string]$Freshness,
        [string]$HeadCommit,
        [string]$LastMappedCommit,
        [bool]$Dirty,
        [object[]]$DirtyReasons,
        [object[]]$Reasons,
        [object[]]$ChangedFiles
    )

    [ordered]@{
        status_path = $statusPath
        freshness = $Freshness
        head_commit = $HeadCommit
        last_mapped_commit = $LastMappedCommit
        dirty = $Dirty
        dirty_reasons = @($DirtyReasons)
        reasons = @($Reasons)
        changed_files = @($ChangedFiles)
    } | ConvertTo-Json -Depth 6
}

function Invoke-Check {
    $status = Read-Status
    $headCommit = Get-HeadCommit

    if (-not (Test-Path -LiteralPath $statusPath)) {
        Emit-CheckResult -Freshness "missing" -HeadCommit $headCommit -LastMappedCommit "" -Dirty $false -DirtyReasons @() -Reasons @("project-map status missing") -ChangedFiles @()
        return
    }

    $lastMappedCommit = [string](Get-StatusValue -Status $status -Key "last_mapped_commit" -Default "")
    $dirty = [bool](Get-StatusValue -Status $status -Key "dirty" -Default $false)
    $dirtyReasons = @((Get-StatusValue -Status $status -Key "dirty_reasons" -Default @()))

    if ($dirty) {
        Emit-CheckResult -Freshness "stale" -HeadCommit $headCommit -LastMappedCommit $lastMappedCommit -Dirty $true -DirtyReasons $dirtyReasons -Reasons $dirtyReasons -ChangedFiles @()
        return
    }

    if (-not (Test-HasGit) -or [string]::IsNullOrEmpty($lastMappedCommit) -or [string]::IsNullOrEmpty($headCommit)) {
        Emit-CheckResult -Freshness "possibly_stale" -HeadCommit $headCommit -LastMappedCommit $lastMappedCommit -Dirty $false -DirtyReasons $dirtyReasons -Reasons @("git baseline unavailable for project-map freshness") -ChangedFiles @()
        return
    }

    $diffLines = @()
    try {
        $diffLines += @(git -C $RepoRoot diff --name-status --find-renames "$lastMappedCommit..$headCommit" 2>$null)
        $diffLines += @(git -C $RepoRoot diff --name-status --find-renames --cached 2>$null)
        $diffLines += @(git -C $RepoRoot diff --name-status --find-renames 2>$null)
        $diffLines += @((git -C $RepoRoot ls-files --others --exclude-standard 2>$null) | ForEach-Object { "??`t$_" })
        $diffLines = @($diffLines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } catch {
        $diffLines = @()
    }

    if (-not $diffLines -or $diffLines.Count -eq 0) {
        Emit-CheckResult -Freshness "fresh" -HeadCommit $headCommit -LastMappedCommit $lastMappedCommit -Dirty $false -DirtyReasons $dirtyReasons -Reasons @() -ChangedFiles @()
        return
    }

    $worst = "fresh"
    $reasons = New-Object System.Collections.Generic.List[string]
    $changedFiles = New-Object System.Collections.Generic.List[string]

    foreach ($line in $diffLines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split "`t"
        if ($parts.Count -lt 2) { continue }
        $statusCode = $parts[0]
        $candidatePath = if ($statusCode.StartsWith("R") -and $parts.Count -ge 3) { $parts[2] } else { $parts[1] }
        $changedFiles.Add($candidatePath)
        $classification = Classify-Path -Path $candidatePath
        if ($classification -eq "stale") {
            $worst = "stale"
            $reasons.Add("high-impact project-map change: $candidatePath")
        } elseif ($classification -eq "possibly_stale" -and $worst -ne "stale") {
            $worst = "possibly_stale"
            $reasons.Add("codebase surface changed since last map: $candidatePath")
        }
    }

    Emit-CheckResult -Freshness $worst -HeadCommit $headCommit -LastMappedCommit $lastMappedCommit -Dirty $false -DirtyReasons $dirtyReasons -Reasons $reasons -ChangedFiles $changedFiles
}

switch ($Command) {
    "check" {
        Invoke-Check
    }
    "record-refresh" {
        $why = if ($Reason) { $Reason } else { "manual" }
        Assert-CanonicalMapFiles
        Write-Status -LastMappedCommit (Get-HeadCommit) -LastMappedAt (Get-IsoNow) -LastMappedBranch (Get-BranchName) -Freshness "fresh" -LastRefreshReason $why -Dirty $false -DirtyReasons @()
        Invoke-Check
    }
    "complete-refresh" {
        $why = if ($Reason) { $Reason } else { "map-codebase" }
        Assert-CanonicalMapFiles
        Write-Status -LastMappedCommit (Get-HeadCommit) -LastMappedAt (Get-IsoNow) -LastMappedBranch (Get-BranchName) -Freshness "fresh" -LastRefreshReason $why -Dirty $false -DirtyReasons @()
        Invoke-Check
    }
    "mark-dirty" {
        $status = Read-Status
        $dirtyReasons = New-Object System.Collections.Generic.List[string]
        foreach ($item in @((Get-StatusValue -Status $status -Key "dirty_reasons" -Default @()))) {
            if (-not [string]::IsNullOrWhiteSpace([string]$item)) {
                $dirtyReasons.Add([string]$item)
            }
        }
        $why = if ($Reason) { $Reason } else { "project-map-dirty" }
        if ($dirtyReasons -notcontains $why) {
            $dirtyReasons.Add($why)
        }
        $lastMappedAt = [string](Get-StatusValue -Status $status -Key "last_mapped_at" -Default "")
        if (-not $lastMappedAt) { $lastMappedAt = Get-IsoNow }
        Write-Status -LastMappedCommit ([string](Get-StatusValue -Status $status -Key "last_mapped_commit" -Default "")) -LastMappedAt $lastMappedAt -LastMappedBranch ([string](Get-StatusValue -Status $status -Key "last_mapped_branch" -Default "")) -Freshness "stale" -LastRefreshReason ([string](Get-StatusValue -Status $status -Key "last_refresh_reason" -Default "manual")) -Dirty $true -DirtyReasons $dirtyReasons
        Invoke-Check
    }
    "clear-dirty" {
        $status = Read-Status
        Write-Status -LastMappedCommit ([string](Get-StatusValue -Status $status -Key "last_mapped_commit" -Default "")) -LastMappedAt ([string](Get-StatusValue -Status $status -Key "last_mapped_at" -Default "")) -LastMappedBranch ([string](Get-StatusValue -Status $status -Key "last_mapped_branch" -Default "")) -Freshness "fresh" -LastRefreshReason ([string](Get-StatusValue -Status $status -Key "last_refresh_reason" -Default "manual")) -Dirty $false -DirtyReasons @()
        Invoke-Check
    }
}
