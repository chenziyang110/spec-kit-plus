"""Minimal live acceptance probe for the Codex team runtime."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from specify_cli.execution.result_schema import RuleAcknowledgement, ValidationResult, WorkerTaskResult
from specify_cli.execution import worker_task_result_payload
from specify_cli.orchestration.state_store import write_json

from .agent_teams_executor import run_manifest
from .doctor import codex_team_doctor
from .manifests import RuntimeSession, runtime_state_payload
from .runtime_bridge import RuntimeEnvironmentError
from .state_paths import (
    dispatch_record_path,
    executor_record_root,
    result_record_path,
    runtime_session_path,
)
from .runtime_bridge import codex_team_runtime_status, dispatch_runtime_task


def _probe_packet(task_id: str) -> dict[str, Any]:
    return {
        "feature_id": "live-probe",
        "task_id": task_id,
        "story_id": "PROBE",
        "objective": "Validate Codex team delegated executor round-trip",
        "scope": {"write_scope": ["docs/live-probe.txt"], "read_scope": ["docs/live-probe.txt"]},
        "required_references": [{"path": "docs/live-probe.txt", "reason": "probe-only synthetic boundary"}],
        "hard_rules": ["do not drift"],
        "forbidden_drift": ["do not skip structured worker result handoff"],
        "validation_gates": ["probe-pass"],
        "done_criteria": ["probe completed"],
        "handoff_requirements": ["return changed files"],
        "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": True},
        "packet_version": 1,
    }


def _probe_result_payload(task_id: str) -> dict[str, Any]:
    result = WorkerTaskResult(
        task_id=task_id,
        status="success",
        changed_files=["docs/live-probe.txt"],
        validation_results=[ValidationResult(command="probe-pass", status="passed", output="probe-pass")],
        summary="live probe completed",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
        ),
    )
    return worker_task_result_payload(result)


def codex_team_live_probe(
    project_root: Path,
    *,
    integration_key: str = "codex",
    session_id: str = "default",
) -> dict[str, Any]:
    """Run a minimal executor probe and return the resulting diagnostics payload."""

    status = codex_team_runtime_status(
        project_root,
        integration_key=integration_key,
        session_id=session_id,
    )
    if not status["executor_available"]:
        raise RuntimeEnvironmentError(str(status["executor_reason"]))

    runtime_cli_path = str(status.get("executor_runtime_cli_path", "")).strip()
    if not runtime_cli_path:
        raise RuntimeEnvironmentError("live probe requires a runtime_cli_path-backed executor")

    probe_id = uuid.uuid4().hex[:8]
    probe_session_id = f"probe-{probe_id}"
    request_id = f"{probe_session_id}-live-probe"
    task_id = "LIVE-PROBE"

    session = RuntimeSession(
        session_id=probe_session_id,
        status="ready",
        environment_check="pass",
    )
    write_json(runtime_session_path(project_root, probe_session_id), runtime_state_payload(session)["session"])

    packet_path = project_root / ".specify" / "codex-team" / "state" / "packets" / f"{request_id}.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(_probe_packet(task_id), ensure_ascii=False, indent=2), encoding="utf-8")

    dispatch_runtime_task(
        project_root,
        session_id=probe_session_id,
        request_id=request_id,
        target_worker="live-probe-worker",
        packet_path=str(packet_path),
        packet_summary={"task_id": task_id, "objective": "Codex team live probe", "write_scope": ["docs/live-probe.txt"]},
        delegation_metadata={"structured_results_expected": True, "executor_mode": status["executor_mode"]},
        result_path=str(result_record_path(project_root, request_id)),
    )

    manifest_path = executor_record_root(project_root) / f"{probe_session_id}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "runtime_cli_path": runtime_cli_path,
                "state_root": str(project_root / ".specify" / "codex-team" / "state" / "agent-teams" / probe_session_id),
                "team_name": f"ct-probe-{probe_id}",
                "worker_count": 1,
                "cwd": str(project_root),
                "session_id": probe_session_id,
                "tasks": [
                    {
                        "task_id": task_id,
                        "request_id": request_id,
                        "subject": task_id,
                        "description": (
                            "Live probe task\n"
                            "BEGIN_WORKER_TASK_RESULT_JSON\n"
                            f"{json.dumps(_probe_result_payload(task_id), ensure_ascii=False, indent=2)}\n"
                            "END_WORKER_TASK_RESULT_JSON\n"
                        ),
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    exit_code = run_manifest(project_root, manifest_path)
    dispatch_payload = _read_json(dispatch_record_path(project_root, request_id)) or {}
    result_payload = _read_json(result_record_path(project_root, request_id))
    report = codex_team_doctor(project_root, session_id=probe_session_id, integration_key=integration_key)

    ok = exit_code == 0 and dispatch_payload.get("status") == "completed" and result_payload is not None
    return {
        "ok": ok,
        "probe_id": probe_id,
        "session_id": probe_session_id,
        "request_id": request_id,
        "runtime_cli_path": runtime_cli_path,
        "manifest_path": str(manifest_path),
        "transcript_path": str(manifest_path.with_suffix(".runtime.json")),
        "exit_code": exit_code,
        "dispatch": dispatch_payload,
        "result": result_payload,
        "doctor": report,
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
