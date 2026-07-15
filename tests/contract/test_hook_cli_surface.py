import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.hooks import artifact_validation as artifact_validation_mod
from tests.project_cognition_fake import install_fake_project_cognition, write_project_cognition_status

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


@pytest.fixture(autouse=True)
def _fake_project_cognition_tool(monkeypatch, tmp_path: Path) -> None:
    install_fake_project_cognition(monkeypatch, tmp_path)


def _invoke_in_project(project: Path, args: list[str]):
    runner = CliRunner()
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)
    return result


def _run_module_in_project(project: Path, args: list[str], input_text: str | None = None):
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
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_hook_packetized_implement_review_state(
    feature_dir: Path,
    *,
    task_brief: str = "implementation-review/task-briefs/T001.md",
    review_package: str = "implementation-review/review-packages/T001.md",
    task_review: str = "implementation-review/task-reviews/T001.json",
    write_task_brief: bool = True,
    write_review_package: bool = True,
    write_task_review: bool = True,
    branch_review: bool = True,
) -> None:
    if write_task_brief:
        task_brief_path = feature_dir / "implementation-review/task-briefs/T001.md"
        task_brief_path.parent.mkdir(parents=True, exist_ok=True)
        task_brief_path.write_text("# T001 Brief\n", encoding="utf-8")
    if write_review_package:
        review_package_path = feature_dir / "implementation-review/review-packages/T001.md"
        review_package_path.parent.mkdir(parents=True, exist_ok=True)
        review_package_path.write_text("# T001 Review Package\n", encoding="utf-8")
    if write_task_review:
        task_review_path = feature_dir / "implementation-review/task-reviews/T001.json"
        task_review_path.parent.mkdir(parents=True, exist_ok=True)
        task_review_path.write_text(
            json.dumps(
                {
                    "task_id": "T001",
                    "spec_verdict": "pass",
                    "quality_verdict": "pass",
                    "final_assessment": "accepted",
                }
            )
            + "\n",
            encoding="utf-8",
        )
    review_dir = feature_dir / "implementation-review"
    review_dir.mkdir(parents=True, exist_ok=True)
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_brief": task_brief,
                        "review_package": review_package,
                        "task_review": task_review,
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    if branch_review:
        (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")


def _write_hook_packetized_implement_feature(feature_dir: Path) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")


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
        "coverage-ledger.json": (
            '{"version":1,"rows":[{"surface":"src/app.py","status":"covered",'
            '"evidence":["evidence/api.md"]}]}\n'
        ),
        "capability-ledger.json": (
            "{\"capabilities\": [{\"id\": \"CAP-HEAVY\", \"tier\": \"critical\", "
            "\"status\": \"reconstruction-ready\"}]}\n"
        ),
        "artifact-contracts.json": "{\"artifacts\": [{\"id\": \"ART-HEAVY\", \"status\": \"landed\"}]}\n",
        "reconstruction-checklist.json": (
            '{"checks":[{"id":"CHK-HEAVY","status":"pass"}]}\n'
        ),
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
    (run_dir / "evidence" / "api.md").write_text("API evidence\n", encoding="utf-8")
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
    (master_dir / "master-pack.md").write_text(
        "# Master Pack\n\nAccepted capability evidence.\n", encoding="utf-8"
    )
    exports_dir = run_dir / "exports"
    exports_dir.mkdir(exist_ok=True)
    (exports_dir / "README.md").write_text("# Export Navigation\n\nSee the PRD suite.\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text(
        "# PRD\n\n## Capability Overview\n\nCore capability.\n\n"
        "## Critical Capability Notes\n\nEvidence accepted.\n\n"
        "## Unknowns and Evidence Confidence\n\nNo critical unknowns.\n",
        encoding="utf-8",
    )
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n\nReconstruction detail.\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n\nEntity contract.\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n\nAPI contract.\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n\nRuntime behavior.\n", encoding="utf-8")


def _write_heavy_prd_build_exports(run_dir: Path) -> None:
    _write_legacy_prd_build_exports(run_dir)
    (run_dir / "workflow-state.md").write_text(
        "# Workflow State\n\n## Current Command\n\n"
        "- active_command: sp-prd-build\n- status: complete\n"
        "- build_status: complete\n",
        encoding="utf-8",
    )
    for relative, heading in {
        "config-contracts.md": "# Config Contracts\n",
        "protocol-contracts.md": "# Protocol Contracts\n",
        "state-machines.md": "# State Machines\n",
        "error-semantics.md": "# Error Semantics\n",
        "verification-surface.md": "# Verification Surface\n",
        "reconstruction-risks.md": "# Reconstruction Risks\n",
    }.items():
        (run_dir / "exports" / relative).write_text(
            heading + "\nAccepted contract detail.\n", encoding="utf-8"
        )


def _write_project_cognition_runtime(run_dir: Path) -> None:
    project_root = run_dir.parent.parent
    generation_id = "GEN-0001"
    run_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(run_dir / "project-cognition.db") as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS generations(id TEXT PRIMARY KEY, sequence INTEGER NOT NULL, kind TEXT NOT NULL, state TEXT NOT NULL, source_commit TEXT NOT NULL, started_at TEXT NOT NULL, published_at TEXT NOT NULL, superseded_at TEXT NOT NULL, attrs_json TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY, generation_id TEXT NOT NULL, source_kind TEXT NOT NULL, source_path TEXT NOT NULL, commit_sha TEXT NOT NULL, span TEXT NOT NULL, extractor TEXT NOT NULL, content_hash TEXT NOT NULL, captured_at TEXT NOT NULL, attrs_json TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, generation_id TEXT NOT NULL, observation_type TEXT NOT NULL, summary TEXT NOT NULL, attrs_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS observation_evidence(observation_id TEXT NOT NULL, evidence_id TEXT NOT NULL, PRIMARY KEY(observation_id, evidence_id));
            CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY, generation_id TEXT NOT NULL, type TEXT NOT NULL, title TEXT NOT NULL, confidence TEXT NOT NULL, attrs_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS node_evidence(node_id TEXT NOT NULL, evidence_id TEXT NOT NULL, PRIMARY KEY(node_id, evidence_id));
            CREATE TABLE IF NOT EXISTS edges(id TEXT PRIMARY KEY, generation_id TEXT NOT NULL, type TEXT NOT NULL, source_id TEXT NOT NULL, target_id TEXT NOT NULL, confidence TEXT NOT NULL, attrs_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS edge_evidence(edge_id TEXT NOT NULL, evidence_id TEXT NOT NULL, PRIMARY KEY(edge_id, evidence_id));
            CREATE TABLE IF NOT EXISTS alias_index(id TEXT PRIMARY KEY, generation_id TEXT NOT NULL, alias TEXT NOT NULL, normalized_alias TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT NOT NULL, language TEXT NOT NULL, source TEXT NOT NULL, confidence TEXT NOT NULL, evidence_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS path_index(id TEXT PRIMARY KEY, generation_id TEXT NOT NULL, path TEXT NOT NULL, node_id TEXT NOT NULL, relation TEXT NOT NULL, confidence TEXT NOT NULL, evidence_id TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS updates(id TEXT PRIMARY KEY, generation_id TEXT NOT NULL, trigger TEXT NOT NULL, changed_paths_json TEXT NOT NULL, affected_nodes_json TEXT NOT NULL, affected_claims_json TEXT NOT NULL, affected_slices_json TEXT NOT NULL, result_state TEXT NOT NULL, completed_at TEXT NOT NULL, attrs_json TEXT NOT NULL DEFAULT '{}');
            """
        )
        conn.execute("INSERT OR REPLACE INTO metadata(key, value_json, updated_at) VALUES('runtime_format', '\"project-cognition-go\"', '2026-05-23T00:00:00Z')")
        conn.execute("INSERT OR REPLACE INTO metadata(key, value_json, updated_at) VALUES('runtime_schema', '2', '2026-05-23T00:00:00Z')")
        conn.execute("INSERT OR REPLACE INTO metadata(key, value_json, updated_at) VALUES('schema_version', '3', '2026-05-23T00:00:00Z')")
        conn.execute(
            "INSERT OR REPLACE INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json) VALUES(?, 1, 'full', 'active', 'abc123', '2026-05-23T00:00:00Z', '2026-05-23T00:00:00Z', '', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES('E-login', ?, 'source', 'src/auth/login.ts', 'abc123', '', 'test', 'hash', '2026-05-23T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) VALUES('capability:auth.login', ?, 'capability', 'Login', 'verified', '{}', '2026-05-23T00:00:00Z', '2026-05-23T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES('P-login', ?, 'src/auth/login.ts', 'capability:auth.login', 'owns', 'verified', 'E-login', '2026-05-23T00:00:00Z')",
            (generation_id,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) VALUES('ALIAS-login', ?, 'Login', 'login', 'node', 'capability:auth.login', 'en', 'node_title', 'verified', '')",
            (generation_id,),
        )
        conn.commit()
    workbench = run_dir / "workbench"
    (workbench / "worker-results").mkdir(parents=True, exist_ok=True)
    (workbench / "capability-ledger.json").write_text('{"rows":[]}\n', encoding="utf-8")
    (workbench / "control-ledger.json").write_text('{"rows":[]}\n', encoding="utf-8")
    (workbench / "coverage-ledger.json").write_text('{"rows":[],"open_gaps":[]}\n', encoding="utf-8")
    write_project_cognition_status(
        project_root,
        status="ok",
        freshness="fresh",
        state="fresh",
        readiness="query_ready",
        recommended_next_action="use_project_cognition",
        graph_ready=True,
        active_generation_id=generation_id,
        query_contract_version=1,
        update_contract_version=1,
    )


def _write_project_cognition_scan_artifacts(run_dir: Path) -> None:
    (run_dir / "evidence").mkdir(parents=True, exist_ok=True)
    (run_dir / "evidence" / "E-001.json").write_text('{"id": "E-001"}\n', encoding="utf-8")
    for relative, content in {
        "coverage.json": "{\"rows\": [{\"path\": \"src/auth/login.ts\", \"criticality\": \"critical\"}]}\n",
        "provisional/nodes.json": "{\"nodes\": [{\"id\": \"capability:auth.login\"}]}\n",
        "provisional/edges.json": "{\"edges\": []}\n",
        "provisional/observations.json": "{\"observations\": [{\"id\": \"OBS-001\"}]}\n",
        "workbench/coverage-ledger.json": (
            "{\"rows\": [{\"path\": \"src/auth/login.ts\", \"criticality\": \"critical\", "
            "\"coverage_state\": \"covered\"}], \"open_gaps\": []}\n"
        ),
        "workbench/scan-queue.json": (
            "{\"packets\": [{\"packet_id\": \"core\", \"state\": \"accepted\", "
            "\"assigned_paths\": [\"src/auth/login.ts\"], "
            "\"result_handoff_path\": \".specify/project-cognition/workbench/worker-results/core.json\", "
            "\"next_action\": \"none\"}]}\n"
        ),
        "workbench/handoff-ledger.json": (
            "{\"events\": ["
            "{\"event_id\": \"dispatch-core\", \"packet_id\": \"core\", \"event_type\": \"dispatched\"}, "
            "{\"event_id\": \"return-core\", \"packet_id\": \"core\", \"event_type\": \"returned\", "
            "\"worker_result_path\": \".specify/project-cognition/workbench/worker-results/core.json\"}"
            "]}\n"
        ),
    }.items():
        target = run_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    packets_dir = run_dir / "workbench" / "scan-packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    (packets_dir / "core.md").write_text("# Core scan packet\n", encoding="utf-8")
    worker_results_dir = run_dir / "workbench" / "worker-results"
    worker_results_dir.mkdir(parents=True, exist_ok=True)
    (worker_results_dir / "core.json").write_text(
        json.dumps(
            {
                "packet_id": "core",
                "assigned_paths": ["src/auth/login.ts"],
                "paths_read": ["src/auth/login.ts"],
                "coverage": [
                    {
                        "path": "src/auth/login.ts",
                        "outcome": "deep_read",
                        "evidence_ids": ["E-001"],
                        "confidence": "high",
                    }
                ],
                "acceptance": "pass",
                "confidence": "high",
                "evidence_ids": ["E-001"],
                "ledger": _project_cognition_packet_ledger(),
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _project_cognition_packet_ledger() -> dict[str, list[object]]:
    return {
        "todo": [],
        "doing": [],
        "done": [
            {
                "path": "src/auth/login.ts",
                "coverage_state": "covered",
                "evidence_ids": ["E-001"],
                "confidence": "high",
            }
        ],
        "blocked": [],
        "overflow": [],
    }


def _write_project_cognition_worker_result(run_dir: Path, payload: dict[str, object]) -> None:
    worker_result_path = run_dir / "workbench" / "worker-results" / "core.json"
    worker_result_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _invoke_map_scan_artifact_validation(project: Path, run_dir: Path):
    return _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )


def _update_project_cognition_status(run_dir: Path, **updates: object) -> None:
    status_path = run_dir / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload.update(updates)
    status_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


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

    assert "## Stage State" in template
    assert "## Review State" in template
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


def test_hook_validate_state_implement_json_includes_implementation_review(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: validating",
                "feature: 001-demo",
                "resume_decision: continue",
                "---",
                "",
                "## Current Focus",
                "current_batch: final",
                "next_action: review implementation artifacts",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-state", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"
    review = payload["data"]["implementation_review"]
    assert review["ledger"] == str((feature_dir / "implementation-review" / "ledger.json").resolve())
    assert review["branch_review"] == str((feature_dir / "implementation-review" / "branch-review.md").resolve())


def test_hook_validate_state_implement_blocked_json_includes_implementation_review(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: validating",
                "feature: 001-demo",
                "resume_decision: continue",
                "---",
                "",
                "## Current Focus",
                "current_batch: final",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-state", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert payload["data"]["checkpoint"]["state_kind"] == "implement-tracker"
    review = payload["data"]["implementation_review"]
    ledger = Path(review["ledger"])
    branch_review = Path(review["branch_review"])
    assert ledger.is_absolute()
    assert branch_review.is_absolute()
    assert ledger == (feature_dir / "implementation-review" / "ledger.json").resolve()
    assert branch_review == (feature_dir / "implementation-review" / "branch-review.md").resolve()


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


def test_hook_validate_artifacts_blocks_implement_when_tracker_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("implement-tracker.md" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_missing_review_ledger(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("implementation-review/ledger.json" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_malformed_packet_json(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text("{not-json}\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("task-packets/T001.json" in message and "malformed packet JSON" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_non_object_packet(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('["T001"]\n', encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("task-packets/T001.json" in message and "packet must be a JSON object" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_missing_packet_task_id(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text("{}\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("task-packets/T001.json" in message and "malformed packet task_id" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_non_string_packet_task_id(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":123}\n', encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("task-packets/T001.json" in message and "malformed packet task_id" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_packet_task_id_mismatch(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T999"}\n', encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("task-packets/T001.json" in message and "task_id mismatch" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_blank_packet_task_id(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"   "}\n', encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("task-packets/T001.json" in message and "malformed packet task_id" in message for message in payload["errors"])


def test_hook_validate_artifacts_allows_checked_implement_tasks_without_packets(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx",
                "- [X] T002 [US1] Wire provider form validation in apps/web/src/Form.tsx",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_extra_unknown_packetized_implement_task(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T999.json").write_text('{"task_id":"T999"}\n', encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("T999" in message and "not checked" in message for message in payload["errors"])


def test_hook_validate_artifacts_allows_mixed_implement_tasks_when_only_packetized_task_is_reviewed(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx",
                "- [X] T002 [US1] Wire provider form validation in apps/web/src/Form.tsx",
                "",
            ]
        ),
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    (review_dir / "task-briefs").mkdir(parents=True)
    (review_dir / "task-briefs" / "T001.md").write_text("# T001 Brief\n", encoding="utf-8")
    (review_dir / "review-packages").mkdir(parents=True)
    (review_dir / "review-packages" / "T001.md").write_text(
        "# T001 Review Package\n",
        encoding="utf-8",
    )
    (review_dir / "task-reviews").mkdir(parents=True)
    (review_dir / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_brief": "implementation-review/task-briefs/T001.md",
                        "review_package": "implementation-review/review-packages/T001.md",
                        "task_review": "implementation-review/task-reviews/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_unchecked_known_packetized_implement_task(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx",
                "- [ ] T002 [US1] Wire provider form validation in apps/web/src/Form.tsx",
                "",
            ]
        ),
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    (packets_dir / "T002.json").write_text('{"task_id":"T002"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    (review_dir / "task-reviews").mkdir(parents=True)
    (review_dir / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": "implementation-review/task-reviews/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("T002" in message and "not checked" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_malformed_review_ledger(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    review_dir.mkdir()
    (review_dir / "ledger.json").write_text("[]\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("implementation-review/ledger.json" in message for message in payload["errors"])
    assert any("top-level JSON object" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_ledger_tasks_not_array(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    review_dir.mkdir()
    (review_dir / "ledger.json").write_text('{"tasks": {}}\n', encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("implementation-review/ledger.json" in message for message in payload["errors"])
    assert any("tasks array" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_non_accepted_ledger_task(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    review_dir.mkdir()
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "review_pending",
                        "task_review": "implementation-review/task-reviews/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("implementation-review/ledger.json" in message for message in payload["errors"])
    assert any("status accepted" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_missing_task_review_file(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    review_dir.mkdir()
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": "implementation-review/task-reviews/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("implementation-review/task-reviews/T001.json" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_missing_task_brief_file(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_hook_packetized_implement_feature(feature_dir)
    _write_hook_packetized_implement_review_state(feature_dir, write_task_brief=False)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any(
        "implementation-review/task-briefs/T001.md" in message and "missing" in message
        for message in payload["errors"]
    )


def test_hook_validate_artifacts_blocks_packetized_implement_non_canonical_task_brief_path(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_hook_packetized_implement_feature(feature_dir)
    _write_hook_packetized_implement_review_state(
        feature_dir,
        task_brief="implementation-review/./task-briefs/T001.md",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any(
        "T001" in message and "implementation-review/task-briefs/T001.md" in message
        for message in payload["errors"]
    )


def test_hook_validate_artifacts_blocks_packetized_implement_missing_review_package_file(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_hook_packetized_implement_feature(feature_dir)
    _write_hook_packetized_implement_review_state(feature_dir, write_review_package=False)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any(
        "implementation-review/review-packages/T001.md" in message and "missing" in message
        for message in payload["errors"]
    )


def test_hook_validate_artifacts_blocks_packetized_implement_non_canonical_review_package_path(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_hook_packetized_implement_feature(feature_dir)
    _write_hook_packetized_implement_review_state(
        feature_dir,
        review_package="implementation-review/review-packages/../review-packages/T001.md",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any(
        "T001" in message and "implementation-review/review-packages/T001.md" in message
        for message in payload["errors"]
    )


def test_hook_validate_artifacts_blocks_packetized_implement_rejected_task_review(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    (review_dir / "task-briefs").mkdir(parents=True)
    (review_dir / "task-briefs" / "T001.md").write_text("# T001 Brief\n", encoding="utf-8")
    (review_dir / "review-packages").mkdir(parents=True)
    (review_dir / "review-packages" / "T001.md").write_text(
        "# T001 Review Package\n",
        encoding="utf-8",
    )
    (review_dir / "task-reviews").mkdir(parents=True)
    (review_dir / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "fail",
                "quality_verdict": "pass",
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": "implementation-review/task-reviews/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any(
        "T001" in message
        and "implementation-review/task-reviews/T001.json" in message
        and "not accepted" in message
        for message in payload["errors"]
    )


def test_hook_validate_artifacts_blocks_packetized_implement_malformed_task_review(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    (review_dir / "task-reviews").mkdir(parents=True)
    (review_dir / "task-reviews" / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": "implementation-review/task-reviews/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any(
        "T001" in message
        and "implementation-review/task-reviews/T001.json" in message
        and "malformed" in message
        for message in payload["errors"]
    )


def test_hook_validate_artifacts_blocks_packetized_implement_non_canonical_task_review_path(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    (review_dir / "task-reviews").mkdir(parents=True)
    (review_dir / "task-reviews" / "T001.json").write_text(
        json.dumps({"task_id": "T001", "final_assessment": "accepted"}) + "\n",
        encoding="utf-8",
    )
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": "implementation-review/./task-reviews/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("implementation-review/task-reviews/T001.json" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_packetized_implement_missing_branch_review(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    (review_dir / "task-briefs").mkdir(parents=True)
    (review_dir / "task-briefs" / "T001.md").write_text("# T001 Brief\n", encoding="utf-8")
    (review_dir / "review-packages").mkdir(parents=True)
    (review_dir / "review-packages" / "T001.md").write_text(
        "# T001 Review Package\n",
        encoding="utf-8",
    )
    (review_dir / "task-reviews").mkdir(parents=True)
    (review_dir / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_review": "implementation-review/task-reviews/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.artifacts.validate"
    assert payload["status"] == "blocked"
    assert any("implementation-review/branch-review.md" in message for message in payload["errors"])


def test_hook_validate_artifacts_accepts_packetized_implement_with_accepted_reviews(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text("# Implement Tracker\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n",
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    (review_dir / "task-briefs").mkdir(parents=True)
    (review_dir / "task-briefs" / "T001.md").write_text("# T001 Brief\n", encoding="utf-8")
    (review_dir / "review-packages").mkdir(parents=True)
    (review_dir / "review-packages" / "T001.md").write_text(
        "# T001 Review Package\n",
        encoding="utf-8",
    )
    (review_dir / "task-reviews").mkdir(parents=True)
    (review_dir / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_brief": "implementation-review/task-briefs/T001.md",
                        "review_package": "implementation-review/review-packages/T001.md",
                        "task_review": "implementation-review/task-reviews/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "implement", "--feature-dir", str(feature_dir)],
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
    assert any("spec-contract.json" in message for message in payload["errors"])


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
    assert not any(message.startswith("missing required artifact:") for message in payload["errors"])
    assert any("provisional/nodes.json" in message for message in payload["errors"])
    assert any("provisional/edges.json" in message for message in payload["errors"])
    assert any("provisional/observations.json" in message for message in payload["errors"])
    assert any("scan-queue.json" in message for message in payload["errors"])
    assert any("handoff-ledger.json" in message for message in payload["errors"])


def test_hook_validate_artifacts_accepts_map_scan_when_graph_baseline_outputs_exist(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


@pytest.mark.parametrize("outcome", ["pass"])
def test_hook_validate_artifacts_accepts_map_scan_worker_result_legacy_top_level_outcome(
    tmp_path: Path, outcome: str
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": ["src/auth/login.ts"],
            "paths_read": ["src/auth/login.ts"],
            "coverage": [
                {
                    "path": "src/auth/login.ts",
                    "outcome": "deep_read",
                    "evidence_ids": ["E-001"],
                    "confidence": "high",
                }
            ],
            "outcome": outcome,
            "confidence": "high",
            "evidence_ids": ["E-001"],
            "ledger": _project_cognition_packet_ledger(),
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


@pytest.mark.parametrize(
    ("field", "acceptance"),
    [
        ("acceptance", "overflow"),
        ("acceptance", "blocked"),
        ("acceptance", "repack_required"),
        ("acceptance", "accepted"),
        ("acceptance", "unknown"),
        ("outcome", "unknown"),
    ],
)
def test_hook_validate_artifacts_blocks_map_scan_worker_result_invalid_packet_acceptance(
    tmp_path: Path, field: str, acceptance: str
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": ["src/auth/login.ts"],
            "paths_read": ["src/auth/login.ts"],
            "coverage": [{"path": "src/auth/login.ts", "outcome": "covered"}],
            field: acceptance,
            "ledger": _project_cognition_packet_ledger(),
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert f"packet core has invalid acceptance {acceptance}" in payload["errors"]


@pytest.mark.parametrize("acceptance", ["fail_gap", "fail_quality", "fail_contract", "fail_systemic"])
def test_hook_validate_artifacts_blocks_map_scan_worker_result_failed_packet_acceptance(
    tmp_path: Path, acceptance: str
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": ["src/auth/login.ts"],
            "paths_read": ["src/auth/login.ts"],
            "coverage": [{"path": "src/auth/login.ts", "outcome": "covered"}],
            "acceptance": acceptance,
            "ledger": _project_cognition_packet_ledger(),
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert f"packet core failed acceptance/coverage gate with {acceptance}" in payload["errors"]


def test_hook_validate_artifacts_blocks_map_scan_worker_result_missing_packet_ledger(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": ["src/auth/login.ts"],
            "paths_read": ["src/auth/login.ts"],
            "coverage": [{"path": "src/auth/login.ts", "outcome": "covered"}],
            "acceptance": "pass",
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert "packet core must define ledger object" in payload["errors"]


def test_hook_validate_artifacts_blocks_map_scan_worker_result_legacy_ledger_updates_only(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": ["src/auth/login.ts"],
            "paths_read": ["src/auth/login.ts"],
            "coverage": [
                {
                    "path": "src/auth/login.ts",
                    "outcome": "deep_read",
                    "evidence_ids": ["E-001"],
                    "confidence": "high",
                }
            ],
            "acceptance": "pass",
            "confidence": "high",
            "ledger_updates": _project_cognition_packet_ledger(),
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert "packet core must define ledger object" in payload["errors"]


def test_hook_validate_artifacts_accepts_map_scan_worker_result_packet_local_ledger_alias(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": ["src/auth/login.ts"],
            "paths_read": ["src/auth/login.ts"],
            "coverage": [
                {
                    "path": "src/auth/login.ts",
                    "outcome": "deep_read",
                    "evidence_ids": ["E-001"],
                    "confidence": "high",
                }
            ],
            "acceptance": "pass",
            "confidence": "high",
            "packet_local_ledger": _project_cognition_packet_ledger(),
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_map_scan_worker_result_without_matching_queue_row(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "scan-queue.json").write_text('{"packets": []}\n', encoding="utf-8")

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert "worker result core has no matching scan-queue row" in payload["errors"]


def test_hook_validate_artifacts_blocks_map_scan_worker_result_without_matching_handoff_return(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "handoff-ledger.json").write_text(
        (
            '{"events": ['
            '{"event_id": "dispatch-core", "packet_id": "core", "event_type": "dispatched"}'
            "]}\n"
        ),
        encoding="utf-8",
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert "worker result core has no matching return event in handoff-ledger.json" in payload["errors"]


def test_hook_validate_artifacts_blocks_map_scan_numeric_path_values(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "scan-queue.json").write_text(
        json.dumps(
            {
                "packets": [
                    {
                        "packet_id": "core",
                        "state": "accepted",
                        "assigned_paths": [123],
                        "result_handoff_path": ".specify/project-cognition/workbench/worker-results/core.json",
                        "next_action": "none",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": [123],
            "paths_read": [123],
            "coverage": [
                {
                    "path": 123,
                    "outcome": "deep_read",
                    "evidence_ids": ["E-001"],
                    "confidence": "high",
                }
            ],
            "acceptance": "pass",
            "confidence": "high",
            "evidence_ids": ["E-001"],
            "ledger": {
                "todo": [],
                "doing": [],
                "done": [
                    {
                        "path": 123,
                        "coverage_state": "covered",
                        "evidence_ids": ["E-001"],
                        "confidence": "high",
                    }
                ],
                "blocked": [],
                "overflow": [],
            },
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("scan-queue packet core assigned_paths[0] path must be a string" in message for message in payload["errors"])
    assert any("worker result core assigned_paths[0] path must be a string" in message for message in payload["errors"])
    assert any("packet core coverage[0].path must be a string" in message for message in payload["errors"])
    assert any("packet core ledger.done[0] path must be a string" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_scan_missing_expected_worker_result(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "worker-results" / "core.json").unlink()

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert (
        "scan-queue packet core result_handoff_path references missing worker result "
        ".specify/project-cognition/workbench/worker-results/core.json"
    ) in payload["errors"]
    assert (
        "handoff-ledger return for packet core worker_result_path references missing worker result "
        ".specify/project-cognition/workbench/worker-results/core.json"
    ) in payload["errors"]


def test_hook_validate_artifacts_blocks_map_scan_pass_packet_without_assigned_path_closure(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": ["src/auth/login.ts"],
            "paths_read": ["src/auth/login.ts"],
            "coverage": [],
            "acceptance": "pass",
            "confidence": "high",
            "ledger": {
                "todo": [],
                "doing": [],
                "done": [],
                "blocked": [],
                "overflow": [],
            },
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert "packet core assigned path src/auth/login.ts has no declared final outcome" in payload["errors"]
    assert "packet core assigned path src/auth/login.ts is missing from packet-local ledger" in payload["errors"]
    assert "packet core cannot pass with unresolved path src/auth/login.ts" in payload["errors"]


def test_hook_validate_artifacts_blocks_map_scan_pass_packet_without_paths_read(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": ["src/auth/login.ts"],
            "coverage": [
                {
                    "path": "src/auth/login.ts",
                    "outcome": "deep_read",
                    "evidence_ids": ["E-001"],
                    "confidence": "high",
                }
            ],
            "acceptance": "pass",
            "confidence": "high",
            "evidence_ids": ["E-001"],
            "ledger": _project_cognition_packet_ledger(),
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert "packet core pass acceptance must include non-empty paths_read" in payload["errors"]


def test_hook_validate_artifacts_blocks_map_scan_leader_only_coverage(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "coverage.json").write_text(
        json.dumps({"rows": [{"path": "src/auth/login.ts"}, {"path": "src/auth/forgotten.ts"}]}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "workbench" / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "rows": [
                    {"path": "src/auth/login.ts", "coverage_state": "covered"},
                    {"path": "src/auth/forgotten.ts", "coverage_state": "covered"},
                ],
                "open_gaps": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "workbench" / "repository-universe.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "candidate_universe": [
                    {"path": "src/auth/login.ts", "disposition": "deep_read", "decision_source": "git"},
                    {"path": "src/auth/forgotten.ts", "disposition": "deep_read", "decision_source": "git"},
                ],
                "included_paths": ["src/auth/login.ts", "src/auth/forgotten.ts"],
                "excluded_paths": [],
                "ambiguous_paths": [],
                "dispositions": {
                    "src/auth/login.ts": "deep_read",
                    "src/auth/forgotten.ts": "deep_read",
                },
                "criticality": {
                    "src/auth/login.ts": "critical",
                    "src/auth/forgotten.ts": "important",
                },
                "classification_reasons": {
                    "src/auth/login.ts": "source",
                    "src/auth/forgotten.ts": "source",
                },
                "decision_source": {
                    "src/auth/login.ts": "git",
                    "src/auth/forgotten.ts": "git",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert (
        "repository-universe included path src/auth/forgotten.ts has coverage row "
        "but no scan packet assignment or accepted nonblocking gap"
    ) in payload["errors"]


def test_hook_validate_artifacts_blocks_map_scan_cross_packet_worker_coverage(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "scan-packets" / "lane-1.md").write_text("# Lane 1\n", encoding="utf-8")
    (run_dir / "workbench" / "scan-packets" / "lane-2.md").write_text("# Lane 2\n", encoding="utf-8")
    (run_dir / "workbench" / "scan-packets" / "core.md").unlink()
    (run_dir / "workbench" / "scan-queue.json").write_text(
        json.dumps(
            {
                "packets": [
                    {
                        "packet_id": "lane-1",
                        "state": "accepted",
                        "assigned_paths": ["src/auth/login.ts"],
                        "result_handoff_path": ".specify/project-cognition/workbench/worker-results/lane-1.json",
                    },
                    {
                        "packet_id": "lane-2",
                        "state": "accepted",
                        "assigned_paths": ["src/auth/login.ts"],
                        "result_handoff_path": ".specify/project-cognition/workbench/worker-results/lane-2.json",
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "workbench" / "handoff-ledger.json").write_text(
        json.dumps(
            {
                "events": [
                    {"event_id": "dispatch-1", "packet_id": "lane-1", "event_type": "dispatched"},
                    {
                        "event_id": "return-1",
                        "packet_id": "lane-1",
                        "event_type": "returned",
                        "worker_result_path": ".specify/project-cognition/workbench/worker-results/lane-1.json",
                    },
                    {"event_id": "dispatch-2", "packet_id": "lane-2", "event_type": "dispatched"},
                    {
                        "event_id": "return-2",
                        "packet_id": "lane-2",
                        "event_type": "returned",
                        "worker_result_path": ".specify/project-cognition/workbench/worker-results/lane-2.json",
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "workbench" / "worker-results" / "core.json").unlink()
    (run_dir / "workbench" / "worker-results" / "lane-1.json").write_text(
        json.dumps(
            {
                "packet_id": "lane-1",
                "assigned_paths": ["src/auth/login.ts"],
                "paths_read": ["src/auth/login.ts"],
                "coverage": [],
                "acceptance": "pass",
                "confidence": "high",
                "ledger": _project_cognition_packet_ledger(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "workbench" / "worker-results" / "lane-2.json").write_text(
        json.dumps(
            {
                "packet_id": "lane-2",
                "assigned_paths": ["src/auth/login.ts"],
                "paths_read": ["src/auth/login.ts"],
                "coverage": [
                    {
                        "path": "src/auth/login.ts",
                        "outcome": "deep_read",
                        "evidence_ids": ["E-001"],
                        "confidence": "high",
                    }
                ],
                "acceptance": "pass",
                "confidence": "high",
                "ledger": _project_cognition_packet_ledger(),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert (
        "scan-queue packet lane-1 accepted state requires worker result coverage for assigned path src/auth/login.ts"
        in payload["errors"]
    )


@pytest.mark.parametrize("state", ["overflow", "blocked", "repack_required"])
def test_hook_validate_artifacts_blocks_map_scan_queue_continuation_state_without_gap_or_child_packet(
    tmp_path: Path, state: str
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "scan-queue.json").write_text(
        json.dumps(
            {
                "packets": [
                    {
                        "packet_id": "core",
                        "state": state,
                        "assigned_paths": ["src/auth/login.ts"],
                        "result_handoff_path": ".specify/project-cognition/workbench/worker-results/core.json",
                        "next_action": state,
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert f"scan-queue packet core state {state} must have an open coverage gap or child continuation packet" in payload[
        "errors"
    ]


def test_hook_validate_artifacts_blocks_map_scan_worker_result_path_level_overflow_without_acceptance(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    _write_project_cognition_worker_result(
        run_dir,
        {
            "packet_id": "core",
            "assigned_paths": ["src/auth/login.ts"],
            "paths_read": ["src/auth/login.ts"],
            "coverage": [{"path": "src/auth/login.ts", "outcome": "overflow"}],
        },
    )

    result = _invoke_map_scan_artifact_validation(project, run_dir)

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert "packet core must define acceptance" in payload["errors"]


def test_hook_validate_artifacts_accepts_map_scan_downstream_compatibility_shapes(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    page_path = "desktop/src/pages/ActiveSession.tsx"
    (run_dir / "evidence" / "E-001.json").write_text(
        json.dumps(
            {
                "id": "E-001",
                "source_path": page_path,
                "attrs_json": {"language": "tsx"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "provisional" / "nodes.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "node_id": "NO_ID",
                        "kind": "page",
                        "label": "Active Session Page",
                        "attrs_json": {"path": page_path},
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "provisional" / "edges.json").write_text(
        json.dumps(
            {
                "edges": [
                    {
                        "id": "NO_ID",
                        "kind": "owns",
                        "source_node_id": page_path,
                        "target_node_id": page_path,
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "provisional" / "observations.json").write_text(
        json.dumps({"observations": ["Active session page owns session UI state"]}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "coverage.json").write_text(
        json.dumps({"coverage": [{"path": page_path}]}) + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_map_scan_when_specify_paths_enter_graph_evidence(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "coverage.json").write_text(
        '{"rows": [{"path": ".specify/memory/project-rules.md", "criticality": "critical"}]}\n',
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any(".specify/** must not enter project cognition graph evidence" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_scan_when_excluded_paths_enter_coverage(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "repository-universe.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "candidate_universe": [
                    {"path": "src/auth/login.ts", "disposition": "deep_read", "decision_source": "git"},
                    {"path": " ./vendor\\lib.go ", "disposition": "excluded", "decision_source": ".cognitionignore"},
                ],
                "included_paths": ["src/auth/login.ts"],
                "excluded_paths": [
                    {"path": " ./vendor\\lib.go ", "reason": "vendor", "decision_source": ".cognitionignore"}
                ],
                "ambiguous_paths": [],
                "dispositions": {"src/auth/login.ts": "deep_read", "vendor/lib.go": "excluded"},
                "classification_reasons": {"src/auth/login.ts": "source", "vendor/lib.go": "vendor"},
                "decision_source": {"src/auth/login.ts": "git", "vendor/lib.go": ".cognitionignore"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "coverage.json").write_text(
        json.dumps({"rows": [{"path": "vendor/lib.go", "criticality": "excluded"}]}) + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("excluded path vendor/lib.go must not appear in coverage.json" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_scan_on_malformed_repository_universe(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "repository-universe.json").write_text("{broken\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert ".specify/project-cognition/workbench/repository-universe.json: malformed JSON" in payload["errors"]


def test_hook_validate_artifacts_blocks_map_scan_when_specify_paths_enter_evidence_files(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "evidence" / "E-specify.json").write_text(
        '{"id": "E-specify", "source_path": ".specify/memory/project-rules.md"}\n',
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any(".specify/** must not enter project cognition graph evidence" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_scan_on_malformed_graph_shapes(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
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
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "status.json").write_text("[]\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("status.json" in message and "top-level JSON object" in message for message in payload["errors"])


def test_map_scan_artifact_validation_blocks_subagent_blocked_gap(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _write_project_cognition_scan_artifacts(run_dir)
    (run_dir / "workbench" / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "version": 1,
                "rows": [
                    {
                        "path": "src/auth/login.ts",
                        "criticality": "critical",
                        "coverage_state": "blocked",
                    }
                ],
                "open_gaps": [
                    {
                        "reason": "subagent_blocked",
                        "lane_id": "scan-auth",
                        "packet_id": "packet-auth",
                        "blocked_scope": ["src/auth"],
                        "criticality": "critical",
                        "owner": "map-scan",
                        "status": "blocked",
                        "recovery_condition": "rerun scan-auth packet",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-scan", "--feature-dir", str(run_dir)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert any("subagent_blocked" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_build_when_sqlite_database_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "status.json").write_text('{"version": 3, "graph_ready": true}\n', encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert not any(message.startswith("missing required artifact:") for message in payload["errors"])
    assert any("project-cognition.db" in message for message in payload["errors"])


def test_hook_validate_artifacts_accepts_map_build_when_sqlite_database_exists(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_blocks_map_build_when_path_index_sparse_for_included_paths(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "workbench" / "repository-universe.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "included_paths": ["src/auth/login.ts", "src/billing.ts"],
                "excluded_paths": [],
                "criticality": {
                    "src/auth/login.ts": "critical",
                    "src/billing.ts": "low_risk",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any(
        "path_index_to_included_ratio 0.50 is below hard threshold 0.70" in message
        for message in payload["errors"]
    )


def test_hook_validate_artifacts_blocks_map_build_when_only_unrelated_extra_rows_make_path_index_look_dense(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    generation_id = "GEN-0001"
    with sqlite3.connect(run_dir / "project-cognition.db") as conn:
        for index in range(1, 4):
            conn.execute(
                "INSERT OR REPLACE INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES(?, ?, ?, 'capability:auth.login', 'owns', 'verified', 'E-login', '2026-05-23T00:00:00Z')",
                (f"P-extra-{index}", generation_id, f"src/extra-{index}.ts"),
            )
        conn.commit()
    (run_dir / "workbench" / "repository-universe.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "included_paths": ["src/auth/login.ts", "src/billing.ts", "src/orders.ts"],
                "excluded_paths": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any(
        "path_index_to_included_ratio 0.33 is below hard threshold 0.70" in message
        for message in payload["errors"]
    )


def test_hook_validate_artifacts_blocks_map_build_when_important_path_missing_even_if_ratio_dense(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    generation_id = "GEN-0001"
    with sqlite3.connect(run_dir / "project-cognition.db") as conn:
        for path in ["src/orders.ts", "src/reports.ts"]:
            conn.execute(
                "INSERT OR REPLACE INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES(?, ?, ?, 'capability:auth.login', 'owns', 'verified', 'E-login', '2026-05-23T00:00:00Z')",
                (f"P-{path}", generation_id, path),
            )
        conn.commit()
    (run_dir / "workbench" / "repository-universe.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "included_paths": ["src/auth/login.ts", "src/billing.ts", "src/orders.ts", "src/reports.ts"],
                "excluded_paths": [],
                "criticality": {
                    "src/auth/login.ts": "critical",
                    "src/billing.ts": "important",
                    "src/orders.ts": "low_risk",
                    "src/reports.ts": "low_risk",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert "important_missing_path_index: src/billing.ts" in payload["errors"]


def test_hook_validate_artifacts_excludes_accepted_nonblocking_gaps_from_path_index_denominator(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "workbench" / "repository-universe.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "included_paths": ["src/auth/login.ts", "src/billing.ts"],
                "excluded_paths": [],
                "criticality": {
                    "src/auth/login.ts": "critical",
                    "src/billing.ts": "low_risk",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "workbench" / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "rows": [
                    {"path": "src/auth/login.ts", "coverage_state": "covered"},
                ],
                "open_gaps": [
                    {
                        "path": "src/billing.ts",
                        "status": "low_risk_open_gap",
                        "coverage_state": "low_risk_open_gap",
                        "owner": "scan",
                        "reason": "generated_code",
                        "evidence_expectation": "generated file remains low-risk inventory",
                        "revisit_condition": "path changes",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_keeps_loose_accepted_gap_in_path_index_denominator(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "workbench" / "repository-universe.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "included_paths": ["src/auth/login.ts", "src/billing.ts"],
                "excluded_paths": [],
                "criticality": {
                    "src/auth/login.ts": "critical",
                    "src/billing.ts": "low_risk",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "workbench" / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "rows": [
                    {"path": "src/auth/login.ts", "coverage_state": "covered"},
                    {"path": "src/billing.ts", "coverage_state": "accepted_gap"},
                ],
                "open_gaps": [
                    {
                        "path": "src/billing.ts",
                        "status": "accepted",
                        "reason": "generated_code",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any(
        "path_index_to_included_ratio 0.50 is below hard threshold 0.70" in message
        for message in payload["errors"]
    )


def test_hook_validate_artifacts_keeps_non_low_risk_accepted_gap_in_path_index_denominator(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "workbench" / "repository-universe.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "included_paths": ["src/auth/login.ts", "src/billing.ts"],
                "excluded_paths": [],
                "criticality": {
                    "src/auth/login.ts": "critical",
                    "src/billing.ts": "important",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "workbench" / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "rows": [{"path": "src/auth/login.ts", "coverage_state": "covered"}],
                "open_gaps": [
                    {
                        "path": "src/billing.ts",
                        "status": "low_risk_open_gap",
                        "coverage_state": "low_risk_open_gap",
                        "owner": "scan",
                        "reason": "generated_code",
                        "evidence_expectation": "generated file remains low-risk inventory",
                        "revisit_condition": "path changes",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any(
        "path_index_to_included_ratio 0.50 is below hard threshold 0.70" in message
        for message in payload["errors"]
    )


def test_map_build_artifact_validation_blocks_subagent_blocked_gap(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    ledger_path = run_dir / "workbench" / "coverage-ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(
            {
                "version": 1,
                "rows": [
                    {
                        "path": "src/auth/login.ts",
                        "criticality": "critical",
                        "coverage_state": "blocked",
                    }
                ],
                "open_gaps": [
                    {
                        "reason": "subagent_blocked",
                        "lane_id": "scan-auth",
                        "packet_id": "packet-auth",
                        "blocked_scope": ["src/auth"],
                        "criticality": "critical",
                        "owner": "map-build",
                        "status": "blocked",
                        "recovery_condition": "rerun scan-auth packet",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert any("subagent_blocked" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_build_when_database_is_not_query_ready(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "status.json").write_text(
        '{"version": 3, "graph_ready": true, "freshness": "fresh", '
        '"graph_store_path": ".specify/project-cognition/project-cognition.db", '
        '"active_generation_id": "GEN-0001", "query_contract_version": 1, "update_contract_version": 1}\n',
        encoding="utf-8",
    )
    (run_dir / "project-cognition.db").write_bytes(b"SQLite test database marker")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("project-cognition.db" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_build_when_fake_db_is_schema_v1(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)

    with sqlite3.connect(run_dir / "project-cognition.db") as conn:
        conn.execute(
            "UPDATE metadata SET value_json = '1' WHERE key IN ('schema_version', 'runtime_schema')"
        )
        conn.commit()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("schema_version" in message for message in payload["errors"])
    assert any("run_map_scan_build" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_build_when_specify_paths_enter_graph_store(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)

    with sqlite3.connect(run_dir / "project-cognition.db") as conn:
        generation_id = conn.execute("SELECT id FROM generations WHERE state = 'active'").fetchone()[0]
        conn.execute(
            "INSERT OR REPLACE INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES ('E-specify', ?, 'source', '.specify/memory/project-rules.md', 'abc123', '', 'test', 'hash-specify', '2026-05-23T00:00:00Z', '{}')",
            (generation_id,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES ('P-specify', ?, '.specify/memory/project-rules.md', 'capability:auth.login', 'owns', 'verified', 'E-specify', '2026-05-23T00:00:00Z')",
            (generation_id,),
        )
        conn.commit()

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any(".specify/** must not enter project cognition graph store" in message for message in payload["errors"])


def test_hook_validate_artifacts_blocks_map_build_when_sqlite_database_is_empty(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    (run_dir / "project-cognition.db").write_bytes(b"")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-build", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("project-cognition.db" in message and "must not be empty" in message for message in payload["errors"])


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
    assert any("result_state" in message for message in payload["errors"])


def test_hook_validate_artifacts_rejects_map_update_with_freshness_only(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("result_state" in message for message in payload["errors"])


def test_hook_validate_artifacts_accepts_map_update_with_ready_result_state(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _update_project_cognition_status(
        run_dir,
        version=1,
        freshness="fresh",
        readiness="query_ready",
        last_update_id="UPD-001",
        last_update_outcome="ready",
        recommended_next_action="use_project_cognition",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_accepts_map_update_when_status_records_partial_refresh(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _update_project_cognition_status(
        run_dir,
        freshness="partial_refresh",
        last_update_id="UPD-001",
        last_update_outcome="partial_refresh",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


def test_hook_validate_artifacts_rejects_map_update_with_last_update_id_only(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _update_project_cognition_status(run_dir, version=1, last_update_id="UPD-001", stale_paths=["src/app.py"])

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("result_state" in message for message in payload["errors"])


def test_hook_validate_artifacts_accepts_map_update_without_graph_json_runtime(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _update_project_cognition_status(run_dir, last_update_id="UPD-001", last_update_outcome="no_op")

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"


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
    (run_dir / "workflow-state.md").write_text(
        "# Workflow State\n\n## Current Command\n\n"
        "- active_command: sp-prd-build\n- status: complete\n"
        "- build_status: complete\n",
        encoding="utf-8",
    )
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text(
        '{"version":1,"rows":[{"surface":"src/app.py","status":"covered",'
        '"evidence":["evidence/api.md"]}]}\n',
        encoding="utf-8",
    )
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


def test_implement_closeout_blocks_readable_nonterminal_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n\n## Next Command\n\n- `/sp.implement`\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "- [ ] T001 Validate protected pipeline\n", encoding="utf-8"
    )
    (feature_dir / "implement-tracker.md").write_text(
        "---\nstatus: validating\nfeature: 001-demo\nresume_decision: continue\n---\n\n"
        "## Current Focus\nnext_action: collect protected pipeline evidence\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["implement", "closeout", "--feature-dir", str(feature_dir), "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert payload["resume_audit"]["status"] == "pass"
    assert payload["resume_audit"]["trusted_terminal_state"] is False


def test_hook_validate_commit_accepts_external_evidence_checkpoint_option(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implement-tracker.md").write_text(
        "---\nstatus: validating\nfeature: 001-demo\nresume_decision: continue\n---\n\n"
        "## Current Focus\nnext_action: run pipeline\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T001 Run protected CI\n", encoding="utf-8"
    )
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "blocked",
                "blockers": [
                    {
                        "classification": "external",
                        "owner": "external-system",
                        "evidence": "protected CI requires a commit",
                        "exact_next_action": "run protected CI",
                        "approval_question": None,
                        "unblock_criteria": "protected CI succeeds",
                        "implementation_can_continue": True,
                        "completion_impact": "mandatory_for_completion",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "validate-commit",
            "--commit-message",
            "chore(ci): checkpoint protected pipeline config",
            "--feature-dir",
            str(feature_dir),
            "--commit-intent",
            "external-evidence-checkpoint",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["workflow_finalized"] is False


def test_implement_closeout_writes_user_facing_summary(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n\n## Current Command\n\n- status: `completed`\n\n## Next Command\n\n- `/sp.implement`\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "- [X] T001 [US1] Wire demo CLI route in src/specify_cli/demo.py\n",
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
                "current_batch: final validation",
                "next_action: report completion",
                "",
                "## Open Gaps",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "status": "success",
  "changed_files": ["src/specify_cli/demo.py", "tests/test_demo.py"],
  "validation_results": [
    {"command": "pytest tests/test_demo.py -q", "status": "passed", "output": "1 passed"}
  ],
  "consumer_evidence": [
    {
      "kind": "real_entrypoint",
      "entrypoint": "specify demo",
      "producer": "demo command",
      "transformer": "Typer command dispatch",
      "consumer": "CLI invocation",
      "boundary_or_executor": "CliRunner",
      "validation": "pytest tests/test_demo.py -q"
    }
  ],
  "summary": "Wired the demo CLI route and regression coverage"
}
""".strip(),
        encoding="utf-8",
    )
    packets_dir = feature_dir / "task-packets"
    packets_dir.mkdir()
    (packets_dir / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    (review_dir / "task-briefs").mkdir(parents=True)
    (review_dir / "task-briefs" / "T001.md").write_text("# T001 Brief\n", encoding="utf-8")
    (review_dir / "review-packages").mkdir(parents=True)
    (review_dir / "review-packages" / "T001.md").write_text(
        "# T001 Review Package\n",
        encoding="utf-8",
    )
    (review_dir / "task-reviews").mkdir(parents=True)
    (review_dir / "task-reviews" / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "spec_verdict": "pass",
                "quality_verdict": "pass",
                "final_assessment": "accepted",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "ledger.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T001",
                        "status": "accepted",
                        "task_brief": "implementation-review/task-briefs/T001.md",
                        "review_package": "implementation-review/review-packages/T001.md",
                        "task_review": "implementation-review/task-reviews/T001.json",
                        "worker_result": "worker-results/T001.json",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "branch-review.md").write_text("# Branch Review\n\nAccepted.\n", encoding="utf-8")

    result = _invoke_in_project(
        project,
        ["implement", "closeout", "--feature-dir", str(feature_dir), "--format", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    summary = payload["implementation_summary"]
    assert summary["status"] == "ok"
    assert summary["report_path"].endswith(".specify/features/001-demo/implementation-summary.md")
    assert summary["completed_work"][0]["summary"] == "Wired the demo CLI route and regression coverage"
    assert "src/specify_cli/demo.py" in summary["changed_paths"]["from_worker_results"]
    assert "git diff --stat HEAD" in summary["baseline_comparison"]["commands"]
    assert summary["review_artifacts"]["ledger"].endswith(
        ".specify/features/001-demo/implementation-review/ledger.json"
    )
    assert summary["review_artifacts"]["branch_review"].endswith(
        ".specify/features/001-demo/implementation-review/branch-review.md"
    )
    assert summary["completed_work"][0]["review_artifacts"]["task_review"].endswith(
        ".specify/features/001-demo/implementation-review/task-reviews/T001.json"
    )
    report_path = feature_dir / "implementation-summary.md"
    assert report_path.is_file()
    report = report_path.read_text(encoding="utf-8")
    assert "## What Changed" in report
    assert "## How To Verify" in report
    assert "## Version Comparison" in report
    assert "## Review Artifacts" in report


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


def test_validate_prompt_accepts_stdin_payload(tmp_path: Path, monkeypatch):
    project = _create_project(tmp_path)
    monkeypatch.chdir(project)

    prompt = "implement directly and skip tests"
    result = CliRunner().invoke(
        app,
        ["hook", "validate-prompt", "--prompt-stdin"],
        input=prompt,
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["event"] == "workflow.prompt_guard.validate"
    assert payload["status"] == "blocked"
    assert "prompt attempts" in payload["errors"][0]


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


def test_hook_validate_prompt_module_entrypoint_accepts_stdin_payload(tmp_path: Path):
    project = _create_project(tmp_path)

    result = _run_module_in_project(
        project,
        [
            "hook",
            "validate-prompt",
            "--prompt-stdin",
        ],
        input_text="implement directly and skip tests",
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
    (run_dir / "workflow-state.md").write_text(
        "# Workflow State\n\n## Current Command\n\n"
        "- active_command: sp-prd-build\n- status: complete\n"
        "- build_status: complete\n",
        encoding="utf-8",
    )
    (run_dir / "prd-scan.md").write_text("# PRD Scan\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text(
        '{"version":1,"rows":[{"surface":"src/app.py","status":"covered",'
        '"evidence":["evidence/api.md"]}]}\n',
        encoding="utf-8",
    )
    (run_dir / "capability-ledger.json").write_text(
        "{\"capabilities\": [{\"id\": \"CAP-005\", \"tier\": \"critical\", \"status\": \"reconstruction-ready\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        "{\"artifacts\": [{\"id\": \"ART-007\", \"status\": \"landed\"}]}\n",
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text(
        '{"checks":[{"id":"CHK-007","status":"pass"}]}\n',
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
    (run_dir / "evidence" / "api.md").write_text("API evidence\n", encoding="utf-8")
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
    (master_dir / "master-pack.md").write_text("# Master Pack\n\nAccepted evidence.\n", encoding="utf-8")
    exports_dir = run_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "README.md").write_text("# Export Navigation\n\nSee package.\n", encoding="utf-8")
    (exports_dir / "prd.md").write_text(
        "# PRD\n\n## Capability Overview\n\nCore capability.\n\n"
        "## Critical Capability Notes\n\nEvidence accepted.\n\n"
        "## Unknowns and Evidence Confidence\n\nNo critical unknowns.\n",
        encoding="utf-8",
    )
    for relative, heading in {
        "reconstruction-appendix.md": "Appendix",
        "data-model.md": "Data Model",
        "integration-contracts.md": "Integration Contracts",
        "runtime-behaviors.md": "Runtime Behaviors",
        "config-contracts.md": "Config Contracts",
        "protocol-contracts.md": "Protocol Contracts",
        "state-machines.md": "State Machines",
        "error-semantics.md": "Error Semantics",
        "verification-surface.md": "Verification Surface",
        "reconstruction-risks.md": "Reconstruction Risks",
    }.items():
        (exports_dir / relative).write_text(
            f"# {heading}\n\nAccepted contract detail.\n", encoding="utf-8"
        )

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


def test_hook_complete_refresh_blocks_without_query_ready_runtime(tmp_path: Path):
    project = _create_project(tmp_path)
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, check=True)
    (project / "README.md").write_text("# Test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "Initial test commit"], cwd=project, check=True, capture_output=True, text=True)

    result = _invoke_in_project(
        project,
        [
            "hook",
            "complete-refresh",
            "--format",
            "json",
        ],
    )

    payload = json.loads(result.output.strip())
    status_path = project / ".specify" / "project-cognition" / "status.json"
    status_payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert result.exit_code == 0, result.output
    assert payload["event"] == "project_cognition.complete_refresh"
    assert payload["status"] == "blocked"
    assert payload["severity"] == "critical"
    assert payload["data"]["validation"]["status"] == "blocked"
    assert status_payload["freshness"] == "partial_refresh"


def test_hook_complete_refresh_accepts_query_ready_runtime(tmp_path: Path):
    project = _create_project(tmp_path)
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, check=True)
    (project / "README.md").write_text("# Test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "Initial test commit"], cwd=project, check=True, capture_output=True, text=True)
    _write_project_cognition_runtime(project / ".specify" / "project-cognition")

    result = _invoke_in_project(
        project,
        [
            "hook",
            "complete-refresh",
            "--format",
            "json",
        ],
    )

    payload = json.loads(result.output.strip())
    status_path = project / ".specify" / "project-cognition" / "status.json"
    status_payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert result.exit_code == 0, result.output
    assert payload["event"] == "project_cognition.complete_refresh"
    assert payload["status"] == "ok"
    assert status_payload["freshness"] == "fresh"
    assert status_payload["last_refresh_reason"] == "map-build"


def test_project_map_preflight_support_drift_copy_does_not_route_to_map_update(tmp_path: Path, monkeypatch):
    project = _create_project(tmp_path)
    (project / ".specify" / "integration.json").write_text(
        json.dumps({"integration": "codex"}),
        encoding="utf-8",
    )

    def support_drift(_args: list[str], *, cwd: Path, check: bool = True) -> dict[str, object]:
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

    monkeypatch.setattr("specify_cli.run_project_cognition", support_drift)

    bootstrap = _invoke_in_project(project, ["sp-teams", "--bootstrap"])
    assert bootstrap.exit_code == 0
    result = _invoke_in_project(project, ["sp-teams", "--dispatch", "REQ-001"])

    assert result.exit_code == 0
    assert "support" in result.output.lower()
    assert "sp-map-update" not in result.output.lower()


def test_project_map_preflight_partial_refresh_copy_explains_refresh_recorded_but_not_ready(tmp_path: Path, monkeypatch):
    project = _create_project(tmp_path)
    (project / ".specify" / "integration.json").write_text(
        json.dumps({"integration": "codex"}),
        encoding="utf-8",
    )

    def partial_refresh(_args: list[str], *, cwd: Path, check: bool = True) -> dict[str, object]:
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

    monkeypatch.setattr("specify_cli.run_project_cognition", partial_refresh)

    bootstrap = _invoke_in_project(project, ["sp-teams", "--bootstrap"])
    assert bootstrap.exit_code == 0
    result = _invoke_in_project(project, ["sp-teams", "--dispatch", "REQ-001"])

    assert result.exit_code == 0
    assert "refresh data was recorded" in result.output.lower()
    assert "remains partial" in result.output.lower()


def test_project_map_preflight_path_index_gap_routes_to_map_update(tmp_path: Path, monkeypatch):
    project = _create_project(tmp_path)
    (project / ".specify" / "integration.json").write_text(
        json.dumps({"integration": "codex"}),
        encoding="utf-8",
    )

    def stale_path_index_gap(_args: list[str], *, cwd: Path, check: bool = True) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_update",
            "status_path": str(project / ".specify" / "project-cognition" / "status.json"),
            "reasons": ["58 changed paths missing from project cognition path_index"],
            "changed_files": [],
            "must_refresh_topics": [],
            "review_topics": [],
        }

    monkeypatch.setattr("specify_cli.run_project_cognition", stale_path_index_gap)

    bootstrap = _invoke_in_project(project, ["sp-teams", "--bootstrap"])
    assert bootstrap.exit_code == 0

    result = _invoke_in_project(project, ["sp-teams", "--dispatch", "REQ-001"])

    assert result.exit_code == 0
    assert "path_index" in result.output.lower()
    assert "sp-map-update" in result.output.lower()
    assert "sp-map-scan" not in result.output.lower()
    assert "sp-map-build" not in result.output.lower()


def test_project_map_preflight_scan_build_copy_names_all_rebuild_reasons(tmp_path: Path, monkeypatch):
    project = _create_project(tmp_path)
    (project / ".specify" / "integration.json").write_text(
        json.dumps({"integration": "codex"}),
        encoding="utf-8",
    )

    def zero_path_index_rebuild(_args: list[str], *, cwd: Path, check: bool = True) -> dict[str, object]:
        return {
            "freshness": "stale",
            "state": "runtime_stale",
            "readiness": "blocked",
            "recommended_next_action": "run_map_scan_build",
            "status_path": str(project / ".specify" / "project-cognition" / "status.json"),
            "reasons": ["active_generation_has_no_path_index_rows"],
            "changed_files": [],
            "must_refresh_topics": [],
            "review_topics": [],
        }

    monkeypatch.setattr("specify_cli.run_project_cognition", zero_path_index_rebuild)

    bootstrap = _invoke_in_project(project, ["sp-teams", "--bootstrap"])
    assert bootstrap.exit_code == 0

    result = _invoke_in_project(project, ["sp-teams", "--dispatch", "REQ-001"])

    assert result.exit_code == 0
    assert "sp-map-scan" in result.output.lower()
    assert "sp-map-build" in result.output.lower()
    assert "active_generation_has_no_path_index_rows" in result.output
    assert "path_not_safely_adoptable_by_project_cognition_index" in result.output
    assert "explicit_rebuild_requested" in result.output
    assert "baseline_identity_invalid" in result.output


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
