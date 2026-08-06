"""Unified Specify runtime resolution, execution, installation, and binding."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence
from urllib.error import URLError
from urllib.request import Request, urlopen

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
RUNTIME_DOWNLOAD_MIRRORS_ENV = "SPECIFY_RUNTIME_DOWNLOAD_MIRRORS"
RUNTIME_DOWNLOAD_TIMEOUT_ENV = "SPECIFY_RUNTIME_DOWNLOAD_TIMEOUT"
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 60
# Free community GitHub-release mirrors for open-source installs (esp. regions
# where github.com is slow/unreachable). Official GitHub is always first unless
# SPECIFY_RUNTIME_DOWNLOAD_MIRRORS fully replaces the list.
# Template placeholders: {github_url} {repo} {version} {filename}
DEFAULT_DOWNLOAD_URL_TEMPLATES: tuple[str, ...] = (
    "{github_url}",
    "https://mirror.ghproxy.com/{github_url}",
    "https://ghproxy.net/{github_url}",
    "https://gh-proxy.com/{github_url}",
    "https://gitdl.cn/{github_url}",
)
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
    "artifact.checklist",
    "artifact.delete",
    "artifact.list",
    "artifact.patch",
    "artifact.prepare",
    "artifact.prune",
    "artifact.registry",
    "artifact.restore",
    "artifact.scaffold",
    "artifact.show",
    "artifact.submit",
    "cognition.build-from-scan",
    "cognition.archive-incompatible-store",
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
    "cognition.scan-packet",
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
    "design.preview-manifest",
    "design.preview-lint",
    "design.profiles",
    "design.ui-target",
    "design.ui-target-lint",
    "discussion.archive",
    "discussion.bind-consumer",
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
    "evidence.allocate",
    "evidence.import",
    "evidence.register",
    "evidence.show",
    "evidence.verify",
    "evidence.visual-compare",
    "hook.extension-plan",
    "hook.validate-artifacts",
    "hook.validate-commit",
    "hook.validate-state",
    "implement.closeout",
    "implement.deferral-confirm",
    "implement.deferral-propose",
    "implement.packet-compile",
    "implement.result-merge",
    "implement.resume-audit",
    "implement.task-accept",
    "implement.task-next",
    "implement.task-reopen",
    "implement.task-start",
    "implement.validation-finish",
    "implement.validation-start",
    "implement.validation-status",
    "learning.capture",
    "learning.capture-auto",
    "learning.list",
    "learning.metrics",
    "learning.promote",
    "learning.review",
    "learning.show",
    "learning.start",
    "learning.status",
    "prd-build.scaffold",
    "prd-build.status",
    "prd-scan.finalize",
    "prd-scan.init",
    "prd-scan.record-list",
    "prd-scan.record-remove",
    "prd-scan.record-show",
    "prd-scan.record-upsert",
    "prd-scan.status",
    "quick.archive",
    "quick.close",
    "quick.list",
    "quick.resume",
    "quick.status",
    "result.path",
    "result.submit",
    "review.closeout",
    "review.exception-confirm",
    "review.exception-propose",
    "review.prepare",
    "review.resume-audit",
    "review.target-bind",
    "review.validate",
    "run.cancel",
    "run.create",
    "run.events",
    "run.show",
    "run.supervise",
    "sp-teams.auto-dispatch",
    "sp-teams.complete-batch",
    "sp-teams.doctor",
    "sp-teams.live-probe",
    "sp-teams.result-template",
    "sp-teams.status",
    "sp-teams.submit-result",
    "sp-teams.sync-back",
    "tasks.build",
    "tasks.finalize",
    "tasks.handoff",
    "tasks.remove",
    "tasks.set-root",
    "tasks.upsert",
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
RELEASE_VERSION_PATTERN = re.compile(
    r"^v[0-9]+(?:\.[0-9]+){2}(?:[-.][0-9A-Za-z.-]+)?$"
)
SOURCE_REVISION_PATTERN = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")


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


def github_download_url(version: str = DEFAULT_VERSION) -> str:
    """Return the canonical GitHub Releases download URL for this platform asset."""

    filename = binary_filename()
    if version == "latest":
        return f"https://github.com/{REPO}/releases/latest/download/{filename}"
    return f"https://github.com/{REPO}/releases/download/{version}/{filename}"


def download_url(version: str = DEFAULT_VERSION) -> str:
    """Return the primary download URL (GitHub Releases)."""

    return github_download_url(version)


def _download_timeout_seconds() -> float:
    raw = os.environ.get(RUNTIME_DOWNLOAD_TIMEOUT_ENV, "").strip()
    if not raw:
        return float(DEFAULT_DOWNLOAD_TIMEOUT_SECONDS)
    try:
        value = float(raw)
    except ValueError as exc:
        raise SpecifyRuntimeError(
            f"{RUNTIME_DOWNLOAD_TIMEOUT_ENV} must be a positive number of seconds"
        ) from exc
    if value <= 0:
        raise SpecifyRuntimeError(
            f"{RUNTIME_DOWNLOAD_TIMEOUT_ENV} must be a positive number of seconds"
        )
    return value


def _download_url_templates() -> list[str]:
    """Return ordered download URL templates (official + free mirrors)."""

    override = os.environ.get(RUNTIME_DOWNLOAD_MIRRORS_ENV, "").strip()
    if override:
        templates = [part.strip() for part in override.split(",") if part.strip()]
        if not templates:
            raise SpecifyRuntimeError(
                f"{RUNTIME_DOWNLOAD_MIRRORS_ENV} is set but empty after parsing"
            )
        return templates
    return list(DEFAULT_DOWNLOAD_URL_TEMPLATES)


def download_urls(version: str = DEFAULT_VERSION) -> list[str]:
    """Return ordered candidate download URLs for the current platform asset."""

    filename = binary_filename()
    github_url = github_download_url(version)
    urls: list[str] = []
    seen: set[str] = set()
    for template in _download_url_templates():
        try:
            url = template.format(
                github_url=github_url,
                repo=REPO,
                version=version,
                filename=filename,
            )
        except (KeyError, IndexError, ValueError) as exc:
            raise SpecifyRuntimeError(
                f"Invalid download URL template {template!r}: {exc}"
            ) from exc
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def _download_from_url(url: str, destination: Path, *, timeout: float) -> None:
    request = Request(
        url,
        headers={
            "User-Agent": f"specify-cli/{DEFAULT_VERSION} ({RUNTIME_COMMAND}-installer)",
            "Accept": "application/octet-stream,*/*",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - HTTPS mirrors for public release assets
        status = getattr(response, "status", None) or response.getcode()
        if status is not None and int(status) >= 400:
            raise SpecifyRuntimeError(f"HTTP {status} from {url}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    size = destination.stat().st_size if destination.is_file() else 0
    if size < 1024:
        raise SpecifyRuntimeError(
            f"Downloaded asset from {url} is too small ({size} bytes); treating as failed"
        )


def download(version: str = DEFAULT_VERSION, destination: Path | None = None) -> Path:
    """Download the platform runtime asset, trying official + free CDN mirrors."""

    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    dest = destination or cached_executable()
    urls = download_urls(version)
    timeout = _download_timeout_seconds()
    filename = binary_filename()
    print(
        f"  Downloading {RUNTIME_COMMAND} {version} asset {filename} "
        f"({len(urls)} source(s))...",
        file=sys.stderr,
    )
    errors: list[str] = []
    for index, url in enumerate(urls, start=1):
        label = "github" if "github.com/" in url and "proxy" not in url else "mirror"
        print(f"  [{index}/{len(urls)}] trying {label}: {url}", file=sys.stderr)
        try:
            _download_from_url(url, dest, timeout=timeout)
        except (OSError, URLError, TimeoutError, SpecifyRuntimeError) as exc:
            errors.append(f"{url}: {exc}")
            dest.unlink(missing_ok=True)
            continue
        if platform.system().lower() != "windows":
            os.chmod(dest, 0o755)
        print(f"  Downloaded {RUNTIME_COMMAND} from {url}", file=sys.stderr)
        return dest
    detail = "; ".join(errors) if errors else "no download sources configured"
    raise SpecifyRuntimeError(
        f"Failed to download {RUNTIME_COMMAND} {version} asset {filename} "
        f"from all sources ({detail})"
    )


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


def _runtime_identity_is_compatible(
    info: dict[str, object],
    *,
    allow_dirty: bool,
) -> bool:
    dirty = info.get("dirty")
    if not isinstance(dirty, bool):
        return False
    return allow_dirty or not dirty


def _release_identity_is_compatible(
    info: dict[str, object],
    *,
    expected_version: str,
) -> bool:
    cli_version = str(info.get("cli_version") or "").strip()
    source_revision = str(info.get("source_revision") or "").strip()
    if RELEASE_VERSION_PATTERN.fullmatch(cli_version) is None:
        return False
    if expected_version != "latest" and cli_version != expected_version:
        return False
    return (
        SOURCE_REVISION_PATTERN.fullmatch(source_revision) is not None
        and info.get("dirty") is False
    )


def _binary_is_compatible(binary: Path, *, allow_dirty: bool = False) -> bool:
    if not binary.is_file():
        return False
    if not launcher_supports_required_commands((str(binary),)):
        return False
    info = _runtime_handshake((str(binary),))
    if info is None:
        return False
    return _runtime_identity_is_compatible(info, allow_dirty=allow_dirty)


def _release_binary_is_compatible(binary: Path, version: str) -> bool:
    if not binary.is_file() or not launcher_supports_required_commands((str(binary),)):
        return False
    info = _runtime_handshake((str(binary),))
    return info is not None and _release_identity_is_compatible(
        info,
        expected_version=version,
    )


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
    """Describe launcher binding and whether a source build may be used as fallback.

    ``source_build_required`` means a source-aligned build is *available as a
    fallback* when the release asset is missing or lacks required capabilities.
    It does **not** mean release download is skipped: ``ensure_binary`` always
    prefers a compatible prebuilt release first.
    """

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


def _cached_binary_is_compatible(binary: Path, version: str = DEFAULT_VERSION) -> bool:
    # Prefer reusing either a matching source-built binary or a compatible
    # release binary. Source-bound installs no longer reject release caches.
    if _source_build_marker_matches(binary) and _binary_is_compatible(
        binary,
        allow_dirty=True,
    ):
        return True
    return _release_binary_is_compatible(binary, version)


def _build_from_source(source_dir: Path, dest: Path) -> Path:
    if shutil.which("go") is None:
        raise SpecifyRuntimeError(
            f"{RUNTIME_COMMAND} source build requires Go on PATH "
            f"(used only after release download is unavailable or incompatible)"
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
        print(
            f"  Building {RUNTIME_COMMAND} from bundled source because {reason}...",
            file=sys.stderr,
        )
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
    if _release_binary_is_compatible(binary, version):
        return binary
    return _build_supported_binary_from_source(
        binary,
        version,
        "release asset lacks the required runtime protocol, capabilities, or release identity",
    )


def ensure_binary(version: str = DEFAULT_VERSION, force: bool = False) -> Path:
    """Return a cached specify-runtime binary, preferring release assets.

    Order:
    1. ``SPECIFY_RUNTIME_BIN`` when set and compatible
    2. Compatible cache hit (release or prior source build)
    3. Download the prebuilt GitHub release asset
    4. Fall back to bundled-source ``go build`` only if download fails or the
       release binary lacks required protocol/capabilities

    Source-bound / local-checkout installs (``source_build_required``) still
    enable the source-build fallback; they no longer skip release download.
    """

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
    if dest.exists() and not force and _cached_binary_is_compatible(dest, version):
        return dest

    with interprocess_lock(cache / f".{RUNTIME_COMMAND}.install.lock"):
        dest = cached_executable()
        if dest.exists() and not force and _cached_binary_is_compatible(dest, version):
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
    """Materialize and persist the project-local runtime entrypoint."""

    return write_runtime_launcher_config(project_root, binary)
