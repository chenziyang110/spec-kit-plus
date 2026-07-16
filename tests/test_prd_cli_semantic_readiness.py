import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


def _invoke(project: Path, args: list[str]):
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        return CliRunner().invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def _initialize_run(tmp_path: Path) -> tuple[Path, str, Path]:
    project = tmp_path / "prd-semantic-cli"
    project.mkdir()
    (project / ".specify").mkdir()
    result = _invoke(project, ["prd-scan", "semantic-audit", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    return project, payload["workspace"], Path(payload["workspace_path"])


def _write_build_outputs(run_dir: Path) -> None:
    (run_dir / "master").mkdir(exist_ok=True)
    (run_dir / "master" / "master-pack.md").write_text(
        "# Master Pack\n", encoding="utf-8"
    )
    exports = run_dir / "exports"
    exports.mkdir(exist_ok=True)
    for name in (
        "README.md",
        "prd.md",
        "reconstruction-appendix.md",
        "data-model.md",
        "integration-contracts.md",
        "runtime-behaviors.md",
        "config-contracts.md",
        "protocol-contracts.md",
        "state-machines.md",
        "error-semantics.md",
        "verification-surface.md",
        "reconstruction-risks.md",
    ):
        (exports / name).write_text(f"# {name}\n", encoding="utf-8")


def test_prd_build_cli_blocks_semantically_empty_scan_even_when_surfaces_exist(
    tmp_path: Path,
) -> None:
    project, run_id, run_dir = _initialize_run(tmp_path)
    _write_build_outputs(run_dir)

    result = _invoke(project, ["prd-build", run_id, "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["surface_complete"] is True
    assert payload["complete"] is False
    assert payload["status"] == "blocked"
    assert payload["readiness"] == "blocked"
    assert payload["errors"]
    assert any("critical capability" in error for error in payload["errors"])
    assert payload["recovery"]["stage"] == "prd-scan"


def test_prd_build_cli_reports_ready_to_build_for_valid_frozen_scan(
    tmp_path: Path,
) -> None:
    project, run_id, run_dir = _initialize_run(tmp_path)
    (run_dir / "capability-ledger.json").write_text(
        json.dumps(
            {
                "capabilities": [
                    {
                        "id": "CAP-001",
                        "tier": "critical",
                        "status": "reconstruction-ready",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "version": 1,
                "rows": [
                    {
                        "surface": "src/app.py",
                        "status": "covered",
                        "evidence": ["evidence/CAP-001.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        '{"artifacts":[{"id":"ART-001","status":"landed"}]}',
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text(
        '{"checks":[{"id":"CHK-001","status":"pass"}]}',
        encoding="utf-8",
    )
    (run_dir / "scan-packets" / "lane-001.md").write_text(
        "# Scan Packet\n", encoding="utf-8"
    )
    (run_dir / "evidence" / "CAP-001.md").write_text("# Evidence\n", encoding="utf-8")
    (run_dir / "worker-results" / "lane-001.json").write_text(
        json.dumps(
            {
                "paths_read": ["src/app.py"],
                "unknowns": [],
                "confidence": "high",
                "recommended_ledger_updates": [],
            }
        ),
        encoding="utf-8",
    )

    result = _invoke(project, ["prd-build", run_id, "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["surface_complete"] is False
    assert payload["complete"] is False
    assert payload["status"] == "ready"
    assert payload["readiness"] == "ready-to-build"
    assert payload["errors"] == []
    assert payload["recovery"] is None


def test_prd_build_cli_rejects_heading_only_exports_and_nonterminal_state(
    tmp_path: Path,
) -> None:
    project, run_id, run_dir = _initialize_run(tmp_path)
    (run_dir / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "version": 1,
                "rows": [
                    {
                        "surface": "src/app.py",
                        "status": "covered",
                        "evidence": ["evidence/CAP-001.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "capability-ledger.json").write_text(
        '{"capabilities":[{"id":"CAP-001","tier":"critical",'
        '"status":"reconstruction-ready"}]}',
        encoding="utf-8",
    )
    (run_dir / "artifact-contracts.json").write_text(
        '{"artifacts":[{"id":"ART-001","status":"landed"}]}',
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text(
        '{"checks":[{"id":"CHK-001","status":"pass"}]}',
        encoding="utf-8",
    )
    (run_dir / "scan-packets" / "lane-001.md").write_text(
        "# Scan Packet\n", encoding="utf-8"
    )
    (run_dir / "evidence" / "CAP-001.md").write_text(
        "# Evidence\n", encoding="utf-8"
    )
    (run_dir / "worker-results" / "lane-001.json").write_text(
        json.dumps(
            {
                "paths_read": ["src/app.py"],
                "unknowns": [],
                "confidence": "high",
                "recommended_ledger_updates": [],
            }
        ),
        encoding="utf-8",
    )
    _write_build_outputs(run_dir)

    result = _invoke(project, ["prd-build", run_id, "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["complete"] is False
    assert payload["status"] == "blocked"
    assert any(
        "substantive content" in error or "workflow-state.md" in error
        for error in payload["errors"]
    )
