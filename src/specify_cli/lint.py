"""spec-lint wrapper: auto-download and execute the quality gate binary."""

import os
import platform
import subprocess
from pathlib import Path
from urllib.request import urlretrieve

REPO = "chenziyang110/spec-kit-plus"
DEFAULT_VERSION = "v0.1.0-spec-lint"

# ---- platform detection ----


def _get_platform() -> tuple[str, str]:
    system = platform.system().lower()
    goos = "linux"
    if system == "darwin":
        goos = "darwin"
    elif system == "windows":
        goos = "windows"

    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        goarch = "amd64"
    elif machine in ("arm64", "aarch64"):
        goarch = "arm64"
    else:
        goarch = "amd64"

    return goos, goarch


def _binary_filename() -> str:
    goos, goarch = _get_platform()
    ext = ".exe" if goos == "windows" else ""
    return f"spec-lint-{goos}-{goarch}{ext}"


def _cache_dir() -> Path:
    return Path.home() / ".specify" / "bin"


def _cached_executable() -> Path:
    goos, _ = _get_platform()
    name = "spec-lint.exe" if goos == "windows" else "spec-lint"
    return _cache_dir() / name


# ---- download ----

def _download(version: str) -> Path:
    cache = _cache_dir()
    cache.mkdir(parents=True, exist_ok=True)

    dest = _cached_executable()
    filename = _binary_filename()
    url = f"https://github.com/{REPO}/releases/download/{version}/{filename}"

    print(f"  Downloading spec-lint {version} for {filename.rsplit('-', 2)[1]}/{filename.rsplit('-', 2)[2].removesuffix('.exe')}...")
    urlretrieve(url, dest)

    if platform.system().lower() != "windows":
        os.chmod(dest, 0o755)

    return dest


# ---- public API ----

def ensure_binary(version: str = DEFAULT_VERSION, force: bool = False) -> Path:
    """Return path to spec-lint binary, downloading if needed."""
    dest = _cached_executable()
    if dest.exists() and not force:
        return dest
    if force and dest.exists():
        dest.unlink()
    return _download(version)


def run(args: list[str], version: str = DEFAULT_VERSION, force: bool = False) -> int:
    """Run spec-lint with the given arguments. Returns exit code."""
    binary = ensure_binary(version=version, force=force)
    return subprocess.run([str(binary)] + args).returncode
