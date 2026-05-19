import json
from pathlib import Path
import subprocess

from specify_cli.hooks.engine import run_quality_hook
from specify_cli.project_map_status import ProjectMapStatus, write_project_map_status


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-preflight-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_cognition_baseline(project: Path) -> None:
    cognition_dir = project / ".specify" / "project-cognition"
    cognition_dir.mkdir(parents=True, exist_ok=True)
    (cognition_dir / "status.json").write_text(
        '{"version": 3, "graph_ready": true, "baseline_state": "ready", "freshness": "fresh", '
        '"graph_store_path": ".specify/project-cognition/project-cognition.db", '
        '"active_generation_id": "GEN-0001", "query_contract_version": 1, "update_contract_version": 1}\n',
        encoding="utf-8",
    )
    (cognition_dir / "project-cognition.db").write_bytes(b"SQLite test database marker")


def _write_dirty_cognition_status(project: Path, status: ProjectMapStatus) -> None:
    status_path = write_project_map_status(project, status)
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    for key in ("baseline_state", "graph_ready", "readiness"):
        payload.pop(key, None)
    payload["freshness"] = status.freshness
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_workflow_state(
    feature_dir: Path,
    *,
    active_command: str,
    status: str,
    phase_mode: str,
    next_command: str,
    lane_id: str | None = None,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
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
                "## Next Action",
                "",
                "- continue",
                "",
                "## Next Command",
                "",
                f"- `{next_command}`",
                "",
                "## Lane Context",
                "",
                f"- lane_id: `{lane_id or ''}`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_preflight_blocks_implement_when_workflow_state_requires_analyze(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_command="/sp.analyze",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert result.severity == "critical"
    assert any("/sp.analyze" in message for message in result.errors)
    assert any("active_command=sp-tasks" in message for message in result.errors)
    assert any("workflow_status=completed" in message for message in result.errors)


def test_preflight_explains_implement_block_with_tracker_summary_when_available(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-plan",
        status="completed",
        phase_mode="design-only",
        next_command="/sp.tasks",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: near-complete",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "",
                "- current_batch: batch-final",
                "- goal: finish validation",
                "- next_action: run quickstart validation",
                "",
                "## Execution State",
                "",
                "- retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("/sp.tasks" in message for message in result.errors)
    assert any("active_command=sp-plan" in message for message in result.errors)
    assert any("workflow_status=completed" in message for message in result.errors)
    assert any("tracker_status=near-complete" in message for message in result.errors)
    assert any("current_batch=batch-final" in message for message in result.errors)


def test_preflight_warns_when_project_map_status_is_missing_for_brownfield_work(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-specify",
        status="active",
        phase_mode="planning-only",
        next_command="/sp.plan",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert result.severity == "warning"
    assert result.errors == []
    assert any("cognition" in message.lower() for message in result.warnings)


def test_preflight_missing_runtime_guidance_names_sqlite_database_not_graph_json(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-specify",
        status="active",
        phase_mode="planning-only",
        next_command="/sp.plan",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    combined = "\n".join(result.errors + result.warnings).lower()
    assert "project-cognition.db" in combined or "project cognition" in combined
    assert "nodes.json" not in combined
    assert "edges.json" not in combined
    assert "claims.json" not in combined
    assert "conflicts.json" not in combined


def test_preflight_result_uses_project_cognition_data_key(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-specify",
        status="active",
        phase_mode="planning-only",
        next_command="/sp.plan",
    )
    _write_cognition_baseline(project)

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status in {"ok", "warn"}
    assert "project_cognition" in result.data
    assert "project_map" not in result.data


def test_preflight_warns_for_same_feature_implement_resume_when_dirty_origin_matches(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-implement",
        status="active",
        phase_mode="execution-only",
        next_command="/sp.implement",
        lane_id="lane-001",
    )
    _write_dirty_cognition_status(
        project,
        ProjectMapStatus(
            global_freshness="stale",
            global_dirty=True,
            global_dirty_reasons=["shared_surface_changed"],
            global_dirty_origin_command="implement",
            global_dirty_origin_feature_dir="specs/001-demo",
            global_dirty_origin_lane_id="lane-001",
        ),
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert any("resume may continue" in message.lower() or "shared_surface_changed" in message for message in result.warnings)


def test_preflight_warns_same_feature_implement_when_lane_id_differs(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-implement",
        status="active",
        phase_mode="execution-only",
        next_command="/sp.implement",
        lane_id="lane-002",
    )
    _write_dirty_cognition_status(
        project,
        ProjectMapStatus(
            global_freshness="stale",
            global_dirty=True,
            global_dirty_reasons=["shared_surface_changed"],
            global_dirty_origin_command="implement",
            global_dirty_origin_feature_dir="specs/001-demo",
            global_dirty_origin_lane_id="lane-001",
        ),
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert result.errors == []
    assert any("cognition" in message.lower() or "shared_surface_changed" in message for message in result.warnings)


def test_preflight_warns_same_lane_implement_when_dirty_scope_does_not_overlap(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-implement",
        status="active",
        phase_mode="execution-only",
        next_command="/sp.implement",
        lane_id="lane-001",
    )
    packet_path = project / "packet.json"
    packet_path.write_text(
        json.dumps(
            {
                "feature_id": "001-demo",
                "task_id": "T001",
                "story_id": "US1",
                "objective": "demo",
                "scope": {
                    "write_scope": ["src/feature/current.py"],
                    "read_scope": [".specify/project-cognition/status.json"],
                },
                "context_bundle": [
                    {
                        "path": ".specify/project-cognition/status.json",
                        "kind": "project_cognition",
                        "purpose": "routing",
                        "required_for": ["workflow_boundary"],
                        "read_order": 1,
                        "must_read": True,
                        "selection_reason": "required",
                    }
                ],
                "required_references": [{"path": "src/feature/current.py", "reason": "demo"}],
                "hard_rules": ["preserve boundary"],
                "forbidden_drift": ["do not skip tests"],
                "validation_gates": ["pytest -q"],
                "done_criteria": ["done"],
                "handoff_requirements": ["return changed files"],
                "platform_guardrails": ["respect supported platforms"],
                "intent": {
                    "outcome": "demo",
                    "constraints": ["preserve boundary"],
                    "success_signals": ["done"],
                },
                "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_dirty_cognition_status(
        project,
        ProjectMapStatus(
            global_freshness="stale",
            global_dirty=True,
            global_dirty_reasons=["shared_surface_changed"],
            global_dirty_origin_command="implement",
            global_dirty_origin_feature_dir="specs/001-demo",
            global_dirty_origin_lane_id="lane-001",
            global_dirty_scope_paths=["src/specify_cli/hooks/preflight.py"],
        ),
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {
            "command_name": "implement",
            "feature_dir": str(feature_dir),
            "packet_file": str(packet_path),
        },
    )

    assert result.status == "warn"
    assert result.errors == []
    assert any("shared_surface_changed" in message for message in result.warnings)


def test_preflight_warns_same_lane_implement_when_dirty_scope_overlaps(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-implement",
        status="active",
        phase_mode="execution-only",
        next_command="/sp.implement",
        lane_id="lane-001",
    )
    packet_path = project / "packet.json"
    packet_path.write_text(
        json.dumps(
            {
                "feature_id": "001-demo",
                "task_id": "T001",
                "story_id": "US1",
                "objective": "demo",
                "scope": {
                    "write_scope": ["src/specify_cli/hooks/preflight.py"],
                    "read_scope": [".specify/project-cognition/status.json"],
                },
                "context_bundle": [
                    {
                        "path": ".specify/project-cognition/status.json",
                        "kind": "project_cognition",
                        "purpose": "routing",
                        "required_for": ["workflow_boundary"],
                        "read_order": 1,
                        "must_read": True,
                        "selection_reason": "required",
                    }
                ],
                "required_references": [{"path": "src/specify_cli/hooks/preflight.py", "reason": "demo"}],
                "hard_rules": ["preserve boundary"],
                "forbidden_drift": ["do not skip tests"],
                "validation_gates": ["pytest -q"],
                "done_criteria": ["done"],
                "handoff_requirements": ["return changed files"],
                "platform_guardrails": ["respect supported platforms"],
                "intent": {
                    "outcome": "demo",
                    "constraints": ["preserve boundary"],
                    "success_signals": ["done"],
                },
                "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_dirty_cognition_status(
        project,
        ProjectMapStatus(
            global_freshness="stale",
            global_dirty=True,
            global_dirty_reasons=["shared_surface_changed"],
            global_dirty_origin_command="implement",
            global_dirty_origin_feature_dir="specs/001-demo",
            global_dirty_origin_lane_id="lane-001",
            global_dirty_scope_paths=["src/specify_cli/hooks/preflight.py"],
        ),
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {
            "command_name": "implement",
            "feature_dir": str(feature_dir),
            "packet_file": str(packet_path),
        },
    )

    assert result.status == "warn"
    assert result.errors == []
    assert any("shared_surface_changed" in message for message in result.warnings)


def test_preflight_warns_same_lane_implement_when_dirty_scope_is_shared_config_family(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-implement",
        status="active",
        phase_mode="execution-only",
        next_command="/sp.implement",
        lane_id="lane-001",
    )
    packet_path = project / "packet.json"
    packet_path.write_text(
        json.dumps(
            {
                "feature_id": "001-demo",
                "task_id": "T001",
                "story_id": "US1",
                "objective": "demo",
                "scope": {
                    "write_scope": ["src/feature/current.py"],
                    "read_scope": [".specify/project-cognition/status.json"],
                },
                "context_bundle": [
                    {
                        "path": ".specify/project-cognition/status.json",
                        "kind": "project_cognition",
                        "purpose": "routing",
                        "required_for": ["workflow_boundary"],
                        "read_order": 1,
                        "must_read": True,
                        "selection_reason": "required",
                    }
                ],
                "required_references": [{"path": "src/feature/current.py", "reason": "demo"}],
                "hard_rules": ["preserve boundary"],
                "forbidden_drift": ["do not skip tests"],
                "validation_gates": ["pytest -q"],
                "done_criteria": ["done"],
                "handoff_requirements": ["return changed files"],
                "platform_guardrails": ["respect supported platforms"],
                "intent": {
                    "outcome": "demo",
                    "constraints": ["preserve boundary"],
                    "success_signals": ["done"],
                },
                "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_dirty_cognition_status(
        project,
        ProjectMapStatus(
            global_freshness="stale",
            global_dirty=True,
            global_dirty_reasons=["shared_surface_changed"],
            global_dirty_origin_command="implement",
            global_dirty_origin_feature_dir="specs/001-demo",
            global_dirty_origin_lane_id="lane-001",
            global_dirty_scope_paths=["package.json"],
        ),
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {
            "command_name": "implement",
            "feature_dir": str(feature_dir),
            "packet_file": str(packet_path),
        },
    )

    assert result.status == "warn"
    assert result.errors == []
    assert any("shared_surface_changed" in message for message in result.warnings)


def test_preflight_warns_same_lane_implement_when_dirty_scope_is_workflow_surface_family(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-implement",
        status="active",
        phase_mode="execution-only",
        next_command="/sp.implement",
        lane_id="lane-001",
    )
    packet_path = project / "packet.json"
    packet_path.write_text(
        json.dumps(
            {
                "feature_id": "001-demo",
                "task_id": "T001",
                "story_id": "US1",
                "objective": "demo",
                "scope": {
                    "write_scope": ["src/specify_cli/hooks/preflight.py"],
                    "read_scope": [".specify/project-cognition/status.json"],
                },
                "context_bundle": [
                    {
                        "path": ".specify/project-cognition/status.json",
                        "kind": "project_cognition",
                        "purpose": "routing",
                        "required_for": ["workflow_boundary"],
                        "read_order": 1,
                        "must_read": True,
                        "selection_reason": "required",
                    }
                ],
                "required_references": [{"path": "src/specify_cli/hooks/preflight.py", "reason": "demo"}],
                "hard_rules": ["preserve boundary"],
                "forbidden_drift": ["do not skip tests"],
                "validation_gates": ["pytest -q"],
                "done_criteria": ["done"],
                "handoff_requirements": ["return changed files"],
                "platform_guardrails": ["respect supported platforms"],
                "intent": {
                    "outcome": "demo",
                    "constraints": ["preserve boundary"],
                    "success_signals": ["done"],
                },
                "dispatch_policy": {"mode": "hard_fail", "must_acknowledge_rules": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_dirty_cognition_status(
        project,
        ProjectMapStatus(
            global_freshness="stale",
            global_dirty=True,
            global_dirty_reasons=["shared_surface_changed"],
            global_dirty_origin_command="implement",
            global_dirty_origin_feature_dir="specs/001-demo",
            global_dirty_origin_lane_id="lane-001",
            global_dirty_scope_paths=["templates/commands/implement.md"],
        ),
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {
            "command_name": "implement",
            "feature_dir": str(feature_dir),
            "packet_file": str(packet_path),
        },
    )

    assert result.status == "warn"
    assert result.errors == []
    assert any("shared_surface_changed" in message for message in result.warnings)


def test_preflight_warns_cross_feature_implement_when_dirty_origin_differs(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    feature_dir = project / "specs" / "002-other"
    _write_workflow_state(
        feature_dir,
        active_command="sp-implement",
        status="active",
        phase_mode="execution-only",
        next_command="/sp.implement",
        lane_id="lane-002",
    )
    _write_dirty_cognition_status(
        project,
        ProjectMapStatus(
            global_freshness="stale",
            global_dirty=True,
            global_dirty_reasons=["shared_surface_changed"],
            global_dirty_origin_command="implement",
            global_dirty_origin_feature_dir="specs/001-demo",
            global_dirty_origin_lane_id="lane-001",
        ),
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert result.errors == []
    assert any("shared_surface_changed" in message for message in result.warnings)


def test_preflight_warns_specify_when_dirty_origin_exists(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    feature_dir = project / "specs" / "003-new"
    _write_workflow_state(
        feature_dir,
        active_command="sp-specify",
        status="active",
        phase_mode="planning-only",
        next_command="/sp.plan",
    )
    _write_dirty_cognition_status(
        project,
        ProjectMapStatus(
            global_freshness="stale",
            global_dirty=True,
            global_dirty_reasons=["workflow_contract_changed"],
            global_dirty_origin_command="implement",
            global_dirty_origin_feature_dir="specs/001-demo",
            global_dirty_origin_lane_id="lane-001",
        ),
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert result.errors == []
    assert any("workflow_contract_changed" in message for message in result.warnings)


def test_preflight_uses_cognition_status_metadata_before_stale_project_map_status(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, check=True)
    (project / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "init", "-q"], cwd=project, check=True)
    feature_dir = project / "specs" / "003-new"
    _write_workflow_state(
        feature_dir,
        active_command="sp-specify",
        status="active",
        phase_mode="planning-only",
        next_command="/sp.plan",
    )
    _write_dirty_cognition_status(
        project,
        ProjectMapStatus(
            global_freshness="stale",
            global_dirty=True,
            global_dirty_reasons=["workflow_contract_changed"],
            global_dirty_origin_command="implement",
            global_dirty_origin_feature_dir="specs/001-demo",
            global_dirty_origin_lane_id="lane-001",
        ),
    )
    (project / ".specify" / "project-cognition" / "status.json").write_text(
        json.dumps(
            {
                "version": 2,
                "baseline_state": "ready",
                "baseline_commit": subprocess.run(
                    ["git", "-C", str(project), "rev-parse", "HEAD"],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                ).stdout.strip(),
                "baseline_branch": "main",
                "baseline_built_at": "2026-05-11T00:00:00Z",
                "graph_ready": True,
                "freshness": "fresh",
                "last_refresh_reason": "map-update",
                "last_refresh_topics": ["INTEGRATIONS.md"],
                "last_refresh_scope": "partial",
                "last_refresh_basis": "map-update",
                "manual_force_stale": False,
                "manual_force_stale_reasons": [],
                "dirty": False,
                "dirty_reasons": [],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"


def test_preflight_blocks_support_drift_with_support_specific_guidance(monkeypatch, tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "003-new"
    _write_workflow_state(
        feature_dir,
        active_command="sp-specify",
        status="active",
        phase_mode="planning-only",
        next_command="/sp.plan",
    )

    def support_drift(_project_root: Path) -> dict[str, object]:
        return {
            "freshness": "support_drift",
            "recommended_next_action": "commit_or_ignore_support_files",
            "reasons": ["tool-managed support surface changed: .specify/templates/runtime-config.template.json"],
        }

    monkeypatch.setattr("specify_cli.hooks.project_cognition.inspect_project_cognition_freshness", support_drift)

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert result.errors == []
    assert any("support" in message.lower() for message in result.warnings)
    assert not any("sp-map-update" in message.lower() for message in result.warnings)


def test_preflight_blocks_integrate_when_lane_is_not_ready(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "lanes" / "lane-001").mkdir(parents=True, exist_ok=True)
    (project / ".specify" / "lanes" / "lane-001" / "lane.json").write_text(
        "\n".join(
            [
                "{",
                '  "lane_id": "lane-001",',
                '  "feature_id": "001-demo",',
                '  "feature_dir": "specs/001-demo",',
                '  "branch_name": "001-demo",',
                '  "worktree_path": ".specify/lanes/worktrees/lane-001",',
                '  "lifecycle_state": "implementing",',
                '  "recovery_state": "blocked",',
                '  "last_command": "implement",',
                '  "last_stable_checkpoint": "",',
                '  "recovery_reason": "missing verification",',
                '  "verification_status": "failed",',
                '  "created_at": "2026-05-02T00:00:00+00:00",',
                '  "updated_at": "2026-05-02T00:00:00+00:00"',
                "}",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: blocked",
                "feature: 001-demo",
                "resume_decision: blocked-waiting",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: blocked",
                "next_action: fix verification",
                "",
                "## Execution State",
                "retry_attempts: 1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "integrate", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("integrate precheck failed" in message for message in result.errors)
