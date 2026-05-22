param(
    [string]$Version = $env:PROJECT_COGNITION_VERSION,
    [string]$Repo = $env:PROJECT_COGNITION_REPO,
    [string]$InstallDir = $env:PROJECT_COGNITION_INSTALL_DIR
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = 'latest'
}
if ([string]::IsNullOrWhiteSpace($Repo)) {
    $Repo = 'chenziyang110/spec-kit-plus'
}
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $HOME '.specify/bin'
}

$arch = switch ((Get-CimInstance Win32_OperatingSystem).OSArchitecture) {
    { $_ -match 'ARM64' } { 'arm64'; break }
    default { 'amd64' }
}

if ($arch -ne 'amd64') {
    throw "Unsupported Windows architecture for published project-cognition asset: $arch"
}

$asset = 'project-cognition-windows-amd64.exe'
if ($Version -eq 'latest') {
    $url = "https://github.com/$Repo/releases/latest/download/$asset"
} else {
    $url = "https://github.com/$Repo/releases/download/$Version/$asset"
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$target = Join-Path $InstallDir 'project-cognition.exe'

Write-Host "Downloading $url"
Invoke-WebRequest -Uri $url -OutFile $target

Write-Host "Installed project-cognition to $target"
$pathParts = ($env:PATH -split ';') | Where-Object { $_ }
if ($pathParts -notcontains $InstallDir) {
    Write-Host "Add this directory to PATH if needed:"
    Write-Host "  $InstallDir"
}
