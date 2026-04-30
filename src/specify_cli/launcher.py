"""Helpers for invoking the same ``specify`` source that initialized a project."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata as importlib_metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any


SPECIFY_PACKAGE_NAME = "specify-cli"
SPECIFY_CONFIG_FILE = ".specify/config.json"
SPECIFY_LAUNCHER_CONFIG_KEY = "specify_launcher"


@dataclass(frozen=True)
class SpecifyLauncherSpec:
    """Command forms that invoke a preferred ``specify`` install source."""

    command: str
    argv: tuple[str, ...]


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


def _load_config(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _launcher_payload(launcher: SpecifyLauncherSpec) -> dict[str, Any]:
    return {
        "command": launcher.command,
        "argv": list(launcher.argv),
    }


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
