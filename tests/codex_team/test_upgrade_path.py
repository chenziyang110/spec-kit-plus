from specify_cli.codex_team.installer import upgrade_existing_codex_project
from specify_cli.integrations.manifest import IntegrationManifest


def test_upgrade_existing_codex_project_installs_runtime_assets(codex_team_project_root):
    manifest = IntegrationManifest("codex", codex_team_project_root)

    created = upgrade_existing_codex_project(
        codex_team_project_root,
        manifest,
        integration_key="codex",
    )

    assert len(created) == 3
    assert (codex_team_project_root / ".specify" / "codex-team" / "runtime.json").exists()
    assert (codex_team_project_root / ".specify" / "config.json").exists()
