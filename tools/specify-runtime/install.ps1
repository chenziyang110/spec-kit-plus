param(
    [string]$Version = $env:SPECIFY_RUNTIME_VERSION,
    [string]$Repo = $env:SPECIFY_RUNTIME_REPO,
    [string]$InstallDir = $env:SPECIFY_RUNTIME_INSTALL_DIR
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Version)) { $Version = "latest" }
if ([string]::IsNullOrWhiteSpace($Repo)) { $Repo = "chenziyang110/spec-kit-plus" }
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\specify-runtime"
}
if (-not [Environment]::Is64BitOperatingSystem) {
    throw "Only windows/amd64 release assets are published"
}

$binary = "specify-runtime"
$asset = "${binary}-windows-amd64.exe"
$url = if ($Version -eq "latest") {
    "https://github.com/${Repo}/releases/latest/download/${asset}"
} else {
    "https://github.com/${Repo}/releases/download/${Version}/${asset}"
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$target = Join-Path $InstallDir "${binary}.exe"
$candidate = Join-Path $InstallDir ".${binary}.$PID.candidate.exe"

try {
    $ProgressPreference = "SilentlyContinue"
    Invoke-WebRequest -Uri $url -OutFile $candidate

    $handshake = (& $candidate api handshake --format json 2>&1 | Out-String)
    if (($LASTEXITCODE -ne 0) -or
        ($handshake -notmatch '"protocol_version":"specify-runtime\.v1"') -or
        ($handshake -notmatch '"artifact\.catalog"') -or
        ($handshake -notmatch '"artifact\.prepare"') -or
        ($handshake -notmatch '"artifact\.scaffold"') -or
        ($handshake -notmatch '"artifact\.show"') -or
        ($handshake -notmatch '"artifact\.submit"') -or
        ($handshake -notmatch '"validate\.spec"') -or
        ($handshake -notmatch '"workflow\.start"') -or
        ($handshake -notmatch '"workflow\.status"') -or
        ($handshake -notmatch '"workflow\.transition"')) {
        throw "Downloaded binary failed the specify-runtime API handshake"
    }

    $cognitionHelp = (& $candidate cognition --help 2>&1 | Out-String)
    foreach ($command in @("status", "query", "scan-prepare", "update")) {
        if ($cognitionHelp -notmatch [regex]::Escape($command)) {
            throw "Downloaded binary is missing cognition command: ${command}"
        }
    }

    Move-Item -LiteralPath $candidate -Destination $target -Force
} finally {
    Remove-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue
}

$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$InstallDir", "User")
    $env:PATH = "$env:PATH;$InstallDir"
}
Write-Host "==> Installed ${target}"
