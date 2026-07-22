import json
import os
from pathlib import Path

import pytest

from specify_cli.hooks.engine import QualityHookError, run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-engine-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_fake_project_cognition_bin(tmp_path: Path) -> Path:
    script = tmp_path / "project-cognition-fake.py"
    script.write_text(
        "\n".join(
            [
                "import json",
                "import pathlib",
                "import sys",
                "args = sys.argv[1:]",
                "if args[:1] == ['cognition']:",
                "    args = args[1:]",
                "cmd = args[0] if args else ''",
                "root = pathlib.Path.cwd()",
                "status_path = root / '.specify' / 'project-cognition' / 'status.json'",
                "calls_path = root / '.specify' / 'project-cognition-calls.jsonl'",
                "calls_path.parent.mkdir(parents=True, exist_ok=True)",
                "with calls_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(json.dumps(args) + '\\n')",
                "if cmd == 'mark-dirty':",
                "    reason = args[args.index('--reason') + 1] if '--reason' in args else ''",
                "    payload = {",
                "        'dirty': True,",
                "        'freshness': 'stale',",
                "        'dirty_reasons': [reason.replace(' ', '_')],",
                "        'dirty_origin_command': args[args.index('--origin-command') + 1] if '--origin-command' in args else '',",
                "        'dirty_origin_feature_dir': args[args.index('--origin-feature-dir') + 1] if '--origin-feature-dir' in args else '',",
                "        'dirty_origin_lane_id': args[args.index('--origin-lane-id') + 1] if '--origin-lane-id' in args else '',",
                "        'status_path': str(status_path),",
                "    }",
                "    status_path.parent.mkdir(parents=True, exist_ok=True)",
                "    status_path.write_text(json.dumps(payload) + '\\n', encoding='utf-8')",
                "elif cmd == 'status':",
                "    payload = json.loads(status_path.read_text(encoding='utf-8')) if status_path.exists() else {'freshness': 'missing_baseline', 'status_path': str(status_path)}",
                "elif cmd == 'check':",
                "    payload = {'state': 'fresh', 'freshness': 'fresh', 'readiness': 'ready', 'reasons': [], 'status_path': str(status_path)}",
                "elif cmd == 'complete-refresh':",
                "    payload = {'freshness': 'fresh', 'status_path': str(status_path)}",
                "    status_path.parent.mkdir(parents=True, exist_ok=True)",
                "    status_path.write_text(json.dumps(payload) + '\\n', encoding='utf-8')",
                "elif cmd == 'validate-build':",
                "    payload = {'status': 'ok', 'errors': []}",
                "else:",
                "    payload = {'command': cmd, 'args': args}",
                "print(json.dumps(payload))",
            ]
        ),
        encoding="utf-8",
    )
    return script


def _write_workflow_state(
    feature_dir: Path,
    *,
    active_command: str,
    status: str,
    phase_mode: str,
    next_action: str,
    next_command: str,
) -> Path:
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "workflow-state.md"
    target.write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                f"- active_command: `{active_command}`",
                f"- status: `{status}`",
                "",
                "## Phase Mode",
                "",
                f"- phase_mode: `{phase_mode}`",
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
                "## Exit Criteria",
                "",
                "- done",
                "",
                "## Next Action",
                "",
                f"- {next_action}",
                "",
                "## Next Command",
                "",
                f"- `{next_command}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def _write_quick_status(workspace: Path) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "STATUS.md"
    target.write_text(
        "\n".join(
            [
                "---",
                'id: "260427-001"',
                'slug: "demo-quick-task"',
                'title: "Demo quick task"',
                'status: "executing"',
                'dispatch_shape: "one-subagent"',
                'execution_surface: "native-subagents"',
                "---",
                "",
                "## Current Focus",
                "",
                "goal: keep resumable state accurate",
                "current_focus: validate quick checkpoint",
                "next_action: collect worker result",
                "",
                "## Execution",
                "",
                "active_lane: worker-a",
                "join_point: none",
                "execution_fallback: none",
                "retry_attempts: 0",
                "blocker_reason:",
                "",
                "## Summary Pointer",
                "",
                "summary_path: .planning/quick/260427-001-demo-quick-task/SUMMARY.md",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def test_run_quality_hook_rejects_unknown_event(tmp_path: Path):
    project = _create_project(tmp_path)

    with pytest.raises(QualityHookError, match="Unknown hook event"):
        run_quality_hook(project, "unknown.event", {})


def test_workflow_state_validate_blocks_missing_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert result.severity == "critical"
    assert any("workflow-state.md" in message for message in result.errors)


def test_project_cognition_mark_dirty_hook_invokes_external_binary(tmp_path: Path, monkeypatch):
    project = _create_project(tmp_path)
    fake_bin = _write_fake_project_cognition_bin(tmp_path)
    monkeypatch.setenv("SPECIFY_RUNTIME_BIN", f"{os.sys.executable}{os.pathsep}{fake_bin}")

    result = run_quality_hook(
        project,
        "project_cognition.mark_dirty",
        {
            "reason": "shared surface changed",
            "origin_command": "implement",
            "origin_feature_dir": "specs/001-demo",
            "origin_lane_id": "lane-001",
        },
    )

    assert result.status == "ok"
    assert result.severity == "info"
    status_path = project / ".specify" / "project-cognition" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["dirty"] is True
    assert payload["freshness"] == "stale"
    assert payload["dirty_reasons"] == ["shared_surface_changed"]
    assert payload["dirty_origin_command"] == "implement"
    assert payload["dirty_origin_feature_dir"] == "specs/001-demo"
    assert payload["dirty_origin_lane_id"] == "lane-001"
    calls = (project / ".specify" / "project-cognition-calls.jsonl").read_text(encoding="utf-8")
    assert '"mark-dirty"' in calls


def test_project_map_hook_event_alias_is_removed(tmp_path: Path):
    project = _create_project(tmp_path)

    with pytest.raises(QualityHookError, match="Unknown hook event"):
        run_quality_hook(project, "project_map.mark_dirty", {"reason": "shared surface changed"})


def test_workflow_checkpoint_returns_resume_payload_for_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-plan",
        status="active",
        phase_mode="design-only",
        next_action="finish constitution checks",
        next_command="/sp.tasks",
    )

    result = run_quality_hook(
        project,
        "workflow.checkpoint",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.severity == "info"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["state_kind"] == "workflow-state"
    assert checkpoint["active_command"] == "sp-plan"
    assert checkpoint["phase_mode"] == "design-only"
    assert checkpoint["summary"] == "demo"
    assert checkpoint["next_action"] == "finish constitution checks"
    assert checkpoint["next_command"] == "/sp.tasks"
    assert checkpoint["allowed_artifact_writes"] == ["spec.md"]
    assert checkpoint["forbidden_actions"] == ["edit source code"]
    assert checkpoint["authoritative_files"] == ["spec.md"]


def test_workflow_checkpoint_returns_resume_payload_for_quick_status(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260427-001-demo-quick-task"
    _write_quick_status(workspace)

    result = run_quality_hook(
        project,
        "workflow.checkpoint",
        {"command_name": "quick", "workspace": str(workspace)},
    )

    assert result.status == "ok"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["state_kind"] == "quick-status"
    assert checkpoint["active_lane"] == "worker-a"
    assert checkpoint["next_action"] == "collect worker result"
    assert checkpoint["resume_decision"] == "resume here"
