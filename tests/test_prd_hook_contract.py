from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "prd-hook-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def _write_prd_workflow_state(run_dir: Path) -> None:
    (run_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: PRD Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-prd`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: reverse PRD extraction only",
                "",
                "## Allowed Artifact Writes",
                "",
                "- prd-scan.md",
                "- coverage-ledger.md",
                "- coverage-ledger.json",
                "- capability-ledger.json",
                "- artifact-contracts.json",
                "- reconstruction-checklist.json",
                "- scan-packets/",
                "- evidence/",
                "- worker-results/",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- workflow-state.md",
                "- prd-scan.md",
                "- coverage-ledger.json",
                "- artifact-contracts.json",
                "- reconstruction-checklist.json",
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


def _write_complete_prd_artifacts(run_dir: Path) -> None:
    _write_prd_workflow_state(run_dir)
    (run_dir / "prd-scan.md").write_text(
        "\n".join(
            [
                "# PRD Scan",
                "",
                "## Reconstruction Summary",
                "",
                "- Status: ready",
            ]
        ),
        encoding="utf-8",
    )
    (run_dir / "coverage-ledger.md").write_text("# Coverage Ledger\n", encoding="utf-8")
    (run_dir / "coverage-ledger.json").write_text('{"version": 1, "rows": []}\n', encoding="utf-8")
    (run_dir / "capability-ledger.json").write_text('{"capabilities": []}\n', encoding="utf-8")
    (run_dir / "artifact-contracts.json").write_text('{"artifacts": []}\n', encoding="utf-8")
    (run_dir / "reconstruction-checklist.json").write_text('{"checks": []}\n', encoding="utf-8")
    (run_dir / "entrypoint-ledger.json").write_text('{"entrypoints": []}\n', encoding="utf-8")
    (run_dir / "config-contracts.json").write_text('{"configs": []}\n', encoding="utf-8")
    (run_dir / "protocol-contracts.json").write_text('{"protocols": []}\n', encoding="utf-8")
    (run_dir / "state-machines.json").write_text('{"machines": []}\n', encoding="utf-8")
    (run_dir / "error-semantics.json").write_text('{"errors": []}\n', encoding="utf-8")
    (run_dir / "verification-surfaces.json").write_text('{"surfaces": []}\n', encoding="utf-8")
    (run_dir / "scan-packets").mkdir()
    (run_dir / "evidence").mkdir()
    (run_dir / "worker-results").mkdir()


def test_prd_state_validation_accepts_analysis_only_workflow_state(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_workflow_state(run_dir)

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []
    assert result.data["checkpoint"]["active_command"] == "sp-prd"
    assert result.data["checkpoint"]["phase_mode"] == "analysis-only"


def test_prd_state_validation_blocks_wrong_phase_mode(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_workflow_state(run_dir)
    content = (run_dir / "workflow-state.md").read_text(encoding="utf-8")
    (run_dir / "workflow-state.md").write_text(
        content.replace("analysis-only", "planning-only"),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "blocked"
    assert any("phase_mode" in message for message in result.errors)


def test_prd_artifact_validation_blocks_missing_prd_suite_artifacts(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_prd_workflow_state(run_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "blocked"
    assert any("prd-scan.md" in message for message in result.errors)
    assert any("coverage-ledger.md" in message for message in result.errors)
    assert any("coverage-ledger.json" in message for message in result.errors)
    assert any("scan-packets" in message for message in result.errors)


def test_prd_artifact_validation_blocks_missing_heavy_scan_contract_artifacts(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-heavy-missing"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_complete_prd_artifacts(run_dir)
    (run_dir / "workflow-state.md").write_text(
        (run_dir / "workflow-state.md").read_text(encoding="utf-8") + "\n- config-contracts.json\n",
        encoding="utf-8",
    )
    for relative in [
        "entrypoint-ledger.json",
        "config-contracts.json",
        "protocol-contracts.json",
        "state-machines.json",
        "error-semantics.json",
        "verification-surfaces.json",
    ]:
        target = run_dir / relative
        if target.exists():
            target.unlink()

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd-scan", "feature_dir": str(run_dir)},
    )

    assert result.status == "blocked"
    assert any("entrypoint-ledger.json" in message for message in result.errors)
    assert any("config-contracts.json" in message for message in result.errors)
    assert any("protocol-contracts.json" in message for message in result.errors)


def test_prd_artifact_validation_accepts_complete_prd_suite(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-demo-prd"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_complete_prd_artifacts(run_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []


def test_prd_artifact_validation_allows_missing_optional_control_artifacts(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260503-optional-control-artifacts"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_complete_prd_artifacts(run_dir)

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "prd", "feature_dir": str(run_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []
