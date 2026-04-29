import json
from pathlib import Path

import pytest

from specify_cli.codex_team.runtime_bridge import (
    RuntimeEnvironmentError,
    ensure_codex_team_executor_available,
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
from specify_cli.codex_team import task_ops


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
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge._winget_links_binary", lambda name: None)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge._winget_package_binary", lambda package, binaries: None)

    with pytest.raises(RuntimeEnvironmentError) as excinfo:
        ensure_tmux_available()

    message = str(excinfo.value)
    assert "psmux" in message
    assert "winget install psmux" in message


def test_runtime_status_reports_native_windows_toolchain_requirements(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: {
            "psmux": r"C:\psmux.exe",
            "git": r"C:\git.exe",
        }.get(name),
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge._winget_links_binary", lambda name: None)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge._winget_package_binary", lambda package, binaries: None)

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["runtime_backend"] == "psmux"
    assert status["native_windows"] is True
    assert status["teams_ready"] is False
    assert status["executor_available"] is False
    assert status["native_toolchain_ready"] is False
    assert status["native_toolchain_missing"] == ["codex", "node", "npm", "cargo"]


def test_runtime_bridge_accepts_windows_runtime_exe(tmp_path: Path):
    from specify_cli.codex_team.runtime_bridge import resolve_agent_teams_runtime_binary

    engine_root = tmp_path / "engine"
    release_dir = engine_root / "target" / "release"
    release_dir.mkdir(parents=True)
    runtime_exe = release_dir / "specify-runtime.exe"
    runtime_exe.write_text("", encoding="utf-8")

    resolved = resolve_agent_teams_runtime_binary(engine_root)

    assert resolved == runtime_exe


def test_runtime_status_reports_codex_availability(monkeypatch, codex_team_project_root: Path):
    runtime_cli = codex_team_project_root / "fake-runtime-cli.js"
    runtime_cli.write_text("// fake runtime cli\n", encoding="utf-8")
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_RUNTIME_CLI", str(runtime_cli))
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\tool.exe" if name in {"tmux", "node"} else None,
    )

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["available"] is True
    assert status["runtime_backend"] == "tmux"
    assert status["runtime_backend_available"] is True
    assert status["runtime_state"] is None
    assert status["runtime_state_source"] == "none"
    assert status["preview_runtime_state"]["session"]["environment_check"] == "pass"
    assert status["preview_runtime_state"]["session"]["session_id"] == "preview"
    assert status["executor_available"] is True
    assert status["executor_mode"] == "agent-teams-runtime"


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
    assert status["preview_runtime_state"]["session"]["environment_check"] == "pass"


def test_runtime_status_reports_non_codex_as_unavailable(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    status = codex_team_runtime_status(codex_team_project_root, integration_key="claude")

    assert status["available"] is False
    assert status["preview_runtime_state"]["session"]["status"] == "created"


def test_runtime_status_surfaces_extension_and_git_prerequisites(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge._detect_agent_teams_runtime_cli", lambda project_root: None)
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

    assert status["git_repo_detected"] is False
    assert status["git_head_available"] is False
    assert status["leader_workspace_clean"] is False
    assert status["worktree_ready"] is False
    assert status["teams_ready"] is False
    assert any("bundled teams runtime assets are missing" in step.lower() for step in status["next_steps"])
    assert any("initial commit" in step.lower() for step in status["next_steps"])


def test_runtime_status_surfaces_live_session_separately_from_preview(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    bootstrap_runtime_session(codex_team_project_root, "default")

    status = codex_team_runtime_status(codex_team_project_root, integration_key="codex")

    assert status["runtime_state_source"] == "live"
    assert status["runtime_state"]["session"]["session_id"] == "default"
    assert status["preview_runtime_state"]["session"]["session_id"] == "preview"


def test_ensure_codex_team_executor_available_raises_without_executor(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge._detect_agent_teams_runtime_cli", lambda project_root: None)
    with pytest.raises(RuntimeEnvironmentError, match="No packet executor is configured"):
        ensure_codex_team_executor_available(codex_team_project_root)


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


def test_submit_runtime_result_updates_task_record_and_clears_claim(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    created = task_ops.create_task(codex_team_project_root, task_id="T301", summary="Implement thing")
    token = task_ops.claim_task(
        codex_team_project_root,
        task_id="T301",
        worker_id="worker-301",
        expected_version=created.version,
    )
    in_progress = task_ops.transition_task_status(
        codex_team_project_root,
        task_id="T301",
        new_status="in_progress",
        owner="worker-301",
        expected_version=created.version + 1,
        claim_token=token,
    )

    bootstrap_runtime_session(codex_team_project_root, "task-result-session")
    packet_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets" / "req-task-result.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        """
{
  "feature_id": "001-feature",
  "task_id": "T301",
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
        session_id="task-result-session",
        request_id="req-task-result",
        target_worker="worker-301",
        packet_path=str(packet_path),
        delegation_metadata={"structured_results_expected": True},
    )

    record = submit_runtime_result(
        codex_team_project_root,
        session_id="task-result-session",
        request_id="req-task-result",
        result={
            "taskId": "T301",
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
    task_record = task_ops.get_task(codex_team_project_root, "T301")
    assert task_record.status == "completed"
    assert task_record.metadata.get("current_claim") is None
    assert task_record.metadata["result_request_id"] == "req-task-result"
    assert task_record.metadata["reported_status"] == "done_with_concerns"
    assert task_record.metadata["concerns_present"] is True
    assert task_record.version > in_progress.version


def test_submit_runtime_result_rejects_repeat_submission(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    bootstrap_runtime_session(codex_team_project_root, "dup-session")
    packet_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets" / "req-dup.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        """
{
  "feature_id": "001-feature",
  "task_id": "T401",
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
        session_id="dup-session",
        request_id="req-dup",
        target_worker="worker-dup",
        packet_path=str(packet_path),
        delegation_metadata={"structured_results_expected": True},
    )

    first = WorkerTaskResult(
        task_id="T401",
        status="success",
        changed_files=["src/app.py"],
        validation_results=[ValidationResult(command="pytest -q", status="passed", output="1 passed")],
        summary="done",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
        ),
    )
    submit_runtime_result(
        codex_team_project_root,
        session_id="dup-session",
        request_id="req-dup",
        result=first,
    )

    with pytest.raises(RuntimeEnvironmentError, match="already has a terminal result"):
        submit_runtime_result(
            codex_team_project_root,
            session_id="dup-session",
            request_id="req-dup",
            result=first,
        )
