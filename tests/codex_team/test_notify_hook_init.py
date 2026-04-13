import json
from pathlib import Path
from specify_cli.codex_team.installer import install_codex_team_assets
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
    
    # Should create 3 files now: runtime.json, README.md, and config.json
    assert len(created) == 3
    
    config_path = project_root / ".specify" / "config.json"
    assert config_path.exists()
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    assert "notify" in config
    assert config["notify"] == "specify team notify-hook"

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
