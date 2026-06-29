param(
    [string]$Version = $env:PROJECT_COGNITION_VERSION,
    [string]$Repo = $env:PROJECT_COGNITION_REPO,
    [string]$InstallDir = $env:PROJECT_COGNITION_INSTALL_DIR
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = "latest"
}
if ([string]::IsNullOrWhiteSpace($Repo)) {
    $Repo = "chenziyang110/spec-kit-plus"
}
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\project-cognition"
}

$arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "x86" }
if ($arch -ne "amd64") {
    throw "Unsupported Windows architecture for published project-cognition asset: $arch"
}

$binary = "project-cognition"
$asset = "${binary}-windows-${arch}.exe"
if ($Version -eq "latest") {
    $url = "https://github.com/${Repo}/releases/latest/download/${asset}"
} else {
    $url = "https://github.com/${Repo}/releases/download/${Version}/${asset}"
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$target = Join-Path $InstallDir "${binary}.exe"

Write-Host "==> project-cognition installer"
Write-Host "    platform: windows/${arch}"
Write-Host "    install:  ${target}"
Write-Host ""

Write-Host "==> Downloading prebuilt release asset..."
try {
    $ProgressPreference = "SilentlyContinue"
    Invoke-WebRequest -Uri $url -OutFile $target
} catch {
    Write-Host "Error: download failed from ${url}"
    Write-Host "Make sure a release exists with project-cognition binaries attached."
    Write-Host "Go users can also install from source: go install github.com/${Repo}/tools/project-cognition@latest"
    exit 1
}

function Get-NativeHelpOutput {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    $hasNativeCommandPreference = Test-Path -Path Variable:PSNativeCommandUseErrorActionPreference
    if ($hasNativeCommandPreference) {
        $previousNativeCommandPreference = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
    }

    try {
        return (& $Command @Arguments 2>&1 | Out-String)
    } finally {
        if ($hasNativeCommandPreference) {
            $PSNativeCommandUseErrorActionPreference = $previousNativeCommandPreference
        }
    }
}

Write-Host "==> Verifying..."
& $target --version
$rootHelp = Get-NativeHelpOutput -Command $target -Arguments @("--help")
if ($rootHelp -notmatch 'scan-set') {
    Write-Host "Error: downloaded project-cognition binary is missing required scan-set command."
    Write-Host "Expected 'project-cognition --help' to include scan-set."
    exit 1
}
$updateHelp = Get-NativeHelpOutput -Command $target -Arguments @("update", "--help")
if (($updateHelp -notmatch '-payload-file') -or ($updateHelp -notmatch '-verification')) {
    Write-Host "Error: downloaded project-cognition binary is missing required update flags."
    Write-Host "Expected 'project-cognition update --help' to include -payload-file and -verification."
    exit 1
}
$semanticIntakeHelp = Get-NativeHelpOutput -Command $target -Arguments @("semantic-intake", "--help")
if ($semanticIntakeHelp -notmatch '-input') {
    Write-Host "Error: downloaded project-cognition semantic-intake binary is missing required input flag."
    Write-Host "Expected 'project-cognition semantic-intake --help' to include -input."
    exit 1
}
$semanticAuditResumeHelp = Get-NativeHelpOutput -Command $target -Arguments @("semantic-audit-resume", "--help")
if ($semanticAuditResumeHelp -notmatch '-input') {
    Write-Host "Error: downloaded project-cognition semantic-audit-resume binary is missing required input flag."
    Write-Host "Expected 'project-cognition semantic-audit-resume --help' to include -input."
    exit 1
}
$lexiconHelp = Get-NativeHelpOutput -Command $target -Arguments @("lexicon", "--help")
if ($lexiconHelp -notmatch '-mode') {
    Write-Host "Error: downloaded project-cognition binary is missing required lexicon catalog mode."
    Write-Host "Expected 'project-cognition lexicon --help' to include -mode."
    exit 1
}
$compassHelp = Get-NativeHelpOutput -Command $target -Arguments @("compass", "--help")
if (($compassHelp -notmatch '-semantic-intake-file') -or ($compassHelp -notmatch '-query-plan-file')) {
    Write-Host "Error: downloaded project-cognition binary is missing required compass flags."
    Write-Host "Expected 'project-cognition compass --help' to include -semantic-intake-file and -query-plan-file."
    exit 1
}
$expandHelp = Get-NativeHelpOutput -Command $target -Arguments @("expand", "--help")
if ($expandHelp -notmatch '-section') {
    Write-Host "Error: downloaded project-cognition binary is missing required expand section flag."
    Write-Host "Expected 'project-cognition expand --help' to include -section."
    exit 1
}
$deltaAppendHelp = Get-NativeHelpOutput -Command $target -Arguments @("delta", "append", "--help")
if (($deltaAppendHelp -notmatch '-verification') -or ($deltaAppendHelp -notmatch '-generated-surface')) {
    Write-Host "Error: downloaded project-cognition binary is missing required delta append flags."
    Write-Host "Expected 'project-cognition delta append --help' to include -verification and -generated-surface."
    exit 1
}
$closeoutPlanHelp = Get-NativeHelpOutput -Command $target -Arguments @("closeout-plan", "--help")
if (($closeoutPlanHelp -notmatch '-workflow') -or ($closeoutPlanHelp -notmatch '-delta-session')) {
    Write-Host "Error: downloaded project-cognition binary is missing required closeout-plan flags."
    Write-Host "Expected 'project-cognition closeout-plan --help' to include -workflow and -delta-session."
    exit 1
}

$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$InstallDir", "User")
    $env:PATH = "$env:PATH;$InstallDir"
    Write-Host ""
    Write-Host "==> Added to user PATH (restart terminal to use from any directory)"
}

Write-Host ""
Write-Host "==> project-cognition installed successfully."
Write-Host "    Generated workflows will find it as 'project-cognition' on PATH."
