import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.codex_team.state_paths import batch_record_path, dispatch_record_path, result_record_path, task_record_path
from specify_cli.execution import worker_task_result_payload
from specify_cli.execution.result_schema import RuleAcknowledgement, ValidationResult, WorkerTaskResult


def _create_codex_project(tmp_path: Path) -> Path:
    project = tmp_path / "codex-team-auto-dispatch"
    project.mkdir()
    spec_root = project / ".specify"
    spec_root.mkdir()
    (spec_root / "integration.json").write_text(json.dumps({"integration": "codex"}), encoding="utf-8")
    (spec_root / "teams").mkdir(parents=True, exist_ok=True)
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
    (spec_root / "memory").mkdir(parents=True, exist_ok=True)
    (spec_root / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST preserve subagent validation evidence\n",
        encoding="utf-8",
    )
    feature_dir = project / "specs" / "001-auto-dispatch"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Implementation Constitution",
                "",
                "### Required Implementation References",
                "",
                "- `src/contracts/example.py`",
                "",
                "### Forbidden Implementation Drift",
                "",
                "- Do not create a parallel contract surface",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A in src/workers/worker_a.py
- [ ] T003 [P] Worker B in src/workers/worker_b.py
- [X] T004 Sequential follow-up in src/follow_up.py
- [ ] T005 [P] Worker C in src/workers/worker_c.py
- [ ] T006 [P] Worker D in src/workers/worker_d.py

## Validation Gates

- pytest -q -k auto_dispatch

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before next phase

**Parallel Batch 2.1**

- `T005`
- `T006`

**Join Point 2.1**: final merge
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
    env["SPECIFY_CODEX_TEAM_EXECUTOR"] = "legacy-heartbeat-runtime"
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


def _write_success_results(project: Path) -> None:
    for task_id in ("T002", "T003"):
        request_id = f"default-parallel-batch-1-1-{task_id.lower()}"
        path = result_record_path(project, request_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        result = WorkerTaskResult(
            task_id=task_id,
            status="success",
            changed_files=[f"src/{task_id.lower()}.py"],
            validation_results=[ValidationResult(command="pytest -q -k auto_dispatch", status="passed", output="1 passed")],
            summary=f"{task_id} completed",
            rule_acknowledgement=RuleAcknowledgement(
                required_references_read=True,
                forbidden_drift_respected=True,
                context_bundle_read=True,
                paths_read=["src/contracts/example.py"],
            ),
        )
        path.write_text(json.dumps(worker_task_result_payload(result), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_success_results_for(project: Path, batch_name: str, task_ids: tuple[str, ...]) -> None:
    slug = batch_name.lower().replace(" ", "-")
    for task_id in task_ids:
        request_id = f"default-{slug}-{task_id.lower()}"
        path = result_record_path(project, request_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        result = WorkerTaskResult(
            task_id=task_id,
            status="success",
            changed_files=[f"src/{task_id.lower()}.py"],
            validation_results=[ValidationResult(command="pytest -q -k auto_dispatch", status="passed", output="1 passed")],
            summary=f"{task_id} completed",
            rule_acknowledgement=RuleAcknowledgement(
                required_references_read=True,
                forbidden_drift_respected=True,
                context_bundle_read=True,
                paths_read=["src/contracts/example.py"],
            ),
        )
        path.write_text(json.dumps(worker_task_result_payload(result), ensure_ascii=False, indent=2), encoding="utf-8")


def test_team_auto_dispatch_subcommand_dispatches_ready_batch(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    result = _invoke_in_project(
        project,
        ["sp-teams", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
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
        ["sp-teams", "api", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
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
        ["sp-teams", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )
    assert dispatched.exit_code == 0, dispatched.output
    _write_success_results(project)

    result = _invoke_in_project(
        project,
        ["sp-teams", "complete-batch", "--batch-id", "default-parallel-batch-1-1"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    batch_payload = json.loads(batch_record_path(project, "default-parallel-batch-1-1").read_text(encoding="utf-8"))
    assert batch_payload["status"] == "completed"
    task_payload = json.loads(task_record_path(project, "T002").read_text(encoding="utf-8"))
    assert task_payload["metadata"]["join_points"]["Join Point 1.1"]["status"] == "complete"


def test_team_complete_batch_auto_dispatches_next_ready_batch(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    dispatched = _invoke_in_project(
        project,
        ["sp-teams", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )
    assert dispatched.exit_code == 0, dispatched.output
    _write_success_results(project)

    result = _invoke_in_project(
        project,
        ["sp-teams", "complete-batch", "--batch-id", "default-parallel-batch-1-1"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    lowered = result.output.lower()
    assert "auto-dispatched next batch" in lowered
    assert "parallel batch 2.1" in lowered
    assert dispatch_record_path(project, "default-parallel-batch-2-1-t005").exists()
    assert dispatch_record_path(project, "default-parallel-batch-2-1-t006").exists()


def test_team_api_complete_batch_returns_json_payload(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    dispatched = _invoke_in_project(
        project,
        ["sp-teams", "api", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )
    assert dispatched.exit_code == 0, dispatched.output
    _write_success_results(project)

    result = _invoke_in_project(
        project,
        ["sp-teams", "api", "complete-batch", "--batch-id", "default-parallel-batch-1-1"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output.strip())
    assert envelope["operation"] == "complete-batch"
    assert envelope["status"] == "ok"
    assert envelope["payload"]["batch_id"] == "default-parallel-batch-1-1"
    assert envelope["payload"]["status"] == "completed"


def test_team_api_complete_batch_reports_auto_dispatched_next_batch(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    dispatched = _invoke_in_project(
        project,
        ["sp-teams", "api", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )
    assert dispatched.exit_code == 0, dispatched.output
    _write_success_results(project)

    result = _invoke_in_project(
        project,
        ["sp-teams", "api", "complete-batch", "--batch-id", "default-parallel-batch-1-1"],
        env=env,
    )

    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output.strip())
    assert envelope["payload"]["next_batch_id"] == "default-parallel-batch-2-1"
    assert envelope["payload"]["next_batch_name"] == "Parallel Batch 2.1"
    assert envelope["payload"]["next_dispatched_task_ids"] == ["T005", "T006"]


def test_team_submit_result_updates_task_and_batch_state(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    dispatched = _invoke_in_project(
        project,
        ["sp-teams", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )
    assert dispatched.exit_code == 0, dispatched.output

    _write_success_results(project)
    for task_id in ("T002", "T003"):
        request_id = f"default-parallel-batch-1-1-{task_id.lower()}"
        result_path = result_record_path(project, request_id)
        submit = _invoke_in_project(
            project,
            ["sp-teams", "submit-result", "--request-id", request_id, "--result-file", str(result_path)],
            env=env,
        )
        assert submit.exit_code == 0, submit.output

    batch_payload = json.loads(batch_record_path(project, "default-parallel-batch-1-1").read_text(encoding="utf-8"))
    task_payload = json.loads(task_record_path(project, "T002").read_text(encoding="utf-8"))
    assert batch_payload["status"] == "completed"
    assert task_payload["status"] == "completed"
    assert task_payload["metadata"]["result_request_id"] == "default-parallel-batch-1-1-t002"
    assert task_payload["metadata"]["join_points"]["Join Point 1.1"]["status"] == "complete"


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
        ["sp-teams", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )

    assert result.exit_code != 0
    assert "Project-map freshness is stale" in result.output
    assert "map-scan, then map-build" in result.output


def test_team_auto_dispatch_blocks_when_baseline_build_is_known_blocked(tmp_path: Path):
    project = _create_codex_project(tmp_path)
    env = _fake_tmux_env(tmp_path)

    status_path = project / ".specify" / "project-map" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["freshness"] = "fresh"
    payload["dirty"] = False
    payload["dirty_reasons"] = []
    status_path.write_text(json.dumps(payload), encoding="utf-8")

    baseline_path = project / ".specify" / "teams" / "state" / "baseline-build.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(
            {
                "status": "blocked",
                "reason": "baseline compile debt: missing generated headers",
                "checked_at": "2026-04-26T00:00:00Z",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["sp-teams", "auto-dispatch", "--feature-dir", "specs/001-auto-dispatch"],
        env=env,
    )

    assert result.exit_code != 0
    lowered = result.output.lower()
    assert "baseline build is blocked" in lowered
    normalized = " ".join(lowered.split())
    assert "missing generated headers" in normalized
