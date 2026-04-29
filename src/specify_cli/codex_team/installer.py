"""Install helpers for Codex-only team/runtime assets."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata as importlib_metadata
import json
import os
import re
import subprocess
import shutil
from typing import Any

from .state_paths import codex_team_state_root

CODEX_TEAM_HELPER_FILES = (
    ".specify/teams/runtime.json",
    ".specify/teams/README.md",
    ".specify/config.json",
)
CODEx_TEAM_HELPER_FILES = CODEX_TEAM_HELPER_FILES

CODEX_TEAM_INSTALL_STATE_FILE = ".specify/teams/install-state.json"
TEAM_NOTIFY_TOML_TOKENS = ("sp-teams", "notify-hook")
SPECIFY_TEAMS_MCP_SERVER_NAME = "specify_teams"
SPECIFY_TEAMS_MCP_COMMAND = "specify-teams-mcp"
SPECIFY_PACKAGE_NAME = "specify-cli"


@dataclass(frozen=True)
class SpecifyLauncherSpec:
    """Command forms that invoke the current specify install source."""

    command: str
    argv: tuple[str, ...]

__all__ = [
    "CODEX_TEAM_HELPER_FILES",
    "CODEx_TEAM_HELPER_FILES",
    "CODEX_TEAM_INSTALL_STATE_FILE",
    "can_configure_specify_teams_mcp",
    "codex_team_assets_for_project",
    "install_codex_team_assets",
    "integration_supports_codex_team",
    "missing_codex_team_assets",
    "restore_codex_team_project_configs",
    "resolve_specify_launcher_spec",
    "upgrade_existing_codex_project",
]


def integration_supports_codex_team(integration_key: str | None) -> bool:
    """Return whether the integration should receive Codex team assets."""
    return integration_key == "codex"


def can_configure_specify_teams_mcp() -> bool:
    """Return whether the optional teams MCP facade can be configured."""
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
    except ImportError:
        return False
    return shutil.which(SPECIFY_TEAMS_MCP_COMMAND) is not None


def codex_team_assets_for_project(project_root: Path) -> list[Path]:
    """Return the helper files that define the installed Codex team surface."""
    return [project_root / rel for rel in CODEX_TEAM_HELPER_FILES]


def _record_tracked_file(
    manifest,
    created: list[Path],
    project_root: Path,
    rel_path: str,
    content: str,
) -> None:
    path = manifest.record_file(rel_path, content)
    created.append(path)


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} contains invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _render_command(argv: tuple[str, ...]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(argv))
    return " ".join(argv)


def _default_specify_launcher_spec() -> SpecifyLauncherSpec:
    argv = ("specify",)
    return SpecifyLauncherSpec(command=_render_command(argv), argv=argv)


def resolve_specify_launcher_spec() -> SpecifyLauncherSpec:
    """Return the best available launcher for the current specify install source."""

    default = _default_specify_launcher_spec()

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
    return SpecifyLauncherSpec(command=_render_command(argv), argv=argv)


def _escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _notify_json_command(launcher: SpecifyLauncherSpec) -> str:
    return f"{launcher.command} sp-teams notify-hook"


def _notify_line(launcher: SpecifyLauncherSpec) -> str:
    values = ", ".join(
        f'"{_escape_toml_string(token)}"' for token in launcher.argv + TEAM_NOTIFY_TOML_TOKENS
    )
    return f"notify = [{values}]"


def _split_root_and_tables(content: str) -> tuple[list[str], list[str]]:
    root_lines: list[str] = []
    table_lines: list[str] = []
    in_root = True
    for line in content.splitlines():
        if in_root and re.match(r"^\s*\[[^\]]+\]\s*$", line):
            in_root = False
        if in_root:
            root_lines.append(line)
        else:
            table_lines.append(line)
    return root_lines, table_lines


def _strip_root_notify(root_lines: list[str]) -> list[str]:
    stripped: list[str] = []
    index = 0
    while index < len(root_lines):
        line = root_lines[index]
        if re.match(r"^\s*notify\s*=", line):
            bracket_depth = line.count("[") - line.count("]")
            index += 1
            while bracket_depth > 0 and index < len(root_lines):
                bracket_depth += root_lines[index].count("[") - root_lines[index].count("]")
                index += 1
            continue
        stripped.append(line)
        index += 1
    return stripped


def _merge_notify_root_lines(
    root_lines: list[str],
    launcher: SpecifyLauncherSpec,
) -> list[str]:
    desired_notify = _notify_line(launcher)
    sanitized_root = _strip_root_notify(root_lines)
    prefix: list[str] = []
    index = 0
    while index < len(sanitized_root):
        candidate = sanitized_root[index]
        if candidate.strip() == "" or candidate.lstrip().startswith("#"):
            prefix.append(candidate)
            index += 1
            continue
        break
    body = sanitized_root[index:]

    merged: list[str] = list(prefix)
    if merged and merged[-1].strip():
        merged.append("")
    merged.append(desired_notify)
    if body and body[0].strip():
        merged.append("")
    merged.extend(body)
    return merged


def _strip_managed_teams_mcp_table(table_lines: list[str]) -> list[str]:
    stripped: list[str] = []
    index = 0
    header = f"[mcp_servers.{SPECIFY_TEAMS_MCP_SERVER_NAME}]"
    while index < len(table_lines):
        line = table_lines[index]
        if line.strip() != header:
            stripped.append(line)
            index += 1
            continue

        index += 1
        while index < len(table_lines) and not re.match(r"^\s*\[[^\]]+\]\s*$", table_lines[index]):
            index += 1
        while stripped and stripped[-1].strip() == "":
            stripped.pop()
        while index < len(table_lines) and table_lines[index].strip() == "":
            index += 1
    return stripped


def _managed_teams_mcp_block() -> list[str]:
    return [
        f"[mcp_servers.{SPECIFY_TEAMS_MCP_SERVER_NAME}]",
        f'command = "{SPECIFY_TEAMS_MCP_COMMAND}"',
        "enabled = true",
        "startup_timeout_sec = 5",
    ]


def _merge_codex_config_toml(
    existing: str,
    *,
    launcher: SpecifyLauncherSpec,
    include_teams_mcp: bool,
) -> str:
    root_lines, table_lines = _split_root_and_tables(existing)
    merged_root = _merge_notify_root_lines(root_lines, launcher)
    merged_tables = _strip_managed_teams_mcp_table(table_lines)

    if include_teams_mcp:
        if merged_tables and merged_tables[-1].strip():
            merged_tables.append("")
        merged_tables.extend(_managed_teams_mcp_block())

    result_lines = list(merged_root)
    if merged_tables:
        if result_lines and result_lines[-1].strip():
            result_lines.append("")
        result_lines.extend(merged_tables)
    return "\n".join(result_lines).rstrip() + "\n"


def _restore_entry(project_root: Path, rel_path: str, content: str) -> Path:
    path = project_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def restore_codex_team_project_configs(project_root: Path) -> list[Path]:
    """Restore pre-install project config files when backup metadata exists."""
    install_state_path = project_root / CODEX_TEAM_INSTALL_STATE_FILE
    if not install_state_path.exists():
        return []

    payload = _load_json_object(install_state_path)
    restored: list[Path] = []
    for rel_path, content in payload.get("restore_files", {}).items():
        if not isinstance(rel_path, str) or not isinstance(content, str):
            continue
        restored.append(_restore_entry(project_root, rel_path, content))
    return restored


def install_codex_team_assets(
    project_root: Path,
    manifest,
    *,
    integration_key: str,
) -> list[Path]:
    """Install helper/config assets for Codex projects."""
    if not integration_supports_codex_team(integration_key):
        return []

    created: list[Path] = []
    restore_files: dict[str, str] = {}
    teams_mcp_supported = can_configure_specify_teams_mcp()
    launcher = resolve_specify_launcher_spec()

    runtime_payload = {
        "surface": "sp-teams",
        "integration": "codex",
        "tmux_required": True,
        "state_root": codex_team_state_root(project_root).as_posix(),
        "teams_mcp_supported": teams_mcp_supported,
    }
    _record_tracked_file(
        manifest,
        created,
        project_root,
        ".specify/teams/runtime.json",
        _json_text(runtime_payload),
    )
    _record_tracked_file(
        manifest,
        created,
        project_root,
        ".specify/teams/README.md",
        (
            "# Codex Team Runtime\n\n"
            "This project exposes the Codex-only team/runtime surface through `sp-teams`.\n\n"
            "Optional agent-facing MCP facade: install `specify-cli[mcp]` so "
            f"`{SPECIFY_TEAMS_MCP_COMMAND}` can be registered in `.codex/config.toml`.\n"
        ),
    )

    specify_config_path = project_root / ".specify" / "config.json"
    if specify_config_path.exists():
        restore_files[".specify/config.json"] = specify_config_path.read_text(encoding="utf-8")
        specify_config = _load_json_object(specify_config_path)
    else:
        specify_config = {}
    specify_config["notify"] = _notify_json_command(launcher)
    specify_config_text = _json_text(specify_config)
    if ".specify/config.json" in restore_files:
        specify_config_path.write_text(specify_config_text, encoding="utf-8")
    else:
        _record_tracked_file(
            manifest,
            created,
            project_root,
            ".specify/config.json",
            specify_config_text,
    )

    codex_config_path = project_root / ".codex" / "config.toml"
    if codex_config_path.exists():
        restore_files[".codex/config.toml"] = codex_config_path.read_text(encoding="utf-8")
        existing_codex_config = restore_files[".codex/config.toml"]
    else:
        existing_codex_config = ""
    codex_config_text = _merge_codex_config_toml(
        existing_codex_config,
        launcher=launcher,
        include_teams_mcp=teams_mcp_supported,
    )
    if ".codex/config.toml" in restore_files:
        codex_config_path.write_text(codex_config_text, encoding="utf-8")
    else:
        codex_config_path.parent.mkdir(parents=True, exist_ok=True)
        _record_tracked_file(
            manifest,
            created,
            project_root,
            ".codex/config.toml",
            codex_config_text,
        )

    if restore_files:
        _record_tracked_file(
            manifest,
            created,
            project_root,
            CODEX_TEAM_INSTALL_STATE_FILE,
            _json_text({"restore_files": restore_files}),
        )

    return created


def upgrade_existing_codex_project(
    project_root: Path,
    manifest,
    *,
    integration_key: str,
) -> list[Path]:
    """Optional upgrade path for existing Codex projects."""
    return install_codex_team_assets(
        project_root,
        manifest,
        integration_key=integration_key,
    )


def missing_codex_team_assets(project_root: Path) -> list[Path]:
    """Return helper files that have not yet been installed."""
    return [
        path for path in codex_team_assets_for_project(project_root) if not path.exists()
    ]
