import json
from pathlib import Path

import pytest

from specify_cli.codex_team.runtime_bridge import bootstrap_runtime_session, dispatch_runtime_task


def _seed_dispatch(project_root: Path, *, request_id: str = "req-template") -> None:
    bootstrap_runtime_session(project_root, "default")
    packet_path = project_root / ".specify" / "codex-team" / "state" / "packets" / f"{request_id}.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(
        json.dumps(
            {
                "feature_id": "001-feature",
                "task_id": "T701",
                "story_id": "US1",
                "objective": "Implement T701",
                "scope": {"write_scope": ["src/t701.py"], "read_scope": ["src/contracts.py"]},
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
        project_root,
        session_id="default",
        request_id=request_id,
        target_worker="worker-1",
        packet_path=str(packet_path),
    )


def test_build_request_result_template_uses_dispatched_packet(codex_team_project_root: Path):
    from specify_cli.codex_team.result_template import build_request_result_template

    _seed_dispatch(codex_team_project_root)

    template = build_request_result_template(codex_team_project_root, "req-template")

    assert template["task_id"] == "T701"
    assert template["changed_files"] == ["src/t701.py"]
    assert template["validation_results"][0]["command"] == "pytest -q"


def test_normalize_result_submission_rejects_bom_prefixed_payload(codex_team_project_root: Path):
    from specify_cli.codex_team.result_template import normalize_result_submission

    _seed_dispatch(codex_team_project_root, request_id="req-bom")

    with pytest.raises(ValueError, match="UTF-8 BOM"):
        normalize_result_submission(
            codex_team_project_root,
            "req-bom",
            "\ufeff{}",
        )


def test_normalize_result_submission_requires_task_id_and_status(codex_team_project_root: Path):
    from specify_cli.codex_team.result_template import normalize_result_submission

    _seed_dispatch(codex_team_project_root, request_id="req-missing")

    with pytest.raises(ValueError, match="missing required fields"):
        normalize_result_submission(
            codex_team_project_root,
            "req-missing",
            json.dumps({"summary": "not enough"}),
        )
