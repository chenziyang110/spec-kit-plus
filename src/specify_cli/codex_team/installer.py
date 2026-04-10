"""Install helpers for Codex-only team/runtime assets."""

from __future__ import annotations

from pathlib import Path

from .state_paths import codex_team_state_root

CODEX_TEAM_HELPER_FILES = (
    ".specify/codex-team/runtime.json",
    ".specify/codex-team/README.md",
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
