import json
from pathlib import Path

from specify_cli.codex_team.installer import install_codex_team_assets
from specify_cli.integrations.codex import CodexIntegration
from specify_cli.integrations.manifest import IntegrationManifest

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
    assert config["notify"] == "specify team notify-hook"


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
    assert 'notify = ["specify", "team", "notify-hook"]' in content
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
    assert merged_specify_config["notify"] == "specify team notify-hook"
    assert merged_specify_config["preserve_me"] == {"enabled": True}
    assert 'notify = ["specify", "team", "notify-hook"]' in codex_config.read_text(encoding="utf-8")

    assert ".codex/config.toml" not in manifest.files
    assert ".specify/config.json" not in manifest.files

    removed, skipped = CodexIntegration().uninstall(project_root, manifest)

    assert not skipped
    assert codex_config.exists()
    assert codex_config.read_text(encoding="utf-8") == original_codex_config
    assert json.loads(specify_config.read_text(encoding="utf-8")) == original_specify_config
    assert not (project_root / ".specify" / "codex-team" / "install-state.json").exists()

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
