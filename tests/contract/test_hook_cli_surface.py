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
                "## Phase Mode",
                "",
                "- phase_mode: `planning-only`",
                "- summary: demo ✅",
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
    assert payload["data"]["checkpoint"]["summary"] == "demo ✅"


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
    (exports_dir / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (exports_dir / "reconstruction-appendix.md").write_text("# Appendix\n", encoding="utf-8")
    (exports_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (exports_dir / "integration-contracts.md").write_text("# Integration Contracts\n", encoding="utf-8")
    (exports_dir / "runtime-behaviors.md").write_text("# Runtime Behaviors\n", encoding="utf-8")

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
