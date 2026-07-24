"""Helpers for invoking the same ``specify`` source that initialized a project."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.metadata as importlib_metadata
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
from typing import Any, Callable, TYPE_CHECKING
from urllib.parse import urlsplit
import uuid

from .atomic_io import (
    atomic_write_bytes,
    atomic_write_text,
    read_local_state_text,
    safe_local_state_path,
)
from .hook_artifacts import contains_claude_managed_hook_entries

if TYPE_CHECKING:
    from specify_cli.integrations.manifest import IntegrationManifest


SPECIFY_PACKAGE_NAME = "specify-cli"
SPECIFY_CONFIG_FILE = ".specify/config.json"
SPECIFY_LAUNCHER_CONFIG_KEY = "specify_launcher"
SPECIFY_RUNTIME_ID = "chenziyang110/spec-kit-plus"
SPECIFY_SOURCE_REPOSITORY = (
    "git+https://github.com/chenziyang110/spec-kit-plus.git"
)
SPECIFY_PROJECT_LAUNCHER_POSIX = ".specify/scripts/shared/specify-launcher"
SPECIFY_PROJECT_LAUNCHER_WINDOWS = ".specify/scripts/shared/specify-launcher.ps1"
SPECIFY_PROJECT_LAUNCHER_TEMPLATE_POSIX = "specify-launcher.sh.template"
SPECIFY_PROJECT_LAUNCHER_TEMPLATE_WINDOWS = "specify-launcher.ps1.template"
SPECIFY_LOCAL_BINDING_ENV = "SPECIFY_PROJECT_LAUNCHER_STATE_DIR"
SPECIFY_BINDING_ID_RE = re.compile(r"^[0-9a-f]{32}$")
SPECIFY_BINDING_ENTRY = "binding-entry.py"
SPECIFY_BINDING_METADATA = "binding.json"
SPECIFY_BINDING_POSIX = "invoke"
SPECIFY_BINDING_WINDOWS = "invoke.ps1"
SPECIFY_BINDING_DISPATCH_POSIX = "dispatch"
SPECIFY_BINDING_DISPATCH_WINDOWS = "dispatch.ps1"
SPECIFY_BINDING_DISPATCH_METADATA = "dispatch.json"
SPECIFY_BINDING_PLACEHOLDER = "__SPECIFY_BINDING_ID__"
SPECIFY_REPAIR_MESSAGE_PLACEHOLDER = "__SPECIFY_REPAIR_MESSAGE__"
RUNTIME_LAUNCHER_CONFIG_KEY = "runtime_launcher"
RUNTIME_LAUNCHER_BINDING_CONFIG_KEY = "runtime_launcher_binding"
SPECIFY_RUNTIME_UNAVAILABLE_MARKER = "SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE"
HOOK_RUNTIME_ARGV_ENV = "SPECIFY_HOOK_RUNTIME_ARGV"
HOOK_RUNTIME_COMMAND_ENV = "SPECIFY_HOOK_RUNTIME_COMMAND"
HOOK_LAUNCHER_POSIX = "specify-hook"
HOOK_LAUNCHER_WINDOWS = "specify-hook.cmd"
HOOK_LAUNCHER_NODE = "specify-hook.mjs"
HOOK_LAUNCHER_PYTHON = "specify-hook.py"
DIRECT_HOOK_DISPATCH_MARKERS = (
    "claude-hook-dispatch.py",
    "gemini-hook-dispatch.py",
)
GENERATED_GUIDANCE_ROOTS = (
    ".codex/skills",
    ".claude/commands",
    ".claude/hooks",
    ".claude/skills",
    ".gemini/commands",
    ".gemini/hooks",
    ".github/agents",
    ".cursor/skills",
    ".qwen/commands",
    ".opencode/command",
    ".windsurf/workflows",
    ".junie/commands",
    ".kilocode/workflows",
    ".augment/commands",
    ".roo/commands",
    ".codebuddy/commands",
    ".qoder/commands",
    ".kiro/prompts",
    ".agents/commands",
    ".shai/commands",
    ".tabnine/agent/commands",
    ".kimi/skills",
    ".mimocode/commands",
    ".pi/prompts",
    ".iflow/commands",
    ".forge/commands",
    ".bob/commands",
    ".trae/skills",
    ".agents/skills",
    ".vibe/skills",
    ".zcode/skills",
)
GENERATED_CONTEXT_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "CODEBUDDY.md",
    "GEMINI.md",
    "IFLOW.md",
    "KIMI.md",
    "QODER.md",
    "QWEN.md",
    "SHAI.md",
    "TABNINE.md",
    ".augment/rules/specify-rules.md",
    ".cursor/rules/specify-rules.mdc",
    ".github/copilot-instructions.md",
    ".junie/AGENTS.md",
    ".kilocode/rules/specify-rules.md",
    ".roo/rules/specify-rules.md",
    ".trae/rules/project_rules.md",
    ".windsurf/rules/specify-rules.md",
)
GENERATED_GUIDANCE_FILES = (
    ".specify/templates/project-handbook-template.md",
)
GENERATED_GUIDANCE_SUFFIXES = {".md", ".toml"}
SPEC_KIT_MANAGED_BLOCK_RE = re.compile(
    r"<!-- SPEC-KIT:BEGIN -->.*?<!-- SPEC-KIT:END -->",
    re.DOTALL,
)
SOURCE_BOUND_UVX_SPECIFY_RE = re.compile(r"uvx\s+--from\s+git\+\S+\s+specify")
_MARKDOWN_INLINE_CODE_RE = re.compile(r"`(?P<code>[^`\r\n]+)`")
_MARKDOWN_FENCE_RE = re.compile(
    r"^\s*(?P<marker>`{3,}|~{3,})(?P<language>[A-Za-z0-9_+-]*)\s*$"
)
_BARE_SPECIFY_LINE_RE = re.compile(
    r"^(?P<prefix>\s*(?:(?:PS>)|\$)?\s*)(?P<command>specify(?:\s+[^\r\n]+)?)(?P<suffix>\s*)$"
)
_BARE_UNIFIED_RUNTIME_LINE_RE = re.compile(
    r"^(?P<prefix>\s*(?:(?:PS>)|\$)?\s*)"
    r"(?P<command>specify-runtime(?:\s+[^\r\n]+)?)"
    r"(?P<suffix>\s*)$"
)
_SPECIFY_OPTION_RE = re.compile(r"^-{1,2}[A-Za-z][A-Za-z0-9-]*$")
_POWERSHELL_SAFE_ARG_RE = re.compile(r"^[A-Za-z0-9_./:\\@%+=,~-]+$")
_POWERSHELL_VARIABLE_ARG_RE = re.compile(
    r"^\$(?:env:)?[A-Za-z_][A-Za-z0-9_]*$",
    re.IGNORECASE,
)
_NON_EXECUTABLE_SPECIFY_CONTEXT_RE = re.compile(
    r"\b(?:do\s+not|don't|never|must\s+not|unsupported|not\s+executable|"
    r"non-executable|documentation-only|display-only|literal|illustration|example)\b",
    re.IGNORECASE,
)
_NON_SHELL_FENCE_LANGUAGES = frozenset(
    {
        "css",
        "html",
        "javascript",
        "js",
        "json",
        "markdown",
        "md",
        "python",
        "py",
        "toml",
        "typescript",
        "ts",
        "xml",
        "yaml",
        "yml",
    }
)
_SPECIFY_RUNTIME_ROOTS = frozenset(
    {
        "accept",
        "api",
        "artifact",
        "check",
        "debug",
        "design",
        "discussion",
        "eval",
        "extension",
        "hook",
        "implement",
        "init",
        "integrate",
        "integration",
        "lane",
        "learning",
        "lint",
        "map-build",
        "map-scan",
        "map-update",
        "prd",
        "prd-build",
        "prd-scan",
        "preset",
        "quick",
        "result",
        "sp-debug",
        "sp-teams",
        "version",
    }
)
_UNIFIED_RUNTIME_NAMESPACES = frozenset(
    {
        "accept",
        "api",
        "artifact",
        "cognition",
        "design",
        "discussion",
        "doctor",
        "hook",
        "implement",
        "integrate",
        "lane",
        "learning",
        "prd-build",
        "prd-scan",
        "quick",
        "result",
        "review",
        "sp-teams",
        "validate",
        "version",
        "workflow",
    }
)


@dataclass(frozen=True)
class SpecifyLauncherSpec:
    """Command forms that invoke a preferred ``specify`` install source."""

    command: str
    argv: tuple[str, ...]
    source: str = "direct"
    kind: str = "direct"
    runtime_id: str = ""
    binding_id: str = ""


@dataclass(frozen=True)
class HookRuntimeSpec:
    """Command forms that invoke the stable native-hook Python launcher."""

    command: str
    argv: tuple[str, ...]
    source: str


def render_command(argv: tuple[str, ...]) -> str:
    """Render *argv* as an operator-readable command string."""

    if os.name == "nt":
        rendered: list[str] = []
        for item in argv:
            if _POWERSHELL_SAFE_ARG_RE.fullmatch(item) or _POWERSHELL_VARIABLE_ARG_RE.fullmatch(item):
                rendered.append(item)
            else:
                rendered.append("'" + item.replace("'", "''") + "'")
        command = " ".join(rendered)
        if rendered and rendered[0].startswith("'"):
            command = f"& {command}"
        return command
    return " ".join(shlex.quote(item) for item in argv)


def default_specify_launcher_spec() -> SpecifyLauncherSpec:
    argv = ("specify",)
    return SpecifyLauncherSpec(command=render_command(argv), argv=argv)


def current_environment_specify_launcher_spec() -> SpecifyLauncherSpec:
    """Bind invocation to the interpreter that loaded this Specify package."""

    argv = (sys.executable, "-m", "specify_cli")
    return SpecifyLauncherSpec(
        command=render_command(argv),
        argv=argv,
        source="local_environment",
        kind="local_environment",
        runtime_id=SPECIFY_RUNTIME_ID,
    )


def project_local_specify_launcher_spec(binding_id: str) -> SpecifyLauncherSpec:
    """Return the cwd-independent command for a machine-local binding."""

    if not SPECIFY_BINDING_ID_RE.fullmatch(binding_id):
        raise ValueError("invalid Specify machine binding id")
    if os.name == "nt":
        argv = (
            _windows_powershell_executable(),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(_project_launcher_dispatch_path()),
            binding_id,
        )
    else:
        argv = (str(_project_launcher_dispatch_path()), binding_id)
    return SpecifyLauncherSpec(
        command=render_command(argv),
        argv=argv,
        source="machine_binding",
        kind="machine_binding",
        runtime_id=SPECIFY_RUNTIME_ID,
        binding_id=binding_id,
    )


def _source_bound_specify_launcher_spec(
    argv: tuple[str, ...],
) -> SpecifyLauncherSpec | None:
    """Return a canonical commit-pinned upstream launcher, or reject it."""

    if len(argv) != 4 or argv[:2] != ("uvx", "--from") or argv[3] != "specify":
        return None
    locator, separator, commit_id = argv[2].rpartition("@")
    if (
        separator != "@"
        or locator != SPECIFY_SOURCE_REPOSITORY
        or re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", commit_id)
        is None
    ):
        return None
    normalized_argv = ("uvx", "--from", f"{locator}@{commit_id}", "specify")
    return SpecifyLauncherSpec(
        command=render_command(normalized_argv),
        argv=normalized_argv,
        source="git",
        kind="source_bound",
        runtime_id=SPECIFY_RUNTIME_ID,
    )


def resolve_specify_launcher_spec() -> SpecifyLauncherSpec:
    """Return the best available launcher for the current ``specify`` source.

    Git direct-url installs are converted into a ``uvx --from git+... specify``
    launcher. Other installs bind to the current Python environment. Both forms
    avoid calling an unrelated ``specify`` executable that appears earlier on
    PATH.
    """

    current_environment = current_environment_specify_launcher_spec()

    try:
        distribution = importlib_metadata.distribution(SPECIFY_PACKAGE_NAME)
    except importlib_metadata.PackageNotFoundError:
        return current_environment

    try:
        direct_url_text = distribution.read_text("direct_url.json")
    except FileNotFoundError:
        return current_environment

    if not direct_url_text:
        return current_environment

    try:
        payload = json.loads(direct_url_text)
    except json.JSONDecodeError:
        return current_environment

    if not isinstance(payload, dict):
        return current_environment

    vcs_info = payload.get("vcs_info")
    url = payload.get("url")
    if not isinstance(vcs_info, dict) or not isinstance(url, str):
        return current_environment
    if vcs_info.get("vcs") != "git" or not url.strip():
        return current_environment

    # A direct-url record can contain authenticated clone URLs. Persisting one
    # would copy credentials into project config and every generated command.
    # Fall back to the machine-local binding whenever the URL is not a clean,
    # credential-free source locator.
    try:
        parsed_url = urlsplit(url.removeprefix("git+"))
    except ValueError:
        return current_environment
    if (
        parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
        or re.search(r"[\s\"'`;&|<>^$(){}\[\]\\]", url)
    ):
        return current_environment

    commit_id = str(vcs_info.get("commit_id", "")).strip()
    if not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", commit_id):
        return current_environment
    source = url if url.startswith("git+") else f"git+{url}"
    if source != SPECIFY_SOURCE_REPOSITORY:
        return current_environment
    if commit_id:
        source = f"{source}@{commit_id}"

    if not shutil.which("uvx"):
        return current_environment

    argv = ("uvx", "--from", source, "specify")
    return _source_bound_specify_launcher_spec(argv) or current_environment


def _project_launcher_state_root() -> Path:
    override = os.environ.get(SPECIFY_LOCAL_BINDING_ENV, "").strip()
    return (
        Path(override).expanduser().resolve()
        if override
        else Path.home() / ".specify" / "project-launchers"
    )


def _windows_powershell_executable() -> str:
    """Return the system Windows PowerShell host without consulting PATH."""

    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate = (
        Path(system_root)
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    return str(candidate)


def _project_launcher_binding_dir(binding_id: str) -> Path:
    if not SPECIFY_BINDING_ID_RE.fullmatch(binding_id):
        raise ValueError("invalid Specify machine binding id")
    return _project_launcher_state_root() / binding_id


def _project_launcher_binding_path(binding_id: str) -> Path:
    return _project_launcher_binding_dir(binding_id) / SPECIFY_BINDING_METADATA


def _project_launcher_dispatch_path() -> Path:
    name = (
        SPECIFY_BINDING_DISPATCH_WINDOWS
        if os.name == "nt"
        else SPECIFY_BINDING_DISPATCH_POSIX
    )
    return _project_launcher_state_root() / name


def _project_launcher_dispatch_metadata_path() -> Path:
    return _project_launcher_state_root() / SPECIFY_BINDING_DISPATCH_METADATA


def _project_launcher_native_binding_path(binding_id: str) -> Path:
    name = SPECIFY_BINDING_WINDOWS if os.name == "nt" else SPECIFY_BINDING_POSIX
    return _project_launcher_binding_dir(binding_id) / name


def _binding_package_identity() -> tuple[Path, str, str]:
    launcher_path = Path(__file__).resolve()
    package_dir = launcher_path.parent
    package_init = package_dir / "__init__.py"
    if not package_init.is_file() or launcher_path.name != "launcher.py":
        raise RuntimeError("cannot locate the loaded specify_cli package source")
    import_root = package_dir.parent.resolve()
    return (
        import_root,
        hashlib.sha256(package_init.read_bytes()).hexdigest(),
        hashlib.sha256(launcher_path.read_bytes()).hexdigest(),
    )


def _binding_entry_source(
    binding_id: str,
    package_import_root: Path,
    package_init_sha256: str,
    package_launcher_sha256: str,
    repair_command: str,
) -> str:
    return f'''#!/usr/bin/env python3
"""Machine-local Spec Kit Plus binding entry. Generated; do not edit."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

EXPECTED_RUNTIME_ID = {SPECIFY_RUNTIME_ID!r}
BINDING_ID = {binding_id!r}
PACKAGE_IMPORT_ROOT = {str(package_import_root)!r}
PACKAGE_INIT_SHA256 = {package_init_sha256!r}
PACKAGE_LAUNCHER_SHA256 = {package_launcher_sha256!r}
REPAIR_COMMAND = {repair_command!r}


def _recovery(detail: str) -> None:
    print("Spec Kit Plus machine binding is unavailable or incompatible.", file=sys.stderr)
    print(f"Binding: {{BINDING_ID}}", file=sys.stderr)
    print(f"Cause: {{detail}}", file=sys.stderr)
    print(f"Run this exact trusted repair command from the project root: {{REPAIR_COMMAND}}", file=sys.stderr)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    try:
        import_root = Path(PACKAGE_IMPORT_ROOT)
        if not import_root.is_absolute():
            raise RuntimeError("recorded package import root is not absolute")
        package_dir = import_root / "specify_cli"
        package_init = package_dir / "__init__.py"
        package_launcher = package_dir / "launcher.py"
        if _sha256(package_init) != PACKAGE_INIT_SHA256:
            raise RuntimeError("recorded package __init__.py digest no longer matches")
        if _sha256(package_launcher) != PACKAGE_LAUNCHER_SHA256:
            raise RuntimeError("recorded package launcher.py digest no longer matches")
        sys.path.insert(0, str(import_root))
        import specify_cli.launcher as launcher_runtime
        if Path(launcher_runtime.__file__).resolve() != package_launcher.resolve():
            raise RuntimeError("loaded package does not match the recorded import root")
        if launcher_runtime.SPECIFY_RUNTIME_ID != EXPECTED_RUNTIME_ID:
            raise RuntimeError(
                f"runtime identity {{launcher_runtime.SPECIFY_RUNTIME_ID!r}} does not match {{EXPECTED_RUNTIME_ID!r}}"
            )
        from specify_cli import main as specify_main
    except Exception as exc:
        _recovery(str(exc))
        return 2
    specify_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _binding_invoke_source(interpreter: str, entry_path: Path) -> str:
    if os.name == "nt":
        quoted_interpreter = interpreter.replace("'", "''")
        return (
            "param(\r\n"
            "    [Parameter(ValueFromRemainingArguments = $true)]\r\n"
            "    [string[]]$ForwardedArgs\r\n"
            ")\r\n"
            "$ErrorActionPreference = 'Stop'\r\n"
            "$utf8 = [System.Text.UTF8Encoding]::new($false)\r\n"
            "[Console]::InputEncoding = $utf8\r\n"
            "[Console]::OutputEncoding = $utf8\r\n"
            "$OutputEncoding = $utf8\r\n"
            "$env:PYTHONUTF8 = '1'\r\n"
            "$env:PYTHONIOENCODING = 'utf-8'\r\n"
            f"& '{quoted_interpreter}' (Join-Path $PSScriptRoot '{entry_path.name}') @ForwardedArgs\r\n"
            "exit $LASTEXITCODE\r\n"
        )
    command = " ".join(shlex.quote(item) for item in (interpreter, str(entry_path)))
    return f'#!/bin/sh\nexec {command} "$@"\n'


def _absolute_launcher_entry(entry: str) -> str:
    """Make an executable path absolute without dereferencing venv symlinks."""

    candidate = Path(entry).expanduser()
    if candidate.is_absolute():
        return os.path.abspath(str(candidate))
    located = shutil.which(entry)
    if located:
        return os.path.abspath(os.path.expanduser(located))
    return os.path.abspath(str(candidate))


def _binding_repair_argv(interpreter: str) -> tuple[str, ...]:
    return (interpreter, "-m", "specify_cli", "integration", "repair")


def _binding_repair_message(repair_command: str) -> str:
    return f"Run this exact trusted repair command from the project root: {repair_command}"


def _binding_dispatch_source(repair_command: str) -> str:
    repair_message = _binding_repair_message(repair_command)
    if os.name == "nt":
        quoted_repair_message = "'" + repair_message.replace("'", "''") + "'"
        return r'''param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern('^[0-9a-f]{32}$')]
    [string]$BindingId,
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$ForwardedArgs
)
$ErrorActionPreference = 'Stop'
$stateRoot = $PSScriptRoot
$binding = Join-Path $stateRoot "$BindingId/invoke.ps1"
if (-not (Test-Path -LiteralPath $binding -PathType Leaf)) {
    [Console]::Error.WriteLine("Spec Kit Plus cannot find this project's machine-local Specify binding.")
    [Console]::Error.WriteLine("Binding: $BindingId")
    [Console]::Error.WriteLine("Expected: $binding")
    [Console]::Error.WriteLine(__SPECIFY_REPAIR_MESSAGE__)
    exit 2
}
& $binding @ForwardedArgs
exit $LASTEXITCODE
'''.replace(SPECIFY_REPAIR_MESSAGE_PLACEHOLDER, quoted_repair_message)
    quoted_repair_message = shlex.quote(repair_message)
    return '''#!/bin/sh
set -eu
binding_id="${1:-}"
case "$binding_id" in
  *[!0-9a-f]*|'') echo "Spec Kit Plus received an invalid machine binding id." >&2; exit 2 ;;
esac
if [ "${#binding_id}" -ne 32 ]; then
  echo "Spec Kit Plus received an invalid machine binding id." >&2
  exit 2
fi
shift
script_path=$0
case "$script_path" in
  */*) script_dir=${script_path%/*} ;;
  *) script_dir=. ;;
esac
state_root=$(CDPATH= cd "$script_dir" && pwd -P)
binding="${state_root}/${binding_id}/invoke"
if [ ! -x "$binding" ]; then
  echo "Spec Kit Plus cannot find this project's machine-local Specify binding." >&2
  echo "Binding: ${binding_id}" >&2
  echo "Expected: ${binding}" >&2
  echo __SPECIFY_REPAIR_MESSAGE__ >&2
  exit 2
fi
exec "$binding" "$@"
'''.replace(SPECIFY_REPAIR_MESSAGE_PLACEHOLDER, quoted_repair_message)


def _write_project_launcher_binding(
    binding_id: str,
    launcher: SpecifyLauncherSpec,
) -> Path:
    binding_dir = _project_launcher_binding_dir(binding_id)
    binding_dir.mkdir(parents=True, exist_ok=True)
    entry_path = binding_dir / SPECIFY_BINDING_ENTRY
    invoke_path = _project_launcher_native_binding_path(binding_id)
    dispatch_path = _project_launcher_dispatch_path()
    binding_path = _project_launcher_binding_path(binding_id)
    interpreter = _absolute_launcher_entry(launcher.argv[0])
    repair_argv = _binding_repair_argv(interpreter)
    repair_command = render_command(repair_argv)
    package_import_root, package_init_sha256, package_launcher_sha256 = (
        _binding_package_identity()
    )
    atomic_write_text(
        entry_path,
        _binding_entry_source(
            binding_id,
            package_import_root,
            package_init_sha256,
            package_launcher_sha256,
            repair_command,
        ),
    )
    invoke_source = _binding_invoke_source(interpreter, entry_path)
    dispatch_source = _binding_dispatch_source(repair_command)
    if os.name == "nt":
        # Windows PowerShell 5 decodes BOM-less scripts through the active ANSI
        # code page. Use UTF-8 BOM so CJK interpreter/state paths remain exact.
        atomic_write_bytes(invoke_path, invoke_source.encode("utf-8-sig"))
        atomic_write_bytes(dispatch_path, dispatch_source.encode("utf-8-sig"))
    else:
        atomic_write_text(invoke_path, invoke_source)
        atomic_write_text(dispatch_path, dispatch_source)
    dispatch_payload = {
        "runtime_id": SPECIFY_RUNTIME_ID,
        "repair_argv": list(repair_argv),
        "dispatch_path": str(dispatch_path),
        "dispatch_sha256": hashlib.sha256(dispatch_path.read_bytes()).hexdigest(),
    }
    atomic_write_text(
        _project_launcher_dispatch_metadata_path(),
        json.dumps(dispatch_payload, ensure_ascii=False, indent=2) + "\n",
    )
    payload = {
        "runtime_id": SPECIFY_RUNTIME_ID,
        "binding_id": binding_id,
        "entry_argv": [interpreter, str(entry_path)],
        "package_import_root": str(package_import_root),
        "package_init_sha256": package_init_sha256,
        "package_launcher_sha256": package_launcher_sha256,
        "invoke_path": str(invoke_path),
        "entry_sha256": hashlib.sha256(entry_path.read_bytes()).hexdigest(),
        "invoke_sha256": hashlib.sha256(invoke_path.read_bytes()).hexdigest(),
    }
    atomic_write_text(
        binding_path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    if os.name != "nt":
        entry_path.chmod(0o600)
        binding_path.chmod(0o600)
        _project_launcher_dispatch_metadata_path().chmod(0o600)
        invoke_path.chmod(0o700)
        dispatch_path.chmod(0o700)
    return binding_path


def _read_project_launcher_binding(binding_id: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(
            read_local_state_text(
                _project_launcher_binding_path(binding_id),
                root=_project_launcher_state_root(),
            )
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("runtime_id") != SPECIFY_RUNTIME_ID
        or payload.get("binding_id") != binding_id
    ):
        return None
    entry_argv = payload.get("entry_argv")
    invoke_path = payload.get("invoke_path")
    entry_sha256 = payload.get("entry_sha256")
    package_import_root = payload.get("package_import_root")
    package_init_sha256 = payload.get("package_init_sha256")
    package_launcher_sha256 = payload.get("package_launcher_sha256")
    invoke_sha256 = payload.get("invoke_sha256")
    if (
        not isinstance(entry_argv, list)
        or len(entry_argv) != 2
        or not all(isinstance(item, str) and item for item in entry_argv)
        or not isinstance(invoke_path, str)
        or not invoke_path
        or not isinstance(entry_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", entry_sha256)
        or not isinstance(package_import_root, str)
        or not package_import_root
        or not Path(package_import_root).is_absolute()
        or not isinstance(package_init_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", package_init_sha256)
        or not isinstance(package_launcher_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", package_launcher_sha256)
        or not isinstance(invoke_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", invoke_sha256)
    ):
        return None
    return payload


def _read_project_launcher_dispatch() -> dict[str, Any] | None:
    try:
        payload = json.loads(
            read_local_state_text(
                _project_launcher_dispatch_metadata_path(),
                root=_project_launcher_state_root(),
            )
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("runtime_id") != SPECIFY_RUNTIME_ID:
        return None
    repair_argv = payload.get("repair_argv")
    dispatch_path = payload.get("dispatch_path")
    dispatch_sha256 = payload.get("dispatch_sha256")
    if (
        not isinstance(repair_argv, list)
        or len(repair_argv) != 5
        or not all(isinstance(item, str) and item for item in repair_argv)
        or tuple(repair_argv[1:])
        != ("-m", "specify_cli", "integration", "repair")
        or not Path(repair_argv[0]).is_absolute()
        or not isinstance(dispatch_path, str)
        or not dispatch_path
        or not isinstance(dispatch_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", dispatch_sha256)
    ):
        return None
    return payload


def _launcher_entry_exists(entry: str) -> bool:
    candidate = Path(entry).expanduser()
    return candidate.is_file() if candidate.is_absolute() else shutil.which(entry) is not None


def project_specify_launcher_is_available(
    project_root: Path,
    launcher: SpecifyLauncherSpec,
) -> bool:
    """Validate both a persisted launcher entry and its project-local binding."""

    if not launcher.argv:
        return False
    if launcher.kind != "machine_binding":
        return _launcher_entry_exists(launcher.argv[0])
    if (
        launcher.runtime_id != SPECIFY_RUNTIME_ID
        or not SPECIFY_BINDING_ID_RE.fullmatch(launcher.binding_id)
    ):
        return False
    try:
        wrapper = project_local_specify_launcher_spec(launcher.binding_id)
        destination, expected = _render_project_launcher_asset(
            launcher.binding_id,
            project_root,
        )
    except (FileNotFoundError, ValueError):
        return False
    if launcher.argv != wrapper.argv:
        return False
    try:
        if read_local_state_text(destination, root=project_root) != expected:
            return False
    except (OSError, ValueError):
        return False
    return _machine_binding_probe(launcher.binding_id)


def _machine_binding_probe(binding_id: str) -> bool:
    binding = _read_project_launcher_binding(binding_id)
    dispatch = _read_project_launcher_dispatch()
    if binding is None or dispatch is None:
        return False
    entry_argv = tuple(binding["entry_argv"])
    package_import_root = Path(binding["package_import_root"])
    package_init_sha256 = str(binding["package_init_sha256"])
    package_launcher_sha256 = str(binding["package_launcher_sha256"])
    invoke_path = Path(binding["invoke_path"])
    dispatch_path = Path(dispatch["dispatch_path"])
    dispatch_repair_argv = tuple(dispatch["repair_argv"])
    binding_dir = _project_launcher_binding_dir(binding_id).resolve()
    entry_path = binding_dir / SPECIFY_BINDING_ENTRY
    expected_invoke = _project_launcher_native_binding_path(binding_id).resolve()
    expected_dispatch = _project_launcher_dispatch_path().resolve()
    try:
        recorded_entry = Path(entry_argv[1]).resolve()
        recorded_invoke = invoke_path.resolve()
        recorded_dispatch = dispatch_path.resolve()
        recorded_import_root = package_import_root.resolve()
    except OSError:
        return False
    if (
        recorded_entry != entry_path
        or recorded_invoke != expected_invoke
        or recorded_dispatch != expected_dispatch
        or recorded_import_root != package_import_root
        or not _launcher_entry_exists(entry_argv[0])
        or not _launcher_entry_exists(dispatch_repair_argv[0])
        or not entry_path.is_file()
        or not invoke_path.is_file()
        or not dispatch_path.is_file()
    ):
        return False
    try:
        package_init = package_import_root / "specify_cli" / "__init__.py"
        package_launcher = package_import_root / "specify_cli" / "launcher.py"
        entry_hash = hashlib.sha256(entry_path.read_bytes()).hexdigest()
        invoke_hash = hashlib.sha256(invoke_path.read_bytes()).hexdigest()
        dispatch_hash = hashlib.sha256(dispatch_path.read_bytes()).hexdigest()
        package_init_hash = hashlib.sha256(package_init.read_bytes()).hexdigest()
        package_launcher_hash = hashlib.sha256(package_launcher.read_bytes()).hexdigest()
        repair_command = render_command(_binding_repair_argv(entry_argv[0]))
        expected_entry = _binding_entry_source(
            binding_id,
            package_import_root,
            package_init_sha256,
            package_launcher_sha256,
            repair_command,
        )
        expected_dispatch = _binding_dispatch_source(
            render_command(dispatch_repair_argv)
        ).encode(
            "utf-8-sig" if os.name == "nt" else "utf-8"
        )
        actual_entry = entry_path.read_text(encoding="utf-8")
        actual_dispatch = dispatch_path.read_bytes()
    except OSError:
        return False
    if (
        entry_hash != binding["entry_sha256"]
        or invoke_hash != binding["invoke_sha256"]
        or dispatch_hash != dispatch["dispatch_sha256"]
        or package_init_hash != package_init_sha256
        or package_launcher_hash != package_launcher_sha256
        or actual_entry != expected_entry
        or actual_dispatch != expected_dispatch
    ):
        return False
    try:
        probe = subprocess.run(
            [*project_local_specify_launcher_spec(binding_id).argv, "--runtime-id"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0 and probe.stdout.strip() == SPECIFY_RUNTIME_ID


def _project_launcher_asset() -> Path | None:
    module_dir = Path(__file__).resolve().parent
    name = (
        SPECIFY_PROJECT_LAUNCHER_TEMPLATE_WINDOWS
        if os.name == "nt"
        else SPECIFY_PROJECT_LAUNCHER_TEMPLATE_POSIX
    )
    for candidate in (
        module_dir / "core_pack" / "scripts" / "shared" / name,
        module_dir.parent.parent / "scripts" / "shared" / name,
    ):
        if candidate.is_file():
            return candidate
    return None


def _project_launcher_destination(project_root: Path) -> Path:
    relative = (
        SPECIFY_PROJECT_LAUNCHER_WINDOWS
        if os.name == "nt"
        else SPECIFY_PROJECT_LAUNCHER_POSIX
    )
    return project_root / relative


def _render_project_launcher_asset(binding_id: str, project_root: Path | None = None) -> tuple[Path, str]:
    source = _project_launcher_asset()
    if source is None:
        raise FileNotFoundError("packaged project launcher template is unavailable")
    if not SPECIFY_BINDING_ID_RE.fullmatch(binding_id):
        raise ValueError("invalid Specify machine binding id")
    root = project_root or Path.cwd()
    destination = _project_launcher_destination(root)
    binding = _read_project_launcher_binding(binding_id)
    if binding is None:
        raise FileNotFoundError("machine binding metadata is unavailable or invalid")
    repair_command = render_command(_binding_repair_argv(binding["entry_argv"][0]))
    repair_message = _binding_repair_message(repair_command)
    repair_literal = (
        "'" + repair_message.replace("'", "''") + "'"
        if os.name == "nt"
        else shlex.quote(repair_message)
    )
    rendered = source.read_text(encoding="utf-8").replace(
        SPECIFY_BINDING_PLACEHOLDER,
        binding_id,
    )
    rendered = rendered.replace(SPECIFY_REPAIR_MESSAGE_PLACEHOLDER, repair_literal)
    return destination, rendered


def install_project_specify_launcher(project_root: Path, binding_id: str) -> Path:
    """Install the portable project wrapper used by local environment bindings."""

    destination, rendered = _render_project_launcher_asset(binding_id, project_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        try:
            current = read_local_state_text(destination, root=project_root)
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"cannot inspect existing project launcher: {destination}") from exc
        if current != rendered:
            raise RuntimeError(
                "project launcher conflict: existing runtime shim was modified; "
                f"preserved {destination}. Back up the file, compare it with the installed "
                "Spec Kit Plus launcher template, then run the trusted `specify integration repair` command."
            )
        return destination
    atomic_write_text(destination, rendered)
    if os.name != "nt":
        destination.chmod(0o700)
    return destination


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
    script_type: str | None = None,
) -> str:
    """Render the native hook command that targets the shared launcher."""

    use_windows_launcher = script_type == "ps" if script_type is not None else os.name == "nt"
    launcher_name = HOOK_LAUNCHER_WINDOWS if use_windows_launcher else HOOK_LAUNCHER_POSIX
    launcher_path = f".specify/bin/{launcher_name}"
    if project_dir_env_var:
        # Hook runners (e.g. Claude Code on Windows) invoke these via bash; use `$VAR` not `$env:VAR`.
        project_root = f'"${project_dir_env_var}"'
        return f"{project_root}/{launcher_path} {integration_key} {route}"
    return f"{launcher_path} {integration_key} {route}"


def render_claude_hook_launcher(route: str) -> dict[str, Any]:
    """Render a Claude Code native-hook launcher entry."""

    bootstrap = (
        "let d=process.cwd(),p=require('path'),f=require('fs'),u=require('url');"
        "while(!f.existsSync(p.join(d,'.specify','bin','specify-hook.mjs'))){"
        "let n=p.dirname(d);if(n===d){console.error('Missing .specify/bin/specify-hook.mjs. Run specify integration repair.');process.exit(2)}d=n}"
        "import(u.pathToFileURL(p.join(d,'.specify','bin','specify-hook.mjs')).href)"
    )
    return {
        "type": "command",
        "command": f'node -e "{bootstrap}" specify-hook claude {route}',
    }


def install_shared_hook_launcher_assets(
    project_root: Path,
    *,
    manifest: IntegrationManifest | None = None,
    include_node: bool = True,
    preserve_modified: bool = False,
    skipped_modified: list[str] | None = None,
) -> list[Path]:
    """Install shared native-hook launcher assets into ``.specify/bin/``."""

    assets_dir = _hook_launcher_assets_dir()
    if not assets_dir:
        return []

    created: list[Path] = []
    dest_dir = project_root / ".specify" / "bin"
    dest_dir.mkdir(parents=True, exist_ok=True)
    modified = (
        set(manifest.check_modified())
        if preserve_modified and manifest is not None
        else set()
    )
    for src_file in sorted(assets_dir.iterdir()):
        if not src_file.is_file():
            continue
        if not include_node and src_file.name == HOOK_LAUNCHER_NODE:
            continue
        dst_file = dest_dir / src_file.name
        relative = dst_file.relative_to(project_root).as_posix()
        if preserve_modified and (dst_file.exists() or dst_file.is_symlink()):
            if (
                manifest is None
                or relative not in manifest.files
                or relative in modified
                or dst_file.is_symlink()
            ):
                if skipped_modified is not None:
                    skipped_modified.append(relative)
                continue
        shutil.copy2(src_file, dst_file)
        if dst_file.name == HOOK_LAUNCHER_POSIX:
            dst_file.chmod(dst_file.stat().st_mode | 0o111)
        if manifest is not None:
            manifest.record_existing(relative)
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


def _payload_argv(payload: Any) -> tuple[str, ...] | None:
    if not isinstance(payload, dict):
        return None
    argv = payload.get("argv")
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(item, str) and item for item in argv)
    ):
        return None
    return tuple(argv)


def _normalize_specify_launcher_payload(payload: Any) -> SpecifyLauncherSpec | None:
    """Load only canonical Specify launchers; persisted command text is untrusted."""

    normalized_argv = _payload_argv(payload)
    if normalized_argv is None or not isinstance(payload, dict):
        return None
    source = payload.get("source", "direct")
    kind = payload.get("kind", "direct")
    runtime_id = payload.get("runtime_id", "")
    binding_id = payload.get("binding_id", "")
    if not all(isinstance(item, str) for item in (source, kind, runtime_id, binding_id)):
        return None

    if kind == "machine_binding":
        if (
            source != "machine_binding"
            or runtime_id != SPECIFY_RUNTIME_ID
            or not SPECIFY_BINDING_ID_RE.fullmatch(binding_id)
        ):
            return None
        # Never execute argv/command copied from project-writable JSON. The
        # validated identifier deterministically selects our machine dispatcher.
        return project_local_specify_launcher_spec(binding_id)

    source_bound = _source_bound_specify_launcher_spec(normalized_argv)
    if source_bound is not None:
        return source_bound

    if (
        kind != "source_bound"
        or source != "git"
        or runtime_id != SPECIFY_RUNTIME_ID
        or binding_id
    ):
        return None
    return None


def _normalize_runtime_launcher_payload(payload: Any) -> SpecifyLauncherSpec | None:
    """Load a shell-free single-executable unified runtime launcher."""

    normalized_argv = _payload_argv(payload)
    if normalized_argv is None or len(normalized_argv) != 1:
        return None
    return SpecifyLauncherSpec(
        command=render_command(normalized_argv),
        argv=normalized_argv,
    )


def _launcher_payload(launcher: SpecifyLauncherSpec) -> dict[str, Any]:
    payload = {
        "command": render_command(launcher.argv),
        "argv": list(launcher.argv),
        "source": launcher.source,
        "kind": launcher.kind,
    }
    if launcher.runtime_id:
        payload["runtime_id"] = launcher.runtime_id
    if launcher.binding_id:
        payload["binding_id"] = launcher.binding_id
    return payload


def load_project_specify_launcher(project_root: Path) -> SpecifyLauncherSpec | None:
    """Load the persisted project launcher from ``.specify/config.json``."""

    config_path = project_root / SPECIFY_CONFIG_FILE
    payload = _load_config(config_path)
    if payload is None:
        return None
    return _normalize_specify_launcher_payload(
        payload.get(SPECIFY_LAUNCHER_CONFIG_KEY)
    )


def find_project_specify_root(start: Path) -> Path | None:
    """Find the nearest ancestor that owns a persisted Specify launcher."""

    candidate = start.expanduser().resolve(strict=False)
    if not candidate.is_dir():
        candidate = candidate.parent
    for root in (candidate, *candidate.parents):
        specify_dir = root / ".specify"
        if specify_dir.is_dir():
            return root if (root / SPECIFY_CONFIG_FILE).is_file() else None
    return None


def bind_project_launcher_payload(payload: Any, project_root: Path) -> Any:
    """Bind agent-facing ``*_argv`` records to the project's launcher.

    Command arrays are the executable source of truth.  Operator-facing command
    strings derived from those arrays are rewritten in the same pass so a
    payload cannot advertise a pinned argv while its tutorial or resume text
    still invokes an unrelated executable from ``PATH``.
    """

    root = find_project_specify_root(project_root)
    if root is None:
        return payload
    launcher = load_project_specify_launcher(root)
    runtime_launcher = load_runtime_launcher(root)
    if launcher is None and runtime_launcher is None:
        return payload

    replacements: dict[str, str] = {}

    def is_argv_key(key: object) -> bool:
        return isinstance(key, str) and (key == "argv" or key.endswith("_argv"))

    def bound_argv(value: list[str] | tuple[str, ...]) -> tuple[str, ...] | None:
        if not value or not all(isinstance(item, str) for item in value):
            return None
        if value[0] == "specify" and launcher is not None:
            return (*launcher.argv, *value[1:])
        if value[0] == "specify-runtime" and runtime_launcher is not None:
            return (*runtime_launcher.argv, *value[1:])
        return None

    def collect(value: Any, *, key: object = None) -> None:
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                collect(nested_value, key=nested_key)
            return
        if isinstance(value, (list, tuple)):
            bound = bound_argv(value) if is_argv_key(key) else None
            if bound is not None:
                original = tuple(value)
                replacements[render_command(original)] = render_command(bound)
                return
            for item in value:
                collect(item)

    collect(payload)
    ordered_replacements = sorted(
        replacements.items(), key=lambda item: len(item[0]), reverse=True
    )

    def transform(value: Any, *, key: object = None) -> Any:
        if isinstance(value, dict):
            return {
                nested_key: transform(nested_value, key=nested_key)
                for nested_key, nested_value in value.items()
            }
        if isinstance(value, list):
            bound = bound_argv(value) if is_argv_key(key) else None
            if bound is not None:
                return list(bound)
            return [transform(item) for item in value]
        if isinstance(value, tuple):
            bound = bound_argv(value) if is_argv_key(key) else None
            if bound is not None:
                return bound
            return tuple(transform(item) for item in value)
        if isinstance(value, str):
            rendered = value
            for original, bound in ordered_replacements:
                rendered = rendered.replace(original, bound)
            return rendered
        return value

    return transform(payload)


def load_runtime_launcher(project_root: Path) -> SpecifyLauncherSpec | None:
    """Load the persisted Specify runtime launcher from ``.specify/config.json``."""

    config_path = project_root / SPECIFY_CONFIG_FILE
    payload = _load_config(config_path)
    if payload is None:
        return None
    launcher = _normalize_runtime_launcher_payload(
        payload.get(RUNTIME_LAUNCHER_CONFIG_KEY)
    )
    if launcher is None:
        return None
    from .specify_runtime import (
        _sha256_file,
        project_runtime_entrypoint_path,
        project_runtime_launcher_arg,
    )

    expected = project_runtime_launcher_arg()
    if launcher.argv != (expected,):
        return None
    persisted_binding = payload.get(RUNTIME_LAUNCHER_BINDING_CONFIG_KEY)
    if not isinstance(persisted_binding, dict):
        return None
    if persisted_binding.get("runtime_entrypoint") != expected:
        return None
    expected_digest = persisted_binding.get("runtime_binary_sha256")
    if (
        not isinstance(expected_digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None
    ):
        return None
    try:
        project_binary = project_runtime_entrypoint_path(project_root)
        if (
            project_binary.is_symlink()
            or not project_binary.is_file()
            or _sha256_file(project_binary) != expected_digest
        ):
            return None
    except (OSError, ValueError):
        return None
    return SpecifyLauncherSpec(
        command=render_command((expected,)),
        argv=(expected,),
    )


def resolve_runtime_launcher_argv(
    project_root: Path,
    launcher: SpecifyLauncherSpec | None = None,
) -> tuple[str, ...] | None:
    """Resolve a runtime launcher entry relative to its project when needed."""

    resolved = launcher or load_runtime_launcher(project_root)
    if resolved is None or not resolved.argv:
        return None

    entry = resolved.argv[0]
    candidate = Path(entry).expanduser()
    if candidate.is_absolute():
        executable = candidate
    else:
        try:
            project_candidate = safe_local_state_path(
                project_root / candidate,
                root=project_root,
            )
        except ValueError:
            return None
        if project_candidate.is_file():
            executable = project_candidate
        else:
            return None

    if not executable.is_file():
        return None
    if os.name != "nt" and not os.access(executable, os.X_OK):
        return None
    return (str(executable), *resolved.argv[1:])


def runtime_launcher_is_compatible(
    project_root: Path,
    launcher: SpecifyLauncherSpec | None = None,
) -> bool:
    """Probe the configured launcher for the current required command surface."""

    argv = resolve_runtime_launcher_argv(project_root, launcher)
    if argv is None:
        return False
    from .specify_runtime import (
        _sha256_file,
        current_runtime_binding_metadata,
        launcher_supports_required_commands,
        project_runtime_launcher_arg,
        runtime_binding_metadata_matches,
    )

    if not launcher_supports_required_commands(argv, cwd=project_root):
        return False
    payload = _load_config(project_root / SPECIFY_CONFIG_FILE) or {}
    persisted_binding = payload.get(RUNTIME_LAUNCHER_BINDING_CONFIG_KEY)
    if not isinstance(persisted_binding, dict):
        return False
    if persisted_binding.get("runtime_entrypoint") != project_runtime_launcher_arg():
        return False
    expected_digest = persisted_binding.get("runtime_binary_sha256")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        return False
    try:
        if _sha256_file(Path(argv[0])) != expected_digest:
            return False
    except OSError:
        return False
    return runtime_binding_metadata_matches(
        persisted_binding,
        current_runtime_binding_metadata(),
    )


def _normalize_command_text(command: str) -> str:
    return " ".join(command.split())


def _stale_source_bound_specify_launchers(text: str, launcher: SpecifyLauncherSpec | None) -> list[str]:
    if launcher is None:
        return []
    expected = _normalize_command_text(launcher.command)
    stale: list[str] = []
    for match in SOURCE_BOUND_UVX_SPECIFY_RE.finditer(text):
        command = _normalize_command_text(match.group(0))
        if command != expected and command not in stale:
            stale.append(command)
    return stale


def rebind_source_bound_specify_launchers(
    text: str,
    launcher: SpecifyLauncherSpec,
    *,
    command_renderer: Callable[[str], str] | None = None,
) -> tuple[str, int]:
    """Replace stale commit/source-bound Specify prefixes with the active launcher."""

    expected = _normalize_command_text(launcher.command)
    replacement = (
        command_renderer(launcher.command)
        if command_renderer is not None
        else launcher.command
    )
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        if _normalize_command_text(match.group(0)) == expected:
            return match.group(0)
        count += 1
        return replacement

    return SOURCE_BOUND_UVX_SPECIFY_RE.sub(replace, text), count


def _is_bare_specify_runtime_command(command: str) -> bool:
    """Return whether *command* starts a recognized bare Specify CLI call."""

    stripped = command.strip()
    if not stripped.startswith("specify"):
        return False
    try:
        tokens = shlex.split(stripped, posix=os.name != "nt")
    except ValueError:
        return False
    if not tokens or tokens[0] != "specify" or len(tokens) < 2:
        return False
    root = tokens[1]
    return bool(_SPECIFY_OPTION_RE.fullmatch(root)) or root in _SPECIFY_RUNTIME_ROOTS


def _is_bare_unified_runtime_command(command: str) -> bool:
    """Return whether *command* starts a recognized unified runtime call."""

    stripped = command.strip()
    if not stripped.startswith("specify-runtime"):
        return False
    try:
        tokens = shlex.split(stripped, posix=os.name != "nt")
    except ValueError:
        return False
    return (
        len(tokens) >= 2
        and tokens[0] == "specify-runtime"
        and tokens[1] in _UNIFIED_RUNTIME_NAMESPACES
    )


def _inline_command_context(
    line: str,
    match: re.Match[str],
    previous_nonempty: str,
) -> str:
    """Return the local prose clause governing one inline-code span."""

    before = line[: match.start()]
    after = line[match.end() :]
    clause_start = max(before.rfind(mark) for mark in (".", ";", ",")) + 1
    clause_ends = [position for mark in (".", ";", ",") if (position := after.find(mark)) >= 0]
    clause_end = min(clause_ends) if clause_ends else len(after)
    local = before[clause_start:] + match.group(0) + after[:clause_end]
    if not before[clause_start:].strip():
        local = f"{previous_nonempty}\n{local}"
    return local


def rebind_unbound_specify_runtime_calls(
    text: str,
    launcher_command: str,
    *,
    command_renderer: Callable[[str], str] | None = None,
) -> tuple[str, int]:
    """Rebind only executable bare Specify calls recognized by diagnostics."""

    rendered_launcher = (
        command_renderer(launcher_command)
        if command_renderer is not None
        else launcher_command
    )
    count = 0
    fence_marker: str | None = None
    fence_is_shell_like = False
    fence_context = ""
    previous_nonempty = ""
    output: list[str] = []

    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        newline = raw_line[len(line) :]
        fence_match = _MARKDOWN_FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group("marker")
            if fence_marker is None:
                fence_marker = marker
                language = fence_match.group("language").lower()
                fence_is_shell_like = language not in _NON_SHELL_FENCE_LANGUAGES
                fence_context = previous_nonempty
            elif marker[0] == fence_marker[0]:
                fence_marker = None
                fence_is_shell_like = False
                fence_context = ""
                previous_nonempty = ""
            output.append(raw_line)
            continue

        command_match = _BARE_SPECIFY_LINE_RE.match(line)
        context = (
            f"{fence_context}\n{line}"
            if fence_marker is not None
            else f"{previous_nonempty}\n{line}"
        )
        if (
            (fence_marker is None or fence_is_shell_like)
            and command_match
            and _is_bare_specify_runtime_command(command_match.group("command"))
            and not _NON_EXECUTABLE_SPECIFY_CONTEXT_RE.search(context)
        ):
            command = command_match.group("command")
            line = (
                command_match.group("prefix")
                + rendered_launcher
                + command[len("specify") :]
                + command_match.group("suffix")
            )
            raw_line = line + newline
            count += 1

        if fence_marker is None:
            def replace_inline(match: re.Match[str]) -> str:
                nonlocal count
                code = match.group("code")
                if (
                    not _is_bare_specify_runtime_command(code)
                    or _NON_EXECUTABLE_SPECIFY_CONTEXT_RE.search(
                        _inline_command_context(line, match, previous_nonempty)
                    )
                ):
                    return match.group(0)
                leading = code[: len(code) - len(code.lstrip())]
                trailing = code[len(code.rstrip()) :]
                stripped = code.strip()
                count += 1
                return f"`{leading}{rendered_launcher}{stripped[len('specify'):]}{trailing}`"

            raw_line = _MARKDOWN_INLINE_CODE_RE.sub(replace_inline, raw_line)
            previous_nonempty = line if line.strip() else ""
        output.append(raw_line)
    return "".join(output), count


def rebind_unbound_unified_runtime_calls(
    text: str,
    launcher_command: str,
    *,
    command_renderer: Callable[[str], str] | None = None,
) -> tuple[str, int]:
    """Rebind recognized bare ``specify-runtime`` calls to the pinned binary."""

    rendered_launcher = (
        command_renderer(launcher_command)
        if command_renderer is not None
        else launcher_command
    )
    count = 0
    fence_marker: str | None = None
    fence_is_shell_like = False
    fence_context = ""
    previous_nonempty = ""
    output: list[str] = []

    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        newline = raw_line[len(line) :]
        fence_match = _MARKDOWN_FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group("marker")
            if fence_marker is None:
                fence_marker = marker
                language = fence_match.group("language").lower()
                fence_is_shell_like = language not in _NON_SHELL_FENCE_LANGUAGES
                fence_context = previous_nonempty
            elif marker[0] == fence_marker[0]:
                fence_marker = None
                fence_is_shell_like = False
                fence_context = ""
                previous_nonempty = ""
            output.append(raw_line)
            continue

        command_match = _BARE_UNIFIED_RUNTIME_LINE_RE.match(line)
        context = (
            f"{fence_context}\n{line}"
            if fence_marker is not None
            else f"{previous_nonempty}\n{line}"
        )
        if (
            (fence_marker is None or fence_is_shell_like)
            and command_match
            and _is_bare_unified_runtime_command(
                command_match.group("command")
            )
            and not _NON_EXECUTABLE_SPECIFY_CONTEXT_RE.search(context)
        ):
            command = command_match.group("command")
            suffix = command[len("specify-runtime") :]
            line = (
                command_match.group("prefix")
                + rendered_launcher
                + suffix
                + command_match.group("suffix")
            )
            raw_line = line + newline
            count += 1

        if fence_marker is None:
            def replace_inline(match: re.Match[str]) -> str:
                nonlocal count
                code = match.group("code")
                if (
                    not _is_bare_unified_runtime_command(code)
                    or _NON_EXECUTABLE_SPECIFY_CONTEXT_RE.search(
                        _inline_command_context(line, match, previous_nonempty)
                    )
                ):
                    return match.group(0)
                leading = code[: len(code) - len(code.lstrip())]
                trailing = code[len(code.rstrip()) :]
                stripped = code.strip()
                suffix = stripped[len("specify-runtime") :]
                count += 1
                return f"`{leading}{rendered_launcher}{suffix}{trailing}`"

            raw_line = _MARKDOWN_INLINE_CODE_RE.sub(replace_inline, raw_line)
            previous_nonempty = line if line.strip() else ""
        output.append(raw_line)
    return "".join(output), count


def _contains_unbound_specify_runtime_call(text: str) -> bool:
    _, count = rebind_unbound_specify_runtime_calls(
        text,
        "__SPEC_KIT_BOUND_SPECIFY__",
    )
    return count > 0


def _contains_unbound_unified_runtime_call(text: str) -> bool:
    _, count = rebind_unbound_unified_runtime_calls(
        text,
        "__SPEC_KIT_BOUND_SPECIFY_RUNTIME__",
    )
    return count > 0


def _generated_guidance_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    for rel_root in GENERATED_GUIDANCE_ROOTS:
        root = project_root / rel_root
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in GENERATED_GUIDANCE_SUFFIXES:
                files.append(path)
    for rel_path in GENERATED_CONTEXT_FILES:
        path = project_root / rel_path
        if path.is_file():
            files.append(path)
    for rel_path in GENERATED_GUIDANCE_FILES:
        path = project_root / rel_path
        if path.is_file():
            files.append(path)
    return files


def _generated_guidance_text(project_root: Path, path: Path, text: str) -> str:
    """Limit root context diagnostics to the runtime-owned managed block."""

    relative = path.relative_to(project_root).as_posix()
    if relative not in GENERATED_CONTEXT_FILES:
        return text
    blocks = SPEC_KIT_MANAGED_BLOCK_RE.findall(text)
    return blocks[0] if len(blocks) == 1 else ""


def diagnose_claude_personal_skill_shadows(
    project_root: Path,
) -> list[dict[str, str]]:
    """Report personal Claude skills that take precedence over managed project skills."""

    manifest = _load_config(
        project_root
        / ".specify"
        / "integrations"
        / "claude.manifest.json"
    )
    if not isinstance(manifest, dict):
        return []
    files = manifest.get("files")
    if not isinstance(files, dict):
        return []

    configured_root = str(os.environ.get("CLAUDE_CONFIG_DIR") or "").strip()
    try:
        claude_root = (
            Path(configured_root).expanduser()
            if configured_root
            else Path.home() / ".claude"
        ).resolve(strict=False)
        resolved_project_root = project_root.resolve(strict=False)
    except (OSError, RuntimeError):
        return []
    personal_skills_root = claude_root / "skills"
    project_skills_root = resolved_project_root / ".claude" / "skills"
    if personal_skills_root == project_skills_root:
        return []

    collisions: list[str] = []
    for relative in files:
        normalized = str(relative).replace("\\", "/")
        parts = normalized.split("/")
        if (
            len(parts) != 4
            or parts[:2] != [".claude", "skills"]
            or parts[3] != "SKILL.md"
            or parts[2] in {"", ".", ".."}
        ):
            continue
        skill_name = parts[2]
        if not skill_name.startswith(("sp-", "spx-")):
            continue
        project_skill = project_skills_root / skill_name / "SKILL.md"
        personal_skill = personal_skills_root / skill_name / "SKILL.md"
        if not project_skill.is_file() or not personal_skill.is_file():
            continue
        try:
            if project_skill.samefile(personal_skill):
                continue
        except OSError:
            pass
        collisions.append(skill_name)

    if not collisions:
        return []

    map_priority = {
        "sp-map-scan": 0,
        "sp-map-build": 1,
        "sp-map-update": 2,
    }
    collisions = sorted(
        set(collisions),
        key=lambda name: (map_priority.get(name, 3), name),
    )
    preview = ", ".join(f"/{name}" for name in collisions[:8])
    if len(collisions) > 8:
        preview += f", +{len(collisions) - 8} more"
    affected_directories = ", ".join(collisions)
    return [
        {
            "code": "claude-personal-skills-shadow-project",
            "severity": "repairable-block",
            "summary": (
                "Claude personal skills shadow "
                f"{len(collisions)} project-installed Spec Kit skill(s): {preview}. "
                "Claude resolves personal skills before project skills, so the "
                "project-managed workflow is not authoritative."
            ),
            "repair": (
                "1. Pause Claude Code and choose a new backup location outside "
                f"Claude's `skills` directory (`{personal_skills_root}`). Do not "
                "remove an original without a recoverable copy.\n"
                "2. Move these personal workflow directories from that `skills` "
                f"directory into the backup: {affected_directories}. Expected: each "
                "listed directory exists in the backup and no longer exists under "
                f"`{personal_skills_root}`. If a destination already exists or any "
                "move fails, stop and use a fresh backup directory so neither copy "
                "is overwritten.\n"
                "3. Then fully restart Claude Code from the project root. Expected: "
                f"project skills are discovered from `{project_skills_root}`. If "
                "they are not, verify `CLAUDE_CONFIG_DIR` and the project root.\n"
                "4. Run `specify check`. Expected: diagnostic "
                "`claude-personal-skills-shadow-project` is absent. If it remains, "
                "return that diagnostic and its sanitized paths.\n"
                "5. Resume the interrupted `/sp-*` or `/spx-*` command from its "
                "normal entrypoint. For map work, discard hand-authored cognition "
                "artifacts from the shadowed run and resume at `/sp-map-scan`."
            ),
        }
    ]


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

    if not isinstance(body, str):
        return body

    launcher = load_project_specify_launcher(project_root)
    runtime_launcher = load_runtime_launcher(project_root)
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
        if tokens[0] == "workflow":
            return (
                f"{SPECIFY_RUNTIME_UNAVAILABLE_MARKER}:"
                "retired-specify-workflow-placeholder"
            )
        if (
            len(tokens) >= 2
            and tokens[0] == "specify-runtime"
            and tokens[1] in _UNIFIED_RUNTIME_NAMESPACES
        ):
            if runtime_launcher is not None:
                return render_command((*runtime_launcher.argv, *tokens[1:]))
            return (
                f"{SPECIFY_RUNTIME_UNAVAILABLE_MARKER}:"
                f"{render_command(tokens)}"
            )
        if launcher is None:
            return render_command((*default.argv, *tokens))
        subcommand = project_specify_subcommand(project_root, tokens)
        return subcommand.command if subcommand is not None else render_command((*default.argv, *tokens))

    rendered = pattern.sub(replace, rendered)
    rendered, _ = rebind_unbound_specify_runtime_calls(
        rendered,
        active_launcher.command,
    )
    runtime_command = (
        runtime_launcher.command
        if runtime_launcher is not None
        else f"{SPECIFY_RUNTIME_UNAVAILABLE_MARKER}:specify-runtime"
    )
    rendered, _ = rebind_unbound_unified_runtime_calls(
        rendered,
        runtime_command,
    )
    return rendered


def rebind_unavailable_specify_runtime_commands(
    project_root: Path,
    body: str,
    *,
    command_renderer: Callable[[str], str] | None = None,
) -> str:
    """Replace recoverable unavailable markers with the pinned runtime binary."""

    launcher = load_runtime_launcher(project_root)
    if launcher is None:
        return body
    marker = f"{SPECIFY_RUNTIME_UNAVAILABLE_MARKER}:specify-runtime"
    command = (
        command_renderer(launcher.command)
        if command_renderer is not None
        else launcher.command
    )
    rebound = body.replace(marker, command)
    rebound, _ = rebind_unbound_unified_runtime_calls(
        rebound,
        launcher.command,
        command_renderer=command_renderer,
    )
    return rebound


def write_project_specify_launcher_config(
    project_root: Path,
    launcher: SpecifyLauncherSpec | None = None,
    *,
    preserve_conflicting_wrapper: bool = False,
) -> Path | None:
    """Persist the preferred ``specify`` launcher into ``.specify/config.json``.

    Git sources are persisted directly. A normal wheel, tool, editable, or
    otherwise environment-local install is recorded outside the project and
    exposed through a cwd-independent machine dispatcher plus a project repair
    shim. Generated guidance therefore contains neither a PATH-level ``specify``
    call nor an ephemeral absolute interpreter path. Existing user/project keys
    are preserved.
    """

    explicit_launcher = launcher is not None
    resolved = launcher or resolve_specify_launcher_spec()
    if resolved.argv == default_specify_launcher_spec().argv:
        return None

    config_path = project_root / SPECIFY_CONFIG_FILE
    payload = _load_config(config_path)
    if payload is None:
        return None
    existing_payload = payload.get(SPECIFY_LAUNCHER_CONFIG_KEY)
    existing = _normalize_specify_launcher_payload(existing_payload)
    if not explicit_launcher and isinstance(existing_payload, dict):
        raw_runtime_id = existing_payload.get("runtime_id")
        raw_argv = _payload_argv(existing_payload)
        recognized_legacy_source = (
            raw_argv is not None
            and _source_bound_specify_launcher_spec(raw_argv) is not None
        )
        owned_by_this_runtime = (
            raw_runtime_id == SPECIFY_RUNTIME_ID or recognized_legacy_source
        )
        if not owned_by_this_runtime:
            # An unknown or explicitly foreign record is not ours to replace
            # during ordinary init/repair. An explicit caller may intentionally
            # take ownership by supplying a trusted launcher.
            return config_path

    persisted = _source_bound_specify_launcher_spec(resolved.argv)
    if resolved.source == "local_environment":
        expected_local = current_environment_specify_launcher_spec()
        if resolved.argv != expected_local.argv or resolved.runtime_id != SPECIFY_RUNTIME_ID:
            raise ValueError(
                "local_environment launcher must match the currently loaded Specify runtime"
            )
        binding_id = (
            existing.binding_id
            if existing is not None
            and existing.kind == "machine_binding"
            and existing.runtime_id == SPECIFY_RUNTIME_ID
            and SPECIFY_BINDING_ID_RE.fullmatch(existing.binding_id)
            else uuid.uuid4().hex
        )
        _write_project_launcher_binding(binding_id, resolved)
        if not _machine_binding_probe(binding_id):
            raise RuntimeError(
                "the machine-local Spec Kit Plus binding failed its runtime identity probe; "
                "the project launcher and configuration were not changed"
            )
        try:
            install_project_specify_launcher(project_root, binding_id)
        except RuntimeError:
            if (
                not preserve_conflicting_wrapper
                or existing is None
                or existing.kind != "machine_binding"
                or existing.binding_id != binding_id
            ):
                raise
        persisted = project_local_specify_launcher_spec(binding_id)
    elif persisted is None:
        raise ValueError(
            "Specify launchers must use the current local environment or the "
            "canonical commit-pinned Spec Kit Plus uvx source"
        )

    desired = _launcher_payload(persisted)
    if payload.get(SPECIFY_LAUNCHER_CONFIG_KEY) == desired:
        return config_path

    payload[SPECIFY_LAUNCHER_CONFIG_KEY] = desired
    config_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        config_path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    return config_path


def write_runtime_launcher_config(project_root: Path, binary: str | Path) -> Path | None:
    """Persist the preferred ``specify-runtime`` binary into ``.specify/config.json``."""

    from .specify_runtime import (
        _sha256_file,
        current_runtime_binding_metadata,
        materialize_project_runtime_entrypoint,
        project_runtime_launcher_arg,
    )

    project_binary = materialize_project_runtime_entrypoint(project_root, binary)
    launcher_arg = project_runtime_launcher_arg()
    launcher = SpecifyLauncherSpec(
        command=render_command((launcher_arg,)),
        argv=(launcher_arg,),
    )
    config_path = project_root / SPECIFY_CONFIG_FILE
    payload = _load_config(config_path)
    if payload is None:
        return None

    desired = _launcher_payload(launcher)
    binding = {
        **current_runtime_binding_metadata(),
        "runtime_binary_sha256": _sha256_file(project_binary),
        "runtime_entrypoint": launcher_arg,
    }
    if (
        payload.get(RUNTIME_LAUNCHER_CONFIG_KEY) == desired
        and payload.get(RUNTIME_LAUNCHER_BINDING_CONFIG_KEY) == binding
    ):
        return config_path

    payload[RUNTIME_LAUNCHER_CONFIG_KEY] = desired
    payload[RUNTIME_LAUNCHER_BINDING_CONFIG_KEY] = binding
    config_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        config_path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    return config_path


def diagnose_project_runtime_compatibility(project_root: Path) -> list[dict[str, str]]:
    """Inspect persisted launcher and generated runtime surfaces for stale or broken state."""

    issues: list[dict[str, str]] = []
    issues.extend(diagnose_claude_personal_skill_shadows(project_root))
    learning_index = project_root / ".specify" / "memory" / "learnings" / "INDEX.md"

    def _read_text_if_exists(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _uses_legacy_feature_root_contract(text: str) -> bool:
        lowered = text.lower()
        return ".specify/features" not in lowered and (
            "specs/$branch" in lowered
            or 'get_feature_dir() { echo "$1/specs/$2"; }' in lowered
            or 'join-path $reporoot "specs/$branch"' in lowered
            or ".specify/specs" in lowered
            or 'features_dir="$repo_root/specs"' in lowered
            or "$specsdir = join-path $reporoot 'specs'" in lowered
        )

    launcher_config = _load_config(project_root / SPECIFY_CONFIG_FILE)
    raw_launcher_present = (
        isinstance(launcher_config, dict)
        and SPECIFY_LAUNCHER_CONFIG_KEY in launcher_config
    )
    raw_runtime_launcher_present = (
        isinstance(launcher_config, dict)
        and RUNTIME_LAUNCHER_CONFIG_KEY in launcher_config
    )
    launcher = load_project_specify_launcher(project_root)
    if raw_launcher_present and launcher is None:
        trusted_repair_launcher = resolve_specify_launcher_spec()
        trusted_repair_command = render_command(
            (*trusted_repair_launcher.argv, "integration", "repair")
        )
        issues.append(
            {
                "code": "broken-project-launcher",
                "summary": (
                    "Persisted project launcher is configured but unavailable because "
                    "it is malformed, untrusted, or uses an unsupported runtime source."
                ),
                "repair": (
                    "Preserve `.specify/config.json`, then run the exact trusted repair "
                    f"command `{trusted_repair_command}` from the project root. Verify "
                    "the repaired launcher reports runtime identity "
                    f"`{SPECIFY_RUNTIME_ID}` before continuing."
                ),
            }
        )
    if launcher is not None and launcher.argv:
        if not project_specify_launcher_is_available(project_root, launcher):
            issues.append(
                {
                    "code": "broken-project-launcher",
                    "summary": "Persisted project launcher is configured but unavailable.",
                    "repair": "Repair `.specify/config.json`. If regeneration is required, use the `specify init --here --force` command surface from a trusted launcher source and supply the same integration-specific options that originally bootstrapped the project.",
                }
            )
        stale_launcher_files: list[str] = []
        unbound_launcher_files: list[str] = []
        for path in _generated_guidance_files(project_root):
            text = _generated_guidance_text(
                project_root,
                path,
                _read_text_if_exists(path),
            )
            if _stale_source_bound_specify_launchers(text, launcher):
                stale_launcher_files.append(path.relative_to(project_root).as_posix())
            if _contains_unbound_specify_runtime_call(text):
                unbound_launcher_files.append(
                    path.relative_to(project_root).as_posix()
                )
        if stale_launcher_files:
            preview = ", ".join(stale_launcher_files[:5])
            if len(stale_launcher_files) > 5:
                preview += f", +{len(stale_launcher_files) - 5} more"
            issues.append(
                {
                    "code": "stale-generated-specify-launcher",
                    "summary": f"Generated workflow guidance embeds an older source-bound `specify` launcher than `.specify/config.json`: {preview}.",
                    "repair": "Run `specify integration repair` from the current trusted launcher, or re-run `specify init --here --force` with the active integration options, so generated commands are re-rendered from `.specify/config.json`.",
                }
            )
        if unbound_launcher_files:
            preview = ", ".join(unbound_launcher_files[:5])
            if len(unbound_launcher_files) > 5:
                preview += f", +{len(unbound_launcher_files) - 5} more"
            repair = project_specify_subcommand(
                project_root,
                ("integration", "repair"),
            )
            repair_command = (
                repair.command if repair is not None else launcher.command
            )
            issues.append(
                {
                    "code": "unbound-generated-specify-launcher",
                    "summary": (
                        "Generated workflow guidance invokes the PATH-level bare "
                        f"`specify` command despite a project-pinned launcher: {preview}."
                    ),
                    "repair": (
                        f"Run `{repair_command}` from the trusted project launcher, then "
                        "re-run the active initialization profile if the listed generated "
                        "files remain unbound. Verify that their executable Specify CLI "
                        "calls begin with the launcher recorded in `.specify/config.json`."
                    ),
                }
            )

    if (project_root / ".specify").exists():
        runtime_launcher = load_runtime_launcher(project_root)
        runtime_compatible = runtime_launcher_is_compatible(
            project_root, runtime_launcher
        )
        marker_files: list[str] = []
        unbound_runtime_files: list[str] = []
        for path in _generated_guidance_files(project_root):
            text = _generated_guidance_text(
                project_root,
                path,
                _read_text_if_exists(path),
            )
            relative = path.relative_to(project_root).as_posix()
            if f"{SPECIFY_RUNTIME_UNAVAILABLE_MARKER}:specify-runtime" in text:
                marker_files.append(relative)
            if runtime_compatible and _contains_unbound_unified_runtime_call(text):
                unbound_runtime_files.append(relative)

        if not runtime_compatible:
            repair = project_specify_subcommand(
                project_root,
                ("integration", "repair"),
            )
            repair_command = repair.command if repair else "specify integration repair"
            issues.append(
                {
                    "code": (
                        "broken-specify-runtime-launcher"
                        if runtime_launcher or raw_runtime_launcher_present
                        else "missing-specify-runtime-launcher"
                    ),
                    "summary": "The project-pinned specify-runtime launcher is unavailable.",
                    "repair": (
                        f"Run `{repair_command}` to install a compatible runtime, pin it in "
                        "`.specify/config.json`, and rebind unmodified generated guidance. "
                        "Do not probe Python `specify` subcommands as a runtime fallback."
                    ),
                }
            )
        if marker_files:
            preview = ", ".join(marker_files[:5])
            if len(marker_files) > 5:
                preview += f", +{len(marker_files) - 5} more"
            issues.append(
                {
                    "code": "unrebound-specify-runtime-launcher",
                    "summary": (
                        "Generated guidance still contains unavailable specify-runtime "
                        f"markers: {preview}."
                    ),
                    "repair": (
                        "Use a trusted external Spec Kit Plus launcher to run `integration repair`; "
                        "user-modified files are preserved and must be merged using the reported tutorial."
                    ),
                }
            )
        if unbound_runtime_files:
            preview = ", ".join(unbound_runtime_files[:5])
            if len(unbound_runtime_files) > 5:
                preview += f", +{len(unbound_runtime_files) - 5} more"
            issues.append(
                {
                    "code": "unbound-generated-specify-runtime-launcher",
                    "summary": (
                        "Generated workflow guidance invokes PATH-level bare "
                        "recognized `specify-runtime` namespace calls "
                        f"despite a project-pinned launcher: {preview}."
                    ),
                    "repair": (
                        "Run `integration repair` through a trusted external Spec Kit Plus launcher, "
                        "then verify each executable call begins with the runtime_launcher "
                        "recorded in `.specify/config.json`."
                    ),
                }
            )

    if (project_root / ".specify").exists() and not learning_index.exists():
        issues.append(
            {
                "code": "missing-learning-index",
                "summary": "Generated project memory is missing the self-learning v2 index.",
                "repair": "Run `specify learning ensure` or refresh generated assets with `specify integration repair`.",
            }
        )

    powershell_common = project_root / ".specify" / "scripts" / "powershell" / "common.ps1"
    powershell_common_text = _read_text_if_exists(powershell_common)
    if powershell_common_text:
        has_prefix_helper = "function Find-FeatureDirByPrefix" in powershell_common_text
        uses_prefix_resolution = "Find-FeatureDirByPrefix -RepoRoot $repoRoot -BranchName $currentBranch" in powershell_common_text
        if not has_prefix_helper or not uses_prefix_resolution:
            issues.append(
                {
                    "code": "stale-powershell-feature-resolver",
                    "summary": "Generated PowerShell workflow scripts are stale and still rely on exact branch-to-feature-dir matching.",
                    "repair": "Refresh the generated scripts by rerunning the `specify init --here --force` command surface with the active `--ai <agent>` option, or reinstall the active integration.",
                }
            )

    shared_runtime_scripts = (
        project_root / ".specify" / "scripts" / "bash" / "common.sh",
        project_root / ".specify" / "scripts" / "bash" / "create-new-feature.sh",
        project_root / ".specify" / "scripts" / "powershell" / "common.ps1",
        project_root / ".specify" / "scripts" / "powershell" / "create-new-feature.ps1",
    )
    if any(
        script_path.exists() and _uses_legacy_feature_root_contract(_read_text_if_exists(script_path))
        for script_path in shared_runtime_scripts
    ):
        issues.append(
            {
                "code": "stale-feature-root-contract",
                "summary": "Generated shared workflow scripts still target legacy feature roots instead of the canonical `.specify/features/` contract.",
                "repair": "Run `specify integration repair` (or re-run `specify init --here --force --ai <agent>`) so generated shared scripts and templates refresh to the canonical `.specify/features/` feature-root contract.",
            }
        )

    generated_analyze = project_root / ".specify" / "templates" / "commands" / "analyze.md"
    generated_analyze_text = _read_text_if_exists(generated_analyze)
    if generated_analyze_text and "{{specify-subcmd:lane resolve --command analyze --ensure-worktree}}" not in generated_analyze_text:
        issues.append(
            {
                "code": "stale-analyze-lane-routing-template",
                "summary": "Generated analyze workflow guidance is stale and does not require lane resolution before branch-only fallback.",
                "repair": "Run `specify integration repair` (or re-run `specify init --here --force --ai <agent>`) so generated workflow templates refresh to the current routing contract.",
            }
        )

    generated_learning_candidates = (
        project_root / ".specify" / "templates" / "passive-skills" / "spec-kit-project-learning" / "SKILL.md",
        project_root / ".specify" / "templates" / "passive-skills" / "learning.md",
    )
    generated_learning_text = ""
    for candidate in generated_learning_candidates:
        generated_learning_text = _read_text_if_exists(candidate)
        if generated_learning_text:
            break
    if generated_learning_text and "--origin-artifact" in generated_learning_text:
        issues.append(
            {
                "code": "stale-review-learning-command-surface",
                "summary": "Generated learning guidance still references unsupported `review-learning` helper options.",
                "repair": "Run `specify integration repair` so generated workflow and passive-skill assets refresh to the current helper command surface.",
            }
        )

    codex_hooks = project_root / ".codex" / "hooks.json"
    codex_hooks_payload = _load_config(codex_hooks)
    if isinstance(codex_hooks_payload, dict) and contains_claude_managed_hook_entries(codex_hooks_payload):
        issues.append(
            {
                "code": "codex-claude-hook-artifact",
                "summary": "Codex native hook configuration contains misplaced Claude managed hook commands.",
                "repair": "Run `specify integration repair` for this Codex project so `.codex/hooks.json` stops invoking `specify-hook claude` routes.",
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
                        args = hook.get("args")
                        if "claude-hook-dispatch.py" in command:
                            stale_claude_hook = True
                        if command.startswith('node ".specify/bin/specify-hook.mjs" claude '):
                            stale_claude_hook = True
                        if ".specify/bin/specify-hook" in command and "claude" in command:
                            if "${CLAUDE_PROJECT_DIR}" in command or "$CLAUDE_PROJECT_DIR" in command:
                                stale_claude_hook = True
                        if (
                            command == "node"
                            and isinstance(args, list)
                            and args
                            and (
                                str(args[0]).startswith("${CLAUDE_PROJECT_DIR}/.specify/bin/specify-hook")
                                or str(args[0]).startswith('"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook')
                            )
                        ):
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
                    "code": "stale-claude-managed-hook-command",
                    "summary": "Claude managed hook commands still use shell-parsed direct Python, POSIX, cmd, or PowerShell-style launcher commands instead of the shell-free Node launcher.",
                    "repair": "Run `specify integration repair` (or `specify init --here --force --ai claude`) so `.claude/settings.json` refreshes managed hook commands.",
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
