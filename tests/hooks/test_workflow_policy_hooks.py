from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook
from specify_cli.hooks.types import HookResult


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
        {"command_name": "implement", "feature_dir": str(feature_dir), "trigger": "pre_tool"},
    )

    assert result.status == "repairable-block"
    assert any("workflow-state.md" in action for action in result.actions)


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
