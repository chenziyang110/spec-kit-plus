"""Unified Specify runtime resolution, execution, installation, and binding."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence
from urllib.request import urlretrieve

from packaging.version import InvalidVersion, Version

from specify_cli.atomic_io import atomic_write_text, interprocess_lock, read_local_state_text
from specify_cli.launcher import (
    resolve_runtime_launcher_argv,
    write_runtime_launcher_config,
)

REPO = "chenziyang110/spec-kit-plus"
EXPECTED_RUNTIME_PROTOCOL = "specify-runtime.v1"
SOURCE_BUILD_MARKER_VERSION = 1
REQUIRED_CAPABILITIES = (
    "api.handshake",
    "api.list",
    "artifact.catalog",
    "artifact.prepare",
    "artifact.scaffold",
    "artifact.show",
    "artifact.submit",
    "cognition.run",
    "validate.spec",
    "workflow.show",
    "workflow.enter",
    "workflow.next",
    "workflow.complete-stage",
    "workflow.transition",
    "workflow.reopen",
    "workflow.block",
    "workflow.resolve",
    "workflow.closeout",
)
RUNTIME_COMMAND = "specify-runtime"
RUNTIME_ENV = "SPECIFY_RUNTIME_BIN"
RUNTIME_CACHE_ENV = "SPECIFY_RUNTIME_CACHE_DIR"
ALLOW_DIRTY_ENV = "SPECIFY_RUNTIME_ALLOW_DIRTY"


def default_runtime_version() -> str:
    """Pin stable packages to their matching release and let dev builds track latest."""

    try:
        package_version = Version(importlib.metadata.version("specify-cli"))
    except (importlib.metadata.PackageNotFoundError, InvalidVersion):
        return "latest"
    if package_version.is_devrelease or package_version.is_prerelease or package_version.local:
        return "latest"
    return f"v{package_version.public}"


DEFAULT_VERSION = default_runtime_version()


class SpecifyRuntimeError(RuntimeError):
    """Raised when the unified runtime cannot be resolved or invoked."""


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
    goarch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    return goos, goarch


def binary_filename() -> str:
    goos, goarch = get_platform()
    ext = ".exe" if goos == "windows" else ""
    return f"{RUNTIME_COMMAND}-{goos}-{goarch}{ext}"


def cache_dir() -> Path:
    override = os.environ.get(RUNTIME_CACHE_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".specify" / "bin"


def cached_executable() -> Path:
    name = f"{RUNTIME_COMMAND}.exe" if platform.system().lower() == "windows" else RUNTIME_COMMAND
    return cache_dir() / name


def download_url(version: str = DEFAULT_VERSION) -> str:
    filename = binary_filename()
    if version == "latest":
        return f"https://github.com/{REPO}/releases/latest/download/{filename}"
    return f"https://github.com/{REPO}/releases/download/{version}/{filename}"


def download(version: str = DEFAULT_VERSION, destination: Path | None = None) -> Path:
    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    dest = destination or cached_executable()
    url = download_url(version)
    print(f"  Downloading {RUNTIME_COMMAND} {version} from release asset {binary_filename()}...")
    urlretrieve(url, dest)
    if platform.system().lower() != "windows":
        os.chmod(dest, 0o755)
    return dest


def _env_argv() -> list[str] | None:
    override = os.environ.get(RUNTIME_ENV, "").strip()
    if not override:
        return None
    return [override]


def resolve_specify_runtime_binary(project_root: Path | None = None) -> list[str]:
    """Resolve the runtime argv with project config > env > PATH precedence."""

    if project_root is not None:
        launcher = resolve_runtime_launcher_argv(project_root)
        if launcher:
            return list(launcher)

    env_argv = _env_argv()
    if env_argv:
        return env_argv

    resolved = shutil.which(RUNTIME_COMMAND)
    if resolved:
        return [resolved]

    raise SpecifyRuntimeError(
        f"{RUNTIME_COMMAND} binary not found; configure runtime_launcher, set {RUNTIME_ENV}, "
        f"or install {RUNTIME_COMMAND} on PATH"
    )


def run_specify_runtime(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
    install_if_missing: bool = False,
) -> dict[str, Any]:
    """Run specify-runtime and parse its JSON object stdout."""

    try:
        runtime_argv = resolve_specify_runtime_binary(cwd)
    except SpecifyRuntimeError:
        if not install_if_missing:
            raise
        runtime_argv = [str(ensure_binary())]
    command = [*runtime_argv, *args]
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (result.stdout or "").strip()
    if not output:
        if result.returncode != 0:
            detail = (result.stderr or f"{RUNTIME_COMMAND} failed").strip()
            raise SpecifyRuntimeError(f"{RUNTIME_COMMAND} {' '.join(args)} failed: {detail}")
        return {}
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise SpecifyRuntimeError(
            f"{RUNTIME_COMMAND} {' '.join(args)} returned invalid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SpecifyRuntimeError(f"{RUNTIME_COMMAND} {' '.join(args)} returned non-object JSON")
    if args[:1] == ["cognition"]:
        data = payload.get("data")
        if _is_runtime_envelope(payload):
            envelope_status = str(payload.get("status") or "").strip().lower()
            if (
                check
                and result.returncode != 0
                and envelope_status not in {"blocked", "repairable-block"}
            ):
                detail = str(
                    result.stderr
                    or payload.get("summary")
                    or output
                    or f"{RUNTIME_COMMAND} failed"
                ).strip()
                raise SpecifyRuntimeError(
                    f"{RUNTIME_COMMAND} {' '.join(args)} failed: {detail}"
                )
            if isinstance(data, dict):
                return data
    if check and result.returncode != 0:
        detail = str(
            result.stderr
            or payload.get("summary")
            or output
            or f"{RUNTIME_COMMAND} failed"
        ).strip()
        raise SpecifyRuntimeError(f"{RUNTIME_COMMAND} {' '.join(args)} failed: {detail}")
    return payload


def _is_runtime_envelope(payload: dict[str, Any]) -> bool:
    return all(
        key in payload
        for key in (
            "status",
            "summary",
            "data",
            "items",
            "blockers",
            "show_argv",
            "next_argv",
        )
    )


def _runtime_handshake(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
) -> dict[str, object] | None:
    if not argv:
        return None
    try:
        result = subprocess.run(
            [*argv, "api", "handshake", "--format", "json"],
            cwd=cwd,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def launcher_supports_required_commands(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
) -> bool:
    """Return whether a launcher prefix exposes the required runtime protocol."""

    info = _runtime_handshake(argv, cwd=cwd)
    if info is None:
        return False
    protocol = info.get("protocol_version") or info.get("runtime_protocol")
    capabilities = info.get("capability_ids") or info.get("capabilities")
    if protocol != EXPECTED_RUNTIME_PROTOCOL or not isinstance(capabilities, list):
        return False
    capability_set = {str(capability) for capability in capabilities}
    return all(capability in capability_set for capability in REQUIRED_CAPABILITIES)


def _binary_is_compatible(binary: Path, *, allow_dirty: bool = False) -> bool:
    if not binary.is_file():
        return False
    if not launcher_supports_required_commands((str(binary),)):
        return False
    info = _runtime_handshake((str(binary),))
    if info is None:
        return False
    dirty = info.get("dirty")
    return not isinstance(dirty, bool) or allow_dirty or not dirty


def _allow_dirty_runtime() -> bool:
    return os.environ.get(ALLOW_DIRTY_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _bundled_runtime_source() -> Path | None:
    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir / "core_pack" / "tools" / RUNTIME_COMMAND,
        module_dir.parent.parent / "tools" / RUNTIME_COMMAND,
    ]
    for candidate in candidates:
        if (candidate / "go.mod").is_file() and (candidate / "main.go").is_file():
            return candidate
    return None


def _source_build_marker(binary: Path) -> Path:
    return binary.with_name(f"{binary.name}.source-build.json")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint(source_dir: Path) -> str:
    source_files = sorted(
        (
            path
            for path in source_dir.rglob("*")
            if path.is_file() and (path.suffix == ".go" or path.name in {"go.mod", "go.sum"})
        ),
        key=lambda path: path.relative_to(source_dir).as_posix(),
    )
    digest = hashlib.sha256()
    for path in source_files:
        digest.update(path.relative_to(source_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _runtime_contract_fingerprint() -> str:
    contract = {
        "runtime_protocol": EXPECTED_RUNTIME_PROTOCOL,
        "required_capabilities": list(REQUIRED_CAPABILITIES),
    }
    encoded = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_source_build_marker(binary: Path, source_dir: Path) -> None:
    marker = {
        "marker_version": SOURCE_BUILD_MARKER_VERSION,
        "binary_sha256": _sha256_file(binary),
        "runtime_contract_sha256": _runtime_contract_fingerprint(),
        "source_sha256": _source_fingerprint(source_dir),
    }
    atomic_write_text(
        _source_build_marker(binary),
        json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n",
    )


def _source_build_marker_matches(binary: Path) -> bool:
    marker_path = _source_build_marker(binary)
    source_dir = _bundled_runtime_source()
    if source_dir is None or not marker_path.is_file() or not binary.is_file():
        return False
    try:
        marker = json.loads(read_local_state_text(marker_path, root=marker_path.parent))
        if not isinstance(marker, dict):
            return False
        return (
            marker.get("marker_version") == SOURCE_BUILD_MARKER_VERSION
            and marker.get("binary_sha256") == _sha256_file(binary)
            and marker.get("runtime_contract_sha256") == _runtime_contract_fingerprint()
            and marker.get("source_sha256") == _source_fingerprint(source_dir)
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _cached_binary_is_compatible(binary: Path) -> bool:
    if _source_build_marker_matches(binary):
        return True
    return _binary_is_compatible(binary, allow_dirty=_allow_dirty_runtime())


def _build_from_source(source_dir: Path, dest: Path) -> Path:
    if shutil.which("go") is None:
        raise SpecifyRuntimeError(
            f"{RUNTIME_COMMAND} release asset is unavailable and Go is not on PATH"
        )

    cache_dir().mkdir(parents=True, exist_ok=True)
    dest.unlink(missing_ok=True)
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
        message = f"{RUNTIME_COMMAND} source build failed"
        if detail:
            message = f"{message}: {detail}"
        raise SpecifyRuntimeError(message)
    if platform.system().lower() != "windows":
        os.chmod(dest, 0o755)
    return dest


def _build_supported_binary_from_source(binary: Path, version: str, reason: str) -> Path:
    source_dir = _bundled_runtime_source()
    if source_dir is not None:
        print(f"  Building {RUNTIME_COMMAND} from bundled source because {reason}...")
        built = _build_from_source(source_dir, binary)
        if _binary_is_compatible(built, allow_dirty=True):
            _write_source_build_marker(built, source_dir)
            return built

    required = ", ".join(REQUIRED_CAPABILITIES)
    raise SpecifyRuntimeError(
        f"{RUNTIME_COMMAND} is incompatible. Required protocol "
        f"{EXPECTED_RUNTIME_PROTOCOL} and capabilities: {required}. Tried release asset "
        f"{version}; install a newer {RUNTIME_COMMAND} binary or set {RUNTIME_ENV}."
    )


def _ensure_supported_binary(binary: Path, version: str) -> Path:
    if _cached_binary_is_compatible(binary):
        return binary
    return _build_supported_binary_from_source(
        binary,
        version,
        "release asset lacks the required runtime protocol or capabilities",
    )


def ensure_binary(version: str = DEFAULT_VERSION, force: bool = False) -> Path:
    """Return a cached specify-runtime binary, downloading release assets when needed."""

    env_argv = _env_argv()
    if env_argv:
        binary = Path(env_argv[0]).expanduser()
        if _binary_is_compatible(binary, allow_dirty=_allow_dirty_runtime()):
            return binary
        raise SpecifyRuntimeError(
            f"{RUNTIME_ENV} points to an incompatible {RUNTIME_COMMAND} runtime. "
            f"Dirty development builds require {ALLOW_DIRTY_ENV}=1."
        )

    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    dest = cached_executable()
    if dest.exists() and not force and _cached_binary_is_compatible(dest):
        return dest

    with interprocess_lock(cache / f".{RUNTIME_COMMAND}.install.lock"):
        dest = cached_executable()
        if dest.exists() and not force and _cached_binary_is_compatible(dest):
            return dest

        candidate_fd, candidate_name = tempfile.mkstemp(
            prefix=f".{dest.name}.", suffix=".candidate", dir=cache
        )
        os.close(candidate_fd)
        candidate = Path(candidate_name)
        candidate_marker = _source_build_marker(candidate)
        dest_marker = _source_build_marker(dest)
        try:
            try:
                binary = download(version, candidate)
            except Exception as exc:
                binary = _build_supported_binary_from_source(
                    candidate,
                    version,
                    f"release asset download failed ({exc})",
                )
            binary = _ensure_supported_binary(binary, version)
            os.replace(binary, dest)
            if candidate_marker.is_file():
                os.replace(candidate_marker, dest_marker)
            else:
                dest_marker.unlink(missing_ok=True)
            if platform.system().lower() != "windows":
                os.chmod(dest, 0o755)
            return dest
        finally:
            candidate.unlink(missing_ok=True)
            candidate_marker.unlink(missing_ok=True)


def write_project_launcher_config(project_root: Path, binary: Path) -> Path | None:
    """Persist the downloaded runtime path for generated workflow commands."""

    return write_runtime_launcher_config(project_root, binary)
