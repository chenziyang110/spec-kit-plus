"""project-cognition runtime installer and project launcher binding."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlretrieve

from specify_cli.launcher import write_project_cognition_launcher_config

REPO = "chenziyang110/spec-kit-plus"
DEFAULT_VERSION = "latest"
REQUIRED_COMMANDS = ("build-from-scan",)


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


def _binary_supports_required_commands(binary: Path) -> bool:
    try:
        result = subprocess.run(
            [str(binary), "--help"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    output = f"{result.stdout}\n{result.stderr}"
    return all(command in output for command in REQUIRED_COMMANDS)


def _bundled_project_cognition_source() -> Path | None:
    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir / "core_pack" / "tools" / "project-cognition",
        module_dir.parent.parent / "tools" / "project-cognition",
    ]
    for candidate in candidates:
        if (candidate / "go.mod").is_file() and (candidate / "main.go").is_file():
            return candidate
    return None


def _build_from_source(source_dir: Path, dest: Path) -> Path:
    if shutil.which("go") is None:
        raise RuntimeError(
            "project-cognition release asset is missing required commands and Go is not on PATH"
        )

    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["go", "build", "-o", str(dest), "."],
        cwd=source_dir,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        message = "project-cognition release asset is missing required commands and source build failed"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message)
    if platform.system().lower() != "windows":
        os.chmod(dest, 0o755)
    return dest


def _ensure_supported_binary(binary: Path, version: str) -> Path:
    if _binary_supports_required_commands(binary):
        return binary

    return _build_supported_binary_from_source(
        binary,
        version,
        "release asset lacks required commands",
    )


def _build_supported_binary_from_source(binary: Path, version: str, reason: str) -> Path:
    source_dir = _bundled_project_cognition_source()
    if source_dir is not None:
        print(f"  Building project-cognition from bundled source because {reason}...")
        built = _build_from_source(source_dir, binary)
        if _binary_supports_required_commands(built):
            return built

    required = ", ".join(REQUIRED_COMMANDS)
    raise RuntimeError(
        "project-cognition runtime does not support required command(s): "
        f"{required}. Tried release asset {version}; install a newer project-cognition binary "
        "or set PROJECT_COGNITION_BIN to a compatible build."
    )


def ensure_binary(version: str = DEFAULT_VERSION, force: bool = False) -> Path:
    """Return a cached project-cognition binary, downloading release assets when needed."""

    override = os.environ.get("PROJECT_COGNITION_BIN", "").strip()
    if override:
        return Path(override).expanduser()

    dest = cached_executable()
    if dest.exists() and not force:
        if _binary_supports_required_commands(dest):
            return dest
        print("  Cached project-cognition is missing required commands; refreshing runtime...")
    if force and dest.exists():
        dest.unlink()
    try:
        binary = download(version)
    except Exception as exc:
        return _build_supported_binary_from_source(
            dest,
            version,
            f"release asset download failed ({exc})",
        )
    return _ensure_supported_binary(binary, version)


def write_project_launcher_config(project_root: Path, binary: Path) -> Path | None:
    """Persist the downloaded binary path for generated workflow commands."""

    return write_project_cognition_launcher_config(project_root, binary)
