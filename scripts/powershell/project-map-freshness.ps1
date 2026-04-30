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
$legacyStatusPath = Get-LegacyProjectMapStatusPath -RepoRoot $RepoRoot
$canonicalMapFiles = @(
    (Join-Path $RepoRoot "PROJECT-HANDBOOK.md"),
    (Join-Path $RepoRoot ".specify/project-map/index/atlas-index.json"),
    (Join-Path $RepoRoot ".specify/project-map/index/modules.json"),
    (Join-Path $RepoRoot ".specify/project-map/index/relations.json"),
    (Join-Path $RepoRoot ".specify/project-map/root/ARCHITECTURE.md"),
    (Join-Path $RepoRoot ".specify/project-map/root/STRUCTURE.md"),
    (Join-Path $RepoRoot ".specify/project-map/root/CONVENTIONS.md"),
    (Join-Path $RepoRoot ".specify/project-map/root/INTEGRATIONS.md"),
    (Join-Path $RepoRoot ".specify/project-map/root/WORKFLOWS.md"),
    (Join-Path $RepoRoot ".specify/project-map/root/TESTING.md"),
    (Join-Path $RepoRoot ".specify/project-map/root/OPERATIONS.md")
)
New-Item -ItemType Directory -Path $projectMapDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $statusPath) -Force | Out-Null

function Get-StatusReadPath {
    if (Test-Path -LiteralPath $statusPath) {
        return $statusPath
    }
    if (Test-Path -LiteralPath $legacyStatusPath) {
        return $legacyStatusPath
    }
    return $statusPath
}

function Assert-CanonicalMapFiles {
    $missing = @($canonicalMapFiles | Where-Object { -not (Test-Path -LiteralPath $_) })
    if (-not $missing -or $missing.Count -eq 0) {
        return
    }

    Write-Error "Cannot record a fresh project-map baseline because canonical map files are missing:`n - $($missing -join "`n - ")`nRun /sp-map-scan, then /sp-map-build first so PROJECT-HANDBOOK.md and .specify/project-map/*.md exist."
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
    $readPath = Get-StatusReadPath
    if (-not (Test-Path -LiteralPath $readPath)) {
        return @{}
    }
    try {
        $raw = Get-Content -LiteralPath $readPath -Raw -ErrorAction Stop
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
        [string[]]$LastRefreshTopics,
        [string]$LastRefreshScope,
        [string]$LastRefreshBasis,
        [string[]]$LastRefreshChangedFilesBasis,
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
        last_refresh_topics = @($LastRefreshTopics)
        last_refresh_scope = $LastRefreshScope
        last_refresh_basis = $LastRefreshBasis
        last_refresh_changed_files_basis = @($LastRefreshChangedFilesBasis)
        dirty = $Dirty
        dirty_reasons = @($DirtyReasons)
    }

    $json = $payload | ConvertTo-Json -Depth 5
    $json | Set-Content -LiteralPath $statusPath -Encoding utf8
    if ($legacyStatusPath -ne $statusPath) {
        $json | Set-Content -LiteralPath $legacyStatusPath -Encoding utf8
    }
}

function Classify-Path {
    param([string]$Path)

    $lower = $Path.ToLowerInvariant()

    switch -Regex ($lower) {
        '^\.specify/project-map/status\.json$' { return "ignore" }
        '^\.specify/project-map/index/status\.json$' { return "ignore" }
        '^\.specify/project-map/map-state\.md$' { return "ignore" }
        '^\.specify/project-map/worker-results/' { return "ignore" }
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

function Get-SuggestedTopicsForPath {
    param([string]$Path)

    $plan = Get-RefreshPlanForPath -Path $Path
    $allTopics = New-Object System.Collections.Generic.List[string]
    foreach ($topic in @($plan.must_refresh_topics) + @($plan.review_topics)) {
        if ($allTopics -notcontains $topic) { $allTopics.Add($topic) }
    }
    $ordered = @("ARCHITECTURE.md", "STRUCTURE.md", "CONVENTIONS.md", "INTEGRATIONS.md", "OPERATIONS.md", "WORKFLOWS.md", "TESTING.md")
    return @($ordered | Where-Object { $allTopics -contains $_ })
}

function Get-RefreshPlanForPath {
    param([string]$Path)

    $lower = $Path.ToLowerInvariant().Replace('\', '/')
    $classification = Classify-Path -Path $Path
    if ($classification -eq "ignore") {
        return @{
            must_refresh_topics = @()
            review_topics = @()
        }
    }

    $mustRefresh = New-Object System.Collections.Generic.List[string]
    $review = New-Object System.Collections.Generic.List[string]
    $specificBoundaryHit = $false
    function Add-Topic([System.Collections.Generic.List[string]]$Target, [string[]]$Names) {
        foreach ($name in $Names) {
            if ($Target -notcontains $name) { $Target.Add($name) }
        }
    }

    switch ($lower) {
        "project-handbook.md" { Add-Topic $mustRefresh @("ARCHITECTURE.md") }
        ".specify/project-map/root/architecture.md" { Add-Topic $mustRefresh @("ARCHITECTURE.md") }
        ".specify/project-map/architecture.md" { Add-Topic $mustRefresh @("ARCHITECTURE.md") }
        ".specify/project-map/root/structure.md" { Add-Topic $mustRefresh @("STRUCTURE.md") }
        ".specify/project-map/structure.md" { Add-Topic $mustRefresh @("STRUCTURE.md") }
        ".specify/project-map/root/conventions.md" { Add-Topic $mustRefresh @("CONVENTIONS.md") }
        ".specify/project-map/conventions.md" { Add-Topic $mustRefresh @("CONVENTIONS.md") }
        ".specify/project-map/root/integrations.md" { Add-Topic $mustRefresh @("INTEGRATIONS.md") }
        ".specify/project-map/integrations.md" { Add-Topic $mustRefresh @("INTEGRATIONS.md") }
        ".specify/project-map/root/workflows.md" { Add-Topic $mustRefresh @("WORKFLOWS.md") }
        ".specify/project-map/workflows.md" { Add-Topic $mustRefresh @("WORKFLOWS.md") }
        ".specify/project-map/root/testing.md" { Add-Topic $mustRefresh @("TESTING.md") }
        ".specify/project-map/testing.md" { Add-Topic $mustRefresh @("TESTING.md") }
        ".specify/project-map/root/operations.md" { Add-Topic $mustRefresh @("OPERATIONS.md") }
        ".specify/project-map/operations.md" { Add-Topic $mustRefresh @("OPERATIONS.md") }
    }

    if ($lower -match '(^|/)(route|routes|router|routing|api|endpoint|endpoints|workflow|workflows|command|commands)(/|\.|$)') {
        $specificBoundaryHit = $true
        Add-Topic $mustRefresh @("INTEGRATIONS.md", "WORKFLOWS.md")
        Add-Topic $review @("ARCHITECTURE.md", "TESTING.md")
    }
    if ($lower -match '(^|/)(schema|schemas|contract|contracts|type|types|interface|interfaces|manifest|manifests|adapter|adapters|middleware|export|exports)(/|\.|$)') {
        $specificBoundaryHit = $true
        Add-Topic $mustRefresh @("INTEGRATIONS.md")
        Add-Topic $review @("ARCHITECTURE.md", "TESTING.md")
    }
    if ($lower -match '(^|/)(config|configs|settings)(/|\.|$)' -or $lower -match '(^|/)(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|pyproject\.toml|poetry\.lock|go\.mod|go\.sum|cargo\.toml|cargo\.lock|composer\.json|composer\.lock|gemfile|gemfile\.lock)$') {
        Add-Topic $mustRefresh @("CONVENTIONS.md", "INTEGRATIONS.md", "OPERATIONS.md")
        Add-Topic $review @("TESTING.md")
    }
    if ($lower -match '(^|/)(dockerfile|docker-compose\.yml|docker-compose\.yaml|makefile)$') {
        Add-Topic $mustRefresh @("INTEGRATIONS.md", "OPERATIONS.md")
        Add-Topic $review @("TESTING.md")
    }
    if (-not $specificBoundaryHit -and $lower -match '(^|/)(src|app|apps|server|client|web|ui|frontend|backend|lib|libs)(/|$)') {
        Add-Topic $mustRefresh @("STRUCTURE.md")
        Add-Topic $review @("ARCHITECTURE.md", "TESTING.md")
    }
    if ($lower -match '(^|/)scripts(/|$)') {
        Add-Topic $mustRefresh @("OPERATIONS.md")
        Add-Topic $review @("STRUCTURE.md", "TESTING.md")
    }
    if ($lower -match '(^|/)tests(/|$)') {
        Add-Topic $mustRefresh @("TESTING.md")
        Add-Topic $review @("ARCHITECTURE.md")
    }
    if ($lower -match '(^|/)(docs|specs)(/|$)') {
        Add-Topic $mustRefresh @("WORKFLOWS.md")
        Add-Topic $review @("ARCHITECTURE.md")
    }

    if ($mustRefresh.Count -eq 0 -and $review.Count -eq 0) {
        if ($classification -eq "stale") {
            Add-Topic $mustRefresh @("ARCHITECTURE.md")
            Add-Topic $review @("TESTING.md")
        } elseif ($classification -eq "possibly_stale") {
            Add-Topic $mustRefresh @("STRUCTURE.md")
            Add-Topic $review @("ARCHITECTURE.md", "TESTING.md")
        }
    }

    $ordered = @("ARCHITECTURE.md", "STRUCTURE.md", "CONVENTIONS.md", "INTEGRATIONS.md", "OPERATIONS.md", "WORKFLOWS.md", "TESTING.md")
    return @{
        must_refresh_topics = @($ordered | Where-Object { $mustRefresh -contains $_ })
        review_topics = @($ordered | Where-Object { $review -contains $_ })
    }
}

function Normalize-DirtyReason {
    param([string]$Reason)

    $reasonText = if ($null -ne $Reason) { [string]$Reason } else { "" }
    $normalized = (($reasonText.ToLowerInvariant().Replace("-", " ").Replace("_", " ")) -split '\s+' | Where-Object { $_ }) -join " "
    switch ($normalized) {
        "" { return "project_map_dirty" }
        "shared surface changed" { return "shared_surface_changed" }
        "architecture surface changed" { return "architecture_surface_changed" }
        "integration boundary changed" { return "integration_boundary_changed" }
        "workflow contract changed" { return "workflow_contract_changed" }
        "verification surface changed" { return "verification_surface_changed" }
        "runtime invariant changed" { return "runtime_invariant_changed" }
        default { return ($normalized -replace ' ', '_') }
    }
}

function Get-RefreshPlanForDirtyReason {
    param([string]$Reason)

    switch (Normalize-DirtyReason -Reason $Reason) {
        "shared_surface_changed" {
            return @{ must_refresh_topics = @("ARCHITECTURE.md", "STRUCTURE.md"); review_topics = @("INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md") }
        }
        "architecture_surface_changed" {
            return @{ must_refresh_topics = @("ARCHITECTURE.md"); review_topics = @("STRUCTURE.md", "WORKFLOWS.md", "TESTING.md") }
        }
        "integration_boundary_changed" {
            return @{ must_refresh_topics = @("INTEGRATIONS.md"); review_topics = @("ARCHITECTURE.md", "OPERATIONS.md", "TESTING.md") }
        }
        "workflow_contract_changed" {
            return @{ must_refresh_topics = @("WORKFLOWS.md"); review_topics = @("ARCHITECTURE.md", "INTEGRATIONS.md", "TESTING.md") }
        }
        "verification_surface_changed" {
            return @{ must_refresh_topics = @("TESTING.md"); review_topics = @("ARCHITECTURE.md", "WORKFLOWS.md") }
        }
        "runtime_invariant_changed" {
            return @{ must_refresh_topics = @("OPERATIONS.md"); review_topics = @("INTEGRATIONS.md", "TESTING.md") }
        }
        default {
            return @{ must_refresh_topics = @("ARCHITECTURE.md"); review_topics = @("TESTING.md") }
        }
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
        [object[]]$ChangedFiles,
        [object[]]$SuggestedTopics,
        [object[]]$MustRefreshTopics,
        [object[]]$ReviewTopics
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
        suggested_topics = @($SuggestedTopics)
        must_refresh_topics = @($MustRefreshTopics)
        review_topics = @($ReviewTopics)
    } | ConvertTo-Json -Depth 6
}

function Invoke-Check {
    $status = Read-Status
    $headCommit = Get-HeadCommit

    if (-not (Test-Path -LiteralPath (Get-StatusReadPath))) {
        Emit-CheckResult -Freshness "missing" -HeadCommit $headCommit -LastMappedCommit "" -Dirty $false -DirtyReasons @() -Reasons @("project-map status missing") -ChangedFiles @() -SuggestedTopics @() -MustRefreshTopics @() -ReviewTopics @()
        return
    }

    $lastMappedCommit = [string](Get-StatusValue -Status $status -Key "last_mapped_commit" -Default "")
    $dirty = [bool](Get-StatusValue -Status $status -Key "dirty" -Default $false)
    $dirtyReasons = @((Get-StatusValue -Status $status -Key "dirty_reasons" -Default @()))

    if ($dirty) {
        $mustRefreshTopics = New-Object System.Collections.Generic.List[string]
        $reviewTopics = New-Object System.Collections.Generic.List[string]
        $topicOrder = @("ARCHITECTURE.md", "STRUCTURE.md", "CONVENTIONS.md", "INTEGRATIONS.md", "OPERATIONS.md", "WORKFLOWS.md", "TESTING.md")
        foreach ($reason in $dirtyReasons) {
            $plan = Get-RefreshPlanForDirtyReason -Reason ([string]$reason)
            foreach ($topic in @($plan.must_refresh_topics)) {
                if ($mustRefreshTopics -notcontains $topic) { $mustRefreshTopics.Add($topic) }
            }
            foreach ($topic in @($plan.review_topics)) {
                if ($reviewTopics -notcontains $topic) { $reviewTopics.Add($topic) }
            }
        }
        $orderedMustRefreshTopics = @($topicOrder | Where-Object { $mustRefreshTopics -contains $_ })
        $orderedReviewTopics = @($topicOrder | Where-Object { $reviewTopics -contains $_ })
        $suggestedTopics = @($topicOrder | Where-Object { $orderedMustRefreshTopics -contains $_ -or $orderedReviewTopics -contains $_ })
        Emit-CheckResult -Freshness "stale" -HeadCommit $headCommit -LastMappedCommit $lastMappedCommit -Dirty $true -DirtyReasons $dirtyReasons -Reasons $dirtyReasons -ChangedFiles @() -SuggestedTopics $suggestedTopics -MustRefreshTopics $orderedMustRefreshTopics -ReviewTopics $orderedReviewTopics
        return
    }

    if (-not (Test-HasGit) -or [string]::IsNullOrEmpty($lastMappedCommit) -or [string]::IsNullOrEmpty($headCommit)) {
        Emit-CheckResult -Freshness "possibly_stale" -HeadCommit $headCommit -LastMappedCommit $lastMappedCommit -Dirty $false -DirtyReasons $dirtyReasons -Reasons @("git baseline unavailable for project-map freshness") -ChangedFiles @() -SuggestedTopics @() -MustRefreshTopics @() -ReviewTopics @()
        return
    }

    $diffLines = @()
    try {
        $diffLines += @(git -C $RepoRoot diff --ignore-cr-at-eol --name-status --find-renames "$lastMappedCommit..$headCommit" 2>$null)
        $diffLines += @(git -C $RepoRoot diff --ignore-cr-at-eol --name-status --find-renames --cached 2>$null)
        $diffLines += @(git -C $RepoRoot diff --ignore-cr-at-eol --name-status --find-renames 2>$null)
        $diffLines += @((git -C $RepoRoot ls-files --others --exclude-standard 2>$null) | ForEach-Object { "??`t$_" })
        $diffLines = @($diffLines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    } catch {
        $diffLines = @()
    }

    if (-not $diffLines -or $diffLines.Count -eq 0) {
        Emit-CheckResult -Freshness "fresh" -HeadCommit $headCommit -LastMappedCommit $lastMappedCommit -Dirty $false -DirtyReasons $dirtyReasons -Reasons @() -ChangedFiles @() -SuggestedTopics @() -MustRefreshTopics @() -ReviewTopics @()
        return
    }

    $worst = "fresh"
    $reasons = New-Object System.Collections.Generic.List[string]
    $changedFiles = New-Object System.Collections.Generic.List[string]
    $suggestedTopics = New-Object System.Collections.Generic.List[string]
    $mustRefreshTopics = New-Object System.Collections.Generic.List[string]
    $reviewTopics = New-Object System.Collections.Generic.List[string]
    $lastRefreshScope = [string](Get-StatusValue -Status $status -Key "last_refresh_scope" -Default "")
    $lastRefreshTopics = @((Get-StatusValue -Status $status -Key "last_refresh_topics" -Default @()))

    foreach ($line in $diffLines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split "`t"
        if ($parts.Count -lt 2) { continue }
        $statusCode = $parts[0]
        $candidatePath = if ($statusCode.StartsWith("R") -and $parts.Count -ge 3) { $parts[2] } else { $parts[1] }
        $candidateLower = $candidatePath.ToLowerInvariant().Replace('\', '/')
        if ($headCommit -eq $lastMappedCommit -and ($candidateLower -eq "project-handbook.md" -or $candidateLower.StartsWith(".specify/project-map/"))) {
            continue
        }
        $changedFiles.Add($candidatePath)
        $plan = Get-RefreshPlanForPath -Path $candidatePath
        $coveredByLastRefresh = $false
        if ($lastRefreshScope -eq "partial") {
            $neededTopics = @($plan.must_refresh_topics) + @($plan.review_topics)
            if (@($neededTopics | Where-Object { $lastRefreshTopics -notcontains $_ }).Count -eq 0) {
                $coveredByLastRefresh = $true
                $plan = @{
                    must_refresh_topics = @()
                    review_topics = @("ARCHITECTURE.md", "STRUCTURE.md", "CONVENTIONS.md", "INTEGRATIONS.md", "OPERATIONS.md", "WORKFLOWS.md", "TESTING.md" | Where-Object { $neededTopics -contains $_ })
                }
            }
        }
        foreach ($topic in @($plan.must_refresh_topics)) {
            if ($mustRefreshTopics -notcontains $topic) { $mustRefreshTopics.Add($topic) }
        }
        foreach ($topic in @($plan.review_topics)) {
            if ($reviewTopics -notcontains $topic) { $reviewTopics.Add($topic) }
        }
        foreach ($topic in @(Get-SuggestedTopicsForPath -Path $candidatePath)) {
            if ($suggestedTopics -notcontains $topic) {
                $suggestedTopics.Add($topic)
            }
        }
        $classification = Classify-Path -Path $candidatePath
        if ($classification -eq "stale") {
            $worst = "stale"
            $reasons.Add("high-impact project-map change: $candidatePath")
        } elseif ($classification -eq "possibly_stale" -and $worst -ne "stale") {
            $worst = "possibly_stale"
            if ($coveredByLastRefresh) {
                $reasons.Add("covered topic changed since last partial map: $candidatePath")
            } else {
                $reasons.Add("codebase surface changed since last map: $candidatePath")
            }
        }
    }

    Emit-CheckResult -Freshness $worst -HeadCommit $headCommit -LastMappedCommit $lastMappedCommit -Dirty $false -DirtyReasons $dirtyReasons -Reasons $reasons -ChangedFiles $changedFiles -SuggestedTopics $suggestedTopics -MustRefreshTopics $mustRefreshTopics -ReviewTopics $reviewTopics
}

switch ($Command) {
    "check" {
        Invoke-Check
    }
    "record-refresh" {
        $why = if ($Reason) { $Reason } else { "manual" }
        Assert-CanonicalMapFiles
        Write-Status -LastMappedCommit (Get-HeadCommit) -LastMappedAt (Get-IsoNow) -LastMappedBranch (Get-BranchName) -Freshness "fresh" -LastRefreshReason $why -LastRefreshTopics @("ARCHITECTURE.md","STRUCTURE.md","CONVENTIONS.md","INTEGRATIONS.md","OPERATIONS.md","WORKFLOWS.md","TESTING.md") -LastRefreshScope "full" -LastRefreshBasis $why -LastRefreshChangedFilesBasis @() -Dirty $false -DirtyReasons @()
        Invoke-Check
    }
    "complete-refresh" {
        $why = if ($Reason) { $Reason } else { "map-build" }
        Assert-CanonicalMapFiles
        Write-Status -LastMappedCommit (Get-HeadCommit) -LastMappedAt (Get-IsoNow) -LastMappedBranch (Get-BranchName) -Freshness "fresh" -LastRefreshReason $why -LastRefreshTopics @("ARCHITECTURE.md","STRUCTURE.md","CONVENTIONS.md","INTEGRATIONS.md","OPERATIONS.md","WORKFLOWS.md","TESTING.md") -LastRefreshScope "full" -LastRefreshBasis $why -LastRefreshChangedFilesBasis @() -Dirty $false -DirtyReasons @()
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
        $rawReason = if ($Reason) { $Reason } else { "project-map-dirty" }
        $why = Normalize-DirtyReason -Reason $rawReason
        if ($dirtyReasons -notcontains $why) {
            $dirtyReasons.Add($why)
        }
        $lastMappedAt = [string](Get-StatusValue -Status $status -Key "last_mapped_at" -Default "")
        if (-not $lastMappedAt) { $lastMappedAt = Get-IsoNow }
        Write-Status -LastMappedCommit ([string](Get-StatusValue -Status $status -Key "last_mapped_commit" -Default "")) -LastMappedAt $lastMappedAt -LastMappedBranch ([string](Get-StatusValue -Status $status -Key "last_mapped_branch" -Default "")) -Freshness "stale" -LastRefreshReason ([string](Get-StatusValue -Status $status -Key "last_refresh_reason" -Default "manual")) -LastRefreshTopics @((Get-StatusValue -Status $status -Key "last_refresh_topics" -Default @())) -LastRefreshScope ([string](Get-StatusValue -Status $status -Key "last_refresh_scope" -Default "full")) -LastRefreshBasis ([string](Get-StatusValue -Status $status -Key "last_refresh_basis" -Default "manual")) -LastRefreshChangedFilesBasis @((Get-StatusValue -Status $status -Key "last_refresh_changed_files_basis" -Default @())) -Dirty $true -DirtyReasons $dirtyReasons
        Invoke-Check
    }
    "clear-dirty" {
        $status = Read-Status
        Write-Status -LastMappedCommit ([string](Get-StatusValue -Status $status -Key "last_mapped_commit" -Default "")) -LastMappedAt ([string](Get-StatusValue -Status $status -Key "last_mapped_at" -Default "")) -LastMappedBranch ([string](Get-StatusValue -Status $status -Key "last_mapped_branch" -Default "")) -Freshness "fresh" -LastRefreshReason ([string](Get-StatusValue -Status $status -Key "last_refresh_reason" -Default "manual")) -LastRefreshTopics @((Get-StatusValue -Status $status -Key "last_refresh_topics" -Default @())) -LastRefreshScope ([string](Get-StatusValue -Status $status -Key "last_refresh_scope" -Default "full")) -LastRefreshBasis ([string](Get-StatusValue -Status $status -Key "last_refresh_basis" -Default "manual")) -LastRefreshChangedFilesBasis @((Get-StatusValue -Status $status -Key "last_refresh_changed_files_basis" -Default @())) -Dirty $false -DirtyReasons @()
        Invoke-Check
    }
}
