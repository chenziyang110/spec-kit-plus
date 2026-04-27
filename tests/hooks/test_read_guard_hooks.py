from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-read-guard-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def test_read_guard_allows_repository_local_paths(tmp_path: Path):
    project = _create_project(tmp_path)
    target = project / "src" / "demo.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("print('demo')\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.read_guard.validate",
        {"target_path": str(target)},
    )

    assert result.status == "ok"
    assert result.data["target_path"] == str(target.resolve())


def test_read_guard_blocks_sensitive_env_files_even_inside_repo(tmp_path: Path):
    project = _create_project(tmp_path)
    target = project / ".env"
    target.write_text("SECRET=1\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.read_guard.validate",
        {"target_path": str(target)},
    )

    assert result.status == "blocked"
    assert any(".env" in message for message in result.errors)


def test_read_guard_blocks_paths_outside_repository_root(tmp_path: Path):
    project = _create_project(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("demo\n", encoding="utf-8")

    result = run_quality_hook(
        project,
        "workflow.read_guard.validate",
        {"target_path": str(outside)},
    )

    assert result.status == "blocked"
    assert any("outside project root" in message for message in result.errors)
