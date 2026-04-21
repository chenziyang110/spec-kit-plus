"""Install helpers for Codex-only team/runtime assets."""

from __future__ import annotations

from pathlib import Path

from .state_paths import codex_team_state_root

CODEX_TEAM_HELPER_FILES = (
    ".specify/codex-team/runtime.json",
    ".specify/codex-team/README.md",
    ".specify/config.json",
)
CODEx_TEAM_HELPER_FILES = CODEX_TEAM_HELPER_FILES

__all__ = [
    "CODEX_TEAM_HELPER_FILES",
    "CODEx_TEAM_HELPER_FILES",
    "codex_team_assets_for_project",
    "install_codex_team_assets",
    "integration_supports_codex_team",
    "missing_codex_team_assets",
    "upgrade_existing_codex_project",
]


def integration_supports_codex_team(integration_key: str | None) -> bool:
    """Return whether the integration should receive Codex team assets."""
    return integration_key == "codex"


def codex_team_assets_for_project(project_root: Path) -> list[Path]:
    """Return the helper files that define the installed Codex team surface."""
    return [project_root / rel for rel in CODEX_TEAM_HELPER_FILES]


def install_codex_team_assets(
    project_root: Path,
    manifest,
    *,
    integration_key: str,
) -> list[Path]:
    """Install helper/config assets for Codex projects.

    The caller owns the integration manifest and can pass any object that
    implements ``record_file(rel_path, content)``.
    """
    if not integration_supports_codex_team(integration_key):
        return []

    created = []
    runtime_payload = (
        '{\n'
        '  "surface": "specify team",\n'
        '  "integration": "codex",\n'
        '  "tmux_required": true,\n'
        f'  "state_root": "{codex_team_state_root(project_root).as_posix()}"\n'
        '}\n'
    )
    created.append(
        manifest.record_file(".specify/codex-team/runtime.json", runtime_payload)
    )
    created.append(
        manifest.record_file(
            ".specify/codex-team/README.md",
            (
                "# Codex Team Runtime\n\n"
                "This project exposes the Codex-only team/runtime surface "
                "through `specify team`.\n"
            ),
        )
    )

    # Register the notify hook in .specify/config.json
    # This hook is triggered after every agent turn and checks for ready team batches.
    config_payload = (
        '{\n'
        '  "notify": "specify team notify-hook"\n'
        '}\n'
    )
    created.append(
        manifest.record_file(".specify/config.json", config_payload)
    )

    # Also register in .codex/config.toml for the official Codex CLI
    codex_config_path = project_root / ".codex" / "config.toml"
    notify_cmd = "specify team notify-hook"
    
    # We use a simple append or create approach for .codex/config.toml
    # In a real scenario, we might want a proper TOML parser/merger like oh-my-codex
    codex_notify_line = f'notify = ["{notify_cmd}"]\n'
    
    if codex_config_path.exists():
        content = codex_config_path.read_text(encoding="utf-8")
        if "notify =" not in content:
            new_content = codex_notify_line + "\n" + content
            codex_config_path.write_text(new_content, encoding="utf-8")
    else:
        codex_config_path.parent.mkdir(parents=True, exist_ok=True)
        codex_config_path.write_text(codex_notify_line, encoding="utf-8")
    
    manifest.record_existing(".codex/config.toml")

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
