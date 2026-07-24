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

from specify_cli.atomic_io import (
    atomic_write_text,
    interprocess_lock,
    read_local_state_text,
    safe_local_state_path,
)
from specify_cli.launcher import (
    resolve_runtime_launcher_argv,
    write_runtime_launcher_config,
)

REPO = "chenziyang110/spec-kit-plus"
EXPECTED_RUNTIME_PROTOCOL = "specify-runtime.v1"
SOURCE_BUILD_MARKER_VERSION = 1
RUNTIME_LAUNCHER_BINDING_VERSION = 1
REQUIRED_CAPABILITIES = (
    "api.handshake",
    "api.list",
    "api.schema",
    "api.show",
    "accept.closeout",
    "accept.prepare",
    "accept.route-repair",
    "accept.validate",
    "artifact.catalog",
    "artifact.prepare",
    "artifact.scaffold",
    "artifact.show",
    "artifact.submit",
    "cognition.build-from-scan",
    "cognition.changes",
    "cognition.claim-reconcile.apply",
    "cognition.claim-reconcile.prepare",
    "cognition.clear-dirty",
    "cognition.closeout-plan",
    "cognition.compass",
    "cognition.complete-refresh",
    "cognition.delta.append",
    "cognition.delta.begin",
    "cognition.delta.status",
    "cognition.discover",
    "cognition.expand",
    "cognition.generate-ignore",
    "cognition.init-empty",
    "cognition.lexicon",
    "cognition.mark-dirty",
    "cognition.query",
    "cognition.read",
    "cognition.record-refresh",
    "cognition.run",
    "cognition.scan-accept",
    "cognition.scan-checkpoint",
    "cognition.scan-lease",
    "cognition.scan-prepare",
    "cognition.scan-requeue",
    "cognition.scan-set",
    "cognition.scan-status",
    "cognition.scan-yield",
    "cognition.semantic-audit",
    "cognition.semantic-audit-resume",
    "cognition.semantic-intake",
    "cognition.status",
    "cognition.update",
    "cognition.validate-build",
    "cognition.validate-scan",
    "design.approve",
    "design.export",
    "design.import",
    "design.lint",
    "design.preview",
    "design.preview-lint",
    "design.ui-target",
    "design.ui-target-lint",
    "discussion.archive",
    "discussion.checkpoint",
    "discussion.close",
    "discussion.confirm-handoff",
    "discussion.init",
    "discussion.list",
    "discussion.mark-consumed",
    "discussion.mark-ready",
    "discussion.resume",
    "discussion.status",
    "discussion.validate-handoff",
    "discussion.write-handoff",
    "doctor.check",
    "hook.validate-artifacts",
    "hook.validate-commit",
    "hook.validate-state",
    "implement.closeout",
    "implement.deferral-confirm",
    "implement.deferral-propose",
    "implement.resume-audit",
    "implement.validation-finish",
    "implement.validation-start",
    "implement.validation-status",
    "integrate.close",
    "integrate.discover",
    "lane.resolve",
    "learning.capture",
    "learning.capture-auto",
    "learning.list",
    "learning.promote",
    "learning.show",
    "learning.start",
    "prd-build.status",
    "prd-scan.init",
    "prd-scan.status",
    "quick.archive",
    "quick.close",
    "quick.list",
    "quick.resume",
    "quick.status",
    "result.path",
    "result.submit",
    "review.closeout",
    "review.prepare",
    "review.resume-audit",
    "review.validate",
    "sp-teams.auto-dispatch",
    "sp-teams.complete-batch",
    "sp-teams.doctor",
    "sp-teams.live-probe",
    "sp-teams.result-template",
    "sp-teams.status",
    "sp-teams.submit-result",
    "sp-teams.sync-back",
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
PROJECT_RUNTIME_RELATIVE_DIR = Path(".specify") / "bin"


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


def runtime_executable_name() -> str:
    """Return the platform-native runtime executable filename."""

    return f"{RUNTIME_COMMAND}.exe" if platform.system().lower() == "windows" else RUNTIME_COMMAND


def project_runtime_relative_path() -> Path:
    """Return the stable project-relative runtime entrypoint path."""

    return PROJECT_RUNTIME_RELATIVE_DIR / runtime_executable_name()


def project_runtime_launcher_arg() -> str:
    """Return a shell-usable short runtime argv entry for generated guidance."""

    relative = project_runtime_relative_path()
    if platform.system().lower() == "windows":
        windows_relative = str(relative).replace("/", "\\")
        return f".\\{windows_relative}"
    return f"./{relative.as_posix()}"


def project_runtime_entrypoint_path(project_root: Path) -> Path:
    """Return the materialized runtime executable owned by one project."""

    root = Path(os.path.abspath(os.fspath(project_root.expanduser())))
    return safe_local_state_path(
        root / project_runtime_relative_path(),
        root=root,
    )


def content_addressed_runtime_path(digest: str) -> Path:
    """Return the immutable user-cache location for a runtime content digest."""

    normalized = digest.strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError("runtime digest must be a lowercase SHA-256 value")
    return cache_dir() / "runtimes" / normalized / runtime_executable_name()


def _atomic_link_or_copy(source: Path, destination: Path) -> None:
    """Materialize one regular file atomically, preferring a hardlink."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".candidate",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink(missing_ok=True)
    try:
        try:
            os.link(source, temporary)
        except OSError:
            shutil.copy2(source, temporary)
        if platform.system().lower() != "windows":
            os.chmod(temporary, temporary.stat().st_mode | 0o111)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _ensure_project_runtime_gitignore(project_root: Path) -> None:
    """Keep the materialized binary out of source control without hiding other helpers."""

    ignore_path = project_root / PROJECT_RUNTIME_RELATIVE_DIR / ".gitignore"
    ignored_names = (RUNTIME_COMMAND, f"{RUNTIME_COMMAND}.exe")
    try:
        existing = ignore_path.read_text(encoding="utf-8") if ignore_path.is_file() else ""
    except OSError:
        existing = ""
    lines = existing.splitlines()
    present = {line.strip() for line in lines}
    changed = False
    for name in ignored_names:
        if name not in present:
            lines.append(name)
            changed = True
    if changed or not ignore_path.exists():
        content = "\n".join(lines).strip() + "\n"
        atomic_write_text(ignore_path, content)


def materialize_project_runtime_entrypoint(project_root: Path, binary: str | Path) -> Path:
    """Pin a compatible runtime into the user cache and one project-local short path."""

    requested_source = Path(binary).expanduser()
    if requested_source.is_symlink():
        raise SpecifyRuntimeError(
            f"{RUNTIME_COMMAND} source must not be a symbolic link: {requested_source}"
        )
    source = requested_source.resolve(strict=True)
    if not source.is_file():
        raise SpecifyRuntimeError(f"{RUNTIME_COMMAND} source must be a regular file: {source}")

    digest = _sha256_file(source)
    cached = content_addressed_runtime_path(digest)
    if not cached.is_file() or cached.is_symlink() or _sha256_file(cached) != digest:
        _atomic_link_or_copy(source, cached)
    if cached.is_symlink() or not cached.is_file() or _sha256_file(cached) != digest:
        raise SpecifyRuntimeError(f"{RUNTIME_COMMAND} cache materialization failed integrity check")

    project_binary = project_runtime_entrypoint_path(project_root)
    if (
        not project_binary.is_file()
        or project_binary.is_symlink()
        or _sha256_file(project_binary) != digest
    ):
        _atomic_link_or_copy(cached, project_binary)
    if (
        project_binary.is_symlink()
        or not project_binary.is_file()
        or _sha256_file(project_binary) != digest
    ):
        raise SpecifyRuntimeError(f"{RUNTIME_COMMAND} project entrypoint failed integrity check")
    if platform.system().lower() != "windows":
        os.chmod(project_binary, project_binary.stat().st_mode | 0o111)
    _ensure_project_runtime_gitignore(project_root)
    return project_binary


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
        _local_runtime_source_checkout(),
    ]
    for candidate in candidates:
        if (
            candidate is not None
            and (candidate / "go.mod").is_file()
            and (candidate / "main.go").is_file()
        ):
            return candidate
    return None


def _local_runtime_source_checkout() -> Path | None:
    """Return the runtime source only when this module lives in a repo checkout."""

    candidate = Path(__file__).resolve().parent.parent.parent / "tools" / RUNTIME_COMMAND
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


def current_runtime_binding_metadata() -> dict[str, Any]:
    """Describe when the current Specify install requires a source-aligned runtime."""

    from specify_cli.launcher import resolve_specify_launcher_spec

    launcher = resolve_specify_launcher_spec()
    source_dir = _bundled_runtime_source()
    local_source_dir = _local_runtime_source_checkout()
    metadata: dict[str, Any] = {
        "binding_version": RUNTIME_LAUNCHER_BINDING_VERSION,
        "runtime_contract_sha256": _runtime_contract_fingerprint(),
        "specify_launcher_kind": launcher.kind,
        "source_build_required": False,
    }
    if launcher.kind == "source_bound":
        metadata["specify_launcher_argv"] = list(launcher.argv)
        if source_dir is not None:
            metadata["runtime_source_sha256"] = _source_fingerprint(source_dir)
            metadata["source_build_required"] = True
    elif launcher.kind == "local_environment" and local_source_dir is not None:
        metadata["runtime_source_sha256"] = _source_fingerprint(local_source_dir)
        metadata["source_build_required"] = True
    return metadata


def runtime_binding_metadata_matches(
    persisted: object,
    current: dict[str, Any] | None = None,
) -> bool:
    """Return whether a persisted runtime binding still matches the current source."""

    current = current or current_runtime_binding_metadata()
    if not bool(current.get("source_build_required")):
        return True
    if not isinstance(persisted, dict):
        return False
    return (
        persisted.get("binding_version") == current.get("binding_version")
        and persisted.get("runtime_contract_sha256")
        == current.get("runtime_contract_sha256")
        and persisted.get("runtime_source_sha256")
        == current.get("runtime_source_sha256")
        and persisted.get("specify_launcher_kind")
        == current.get("specify_launcher_kind")
        and persisted.get("specify_launcher_argv")
        == current.get("specify_launcher_argv")
        and bool(persisted.get("source_build_required"))
        == bool(current.get("source_build_required"))
    )


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
    binding = current_runtime_binding_metadata()
    if bool(binding.get("source_build_required")):
        return _source_build_marker_matches(binary) and _binary_is_compatible(
            binary,
            allow_dirty=_allow_dirty_runtime(),
        )
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
    binding = current_runtime_binding_metadata()
    if dest.exists() and not force and _cached_binary_is_compatible(dest):
        return dest

    with interprocess_lock(cache / f".{RUNTIME_COMMAND}.install.lock"):
        dest = cached_executable()
        if dest.exists() and not force and _cached_binary_is_compatible(dest):
            return dest
        if bool(binding.get("source_build_required")):
            return _build_supported_binary_from_source(
                dest,
                version,
                "the current Specify installation requires a source-aligned runtime",
            )

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
    """Materialize and persist the project-local runtime entrypoint."""

    return write_runtime_launcher_config(project_root, binary)
