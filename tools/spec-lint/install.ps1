param(
    [string]$Version = "latest"
)

$ErrorActionPreference = "Stop"

$repo = "chenziyang110/spec-kit-plus"
$binary = "spec-lint"

# ---- detect arch ----
$arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "x86" }
$filename = "${binary}-windows-${arch}.exe"

if ($Version -eq "latest") {
    $url = "https://github.com/${repo}/releases/latest/download/${filename}"
} else {
    $url = "https://github.com/${repo}/releases/download/${Version}/${filename}"
}

# ---- install directory ----
$installDir = "$env:LOCALAPPDATA\Programs\spec-lint"
New-Item -ItemType Directory -Force -Path $installDir | Out-Null

Write-Host "==> spec-lint installer"
Write-Host "    platform: windows/${arch}"
Write-Host "    install:  ${installDir}\${binary}.exe"
Write-Host ""

# ---- download ----
Write-Host "==> Downloading..."
try {
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $url -OutFile "$installDir\${binary}.exe"
} catch {
    Write-Host "Error: download failed from ${url}"
    Write-Host "Make sure a release exists with binaries attached."
    Write-Host "You can also install with Go: go install github.com/${repo}/tools/spec-lint@latest"
    exit 1
}

# ---- verify ----
Write-Host "==> Verifying..."
& "$installDir\${binary}.exe" --version

# ---- PATH ----
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$installDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$installDir", "User")
    $env:PATH = "$env:PATH;$installDir"
    Write-Host ""
    Write-Host "==> Added to user PATH (restart terminal to use from any directory)"
}

Write-Host ""
Write-Host "==> spec-lint installed successfully."
Write-Host "    Run 'spec-lint -dir <feature-dir>' to validate a spec."
