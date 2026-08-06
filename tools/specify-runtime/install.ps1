param(
    [string]$Version = $env:SPECIFY_RUNTIME_VERSION,
    [string]$Repo = $env:SPECIFY_RUNTIME_REPO,
    [string]$InstallDir = $env:SPECIFY_RUNTIME_INSTALL_DIR
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Version)) { $Version = "latest" }
if ([string]::IsNullOrWhiteSpace($Repo)) { $Repo = "chenziyang110/spec-kit-plus" }
if (($Version -ne "latest") -and ($Version -notmatch '^v[0-9]+(\.[0-9]+){2}([.-][0-9A-Za-z.-]+)?$')) {
    throw "SPECIFY_RUNTIME_VERSION must be latest or a concrete release tag such as v0.6.6"
}
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\specify-runtime"
}
if (-not [Environment]::Is64BitOperatingSystem) {
    throw "Only windows/amd64 release assets are published"
}

$binary = "specify-runtime"
$asset = "${binary}-windows-amd64.exe"
$githubUrl = if ($Version -eq "latest") {
    "https://github.com/${Repo}/releases/latest/download/${asset}"
} else {
    "https://github.com/${Repo}/releases/download/${Version}/${asset}"
}

# Official GitHub first, then free community mirrors (override with SPECIFY_RUNTIME_DOWNLOAD_MIRRORS).
$templates = if (-not [string]::IsNullOrWhiteSpace($env:SPECIFY_RUNTIME_DOWNLOAD_MIRRORS)) {
    $env:SPECIFY_RUNTIME_DOWNLOAD_MIRRORS -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
} else {
    @(
        "{github_url}",
        "https://mirror.ghproxy.com/{github_url}",
        "https://ghproxy.net/{github_url}",
        "https://gh-proxy.com/{github_url}",
        "https://gitdl.cn/{github_url}"
    )
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$target = Join-Path $InstallDir "${binary}.exe"
$candidate = Join-Path $InstallDir ".${binary}.$PID.candidate.exe"

try {
    $ProgressPreference = "SilentlyContinue"
    $downloaded = $false
    $errors = New-Object System.Collections.Generic.List[string]
    foreach ($template in $templates) {
        $url = $template.
            Replace("{github_url}", $githubUrl).
            Replace("{repo}", $Repo).
            Replace("{version}", $Version).
            Replace("{filename}", $asset)
        Write-Host "    trying $url"
        try {
            Invoke-WebRequest -Uri $url -OutFile $candidate
            if ((Test-Path $candidate) -and ((Get-Item $candidate).Length -ge 1024)) {
                $downloaded = $true
                break
            }
            $errors.Add("${url}: empty or too-small response") | Out-Null
        } catch {
            $errors.Add("${url}: $($_.Exception.Message)") | Out-Null
            if (Test-Path $candidate) { Remove-Item -Force $candidate -ErrorAction SilentlyContinue }
        }
    }
    if (-not $downloaded) {
        throw "Failed to download ${asset} from all configured sources: $($errors -join '; ')"
    }

    $handshake = (& $candidate api handshake --format json 2>&1 | Out-String)
    if (($LASTEXITCODE -ne 0) -or
        ($handshake -notmatch '"protocol_version":"specify-runtime\.v1"') -or
        ($handshake -notmatch '"artifact\.catalog"') -or
        ($handshake -notmatch '"artifact\.checklist"') -or
        ($handshake -notmatch '"artifact\.delete"') -or
        ($handshake -notmatch '"artifact\.list"') -or
        ($handshake -notmatch '"artifact\.patch"') -or
        ($handshake -notmatch '"artifact\.prepare"') -or
        ($handshake -notmatch '"artifact\.restore"') -or
        ($handshake -notmatch '"artifact\.scaffold"') -or
        ($handshake -notmatch '"artifact\.show"') -or
        ($handshake -notmatch '"artifact\.submit"') -or
        ($handshake -notmatch '"cognition\.archive-incompatible-store"') -or
        ($handshake -notmatch '"cognition\.run"') -or
        ($handshake -notmatch '"cognition\.scan-packet"') -or
        ($handshake -notmatch '"implement\.task-reopen"') -or
        ($handshake -notmatch '"validate\.spec"') -or
        ($handshake -notmatch '"workflow\.show"') -or
        ($handshake -notmatch '"workflow\.enter"') -or
        ($handshake -notmatch '"workflow\.next"') -or
        ($handshake -notmatch '"workflow\.complete-stage"') -or
        ($handshake -notmatch '"workflow\.transition"') -or
        ($handshake -notmatch '"workflow\.reopen"') -or
        ($handshake -notmatch '"workflow\.block"') -or
        ($handshake -notmatch '"workflow\.resolve"') -or
        ($handshake -notmatch '"workflow\.closeout"')) {
        throw "Downloaded binary failed the specify-runtime API handshake"
    }

    try {
        $handshakePayload = $handshake | ConvertFrom-Json
    } catch {
        throw "Downloaded binary returned an invalid specify-runtime API handshake"
    }
    $versionText = (& $candidate version --format json 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) {
        throw "Downloaded binary failed to report its release identity"
    }
    try {
        $versionPayload = $versionText | ConvertFrom-Json
    } catch {
        throw "Downloaded binary returned invalid version metadata"
    }
    $actualVersion = [string]$versionPayload.data.cli_version
    $sourceRevision = [string]$versionPayload.data.source_revision
    $dirty = $versionPayload.data.dirty
    $handshakeVersion = [string]$handshakePayload.data.cli_version
    $handshakeSourceRevision = [string]$handshakePayload.data.source_revision
    $handshakeDirty = $handshakePayload.data.dirty
    if ($Version -eq "latest") {
        if ($actualVersion -notmatch '^v[0-9]+(\.[0-9]+){2}([.-][0-9A-Za-z.-]+)?$') {
            throw "Downloaded latest binary has no concrete release version: ${actualVersion}"
        }
    } elseif ($actualVersion -ne $Version) {
        throw "Downloaded binary version ${actualVersion} does not match requested ${Version}"
    }
    if ($handshakeVersion -ne $actualVersion) {
        throw "Downloaded binary reports inconsistent version identity"
    }
    if (($handshakeSourceRevision -ne $sourceRevision) -or
        ($handshakeDirty -isnot [bool]) -or
        ($handshakeDirty -ne $dirty)) {
        throw "Downloaded binary reports inconsistent release provenance"
    }
    if (($sourceRevision -notmatch '^([0-9a-fA-F]{40}|[0-9a-fA-F]{64})$') -or
        ($dirty -isnot [bool]) -or $dirty) {
        throw "Downloaded binary has invalid release provenance"
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
