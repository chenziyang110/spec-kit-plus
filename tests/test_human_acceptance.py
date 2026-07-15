from __future__ import annotations

import json
import subprocess
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.human_acceptance import (
    acceptance_closeout_blockers,
    new_human_acceptance_state,
    prepare_human_acceptance,
    validate_human_acceptance,
)


ROOT = Path(__file__).resolve().parents[1]


def _feature(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / ".specify" / "features" / "001-demo"
    feature.mkdir(parents=True)
    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nDemo feature complete.\n", encoding="utf-8"
    )
    return project, feature


def _accepted_state(state_path: Path) -> dict[str, object]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["status"] = "accepted"
    state["orientation"] = {
        "outcome": "The user can complete the demo flow.",
        "why_it_matters": "The primary task no longer needs a workaround.",
        "user_visible_changes": ["A new Demo action is available."],
        "not_in_scope": ["Administrative reporting is unchanged."],
        "prerequisites": ["Open the demo workspace."],
        "start_here": "Open the application and select Demo.",
    }
    state["scenarios"] = [
        {
            "id": "HA-001",
            "title": "Complete the demo flow",
            "user_value": "The user reaches the expected result.",
            "required": True,
            "start_state": "The application is open on the home screen.",
            "steps": [
                {
                    "id": "HA-001-S01",
                    "action": "Select Demo.",
                    "expected_result": "The Demo screen opens.",
                    "if_failed": "Return the visible error or a screenshot.",
                    "response_prompt": "Reply `seen`; otherwise send the visible error.",
                    "result": "pass",
                    "observed_result": "The Demo screen opened.",
                    "evidence": ["human: seen"],
                }
            ],
            "verdict": "pass",
            "notes": None,
        }
    ]
    state["cursor"] = {"scenario_id": None, "step_id": None}
    state["overall"] = {
        "verdict": "pass",
        "summary": "The human completed the required demo scenario.",
        "next_command": "sp-integrate or spx-integrate",
    }
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return state


def test_template_matches_runtime_empty_state() -> None:
    template = json.loads(
        (ROOT / "templates" / "human-acceptance-state-template.json").read_text(
            encoding="utf-8"
        )
    )

    assert template == new_human_acceptance_state()


def test_human_acceptance_schema_is_valid_and_accepts_the_draft_template() -> None:
    schema = json.loads(
        (ROOT / "templates" / "human-acceptance-state-schema.json").read_text(
            encoding="utf-8"
        )
    )
    template = new_human_acceptance_state()

    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(template)) == []


def test_advanced_acceptance_finding_routes_validate_in_schema_and_runtime(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    state["findings"] = [
        {
            "id": "HAF-001",
            "scenario_id": "HA-001",
            "step_id": "HA-001-S01",
            "classification": "product-defect",
            "route": "spx-debug",
            "expected": "The Demo screen opens.",
            "observed": "The repaired Demo screen opens.",
            "evidence": ["human: verified repaired behavior"],
            "status": "resolved",
        }
    ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    schema = json.loads(
        (ROOT / "templates" / "human-acceptance-state-schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(state)
    assert (
        validate_human_acceptance(project, feature, require_accepted=True)["valid"]
        is True
    )


def test_acceptance_paths_cannot_escape_the_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside-feature"
    outside.mkdir()
    (outside / "implementation-summary.md").write_text(
        "# Implementation Summary\n", encoding="utf-8"
    )

    for operation in (prepare_human_acceptance, validate_human_acceptance):
        try:
            operation(project, outside)
        except ValueError as exc:
            assert "inside the current project" in str(exc)
        else:
            raise AssertionError("outside feature_dir was accepted")
    assert not (outside / "human-acceptance.json").exists()


def test_acceptance_closeout_blocker_is_schema_valid_and_guides_a_novice(
    tmp_path: Path,
) -> None:
    _, feature = _feature(tmp_path)
    blocker = acceptance_closeout_blockers(
        feature,
        acceptance_errors=["human acceptance closeout requires status=accepted"],
    )[0]
    schema = json.loads(
        (ROOT / "templates" / "workflow-blocker-schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(blocker)
    assert blocker["human_action_required"] is True
    assert len(blocker["human_action_guide"]["steps"]) == 4
    assert blocker["resume"]["argv"][:3] == ["specify", "accept", "closeout"]


def test_prepare_creates_fingerprinted_state_and_marks_changed_summary_stale(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)

    prepared = prepare_human_acceptance(project, feature)

    assert prepared["status"] == "draft"
    state_path = feature / "human-acceptance.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["source"]["prepared_from_sha256"]
    assert state["source"]["prepared_from_sha256"] == state["source"]["current_sha256"]

    (feature / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nThe implementation changed.\n", encoding="utf-8"
    )
    stale = prepare_human_acceptance(project, feature)
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert stale["status"] == "stale"
    assert state["status"] == "stale"
    assert state["source"]["prepared_from_sha256"] != state["source"]["current_sha256"]


def test_prepare_marks_source_change_after_closeout_stale(tmp_path: Path) -> None:
    project, feature = _feature(tmp_path)
    source = project / "src" / "demo.txt"
    source.parent.mkdir()
    source.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "acceptance@example.test"],
        cwd=project,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Acceptance Test"],
        cwd=project,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    prepare_human_acceptance(project, feature)

    source.write_text("after\n", encoding="utf-8")
    stale = prepare_human_acceptance(project, feature)

    assert stale["status"] == "stale"
    state = json.loads((feature / "human-acceptance.json").read_text(encoding="utf-8"))
    assert state["source"]["prepared_from_sha256"] != state["source"]["current_sha256"]


def test_validate_requires_explicit_human_pass_for_every_required_scenario(
    tmp_path: Path,
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)

    accepted = validate_human_acceptance(project, feature, require_accepted=True)

    assert accepted["valid"] is True
    assert accepted["accepted"] is True

    state["scenarios"][0]["verdict"] = "pending"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    invalid = validate_human_acceptance(project, feature, require_accepted=True)

    assert invalid["valid"] is False
    assert (
        "accepted status requires every required scenario to pass" in invalid["errors"]
    )


def test_in_progress_state_requires_a_real_resume_cursor(tmp_path: Path) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    state_path = feature / "human-acceptance.json"
    state = _accepted_state(state_path)
    state["status"] = "in_progress"
    state["overall"]["verdict"] = "pending"
    state["scenarios"][0]["verdict"] = "pending"
    state["scenarios"][0]["steps"][0]["result"] = "pending"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    invalid = validate_human_acceptance(project, feature)

    assert invalid["valid"] is False
    assert any("cursor.scenario_id" in error for error in invalid["errors"])
    assert any("cursor.step_id" in error for error in invalid["errors"])


def test_accept_cli_closes_only_fresh_explicit_human_acceptance(
    monkeypatch, tmp_path: Path
) -> None:
    project, feature = _feature(tmp_path)
    prepare_human_acceptance(project, feature)
    _accepted_state(feature / "human-acceptance.json")
    (feature / "workflow-state.md").write_text(
        """# Workflow State: Demo

## Current Command

- active_command: sp-accept
- status: completed

## Phase Mode

- phase_mode: acceptance-only
- summary: Human accepted every required scenario.

## Allowed Artifact Writes

- human-acceptance.json
- workflow-state.md

## Forbidden Actions

- edit production source code
- edit tests

## Authoritative Files

- implementation-summary.md
- human-acceptance.json

## Next Command

- `/sp.integrate`
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(project)

    result = CliRunner().invoke(
        app,
        [
            "accept",
            "closeout",
            "--feature-dir",
            str(feature),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "accepted"
    assert payload["human_acceptance"]["accepted"] is True
    assert payload["hook_result"]["status"] == "ok"
