from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from types import ModuleType

import pytest

from specify_cli.workflow_runtime import (
    complete_workflow_stage,
    enter_workflow,
    show_workflow,
    transition_workflow,
)


def _review_runtime() -> ModuleType:
    return importlib.import_module("specify_cli.review_runtime")


def _feature_at_review(tmp_path: Path) -> tuple[Path, Path, int]:
    project_root = tmp_path / "project"
    feature_dir = project_root / ".specify" / "features" / "001-system-review"
    feature_dir.mkdir(parents=True)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for target in ("plan", "tasks", "implement", "review"):
        completed = complete_workflow_stage(feature_dir, expected_revision=revision)
        transitioned = transition_workflow(
            feature_dir,
            target_stage=target,
            expected_revision=completed["data"]["revision"],
        )
        revision = transitioned["data"]["revision"]
    return project_root, feature_dir, revision


def _write_implementation_handoff(feature_dir: Path, revision: int) -> Path:
    handoff_path = feature_dir / "implementation-handoff.json"
    handoff_path.write_text(
        json.dumps(
            {
                "version": 1,
                "source_revision": revision,
                "implementation_fingerprint": "a" * 64,
                "official_entrypoints": [
                    {
                        "id": "web",
                        "command": "npm run dev",
                        "ready_signal": "GET /health returns 200",
                    }
                ],
                "system_review_scenarios": [
                    {
                        "id": "SR-START-001",
                        "kind": "startup",
                        "title": "Start the product from its official entrypoint",
                        "required": True,
                        "entrypoint_id": "web",
                        "preconditions": ["Dependencies are installed."],
                        "actions": ["Run npm run dev."],
                        "expected_results": ["GET /health returns 200."],
                        "required_evidence": ["runtime_diagnostics"],
                    },
                    {
                        "id": "SR-UI-001",
                        "kind": "interaction",
                        "title": "Complete the primary user journey",
                        "required": True,
                        "entrypoint_id": "web",
                        "preconditions": ["The product is ready."],
                        "actions": ["Open the home page.", "Select Demo."],
                        "expected_results": ["The Demo screen opens."],
                        "required_evidence": [
                            "structure_snapshot",
                            "visual_capture",
                            "runtime_diagnostics",
                        ],
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return handoff_path


def _prepare(tmp_path: Path) -> tuple[ModuleType, Path, Path, int, dict[str, object]]:
    runtime = _review_runtime()
    project_root, feature_dir, revision = _feature_at_review(tmp_path)
    _write_implementation_handoff(feature_dir, revision)
    prepared = runtime.prepare_review(
        project_root,
        feature_dir,
        expected_revision=revision,
    )
    return runtime, project_root, feature_dir, revision, prepared


def _write_scenario_evidence(feature_dir: Path, state: dict[str, object]) -> None:
    for scenario in state["scenarios"]:
        scenario["result"] = "pass"
        scenario["evidence"] = []
        for kind in scenario["required_evidence"]:
            relative_path = Path("review-evidence") / scenario["id"] / f"{kind}.json"
            evidence_path = feature_dir / relative_path
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text("{}\n", encoding="utf-8")
            scenario["evidence"].append(
                {
                    "kind": kind,
                    "path": relative_path.as_posix(),
                    "evidence_scope": "integrated",
                }
            )


def test_prepare_review_compiles_handoff_into_resumable_review_state(
    tmp_path: Path,
) -> None:
    runtime, _project_root, feature_dir, revision, prepared = _prepare(tmp_path)

    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    handoff_bytes = (feature_dir / "implementation-handoff.json").read_bytes()

    assert prepared["status"] == "ok"
    assert prepared["data"]["status"] == "reviewing"
    assert state_path == feature_dir / "review-state.json"
    assert state["status"] == "reviewing"
    assert state["source"] == {
        "workflow_revision": revision,
        "implementation_fingerprint": "a" * 64,
        "implementation_handoff_sha256": hashlib.sha256(handoff_bytes).hexdigest(),
    }
    assert [scenario["id"] for scenario in state["scenarios"]] == [
        "SR-START-001",
        "SR-UI-001",
    ]
    assert all(scenario["result"] == "pending" for scenario in state["scenarios"])
    assert state["findings"] == []
    assert state["cursor"]["scenario_id"] == "SR-START-001"


def test_validate_review_rejects_failed_scenario_and_open_finding(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "repairing"
    state["scenarios"][0]["result"] = "fail"
    state["findings"] = [
        {
            "id": "SRF-001",
            "scenario_id": "SR-START-001",
            "classification": "startup",
            "summary": "The official entrypoint exits before becoming ready.",
            "status": "open",
        }
    ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert validation["fresh"] is True
    assert any("SR-START-001" in error for error in validation["errors"])
    assert any("SRF-001" in error for error in validation["errors"])


def test_validate_review_marks_changed_implementation_handoff_stale(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    handoff_path = feature_dir / "implementation-handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["implementation_fingerprint"] = "b" * 64
    handoff_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert validation["fresh"] is False
    assert any("stale" in error.lower() for error in validation["errors"])


def test_validate_review_rejects_declared_evidence_without_a_real_file(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, _revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    for scenario in state["scenarios"]:
        scenario["result"] = "pass"
        scenario["evidence"] = [
            {
                "kind": kind,
                "path": f"review-evidence/{scenario['id']}/{kind}.json",
                "evidence_scope": "integrated",
            }
            for kind in scenario["required_evidence"]
        ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)

    assert validation["valid"] is False
    assert any("does not exist" in error for error in validation["errors"])


def test_closeout_review_requires_approved_fresh_evidence_and_does_not_advance_workflow(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    state["status"] = "approved"
    state["findings"] = []
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    closed = runtime.closeout_review(
        project_root,
        feature_dir,
        expected_revision=revision,
    )

    assert closed["status"] == "ok"
    assert closed["data"]["status"] == "approved"
    assert closed["data"]["fresh"] is True
    assert closed["next_argv"] == [
        "specify",
        "workflow",
        "complete-stage",
        "--feature-dir",
        str(feature_dir.resolve()),
        "--expected-revision",
        str(revision),
        "--format",
        "json",
    ]
    workflow = show_workflow(feature_dir)["data"]
    assert workflow["stage"] == "review"
    assert workflow["status"] == "active"
    assert workflow["revision"] == revision


def test_closeout_review_preserves_state_when_review_is_not_approved(
    tmp_path: Path,
) -> None:
    runtime, project_root, feature_dir, revision, _prepared = _prepare(tmp_path)
    state_path = runtime.review_state_path(feature_dir)
    before = state_path.read_bytes()

    with pytest.raises(runtime.ReviewRuntimeError, match="approved"):
        runtime.closeout_review(
            project_root,
            feature_dir,
            expected_revision=revision,
        )

    assert state_path.read_bytes() == before
    assert show_workflow(feature_dir)["data"]["stage"] == "review"


def test_approved_review_becomes_stale_when_live_source_changes(tmp_path: Path) -> None:
    runtime = _review_runtime()
    project_root, feature_dir, revision = _feature_at_review(tmp_path)
    source_path = project_root / "src" / "app.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("print('ready')\n", encoding="utf-8")
    handoff_path = _write_implementation_handoff(feature_dir, revision)
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["fingerprint_algorithm"] = "git-working-tree-v1"
    handoff["implementation_fingerprint"] = runtime.implementation_snapshot_sha256(
        project_root, feature_dir
    )
    handoff_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
    runtime.prepare_review(project_root, feature_dir, expected_revision=revision)

    state_path = runtime.review_state_path(feature_dir)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    _write_scenario_evidence(feature_dir, state)
    state["status"] = "approved"
    state["final"]["reviewed_snapshot_sha256"] = runtime.implementation_snapshot_sha256(
        project_root, feature_dir
    )
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    assert runtime.validate_review(project_root, feature_dir)["valid"] is True

    source_path.write_text("print('changed after review')\n", encoding="utf-8")

    validation = runtime.validate_review(project_root, feature_dir)
    assert validation["valid"] is False
    assert validation["fresh"] is False
    assert any("reviewed snapshot" in error for error in validation["errors"])
