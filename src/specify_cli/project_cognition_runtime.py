"""project-cognition runtime installer and project launcher binding."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence
from urllib.request import urlretrieve

from specify_cli.atomic_io import atomic_write_text, interprocess_lock, read_local_state_text
from specify_cli.launcher import write_project_cognition_launcher_config

REPO = "chenziyang110/spec-kit-plus"
DEFAULT_VERSION = "latest"
EXPECTED_RUNTIME_PROTOCOL = "project-cognition.v2"
EXPECTED_SCHEMA_VERSION = 5
SOURCE_BUILD_MARKER_VERSION = 1
REQUIRED_COMMANDS = (
    "build-from-scan",
    "init-empty",
    "repair-status",
    "generate-ignore",
    "scan-set",
    "scan-prepare",
    "scan-lease",
    "scan-checkpoint",
    "scan-yield",
    "scan-requeue",
    "scan-status",
    "scan-accept",
    "changes",
    "closeout-plan",
    "semantic-intake --input",
    "semantic-audit-resume --input",
    "lexicon --mode",
    "compass --semantic-intake-file --query-plan-file",
    "expand --section",
    "update --payload-file --verification",
    "delta append --verification --generated-surface",
)


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


def download(version: str = DEFAULT_VERSION, destination: Path | None = None) -> Path:
    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    dest = destination or cached_executable()
    url = download_url(version)
    print(f"  Downloading project-cognition {version} from release asset {binary_filename()}...")
    urlretrieve(url, dest)
    if platform.system().lower() != "windows":
        os.chmod(dest, 0o755)
    return dest


def _launcher_help_output(
    argv: Sequence[str],
    *command: str,
    cwd: Path | None = None,
) -> str | None:
    try:
        result = subprocess.run(
            [*argv, *command, "--help"],
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
    return f"{result.stdout}\n{result.stderr}"


def launcher_supports_required_commands(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
) -> bool:
    """Return whether a launcher prefix exposes the required cognition surface."""

    if not argv:
        return False
    root_output = _launcher_help_output(argv, cwd=cwd)
    if root_output is None or not all(
        command.split()[0] in root_output for command in REQUIRED_COMMANDS
    ):
        return False

    required_help_flags: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
        (("update",), ("-payload-file", "-verification")),
        (("semantic-intake",), ("-input",)),
        (("semantic-audit-resume",), ("-input",)),
        (("lexicon",), ("-mode",)),
        (("compass",), ("-semantic-intake-file", "-query-plan-file")),
        (("expand",), ("-section",)),
        (("delta", "append"), ("-verification", "-generated-surface")),
        (("closeout-plan",), ("-workflow", "-delta-session")),
        (
            ("scan-prepare",),
            (
                "-force",
                "-scan-set",
                "-max-paths",
                "-max-bytes",
                "-worker-budget-tokens",
                "-context-window-tokens",
                "-inherited-context-tokens",
                "-system-skill-tokens",
                "-reserved-output-tokens",
                "-reserved-tool-tokens",
                "-reserved-reasoning-tokens",
                "-safety-percent",
            ),
        ),
        (("scan-lease",), ("-packet-id", "-worker-id", "-worker-capacity-tokens")),
        (("scan-checkpoint",), ("-packet-id", "-attempt-id", "-result")),
        (("scan-yield",), ("-packet-id", "-attempt-id")),
        (("scan-requeue",), ("-packet-id", "-attempt-id")),
        (("scan-accept",), ("-packet-id", "-attempt-id", "-result")),
    )
    for command, flags in required_help_flags:
        output = _launcher_help_output(argv, *command, cwd=cwd)
        if output is None or any(flag not in output for flag in flags):
            return False
    return True


def _binary_supports_required_commands(binary: Path) -> bool:
    return launcher_supports_required_commands((str(binary),))


def _runtime_info(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
) -> dict[str, object] | None:
    """Read the machine-verifiable contract and provenance exposed by a runtime."""

    if not argv:
        return None
    try:
        result = subprocess.run(
            [*argv, "version", "--format", "json"],
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
    return payload


def _binary_is_compatible(binary: Path, *, allow_dirty: bool = False) -> bool:
    """Return whether a binary implements the exact runtime and store contract."""

    if not _binary_supports_required_commands(binary):
        return False
    info = _runtime_info((str(binary),))
    if info is None:
        return False
    schema_version = info.get("schema_version")
    dirty = info.get("dirty")
    return (
        info.get("runtime_protocol") == EXPECTED_RUNTIME_PROTOCOL
        and isinstance(schema_version, int)
        and not isinstance(schema_version, bool)
        and schema_version == EXPECTED_SCHEMA_VERSION
        and isinstance(info.get("version"), str)
        and bool(str(info["version"]).strip())
        and isinstance(info.get("source_revision"), str)
        and bool(str(info["source_revision"]).strip())
        and isinstance(dirty, bool)
        and (allow_dirty or not dirty)
    )


def _allow_dirty_runtime() -> bool:
    """Allow an explicitly opted-in local development runtime."""

    return os.environ.get("PROJECT_COGNITION_ALLOW_DIRTY_RUNTIME", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


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


def _source_build_marker(binary: Path) -> Path:
    return binary.with_name(f"{binary.name}.source-build.json")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint(source_dir: Path) -> str:
    """Hash the Go inputs that can affect a bundled project-cognition build."""

    source_files = sorted(
        (
            path
            for path in source_dir.rglob("*")
            if path.is_file()
            and (path.suffix == ".go" or path.name in {"go.mod", "go.sum"})
        ),
        key=lambda path: path.relative_to(source_dir).as_posix(),
    )
    digest = hashlib.sha256()
    for path in source_files:
        relative = path.relative_to(source_dir).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _runtime_contract_fingerprint() -> str:
    contract = {
        "runtime_protocol": EXPECTED_RUNTIME_PROTOCOL,
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "required_commands": list(REQUIRED_COMMANDS),
    }
    encoded = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
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
    """Return whether a dirty cache entry is the current bundled-source build."""

    marker_path = _source_build_marker(binary)
    source_dir = _bundled_project_cognition_source()
    if source_dir is None or not marker_path.is_file() or not binary.is_file():
        return False
    try:
        marker = json.loads(
            read_local_state_text(marker_path, root=marker_path.parent)
        )
        if not isinstance(marker, dict):
            return False
        return (
            marker.get("marker_version") == SOURCE_BUILD_MARKER_VERSION
            and marker.get("binary_sha256") == _sha256_file(binary)
            and marker.get("runtime_contract_sha256")
            == _runtime_contract_fingerprint()
            and marker.get("source_sha256") == _source_fingerprint(source_dir)
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _cached_binary_is_compatible(binary: Path) -> bool:
    # The source-build marker is written only after a complete compatibility
    # probe. Its binary, source, and runtime-contract hashes make that result a
    # reusable cache attestation rather than an unchecked dirty-build bypass.
    if _source_build_marker_matches(binary):
        return True
    return _binary_is_compatible(binary, allow_dirty=_allow_dirty_runtime())


def _build_from_source(source_dir: Path, dest: Path) -> Path:
    if shutil.which("go") is None:
        raise RuntimeError(
            "project-cognition release asset is missing required commands and Go is not on PATH"
        )

    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    # ensure_binary reserves a unique candidate name with mkstemp. Go refuses
    # to build a Windows executable over that pre-existing non-object file.
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
        message = "project-cognition release asset is missing required commands and source build failed"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message)
    if platform.system().lower() != "windows":
        os.chmod(dest, 0o755)
    return dest


def _ensure_supported_binary(binary: Path, version: str) -> Path:
    if _cached_binary_is_compatible(binary):
        return binary

    return _build_supported_binary_from_source(
        binary,
        version,
        "release asset lacks the required runtime protocol, schema, commands, or provenance",
    )


def _build_supported_binary_from_source(binary: Path, version: str, reason: str) -> Path:
    source_dir = _bundled_project_cognition_source()
    if source_dir is not None:
        print(f"  Building project-cognition from bundled source because {reason}...")
        built = _build_from_source(source_dir, binary)
        # This path is an explicit local-source fallback. A dirty VCS marker is
        # therefore allowed only when a hash-bound marker proves the cached
        # binary still matches the current bundled source. Override binaries
        # remain fail-closed unless the developer opts in through the env flag.
        if _binary_is_compatible(built, allow_dirty=True):
            _write_source_build_marker(built, source_dir)
            return built

    required = ", ".join(REQUIRED_COMMANDS)
    raise RuntimeError(
        "project-cognition runtime is incompatible. Required runtime protocol "
        f"{EXPECTED_RUNTIME_PROTOCOL}, schema {EXPECTED_SCHEMA_VERSION}, and command support: "
        f"{required}. Tried release asset {version}; install a newer project-cognition binary "
        "or set PROJECT_COGNITION_BIN to a compatible clean build."
    )


def ensure_binary(version: str = DEFAULT_VERSION, force: bool = False) -> Path:
    """Return a cached project-cognition binary, downloading release assets when needed."""

    override = os.environ.get("PROJECT_COGNITION_BIN", "").strip()
    if override:
        binary = Path(override).expanduser()
        if _binary_is_compatible(binary, allow_dirty=_allow_dirty_runtime()):
            return binary
        required = ", ".join(REQUIRED_COMMANDS)
        raise RuntimeError(
            "PROJECT_COGNITION_BIN points to an incompatible project-cognition runtime. "
            f"Required protocol {EXPECTED_RUNTIME_PROTOCOL}, schema {EXPECTED_SCHEMA_VERSION}, "
            f"and command support: {required}. Dirty development builds require "
            "PROJECT_COGNITION_ALLOW_DIRTY_RUNTIME=1. Use a newer binary or unset "
            "PROJECT_COGNITION_BIN so specify can download or build a compatible runtime."
        )

    cache = cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    dest = cached_executable()
    # Cache hits are read-only and safe without the publication lock. Keeping
    # the expensive command/provenance probe outside the lock prevents many
    # concurrent init/repair processes from serializing behind a healthy cache.
    # Any miss is checked again under the lock before a candidate is published.
    if dest.exists() and not force and _cached_binary_is_compatible(dest):
        return dest

    with interprocess_lock(cache / ".project-cognition.install.lock"):
        # Recheck only after taking the process-wide install lock. Concurrent
        # init/repair calls may all observe a stale cache before the first one
        # publishes its candidate, especially under test runners and agent teams.
        dest = cached_executable()
        if dest.exists() and not force:
            if _cached_binary_is_compatible(dest):
                return dest
            print("  Cached project-cognition runtime is incompatible; refreshing runtime...")

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
    """Persist the downloaded binary path for generated workflow commands."""

    return write_project_cognition_launcher_config(project_root, binary)
