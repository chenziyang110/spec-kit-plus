import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.command_catalog import command_catalog
from specify_cli.human_acceptance import prepare_human_acceptance
from specify_cli.workflow_runtime import (
    complete_workflow_stage,
    enter_workflow,
    transition_workflow,
)


runner = CliRunner()


def _invoke_in_project(project: Path, args: list[str]):
    previous = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(previous)


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "agent-api-project"
    (project / ".specify").mkdir(parents=True)
    return project


def _complete_then_transition(
    feature_dir: Path,
    *,
    target_stage: str,
    revision: int,
) -> dict[str, object]:
    completed = complete_workflow_stage(feature_dir, expected_revision=revision)
    return transition_workflow(
        feature_dir,
        target_stage=target_stage,
        expected_revision=completed["data"]["revision"],
    )


def _write_valid_spec_contract(feature_dir: Path) -> None:
    (feature_dir / "spec.md").write_text("# Specification\n", encoding="utf-8")
    payload = {
        "version": 1,
        "status": "planning-ready",
        "source_contract": None,
        "source_revision": None,
        "decision_digest_ref": None,
        "target_need": "Guarded workflow handoff",
        "scope": {"in": ["Guard the handoff"], "out": [], "deferred": []},
        "constraints": [],
        "acceptance_criteria": ["The next stage is entered exactly once"],
        "decisions": [],
        "semantic_delta": [],
        "capability_operations": [],
        "must_preserve_refs": [],
        "consequence_obligation_refs": [],
        "design_contract": {
            "experience_requirements": [],
            "design_source_refs": [],
            "design_system_requirements": [],
            "design_system_status": "not-applicable",
            "design_risk_level": "none",
            "fidelity_refs": [],
            "required_states": [],
            "validation_refs": [],
        },
        "context_capsule": {
            "boundary_ref": None,
            "evidence_refs": [],
            "selected_capabilities": [],
            "minimal_live_reads": [],
            "validation_routes": [],
            "stale_if": [],
        },
        "open_items": [],
        "artifact_refs": {
            "spec": "spec.md",
            "alignment": None,
            "context": None,
            "references": None,
        },
        "transition": {
            "version": 1,
            "status": "ready",
            "source_ref": "spec-contract.json",
            "semantic_delta": [],
            "required_refs": [],
            "blockers": [],
            "next_action": "/sp.plan",
            "recovery": None,
        },
    }
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    _write_rich_workflow_state(
        feature_dir,
        command="sp-specify",
        phase="planning-only",
        next_command="/sp.plan",
    )


def _write_rich_workflow_state(
    feature_dir: Path,
    *,
    command: str,
    phase: str,
    next_command: str,
) -> None:
    (feature_dir / "workflow-state.md").write_text(
        f"""# Workflow State

## Current Command

- active_command: `{command}`
- status: `completed`

## Phase Mode

- phase_mode: `{phase}`

## Stage State

- current_stage: `complete`
- current_domain: `none`
- next_action: `Continue through the deterministic phase runtime.`
- blocker_reason: `none`
- final_handoff_decision: `{next_command}`

## Allowed Artifact Writes

- workflow-owned evidence

## Forbidden Actions

- skip deterministic runtime stages

## Authoritative Files

- workflow-state.md

## Next Command

- `{next_command}`
""",
        encoding="utf-8",
    )


def test_agent_api_handshake_is_compact_and_machine_readable() -> None:
    result = runner.invoke(
        app,
        [
            "api",
            "handshake",
            "--require",
            "learning.start,workflow.enter,workflow.transition",
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["data"]["protocol_version"]
    assert payload["data"]["cli_version"]
    assert payload["data"]["missing_capabilities"] == []
    assert "learning.start" in payload["data"]["capability_ids"]
    assert "workflow.enter" in payload["data"]["capability_ids"]
    assert "workflow.reopen" in payload["data"]["capability_ids"]
    assert "workflow.resolve" in payload["data"]["capability_ids"]
    assert "accept.route-repair" in payload["data"]["capability_ids"]


def test_agent_api_list_uses_progressive_disclosure() -> None:
    result = runner.invoke(
        app,
        ["api", "list", "--limit", "2", "--format", "json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert len(payload["items"]) == 2
    assert all(item["id"] and item["summary"] for item in payload["items"])
    assert all(item["show_argv"] for item in payload["items"])
    assert payload["next_argv"]


def test_agent_api_show_and_schema_expand_one_record() -> None:
    show_result = runner.invoke(
        app,
        ["api", "show", "learning.start", "--format", "json"],
        catch_exceptions=False,
    )
    schema_result = runner.invoke(
        app,
        ["api", "schema", "workflow-blocker", "--format", "json"],
        catch_exceptions=False,
    )

    assert show_result.exit_code == 0
    assert json.loads(show_result.stdout)["data"]["id"] == "learning.start"
    assert schema_result.exit_code == 0
    schema_payload = json.loads(schema_result.stdout)
    assert schema_payload["data"]["schema_id"] == "workflow-blocker"
    assert schema_payload["data"]["schema"]["type"] == "object"


def test_agent_api_commands_catalog_lists_all_surfaces_progressively() -> None:
    result = runner.invoke(
        app,
        [
            "api",
            "commands",
            "--query",
            "learning",
            "--limit",
            "3",
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["data"]["total_catalog"] > 100
    assert payload["data"]["total_matching"] >= 3
    assert len(payload["items"]) == 3
    assert all("learning" in item["id"] for item in payload["items"])
    assert all("parameters" not in item for item in payload["items"])
    assert all(
        item["show_argv"][:3] == ["specify", "api", "command"]
        for item in payload["items"]
    )


def test_agent_api_command_expands_only_one_cli_operation() -> None:
    result = runner.invoke(
        app,
        ["api", "command", "learning.start", "--format", "json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["id"] == "learning.start"
    assert payload["data"]["argv"] == ["specify", "learning", "start"]
    command_option = next(
        item for item in payload["data"]["parameters"] if "--command" in item["flags"]
    )
    assert command_option["required"] is True
    assert payload["data"]["machine_output"]["format_option"] == "--format"


@pytest.mark.parametrize(
    ("schema_id", "command_id"),
    [
        ("workflow-enter-input", "workflow.enter"),
        ("workflow-transition-input", "workflow.transition"),
        ("workflow-reopen-input", "workflow.reopen"),
        ("workflow-resolve-input", "workflow.resolve"),
    ],
)
def test_workflow_input_schema_fields_map_to_published_cli_options(
    schema_id: str,
    command_id: str,
) -> None:
    schema_result = runner.invoke(
        app,
        ["api", "schema", schema_id, "--format", "json"],
        catch_exceptions=False,
    )
    command_result = runner.invoke(
        app,
        ["api", "command", command_id, "--format", "json"],
        catch_exceptions=False,
    )

    assert schema_result.exit_code == 0
    assert command_result.exit_code == 0
    schema = json.loads(schema_result.stdout)["data"]["schema"]
    schema_options = {
        f"--{field_name.replace('_', '-')}" for field_name in schema["properties"]
    }
    command_parameters = json.loads(command_result.stdout)["data"]["parameters"]
    command_options = {
        flag
        for parameter in command_parameters
        for flag in parameter["flags"]
        if flag.startswith("--") and flag != "--format"
    }

    assert schema_options == command_options
    parameters_by_flag = {
        flag: parameter
        for parameter in command_parameters
        for flag in parameter["flags"]
    }
    for field_name in schema["required"]:
        flag = f"--{field_name.replace('_', '-')}"
        assert parameters_by_flag[flag]["required"] is True
        if schema["properties"][field_name].get("type") == "array":
            assert parameters_by_flag[flag]["repeatable"] is True


def test_agent_api_command_recognizes_boolean_json_output_switches() -> None:
    result = runner.invoke(
        app,
        ["api", "command", "discussion.status", "--format", "json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    machine_output = json.loads(result.stdout)["data"]["machine_output"]
    assert machine_output == {
        "declared": True,
        "format_option": "--json",
        "choices": ["json"],
    }


def test_agent_api_command_extracts_declared_format_values_from_live_help() -> None:
    expected = {
        "api.handshake": ["json"],
        "design.export": ["json", "tailwind"],
        "debug": ["text", "json", "spawn-json"],
    }

    for command_id, choices in expected.items():
        result = runner.invoke(
            app,
            ["api", "command", command_id, "--format", "json"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        machine_output = json.loads(result.stdout)["data"]["machine_output"]
        assert machine_output["choices"] == choices


def test_agent_api_commands_catalog_covers_the_actual_cross_domain_cli() -> None:
    result = runner.invoke(
        app,
        ["api", "commands", "--limit", "200", "--format", "json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    ids = {item["id"] for item in payload["items"]}
    assert payload["data"]["total_catalog"] == len(ids)
    assert {
        "init",
        "check",
        "lint",
        "learning.start",
        "learning.capture",
        "workflow.transition",
        "accept.closeout",
        "hook.validate-artifacts",
        "artifact.scaffold",
        "integration.install",
        "extension.add",
        "sp-teams.status",
    } <= ids
    assert "sp-teams.notify-hook" not in ids


def test_agent_command_catalog_never_requires_side_effect_or_summary_guessing() -> None:
    records = command_catalog(app)
    hints = {record["id"]: record["mutation_hint"] for record in records}

    assert [
        record["id"] for record in records if record["mutation_hint"] == "unknown"
    ] == []
    assert [
        record["id"]
        for record in records
        if record["summary"] == "No command summary is declared."
    ] == []
    assert hints["accept.validate"] == "read-only"
    assert hints["discussion.validate-handoff"] == "read-only"
    assert hints["hook.build-compaction"] == "local-write"
    assert hints["hook.validate-artifacts"] == "read-only"
    assert hints["hook.validate-state"] == "conditional-local-write"
    assert hints["learning.aggregate"] == "conditional-local-write"
    assert hints["eval.run"] == "inspect-before-execution"
    assert hints["sp-teams.live-probe"] == "inspect-before-execution"


def test_workflow_cli_refuses_skipping_plan_and_returns_human_recovery(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-agent-api"
    feature_dir.mkdir(parents=True)

    enter_result = _invoke_in_project(
        project,
        [
            "workflow",
            "enter",
            "--command",
            "specify",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    assert enter_result.exit_code == 0
    entered = json.loads(enter_result.stdout)
    revision = entered["data"]["revision"]

    skip_result = _invoke_in_project(
        project,
        [
            "workflow",
            "transition",
            "--to",
            "tasks",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            str(revision),
            "--format",
            "json",
        ],
    )

    assert skip_result.exit_code == 10
    blocked = json.loads(skip_result.stdout)
    assert blocked["status"] == "blocked"
    assert blocked["blockers"][0]["code"] == "invalid-transition"
    assert blocked["blockers"][0]["human_action_required"] is False
    assert blocked["blockers"][0]["exact_next_action"]
    assert blocked["next_argv"]


def test_workflow_cli_validates_current_stage_artifacts_before_advancing(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    feature_dir = project / ".specify" / "features" / "004-stage-gate"
    feature_dir.mkdir(parents=True)
    enter = _invoke_in_project(
        project,
        [
            "workflow",
            "enter",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    assert enter.exit_code == 0

    transition = _invoke_in_project(
        project,
        [
            "workflow",
            "complete-stage",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            "1",
            "--format",
            "json",
        ],
    )

    assert transition.exit_code == 10
    payload = json.loads(transition.stdout)
    assert payload["status"] == "blocked"
    assert payload["data"]["error_code"] == "artifact-validation-blocked"
    schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "workflow-blocker-schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload["blockers"][0])
    show = _invoke_in_project(
        project,
        [
            "workflow",
            "show",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    assert json.loads(show.stdout)["data"]["stage"] == "specify"
    assert json.loads(show.stdout)["data"]["revision"] == 1


def test_workflow_cli_advances_after_source_stage_artifacts_pass(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    feature_dir = project / ".specify" / "features" / "006-valid-stage"
    feature_dir.mkdir(parents=True)
    entered = _invoke_in_project(
        project,
        [
            "workflow",
            "enter",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    assert entered.exit_code == 0
    _write_valid_spec_contract(feature_dir)

    completed = _invoke_in_project(
        project,
        [
            "workflow",
            "complete-stage",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            "1",
            "--format",
            "json",
        ],
    )
    assert completed.exit_code == 0, completed.stdout
    completed_payload = json.loads(completed.stdout)

    result = _invoke_in_project(
        project,
        [
            "workflow",
            "transition",
            "--to",
            "plan",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            str(completed_payload["data"]["revision"]),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["stage"] == "plan"
    assert payload["data"]["revision"] == 3


def test_workflow_cli_reopens_an_invalidated_upstream_stage(tmp_path: Path) -> None:
    project = _project(tmp_path)
    feature_dir = project / ".specify" / "features" / "006-reopen-plan"
    feature_dir.mkdir(parents=True)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for stage in ("plan", "tasks", "implement"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=stage,
            revision=revision,
        )
        revision = advanced["data"]["revision"]

    result = _invoke_in_project(
        project,
        [
            "workflow",
            "reopen",
            "--feature-dir",
            str(feature_dir),
            "--to",
            "plan",
            "--expected-revision",
            str(revision),
            "--reason",
            "Analyze invalidated the plan contract.",
            "--evidence",
            "AN-004",
            "--invalidated-artifacts",
            "plan.md",
            "--invalidated-artifacts",
            "tasks.md",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["data"]["stage"] == "plan"
    assert payload["data"]["last_reopen"]["source_stage"] == "implement"
    assert payload["next_argv"][:3] == ["specify", "workflow", "complete-stage"]


def test_workflow_cli_human_blocker_includes_novice_acceptance_steps(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    feature_dir = project / ".specify" / "features" / "003-human-block"
    feature_dir.mkdir(parents=True)
    enter = _invoke_in_project(
        project,
        [
            "workflow",
            "enter",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    assert enter.exit_code == 0
    blocker_input = project / "blocker.json"
    blocker_input.write_text(
        json.dumps(
            {
                "feature_dir": "ignored/by-explicit-override",
                "expected_revision": 1,
                "category": "credentials-or-permission",
                "owner": "maintainer",
                "cause": "A protected setting needs maintainer authority.",
                "evidence": ["Sanitized probe returned HTTP 403."],
                "attempted_recovery": [
                    {"action": "Checked token scope", "result": "Write scope absent"}
                ],
                "affected_scope": ["protected pipeline"],
                "exact_next_action": "Enable the named protected setting.",
                "unblock_criteria": "A read-only probe reports enabled.",
            }
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "workflow",
            "block",
            "--input",
            "blocker.json",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 10
    payload = json.loads(result.stdout)
    blocker = payload["blockers"][0]
    assert blocker["human_action_required"] is True
    assert len(blocker["human_action_guide"]["steps"]) >= 3
    assert payload["next_argv"] == []
    assert payload["show_argv"][:3] == ["specify", "workflow", "show"]
    assert "resolution_action" not in blocker
    assert payload["data"]["resolution_action"]["capability_id"] == "workflow.resolve"

    resumed = _invoke_in_project(project, payload["show_argv"][1:])
    assert resumed.exit_code == 10
    resumed_payload = json.loads(resumed.stdout)
    assert resumed_payload["status"] == "blocked"
    assert resumed_payload["blockers"][0]["blocker_id"] == blocker["blocker_id"]

    resolved = _invoke_in_project(
        project,
        [
            "workflow",
            "resolve",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            "2",
            "--resolution-evidence",
            "Read-only probe reports the setting enabled.",
            "--format",
            "json",
        ],
    )
    assert resolved.exit_code == 0
    resolved_payload = json.loads(resolved.stdout)
    assert resolved_payload["data"]["status"] == "active"
    assert resolved_payload["data"]["last_blocker_resolution"]["owner"] == "maintainer"


def test_workflow_cli_external_system_blocker_does_not_invent_human_work(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    feature_dir = project / ".specify" / "features" / "007-external-block"
    feature_dir.mkdir(parents=True)
    enter = _invoke_in_project(
        project,
        [
            "workflow",
            "enter",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    assert enter.exit_code == 0
    blocker_input = project / "blocker.json"
    blocker_input.write_text(
        json.dumps(
            {
                "feature_dir": str(feature_dir),
                "expected_revision": 1,
                "category": "external-system",
                "owner": "external-system",
                "cause": "The required upstream service is unavailable.",
                "evidence": ["A sanitized health probe returned HTTP 503."],
                "attempted_recovery": [
                    {
                        "action": "Retried the read-only probe",
                        "result": "Still HTTP 503",
                    }
                ],
                "affected_scope": ["remote verification evidence"],
                "exact_next_action": "Retry after the upstream service recovers.",
                "unblock_criteria": "The health probe returns HTTP 200.",
                "human_action_required": False,
            }
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["workflow", "block", "--input", "blocker.json", "--format", "json"],
    )

    assert result.exit_code == 10
    payload = json.loads(result.stdout)
    blocker = payload["blockers"][0]
    assert blocker["human_action_required"] is False
    assert blocker["human_action_guide"] is None
    assert blocker["evidence"] == ["A sanitized health probe returned HTTP 503."]
    assert payload["next_argv"] == []
    assert "resolution_action" not in blocker
    assert payload["data"]["resolution_action"]["capability_id"] == "workflow.resolve"


def test_workflow_cli_requires_matching_revision_for_mutation(tmp_path: Path) -> None:
    project = _project(tmp_path)
    feature_dir = project / ".specify" / "features" / "002-revision"
    feature_dir.mkdir(parents=True)
    enter_result = _invoke_in_project(
        project,
        [
            "workflow",
            "enter",
            "--command",
            "specify",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    assert enter_result.exit_code == 0

    closeout_result = _invoke_in_project(
        project,
        [
            "workflow",
            "closeout",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            "99",
            "--summary",
            "Specification is complete",
            "--format",
            "json",
        ],
    )

    assert closeout_result.exit_code == 10
    payload = json.loads(closeout_result.stdout)
    assert payload["status"] == "blocked"
    assert payload["blockers"][0]["code"] == "revision-conflict"


def test_workflow_cli_validates_human_acceptance_before_closeout(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    feature_dir = project / ".specify" / "features" / "005-accept-gate"
    feature_dir.mkdir(parents=True)
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for stage in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=stage,
            revision=revision,
        )
        revision = advanced["data"]["revision"]

    result = _invoke_in_project(
        project,
        [
            "workflow",
            "closeout",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            str(revision),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 10
    payload = json.loads(result.stdout)
    assert payload["data"]["error_code"] == "human-acceptance-required"
    assert payload["blockers"][0]["owner"] == "agent"
    assert payload["blockers"][0]["human_action_required"] is False
    assert payload["blockers"][0]["resume"]["argv"][:3] == [
        "specify",
        "accept",
        "prepare",
    ]
    shown = json.loads(
        _invoke_in_project(
            project,
            [
                "workflow",
                "show",
                "--feature-dir",
                str(feature_dir),
                "--format",
                "json",
            ],
        ).stdout
    )
    assert shown["data"]["status"] == "active"


def test_workflow_closeout_rejects_a_valid_but_unaccepted_draft(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    feature_dir = project / ".specify" / "features" / "006-accept-draft"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implementation-summary.md").write_text(
        "# Implementation Summary\n\nThe feature is technically complete.\n",
        encoding="utf-8",
    )
    prepare_human_acceptance(project, feature_dir)
    _write_rich_workflow_state(
        feature_dir,
        command="sp-accept",
        phase="acceptance-only",
        next_command="/sp.accept",
    )
    entered = enter_workflow(feature_dir, stage="specify", expected_revision=0)
    revision = entered["data"]["revision"]
    for stage in ("plan", "tasks", "implement", "accept"):
        advanced = _complete_then_transition(
            feature_dir,
            target_stage=stage,
            revision=revision,
        )
        revision = advanced["data"]["revision"]

    result = _invoke_in_project(
        project,
        [
            "workflow",
            "closeout",
            "--feature-dir",
            str(feature_dir),
            "--expected-revision",
            str(revision),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 10
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["data"]["error_code"] == "human-acceptance-required"
    assert any(
        "status=accepted" in error
        for error in payload["data"]["human_acceptance"]["errors"]
    )
    assert (
        json.loads(
            _invoke_in_project(
                project,
                [
                    "workflow",
                    "show",
                    "--feature-dir",
                    str(feature_dir),
                    "--format",
                    "json",
                ],
            ).stdout
        )["data"]["status"]
        == "active"
    )
