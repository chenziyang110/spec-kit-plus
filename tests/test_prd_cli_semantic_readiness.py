import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.specify_runtime import run_specify_runtime


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
    payload = json.loads(result.stdout.strip())
    return project, payload["workspace"], Path(payload["workspace_path"])


def _write_workflow_state(
    run_dir: Path,
    run_id: str,
    *,
    command: str,
    status: str,
    build_status: str,
    next_command: str,
) -> None:
    (run_dir / "workflow-state.md").write_text(
        f'''---
id: "{run_id}"
slug: "semantic-audit"
status: "{status}"
---
# PRD Workflow State

## Current Command

- active_command: `{command}`
- status: `{status}`

## Phase Mode

- phase_mode: `analysis-only`
- classification: `mixed`
- scan_status: `complete`
- build_status: `{build_status}`
- failed_readiness_checks: `none`
- failed_reverse_coverage_checks: `none`

## Allowed Artifact Writes

- `.specify/prd-runs/{run_id}/workflow-state.md`

## Forbidden Actions

- edit source code

## Next Command

- `{next_command}`

## Authoritative Files

- `.specify/prd-runs/{run_id}/workflow-state.md`
''',
        encoding="utf-8",
    )


def _write_valid_scan(run_dir: Path, run_id: str) -> None:
    _write_workflow_state(
        run_dir,
        run_id,
        command="sp-prd-scan",
        status="ready-for-build",
        build_status="pending",
        next_command="/sp.prd-build",
    )
    (run_dir / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "version": 1,
                "rows": [
                    {
                        "id": "COV-001",
                        "surface": "src/app.py",
                        "status": "covered",
                        "evidence": ["evidence/EVD-001.json"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
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
    (run_dir / "artifact-contracts.json").write_text(
        '{"artifacts":[{"id":"ART-001","status":"landed"}]}',
        encoding="utf-8",
    )
    (run_dir / "reconstruction-checklist.json").write_text(
        '{"checks":[{"id":"CHK-001","status":"pass"}]}',
        encoding="utf-8",
    )
    (run_dir / "scan-packets" / "lane-001.md").write_text(
        "# Scan Packet\n\nRepository evidence packet.\n", encoding="utf-8"
    )
    (run_dir / "evidence" / "EVD-001.json").write_text(
        '{"id":"EVD-001","kind":"repository"}\n', encoding="utf-8"
    )
    (run_dir / "worker-results" / "lane-001.json").write_text(
        json.dumps(
            {
                "lane_id": "lane-001",
                "reported_status": "done",
                "paths_read": ["src/app.py"],
                "key_facts": ["Entrypoint observed."],
                "evidence_refs": ["evidence/EVD-001.json"],
                "recommended_contract_updates": [],
                "confidence": "high",
                "unknowns": [],
                "minimum_verification": ["Inspect entrypoint."],
                "result_handoff_path": "worker-results/lane-001.json",
            }
        ),
        encoding="utf-8",
    )


def _finalize_scan(project: Path, run_id: str) -> dict:
    return run_specify_runtime(
        [
            "prd-scan",
            "finalize",
            run_id,
            "--project-root",
            str(project),
            "--format",
            "json",
        ],
        cwd=project,
        check=False,
        install_if_missing=True,
    )


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


def test_prd_scan_finalize_blocks_semantically_empty_scan_even_when_surfaces_exist(
    tmp_path: Path,
) -> None:
    project, run_id, run_dir = _initialize_run(tmp_path)
    _write_valid_scan(run_dir, run_id)
    (run_dir / "coverage-ledger.json").write_text(
        '{"version":1,"rows":[]}', encoding="utf-8"
    )
    (run_dir / "capability-ledger.json").write_text(
        '{"capabilities":[]}', encoding="utf-8"
    )
    (run_dir / "artifact-contracts.json").write_text(
        '{"artifacts":[]}', encoding="utf-8"
    )
    (run_dir / "reconstruction-checklist.json").write_text(
        '{"checks":[]}', encoding="utf-8"
    )

    payload = _finalize_scan(project, run_id)

    assert payload["status"] == "blocked"
    assert any(
        "coverage-ledger.json" in blocker for blocker in payload["blockers"]
    ), payload


def test_prd_build_cli_reports_ready_to_build_for_valid_frozen_scan(
    tmp_path: Path,
) -> None:
    project, run_id, run_dir = _initialize_run(tmp_path)
    _write_valid_scan(run_dir, run_id)
    finalized = _finalize_scan(project, run_id)
    assert finalized["status"] == "ok", finalized

    result = _invoke(project, ["prd-build", run_id, "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip())
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
    _write_valid_scan(run_dir, run_id)
    finalized = _finalize_scan(project, run_id)
    assert finalized["status"] == "ok", finalized
    _write_build_outputs(run_dir)

    result = _invoke(project, ["prd-build", run_id, "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip())
    assert payload["complete"] is False
    assert payload["status"] == "blocked"
    assert any("workflow-state.md" in error for error in payload["errors"])
    assert payload["recovery"]["stage"] == "prd-build"

    _write_workflow_state(
        run_dir,
        run_id,
        command="sp-prd-build",
        status="complete",
        build_status="complete",
        next_command="none",
    )
    result = _invoke(project, ["prd-build", run_id, "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "blocked"
    assert any("substantive content" in error for error in payload["errors"])
