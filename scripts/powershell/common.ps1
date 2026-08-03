#!/usr/bin/env pwsh
# Common PowerShell functions analogous to common.sh

# Find repository root by searching upward for .specify directory
# This is the primary marker for spec-kit projects
function Find-SpecifyRoot {
    param([string]$StartDir = (Get-Location).Path)

    # Normalize to absolute path to prevent issues with relative paths
    # Use -LiteralPath to handle paths with wildcard characters ([, ], *, ?)
    $resolved = Resolve-Path -LiteralPath $StartDir -ErrorAction SilentlyContinue
    $current = if ($resolved) { $resolved.Path } else { $null }
    if (-not $current) { return $null }

    while ($true) {
        if (Test-Path -LiteralPath (Join-Path $current ".specify") -PathType Container) {
            return $current
        }
        $parent = Split-Path $current -Parent
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $current) {
            return $null
        }
        $current = $parent
    }
}

# Get repository root, prioritizing .specify directory over git
# This prevents using a parent git repo when spec-kit is initialized in a subdirectory
function Get-RepoRoot {
    # First, look for .specify directory (spec-kit's own marker)
    $specifyRoot = Find-SpecifyRoot
    if ($specifyRoot) {
        return $specifyRoot
    }

    # Fallback to git if no .specify found
    try {
        $result = git rev-parse --show-toplevel 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $result
        }
    } catch {
        # Git command failed
    }

    # Final fallback to script location for non-git repos
    # Use -LiteralPath to handle paths with wildcard characters
    return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../../..")).Path
}

# Feature roots are ordered by current preference first, then compatibility fallbacks.
function Get-FeatureSpecsRoots {
    param([string]$RepoRoot)

    @(
        (Join-Path $RepoRoot ".specify/features")
        (Join-Path $RepoRoot "specs")
        (Join-Path $RepoRoot ".specify/specs")
    )
}

function Get-CurrentBranch {
    # First check if SPECIFY_FEATURE environment variable is set
    if ($env:SPECIFY_FEATURE) {
        return $env:SPECIFY_FEATURE
    }

    # Then check git if available at the spec-kit root (not parent)
    $repoRoot = Get-RepoRoot
    if (Test-HasGit) {
        try {
            $result = git -C $repoRoot rev-parse --abbrev-ref HEAD 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $result
            }
        } catch {
            # Git command failed
        }
    }

    # For non-git repos, try to find the latest feature directory.
    $latestFeature = ""
    $highest = 0
    $latestDate = ""
    $latestTimestamp = ""
    foreach ($specsDir in (Get-FeatureSpecsRoots -RepoRoot $repoRoot)) {
        if (-not (Test-Path $specsDir)) {
            continue
        }

        Get-ChildItem -Path $specsDir -Directory | ForEach-Object {
            if ($_.Name -match '^(\d{8}-\d{6})-') {
                # Timestamp-based branch: compare lexicographically
                $ts = $matches[1]
                if ($ts -gt $latestTimestamp) {
                    $latestTimestamp = $ts
                    $latestFeature = $_.Name
                }
            } elseif ($_.Name -match '^(\d{4}-\d{2}-\d{2})-') {
                # Date-based branch: compare lexicographically, but prefer timestamp when present.
                $dt = $matches[1]
                if (-not $latestTimestamp -and (($dt -gt $latestDate) -or (($dt -eq $latestDate) -and ($_.Name -gt $latestFeature)))) {
                    $latestDate = $dt
                    $latestFeature = $_.Name
                }
            } elseif ($_.Name -match '^(\d{3,})-') {
                $num = [long]$matches[1]
                if ($num -gt $highest) {
                    $highest = $num
                    # Only update if no timestamp/date branch found yet
                    if (-not $latestTimestamp -and -not $latestDate) {
                        $latestFeature = $_.Name
                    }
                }
            }
        }
    }

    if ($latestFeature) {
        return $latestFeature
    }
    
    # Final fallback
    return "main"
}

# Check if we have git available at the spec-kit root level
# Returns true only if git is installed and the repo root is inside a git work tree
# Handles both regular repos (.git directory) and worktrees/submodules (.git file)
function Test-HasGit {
    # First check if git command is available (before calling Get-RepoRoot which may use git)
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        return $false
    }
    $repoRoot = Get-RepoRoot
    # Check if .git exists (directory or file for worktrees/submodules)
    # Use -LiteralPath to handle paths with wildcard characters
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot ".git"))) {
        return $false
    }
    # Verify it's actually a valid git work tree
    try {
        $null = git -C $repoRoot rev-parse --is-inside-work-tree 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-FeatureBranch {
    param(
        [string]$Branch,
        [bool]$HasGit = $true
    )
    
    # For non-git repos, we can't enforce branch naming but still provide output
    if (-not $HasGit) {
        Write-Warning "[specify] Warning: Git repository not detected; skipped branch validation"
        return $true
    }
    
    # Accept date, timestamp, and legacy sequential prefixes.
    $isDate = $Branch -match '^\d{4}-\d{2}-\d{2}-'

    # Accept sequential prefix (3+ digits) but exclude date/malformed timestamp forms.
    # Malformed: 7-or-8 digit date + 6-digit time with no trailing slug (e.g. "2026031-143022" or "20260319-143022")
    $hasMalformedTimestamp = ($Branch -match '^[0-9]{7}-[0-9]{6}-') -or ($Branch -match '^(?:\d{7}|\d{8})-\d{6}$')
    $isSequential = ($Branch -match '^[0-9]{3,}-') -and (-not $isDate) -and (-not $hasMalformedTimestamp)
    if (-not $isDate -and -not $isSequential -and $Branch -notmatch '^\d{8}-\d{6}-') {
        Write-Output "ERROR: Not on a feature branch. Current branch: $Branch"
        Write-Output "Feature branches should be named like: 2026-06-23-feature-name, 20260319-143022-feature-name, 001-feature-name, or 1234-feature-name"
        return $false
    }
    return $true
}

function Get-FeatureDir {
    param([string]$RepoRoot, [string]$Branch)
    Join-Path $RepoRoot ".specify/features/$Branch"
}

function Find-FeatureDirByPrefix {
    param(
        [string]$RepoRoot,
        [string]$BranchName
    )

    $prefix = ""

    if ($BranchName -match '^(\d{4}-\d{2}-\d{2})-') {
        # Date-prefixed branches use the full branch name as the feature identity
        # because many independent features can share the same YYYY-MM-DD prefix.
        foreach ($specsDir in (Get-FeatureSpecsRoots -RepoRoot $RepoRoot)) {
            if (-not (Test-Path -LiteralPath $specsDir -PathType Container)) {
                continue
            }
            $exactMatch = Join-Path $specsDir $BranchName
            if (Test-Path -LiteralPath $exactMatch -PathType Container) {
                return $exactMatch
            }
        }

        return (Join-Path (Join-Path $RepoRoot ".specify/features") $BranchName)
    } elseif ($BranchName -match '^(\d{8}-\d{6})-') {
        $prefix = $matches[1]
    } elseif ($BranchName -match '^(\d{3,})-') {
        $prefix = $matches[1]
    } else {
        return (Join-Path (Join-Path $RepoRoot ".specify/features") $BranchName)
    }

    foreach ($specsDir in (Get-FeatureSpecsRoots -RepoRoot $RepoRoot)) {
        if (-not (Test-Path -LiteralPath $specsDir -PathType Container)) {
            continue
        }
        $featureMatches = @(
            Get-ChildItem -LiteralPath $specsDir -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -like "$prefix-*" } |
                Select-Object -ExpandProperty FullName
        )
        if ($featureMatches.Count -eq 1) {
            return $featureMatches[0]
        }
        if ($featureMatches.Count -gt 1) {
            Write-Output "ERROR: Multiple spec directories found with prefix '$prefix' under '$specsDir': $($featureMatches -join ', ')"
            Write-Output "Please ensure only one spec directory exists per prefix in the active feature root."
            return $null
        }
    }

    return (Join-Path (Join-Path $RepoRoot ".specify/features") $BranchName)
}

function Get-CanonicalManagedRunPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
    return [System.IO.Path]::GetFullPath($resolved.Path).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
}

function Assert-ManagedRunWorkspace {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

    if ([string]::IsNullOrWhiteSpace($env:SPECIFY_RUN_WORKSPACE)) {
        throw "Managed Run is missing SPECIFY_RUN_WORKSPACE"
    }

    $canonicalWorkspace = Get-CanonicalManagedRunPath -Path $env:SPECIFY_RUN_WORKSPACE
    $canonicalRepoRoot = Get-CanonicalManagedRunPath -Path $RepoRoot
    $canonicalCwd = Get-CanonicalManagedRunPath -Path (Get-Location).Path
    $comparison = if ($env:OS -eq 'Windows_NT') {
        [System.StringComparison]::OrdinalIgnoreCase
    } else {
        [System.StringComparison]::Ordinal
    }
    if (
        -not [string]::Equals($canonicalRepoRoot, $canonicalWorkspace, $comparison) -or
        -not [string]::Equals($canonicalCwd, $canonicalWorkspace, $comparison)
    ) {
        throw "Managed Run workspace binding mismatch; expected '$canonicalWorkspace', repo root '$canonicalRepoRoot', cwd '$canonicalCwd'"
    }
}

function Assert-ManagedRunFeatureDir {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$FeatureDir
    )

    $canonicalFeatureDir = Get-CanonicalManagedRunPath -Path $FeatureDir
    $comparison = if ($env:OS -eq 'Windows_NT') {
        [System.StringComparison]::OrdinalIgnoreCase
    } else {
        [System.StringComparison]::Ordinal
    }
    foreach ($registeredRoot in (Get-FeatureSpecsRoots -RepoRoot $RepoRoot)) {
        if (-not (Test-Path -LiteralPath $registeredRoot -PathType Container)) {
            continue
        }
        $canonicalRoot = Get-CanonicalManagedRunPath -Path $registeredRoot
        $rootPrefix = $canonicalRoot + [System.IO.Path]::DirectorySeparatorChar
        if ($canonicalFeatureDir.StartsWith($rootPrefix, $comparison)) {
            return
        }
    }

    throw "Managed Run feature directory is outside registered feature roots: $FeatureDir"
}

function Find-FeatureDirFromManagedRun {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

    Assert-ManagedRunWorkspace -RepoRoot $RepoRoot
    if (
        $env:SPECIFY_RUN_SUBJECT_TYPE -ne 'feature' -or
        [string]::IsNullOrWhiteSpace($env:SPECIFY_RUN_SUBJECT_ID)
    ) {
        throw "Managed feature workflow requires SPECIFY_RUN_SUBJECT_TYPE=feature and a non-empty SPECIFY_RUN_SUBJECT_ID"
    }

    $subjectPath = ([string]$env:SPECIFY_RUN_SUBJECT_ID).Replace('\', '/')
    $segments = @($subjectPath.Split('/') | Where-Object { $_ -ne '' })
    if (
        [System.IO.Path]::IsPathRooted($subjectPath) -or
        $segments -contains '..'
    ) {
        throw "Managed Run feature subject must be a safe project-relative feature id or path"
    }
    if ($subjectPath.Contains('/')) {
        if (
            $subjectPath -notlike '.specify/features/*' -and
            $subjectPath -notlike '.specify/specs/*' -and
            $subjectPath -notlike 'specs/*'
        ) {
            throw "Managed Run feature subject path is outside registered feature roots: $subjectPath"
        }
        return (Join-Path $RepoRoot $subjectPath)
    }

    $exactMatches = @(
        foreach ($specsDir in (Get-FeatureSpecsRoots -RepoRoot $RepoRoot)) {
            $candidate = Join-Path $specsDir $subjectPath
            if (Test-Path -LiteralPath $candidate -PathType Container) {
                $candidate
            }
        }
    )
    if ($exactMatches.Count -eq 1) {
        return $exactMatches[0]
    }
    if ($exactMatches.Count -gt 1) {
        throw "Managed Run feature subject '$subjectPath' matches multiple feature roots: $($exactMatches -join ', ')"
    }

    return (Find-FeatureDirByPrefix -RepoRoot $RepoRoot -BranchName $subjectPath)
}

function Get-FeaturePathsEnv {
    param([string]$FeatureDirOverride = "")

    $repoRoot = Get-RepoRoot
    $currentBranch = Get-CurrentBranch
    $hasGit = Test-HasGit
    if ($env:SPECIFY_RUN_MANAGED -eq '1') {
        Assert-ManagedRunWorkspace -RepoRoot $repoRoot
    }
    if (-not [string]::IsNullOrWhiteSpace($FeatureDirOverride)) {
        $featureDir = if ([System.IO.Path]::IsPathRooted($FeatureDirOverride)) {
            $FeatureDirOverride
        } else {
            Join-Path $repoRoot $FeatureDirOverride
        }
    } elseif ($env:SPECIFY_RUN_MANAGED -eq '1') {
        $featureDir = Find-FeatureDirFromManagedRun -RepoRoot $repoRoot
    } else {
        $featureDir = Find-FeatureDirByPrefix -RepoRoot $repoRoot -BranchName $currentBranch
    }
    if (-not $featureDir) {
        throw "Failed to resolve feature directory"
    }
    if ($env:SPECIFY_RUN_MANAGED -eq '1') {
        Assert-ManagedRunFeatureDir -RepoRoot $repoRoot -FeatureDir $featureDir
    }
    
    [PSCustomObject]@{
        REPO_ROOT     = $repoRoot
        CURRENT_BRANCH = $currentBranch
        HAS_GIT       = $hasGit
        FEATURE_DIR   = $featureDir
        FEATURE_SPEC  = Join-Path $featureDir 'spec.md'
        CONTEXT       = Join-Path $featureDir 'context.md'
        SPECIFY_DRAFT = Join-Path $featureDir 'specify-draft.md'
        BRAINSTORMING_FACTS = Join-Path $featureDir 'brainstorming/facts.json'
        BRAINSTORMING_ROUTE = Join-Path $featureDir 'brainstorming/route.json'
        BRAINSTORMING_INTENT = Join-Path $featureDir 'brainstorming/intent.json'
        BRAINSTORMING_COMPLEXITY = Join-Path $featureDir 'brainstorming/complexity.json'
        BRAINSTORMING_JOURNAL = Join-Path $featureDir 'brainstorming/journal.ndjson'
        BRAINSTORMING_STAGE_MANIFEST = Join-Path $featureDir 'brainstorming/stage-manifest.json'
        BRAINSTORMING_DOMAINS = Join-Path $featureDir 'brainstorming/domains.json'
        BRAINSTORMING_EVIDENCE_INDEX = Join-Path $featureDir 'brainstorming/evidence-index.json'
        BRAINSTORMING_EVIDENCE_DIR = Join-Path $featureDir 'brainstorming/evidence'
        HANDOFF_TO_SPECIFY = Join-Path $featureDir 'brainstorming/handoff-to-specify.json'
        IMPL_PLAN     = Join-Path $featureDir 'plan.md'
        TASKS         = Join-Path $featureDir 'tasks.md'
        RESEARCH      = Join-Path $featureDir 'research.md'
        DATA_MODEL    = Join-Path $featureDir 'data-model.md'
        QUICKSTART    = Join-Path $featureDir 'quickstart.md'
        CONTRACTS_DIR = Join-Path $featureDir 'contracts'
    }
}

function Test-FileExists {
    param([string]$Path, [string]$Description)
    if (Test-Path -Path $Path -PathType Leaf) {
        Write-Output "  ✓ $Description"
        return $true
    } else {
        Write-Output "  ✗ $Description"
        return $false
    }
}

function Test-DirHasFiles {
    param([string]$Path, [string]$Description)
    if ((Test-Path -Path $Path -PathType Container) -and (Get-ChildItem -Path $Path -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer } | Select-Object -First 1)) {
        Write-Output "  ✓ $Description"
        return $true
    } else {
        Write-Output "  ✗ $Description"
        return $false
    }
}

# Resolve a template name to a file path using the priority stack:
#   1. .specify/templates/overrides/
#   2. .specify/presets/<preset-id>/templates/ (sorted by priority from .registry)
#   3. .specify/extensions/<ext-id>/templates/
#   4. .specify/templates/ (core)
function Resolve-Template {
    param(
        [Parameter(Mandatory=$true)][string]$TemplateName,
        [Parameter(Mandatory=$true)][string]$RepoRoot
    )

    $base = Join-Path $RepoRoot '.specify/templates'
    $templateExtensions = @('md', 'json')

    # Priority 1: Project overrides
    foreach ($extension in $templateExtensions) {
        $override = Join-Path $base "overrides/$TemplateName.$extension"
        if (Test-Path $override) { return $override }
    }

    # Priority 2: Installed presets (sorted by priority from .registry)
    $presetsDir = Join-Path $RepoRoot '.specify/presets'
    if (Test-Path $presetsDir) {
        $registryFile = Join-Path $presetsDir '.registry'
        $sortedPresets = @()
        if (Test-Path $registryFile) {
            try {
                $registryData = Get-Content $registryFile -Raw | ConvertFrom-Json
                $presets = $registryData.presets
                if ($presets) {
                    $sortedPresets = $presets.PSObject.Properties |
                        Sort-Object { if ($null -ne $_.Value.priority) { $_.Value.priority } else { 10 } } |
                        ForEach-Object { $_.Name }
                }
            } catch {
                # Fallback: alphabetical directory order
                $sortedPresets = @()
            }
        }

        if ($sortedPresets.Count -gt 0) {
            foreach ($presetId in $sortedPresets) {
                foreach ($extension in $templateExtensions) {
                    $candidate = Join-Path $presetsDir "$presetId/templates/$TemplateName.$extension"
                    if (Test-Path $candidate) { return $candidate }
                }
            }
        } else {
            # Fallback: alphabetical directory order
            foreach ($preset in Get-ChildItem -Path $presetsDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '.*' }) {
                foreach ($extension in $templateExtensions) {
                    $candidate = Join-Path $preset.FullName "templates/$TemplateName.$extension"
                    if (Test-Path $candidate) { return $candidate }
                }
            }
        }
    }

    # Priority 3: Extension-provided templates
    $extDir = Join-Path $RepoRoot '.specify/extensions'
    if (Test-Path $extDir) {
        foreach ($ext in Get-ChildItem -Path $extDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '.*' } | Sort-Object Name) {
            foreach ($extension in $templateExtensions) {
                $candidate = Join-Path $ext.FullName "templates/$TemplateName.$extension"
                if (Test-Path $candidate) { return $candidate }
            }
        }
    }

    # Priority 4: Core templates
    foreach ($extension in $templateExtensions) {
        $core = Join-Path $base "$TemplateName.$extension"
        if (Test-Path $core) { return $core }
    }

    return $null
}

function Get-ProjectCognitionDir {
    param([string]$RepoRoot = (Get-RepoRoot))
    return (Join-Path $RepoRoot ".specify/project-cognition")
}

function Get-ProjectCognitionStatusPath {
    param([string]$RepoRoot = (Get-RepoRoot))
    return (Join-Path (Get-ProjectCognitionDir -RepoRoot $RepoRoot) "status.json")
}

function Get-ProjectCognitionHelperPath {
    param([string]$RepoRoot = (Get-RepoRoot))
    return (Join-Path $RepoRoot ".specify/scripts/powershell/project-cognition-freshness.ps1")
}

function Get-ProjectMapDir {
    param([string]$RepoRoot = (Get-RepoRoot))
    return (Join-Path $RepoRoot ".specify/project-map")
}

function Get-ProjectMapStatusPath {
    param([string]$RepoRoot = (Get-RepoRoot))
    return (Get-ProjectCognitionStatusPath -RepoRoot $RepoRoot)
}

function Get-LegacyProjectMapStatusPath {
    param([string]$RepoRoot = (Get-RepoRoot))
    return (Join-Path (Get-ProjectMapDir -RepoRoot $RepoRoot) "status.json")
}
