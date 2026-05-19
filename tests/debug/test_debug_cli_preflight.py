from pathlib import Path

from specify_cli.debug.cli import _project_map_preflight_for_debug


def test_debug_preflight_warns_instead_of_exiting_on_stale_cognition(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "debug-project"
    project.mkdir()
    (project / ".specify").mkdir()
    monkeypatch.chdir(project)

    def stale(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "review",
            "recommended_next_action": "run_map_update",
            "reasons": ["changed path not reflected in map"],
        }

    monkeypatch.setattr("specify_cli.debug.cli.inspect_project_cognition_freshness", stale)

    _project_map_preflight_for_debug()


def test_debug_preflight_warns_on_reviewable_possibly_stale_cognition(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "debug-project-review"
    project.mkdir()
    (project / ".specify").mkdir()
    monkeypatch.chdir(project)

    def reviewable(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "possibly_stale",
            "state": "runtime_stale",
            "readiness": "review",
            "recommended_next_action": "run_map_update",
            "reasons": ["reviewable advisory state"],
        }

    monkeypatch.setattr("specify_cli.debug.cli.inspect_project_cognition_freshness", reviewable)

    _project_map_preflight_for_debug()
