from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook
from specify_cli.hooks.types import HookResult
from specify_cli.agent_api import validate_workflow_blocker_payload


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "policy-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def test_hook_result_supports_repairable_block_status():
    result = HookResult(
        event="workflow.policy.evaluate",
        status="repairable-block",
        severity="warning",
    )
    payload = result.to_dict()
    assert payload["status"] == "repairable-block"
    blocker = payload["blockers"][0]
    assert blocker["workflow"] == "shared-hook-runtime"
    assert blocker["stage"] == "workflow.policy.evaluate"
    assert blocker["owner"] == "agent"
    assert blocker["human_action_required"] is False
    assert blocker["unblock_criteria"]
    assert blocker["resume"]["instruction"]
    assert blocker["resume"]["argv"] == [
        "specify",
        "api",
        "command",
        "hook.workflow-policy",
        "--format",
        "json",
    ]
    assert blocker["resume"]["command"]
    assert validate_workflow_blocker_payload(blocker) == []


def test_hook_result_preserves_explicit_human_blocker_tutorial():
    blocker = {
        "version": 1,
        "blocker_id": "ci-approval",
        "workflow": "spx-implement",
        "stage": "protected-ci",
        "category": "external-system",
        "owner": "maintainer",
        "summary": "Protected CI approval is required",
        "details": "The manual job is organization-controlled.",
        "evidence": ["pipeline 42 is waiting"],
        "attempted_recovery": [],
        "exact_next_action": "Approve the verify job",
        "approval_question": "Approve verify?",
        "unblock_criteria": "verify passes",
        "affected_scope": ["implementation closeout"],
        "can_continue": False,
        "human_action_required": True,
        "human_action_guide": {
            "goal": "Run verify",
            "why_human": "Protected authority",
            "prerequisites": ["Maintainer access"],
            "safety_notes": ["Do not share tokens"],
            "steps": [{"order": 1, "title": "Approve", "action": "Click verify", "command": None, "expected_result": "passed", "if_failed": "return the job log"}],
            "verification": ["verify passes"],
            "evidence_to_return": ["pipeline URL"],
            "resume_instruction": "Resume spx-implement",
        },
        "resume": {
            "instruction": "Inspect the implementation workflow command contract.",
            "command": "specify api command workflow.next --format json",
            "argv": [
                "specify",
                "api",
                "command",
                "workflow.next",
                "--format",
                "json",
            ],
        },
    }
    result = HookResult(
        event="workflow.commit.validate",
        status="blocked",
        severity="critical",
        blockers=[blocker],
    )

    assert result.to_dict()["blockers"] == [blocker]


def test_hook_result_round_trips_policy_metadata():
    result = HookResult(
        event="workflow.policy.evaluate",
        status="warn",
        severity="warning",
        data={
            "policy": {
                "classification": "soft-enforced",
                "repairable": True,
                "compaction": {"stale": False},
            }
        },
    )
    payload = result.to_dict()
    assert payload["data"]["policy"]["classification"] == "soft-enforced"
    assert payload["data"]["policy"]["repairable"] is True
    assert payload["data"]["policy"]["compaction"]["stale"] is False


def test_workflow_policy_marks_missing_state_as_repairable_block(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)

    result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        {"command_name": "specify", "feature_dir": str(feature_dir), "trigger": "pre_tool"},
    )

    assert result.status == "repairable-block"
    assert any("workflow-state.md" in action for action in result.actions)
    state_result = result.data["policy"]["state_result"]
    assert state_result["data"]["autofix"]["available"] is True
    assert "--autofix" in state_result["data"]["autofix"]["command"]


def test_workflow_policy_denies_explicit_phase_jump(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-specify`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: demo",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        {
            "command_name": "specify",
            "feature_dir": str(feature_dir),
            "trigger": "prompt",
            "requested_action": "jump_to_implement",
        },
    )

    assert result.status == "blocked"
    assert any("phase" in error.lower() for error in result.errors)


def _write_sp_specify_workflow_state(feature_dir: Path) -> None:
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-specify`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: demo",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "",
                "## Next Action",
                "",
                "- refine scope",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
                "## Learning Signals",
                "",
                "- route_reason: spec not yet approved for planning",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_workflow_policy_redirects_first_phase_drift(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_sp_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        {
            "command_name": "specify",
            "feature_dir": str(feature_dir),
            "trigger": "prompt",
            "requested_action": "start_editing_code",
        },
    )

    assert result.status == "warn"
    assert result.data["policy"]["classification"] == "redirect"
    assert result.data["policy"]["recovery_summary"]["next_command"] == "/sp.plan"


def test_workflow_policy_blocks_repeated_phase_drift(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_sp_specify_workflow_state(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        {
            "command_name": "specify",
            "feature_dir": str(feature_dir),
            "trigger": "prompt",
            "requested_action": "start_editing_code",
            "prior_redirect_count": 1,
        },
    )

    assert result.status == "blocked"
    assert any("phase" in error.lower() for error in result.errors)


def test_workflow_policy_blocks_second_phase_drift_without_override(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_sp_specify_workflow_state(feature_dir)
    payload = {
        "command_name": "specify",
        "feature_dir": str(feature_dir),
        "trigger": "prompt",
        "requested_action": "start_editing_code",
    }

    first_result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        payload,
    )
    second_result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        payload,
    )

    assert first_result.status == "warn"
    assert second_result.status == "blocked"
    assert any("phase" in error.lower() for error in second_result.errors)


def test_workflow_policy_blocks_second_phase_drift_across_soft_action_labels(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_sp_specify_workflow_state(feature_dir)

    first_result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        {
            "command_name": "specify",
            "feature_dir": str(feature_dir),
            "trigger": "prompt",
            "requested_action": "start_editing_code",
        },
    )
    second_result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        {
            "command_name": "specify",
            "feature_dir": str(feature_dir),
            "trigger": "prompt",
            "requested_action": "run_fix_loop",
        },
    )

    assert first_result.status == "warn"
    assert second_result.status == "blocked"
    assert any("phase" in error.lower() for error in second_result.errors)
