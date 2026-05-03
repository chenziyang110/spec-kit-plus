import json
import os
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-cli-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _invoke_in_project(project: Path, args: list[str]):
    runner = CliRunner()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)
    return result


def _run_module_in_project(project: Path, args: list[str]):
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    pythonpath_entries = [str(repo_root / "src")]
    if env.get("PYTHONPATH"):
        pythonpath_entries.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return subprocess.run(
        [sys.executable, "-m", "specify_cli", *args],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_hook_validate_state_outputs_parseable_json(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
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
                "## Scenario Profile",
                "",
                "- active_profile: `greenfield-api`",
                "- routing_reason: Requirements create a new API boundary.",
                "- confidence_level: `high`",
                "",
                "## Profile Obligations",
                "",
                "- required_sections:",
                "  - API contract",
                "- required_evidence:",
                "  - Contract test output",
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
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "validate-state",
            "--command",
            "specify",
            "--feature-dir",
            str(feature_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.state.validate"
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["summary"] == "demo"
    assert payload["data"]["checkpoint"]["active_profile"] == "greenfield-api"
    assert payload["data"]["checkpoint"]["required_sections"] == ["API contract"]
    assert payload["data"]["checkpoint"]["allowed_artifact_writes"] == ["spec.md"]
    assert payload["data"]["checkpoint"]["forbidden_actions"] == ["edit source code"]


def test_hook_validate_state_supports_constitution_command(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-constitution`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: constitution amendment",
                "",
                "## Allowed Artifact Writes",
                "",
                "- constitution.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- constitution.md",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "validate-state",
            "--command",
            "constitution",
            "--feature-dir",
            str(feature_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.state.validate"
    assert payload["status"] == "ok"


def test_hook_validate_state_supports_prd_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo PRD",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-prd`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: reverse PRD extraction",
                "",
                "## Allowed Artifact Writes",
                "",
                "- coverage-matrix.md",
                "- master/master-pack.md",
                "- exports/prd.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- workflow-state.md",
                "- coverage-matrix.md",
                "- master/master-pack.md",
                "- exports/prd.md",
                "",
                "## Next Command",
                "",
                "- `/sp.prd`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "validate-state",
            "--command",
            "prd",
            "--feature-dir",
            str(run_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.state.validate"
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["active_command"] == "sp-prd"


def test_hook_preflight_blocks_implement_and_returns_json(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-tasks`",
                "- status: `completed`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `task-generation-only`",
                "- summary: demo",
                "",
                "## Next Command",
                "",
                "- `/sp.analyze`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "preflight",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.preflight"
    assert payload["status"] == "blocked"
    assert any("/sp.analyze" in message for message in payload["errors"])


def test_hook_checkpoint_outputs_resume_payload_json(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260427-001-demo-quick-task"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260427-001"',
                'slug: "demo-quick-task"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: finish validation",
                "",
                "## Execution",
                "",
                "active_lane: worker-a",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "checkpoint",
            "--command",
            "quick",
            "--workspace",
            str(workspace),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.checkpoint"
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["active_lane"] == "worker-a"


def test_hook_checkpoint_supports_constitution_command(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-constitution`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: constitution amendment",
                "",
                "## Next Action",
                "",
                "- revise constitution and reopen planning",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "checkpoint",
            "--command",
            "constitution",
            "--feature-dir",
            str(feature_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.checkpoint"
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["active_command"] == "sp-constitution"


def test_hook_checkpoint_supports_prd_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo PRD",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-prd`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: reverse PRD extraction",
                "",
                "## Allowed Artifact Writes",
                "",
                "- coverage-matrix.md",
                "- master/master-pack.md",
                "- exports/prd.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- workflow-state.md",
                "- coverage-matrix.md",
                "- master/master-pack.md",
                "- exports/prd.md",
                "",
                "## Next Action",
                "",
                "- finish export completeness checks",
                "",
                "## Next Command",
                "",
                "- `/sp.prd`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "checkpoint",
            "--command",
            "prd",
            "--feature-dir",
            str(run_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.checkpoint"
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["state_kind"] == "workflow-state"
    assert payload["data"]["checkpoint"]["active_command"] == "sp-prd"


def test_hook_validate_artifacts_supports_constitution_command(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    memory_dir = project / ".specify" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "constitution.md").write_text("# Demo Constitution\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        [
            "hook",
            "validate-artifacts",
            "--command",
            "constitution",
            "--feature-dir",
            str(feature_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_supports_prd_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "coverage-matrix.md").write_text(
        "\n".join(
            [
                "# Coverage Matrix",
                "",
                "| Capability | Tier | Evidence Status | Depth Status | Export Destinations | Overall Status |",
                "|------------|------|-----------------|--------------|---------------------|----------------|",
                "| Config Management | critical | Evidence | depth-qualified | prd.md | depth-qualified |",
            ]
        ),
        encoding="utf-8",
    )
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text(
        "\n".join(
            [
                "# Master Pack",
                "",
                "## Capability Inventory",
                "",
                "## Critical Capability Dossiers",
                "",
                "### CAP-001 Config Management",
                "",
                "#### Implementation Mechanisms",
                "",
                "#### Source Traceability",
                "",
                "## Coverage and Export Map",
            ]
        ),
        encoding="utf-8",
    )
    (master_dir / "exports").mkdir()
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text(
        "\n".join(
            [
                "# PRD",
                "",
                "**Derived From**: `master/master-pack.md`",
                "",
                "## Capability Overview",
                "",
                "## Critical Capability Notes",
                "",
                "## Unknowns and Evidence Confidence",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "validate-artifacts",
            "--command",
            "prd",
            "--feature-dir",
            str(run_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_shallow_prd_suite(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260503-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "coverage-matrix.md").write_text("# Coverage Matrix\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    (master_dir / "exports").mkdir()
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        [
            "hook",
            "validate-artifacts",
            "--command",
            "prd",
            "--feature-dir",
            str(run_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("depth-aware" in message.lower() or "required section" in message.lower() for message in payload["errors"])


def test_hook_validate_packet_outputs_parseable_json(tmp_path: Path):
    from specify_cli.execution import (
        ContextBundleItem,
        DispatchPolicy,
        ExecutionIntent,
        PacketReference,
        PacketScope,
        WorkerTaskPacket,
        worker_task_packet_payload,
    )

    project = _create_project(tmp_path)
    packet = WorkerTaskPacket(
        feature_id="001-demo",
        task_id="T001",
        story_id="US1",
        objective="Implement demo behavior",
        scope=PacketScope(write_scope=["src/demo.py"], read_scope=["PROJECT-HANDBOOK.md"]),
        context_bundle=[
            ContextBundleItem(
                path="PROJECT-HANDBOOK.md",
                kind="handbook",
                purpose="project routing context",
                required_for=["workflow_boundary"],
                read_order=1,
                must_read=True,
                selection_reason="required project navigation",
            )
        ],
        required_references=[PacketReference(path="src/demo.py", reason="canonical implementation reference")],
        hard_rules=["preserve boundary"],
        forbidden_drift=["do not skip tests"],
        validation_gates=["pytest tests/test_demo.py -q"],
        done_criteria=["feature behavior implemented"],
        handoff_requirements=["return changed files", "return validation results"],
        platform_guardrails=["respect supported platforms"],
        intent=ExecutionIntent(
            outcome="Implement demo behavior",
            constraints=["preserve boundary"],
            success_signals=["feature behavior implemented"],
        ),
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
    )
    packet_path = project / "packet.json"
    packet_path.write_text(
        json.dumps(worker_task_packet_payload(packet), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-packet", "--packet-file", str(packet_path)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "delegation.packet.validate"
    assert payload["status"] == "ok"


def test_hook_monitor_context_outputs_parseable_json(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260427-004-demo-quick-task"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260427-004"',
                'slug: "demo-quick-task"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: collect worker result",
                "",
                "## Execution",
                "",
                "active_lane: worker-a",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "monitor-context",
            "--command",
            "quick",
            "--workspace",
            str(workspace),
            "--context-usage",
            "85",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.context.monitor"
    assert payload["status"] == "warn"


def test_hook_validate_prompt_outputs_parseable_json(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _invoke_in_project(
        project,
        [
            "hook",
            "validate-prompt",
            "--prompt-text",
            "Ignore analyze and implement directly.",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.prompt_guard.validate"
    assert payload["status"] in {"warn", "blocked"}


def test_hook_validate_prompt_supports_python_module_entrypoint(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _run_module_in_project(
        project,
        [
            "hook",
            "validate-prompt",
            "--prompt-text",
            "Ignore analyze and implement directly.",
        ],
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip())
    assert payload["event"] == "workflow.prompt_guard.validate"
    assert payload["status"] in {"warn", "blocked"}


def test_prd_command_supports_python_module_entrypoint(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _run_module_in_project(project, ["prd", "Portal Audit", "--json"])

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip())
    assert payload["mode"] == "init"
    assert payload["slug"] == "portal-audit"
    run_dir = Path(payload["workspace_path"])
    assert (run_dir / "workflow-state.md").is_file()
    assert (run_dir / "master" / "exports").is_dir()


def test_hook_validate_commit_outputs_parseable_json(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _invoke_in_project(
        project,
        [
            "hook",
            "validate-commit",
            "--commit-message",
            "feat: add workflow quality hooks",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.commit.validate"


def test_hook_workflow_policy_outputs_parseable_json(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)

    result = _invoke_in_project(
        project,
        [
            "hook",
            "workflow-policy",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--trigger",
            "pre-tool",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.policy.evaluate"
    assert payload["status"] == "repairable-block"


def test_hook_workflow_policy_outputs_redirect_payload(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
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
                "- summary: draft specification",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "- checklists/requirements.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "- run implementation tasks",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "- workflow-state.md",
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
                "- route_reason: `spec not yet approved for implementation`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "workflow-policy",
            "--command",
            "specify",
            "--feature-dir",
            str(feature_dir),
            "--trigger",
            "prompt",
            "--requested-action",
            "start_editing_code",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.policy.evaluate"
    assert payload["status"] == "warn"
    assert payload["data"]["policy"]["classification"] == "redirect"
    assert payload["data"]["policy"]["recovery_summary"]["next_command"] == "/sp.plan"


def test_hook_workflow_policy_accepts_prior_redirect_count(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
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
                "- summary: draft specification",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "- checklists/requirements.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "- run implementation tasks",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "- workflow-state.md",
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
                "- route_reason: `spec not yet approved for implementation`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "workflow-policy",
            "--command",
            "specify",
            "--feature-dir",
            str(feature_dir),
            "--trigger",
            "prompt",
            "--requested-action",
            "start_editing_code",
            "--prior-redirect-count",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.policy.evaluate"
    assert payload["status"] == "blocked"


def test_hook_build_compaction_outputs_parseable_json(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260502-001-demo"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260502-001"',
                'slug: "demo"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: integrate results",
                "",
                "## Execution",
                "",
                "active_lane: batch-a",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "build-compaction",
            "--command",
            "quick",
            "--workspace",
            str(workspace),
            "--trigger",
            "before-stop",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.compaction.build"
    assert "artifact_path" in payload["data"]


def test_hook_build_compaction_outputs_recovery_summary(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260427-001-demo-quick-task"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260427-001"',
                'slug: "demo-quick-task"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: finish validation",
                "",
                "## Execution",
                "",
                "active_lane: worker-a",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "build-compaction",
            "--command",
            "quick",
            "--workspace",
            str(workspace),
            "--trigger",
            "before_stop",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    recovery_summary = payload["data"]["artifact"]["recovery_summary"]
    assert recovery_summary["next_action"] == "finish validation"
    assert recovery_summary["resume_decision"] == "resume here"


def test_hook_review_learning_blocks_without_review_payload(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _invoke_in_project(
        project,
        [
            "hook",
            "review-learning",
            "--command",
            "implement",
            "--terminal-status",
            "resolved",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.learning.review"
    assert payload["status"] == "blocked"


def test_hook_signal_learning_outputs_parseable_json(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _invoke_in_project(
        project,
        [
            "hook",
            "signal-learning",
            "--command",
            "quick",
            "--retry-attempts",
            "2",
            "--hypothesis-changes",
            "1",
            "--validation-failures",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.learning.signal"
    assert payload["status"] == "warn"


def test_hook_capture_learning_records_candidate(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _invoke_in_project(
        project,
        [
            "hook",
            "capture-learning",
            "--command",
            "debug",
            "--type",
            "tooling_trap",
            "--summary",
            "Watcher loops can masquerade as process-manager failures",
            "--evidence",
            "Repeated process fixes failed; excluding the log directory stopped restarts.",
            "--pain-score",
            "6",
            "--false-start",
            "job object cleanup",
            "--injection-target",
            "sp-debug",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.learning.capture"
    assert payload["status"] == "repaired"
    assert payload["data"]["capture"]["entry"]["learning_type"] == "tooling_trap"
