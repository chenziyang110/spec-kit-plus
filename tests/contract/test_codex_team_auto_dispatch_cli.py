import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.codex_team.state_paths import batch_record_path, dispatch_record_path, task_record_path


def _create_codex_project(tmp_path: Path) -> Path:
    project = tmp_path / "codex-team-auto-dispatch"
    project.mkdir()
    spec_root = project / ".specify"
    spec_root.mkdir()
    (spec_root / "integration.json").write_text(json.dumps({"integration": "codex"}), encoding="utf-8")
    (spec_root / "codex-team").mkdir(parents=True, exist_ok=True)
    (spec_root / "project-map").mkdir(parents=True, exist_ok=True)
    (spec_root / "project-map" / "status.json").write_text(
        json.dumps(
            {
                "version": 1,
                "last_mapped_commit": "",
                "last_mapped_at": "2026-04-21T00:00:00Z",
                "last_mapped_branch": "",
                "freshness": "missing",
                "last_refresh_reason": "seeded-test",
                "dirty": False,
                "dirty_reasons": [],
            }
        ),
        encoding="utf-8",
    )
    feature_dir = project / "specs" / "001-auto-dispatch"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before next phase
""",
        encoding="utf-8",
    )
    return project


def _fake_tmux_env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "fake-tmux-bin"
    bin_dir.mkdir()
    script_name = "tmux.exe" if os.name == "nt" else "tmux"
    (bin_dir / script_name).write_text("", encoding="utf-8")
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


def _invoke_in_project(project: Path, args: list[str], env: dict[str, str] | None = None):
    runner = CliRunner()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, args, env=env or os.environ)
    finally:
        os.chdir(old_cwd)
    return result


def test_team_auto_dispatch_subcommand_dispatches_ready_batch(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    result = _invoke_in_project(
        project,
        ["team", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    assert "Parallel Batch 1.1" in result.output
    assert dispatch_record_path(project, "default-parallel-batch-1-1-t002").exists()
    assert dispatch_record_path(project, "default-parallel-batch-1-1-t003").exists()


def test_team_api_auto_dispatch_returns_json_payload(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    result = _invoke_in_project(
        project,
        ["team", "api", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output.strip())
    assert envelope["operation"] == "auto-dispatch"
    assert envelope["status"] == "ok"
    assert envelope["payload"]["batch_id"] == "default-parallel-batch-1-1"
    assert envelope["payload"]["batch_name"] == "Parallel Batch 1.1"
    assert envelope["payload"]["join_point_name"] == "Join Point 1.1"
    assert envelope["payload"]["dispatched_task_ids"] == ["T002", "T003"]


def test_team_complete_batch_marks_join_point_complete(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    dispatched = _invoke_in_project(
        project,
        ["team", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )
    assert dispatched.exit_code == 0, dispatched.output

    result = _invoke_in_project(
        project,
        ["team", "complete-batch", "--batch-id", "default-parallel-batch-1-1"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    batch_payload = json.loads(batch_record_path(project, "default-parallel-batch-1-1").read_text(encoding="utf-8"))
    assert batch_payload["status"] == "completed"
    task_payload = json.loads(task_record_path(project, "T002").read_text(encoding="utf-8"))
    assert task_payload["metadata"]["join_points"]["Join Point 1.1"]["status"] == "complete"


def test_team_api_complete_batch_returns_json_payload(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    dispatched = _invoke_in_project(
        project,
        ["team", "api", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )
    assert dispatched.exit_code == 0, dispatched.output

    result = _invoke_in_project(
        project,
        ["team", "api", "complete-batch", "--batch-id", "default-parallel-batch-1-1"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output.strip())
    assert envelope["operation"] == "complete-batch"
    assert envelope["status"] == "ok"
    assert envelope["payload"]["batch_id"] == "default-parallel-batch-1-1"
    assert envelope["payload"]["status"] == "completed"


def test_team_auto_dispatch_blocks_when_project_map_is_dirty(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    status_path = project / ".specify" / "project-map" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["freshness"] = "stale"
    payload["dirty"] = True
    payload["dirty_reasons"] = ["shared_surface_changed"]
    status_path.write_text(json.dumps(payload), encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["team", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )

    assert result.exit_code != 0
    assert "Project-map freshness is stale" in result.output
    assert "map-codebase" in result.output
