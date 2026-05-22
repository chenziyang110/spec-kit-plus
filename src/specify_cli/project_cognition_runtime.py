"""project-cognition runtime installer and project launcher binding."""

from __future__ import annotations

import os
import platform
from pathlib import Path
from urllib.request import urlretrieve

from specify_cli.launcher import write_project_cognition_launcher_config

REPO = "chenziyang110/spec-kit-plus"
DEFAULT_VERSION = "latest"


def get_platform() -> tuple[str, str]:
    system = platform.system().lower()
    if system == "darwin":
        goos = "darwin"
    elif system == "windows":
        goos = "windows"
    else:
        goos = "linux"

    if goos == "windows":
        return goos, "amd64"

    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        goarch = "arm64"
    else:
        goarch = "amd64"
    return goos, goarch


def binary_filename() -> str:
    goos, goarch = get_platform()
    ext = ".exe" if goos == "windows" else ""
    return f"project-cognition-{goos}-{goarch}{ext}"


def cache_dir() -> Path:
    override = os.environ.get("PROJECT_COGNITION_CACHE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".specify" / "bin"


def cached_executable() -> Path:
    goos, _ = get_platform()
    name = "project-cognition.exe" if goos == "windows" else "project-cognition"
    return cache_dir() / name


def download_url(version: str = DEFAULT_VERSION) -> str:
    filename = binary_filename()
    if version == "latest":
        return f"https://github.com/{REPO}/releases/latest/download/{filename}"
    return f"https://github.com/{REPO}/releases/download/{version}/{filename}"


def download(version: str = DEFAULT_VERSION) -> Path:
    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    dest = cached_executable()
    url = download_url(version)
    print(f"  Downloading project-cognition {version} from release asset {binary_filename()}...")
    urlretrieve(url, dest)
    if platform.system().lower() != "windows":
        os.chmod(dest, 0o755)
    return dest


def ensure_binary(version: str = DEFAULT_VERSION, force: bool = False) -> Path:
    """Return a cached project-cognition binary, downloading release assets when needed."""

    override = os.environ.get("PROJECT_COGNITION_BIN", "").strip()
    if override:
        return Path(override).expanduser()

    dest = cached_executable()
    if dest.exists() and not force:
        return dest
    if force and dest.exists():
        dest.unlink()
    return download(version)


def write_project_launcher_config(project_root: Path, binary: Path) -> Path | None:
    """Persist the downloaded binary path for generated workflow commands."""

    return write_project_cognition_launcher_config(project_root, binary)
