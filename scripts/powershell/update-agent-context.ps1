#!/usr/bin/env pwsh
<#!
.SYNOPSIS
Update agent context files with information from plan.md (PowerShell version)

.DESCRIPTION
Mirrors the behavior of scripts/bash/update-agent-context.sh:
 1. Environment Validation
 2. Plan Data Extraction
 3. Agent File Management (create from template or update existing)
 4. Content Generation (technology stack, recent changes, timestamp)
 5. Multi-Agent Support (claude, gemini, copilot, cursor-agent, qwen, opencode, codex, windsurf, junie, kilocode, auggie, roo, codebuddy, amp, shai, tabnine, kiro-cli, agy, bob, vibe, qodercli, kimi, trae, pi, iflow, forge, generic)

.PARAMETER AgentType
Optional agent key to update a single agent. If omitted, updates all existing agent files (creating a default Claude file if none exist).

.EXAMPLE
./update-agent-context.ps1 -AgentType claude

.EXAMPLE
./update-agent-context.ps1   # Updates all existing agent files

.NOTES
Relies on common helper functions in common.ps1
#>
param(
    [Parameter(Position=0)]
    [ValidateSet('claude','gemini','copilot','cursor-agent','qwen','opencode','codex','windsurf','junie','kilocode','auggie','roo','codebuddy','amp','shai','tabnine','kiro-cli','agy','bob','vibe','qodercli','kimi','trae','pi','iflow','forge','generic')]
    [string]$AgentType
)

$ErrorActionPreference = 'Stop'

# Import common helpers
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir 'common.ps1')

# Acquire environment paths
$envData = Get-FeaturePathsEnv
$REPO_ROOT     = $envData.REPO_ROOT
$CURRENT_BRANCH = $envData.CURRENT_BRANCH
$HAS_GIT       = $envData.HAS_GIT
$IMPL_PLAN     = $envData.IMPL_PLAN
$NEW_PLAN = $IMPL_PLAN

# Agent file paths
$CLAUDE_FILE   = Join-Path $REPO_ROOT 'CLAUDE.md'
$GEMINI_FILE   = Join-Path $REPO_ROOT 'GEMINI.md'
$COPILOT_FILE  = Join-Path $REPO_ROOT '.github/copilot-instructions.md'
$CURSOR_FILE   = Join-Path $REPO_ROOT '.cursor/rules/specify-rules.mdc'
$QWEN_FILE     = Join-Path $REPO_ROOT 'QWEN.md'
$AGENTS_FILE   = Join-Path $REPO_ROOT 'AGENTS.md'
$WINDSURF_FILE = Join-Path $REPO_ROOT '.windsurf/rules/specify-rules.md'
$JUNIE_FILE = Join-Path $REPO_ROOT '.junie/AGENTS.md'
$KILOCODE_FILE = Join-Path $REPO_ROOT '.kilocode/rules/specify-rules.md'
$AUGGIE_FILE   = Join-Path $REPO_ROOT '.augment/rules/specify-rules.md'
$ROO_FILE      = Join-Path $REPO_ROOT '.roo/rules/specify-rules.md'
$CODEBUDDY_FILE = Join-Path $REPO_ROOT 'CODEBUDDY.md'
$QODER_FILE    = Join-Path $REPO_ROOT 'QODER.md'
$AMP_FILE      = Join-Path $REPO_ROOT 'AGENTS.md'
$SHAI_FILE     = Join-Path $REPO_ROOT 'SHAI.md'
$TABNINE_FILE  = Join-Path $REPO_ROOT 'TABNINE.md'
$KIRO_FILE     = Join-Path $REPO_ROOT 'AGENTS.md'
$AGY_FILE      = Join-Path $REPO_ROOT 'AGENTS.md'
$BOB_FILE      = Join-Path $REPO_ROOT 'AGENTS.md'
$VIBE_FILE     = Join-Path $REPO_ROOT '.vibe/agents/specify-agents.md'
$KIMI_FILE     = Join-Path $REPO_ROOT 'KIMI.md'
$TRAE_FILE     = Join-Path $REPO_ROOT '.trae/rules/AGENTS.md'
$IFLOW_FILE    = Join-Path $REPO_ROOT 'IFLOW.md'
$FORGE_FILE    = Join-Path $REPO_ROOT 'AGENTS.md'

$TEMPLATE_FILE = Join-Path $REPO_ROOT '.specify/templates/agent-file-template.md'

# Parsed plan data placeholders
$script:NEW_LANG = ''
$script:NEW_FRAMEWORK = ''
$script:NEW_DB = ''
$script:NEW_PROJECT_TYPE = ''
$script:SpecKitBlockStart = '<!-- SPEC-KIT:BEGIN -->'
$script:SpecKitBlockEnd = '<!-- SPEC-KIT:END -->'

function Write-Info { 
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message
    )
    Write-Host "INFO: $Message" 
}

function Write-Success { 
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message
    )
    Write-Host "$([char]0x2713) $Message" 
}

function Write-WarningMsg { 
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message
    )
    Write-Warning $Message 
}

function Write-Err { 
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message
    )
    Write-Host "ERROR: $Message" -ForegroundColor Red 
}

function Test-IsManagedAgentsFile {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TargetFile
    )
    return ([System.IO.Path]::GetFullPath($TargetFile) -eq [System.IO.Path]::GetFullPath($AGENTS_FILE))
}

function Get-SpecKitManagedBlock {
    param(
        [Parameter(Mandatory=$false)]
        [string]$Newline = "`n"
    )

    return (
        @(
            '<!-- SPEC-KIT:BEGIN -->'
            '## Spec Kit Plus Managed Rules'
            ''
            '- `[AGENT]` marks an action the AI must explicitly execute.'
            '- `[AGENT]` is independent from `[P]`.'
            ''
            '## Workflow Mainline'
            ''
            '- Treat `specify -> plan` as the default path.'
            '- Use `clarify` only when an existing spec needs deeper analysis before planning.'
            '- Use `deep-research` only when requirements are clear but feasibility or the implementation chain must be proven before planning; its research findings, demo evidence, and Planning Handoff become inputs to `plan`.'
            ''
            '## Workflow Activation Discipline'
            ''
            '- If there is even a 1% chance an `sp-*` workflow or passive skill applies, route before any response or action, including a clarifying question, file read, shell command, repository inspection, code edit, test run, or summary.'
            '- Do not inspect first outside the workflow; repository inspection belongs inside the selected workflow.'
            '- Name the selected workflow or passive skill in one concise line, then continue under that contract.'
            ''
            '## Brownfield Context Gate'
            ''
            '- `PROJECT-HANDBOOK.md` is the root navigation artifact.'
            '- Deep project knowledge lives under `.specify/project-map/`.'
            '- Before planning, debugging, or implementing against existing code, read `PROJECT-HANDBOOK.md` and the smallest relevant `.specify/project-map/*.md` files.'
            '- If handbook/project-map coverage is missing, stale, or too broad, run the runtime''s `map-scan` workflow entrypoint followed by `map-build` before continuing.'
            ''
            '## Project Memory'
            ''
            '- Passive project memory lives under `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`.'
            '- Shared project memory is always available to later work in this repository, not just when a `sp-*` workflow is active.'
            '- Prefer generated project-local Spec Kit workflows, skills, and commands over ad-hoc execution when they fit the task.'
            ''
            '## Workflow Routing'
            ''
            '- Use `sp-fast` only for trivial, low-risk local changes that do not need planning artifacts.'
            '- Use `sp-quick` for bounded tasks that need lightweight tracking but not the full `specify -> plan -> tasks -> implement` flow.'
            '- Use `sp-auto` when repository state already records the recommended next step and the user wants one continue entrypoint instead of naming the exact workflow manually.'
            '- Use `sp-specify` when scope, behavior, constraints, or acceptance criteria need explicit alignment before planning.'
            '- Use `sp-deep-research` when a clear requirement still lacks a proven implementation chain and needs coordinated research, optional multi-agent evidence gathering, or a disposable demo before planning.'
            '- Use `sp-debug` when diagnosis or root-cause analysis is still required before a fix path is trustworthy.'
            '- Use `sp-test` as the compatibility router for project-level testing work.'
            '- Use `sp-test-scan` when testing-system coverage needs read-only evidence, risk tiering, module-by-module gap analysis, or build-ready lanes.'
            '- Use `sp-test-build` when scan-approved lanes should construct or refresh the unit testing system through leader/subagent execution.'
            ''
            '## Delegated Execution Defaults'
            ''
            '- Dispatch native subagents by default for independent, bounded lanes when parallel work materially improves speed, quality, or verification confidence.'
            '- Use a validated `WorkerTaskPacket` or equivalent execution contract before subagent work begins.'
            '- Do not dispatch from raw task text alone.'
            '- Wait for each subagent''s structured handoff before integrating or marking work complete; idle status is not completion evidence.'
            '- Use `sp-teams` only when Codex work needs durable team state, explicit join-point tracking, result files, or lifecycle control beyond one in-session subagent burst.'
            ''
            '## Artifact Priority'
            ''
            '- `.specify/memory/constitution.md` is the principle-level source of truth when present.'
            '- `workflow-state.md` under the active feature directory is the stage/status source of truth for resumable workflow progress.'
            '- `alignment.md` and `context.md` under the active feature directory carry locked decisions from `sp-specify` into planning.'
            '- `deep-research.md`, its traceable `Planning Handoff`, and `research-spikes/` under the active feature directory carry feasibility evidence IDs, recommended approach, constraints, rejected options, and demo results from `sp-deep-research` into planning.'
            '- `plan.md` under the active feature directory is the implementation design source of truth once planning begins.'
            '- `tasks.md` under the active feature directory is the execution breakdown source of truth once task generation begins.'
            '- `.specify/testing/TEST_SCAN.md`, `.specify/testing/TEST_BUILD_PLAN.md`, `.specify/testing/TEST_BUILD_PLAN.json`, `.specify/testing/TESTING_CONTRACT.md`, `.specify/testing/TESTING_PLAYBOOK.md`, `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md`, and `.specify/testing/testing-state.md` constrain testing-system construction and brownfield testing-program routing when present.'
            '- `.specify/project-map/index/status.json` determines whether handbook/project-map coverage can be trusted as fresh.'
            ''
            '## Map Maintenance'
            ''
            '- If a change alters architecture boundaries, ownership, workflow names, integration contracts, or verification entry points, refresh `PROJECT-HANDBOOK.md` and the affected `.specify/project-map/*.md` files.'
            '- If that refresh cannot happen in the current pass, mark `.specify/project-map/index/status.json` dirty and explicitly route the next brownfield workflow through `sp-map-scan` followed by `sp-map-build`.'
            '- Do not treat consumed handbook/project-map context as self-maintaining; the agent changing map-level truth is responsible for keeping the atlas-style handbook system current.'
            ''
            '- Preserve content outside this managed block.'
            '<!-- SPEC-KIT:END -->'
        ) -join $Newline
    )
}

function Get-PreferredNewline {
    param(
        [Parameter(Mandatory=$false)]
        [string]$Text
    )

    if ($Text.Contains("`r`n")) { return "`r`n" }
    if ($Text.Contains("`n")) { return "`n" }
    if ($Text.Contains("`r")) { return "`r" }
    return "`n"
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TargetFile,
        [Parameter(Mandatory=$true)]
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $directory = Split-Path -Parent $TargetFile
    $tempFile = Join-Path $directory ([System.IO.Path]::GetRandomFileName())
    $backupFile = Join-Path $directory ([System.IO.Path]::GetRandomFileName())

    try {
        [System.IO.File]::WriteAllText($tempFile, $Content, $utf8NoBom)
        if (Test-Path $TargetFile) {
            [System.IO.File]::Replace($tempFile, $TargetFile, $backupFile)
            if (Test-Path $backupFile) {
                Remove-Item -LiteralPath $backupFile -Force
            }
        }
        else {
            [System.IO.File]::Move($tempFile, $TargetFile)
        }
    }
    finally {
        if (Test-Path $tempFile) {
            Remove-Item -LiteralPath $tempFile -Force
        }
        if (Test-Path $backupFile) {
            Remove-Item -LiteralPath $backupFile -Force
        }
    }
}

function Update-SpecKitManagedBlock {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TargetFile
    )

    $content = if (Test-Path $TargetFile) {
        Get-Content -LiteralPath $TargetFile -Raw -Encoding utf8
    } else {
        ''
    }

    $rawStartCount = ([regex]::Matches($content, [regex]::Escape($script:SpecKitBlockStart))).Count
    $rawEndCount = ([regex]::Matches($content, [regex]::Escape($script:SpecKitBlockEnd))).Count
    $completeBlocks = [regex]::Matches(
        $content,
        "(?s)$([regex]::Escape($script:SpecKitBlockStart)).*?$([regex]::Escape($script:SpecKitBlockEnd))"
    )

    if ($rawStartCount -eq 1 -and $rawEndCount -eq 1 -and $completeBlocks.Count -eq 1) {
        $match = $completeBlocks[0]
        $newline = Get-PreferredNewline -Text $match.Value
        $block = Get-SpecKitManagedBlock -Newline $newline
        $content = $content.Substring(0, $match.Index) + $block + $content.Substring($match.Index + $match.Length)
    }
    elseif ($content.Length -eq 0) {
        $content = Get-SpecKitManagedBlock
    }
    else {
        $newline = Get-PreferredNewline -Text $content
        $block = Get-SpecKitManagedBlock -Newline $newline
        if ($content.Contains($block)) {
            $content = $content
        }
        else {
            if ($content.EndsWith($newline + $newline)) {
                $separator = ''
            }
            elseif ($content.EndsWith($newline)) {
                $separator = $newline
            }
            else {
                $separator = $newline + $newline
            }
            $content = $content + $separator + $block
        }
    }

    Write-Utf8NoBom -TargetFile $TargetFile -Content $content
}

function Validate-Environment {
    if (-not $CURRENT_BRANCH) {
        Write-Err 'Unable to determine current feature'
        if ($HAS_GIT) { Write-Info "Make sure you're on a feature branch" } else { Write-Info 'Set SPECIFY_FEATURE environment variable or create a feature first' }
        exit 1
    }
    if (-not (Test-Path $NEW_PLAN)) {
        Write-Err "No plan.md found at $NEW_PLAN"
        Write-Info 'Ensure you are working on a feature with a corresponding spec directory'
        if (-not $HAS_GIT) { Write-Info 'Use: $env:SPECIFY_FEATURE=your-feature-name or create a new feature first' }
        exit 1
    }
    if (-not (Test-Path $TEMPLATE_FILE)) {
        Write-WarningMsg "Template file not found at $TEMPLATE_FILE"
        Write-WarningMsg 'Creating new agent files will fail'
    }
}

function Extract-PlanField {
    param(
        [Parameter(Mandatory=$true)]
        [string]$FieldPattern,
        [Parameter(Mandatory=$true)]
        [string]$PlanFile
    )
    if (-not (Test-Path $PlanFile)) { return '' }
    # Lines like **Language/Version**: Python 3.12
    $regex = "^\*\*$([Regex]::Escape($FieldPattern))\*\*: (.+)$"
    Get-Content -LiteralPath $PlanFile -Encoding utf8 | ForEach-Object {
        if ($_ -match $regex) { 
            $val = $Matches[1].Trim()
            if ($val -notin @('NEEDS CLARIFICATION','N/A')) { return $val }
        }
    } | Select-Object -First 1
}

function Parse-PlanData {
    param(
        [Parameter(Mandatory=$true)]
        [string]$PlanFile
    )
    if (-not (Test-Path $PlanFile)) { Write-Err "Plan file not found: $PlanFile"; return $false }
    Write-Info "Parsing plan data from $PlanFile"
    $script:NEW_LANG        = Extract-PlanField -FieldPattern 'Language/Version' -PlanFile $PlanFile
    $script:NEW_FRAMEWORK   = Extract-PlanField -FieldPattern 'Primary Dependencies' -PlanFile $PlanFile
    $script:NEW_DB          = Extract-PlanField -FieldPattern 'Storage' -PlanFile $PlanFile
    $script:NEW_PROJECT_TYPE = Extract-PlanField -FieldPattern 'Project Type' -PlanFile $PlanFile

    if ($NEW_LANG) { Write-Info "Found language: $NEW_LANG" } else { Write-WarningMsg 'No language information found in plan' }
    if ($NEW_FRAMEWORK) { Write-Info "Found framework: $NEW_FRAMEWORK" }
    if ($NEW_DB -and $NEW_DB -ne 'N/A') { Write-Info "Found database: $NEW_DB" }
    if ($NEW_PROJECT_TYPE) { Write-Info "Found project type: $NEW_PROJECT_TYPE" }
    return $true
}

function Format-TechnologyStack {
    param(
        [Parameter(Mandatory=$false)]
        [string]$Lang,
        [Parameter(Mandatory=$false)]
        [string]$Framework
    )
    $parts = @()
    if ($Lang -and $Lang -ne 'NEEDS CLARIFICATION') { $parts += $Lang }
    if ($Framework -and $Framework -notin @('NEEDS CLARIFICATION','N/A')) { $parts += $Framework }
    if (-not $parts) { return '' }
    return ($parts -join ' + ')
}

function Get-ProjectStructure { 
    param(
        [Parameter(Mandatory=$false)]
        [string]$ProjectType
    )
    if ($ProjectType -match 'web') { return "backend/`nfrontend/`ntests/" } else { return "src/`ntests/" } 
}

function Get-CommandsForLanguage { 
    param(
        [Parameter(Mandatory=$false)]
        [string]$Lang
    )
    switch -Regex ($Lang) {
        'Python' { return "cd src; pytest; ruff check ." }
        'Rust' { return "cargo test; cargo clippy" }
        'JavaScript|TypeScript' { return "npm test; npm run lint" }
        default { return "# Add commands for $Lang" }
    }
}

function Get-LanguageConventions { 
    param(
        [Parameter(Mandatory=$false)]
        [string]$Lang
    )
    if ($Lang) { "${Lang}: Follow standard conventions" } else { 'General: Follow standard conventions' } 
}

function New-AgentFile {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TargetFile,
        [Parameter(Mandatory=$true)]
        [string]$ProjectName,
        [Parameter(Mandatory=$true)]
        [datetime]$Date
    )
    if (-not (Test-Path $TEMPLATE_FILE)) { Write-Err "Template not found at $TEMPLATE_FILE"; return $false }
    $temp = New-TemporaryFile
    Copy-Item -LiteralPath $TEMPLATE_FILE -Destination $temp -Force

    $projectStructure = Get-ProjectStructure -ProjectType $NEW_PROJECT_TYPE
    $commands = Get-CommandsForLanguage -Lang $NEW_LANG
    $languageConventions = Get-LanguageConventions -Lang $NEW_LANG

    $escaped_lang = $NEW_LANG
    $escaped_framework = $NEW_FRAMEWORK
    $escaped_branch = $CURRENT_BRANCH

    $content = Get-Content -LiteralPath $temp -Raw -Encoding utf8
    $content = $content -replace '\[PROJECT NAME\]',$ProjectName
    $content = $content -replace '\[DATE\]',$Date.ToString('yyyy-MM-dd')
    
    # Build the technology stack string safely
    $techStackForTemplate = ""
    if ($escaped_lang -and $escaped_framework) {
        $techStackForTemplate = "- $escaped_lang + $escaped_framework ($escaped_branch)"
    } elseif ($escaped_lang) {
        $techStackForTemplate = "- $escaped_lang ($escaped_branch)"
    } elseif ($escaped_framework) {
        $techStackForTemplate = "- $escaped_framework ($escaped_branch)"
    }
    
    $content = $content -replace '\[EXTRACTED FROM ALL PLAN.MD FILES\]',$techStackForTemplate
    # For project structure we manually embed (keep newlines)
    $escapedStructure = [Regex]::Escape($projectStructure)
    $content = $content -replace '\[ACTUAL STRUCTURE FROM PLANS\]',$escapedStructure
    # Replace escaped newlines placeholder after all replacements
    $content = $content -replace '\[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES\]',$commands
    $content = $content -replace '\[LANGUAGE-SPECIFIC, ONLY FOR LANGUAGES IN USE\]',$languageConventions
    
    # Build the recent changes string safely
    $recentChangesForTemplate = ""
    if ($escaped_lang -and $escaped_framework) {
        $recentChangesForTemplate = "- ${escaped_branch}: Added ${escaped_lang} + ${escaped_framework}"
    } elseif ($escaped_lang) {
        $recentChangesForTemplate = "- ${escaped_branch}: Added ${escaped_lang}"
    } elseif ($escaped_framework) {
        $recentChangesForTemplate = "- ${escaped_branch}: Added ${escaped_framework}"
    }
    
    $content = $content -replace '\[LAST 3 FEATURES AND WHAT THEY ADDED\]',$recentChangesForTemplate
    # Convert literal \n sequences introduced by Escape to real newlines
    $content = $content -replace '\\n',[Environment]::NewLine

    # Prepend Cursor frontmatter for .mdc files so rules are auto-included
    if ($TargetFile -match '\.mdc$') {
        $frontmatter = @('---','description: Project Development Guidelines','globs: ["**/*"]','alwaysApply: true','---','') -join [Environment]::NewLine
        $content = $frontmatter + $content
    }

    $parent = Split-Path -Parent $TargetFile
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    Write-Utf8NoBom -TargetFile $TargetFile -Content $content
    Remove-Item $temp -Force
    return $true
}

function Update-ExistingAgentFile {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TargetFile,
        [Parameter(Mandatory=$true)]
        [datetime]$Date
    )
    if (-not (Test-Path $TargetFile)) { return (New-AgentFile -TargetFile $TargetFile -ProjectName (Split-Path $REPO_ROOT -Leaf) -Date $Date) }

    $techStack = Format-TechnologyStack -Lang $NEW_LANG -Framework $NEW_FRAMEWORK
    $newTechEntries = @()
    if ($techStack) {
        $escapedTechStack = [Regex]::Escape($techStack)
        if (-not (Select-String -Pattern $escapedTechStack -Path $TargetFile -Quiet)) { 
            $newTechEntries += "- $techStack ($CURRENT_BRANCH)" 
        }
    }
    if ($NEW_DB -and $NEW_DB -notin @('N/A','NEEDS CLARIFICATION')) {
        $escapedDB = [Regex]::Escape($NEW_DB)
        if (-not (Select-String -Pattern $escapedDB -Path $TargetFile -Quiet)) { 
            $newTechEntries += "- $NEW_DB ($CURRENT_BRANCH)" 
        }
    }
    $newChangeEntry = ''
    if ($techStack) { $newChangeEntry = "- ${CURRENT_BRANCH}: Added ${techStack}" }
    elseif ($NEW_DB -and $NEW_DB -notin @('N/A','NEEDS CLARIFICATION')) { $newChangeEntry = "- ${CURRENT_BRANCH}: Added ${NEW_DB}" }

    $hasActiveTechnologies = Select-String -Pattern '^## Active Technologies$' -Path $TargetFile -Quiet
    $hasRecentChanges = Select-String -Pattern '^## Recent Changes$' -Path $TargetFile -Quiet

    $lines = Get-Content -LiteralPath $TargetFile -Encoding utf8
    $output = New-Object System.Collections.Generic.List[string]
    $inTech = $false; $inChanges = $false; $techAdded = $false; $changeAdded = $false; $existingChanges = 0

    for ($i=0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -eq '## Active Technologies') {
            $output.Add($line)
            $inTech = $true
            continue
        }
        if ($inTech -and $line -match '^##\s') {
            if (-not $techAdded -and $newTechEntries.Count -gt 0) { $newTechEntries | ForEach-Object { $output.Add($_) }; $techAdded = $true }
            $output.Add($line); $inTech = $false; continue
        }
        if ($inTech -and [string]::IsNullOrWhiteSpace($line)) {
            if (-not $techAdded -and $newTechEntries.Count -gt 0) { $newTechEntries | ForEach-Object { $output.Add($_) }; $techAdded = $true }
            $output.Add($line); continue
        }
        if ($line -eq '## Recent Changes') {
            $output.Add($line)
            if ($newChangeEntry) { $output.Add($newChangeEntry); $changeAdded = $true }
            $inChanges = $true
            continue
        }
        if ($inChanges -and $line -match '^##\s') { $output.Add($line); $inChanges = $false; continue }
        if ($inChanges -and $line -match '^- ') {
            if ($existingChanges -lt 2) { $output.Add($line); $existingChanges++ }
            continue
        }
        if ($line -match '(\*\*)?Last updated(\*\*)?: .*\d{4}-\d{2}-\d{2}') {
            $output.Add(($line -replace '\d{4}-\d{2}-\d{2}',$Date.ToString('yyyy-MM-dd')))
            continue
        }
        $output.Add($line)
    }

    # Post-loop check: if we're still in the Active Technologies section and haven't added new entries
    if ($inTech -and -not $techAdded -and $newTechEntries.Count -gt 0) {
        $newTechEntries | ForEach-Object { $output.Add($_) }
    }

    if (-not $hasActiveTechnologies -and $newTechEntries.Count -gt 0) {
        if ($output.Count -gt 0) { $output.Add('') }
        $output.Add('## Active Technologies')
        $newTechEntries | ForEach-Object { $output.Add($_) }
    }

    if (-not $hasRecentChanges -and $newChangeEntry) {
        if ($output.Count -gt 0) { $output.Add('') }
        $output.Add('## Recent Changes')
        $output.Add($newChangeEntry)
    }

    # Ensure Cursor .mdc files have YAML frontmatter for auto-inclusion
    if ($TargetFile -match '\.mdc$' -and $output.Count -gt 0 -and $output[0] -ne '---') {
        [string[]]$frontmatter = @('---','description: Project Development Guidelines','globs: ["**/*"]','alwaysApply: true','---','')
        $output.InsertRange(0, $frontmatter)
    }

    Write-Utf8NoBom -TargetFile $TargetFile -Content ($output -join [Environment]::NewLine)
    return $true
}

function Update-AgentFile {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TargetFile,
        [Parameter(Mandatory=$true)]
        [string]$AgentName
    )
    if (-not $TargetFile -or -not $AgentName) { Write-Err 'Update-AgentFile requires TargetFile and AgentName'; return $false }
    Write-Info "Updating $AgentName context file: $TargetFile"
    $projectName = Split-Path $REPO_ROOT -Leaf
    $date = Get-Date

    $dir = Split-Path -Parent $TargetFile
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }

    $exists = Test-Path $TargetFile

    if (-not $exists) {
        if (-not (New-AgentFile -TargetFile $TargetFile -ProjectName $projectName -Date $date)) { Write-Err 'Failed to create new agent file'; return $false }
    } elseif (-not (Test-IsManagedAgentsFile -TargetFile $TargetFile)) {
        try {
            if (-not (Update-ExistingAgentFile -TargetFile $TargetFile -Date $date)) { Write-Err 'Failed to update agent file'; return $false }
        } catch {
            Write-Err "Cannot access or update existing file: $TargetFile. $_"
            return $false
        }
    }

    try {
        Update-SpecKitManagedBlock -TargetFile $TargetFile
    } catch {
        Write-Err "Cannot access or update managed Spec Kit block in $TargetFile. $_"
        return $false
    }

    if ($exists) {
        Write-Success "Updated existing $AgentName context file"
    } else {
        Write-Success "Created new $AgentName context file"
    }

    return $true
}

function Update-SpecificAgent {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Type
    )
    switch ($Type) {
        'claude'   { Update-AgentFile -TargetFile $CLAUDE_FILE   -AgentName 'Claude Code' }
        'gemini'   { Update-AgentFile -TargetFile $GEMINI_FILE   -AgentName 'Gemini CLI' }
        'copilot'  { Update-AgentFile -TargetFile $COPILOT_FILE  -AgentName 'GitHub Copilot' }
        'cursor-agent' { Update-AgentFile -TargetFile $CURSOR_FILE   -AgentName 'Cursor IDE' }
        'qwen'     { Update-AgentFile -TargetFile $QWEN_FILE     -AgentName 'Qwen Code' }
        'opencode' { Update-AgentFile -TargetFile $AGENTS_FILE   -AgentName 'opencode' }
        'codex'    {
            Update-AgentFile -TargetFile $AGENTS_FILE -AgentName 'Codex CLI'
            Write-Info 'Codex team/runtime uses the specify-owned surface: sp-teams'
        }
        'windsurf' { Update-AgentFile -TargetFile $WINDSURF_FILE -AgentName 'Windsurf' }
        'junie'    { Update-AgentFile -TargetFile $JUNIE_FILE    -AgentName 'Junie' }
        'kilocode' { Update-AgentFile -TargetFile $KILOCODE_FILE -AgentName 'Kilo Code' }
        'auggie'   { Update-AgentFile -TargetFile $AUGGIE_FILE   -AgentName 'Auggie CLI' }
        'roo'      { Update-AgentFile -TargetFile $ROO_FILE      -AgentName 'Roo Code' }
        'codebuddy' { Update-AgentFile -TargetFile $CODEBUDDY_FILE -AgentName 'CodeBuddy CLI' }
        'qodercli' { Update-AgentFile -TargetFile $QODER_FILE    -AgentName 'Qoder CLI' }
        'amp'      { Update-AgentFile -TargetFile $AMP_FILE      -AgentName 'Amp' }
        'shai'     { Update-AgentFile -TargetFile $SHAI_FILE     -AgentName 'SHAI' }
        'tabnine'  { Update-AgentFile -TargetFile $TABNINE_FILE  -AgentName 'Tabnine CLI' }
        'kiro-cli' { Update-AgentFile -TargetFile $KIRO_FILE     -AgentName 'Kiro CLI' }
        'agy'      { Update-AgentFile -TargetFile $AGY_FILE      -AgentName 'Antigravity' }
        'bob'      { Update-AgentFile -TargetFile $BOB_FILE      -AgentName 'IBM Bob' }
        'vibe'     { Update-AgentFile -TargetFile $VIBE_FILE     -AgentName 'Mistral Vibe' }
        'kimi'     { Update-AgentFile -TargetFile $KIMI_FILE     -AgentName 'Kimi Code' }
        'trae'     { Update-AgentFile -TargetFile $TRAE_FILE     -AgentName 'Trae' }
        'pi'       { Update-AgentFile -TargetFile $AGENTS_FILE   -AgentName 'Pi Coding Agent' }
        'iflow'    { Update-AgentFile -TargetFile $IFLOW_FILE    -AgentName 'iFlow CLI' }
        'forge'    { Update-AgentFile -TargetFile $FORGE_FILE    -AgentName 'Forge' }
        'generic'  { Write-Info 'Generic agent: no predefined context file. Use the agent-specific update script for your agent.' }
        default { Write-Err "Unknown agent type '$Type'"; Write-Err 'Expected: claude|gemini|copilot|cursor-agent|qwen|opencode|codex|windsurf|junie|kilocode|auggie|roo|codebuddy|amp|shai|tabnine|kiro-cli|agy|bob|vibe|qodercli|kimi|trae|pi|iflow|forge|generic'; return $false }
    }
}

function Update-AllExistingAgents {
    $found = $false
    $ok = $true
    $updatedPaths = @()
    
    # Helper function to update only if file exists and hasn't been updated yet
    function Update-IfNew {
        param(
            [Parameter(Mandatory=$true)]
            [string]$FilePath,
            [Parameter(Mandatory=$true)]
            [string]$AgentName
        )
        
        if (-not (Test-Path $FilePath)) { return $true }
        
        # Get the real path to detect duplicates (e.g., AMP_FILE, KIRO_FILE, BOB_FILE all point to AGENTS.md)
        $realPath = (Get-Item -LiteralPath $FilePath).FullName
        
        # Check if we've already updated this file
        if ($updatedPaths -contains $realPath) {
            return $true
        }
        
        # Record the file as seen before attempting the update
        # Use parent scope (1) to modify Update-AllExistingAgents' local variables
        Set-Variable -Name updatedPaths -Value ($updatedPaths + $realPath) -Scope 1
        Set-Variable -Name found -Value $true -Scope 1
        
        # Perform the update
        return (Update-AgentFile -TargetFile $FilePath -AgentName $AgentName)
    }
    
    if (-not (Update-IfNew -FilePath $CLAUDE_FILE   -AgentName 'Claude Code')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $GEMINI_FILE   -AgentName 'Gemini CLI')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $COPILOT_FILE  -AgentName 'GitHub Copilot')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $CURSOR_FILE   -AgentName 'Cursor IDE')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $QWEN_FILE     -AgentName 'Qwen Code')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $AGENTS_FILE   -AgentName 'Codex/opencode/Amp/Kiro/Bob/Pi/Forge')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $WINDSURF_FILE -AgentName 'Windsurf')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $JUNIE_FILE    -AgentName 'Junie')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $KILOCODE_FILE -AgentName 'Kilo Code')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $AUGGIE_FILE   -AgentName 'Auggie CLI')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $ROO_FILE      -AgentName 'Roo Code')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $CODEBUDDY_FILE -AgentName 'CodeBuddy CLI')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $QODER_FILE    -AgentName 'Qoder CLI')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $SHAI_FILE     -AgentName 'SHAI')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $TABNINE_FILE  -AgentName 'Tabnine CLI')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $AGY_FILE      -AgentName 'Antigravity')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $VIBE_FILE     -AgentName 'Mistral Vibe')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $KIMI_FILE     -AgentName 'Kimi Code')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $TRAE_FILE     -AgentName 'Trae')) { $ok = $false }
    if (-not (Update-IfNew -FilePath $IFLOW_FILE    -AgentName 'iFlow CLI')) { $ok = $false }
    
    if (-not $found) {
        Write-Info 'No existing agent files found, creating default Claude file...'
        if (-not (Update-AgentFile -TargetFile $CLAUDE_FILE -AgentName 'Claude Code')) { $ok = $false }
    }
    return $ok
}

function Print-Summary {
    Write-Host ''
    Write-Info 'Summary of changes:'
    if ($NEW_LANG) { Write-Host "  - Added language: $NEW_LANG" }
    if ($NEW_FRAMEWORK) { Write-Host "  - Added framework: $NEW_FRAMEWORK" }
    if ($NEW_DB -and $NEW_DB -ne 'N/A') { Write-Host "  - Added database: $NEW_DB" }
    Write-Host ''
    Write-Info 'Usage: ./update-agent-context.ps1 [-AgentType claude|gemini|copilot|cursor-agent|qwen|opencode|codex|windsurf|junie|kilocode|auggie|roo|codebuddy|amp|shai|tabnine|kiro-cli|agy|bob|vibe|qodercli|kimi|trae|pi|iflow|forge|generic]'
}

function Main {
    Validate-Environment
    Write-Info "=== Updating agent context files for feature $CURRENT_BRANCH ==="
    if (-not (Parse-PlanData -PlanFile $NEW_PLAN)) { Write-Err 'Failed to parse plan data'; exit 1 }
    $success = $true
    if ($AgentType) {
        Write-Info "Updating specific agent: $AgentType"
        if (-not (Update-SpecificAgent -Type $AgentType)) { $success = $false }
    }
    else {
        Write-Info 'No agent specified, updating all existing agent files...'
        if (-not (Update-AllExistingAgents)) { $success = $false }
    }
    Print-Summary
    if ($success) { Write-Success 'Agent context update completed successfully'; exit 0 } else { Write-Err 'Agent context update completed with errors'; exit 1 }
}

Main
