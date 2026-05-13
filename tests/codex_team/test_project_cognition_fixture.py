def test_codex_team_fixture_seeds_canonical_cognition_status(codex_team_project_root):
    assert (codex_team_project_root / ".specify" / "project-cognition" / "status.json").exists()
    assert not (codex_team_project_root / ".specify" / "project-map" / "status.json").exists()
