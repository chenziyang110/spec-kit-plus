from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli import workflow_runtime


def _feature(tmp_path: Path) -> Path:
    feature = tmp_path / ".specify" / "features" / "001-runtime-adapter"
    feature.mkdir(parents=True)
    return feature


def _envelope(
    status: str = "ok",
    *,
    data: dict[str, Any] | None = None,
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "summary": "runtime result",
        "data": data or {},
        "items": [],
        "blockers": blockers or [],
        "show_argv": [],
        "next_argv": [],
    }


def _capture_runtime(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_run(args, *, cwd, check, install_if_missing):
        calls.append(
            {
                "args": list(args),
                "cwd": cwd,
                "check": check,
                "install_if_missing": install_if_missing,
            }
        )
        return payload or _envelope(
            data={"revision": 1, "stage": "specify", "status": "active"}
        )

    monkeypatch.setattr(workflow_runtime, "run_specify_runtime", fake_run)
    return calls


def test_path_helpers_expose_current_files_without_touching_them(
    tmp_path: Path,
) -> None:
    feature = _feature(tmp_path)

    assert workflow_runtime.workflow_runtime_path(feature) == feature / "workflow.json"
    assert workflow_runtime.workflow_state_path(feature) == feature / "workflow-state.md"
    assert not workflow_runtime.workflow_runtime_path(feature).exists()
    assert not workflow_runtime.workflow_state_path(feature).exists()


def test_adapter_rejects_nested_or_unconfined_feature_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls = _capture_runtime(monkeypatch)
    nested = _feature(tmp_path) / "nested"
    nested.mkdir()

    with pytest.raises(ValueError, match="one direct child"):
        workflow_runtime.show_workflow(nested)
    with pytest.raises(ValueError, match="one direct child"):
        workflow_runtime.show_workflow(tmp_path / "feature")

    assert calls == []


def test_show_is_a_read_only_unified_runtime_adapter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    feature = _feature(tmp_path)
    calls = _capture_runtime(monkeypatch)

    payload = workflow_runtime.show_workflow(feature)

    assert payload["data"]["stage"] == "specify"
    assert calls == [
        {
            "args": [
                "workflow",
                "show",
                "--feature-dir",
                str(feature),
                "--project-root",
                str(tmp_path),
                "--format",
                "json",
            ],
            "cwd": tmp_path,
            "check": False,
            "install_if_missing": True,
        }
    ]


def test_all_workflow_operations_map_to_the_frozen_go_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    feature = _feature(tmp_path)
    calls = _capture_runtime(monkeypatch)

    workflow_runtime.enter_workflow(
        feature,
        stage="specify",
        expected_revision=0,
        summary="entered",
    )
    workflow_runtime.next_workflow(feature)
    workflow_runtime.complete_workflow_stage(
        feature,
        expected_revision=1,
        summary="complete",
    )
    workflow_runtime.transition_workflow(
        feature,
        target_stage="plan",
        expected_revision=2,
        summary="advance",
    )
    workflow_runtime.reopen_workflow(
        feature,
        target_stage="specify",
        expected_revision=3,
        reason="contract drift",
        evidence=["spec changed"],
        invalidated_artifacts=["plan.md", "tasks.md"],
    )
    workflow_runtime.resolve_workflow_blocker(
        feature,
        expected_revision=4,
        resolution_evidence=["CI passed"],
        summary="resolved",
    )
    workflow_runtime.closeout_workflow(
        feature,
        expected_revision=5,
        summary="accepted",
    )

    commands = [call["args"] for call in calls]
    assert [command[:2] for command in commands] == [
        ["workflow", "enter"],
        ["workflow", "next"],
        ["workflow", "complete-stage"],
        ["workflow", "transition"],
        ["workflow", "reopen"],
        ["workflow", "resolve"],
        ["workflow", "closeout"],
    ]
    assert commands[0][:8] == [
        "workflow",
        "enter",
        "--feature-dir",
        str(feature),
        "--command",
        "specify",
        "--expected-revision",
        "0",
    ]
    assert commands[2][:8] == [
        "workflow",
        "complete-stage",
        "--feature-dir",
        str(feature),
        "--expected-revision",
        "1",
        "--summary",
        "complete",
    ]
    evidence_index = commands[4].index("--evidence")
    assert commands[4][evidence_index : evidence_index + 2] == [
        "--evidence",
        "spec changed",
    ]
    assert commands[4].count("--invalidated-artifacts") == 2
    resolution_index = commands[5].index("--resolution-evidence")
    assert commands[5][resolution_index : resolution_index + 2] == [
        "--resolution-evidence",
        "CI passed",
    ]
    assert all(command[-2:] == ["--format", "json"] for command in commands)


def test_block_serializes_structured_input_to_a_temporary_json_bridge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    feature = _feature(tmp_path)
    captured: dict[str, Any] = {}

    def fake_run(args, *, cwd, check, install_if_missing):
        input_path = Path(args[args.index("--input") + 1])
        captured["payload"] = json.loads(input_path.read_text(encoding="utf-8"))
        captured["args"] = list(args)
        return _envelope(
            "blocked",
            data={"revision": 2, "stage": "specify", "status": "blocked"},
            blockers=[{"code": "workflow-blocked"}],
        )

    monkeypatch.setattr(workflow_runtime, "run_specify_runtime", fake_run)

    result = workflow_runtime.block_workflow(
        feature,
        expected_revision=1,
        category="external-system",
        owner="maintainer",
        cause="protected CI is pending",
        evidence=["job 42 is pending"],
        attempted_recovery=[{"action": "checked CI", "result": "pending"}],
        affected_scope=["delivery"],
        exact_next_action="Wait for job 42.",
        unblock_criteria="Job 42 passes.",
    )

    assert result["status"] == "blocked"
    assert captured["payload"]["feature_dir"] == ".specify/features/001-runtime-adapter"
    assert captured["payload"]["expected_revision"] == 1
    assert captured["payload"]["cause"] == "protected CI is pending"
    assert captured["args"][:2] == ["workflow", "block"]
    assert captured["args"][captured["args"].index("--feature-dir") + 1] == str(
        feature
    )


def test_acceptance_repair_reopen_uses_the_runtime_owned_repair_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    feature = _feature(tmp_path)
    calls = _capture_runtime(monkeypatch)

    workflow_runtime.reopen_acceptance_workflow(
        feature,
        target_stage="review",
        repair_route="sp-review",
        finding_id="HAF-001",
        expected_revision=8,
        evidence=["scenario failed"],
    )

    args = calls[0]["args"]
    assert args[:2] == ["workflow", "reopen"]
    route_index = args.index("--repair-route")
    assert args[route_index : route_index + 2] == ["--repair-route", "sp-review"]
    finding_index = args.index("--finding-id")
    assert args[finding_index : finding_index + 2] == ["--finding-id", "HAF-001"]
    assert "--reason" not in args
    assert "--invalidated-artifacts" not in args


def test_persisted_blocked_show_is_returned_without_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    feature = _feature(tmp_path)
    blocked = _envelope(
        "blocked",
        data={"revision": 4, "stage": "implement", "status": "blocked"},
        blockers=[{"code": "workflow-blocked"}],
    )
    _capture_runtime(monkeypatch, blocked)

    assert workflow_runtime.show_workflow(feature) == blocked


@pytest.mark.parametrize(
    ("error_code", "exception_type"),
    (
        ("missing-workflow-state", workflow_runtime.MissingWorkflowState),
        ("invalid-workflow-runtime", workflow_runtime.WorkflowRuntimeError),
        ("revision-conflict", workflow_runtime.RevisionConflict),
        ("invalid-transition", workflow_runtime.InvalidTransition),
    ),
)
def test_runtime_failure_envelopes_become_typed_python_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_code: str,
    exception_type: type[workflow_runtime.WorkflowRuntimeError],
) -> None:
    feature = _feature(tmp_path)
    failed = _envelope(
        "blocked",
        data={"error_code": error_code},
        blockers=[{"code": error_code}],
    )
    _capture_runtime(monkeypatch, failed)

    with pytest.raises(exception_type) as captured:
        workflow_runtime.transition_workflow(
            feature,
            target_stage="plan",
            expected_revision=1,
        )

    assert captured.value.to_envelope() == failed
