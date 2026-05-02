"""Helpers for invoking the same ``specify`` source that initialized a project."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata as importlib_metadata
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.integrations.manifest import IntegrationManifest


SPECIFY_PACKAGE_NAME = "specify-cli"
SPECIFY_CONFIG_FILE = ".specify/config.json"
SPECIFY_LAUNCHER_CONFIG_KEY = "specify_launcher"
HOOK_RUNTIME_ARGV_ENV = "SPECIFY_HOOK_RUNTIME_ARGV"
HOOK_RUNTIME_COMMAND_ENV = "SPECIFY_HOOK_RUNTIME_COMMAND"
HOOK_LAUNCHER_POSIX = "specify-hook"
HOOK_LAUNCHER_WINDOWS = "specify-hook.cmd"
HOOK_LAUNCHER_PYTHON = "specify-hook.py"
DIRECT_HOOK_DISPATCH_MARKERS = (
    "claude-hook-dispatch.py",
    "gemini-hook-dispatch.py",
)


@dataclass(frozen=True)
class SpecifyLauncherSpec:
    """Command forms that invoke a preferred ``specify`` install source."""

    command: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class HookRuntimeSpec:
    """Command forms that invoke the stable native-hook Python launcher."""

    command: str
    argv: tuple[str, ...]
    source: str


def render_command(argv: tuple[str, ...]) -> str:
    """Render *argv* as an operator-readable command string."""

    if os.name == "nt":
        return subprocess.list2cmdline(list(argv))
    return " ".join(argv)


def default_specify_launcher_spec() -> SpecifyLauncherSpec:
    argv = ("specify",)
    return SpecifyLauncherSpec(command=render_command(argv), argv=argv)


def resolve_specify_launcher_spec() -> SpecifyLauncherSpec:
    """Return the best available launcher for the current ``specify`` source.

    Git direct-url installs are converted into a ``uvx --from git+... specify``
    launcher so generated project hooks do not accidentally call an older
    ``specify`` executable that happens to appear earlier on PATH.
    """

    default = default_specify_launcher_spec()

    try:
        distribution = importlib_metadata.distribution(SPECIFY_PACKAGE_NAME)
    except importlib_metadata.PackageNotFoundError:
        return default

    try:
        direct_url_text = distribution.read_text("direct_url.json")
    except FileNotFoundError:
        return default

    if not direct_url_text:
        return default

    try:
        payload = json.loads(direct_url_text)
    except json.JSONDecodeError:
        return default

    if not isinstance(payload, dict):
        return default

    vcs_info = payload.get("vcs_info")
    url = payload.get("url")
    if not isinstance(vcs_info, dict) or not isinstance(url, str):
        return default
    if vcs_info.get("vcs") != "git" or not url.strip():
        return default

    commit_id = str(vcs_info.get("commit_id", "")).strip()
    source = url if url.startswith("git+") else f"git+{url}"
    if commit_id:
        source = f"{source}@{commit_id}"

    if not shutil.which("uvx"):
        return default

    argv = ("uvx", "--from", source, "specify")
    return SpecifyLauncherSpec(command=render_command(argv), argv=argv)


def _hook_launcher_assets_dir() -> Path | None:
    package_root = Path(__file__).resolve().parent
    for candidate in (
        package_root / "core_pack" / "shared_hooks",
        package_root / "shared_hooks",
    ):
        if candidate.is_dir():
            return candidate
    return None


def _argv_from_env(name: str) -> tuple[str, ...] | None:
    raw_json = os.environ.get(f"{name}_ARGV", "").strip()
    if raw_json:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list) and parsed and all(isinstance(item, str) and item for item in parsed):
            return tuple(parsed)

    raw_command = os.environ.get(f"{name}_COMMAND", "").strip()
    if raw_command:
        try:
            parsed_command = shlex.split(raw_command, posix=os.name != "nt")
        except ValueError:
            parsed_command = []
        if parsed_command:
            return tuple(parsed_command)

    return None


def _project_hook_python_candidates(project_root: Path) -> list[Path]:
    return [
        project_root / ".venv" / "Scripts" / "python.exe",
        project_root / ".venv" / "bin" / "python",
    ]


def resolve_hook_runtime_spec(project_root: Path) -> HookRuntimeSpec | None:
    """Resolve the runtime that should launch ``.specify/bin/specify-hook.py``."""

    if env_argv := _argv_from_env("SPECIFY_HOOK_RUNTIME"):
        return HookRuntimeSpec(
            command=render_command(env_argv),
            argv=env_argv,
            source=f"env:{HOOK_RUNTIME_ARGV_ENV if os.environ.get(HOOK_RUNTIME_ARGV_ENV) else HOOK_RUNTIME_COMMAND_ENV}",
        )

    for candidate in _project_hook_python_candidates(project_root):
        if candidate.exists():
            argv = (str(candidate),)
            return HookRuntimeSpec(
                command=render_command(argv),
                argv=argv,
                source="project-venv",
            )

    system_candidates: list[tuple[tuple[str, ...], str]] = []
    if os.name == "nt":
        if shutil.which("py"):
            system_candidates.append((("py",), "system:py"))
        if shutil.which("python"):
            system_candidates.append((("python",), "system:python"))
    else:
        if shutil.which("python3"):
            system_candidates.append((("/usr/bin/env", "python3"), "system:python3"))
        if shutil.which("python"):
            system_candidates.append((("/usr/bin/env", "python"), "system:python"))

    if system_candidates:
        argv, source = system_candidates[0]
        return HookRuntimeSpec(
            command=render_command(argv),
            argv=argv,
            source=source,
        )
    return None


def render_hook_launcher_command(
    integration_key: str,
    route: str,
    *,
    project_dir_env_var: str | None = None,
) -> str:
    """Render the native hook command that targets the shared launcher."""

    launcher_name = HOOK_LAUNCHER_WINDOWS if os.name == "nt" else HOOK_LAUNCHER_POSIX
    launcher_path = f".specify/bin/{launcher_name}"
    if project_dir_env_var:
        project_root = f'"$env:{project_dir_env_var}"' if os.name == "nt" else f'"${project_dir_env_var}"'
        return f"{project_root}/{launcher_path} {integration_key} {route}"
    return f"{launcher_path} {integration_key} {route}"


def install_shared_hook_launcher_assets(
    project_root: Path,
    *,
    manifest: IntegrationManifest | None = None,
) -> list[Path]:
    """Install shared native-hook launcher assets into ``.specify/bin/``."""

    assets_dir = _hook_launcher_assets_dir()
    if not assets_dir:
        return []

    created: list[Path] = []
    dest_dir = project_root / ".specify" / "bin"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for src_file in sorted(assets_dir.iterdir()):
        if not src_file.is_file():
            continue
        dst_file = dest_dir / src_file.name
        shutil.copy2(src_file, dst_file)
        if dst_file.name == HOOK_LAUNCHER_POSIX:
            dst_file.chmod(dst_file.stat().st_mode | 0o111)
        if manifest is not None:
            rel = dst_file.resolve().relative_to(project_root.resolve())
            manifest.record_existing(rel)
        created.append(dst_file)
    return created


def _load_config(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _normalize_launcher_payload(payload: Any) -> SpecifyLauncherSpec | None:
    if not isinstance(payload, dict):
        return None
    argv = payload.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        return None

    normalized_argv = tuple(argv)
    command = payload.get("command")
    if not isinstance(command, str) or not command.strip():
        command = render_command(normalized_argv)

    return SpecifyLauncherSpec(command=command.strip(), argv=normalized_argv)


def _launcher_payload(launcher: SpecifyLauncherSpec) -> dict[str, Any]:
    return {
        "command": launcher.command,
        "argv": list(launcher.argv),
    }


def load_project_specify_launcher(project_root: Path) -> SpecifyLauncherSpec | None:
    """Load the persisted project launcher from ``.specify/config.json``."""

    config_path = project_root / SPECIFY_CONFIG_FILE
    payload = _load_config(config_path)
    if payload is None:
        return None
    return _normalize_launcher_payload(payload.get(SPECIFY_LAUNCHER_CONFIG_KEY))


def project_specify_subcommand(
    project_root: Path,
    args: list[str] | tuple[str, ...],
) -> SpecifyLauncherSpec | None:
    """Compose a trusted launcher-backed ``specify`` subcommand for a project."""

    launcher = load_project_specify_launcher(project_root)
    if launcher is None:
        return None

    normalized_args = tuple(args)
    argv = (*launcher.argv, *normalized_args)
    return SpecifyLauncherSpec(command=render_command(argv), argv=argv)


def render_project_launcher_placeholders(project_root: Path, body: str) -> str:
    """Expand launcher placeholders in template or guidance text."""

    if not isinstance(body, str) or "{{specify-" not in body:
        return body

    launcher = load_project_specify_launcher(project_root)
    default = default_specify_launcher_spec()
    active_launcher = launcher or default

    rendered = body.replace("{{specify-cli}}", active_launcher.command)
    pattern = re.compile(r"\{\{specify-subcmd:(?P<args>[^{}]+)\}\}")

    def replace(match: re.Match[str]) -> str:
        args_text = match.group("args").strip()
        if not args_text:
            return match.group(0)
        try:
            tokens = tuple(shlex.split(args_text, posix=os.name != "nt"))
        except ValueError:
            return match.group(0)
        if not tokens:
            return match.group(0)
        if launcher is None:
            return render_command((*default.argv, *tokens))
        subcommand = project_specify_subcommand(project_root, tokens)
        return subcommand.command if subcommand is not None else render_command((*default.argv, *tokens))

    return pattern.sub(replace, rendered)


def write_project_specify_launcher_config(
    project_root: Path,
    launcher: SpecifyLauncherSpec | None = None,
) -> Path | None:
    """Persist the preferred ``specify`` launcher into ``.specify/config.json``.

    Returns the written config path, or ``None`` when there is no source-bound
    launcher to persist. Existing user/project keys are preserved.
    """

    resolved = launcher or resolve_specify_launcher_spec()
    if resolved.argv == default_specify_launcher_spec().argv:
        return None

    config_path = project_root / SPECIFY_CONFIG_FILE
    payload = _load_config(config_path)
    if payload is None:
        return None

    desired = _launcher_payload(resolved)
    if payload.get(SPECIFY_LAUNCHER_CONFIG_KEY) == desired:
        return config_path

    payload[SPECIFY_LAUNCHER_CONFIG_KEY] = desired
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path


def diagnose_project_runtime_compatibility(project_root: Path) -> list[dict[str, str]]:
    """Inspect persisted launcher and generated runtime surfaces for stale or broken state."""

    issues: list[dict[str, str]] = []

    launcher = load_project_specify_launcher(project_root)
    if launcher is not None and launcher.argv:
        launcher_entry = launcher.argv[0]
        launcher_exists = Path(launcher_entry).exists() if Path(launcher_entry).is_absolute() else shutil.which(launcher_entry)
        if not launcher_exists:
            issues.append(
                {
                    "code": "broken-project-launcher",
                    "summary": "Persisted project launcher is configured but unavailable.",
                    "repair": "Repair `.specify/config.json` or re-run `specify init --here --force ...` from a trusted launcher source.",
                }
            )

    powershell_common = project_root / ".specify" / "scripts" / "powershell" / "common.ps1"
    try:
        powershell_common_text = powershell_common.read_text(encoding="utf-8")
    except OSError:
        powershell_common_text = ""
    if powershell_common_text:
        has_prefix_helper = "function Find-FeatureDirByPrefix" in powershell_common_text
        uses_prefix_resolution = "Find-FeatureDirByPrefix -RepoRoot $repoRoot -BranchName $currentBranch" in powershell_common_text
        if not has_prefix_helper or not uses_prefix_resolution:
            issues.append(
                {
                    "code": "stale-powershell-feature-resolver",
                    "summary": "Generated PowerShell workflow scripts are stale and still rely on exact branch-to-feature-dir matching.",
                    "repair": "Refresh the generated scripts by re-running `specify init --here --force --ai <agent>` or reinstalling the active integration.",
                }
            )

    claude_settings = project_root / ".claude" / "settings.json"
    claude_payload = _load_config(claude_settings)
    if isinstance(claude_payload, dict):
        hooks = claude_payload.get("hooks")
        stale_claude_hook = False
        stale_direct_launcher = False
        if isinstance(hooks, dict):
            for entries in hooks.values():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    hook_items = entry.get("hooks", [])
                    if not isinstance(hook_items, list):
                        continue
                    for hook in hook_items:
                        if not isinstance(hook, dict):
                            continue
                        command = str(hook.get("command") or "")
                        if "claude-hook-dispatch.py" in command and '"$CLAUDE_PROJECT_DIR"' in command:
                            stale_claude_hook = True
                        if any(marker in command for marker in DIRECT_HOOK_DISPATCH_MARKERS) and any(
                            token in command for token in ("python ", "python3 ", "py ")
                        ):
                            stale_direct_launcher = True
                    if stale_claude_hook and stale_direct_launcher:
                        break
                if stale_claude_hook and stale_direct_launcher:
                    break
        if stale_claude_hook:
            issues.append(
                {
                    "code": "stale-claude-windows-hook-command",
                    "summary": "Claude managed hook commands still use POSIX-style `$CLAUDE_PROJECT_DIR` expansion.",
                    "repair": "Refresh the Claude integration so `.claude/settings.json` rewrites managed hook commands with the current Windows-safe format.",
                }
            )
        if stale_direct_launcher:
            issues.append(
                {
                    "code": "stale-direct-hook-launcher-command",
                    "summary": "Managed native hook commands still invoke integration dispatch scripts through a direct Python command.",
                    "repair": "Refresh the integration so managed hook commands call the shared `.specify/bin/specify-hook` launcher instead of embedding `python`, `python3`, or `py` directly.",
                }
            )

    gemini_settings = project_root / ".gemini" / "settings.json"
    gemini_payload = _load_config(gemini_settings)
    if isinstance(gemini_payload, dict):
        hooks = gemini_payload.get("hooks")
        stale_direct_launcher = False
        if isinstance(hooks, dict):
            for entries in hooks.values():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    hook_items = entry.get("hooks", [])
                    if not isinstance(hook_items, list):
                        continue
                    for hook in hook_items:
                        if not isinstance(hook, dict):
                            continue
                        command = str(hook.get("command") or "")
                        if any(marker in command for marker in DIRECT_HOOK_DISPATCH_MARKERS) and any(
                            token in command for token in ("python ", "python3 ", "py ")
                        ):
                            stale_direct_launcher = True
                            break
                    if stale_direct_launcher:
                        break
                if stale_direct_launcher:
                    break
        if stale_direct_launcher:
            issues.append(
                {
                    "code": "stale-direct-hook-launcher-command",
                    "summary": "Managed native hook commands still invoke integration dispatch scripts through a direct Python command.",
                    "repair": "Refresh the integration so managed hook commands call the shared `.specify/bin/specify-hook` launcher instead of embedding `python`, `python3`, or `py` directly.",
                }
            )

    return issues
