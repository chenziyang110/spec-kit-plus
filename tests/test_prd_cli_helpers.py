import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import specify_cli


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASH_HELPER = PROJECT_ROOT / "scripts" / "bash" / "prd-state.sh"
POWERSHELL_HELPER = PROJECT_ROOT / "scripts" / "powershell" / "prd-state.ps1"


def _setup_project(tmp_path: Path) -> Path:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    return project


def _run_json(cmd: list[str]) -> dict:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


@pytest.mark.skipif(os.name == "nt", reason="direct bash helper path execution is POSIX-only")
def test_bash_prd_init_creates_run_workspace_and_emits_json(tmp_path: Path):
    project = _setup_project(tmp_path)

    payload = _run_json(["bash", str(BASH_HELPER), str(project), "init", "Checkout Audit"])

    assert payload["mode"] == "init"
    assert payload["slug"] == "checkout-audit"
    assert payload["workspace"] == f"{payload['date']}-checkout-audit"
    run_dir = Path(payload["workspace_path"])
    assert run_dir == project / ".specify" / "prd-runs" / payload["workspace"]
    assert run_dir.is_dir()
    assert (run_dir / "evidence").is_dir()
    assert (run_dir / "master").is_dir()
    assert (run_dir / "exports").is_dir()
    assert (run_dir / "master" / "exports").is_dir()
    assert (run_dir / "workflow-state.md").is_file()
    assert (run_dir / "coverage-matrix.md").is_file()
    workflow_state = (run_dir / "workflow-state.md").read_text(encoding="utf-8")
    assert "- active_command: `sp-prd`" in workflow_state
    assert "- phase_mode: `analysis-only`" in workflow_state
    assert payload["surfaces"] == {
        "workspace": True,
        "evidence": True,
        "master": True,
        "exports": True,
        "master_exports": True,
        "workflow_state": True,
        "coverage_matrix": True,
    }


@pytest.mark.skipif(os.name == "nt", reason="direct bash helper path execution is POSIX-only")
def test_bash_prd_status_reports_missing_and_present_surfaces(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260502-partial-prd"
    (run_dir / "evidence").mkdir(parents=True)
    (run_dir / "workflow-state.md").write_text("# PRD Workflow State\n", encoding="utf-8")

    payload = _run_json(["bash", str(BASH_HELPER), str(project), "status", "260502-partial-prd"])

    assert payload["mode"] == "status"
    assert payload["workspace"] == "260502-partial-prd"
    assert payload["workspace_path"] == str(run_dir.resolve())
    assert payload["surfaces"] == {
        "workspace": True,
        "evidence": True,
        "master": False,
        "exports": False,
        "master_exports": False,
        "workflow_state": True,
        "coverage_matrix": False,
    }
    assert payload["complete"] is False


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh is not available")
def test_powershell_prd_helper_matches_bash_init_contract(tmp_path: Path):
    project = _setup_project(tmp_path)

    payload = _run_json(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(POWERSHELL_HELPER),
            str(project),
            "init",
            "Support Desk",
        ]
    )

    run_dir = Path(payload["workspace_path"])
    assert payload["mode"] == "init"
    assert payload["slug"] == "support-desk"
    assert run_dir.is_dir()
    assert (run_dir / "master" / "exports").is_dir()
    assert all(payload["surfaces"].values())


def test_python_prd_helper_wrapper_runs_helper_from_current_project(tmp_path: Path, monkeypatch):
    project = _setup_project(tmp_path)
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        payload = specify_cli._run_prd_helper("init", run_slug="Billing Portal")
    finally:
        os.chdir(old_cwd)

    assert payload["mode"] == "init"
    assert payload["slug"] == "billing-portal"
    assert Path(payload["workspace_path"]).is_dir()
    state_path = Path(payload["workspace_path"]) / "workflow-state.md"
    state_content = state_path.read_text(encoding="utf-8")
    assert "- active_command: `sp-prd`" in state_content
    assert "- phase_mode: `analysis-only`" in state_content


def test_prd_helper_script_prefers_bundled_core_pack_scripts(tmp_path: Path, monkeypatch):
    core_pack = tmp_path / "core_pack"
    bundled_script = core_pack / "scripts" / ("powershell" if os.name == "nt" else "bash")
    bundled_script.mkdir(parents=True)
    expected_script = bundled_script / ("prd-state.ps1" if os.name == "nt" else "prd-state.sh")
    expected_script.write_text("# bundled prd helper\n", encoding="utf-8")

    source_root = tmp_path / "source-without-helper"
    source_root.mkdir()
    monkeypatch.setattr(specify_cli, "_locate_core_pack", lambda: core_pack)
    monkeypatch.setattr(specify_cli, "_project_root_from_source", lambda: source_root)

    _interpreter, script_path = specify_cli._prd_helper_script()

    assert script_path == expected_script
