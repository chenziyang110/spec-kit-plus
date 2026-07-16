#!/usr/bin/env pwsh
# Create a new feature
[CmdletBinding()]
param(
    [switch]$Json,
    [switch]$AllowExistingBranch,
    [switch]$DryRun,
    [string]$ShortName,
    [Parameter()]
    [long]$Number = 0,
    [switch]$Timestamp,
    [switch]$Help,
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$FeatureDescription
)
$ErrorActionPreference = 'Stop'

# Show help if requested
if ($Help) {
    Write-Host "Usage: ./create-new-feature.ps1 [-Json] [-DryRun] [-AllowExistingBranch] [-ShortName <name>] [-Number N] [-Timestamp] <feature description>"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Json               Output in JSON format"
    Write-Host "  -DryRun             Compute branch name and paths without creating branches, directories, or files"
    Write-Host "  -AllowExistingBranch  Switch to branch if it already exists instead of failing"
    Write-Host "  -ShortName <name>   Provide a custom short name (2-4 words) for the branch"
    Write-Host "  -Number N           Use legacy numeric prefix N; use 0 to auto-detect next number"
    Write-Host "  -Timestamp          Use timestamp prefix (YYYYMMDD-HHMMSS) instead of the default date prefix"
    Write-Host "  -Help               Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  ./create-new-feature.ps1 'Add user authentication system' -ShortName 'user-auth'"
    Write-Host "  ./create-new-feature.ps1 'Implement OAuth2 integration for API'"
    Write-Host "  ./create-new-feature.ps1 -Timestamp -ShortName 'user-auth' 'Add user authentication'"
    exit 0
}

# Check if feature description provided
if (-not $FeatureDescription -or $FeatureDescription.Count -eq 0) {
    Write-Error "Usage: ./create-new-feature.ps1 [-Json] [-DryRun] [-AllowExistingBranch] [-ShortName <name>] [-Number N] [-Timestamp] <feature description>"
    exit 1
}

$featureDesc = ($FeatureDescription -join ' ').Trim()

# Validate description is not empty after trimming (e.g., user passed only whitespace)
if ([string]::IsNullOrWhiteSpace($featureDesc)) {
    Write-Error "Error: Feature description cannot be empty or contain only whitespace"
    exit 1
}

function Get-HighestNumberFromSpecs {
    param([string]$SpecsDir)

    [long]$highest = 0
    if (Test-Path $SpecsDir) {
        Get-ChildItem -Path $SpecsDir -Directory | ForEach-Object {
            # Match sequential prefixes (>=3 digits), but skip date/timestamp dirs.
            if ($_.Name -match '^(\d{3,})-' -and $_.Name -notmatch '^\d{4}-\d{2}-\d{2}-' -and $_.Name -notmatch '^\d{8}-\d{6}-') {
                [long]$num = 0
                if ([long]::TryParse($matches[1], [ref]$num) -and $num -gt $highest) {
                    $highest = $num
                }
            }
        }
    }
    return $highest
}

# Extract the highest sequential feature number from a list of branch/ref names.
# Shared by Get-HighestNumberFromBranches and Get-HighestNumberFromRemoteRefs.
function Get-HighestNumberFromNames {
    param([string[]]$Names)

    [long]$highest = 0
    foreach ($name in $Names) {
        if ($name -match '^(\d{3,})-' -and $name -notmatch '^\d{4}-\d{2}-\d{2}-' -and $name -notmatch '^\d{8}-\d{6}-') {
            [long]$num = 0
            if ([long]::TryParse($matches[1], [ref]$num) -and $num -gt $highest) {
                $highest = $num
            }
        }
    }
    return $highest
}

function Get-HighestNumberFromBranches {
    param()

    try {
        $branches = git branch -a 2>$null
        if ($LASTEXITCODE -eq 0 -and $branches) {
            $cleanNames = $branches | ForEach-Object {
                $_.Trim() -replace '^\*?\s+', '' -replace '^remotes/[^/]+/', ''
            }
            return Get-HighestNumberFromNames -Names $cleanNames
        }
    } catch {
        Write-Verbose "Could not check Git branches: $_"
    }
    return 0
}

function Get-HighestNumberFromRemoteRefs {
    [long]$highest = 0
    try {
        $remotes = git remote 2>$null
        if ($remotes) {
            foreach ($remote in $remotes) {
                $env:GIT_TERMINAL_PROMPT = '0'
                $refs = git ls-remote --heads $remote 2>$null
                $env:GIT_TERMINAL_PROMPT = $null
                if ($LASTEXITCODE -eq 0 -and $refs) {
                    $refNames = $refs | ForEach-Object {
                        if ($_ -match 'refs/heads/(.+)$') { $matches[1] }
                    } | Where-Object { $_ }
                    $remoteHighest = Get-HighestNumberFromNames -Names $refNames
                    if ($remoteHighest -gt $highest) { $highest = $remoteHighest }
                }
            }
        }
    } catch {
        Write-Verbose "Could not query remote refs: $_"
    }
    return $highest
}

# Return next available branch number. When SkipFetch is true, queries remotes
# via ls-remote (read-only) instead of fetching.
function Get-NextBranchNumber {
    param(
        [string]$SpecsDir,
        [switch]$SkipFetch
    )

    if ($SkipFetch) {
        # Side-effect-free: query remotes via ls-remote
        $highestBranch = Get-HighestNumberFromBranches
        $highestRemote = Get-HighestNumberFromRemoteRefs
        $highestBranch = [Math]::Max($highestBranch, $highestRemote)
    } else {
        # Fetch all remotes to get latest branch info (suppress errors if no remotes)
        try {
            git fetch --all --prune 2>$null | Out-Null
        } catch {
            # Ignore fetch errors
        }
        $highestBranch = Get-HighestNumberFromBranches
    }

    # Get highest number from ALL specs (not just matching short name)
    $highestSpec = Get-HighestNumberFromSpecs -SpecsDir $SpecsDir

    # Take the maximum of both
    $maxNum = [Math]::Max($highestBranch, $highestSpec)

    # Return next number
    return $maxNum + 1
}

function ConvertTo-CleanBranchName {
    param([string]$Name)

    return $Name.ToLower() -replace '[^a-z0-9]', '-' -replace '-{2,}', '-' -replace '^-', '' -replace '-$', ''
}
# Load common functions (includes Get-RepoRoot, Test-HasGit, Resolve-Template)
. "$PSScriptRoot/common.ps1"

# Use common.ps1 functions which prioritize .specify over git
$repoRoot = Get-RepoRoot

# Check if git is available at this repo root (not a parent)
$hasGit = Test-HasGit

Set-Location $repoRoot

$featuresDir = Join-Path $repoRoot '.specify/features'
if (-not $DryRun) {
    New-Item -ItemType Directory -Path $featuresDir -Force | Out-Null
}

function Get-ConfiguredBranchNumbering {
    param([string]$RepoRoot)

    $configPath = Join-Path $RepoRoot '.specify/init-options.json'
    $value = ''
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        try {
            $payload = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
            $value = [string]$payload.branch_numbering
        } catch {
            $value = ''
        }
    }

    switch ($value) {
        'date' { return 'date' }
        'sequential' { return 'sequential' }
        'timestamp' { return 'timestamp' }
        '' { return 'date' }
        default {
            Write-Warning "[specify] Warning: unsupported branch_numbering '$value'; using date"
            return 'date'
        }
    }
}

function Get-DatePrefix {
    if ($env:SPECIFY_FEATURE_DATE_PREFIX) {
        if ($env:SPECIFY_FEATURE_DATE_PREFIX -notmatch '^\d{4}-\d{2}-\d{2}$') {
            Write-Error "Error: SPECIFY_FEATURE_DATE_PREFIX must match YYYY-MM-DD"
            exit 1
        }
        return $env:SPECIFY_FEATURE_DATE_PREFIX
    }

    return (Get-Date -Format 'yyyy-MM-dd')
}

function Get-TimestampPrefix {
    if ($env:SPECIFY_FEATURE_TIMESTAMP_PREFIX) {
        if ($env:SPECIFY_FEATURE_TIMESTAMP_PREFIX -notmatch '^\d{8}-\d{6}$') {
            Write-Error "Error: SPECIFY_FEATURE_TIMESTAMP_PREFIX must match YYYYMMDD-HHMMSS"
            exit 1
        }
        return $env:SPECIFY_FEATURE_TIMESTAMP_PREFIX
    }

    return (Get-Date -Format 'yyyyMMdd-HHmmss')
}

# Function to generate branch name with stop word filtering and length filtering
function Get-BranchName {
    param([string]$Description)

    # Common stop words to filter out
    $stopWords = @(
        'i', 'a', 'an', 'the', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall',
        'this', 'that', 'these', 'those', 'my', 'your', 'our', 'their',
        'want', 'need', 'add', 'get', 'set'
    )

    # Convert to lowercase and extract words (alphanumeric only)
    $cleanName = $Description.ToLower() -replace '[^a-z0-9\s]', ' '
    $words = $cleanName -split '\s+' | Where-Object { $_ }

    # Filter words: remove stop words and words shorter than 3 chars (unless they're uppercase acronyms in original)
    $meaningfulWords = @()
    foreach ($word in $words) {
        # Skip stop words
        if ($stopWords -contains $word) { continue }

        # Keep words that are length >= 3 OR appear as uppercase in original (likely acronyms)
        if ($word.Length -ge 3) {
            $meaningfulWords += $word
        } elseif ($Description -match "\b$($word.ToUpper())\b") {
            # Keep short words if they appear as uppercase in original (likely acronyms)
            $meaningfulWords += $word
        }
    }

    # If we have meaningful words, use first 3-4 of them
    if ($meaningfulWords.Count -gt 0) {
        $maxWords = if ($meaningfulWords.Count -eq 4) { 4 } else { 3 }
        $result = ($meaningfulWords | Select-Object -First $maxWords) -join '-'
        return $result
    } else {
        # Fallback to original logic if no meaningful words found
        $result = ConvertTo-CleanBranchName -Name $Description
        $fallbackWords = ($result -split '-') | Where-Object { $_ } | Select-Object -First 3
        return [string]::Join('-', $fallbackWords)
    }
}

# Generate branch name
if ($ShortName) {
    # Use provided short name, just clean it up
    $branchSuffix = ConvertTo-CleanBranchName -Name $ShortName
} else {
    # Generate from description with smart filtering
    $branchSuffix = Get-BranchName -Description $featureDesc
}

$numberWasSpecified = $PSBoundParameters.ContainsKey('Number')

# Warn if -Number and -Timestamp are both specified
if ($Timestamp -and $numberWasSpecified -and $Number -ne 0) {
    Write-Warning "[specify] Warning: -Number is ignored when -Timestamp is used"
    $Number = 0
}

# Determine branch prefix
$branchNumbering = Get-ConfiguredBranchNumbering -RepoRoot $repoRoot
$featurePrefixKind = 'date'
if ($Timestamp) {
    $featurePrefixKind = 'timestamp'
    $featureNum = Get-TimestampPrefix
    $branchName = "$featureNum-$branchSuffix"
} elseif ($numberWasSpecified -or $branchNumbering -eq 'sequential') {
    $featurePrefixKind = 'sequential'
    # Determine branch number
    if ($Number -eq 0) {
        if ($DryRun -and $hasGit) {
            # Dry-run: query remotes via ls-remote (side-effect-free, no fetch)
            $Number = Get-NextBranchNumber -SpecsDir $featuresDir -SkipFetch
        } elseif ($DryRun) {
            # Dry-run without git: local spec dirs only
            $Number = (Get-HighestNumberFromSpecs -SpecsDir $featuresDir) + 1
        } elseif ($hasGit) {
            # Check existing branches on remotes
            $Number = Get-NextBranchNumber -SpecsDir $featuresDir
        } else {
            # Fall back to local directory check
            $Number = (Get-HighestNumberFromSpecs -SpecsDir $featuresDir) + 1
        }
    }

    $featureNum = ('{0:000}' -f $Number)
    $branchName = "$featureNum-$branchSuffix"
} elseif ($branchNumbering -eq 'timestamp') {
    $featurePrefixKind = 'timestamp'
    $featureNum = Get-TimestampPrefix
    $branchName = "$featureNum-$branchSuffix"
} else {
    $featurePrefixKind = 'date'
    $featureNum = Get-DatePrefix
    $branchName = "$featureNum-$branchSuffix"
}

# GitHub enforces a 244-byte limit on branch names
# Validate and truncate if necessary
$maxBranchLength = 244
if ($branchName.Length -gt $maxBranchLength) {
    # Calculate how much we need to trim from suffix
    # Account for prefix length plus the separator hyphen.
    $prefixLength = $featureNum.Length + 1
    $maxSuffixLength = $maxBranchLength - $prefixLength

    # Truncate suffix
    $truncatedSuffix = $branchSuffix.Substring(0, [Math]::Min($branchSuffix.Length, $maxSuffixLength))
    # Remove trailing hyphen if truncation created one
    $truncatedSuffix = $truncatedSuffix -replace '-$', ''

    $originalBranchName = $branchName
    $branchName = "$featureNum-$truncatedSuffix"

    Write-Warning "[specify] Branch name exceeded GitHub's 244-byte limit"
    Write-Warning "[specify] Original: $originalBranchName ($($originalBranchName.Length) bytes)"
    Write-Warning "[specify] Truncated to: $branchName ($($branchName.Length) bytes)"
}

$featureDir = Join-Path $featuresDir $branchName
$specFile = Join-Path $featureDir 'spec.md'
$contextFile = Join-Path $featureDir 'context.md'
$specifyDraftFile = Join-Path $featureDir 'specify-draft.md'
$brainstormingDir = Join-Path $featureDir 'brainstorming'
$brainstormingFactsFile = Join-Path $featureDir 'brainstorming/facts.json'
$brainstormingRouteFile = Join-Path $featureDir 'brainstorming/route.json'
$brainstormingIntentFile = Join-Path $featureDir 'brainstorming/intent.json'
$brainstormingComplexityFile = Join-Path $featureDir 'brainstorming/complexity.json'
$BRAINSTORMING_JOURNAL_FILE = Join-Path $brainstormingDir 'journal.ndjson'
$BRAINSTORMING_STAGE_MANIFEST_FILE = Join-Path $brainstormingDir 'stage-manifest.json'
$BRAINSTORMING_DOMAINS_FILE = Join-Path $brainstormingDir 'domains.json'
$BRAINSTORMING_EVIDENCE_INDEX_FILE = Join-Path $brainstormingDir 'evidence-index.json'
$BRAINSTORMING_EVIDENCE_DIR = Join-Path $brainstormingDir 'evidence'
$BRAINSTORMING_EVIDENCE_RECORD_TEMPLATE_FILE = Join-Path $BRAINSTORMING_EVIDENCE_DIR 'EVD-000-template.json'
$handoffToSpecifyFile = Join-Path $featureDir 'brainstorming/handoff-to-specify.json'
$laneId = $branchName
$laneWorktree = Join-Path $repoRoot ".specify/lanes/worktrees/$laneId"

if (-not $DryRun) {
    if ($hasGit) {
        $branchCreated = $false
        $branchCreateError = ''
        try {
            $branchCreateError = git checkout -q -b $branchName 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0) {
                $branchCreated = $true
            }
        } catch {
            $branchCreateError = $_.Exception.Message
        }

        if (-not $branchCreated) {
            $currentBranch = ''
            try { $currentBranch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch {}
            # Check if branch already exists
            $existingBranch = git branch --list $branchName 2>$null
            if ($existingBranch) {
                if ($AllowExistingBranch) {
                    # If we're already on the branch, continue without another checkout.
                    if ($currentBranch -eq $branchName) {
                        # Already on the target branch — nothing to do
                    } else {
                        # Otherwise switch to the existing branch instead of failing.
                        git checkout -q $branchName 2>$null | Out-Null
                        if ($LASTEXITCODE -ne 0) {
                            Write-Error "Error: Branch '$branchName' exists but could not be checked out. Resolve any uncommitted changes or conflicts and try again."
                            exit 1
                        }
                    }
                } elseif ($featurePrefixKind -eq 'timestamp') {
                    Write-Error "Error: Branch '$branchName' already exists. Rerun to get a new timestamp or use a different -ShortName."
                    exit 1
                } elseif ($featurePrefixKind -eq 'date') {
                    Write-Error "Error: Branch '$branchName' already exists for this date and short name. Use a different -ShortName, -Timestamp, or -Number."
                    exit 1
                } else {
                    Write-Error "Error: Branch '$branchName' already exists. Please use a different feature name or specify a different number with -Number."
                    exit 1
                }
            } else {
                if ($branchCreateError) {
                    Write-Error "Error: Failed to create git branch '$branchName'.`n$($branchCreateError.Trim())"
                } else {
                    Write-Error "Error: Failed to create git branch '$branchName'. Please check your git configuration and try again."
                }
                exit 1
            }
        }
    } else {
        Write-Warning "[specify] Warning: Git repository not detected; skipped branch creation for $branchName"
    }

    New-Item -ItemType Directory -Path $featureDir -Force | Out-Null
    New-Item -ItemType Directory -Path $brainstormingDir -Force | Out-Null
    New-Item -ItemType Directory -Path $BRAINSTORMING_EVIDENCE_DIR -Force | Out-Null

    if (-not (Test-Path -PathType Leaf $specFile)) {
        $template = Resolve-Template -TemplateName 'spec-template' -RepoRoot $repoRoot
        if ($template -and (Test-Path $template)) {
            Copy-Item $template $specFile -Force
        } else {
            New-Item -ItemType File -Path $specFile -Force | Out-Null
        }
    }

    if (-not (Test-Path -PathType Leaf $contextFile)) {
        $contextTemplate = Resolve-Template -TemplateName 'context-template' -RepoRoot $repoRoot
        if ($contextTemplate -and (Test-Path $contextTemplate)) {
            Copy-Item $contextTemplate $contextFile -Force
        } else {
            New-Item -ItemType File -Path $contextFile -Force | Out-Null
        }
    }

    if (-not (Test-Path -PathType Leaf $specifyDraftFile)) {
        $specifyDraftTemplate = Resolve-Template -TemplateName 'specify-draft-template' -RepoRoot $repoRoot
        if ($specifyDraftTemplate -and (Test-Path $specifyDraftTemplate)) {
            Copy-Item $specifyDraftTemplate $specifyDraftFile -Force
        } else {
            New-Item -ItemType File -Path $specifyDraftFile -Force | Out-Null
        }
    }

    function Copy-OrCreateTemplateFile {
        param(
            [Parameter(Mandatory = $true)][string]$TemplateName,
            [Parameter(Mandatory = $true)][string]$Destination
        )

        if (Test-Path -PathType Leaf $Destination) {
            return
        }

        $templatePath = Resolve-Template -TemplateName $TemplateName -RepoRoot $repoRoot
        if ($templatePath -and (Test-Path $templatePath)) {
            Copy-Item $templatePath $Destination -Force
        } else {
            New-Item -ItemType File -Path $Destination -Force | Out-Null
        }
    }

    @(
        @{ Template = 'brainstorming-facts-template'; Destination = $brainstormingFactsFile }
        @{ Template = 'brainstorming-route-template'; Destination = $brainstormingRouteFile }
        @{ Template = 'brainstorming-intent-template'; Destination = $brainstormingIntentFile }
        @{ Template = 'brainstorming-complexity-template'; Destination = $brainstormingComplexityFile }
        @{ Template = 'brainstorming-handoff-specify-template'; Destination = $handoffToSpecifyFile }
        @{ Template = 'brainstorming-stage-manifest-template'; Destination = $BRAINSTORMING_STAGE_MANIFEST_FILE }
        @{ Template = 'brainstorming-domains-template'; Destination = $BRAINSTORMING_DOMAINS_FILE }
        @{ Template = 'brainstorming-evidence-index-template'; Destination = $BRAINSTORMING_EVIDENCE_INDEX_FILE }
        @{ Template = 'brainstorming-evidence-record-template'; Destination = $BRAINSTORMING_EVIDENCE_RECORD_TEMPLATE_FILE }
    ) | ForEach-Object {
        Copy-OrCreateTemplateFile -TemplateName $_.Template -Destination $_.Destination
    }

    if (-not (Test-Path -PathType Leaf $BRAINSTORMING_JOURNAL_FILE)) {
        New-Item -ItemType File -Path $BRAINSTORMING_JOURNAL_FILE -Force | Out-Null
    }

    # Set the SPECIFY_FEATURE environment variable for the current session
    $env:SPECIFY_FEATURE = $branchName
}

if ($Json) {
    $obj = [PSCustomObject]@{
        BRANCH_NAME = $branchName
        FEATURE_DIR = $featureDir
        SPEC_FILE = $specFile
        CONTEXT_FILE = $contextFile
        SPECIFY_DRAFT_FILE = $specifyDraftFile
        LANE_ID = $laneId
        LANE_WORKTREE = $laneWorktree
        FEATURE_NUM = $featureNum
        HAS_GIT = $hasGit
    }
    if ($DryRun) {
        $obj | Add-Member -NotePropertyName 'DRY_RUN' -NotePropertyValue $true
    }
    $obj | ConvertTo-Json -Compress
} else {
    Write-Output "BRANCH_NAME: $branchName"
    Write-Output "FEATURE_DIR: $featureDir"
    Write-Output "SPEC_FILE: $specFile"
    Write-Output "CONTEXT_FILE: $contextFile"
    Write-Output "SPECIFY_DRAFT_FILE: $specifyDraftFile"
    Write-Output "LANE_ID: $laneId"
    Write-Output "LANE_WORKTREE: $laneWorktree"
    Write-Output "FEATURE_NUM: $featureNum"
    Write-Output "HAS_GIT: $hasGit"
    if (-not $DryRun) {
        Write-Output "SPECIFY_FEATURE environment variable set to: $branchName"
    }
}
