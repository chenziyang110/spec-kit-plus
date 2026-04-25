import json
from pathlib import Path

from specify_cli.codex_team.runtime_bridge import bootstrap_runtime_session, dispatch_runtime_task
from specify_cli.codex_team.state_paths import batch_record_path, task_record_path


def test_codex_team_doctor_surfaces_latest_runtime_transcript_and_failed_dispatches(
    monkeypatch,
    codex_team_project_root: Path,
):
    from specify_cli.codex_team.doctor import codex_team_doctor

    runtime_cli = codex_team_project_root / "fake-runtime-cli.js"
    runtime_cli.write_text("// fake runtime cli\n", encoding="utf-8")
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_RUNTIME_CLI", str(runtime_cli))
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\tool.exe" if name in {"tmux", "node"} else None,
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})

    bootstrap_runtime_session(codex_team_project_root, "default")
    packet_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets" / "req-doctor.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        json.dumps(
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
                "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": True},
                "packet_version": 1,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    dispatch_runtime_task(
        codex_team_project_root,
        session_id="default",
        request_id="req-doctor",
        target_worker="worker-1",
        packet_path=str(packet_path),
        delegation_metadata={"structured_results_expected": True, "executor_mode": "agent-teams-runtime"},
    )

    executors_dir = codex_team_project_root / ".specify" / "codex-team" / "state" / "executors"
    executors_dir.mkdir(parents=True, exist_ok=True)
    state_root = codex_team_project_root / ".specify" / "codex-team" / "state" / "agent-teams" / "doctor-batch"
    team_root = state_root / "team" / "ct-doctor"
    team_root.mkdir(parents=True, exist_ok=True)
    (team_root / "phase.json").write_text(
        json.dumps(
            {
                "current_phase": "failed",
                "updated_at": "2026-04-26T00:00:00Z",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (team_root / "monitor-snapshot.json").write_text(
        json.dumps(
            {
                "taskStatusById": {"1": "pending"},
                "workerAliveByName": {"worker-1": False},
                "workerStateByName": {"worker-1": "unknown"},
                "workerTurnCountByName": {"worker-1": 0},
                "workerTaskIdByName": {"worker-1": ""},
                "mailboxNotifiedByMessageId": {},
                "completedEventTaskIds": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    transcript_path = executors_dir / "default-parallel-batch-1-1.runtime.json"
    transcript_path.write_text(
        json.dumps(
            {
                "runtime_command": ["node", "runtime-cli.js"],
                "runtime_payload": {
                    "teamName": "ct-doctor",
                    "workerCount": 1,
                    "agentTypes": ["gemini"],
                    "tasks": [{"subject": "T001", "description": "demo"}],
                    "cwd": str(codex_team_project_root),
                },
                "state_root": str(state_root),
                "returncode": 1,
                "stdout": '{"status":"failed"}',
                "stderr": "[runtime-cli] phase=failed pending=1 completed=0",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    dispatch_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "dispatch" / "req-doctor.json"
    dispatch_payload = json.loads(dispatch_path.read_text(encoding="utf-8"))
    dispatch_payload["status"] = "failed"
    dispatch_payload["reason"] = "structured worker result for T001 is missing"
    dispatch_path.write_text(json.dumps(dispatch_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report = codex_team_doctor(codex_team_project_root, session_id="default")

    assert report["status"]["executor_available"] is True
    assert "baseline_build" in report
    assert "native_build_shell" in report
    assert report["recent_batches"] == []
    assert report["transcript"]["path"] == str(transcript_path)
    assert report["transcript"]["returncode"] == 1
    assert report["transcript"]["state_probe"]["team_name"] == "ct-doctor"
    assert report["transcript"]["state_probe"]["phase"] == "failed"
    assert report["transcript"]["state_probe"]["worker_alive_breakdown"]["worker-1"] is False
    assert report["failed_dispatches"][0]["request_id"] == "req-doctor"
    assert "structured worker result" in report["failed_dispatches"][0]["reason"]


def test_codex_team_doctor_reports_lane_and_repo_verification_status(
    monkeypatch,
    codex_team_project_root: Path,
):
    from specify_cli.codex_team.doctor import codex_team_doctor

    runtime_cli = codex_team_project_root / "fake-runtime-cli.js"
    runtime_cli.write_text("// fake runtime cli\n", encoding="utf-8")
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_RUNTIME_CLI", str(runtime_cli))
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\tool.exe" if name in {"tmux", "node"} else None,
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})

    baseline_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "baseline-build.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(
            {
                "status": "blocked",
                "reason": "baseline compile debt",
                "checked_at": "2026-04-26T00:00:00Z",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    task_payload = {
        "task_id": "T900",
        "summary": "seed",
        "status": "completed",
        "owner": "worker-a",
        "version": 1,
        "schema_version": "1.0",
        "created_at": "2026-04-26T00:00:00Z",
        "updated_at": "2026-04-26T00:00:00Z",
        "metadata": {
            "concerns_present": True,
        },
    }
    task_record_path(codex_team_project_root, "T900").parent.mkdir(parents=True, exist_ok=True)
    task_record_path(codex_team_project_root, "T900").write_text(
        json.dumps(task_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    batch_payload = {
        "batch_id": "batch-1",
        "batch_name": "Batch 1",
        "session_id": "default",
        "feature_dir": "specs/001",
        "task_ids": ["T900"],
        "request_ids": ["req-1"],
        "join_point_name": "Join 1",
        "batch_classification": "strict",
        "safe_preparation": False,
        "review_required": False,
        "peer_review_lane_recommended": False,
        "review_reason": "low_risk_batch",
        "review_status": "not_required",
        "review_round": 0,
        "review_record_ids": [],
        "status": "completed",
        "schema_version": "1.0",
        "created_at": "2026-04-26T00:00:00Z",
        "updated_at": "2026-04-26T00:00:00Z",
    }
    batch_record_path(codex_team_project_root, "batch-1").parent.mkdir(parents=True, exist_ok=True)
    batch_record_path(codex_team_project_root, "batch-1").write_text(
        json.dumps(batch_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = codex_team_doctor(codex_team_project_root, session_id="default")

    assert report["recent_batches"][0]["lane_status"] == "completed_with_concerns"
    assert report["recent_batches"][0]["repo_verification_status"] == "blocked_by_baseline"
