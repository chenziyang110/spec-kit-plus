"""Exercise the production parent/child boundaries, not just backend metadata."""

import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli.codex_team import agent_teams_executor, auto_dispatch, packet_executor
from specify_cli.codex_team.runtime_bridge import (
    bootstrap_runtime_session,
    dispatch_runtime_task,
    submit_runtime_result,
)
from specify_cli.codex_team.state_paths import (
    codex_team_state_root,
    dispatch_record_path,
    runtime_session_path,
)
from specify_cli.execution.packet_validator import PacketValidationError


@pytest.fixture
def dispatched_context(monkeypatch, codex_team_project_root: Path):
    project = codex_team_project_root
    state = codex_team_state_root(project)
    packet_path = state / "packets" / "req-42.json"
    packet_path.parent.mkdir(parents=True)
    packet_path.write_text(
        json.dumps({
            "feature_id": "001-feature", "task_id": "T042", "story_id": "US1",
            "objective": "Implement bounded task",
            "scope": {"write_scope": ["src/task.py"], "read_scope": ["src/contracts.py"]},
            "required_references": [{"path": "src/contracts.py", "reason": "preserve contract"}],
            "hard_rules": ["preserve existing behavior"],
            "forbidden_drift": ["no unrelated writes"],
            "validation_gates": ["pytest -q"], "done_criteria": ["works"],
            "handoff_requirements": ["return changed files"],
            "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": True},
            "packet_version": 1,
        }), encoding="utf-8",
    )
    result_path = state / "results" / "req-42.json"
    bootstrap_runtime_session(project, "session-a")
    dispatch_runtime_task(
        project, session_id="session-a", request_id="req-42", target_worker="worker-42",
        packet_path=str(packet_path), result_path=str(result_path),
        packet_summary={"task_id": "T042", "write_scope": ["src/task.py"]},
    )
    binding = {
        "SPECIFY_WORK_ID": "work-parent",
        "SPECIFY_WORK_FENCE": "17",
        "SPECIFY_WORK_REVISION": "4",
        "SPECIFY_WORK_PACKET_FILE": str(packet_path),
        "SPECIFY_WORK_PACKET_SHA256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
        "SPECIFY_EXECUTION_ACTIVITY_ID": "activity-parent",
        "SPECIFY_FEATURE_BRANCH_POLICY": "keep-current",
    }
    for key, value in binding.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SPECIFY_RUN_ID", "retired-parent-run")
    monkeypatch.setenv("SPECIFY_RUN_MANAGED", "1")
    monkeypatch.setenv("SPECIFY_RUN_WORKSPACE", str(project.parent))
    monkeypatch.setenv("SPECIFY_WORKSPACE_ROOT", str(project.parent))
    monkeypatch.setenv(
        "WSLENV",
        "SPECIFY_RUN_ID:SPECIFY_RUN_WORKSPACE/p:SPECIFY_WORK_ID:SPECIFY_WORK_FENCE:"
        "SPECIFY_WORK_PACKET_FILE/p:SPECIFY_EXECUTION_ACTIVITY_ID:SPECIFY_FEATURE_BRANCH_POLICY",
    )
    owned = {
        path: path.read_bytes()
        for path in (
            packet_path, dispatch_record_path(project, "req-42"),
            runtime_session_path(project, "session-a"),
        )
    }
    return SimpleNamespace(
        project=project, state=state, packet_path=packet_path, result_path=result_path,
        binding=binding, owned=owned,
    )


def _assert_environment(env, context):
    assert not any(key.upper().startswith("SPECIFY_RUN_") for key in env)
    assert "SPECIFY_WORKSPACE_ROOT" not in env
    assert env["WSLENV"] == (
        "SPECIFY_WORK_ID:SPECIFY_WORK_FENCE:SPECIFY_WORK_PACKET_FILE/p:"
        "SPECIFY_EXECUTION_ACTIVITY_ID:SPECIFY_FEATURE_BRANCH_POLICY"
    )
    for key, value in context.binding.items():
        assert env[key] == value


def _assert_owner_unchanged(context):
    for path, original in context.owned.items():
        assert path.read_bytes() == original
    assert not context.result_path.exists()
    assert os.environ["SPECIFY_RUN_ID"] == "retired-parent-run"


@pytest.mark.parametrize("route", ["worker", "batch"])
@pytest.mark.parametrize("spawn_fails", [False, True])
def test_actual_parent_dispatch_keeps_project_and_packet_owner(
    monkeypatch, dispatched_context, route: str, spawn_fails: bool
):
    context = dispatched_context
    captured = {}

    def fake_popen(command, **kwargs):
        captured.update(command=command, **kwargs)
        if spawn_fails:
            raise OSError("definite spawn failure")
        return SimpleNamespace(pid=12345)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    task_specs = [{
        "task_id": "T042", "request_id": "req-42", "subject": "T042",
        "description": "Confirmed packet scope: src/task.py; no unrelated writes.",
    }]

    def dispatch():
        if route == "worker":
            auto_dispatch.launch_dispatched_worker(
                context.project, session_id="session-a", worker_id="worker-42",
                task_id="T042", request_id="req-42", result_path=str(context.result_path),
            )
        else:
            auto_dispatch.launch_agent_teams_batch_executor(
                context.project, session_id="session-a", batch_id="batch-42",
                runtime_cli_path="runtime-cli.js", task_specs=task_specs,
            )

    if spawn_fails:
        with pytest.raises(OSError, match="definite spawn failure"):
            dispatch()
    else:
        dispatch()

    command = captured["command"]
    assert captured["cwd"] == context.project
    assert command[command.index("--project-root") + 1] == str(context.project)
    _assert_environment(captured["env"], context)
    if route == "worker":
        assert command[command.index("--request-id") + 1] == "req-42"
        assert command[command.index("--session-id") + 1] == "session-a"
        assert command[command.index("--worker-id") + 1] == "worker-42"
        assert command[command.index("--task-id") + 1] == "T042"
        assert command[command.index("--result-path") + 1] == str(context.result_path)
    else:
        manifest = json.loads(Path(command[command.index("--manifest-path") + 1]).read_text())
        assert manifest["cwd"] == str(context.project)
        assert manifest["session_id"] == "session-a"
        assert manifest["tasks"] == task_specs
    _assert_owner_unchanged(context)


@pytest.mark.parametrize("wrong_task", [False, True])
def test_packet_executor_filters_environment_without_bypassing_result_validation(
    monkeypatch, dispatched_context, wrong_task: bool
):
    context = dispatched_context
    result = {
        "task_id": "T999" if wrong_task else "T042", "status": "success",
        "changed_files": ["src/task.py"],
        "validation_results": [{"command": "pytest -q", "status": "passed", "output": "1 passed"}],
        "summary": "executed", "rule_acknowledgement": {
            "required_references_read": True, "forbidden_drift_respected": True,
        },
    }
    executor = context.project / "assert-child-context.py"
    executor.write_text("\n".join([
        "import json, os, sys", "from pathlib import Path",
        "payload = json.loads(sys.stdin.read())",
        f"assert Path.cwd() == Path({str(context.project)!r})",
        f"assert payload['project_root'] == {str(context.project)!r}",
        "assert payload['request_id'] == 'req-42'",
        "assert payload['session_id'] == 'session-a'",
        "assert payload['worker_id'] == 'worker-42'",
        "assert payload['packet']['task_id'] == 'T042'",
        "assert payload['packet']['scope']['write_scope'] == ['src/task.py']",
        "assert not any(key.upper().startswith('SPECIFY_RUN_') for key in os.environ)",
        "assert 'SPECIFY_WORKSPACE_ROOT' not in os.environ",
        f"assert all(os.environ[key] == value for key, value in {context.binding!r}.items())",
        f"print({json.dumps(result)!r})",
    ]), encoding="utf-8")
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_PACKET_EXECUTOR", str(executor))

    outcome = packet_executor.execute_packet(
        packet_executor.load_packet(context.packet_path), project_root=context.project,
        session_id="session-a", request_id="req-42", worker_id="worker-42",
        worktree=context.project / "worker-area",
    )

    if wrong_task:
        assert outcome.result.status == "blocked"
        assert "invalid structured worker result" in outcome.reason
    else:
        assert outcome.result.status == "success", outcome.reason
        assert outcome.result.changed_files == ["src/task.py"]
    _assert_owner_unchanged(context)


def test_batch_runtime_cli_retains_board_binding_and_nonzero_exit(monkeypatch, dispatched_context):
    context = dispatched_context
    manifest_path = context.project / "batch-manifest.json"
    state_root = context.state / "agent-teams/batch-42"
    manifest_path.write_text(json.dumps({
        "runtime_cli_path": str(context.project / "fake-runtime.py"),
        "state_root": str(state_root), "session_id": "session-a",
        "team_name": "batch-42", "worker_count": 1, "tasks": [], "cwd": str(context.project),
    }), encoding="utf-8")
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(command=command, **kwargs)
        return subprocess.CompletedProcess(command, 23, "", "runtime failed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert agent_teams_executor.run_manifest(context.project, manifest_path) == 1
    assert captured["cwd"] == str(context.project)
    assert json.loads(captured["input"])["cwd"] == str(context.project)
    _assert_environment(captured["env"], context)
    assert captured["env"]["SPECIFY_TEAM_STATE_ROOT"] == str(state_root)
    assert captured["env"]["SP_TEAMS_STATE_ROOT"] == str(state_root)
    _assert_owner_unchanged(context)


@pytest.mark.parametrize("status", ["pending", "success", "blocked", "failed"])
def test_parent_result_submission_rejects_foreign_task_without_changing_owner(
    dispatched_context, status: str
):
    context = dispatched_context
    with pytest.raises(PacketValidationError, match="does not match dispatched packet"):
        submit_runtime_result(
            context.project, session_id="session-a", request_id="req-42",
            result={"task_id": "T999", "status": status, "summary": "foreign task"},
        )
    _assert_owner_unchanged(context)
