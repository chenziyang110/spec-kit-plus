import specify_cli.debug.cli as cli_module

from tests.conftest import strip_ansi


def test_project_map_preflight_for_debug_is_advisory(monkeypatch, tmp_path, capsys):
    project_root = tmp_path / "debug-project"
    project_root.mkdir()
    (project_root / ".specify").mkdir()
    monkeypatch.chdir(project_root)
    monkeypatch.setattr(
        cli_module,
        "run_specify_runtime",
        lambda _args, *, cwd, check=True: {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "review",
            "recommended_next_action": "run_map_update",
            "reasons": ["changed surface requires review"],
        },
    )

    cli_module._project_map_preflight_for_debug()

    output = strip_ansi(capsys.readouterr().out).lower()
    assert "advisory" in output
    assert "run_map_update" in output
    assert "changed surface requires review" in output
