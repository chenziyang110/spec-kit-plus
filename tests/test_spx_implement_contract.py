import json
from pathlib import Path

from specify_cli.execution.ui_validation import validate_accepted_task_lifecycle


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_spx_implement_owns_durable_state_and_hands_off_cross_phase_work() -> None:
    skill = _read("templates/advanced-skills/spx-implement/SKILL.md").lower()
    execution = _read(
        "templates/advanced-skills/spx-implement/references/execution-contract.md"
    ).lower()
    combined = "\n".join((skill, execution))

    assert "workflow-state.md" in combined
    assert "implement-tracker.md" in combined
    assert "leader" in combined and "task lifecycle" in combined
    assert "task-index" in combined and "source_revision" in combined
    assert "spx-analyze" in combined and "handoff" in combined and "stop" in combined
    assert "do not run" in combined and "inline" in combined
    for route in ("spx-debug", "spx-design", "spx-implement-teams", "spx-integrate"):
        assert route in combined


def test_spx_implement_defines_actionable_external_verification_blockers() -> None:
    execution = _read(
        "templates/advanced-skills/spx-implement/references/execution-contract.md"
    ).lower()

    assert ".specify/templates/task-lifecycle-schema.json#/$defs/blocker" in execution
    assert "mandatory_for_completion" in execution
    assert "external-evidence-checkpoint" in execution
    assert "unchecked" in execution
    assert "must not" in execution and "resolved" in execution


def test_task_lifecycle_points_to_structured_blocker_schema() -> None:
    lifecycle = json.loads(_read("templates/task-lifecycle-template.json"))
    schema = json.loads(_read("templates/task-lifecycle-schema.json"))

    assert (
        lifecycle["blocker_schema_ref"]
        == ".specify/templates/task-lifecycle-schema.json#/$defs/blocker"
    )
    blocker = schema["$defs"]["blocker"]
    assert set(blocker["required"]) >= {
        "classification",
        "owner",
        "evidence",
        "exact_next_action",
        "approval_question",
        "unblock_criteria",
        "implementation_can_continue",
        "completion_impact",
    }
    assert "external-system" in blocker["properties"]["owner"]["enum"]
    assert (
        "mandatory_for_completion"
        in blocker["properties"]["completion_impact"]["enum"]
    )


def test_accepted_task_lifecycle_cannot_retain_open_blockers() -> None:
    errors = validate_accepted_task_lifecycle(
        {
            "task_id": "T001",
            "status": "accepted",
            "changed_paths": [".gitlab-ci.yml"],
            "validation": [{"command": "pipeline", "status": "passed"}],
            "blockers": [
                {
                    "classification": "external",
                    "owner": "external-system",
                    "evidence": "pipeline has not run",
                    "exact_next_action": "run pipeline",
                    "approval_question": None,
                    "unblock_criteria": "pipeline succeeds",
                    "implementation_can_continue": True,
                    "completion_impact": "mandatory_for_completion",
                }
            ],
        },
        "implementation-review/tasks/T001.json",
        "T001",
    )

    assert any("unresolved blockers" in error for error in errors)


def test_classic_implement_exposes_same_protected_ci_checkpoint_contract() -> None:
    classic = "\n".join(
        (
            _read("templates/command-references/implement/safe-repair-loop.md"),
            _read("templates/command-references/implement/branch-review-and-closeout.md"),
        )
    ).lower()

    assert "external-evidence-checkpoint" in classic
    assert "mandatory_for_completion" in classic
    assert "task lifecycle" in classic
    assert "does not" in classic and "resolved" in classic
