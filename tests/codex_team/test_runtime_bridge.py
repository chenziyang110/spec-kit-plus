import json
from pathlib import Path

import pytest

from specify_cli.codex_team.runtime_bridge import (
    RuntimeEnvironmentError,
    codex_team_runtime_status,
    detect_team_runtime_backend,
    ensure_tmux_available,
    bootstrap_runtime_session,
    dispatch_runtime_task,
    submit_runtime_result,
)
from specify_cli.codex_team.state_paths import dispatch_record_path, result_record_path
from specify_cli.execution import worker_task_result_payload
from specify_cli.execution.result_schema import RuleAcknowledgement, ValidationResult, WorkerTaskResult


def test_ensure_tmux_available_raises_when_tmux_missing(monkeypatch):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)

    with pytest.raises(RuntimeEnvironmentError) as excinfo:
        ensure_tmux_available()

    assert "tmux is required" in str(excinfo.value)


def test_detect_runtime_backend_uses_psmux_on_native_windows(monkeypatch):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\psmux.exe" if name == "psmux" else None,
    )

    backend = detect_team_runtime_backend()

    assert backend["available"] is True
    assert backend["name"] == "psmux"


def test_detect_runtime_backend_uses_winget_links_psmux_on_native_windows(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    links_dir = tmp_path / "Microsoft" / "WinGet" / "Links"
    links_dir.mkdir(parents=True)
    (links_dir / "psmux.exe").write_text("", encoding="utf-8")

    backend = detect_team_runtime_backend()

    assert backend["available"] is True
    assert backend["name"] == "psmux"
    assert str(links_dir / "psmux.exe") == backend["binary"]


def test_ensure_tmux_available_mentions_psmux_on_native_windows(monkeypatch):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)

    with pytest.raises(RuntimeEnvironmentError) as excinfo:
        ensure_tmux_available()

    message = str(excinfo.value)
    assert "psmux" in message
    assert "winget install psmux" in message


def test_runtime_status_reports_codex_availability(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["available"] is True
    assert status["runtime_backend"] == "tmux"
    assert status["runtime_backend_available"] is True
    assert status["runtime_state"]["session"]["environment_check"] == "pass"


def test_runtime_status_reports_psmux_backend_on_native_windows(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\psmux.exe" if name == "psmux" else None,
    )

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["available"] is True
    assert status["runtime_backend"] == "psmux"
    assert status["runtime_backend_available"] is True
    assert status["runtime_state"]["session"]["environment_check"] == "pass"


def test_runtime_status_reports_non_codex_as_unavailable(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    status = codex_team_runtime_status(codex_team_project_root, integration_key="claude")

    assert status["available"] is False
    assert status["runtime_state"]["session"]["status"] == "created"


def test_runtime_status_surfaces_extension_and_git_prerequisites(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.codex_team_extension_installed", lambda project_root: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.codex_team_git_readiness",
        lambda project_root: {
            "git_repo_detected": False,
            "git_head_available": False,
            "leader_workspace_clean": False,
            "worktree_ready": False,
            "git_next_steps": ['Create an initial commit before teams execution: git add . && git commit -m "Initial commit"'],
        },
    )

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["agent_teams_extension_installed"] is False
    assert status["git_repo_detected"] is False
    assert status["git_head_available"] is False
    assert status["leader_workspace_clean"] is False
    assert status["worktree_ready"] is False
    assert status["teams_ready"] is False
    assert any("specify extension add agent-teams" in step for step in status["next_steps"])
    assert any("initial commit" in step.lower() for step in status["next_steps"])


def test_submit_runtime_result_writes_canonical_result_and_updates_dispatch(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    bootstrap_runtime_session(codex_team_project_root, "result-session")
    packet_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets" / "req-result.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        """
{
  "feature_id": "001-feature",
  "task_id": "T001",
  "story_id": "US1",
  "objective": "Implement thing",
  "scope": {"write_scope": ["src/app.py"], "read_scope": ["src/contracts.py"]},
  "required_references": [{"path": "src/contracts.py", "reason": "preserve contract"}],
  "hard_rules": ["do not drift"],
  "forbidden_drift": ["no parallel stack"],
  "validation_gates": ["pytest -q"],
  "done_criteria": ["works"],
  "handoff_requirements": ["return changed files"],
  "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": true},
  "packet_version": 1
}
""".strip(),
        encoding="utf-8",
    )
    dispatch_runtime_task(
        codex_team_project_root,
        session_id="result-session",
        request_id="req-result",
        target_worker="worker-1",
        packet_path=str(packet_path),
        delegation_metadata={"structured_results_expected": True},
    )

    result = WorkerTaskResult(
        task_id="T001",
        status="success",
        changed_files=["src/app.py"],
        validation_results=[ValidationResult(command="pytest -q", status="passed", output="1 passed")],
        summary="done",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
        ),
    )

    record = submit_runtime_result(
        codex_team_project_root,
        session_id="result-session",
        request_id="req-result",
        result=result,
    )

    assert record.status == "completed"
    stored_dispatch = json.loads(dispatch_record_path(codex_team_project_root, "req-result").read_text(encoding="utf-8"))
    stored_result = json.loads(result_record_path(codex_team_project_root, "req-result").read_text(encoding="utf-8"))
    assert stored_dispatch["status"] == "completed"
    assert stored_result == worker_task_result_payload(result)


def test_submit_runtime_result_normalizes_done_with_concerns_payload(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    bootstrap_runtime_session(codex_team_project_root, "norm-session")
    packet_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets" / "req-norm.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        """
{
  "feature_id": "001-feature",
  "task_id": "T201",
  "story_id": "US1",
  "objective": "Implement thing",
  "scope": {"write_scope": ["src/app.py"], "read_scope": ["src/contracts.py"]},
  "required_references": [{"path": "src/contracts.py", "reason": "preserve contract"}],
  "hard_rules": ["do not drift"],
  "forbidden_drift": ["no parallel stack"],
  "validation_gates": ["pytest -q"],
  "done_criteria": ["works"],
  "handoff_requirements": ["return changed files"],
  "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": true},
  "packet_version": 1
}
""".strip(),
        encoding="utf-8",
    )
    dispatch_runtime_task(
        codex_team_project_root,
        session_id="norm-session",
        request_id="req-norm",
        target_worker="worker-2",
        packet_path=str(packet_path),
        delegation_metadata={"structured_results_expected": True},
    )

    record = submit_runtime_result(
        codex_team_project_root,
        session_id="norm-session",
        request_id="req-norm",
        result={
            "taskId": "T201",
            "status": "DONE_WITH_CONCERNS",
            "files_changed": ["src/app.py"],
            "message": "done with concerns",
            "issues": ["follow-up cleanup remains"],
            "validationResults": [
                {"command": "pytest -q", "status": "passed", "output": "1 passed"}
            ],
            "ruleAcknowledgement": {
                "required_references_read": True,
                "forbidden_drift_respected": True,
            },
        },
    )

    assert record.status == "completed"
