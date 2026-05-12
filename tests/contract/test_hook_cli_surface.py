import json
import os
import re
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.hooks import artifact_validation as artifact_validation_mod

HOOK_SUBCOMMANDS = [
    "preflight",
    "validate-state",
    "validate-artifacts",
    "checkpoint",
    "validate-packet",
    "validate-result",
    "monitor-context",
    "validate-session-state",
    "render-statusline",
    "validate-read-path",
    "validate-prompt",
    "validate-boundary",
    "validate-phase-boundary",
    "validate-commit",
    "workflow-policy",
    "build-compaction",
    "read-compaction",
    "signal-learning",
    "review-learning",
    "capture-learning",
    "inject-learning",
    "mark-dirty",
    "complete-refresh",
]


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


def test_all_hook_commands_advertise_json_format_alias():
    runner = CliRunner()
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")

    for subcommand in HOOK_SUBCOMMANDS:
        result = runner.invoke(app, ["hook", subcommand, "--help"], catch_exceptions=False)
        clean_output = ansi_re.sub("", result.output)

        assert result.exit_code == 0, result.output
        assert "--format" in clean_output, f"{subcommand} is missing --format in help output"


def _write_prd_build_ready_scan_artifacts(run_dir: Path) -> None:
    for relative, content in {
        "workflow-state.md": "# Workflow State\n",
        "prd-scan.md": "# PRD Scan\n",
        "coverage-ledger.json": "{\"version\": 1, \"rows\": []}\n",
        "capability-ledger.json": (
            "{\"capabilities\": [{\"id\": \"CAP-HEAVY\", \"tier\": \"critical\", "
            "\"status\": \"reconstruction-ready\"}]}\n"
        ),
        "artifact-contracts.json": "{\"artifacts\": [{\"id\": \"ART-HEAVY\", \"status\": \"landed\"}]}\n",
        "reconstruction-checklist.json": "{\"checks\": [{\"id\": \"CHK-HEAVY\"}]}\n",
        "entrypoint-ledger.json": "{\"entrypoints\": []}\n",
        "config-contracts.json": "{\"configs\": []}\n",
        "protocol-contracts.json": "{\"protocols\": []}\n",
        "state-machines.json": "{\"machines\": []}\n",
        "error-semantics.json": "{\"errors\": []}\n",
        "verification-surfaces.json": "{\"surfaces\": []}\n",
    }.items():
        (run_dir / relative).write_text(content, encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Scan Packet\n", encoding="utf-8")
    (run_dir / "evidence").mkdir()
    (run_dir / "evidence" / "api").mkdir()
    (run_dir / "worker-results").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "paths_read": ["src/app.py"],
                "unknowns": [],
                "confidence": "high",
                "recommended_ledger_updates": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_legacy_prd_build_exports(run_dir: Path) -> None:
    master_dir = run_dir / "master"
    master_dir.mkdir(exist_ok=True)
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir(exist_ok=True)
    (exports_dir / "README.md").write_text("# Export Navigation\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")


def _write_heavy_prd_build_exports(run_dir: Path) -> None:
    _write_legacy_prd_build_exports(run_dir)
    for relative, heading in {
        "config-contracts.md": "# Config Contracts\n",
        "protocol-contracts.md": "# Protocol Contracts\n",
        "state-machines.md": "# State Machines\n",
        "error-semantics.md": "# Error Semantics\n",
        "verification-surface.md": "# Verification Surface\n",
        "reconstruction-risks.md": "# Reconstruction Risks\n",
    }.items():
        (run_dir / "exports" / relative).write_text(heading, encoding="utf-8")


def _write_project_cognition_runtime(run_dir: Path) -> None:
    for relative, content in {
        "status.json": "{\"version\": 1, \"graph_ready\": true, \"last_update_id\": \"UPD-001\"}\n",
        "coverage.json": "{\"rows\": []}\n",
        "provisional/nodes.json": "{\"nodes\": []}\n",
        "provisional/edges.json": "{\"edges\": []}\n",
        "provisional/observations.json": "{\"observations\": []}\n",
        "graph/nodes.json": "{\"nodes\": []}\n",
        "graph/edges.json": "{\"edges\": []}\n",
        "graph/claims.json": "{\"claims\": []}\n",
        "graph/conflicts.json": "{\"conflicts\": []}\n",
        "graph/updates.json": "{\"updates\": []}\n",
        "slices/change.json": "{\"slice\": {\"slice_id\": \"change\", \"slice_type\": \"change\"}}\n",
    }.items():
        target = run_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (run_dir / "evidence").mkdir(parents=True, exist_ok=True)


def test_map_build_capability_diagram_validation_accepts_project_map_prefixed_pages(tmp_path: Path):
    feature_dir = tmp_path / ".specify" / "project-cognition"
    (feature_dir / "index").mkdir(parents=True, exist_ok=True)
    (feature_dir / "modules").mkdir(parents=True, exist_ok=True)
    (feature_dir / "index" / "capabilities.json").write_text(
        json.dumps(
            {
                "capabilities": [
                    {
                        "id": "CAP-001",
                        "deep_workflow_path": ".specify/project-map/modules/capability.md",
                        "lifecycle_mermaid": "graph TD; A-->B",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (feature_dir / "modules" / "capability.md").write_text(
        "```mermaid\ngraph TD; A-->B\n```\n",
        encoding="utf-8",
    )

    assert artifact_validation_mod._validate_map_build_capability_diagrams(feature_dir) == []


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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `intent-confirmation`",
                "- current_domain: `goal-and-users`",
                "- next_action: `Confirm the current understanding summary with the user.`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
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
    assert payload["data"]["checkpoint"]["current_stage"] == "intent-confirmation"
    assert payload["data"]["checkpoint"]["current_domain"] == "goal-and-users"
    assert payload["data"]["checkpoint"]["next_action"] == "Confirm the current understanding summary with the user."
    assert payload["data"]["checkpoint"]["blocker_reason"] == "none"
    assert payload["data"]["checkpoint"]["final_handoff_decision"] == "pending"
    assert payload["data"]["checkpoint"]["allowed_artifact_writes"] == ["spec.md"]
    assert payload["data"]["checkpoint"]["forbidden_actions"] == ["edit source code"]


def test_hook_validate_state_supports_fixed_specify_lifecycle_state_shape(tmp_path: Path):
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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `question-batch`",
                "- current_domain: `goal-and-users`",
                "- next_action: `Ask the next bounded domain question batch.`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
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
    checkpoint = payload["data"]["checkpoint"]
    assert checkpoint["current_stage"] == "question-batch"
    assert checkpoint["current_domain"] == "goal-and-users"
    assert checkpoint["next_action"] == "Ask the next bounded domain question batch."
    assert checkpoint["blocker_reason"] == "none"
    assert checkpoint["final_handoff_decision"] == "pending"
    assert "active_profile" not in checkpoint
    assert "coverage_mode" not in checkpoint
    assert "observer_status" not in checkpoint


def test_hook_cli_surface_locks_fixed_specify_template_contract() -> None:
    template = (Path(__file__).resolve().parents[2] / "templates" / "workflow-state-template.md").read_text(encoding="utf-8")

    assert "## Fixed Lifecycle State" in template
    assert "## Allowed Artifact Writes" in template
    assert "## Forbidden Actions" in template
    assert "## Authoritative Files" in template
    assert "## Next Command" in template
    assert "current_stage" in template
    assert "current_domain" in template
    assert "next_action" in template
    assert "blocker_reason" in template
    assert "final_handoff_decision" in template
    assert "active_profile" not in template
    assert "coverage_mode" not in template
    assert "observer_status" not in template


def test_hook_validate_state_supports_frontmatter_fallback_via_cli(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "---",
                "active_command: sp-specify",
                "status: active",
                "phase_mode: planning-only",
                "summary: draft specification",
                "current_stage: intent-analysis",
                "current_domain: goal-and-users",
                "next_action: Refine scope.",
                "blocker_reason: none",
                "final_handoff_decision: pending",
                "allowed_artifact_writes:",
                "  - spec.md",
                "forbidden_actions:",
                "  - edit source code",
                "authoritative_files:",
                "  - spec.md",
                "next_command: /sp.plan",
                "---",
                "",
                "# Workflow State: Demo",
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
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["allowed_artifact_writes"] == ["spec.md"]


def test_hook_validate_state_autofix_repairs_missing_sections_via_cli(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    target = feature_dir / "workflow-state.md"
    target.write_text(
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
            "--autofix",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["status"] == "repaired"
    assert payload["writes"]["workflow_state"] == str(target.resolve())


def test_hook_validate_state_escapes_unicode_for_non_utf8_stdout(tmp_path: Path):
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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `intent-confirmation`",
                "- current_domain: `goal-and-users`",
                "- next_action: `Confirm the current understanding summary with the user ✅.`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
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
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    pythonpath_entries = [str(repo_root / "src")]
    if env.get("PYTHONPATH"):
        pythonpath_entries.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    env["PYTHONIOENCODING"] = "gbk"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "specify_cli",
            "hook",
            "validate-state",
            "--command",
            "specify",
            "--feature-dir",
            str(feature_dir),
        ],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "\\u2705" in result.stdout
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["next_action"] == "Confirm the current understanding summary with the user ✅."


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


def test_hook_validate_state_supports_prd_scan_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-scan"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo PRD Scan",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-prd-scan`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: reconstruction scan",
                "",
                "## Allowed Artifact Writes",
                "",
                "- prd-scan.md",
                "- coverage-ledger.json",
                "- artifact-contracts.json",
                "",
                "## Forbidden Actions",
                "",
                "- write exports",
                "",
                "## Authoritative Files",
                "",
                "- workflow-state.md",
                "- prd-scan.md",
                "- artifact-contracts.json",
                "",
                "## Next Command",
                "",
                "- `/sp.prd-build`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-state", "--command", "prd-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["active_command"] == "sp-prd-scan"


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


def test_hook_checkpoint_supports_prd_build_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo PRD Build",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-prd-build`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: reconstruction build",
                "",
                "## Allowed Artifact Writes",
                "",
                "- master/master-pack.md",
                "- exports/prd.md",
                "",
                "## Forbidden Actions",
                "",
                "- rescan repository ad hoc",
                "",
                "## Authoritative Files",
                "",
                "- workflow-state.md",
                "- master/master-pack.md",
                "- exports/prd.md",
                "",
                "## Next Command",
                "",
                "- `/sp.prd-build`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "checkpoint", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"
    assert payload["data"]["checkpoint"]["active_command"] == "sp-prd-build"


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


def test_hook_validate_artifacts_blocks_specify_when_semantic_ready_state_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "alignment.md").write_text("# Alignment\n", encoding="utf-8")
    (feature_dir / "context.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "specify", "--feature-dir", str(feature_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("specify-draft.md" in message for message in payload["errors"])


def test_hook_validate_artifacts_supports_prd_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "workflow-state.md": "# Workflow State\n",
        "prd-scan.md": "# PRD Scan\n",
        "coverage-ledger.md": "# Coverage Ledger\n",
        "coverage-ledger.json": "{\"version\": 1, \"rows\": []}\n",
        "capability-ledger.json": "{\"capabilities\": []}\n",
        "artifact-contracts.json": "{\"artifacts\": []}\n",
        "reconstruction-checklist.json": "{\"checks\": []}\n",
    }.items():
        (run_dir / relative).write_text(content, encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()

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


def test_hook_validate_artifacts_supports_prd_scan_command(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-scan"
    run_dir.mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "workflow-state.md": "# Workflow State\n",
        "prd-scan.md": "# PRD Scan\n",
        "coverage-ledger.md": "# Coverage Ledger\n",
        "coverage-ledger.json": "{\"version\": 1, \"rows\": []}\n",
        "capability-ledger.json": "{\"capabilities\": []}\n",
        "artifact-contracts.json": "{\"artifacts\": []}\n",
        "reconstruction-checklist.json": "{\"checks\": []}\n",
    }.items():
        path = run_dir / relative
        path.write_text(content, encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_map_scan_when_graph_baseline_outputs_are_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    run_dir.mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "status.json": "{\"version\": 1, \"graph_ready\": false}\n",
        "coverage.json": "{\"rows\": []}\n",
    }.items():
        (run_dir / relative).write_text(content, encoding="utf-8")
    (run_dir / "evidence").mkdir()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("provisional/nodes.json" in message for message in payload["errors"])
    assert any("provisional/edges.json" in message for message in payload["errors"])
    assert any("provisional/observations.json" in message for message in payload["errors"])


def test_hook_validate_artifacts_accepts_map_scan_when_graph_baseline_outputs_exist(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_map_scan_on_malformed_graph_shapes(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "coverage.json").write_text("{\"version\": 1}\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("coverage.json" in message and "rows" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_scan_on_malformed_status_shape(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "status.json").write_text("[]\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("status.json" in message and "top-level JSON object" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_build_when_graph_outputs_are_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    run_dir.mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "status.json": "{\"version\": 1, \"graph_ready\": false}\n",
    }.items():
        target = run_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (run_dir / "slices").mkdir()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("graph/nodes.json" in message for message in payload["errors"])
    assert any("graph/conflicts.json" in message for message in payload["errors"])


def test_hook_validate_artifacts_accepts_map_build_when_graph_outputs_exist(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_map_build_on_malformed_graph_shapes(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "graph" / "nodes.json").write_text("{\"items\": []}\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("graph/nodes.json" in message and "nodes" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_build_on_malformed_status_shape(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "status.json").write_text("[]\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("status.json" in message and "top-level JSON object" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_build_when_slices_are_empty(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    for child in (run_dir / "slices").iterdir():
        child.unlink()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("slices must contain at least one file" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_update_when_last_update_id_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "status.json").write_text("{\"version\": 1, \"graph_ready\": true}\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("last_update_id" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_update_when_changed_scope_metadata_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("changed-scope metadata" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_update_when_changed_scope_metadata_has_no_usable_paths(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "status.json").write_text(
        "{\"version\": 1, \"graph_ready\": true, \"last_update_id\": \"UPD-001\", \"stale_paths\": [\"\"]}\n",
        encoding="utf-8",
    )
    (run_dir / "graph" / "updates.json").write_text(
        "{\"updates\": [{\"update_id\": \"UPD-001\", \"changed_paths\": [null]}]}\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("changed-scope metadata" in message for message in payload["errors"])


def test_hook_validate_artifacts_accepts_map_update_when_changed_scope_metadata_exists(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "status.json").write_text(
        "{\"version\": 1, \"graph_ready\": true, \"last_update_id\": \"UPD-001\", \"stale_paths\": [\"src/app.py\"]}\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_accepts_map_update_when_update_log_supplies_changed_scope(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "status.json").write_text(
        "{\"version\": 1, \"graph_ready\": true, \"last_update_id\": \"UPD-001\", \"stale_paths\": []}\n",
        encoding="utf-8",
    )
    (run_dir / "graph" / "updates.json").write_text(
        "{\"updates\": [{\"update_id\": \"UPD-001\", \"changed_paths\": [\"src/app.py\"]}]}\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_map_update_on_malformed_graph_shape(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "status.json").write_text(
        "{\"version\": 1, \"graph_ready\": true, \"last_update_id\": \"UPD-001\", \"stale_paths\": [\"src/app.py\"]}\n",
        encoding="utf-8",
    )
    (run_dir / "graph" / "nodes.json").write_text("{\"items\": []}\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("graph/nodes.json" in message and "nodes" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_scan_on_malformed_json_shapes(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-scan-bad-shapes"
    run_dir.mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "workflow-state.md": "# Workflow State\n",
        "prd-scan.md": "# PRD Scan\n",
        "coverage-ledger.md": "# Coverage Ledger\n",
        "coverage-ledger.json": "[]\n",
        "capability-ledger.json": "{\"capabilities\": {}}\n",
        "artifact-contracts.json": "{\"artifacts\": {}}\n",
        "reconstruction-checklist.json": "{\"checks\": {}}\n",
    }.items():
        (run_dir / relative).write_text(content, encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("coverage-ledger.json" in message for message in payload["errors"])
    assert any("capability-ledger.json" in message for message in payload["errors"])
    assert any("artifact-contracts.json" in message for message in payload["errors"])
    assert any("reconstruction-checklist.json" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_shallow_prd_build(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-001\", \"tier\": \"critical\", \"status\": \"surface-only\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text("{\"artifacts\": []}\n", encoding="utf-8")
    (run_dir / "reconstruction-checklist.json").write_text("{\"checks\": []}\n", encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("critical" in message.lower() or "artifact" in message.lower() for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_build_when_scan_package_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-missing-scan"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-002\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text("{\"artifacts\": []}\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "README.md").write_text("# Export Navigation\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("prd-scan.md" in message for message in payload["errors"])
    assert any("coverage-ledger.json" in message for message in payload["errors"])
    assert any("reconstruction-checklist.json" in message for message in payload["errors"])
    assert any("scan-packets" in message for message in payload["errors"])
    assert any("evidence" in message for message in payload["errors"])
    assert any("worker-results" in message for message in payload["errors"])


def test_hook_validate_artifacts_supports_prd_build_positive_path(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-ok"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_build_ready_scan_artifacts(run_dir)
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-003\", \"tier\": \"critical\", \"status\": \"L4 Reconstruction-Ready\"}]}\n",
        encoding="utf-8",
    )
    _write_heavy_prd_build_exports(run_dir)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_prd_build_when_heavy_exports_are_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-missing-heavy-exports"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_build_ready_scan_artifacts(run_dir)
    _write_legacy_prd_build_exports(run_dir)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("exports/config-contracts.md" in message for message in payload["errors"])
    assert any("exports/protocol-contracts.md" in message for message in payload["errors"])
    assert any("exports/state-machines.md" in message for message in payload["errors"])
    assert any("exports/error-semantics.md" in message for message in payload["errors"])
    assert any("exports/verification-surface.md" in message for message in payload["errors"])
    assert any("exports/reconstruction-risks.md" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_build_when_export_navigation_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-missing-export-readme"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_build_ready_scan_artifacts(run_dir)
    _write_heavy_prd_build_exports(run_dir)
    (run_dir / "exports" / "README.md").unlink()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("exports/README.md" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_build_when_worker_result_lacks_required_fields(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-worker-result-shallow"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_build_ready_scan_artifacts(run_dir)
    _write_legacy_prd_build_exports(run_dir)
    _write_heavy_prd_build_exports(run_dir)
    (run_dir / "worker-results" / "lane-a.json").write_text("{\"status\": \"ok\"}\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any(
        "worker-results/lane-a.json" in message and "paths_read" in message for message in payload["errors"]
    )
    assert any("worker-results/lane-a.json" in message and "unknowns" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_build_when_scan_directories_are_empty(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-empty-dirs"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-006\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        "{\"artifacts\": [{\"id\": \"ART-002\", \"status\": \"landed\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text("{\"checks\": [{\"id\": \"CHK-002\"}]}\n", encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "README.md").write_text("# Export Navigation\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("scan-packets must contain at least one" in message for message in payload["errors"])
    assert any("worker-results must contain at least one" in message for message in payload["errors"])
    assert any("evidence must contain at least one" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_build_when_scan_surfaces_are_files_not_directories(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-file-surfaces"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-007\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        "{\"artifacts\": [{\"id\": \"ART-003\", \"status\": \"landed\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text("{\"checks\": [{\"id\": \"CHK-003\"}]}\n", encoding="utf-8")
    (run_dir / "scan-packets").write_text("not a dir\n", encoding="utf-8")
    (run_dir / "evidence").write_text("not a dir\n", encoding="utf-8")
    (run_dir / "worker-results").write_text("not a dir\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "README.md").write_text("# Export Navigation\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("required artifact must be a directory: scan-packets" in message for message in payload["errors"])
    assert any("required artifact must be a directory: worker-results" in message for message in payload["errors"])
    assert any("required artifact must be a directory: evidence" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_build_when_artifacts_and_checks_are_empty_arrays(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-empty-arrays"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-008\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text("{\"artifacts\": []}\n", encoding="utf-8")
    (run_dir / "reconstruction-checklist.json").write_text("{\"checks\": []}\n", encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Scan Packet\n", encoding="utf-8")
    (run_dir / "evidence").mkdir()
    (run_dir / "evidence" / "api").mkdir()
    (run_dir / "worker-results").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text("{\"status\": \"ok\"}\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "README.md").write_text("# Export Navigation\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("artifact-contracts.json must include at least one artifact" in message for message in payload["errors"])
    assert any("reconstruction-checklist.json must include at least one check" in message for message in payload["errors"])


def test_hook_validate_artifacts_allows_critical_artifact_entries_without_invented_status_gate(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-critical-artifact-entry"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_build_ready_scan_artifacts(run_dir)
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-013\", \"tier\": \"critical\", \"status\": \"L4 Reconstruction-Ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        "{\"artifacts\": [{\"id\": \"ART-009\", \"tier\": \"critical\", \"status\": \"producer-consumer-traced\"}]}\n",
        encoding="utf-8",
    )
    _write_heavy_prd_build_exports(run_dir)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_prd_build_when_artifact_contracts_top_level_is_not_object(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-invalid-json-shape"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-004\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text("[]\n", encoding="utf-8")
    (run_dir / "reconstruction-checklist.json").write_text("{\"checks\": []}\n", encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Scan Packet\n", encoding="utf-8")
    (run_dir / "evidence" / "api").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text("{\"status\": \"ok\"}\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "README.md").write_text("# Export Navigation\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("top-level json object" in message.lower() for message in payload["errors"])


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
    assert any("missing required artifact" in message.lower() for message in payload["errors"])
    assert any("prd-scan.md" in message or "coverage-ledger.json" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_scan_when_json_artifact_path_is_directory(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-scan-json-dir"
    run_dir.mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "workflow-state.md": "# Workflow State\n",
        "prd-scan.md": "# PRD Scan\n",
        "coverage-ledger.md": "# Coverage Ledger\n",
        "capability-ledger.json": "{\"capabilities\": []}\n",
        "artifact-contracts.json": "{\"artifacts\": []}\n",
        "reconstruction-checklist.json": "{\"checks\": []}\n",
    }.items():
        (run_dir / relative).write_text(content, encoding="utf-8")
    (run_dir / "coverage-ledger.json").mkdir()
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-scan", "--feature-dir", str(run_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("required artifact must be a file: coverage-ledger.json" in message for message in payload["errors"])


def test_prd_init_workspace_supports_compatibility_artifact_validation(tmp_path: Path):
    project = _create_project(tmp_path)

    init_result = _run_module_in_project(project, ["prd", "Portal Audit", "--json"])

    assert init_result.returncode == 0, init_result.stderr or init_result.stdout
    init_payload = json.loads(init_result.stdout.strip())
    run_dir = Path(init_payload["workspace_path"])

    validate_result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd", "--feature-dir", str(run_dir)],
    )

    assert validate_result.exit_code == 0, validate_result.output
    validate_payload = json.loads(validate_result.output.strip())
    assert validate_payload["event"] == "workflow.artifacts.validate"
    assert validate_payload["status"] == "ok"


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


def test_implement_resume_audit_cli_blocks_false_resolved_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n\n## Next Command\n\n- `/sp.implement`\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: resolved",
                "feature: 001-demo",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "current_batch: final",
                "next_action: report completion",
                "",
                "## Open Gaps",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["implement", "resume-audit", "--feature-dir", str(feature_dir), "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "fail"
    assert payload["recommended_tracker_status"] == "validating"


def test_validate_session_state_surfaces_terminal_audit_required(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n\n## Next Command\n\n- `/sp.implement`\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: resolved",
                "feature: 001-demo",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "current_batch: final",
                "next_action: report completion",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-session-state", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "warn"
    audit = payload["data"]["resume_audit"]
    assert audit["resume_classification"] == "terminal-audit-required"
    assert audit["trusted_terminal_state"] is False


def test_implement_closeout_blocks_false_resolved_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n\n## Next Command\n\n- `/sp.implement`\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "---\nstatus: resolved\nfeature: 001-demo\nresume_decision: resolved\n---\n\n## Current Focus\nnext_action: report completion\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["implement", "closeout", "--feature-dir", str(feature_dir), "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert payload["resume_audit"]["trusted_terminal_state"] is False


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
    assert (run_dir / "prd-scan.md").is_file()


def test_prd_scan_command_supports_python_module_entrypoint(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _run_module_in_project(project, ["prd-scan", "Portal Audit", "--json"])

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip())
    assert payload["mode"] == "init-scan"
    assert payload["slug"] == "portal-audit"
    run_dir = Path(payload["workspace_path"])
    assert (run_dir / "workflow-state.md").is_file()
    assert (run_dir / "prd-scan.md").is_file()


def test_prd_build_command_supports_python_module_entrypoint(tmp_path: Path):
    project = _create_project(tmp_path)
    run_id = "260504-portal-audit"
    run_dir = project / ".specify" / "prd-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-005\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        "{\"artifacts\": [{\"id\": \"ART-007\", \"status\": \"landed\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text(
        "{\"checks\": [{\"id\": \"CHK-007\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "entrypoint-ledger.json").write_text("{\"entrypoints\": []}\n", encoding="utf-8")
    (run_dir / "config-contracts.json").write_text("{\"configs\": []}\n", encoding="utf-8")
    (run_dir / "protocol-contracts.json").write_text("{\"protocols\": []}\n", encoding="utf-8")
    (run_dir / "state-machines.json").write_text("{\"machines\": []}\n", encoding="utf-8")
    (run_dir / "error-semantics.json").write_text("{\"errors\": []}\n", encoding="utf-8")
    (run_dir / "verification-surfaces.json").write_text("{\"surfaces\": []}\n", encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Scan Packet\n", encoding="utf-8")
    (run_dir / "evidence" / "api").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "paths_read": ["src/app.py"],
                "unknowns": [],
                "confidence": "high",
                "recommended_ledger_updates": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "README.md").write_text("# Export Navigation\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")
    (exports_dir / "config-contracts.md").write_text("# Config Contracts\n", encoding="utf-8")
    (exports_dir / "protocol-contracts.md").write_text("# Protocol Contracts\n", encoding="utf-8")
    (exports_dir / "state-machines.md").write_text("# State Machines\n", encoding="utf-8")
    (exports_dir / "error-semantics.md").write_text("# Error Semantics\n", encoding="utf-8")
    (exports_dir / "verification-surface.md").write_text("# Verification Surface\n", encoding="utf-8")
    (exports_dir / "reconstruction-risks.md").write_text("# Reconstruction Risks\n", encoding="utf-8")

    result = _run_module_in_project(project, ["prd-build", run_id, "--json"])

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip())
    assert payload["mode"] == "status-build"
    assert payload["workspace"] == run_id
    assert payload["complete"] is True
    assert payload["surfaces"]["master_pack"] is True
    assert payload["surfaces"]["prd_export"] is True


def test_prd_build_command_json_entrypoint_reports_incomplete_readiness(tmp_path: Path):
    project = _create_project(tmp_path)
    run_id = "260504-portal-audit-incomplete"
    run_dir = project / ".specify" / "prd-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-012\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        "{\"artifacts\": [{\"id\": \"ART-008\", \"status\": \"landed\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text(
        "{\"checks\": [{\"id\": \"CHK-008\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "scan-packets").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Scan Packet\n", encoding="utf-8")
    (run_dir / "evidence").mkdir()
    (run_dir / "evidence" / "api").mkdir()
    (run_dir / "worker-results").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text("{\"status\": \"ok\"}\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")

    result = _run_module_in_project(project, ["prd-build", run_id, "--json"])

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip())
    assert payload["mode"] == "status-build"
    assert payload["workspace"] == run_id
    assert payload["complete"] is False
    assert "reconstruction_appendix" in payload["missing"]
    assert "data_model" in payload["missing"]
    assert "integration_contracts" in payload["missing"]
    assert "runtime_behaviors" in payload["missing"]
    assert payload["surfaces"]["reconstruction_appendix"] is False
    assert payload["surfaces"]["data_model"] is False
    assert payload["surfaces"]["integration_contracts"] is False
    assert payload["surfaces"]["runtime_behaviors"] is False


def test_prd_command_help_marks_compatibility_only(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _run_module_in_project(project, ["prd", "--help"])

    assert result.returncode == 0, result.stderr or result.stdout
    help_text = result.stdout
    assert "Deprecated compatibility entrypoint" in help_text
    assert "prd-scan" in help_text
    assert "prd-build" in help_text
    assert "heavy reconstruction" in help_text.lower()
    assert "L4 Reconstruction-Ready" in help_text
    assert "subagent-mandatory" in help_text
    assert "config-contracts.json" in help_text


def test_prd_build_command_help_mentions_build_only_reconstruction_contract(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _run_module_in_project(project, ["prd-build", "--help"])

    assert result.returncode == 0, result.stderr or result.stdout
    help_text = result.stdout
    normalized = " ".join(help_text.lower().split())
    assert "heavy reconstruction" in normalized
    assert "second repository scan" in normalized
    assert "critical evidence" in normalized or "critical-evidence" in normalized


def test_hook_validate_artifacts_blocks_prd_build_when_critical_capability_is_not_reconstruction_ready(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-not-ready"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-009\", \"tier\": \"critical\", \"status\": \"depth-qualified\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        "{\"artifacts\": [{\"id\": \"ART-004\", \"status\": \"landed\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text("{\"checks\": [{\"id\": \"CHK-004\"}]}\n", encoding="utf-8")
    (run_dir / "entrypoint-ledger.json").write_text("{\"entrypoints\": []}\n", encoding="utf-8")
    (run_dir / "config-contracts.json").write_text("{\"configs\": []}\n", encoding="utf-8")
    (run_dir / "protocol-contracts.json").write_text("{\"protocols\": []}\n", encoding="utf-8")
    (run_dir / "state-machines.json").write_text("{\"machines\": []}\n", encoding="utf-8")
    (run_dir / "error-semantics.json").write_text("{\"errors\": []}\n", encoding="utf-8")
    (run_dir / "verification-surfaces.json").write_text("{\"surfaces\": []}\n", encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Scan Packet\n", encoding="utf-8")
    (run_dir / "evidence").mkdir()
    (run_dir / "evidence" / "api").mkdir()
    (run_dir / "worker-results").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "paths_read": ["src/app.py"],
                "unknowns": [],
                "confidence": "high",
                "recommended_ledger_updates": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "README.md").write_text("# Export Navigation\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")
    (exports_dir / "config-contracts.md").write_text("# Config Contracts\n", encoding="utf-8")
    (exports_dir / "protocol-contracts.md").write_text("# Protocol Contracts\n", encoding="utf-8")
    (exports_dir / "state-machines.md").write_text("# State Machines\n", encoding="utf-8")
    (exports_dir / "error-semantics.md").write_text("# Error Semantics\n", encoding="utf-8")
    (exports_dir / "verification-surface.md").write_text("# Verification Surface\n", encoding="utf-8")
    (exports_dir / "reconstruction-risks.md").write_text("# Reconstruction Risks\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("reconstruction-ready" in message for message in payload["errors"])
    assert any("depth-qualified" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_build_when_required_file_artifact_is_directory(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-file-path-dir"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-010\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        "{\"artifacts\": [{\"id\": \"ART-005\", \"status\": \"landed\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text("{\"checks\": [{\"id\": \"CHK-005\"}]}\n", encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Scan Packet\n", encoding="utf-8")
    (run_dir / "evidence").mkdir()
    (run_dir / "evidence" / "api").mkdir()
    (run_dir / "worker-results").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text("{\"status\": \"ok\"}\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").mkdir()
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").mkdir()
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("required artifact must be a file: master/master-pack.md" in message for message in payload["errors"])
    assert any("required artifact must be a file: exports/prd.md" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_prd_build_when_secondary_export_paths_are_directories(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-demo-prd-build-secondary-export-dirs"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text("{\"version\": 1, \"rows\": []}\n", encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-011\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        "{\"artifacts\": [{\"id\": \"ART-006\", \"status\": \"landed\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text("{\"checks\": [{\"id\": \"CHK-006\"}]}\n", encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "scan-packets" / "lane-a.md").write_text("# Scan Packet\n", encoding="utf-8")
    (run_dir / "evidence").mkdir()
    (run_dir / "evidence" / "api").mkdir()
    (run_dir / "worker-results").mkdir()
    (run_dir / "worker-results" / "lane-a.json").write_text("{\"status\": \"ok\"}\n", encoding="utf-8")
    master_dir = run_dir / "master"
    master_dir.mkdir()
    (master_dir / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").mkdir()
    (exports_dir / "data-model.md").mkdir()
    (exports_dir / "integration-contracts.md").mkdir()
    (exports_dir / "runtime-behaviors.md").mkdir()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "prd-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("required artifact must be a file: exports/reconstruction-appendix.md" in message for message in payload["errors"])
    assert any("required artifact must be a file: exports/data-model.md" in message for message in payload["errors"])
    assert any("required artifact must be a file: exports/integration-contracts.md" in message for message in payload["errors"])
    assert any("required artifact must be a file: exports/runtime-behaviors.md" in message for message in payload["errors"])


def test_prd_scan_command_json_entrypoint_reports_mode_appropriate_completion(tmp_path: Path):
    project = _create_project(tmp_path)

    init_result = _run_module_in_project(project, ["prd-scan", "Portal Audit", "--json"])

    assert init_result.returncode == 0, init_result.stderr or init_result.stdout
    init_payload = json.loads(init_result.stdout.strip())
    assert init_payload["mode"] == "init-scan"
    surfaces = init_payload["surfaces"]
    assert surfaces["prd_scan"] is True
    assert surfaces["master_pack"] is False
    assert surfaces["prd_export"] is False


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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `question-batch`",
                "- current_domain: `goal-and-users`",
                "- next_action: `refine scope`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `question-batch`",
                "- current_domain: `goal-and-users`",
                "- next_action: `refine scope`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
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


def test_hook_workflow_policy_uses_persisted_redirect_count_when_flag_omitted(tmp_path: Path):
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
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `question-batch`",
                "- current_domain: `goal-and-users`",
                "- next_action: `refine scope`",
                "- blocker_reason: `none`",
                "- final_handoff_decision: `pending`",
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

    first = _invoke_in_project(
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

    assert first.exit_code == 0, first.output
    first_payload = json.loads(first.output.strip())
    assert first_payload["event"] == "workflow.policy.evaluate"
    assert first_payload["status"] == "warn"

    second = _invoke_in_project(
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

    assert second.exit_code == 0, second.output
    second_payload = json.loads(second.output.strip())
    assert second_payload["event"] == "workflow.policy.evaluate"
    assert second_payload["status"] == "blocked"


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


def test_hook_review_learning_accepts_json_format_alias(tmp_path: Path):
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
            "--format",
            "json",
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


def test_hook_complete_refresh_accepts_json_format_alias(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _invoke_in_project(
        project,
        [
            "hook",
            "complete-refresh",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "project_cognition.complete_refresh"
    assert payload["status"] == "blocked"


def test_project_map_preflight_support_drift_copy_does_not_route_to_map_update(tmp_path: Path, monkeypatch):
    project = _create_project(tmp_path)
    (project / ".specify" / "integration.json").write_text(
        json.dumps({"integration": "codex"}),
        encoding="utf-8",
    )

    def support_drift(_project_root: Path, *, command_name: str = "") -> dict[str, object]:
        return {
            "freshness": "support_drift",
            "state": "support_drift",
            "readiness": "blocked",
            "recommended_next_action": "commit_or_ignore_support_files",
            "status_path": str(project / ".specify" / "project-map" / "index" / "status.json"),
            "reasons": ["tool-managed support surface changed: .specify/templates/runtime-config.template.json"],
            "changed_files": [".specify/templates/runtime-config.template.json"],
            "must_refresh_topics": [],
            "review_topics": [],
        }

    monkeypatch.setattr("specify_cli.inspect_project_cognition_freshness_for_command", support_drift)

    result = _invoke_in_project(project, ["sp-teams", "--dispatch", "REQ-001"])

    assert result.exit_code == 1
    assert "support" in result.output.lower()
    assert "sp-map-update" not in result.output.lower()


def test_project_map_preflight_partial_refresh_copy_explains_refresh_recorded_but_not_ready(tmp_path: Path, monkeypatch):
    project = _create_project(tmp_path)
    (project / ".specify" / "integration.json").write_text(
        json.dumps({"integration": "codex"}),
        encoding="utf-8",
    )

    def partial_refresh(_project_root: Path, *, command_name: str = "") -> dict[str, object]:
        return {
            "freshness": "partial_refresh",
            "state": "partial_refresh",
            "readiness": "blocked",
            "recommended_next_action": "run_map_update",
            "status_path": str(project / ".specify" / "project-map" / "index" / "status.json"),
            "reasons": ["Project cognition refresh data was recorded, but runtime readiness is still blocked for the touched area."],
            "changed_files": ["src/routes/api.ts"],
            "must_refresh_topics": ["INTEGRATIONS.md"],
            "review_topics": ["ARCHITECTURE.md"],
        }

    monkeypatch.setattr("specify_cli.inspect_project_cognition_freshness_for_command", partial_refresh)

    result = _invoke_in_project(project, ["sp-teams", "--dispatch", "REQ-001"])

    assert result.exit_code == 1
    assert "refresh data was recorded" in result.output.lower()
    assert "still blocked" in result.output.lower()


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
