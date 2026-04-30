import json
from pathlib import Path

from specify_cli.codex_team.installer import (
    install_codex_team_assets,
    resolve_specify_launcher_spec,
)
from specify_cli.integrations.codex import CodexIntegration
from specify_cli.integrations.manifest import IntegrationManifest


def test_resolve_specify_launcher_spec_prefers_uvx_for_git_direct_url(monkeypatch, tmp_path: Path):
    dist_info_dir = tmp_path / "specify_cli-0.5.1.dev0.dist-info"
    dist_info_dir.mkdir()
    (dist_info_dir / "direct_url.json").write_text(
        json.dumps(
            {
                "url": "https://github.com/chenziyang110/spec-kit-plus.git",
                "vcs_info": {
                    "vcs": "git",
                    "commit_id": "bedf8377221e854d6522472e8765dc88ae67e66c",
                },
            }
        ),
        encoding="utf-8",
    )

    class _FakeDistribution:
        def __init__(self, path: Path):
            self._path = path

        def read_text(self, filename: str) -> str | None:
            return (self._path / filename).read_text(encoding="utf-8")

    monkeypatch.setattr(
        "specify_cli.launcher.importlib_metadata.distribution",
        lambda name: _FakeDistribution(dist_info_dir),
    )
    monkeypatch.setattr(
        "specify_cli.launcher.shutil.which",
        lambda name: f"/fake/{name}" if name == "uvx" else None,
    )

    launcher = resolve_specify_launcher_spec()

    assert launcher.command == (
        "uvx --from "
        "git+https://github.com/chenziyang110/spec-kit-plus.git@"
        "bedf8377221e854d6522472e8765dc88ae67e66c "
        "specify"
    )
    assert launcher.argv == (
        "uvx",
        "--from",
        "git+https://github.com/chenziyang110/spec-kit-plus.git@bedf8377221e854d6522472e8765dc88ae67e66c",
        "specify",
    )


def test_install_codex_team_assets_uses_source_bound_notify_when_launcher_detected(monkeypatch, tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    manifest = IntegrationManifest("codex", project_root)

    monkeypatch.setattr(
        "specify_cli.codex_team.installer.resolve_specify_launcher_spec",
        lambda: type(
            "_Launcher",
            (),
            {
                "command": (
                    "uvx --from "
                    "git+https://github.com/chenziyang110/spec-kit-plus.git@"
                    "bedf8377221e854d6522472e8765dc88ae67e66c "
                    "specify"
                ),
                "argv": (
                    "uvx",
                    "--from",
                    "git+https://github.com/chenziyang110/spec-kit-plus.git@bedf8377221e854d6522472e8765dc88ae67e66c",
                    "specify",
                ),
            },
        )(),
    )

    install_codex_team_assets(
        project_root,
        manifest,
        integration_key="codex",
    )

    config = json.loads((project_root / ".specify" / "config.json").read_text(encoding="utf-8"))
    assert config["notify"] == (
        "uvx --from "
        "git+https://github.com/chenziyang110/spec-kit-plus.git@"
        "bedf8377221e854d6522472e8765dc88ae67e66c "
        "specify sp-teams notify-hook"
    )
    assert (
        'notify = ["uvx", "--from", '
        '"git+https://github.com/chenziyang110/spec-kit-plus.git@bedf8377221e854d6522472e8765dc88ae67e66c", '
        '"specify", "sp-teams", "notify-hook"]'
    ) in (project_root / ".codex" / "config.toml").read_text(encoding="utf-8")

def test_install_codex_team_assets_creates_notify_hook_config(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    
    # Mock manifest
    manifest = IntegrationManifest("codex", project_root)
    
    created = install_codex_team_assets(
        project_root,
        manifest,
        integration_key="codex",
    )
    
    # Fresh installs also create a project-local Codex config.
    assert len(created) == 4
    
    config_path = project_root / ".specify" / "config.json"
    assert config_path.exists()
    assert (project_root / ".codex" / "config.toml").exists()
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    assert "notify" in config
    assert config["notify"] == "specify sp-teams notify-hook"


def test_install_codex_team_assets_creates_codex_config_with_argv_notify(monkeypatch, tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    manifest = IntegrationManifest("codex", project_root)

    monkeypatch.setattr(
        "specify_cli.codex_team.installer.can_configure_specify_teams_mcp",
        lambda: True,
    )

    install_codex_team_assets(
        project_root,
        manifest,
        integration_key="codex",
    )

    codex_config = project_root / ".codex" / "config.toml"
    assert codex_config.exists()
    content = codex_config.read_text(encoding="utf-8")
    assert 'notify = ["specify", "sp-teams", "notify-hook"]' in content
    assert "[mcp_servers.specify_teams]" in content
    assert 'command = "specify-teams-mcp"' in content
    assert ".codex/config.toml" in manifest.files


def test_install_codex_team_assets_restores_existing_configs_on_uninstall(monkeypatch, tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    codex_config = project_root / ".codex" / "config.toml"
    codex_config.parent.mkdir(parents=True, exist_ok=True)
    original_codex_config = 'model = "gpt-5.5"\nnotify = ["python", "legacy-hook.py"]\n'
    codex_config.write_text(original_codex_config, encoding="utf-8")

    specify_config = project_root / ".specify" / "config.json"
    specify_config.parent.mkdir(parents=True, exist_ok=True)
    original_specify_config = {
        "notify": "legacy notify",
        "preserve_me": {"enabled": True},
    }
    specify_config.write_text(json.dumps(original_specify_config, indent=2), encoding="utf-8")

    manifest = IntegrationManifest("codex", project_root)
    monkeypatch.setattr(
        "specify_cli.codex_team.installer.can_configure_specify_teams_mcp",
        lambda: False,
    )

    install_codex_team_assets(
        project_root,
        manifest,
        integration_key="codex",
    )

    merged_specify_config = json.loads(specify_config.read_text(encoding="utf-8"))
    assert merged_specify_config["notify"] == "specify sp-teams notify-hook"
    assert merged_specify_config["preserve_me"] == {"enabled": True}
    assert 'notify = ["specify", "sp-teams", "notify-hook"]' in codex_config.read_text(encoding="utf-8")

    assert ".codex/config.toml" not in manifest.files
    assert ".specify/config.json" not in manifest.files

    removed, skipped = CodexIntegration().uninstall(project_root, manifest)

    assert not skipped
    assert codex_config.exists()
    assert codex_config.read_text(encoding="utf-8") == original_codex_config
    assert json.loads(specify_config.read_text(encoding="utf-8")) == original_specify_config
    assert not (project_root / ".specify" / "teams" / "install-state.json").exists()

def test_install_codex_team_assets_skips_non_codex(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    manifest = IntegrationManifest("other", project_root)
    
    created = install_codex_team_assets(
        project_root,
        manifest,
        integration_key="other",
    )
    
    assert len(created) == 0
