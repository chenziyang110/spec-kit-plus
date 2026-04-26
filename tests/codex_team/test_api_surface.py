import json
from pathlib import Path

import pytest

from specify_cli.codex_team.api_surface import TeamApiError, run_team_api_operation
from specify_cli.codex_team.runtime_bridge import bootstrap_runtime_session, dispatch_runtime_task


def _seed_codex_project(project_root: Path) -> None:
    spec_root = project_root / ".specify"
    spec_root.mkdir(parents=True, exist_ok=True)
    (spec_root / "integration.json").write_text(
        json.dumps({"integration": "codex"}),
        encoding="utf-8",
    )
    (spec_root / "codex-team").mkdir(parents=True, exist_ok=True)


def _seed_runtime_dispatch(project_root: Path, *, request_id: str = "req-template") -> None:
    _seed_codex_project(project_root)
    bootstrap_runtime_session(project_root, "default")
    packet_path = project_root / ".specify" / "codex-team" / "state" / "packets" / f"{request_id}.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        json.dumps(
            {
                "feature_id": "001-feature",
                "task_id": "T880",
                "story_id": "US1",
                "objective": "Implement T880",
                "scope": {"write_scope": ["src/t880.py"], "read_scope": ["src/contracts.py"]},
                "context_bundle": [
                    {
                        "path": "PROJECT-HANDBOOK.md",
                        "kind": "handbook",
                        "purpose": "root navigation artifact",
                        "required_for": ["workflow_boundary"],
                        "read_order": 1,
                        "must_read": True,
                        "selection_reason": "root navigation artifact",
                    }
                ],
                "required_references": [{"path": "src/contracts.py", "reason": "preserve contract"}],
                "hard_rules": ["do not drift"],
                "forbidden_drift": ["no parallel stack"],
                "validation_gates": ["pytest -q"],
                "done_criteria": ["works"],
                "handoff_requirements": ["return changed files"],
                "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": True},
                "packet_version": 2,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    dispatch_runtime_task(
        project_root,
        session_id="default",
        request_id=request_id,
        target_worker="worker-1",
        packet_path=str(packet_path),
    )


def test_run_team_api_operation_returns_status_envelope(codex_team_project_root: Path) -> None:
    _seed_codex_project(codex_team_project_root)

    envelope = run_team_api_operation(
        codex_team_project_root,
        "status",
        session_id="default",
    )

    assert envelope["operation"] == "status"
    assert envelope["status"] == "ok"
    assert "payload" in envelope
    assert "runtime_state_summary" in envelope["payload"]


def test_run_team_api_operation_supports_result_template(codex_team_project_root: Path) -> None:
    _seed_runtime_dispatch(codex_team_project_root)

    envelope = run_team_api_operation(
        codex_team_project_root,
        "result-template",
        request_id="req-template",
        session_id="default",
    )

    assert envelope["operation"] == "result-template"
    assert envelope["status"] == "ok"
    assert envelope["payload"]["task_id"] == "T880"
    assert envelope["payload"]["status"] == "pending"
    assert envelope["payload"]["rule_acknowledgement"]["context_bundle_read"] is False


def test_run_team_api_operation_rejects_non_codex_projects(tmp_path: Path) -> None:
    project = tmp_path / "non-codex"
    project.mkdir()
    spec_root = project / ".specify"
    spec_root.mkdir()
    (spec_root / "integration.json").write_text(
        json.dumps({"integration": "claude"}),
        encoding="utf-8",
    )

    with pytest.raises(TeamApiError, match="Codex integration projects"):
        run_team_api_operation(project, "status", session_id="default")
