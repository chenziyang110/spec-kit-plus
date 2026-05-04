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
    assert (run_dir / "scan-packets").is_dir()
    assert (run_dir / "worker-results").is_dir()
    assert (run_dir / "master").is_dir()
    assert (run_dir / "exports").is_dir()
    assert (run_dir / "workflow-state.md").is_file()
    assert (run_dir / "prd-scan.md").is_file()
    assert (run_dir / "coverage-ledger.md").is_file()
    assert (run_dir / "coverage-ledger.json").is_file()
    assert (run_dir / "capability-ledger.json").is_file()
    assert (run_dir / "artifact-contracts.json").is_file()
    assert (run_dir / "reconstruction-checklist.json").is_file()
    workflow_state = (run_dir / "workflow-state.md").read_text(encoding="utf-8")
    assert "- active_command: `sp-prd`" in workflow_state
    assert "- phase_mode: `analysis-only`" in workflow_state
    assert "## Allowed Artifact Writes" in workflow_state
    assert "## Forbidden Actions" in workflow_state
    assert "## Authoritative Files" in workflow_state
    assert "## Next Command" in workflow_state
    assert payload["surfaces"] == {
        "workspace": True,
        "evidence": True,
        "scan_packets": True,
        "worker_results": True,
        "master": True,
        "exports": True,
        "workflow_state": True,
        "prd_scan": True,
        "coverage_ledger": True,
        "coverage_ledger_json": True,
        "capability_ledger_json": True,
        "artifact_contracts_json": True,
        "reconstruction_checklist_json": True,
        "master_pack": False,
        "prd_export": False,
        "reconstruction_appendix": False,
        "data_model": False,
        "integration_contracts": False,
        "runtime_behaviors": False,
    }
    assert payload["complete"] is True


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
        "scan_packets": False,
        "worker_results": False,
        "master": False,
        "exports": False,
        "workflow_state": True,
        "prd_scan": False,
        "coverage_ledger": False,
        "coverage_ledger_json": False,
        "capability_ledger_json": False,
        "artifact_contracts_json": False,
        "reconstruction_checklist_json": False,
        "master_pack": False,
        "prd_export": False,
        "reconstruction_appendix": False,
        "data_model": False,
        "integration_contracts": False,
        "runtime_behaviors": False,
    }
    assert payload["complete"] is False


@pytest.mark.skipif(os.name == "nt", reason="direct bash helper path execution is POSIX-only")
def test_bash_prd_status_scan_reports_scan_mode_and_completion(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-ready-prd-scan"
    for dirname in ("evidence", "scan-packets", "worker-results", "master", "exports"):
        (run_dir / dirname).mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "workflow-state.md": "- active_command: `sp-prd-scan`\n",
        "prd-scan.md": "# PRD Scan\n",
        "coverage-ledger.md": "# Coverage Ledger\n",
        "coverage-ledger.json": "{}\n",
        "capability-ledger.json": "{}\n",
        "artifact-contracts.json": "{}\n",
        "reconstruction-checklist.json": "{}\n",
    }.items():
        (run_dir / relative).write_text(content, encoding="utf-8")

    payload = _run_json(["bash", str(BASH_HELPER), str(project), "status-scan", "260504-ready-prd-scan"])

    assert payload["mode"] == "status-scan"
    assert payload["workspace"] == "260504-ready-prd-scan"
    assert payload["workspace_path"] == str(run_dir.resolve())
    assert payload["surfaces"]["workspace"] is True
    assert payload["surfaces"]["evidence"] is True
    assert payload["surfaces"]["scan_packets"] is True
    assert payload["surfaces"]["worker_results"] is True
    assert payload["surfaces"]["workflow_state"] is True
    assert payload["surfaces"]["prd_scan"] is True
    assert payload["surfaces"]["coverage_ledger"] is True
    assert payload["surfaces"]["coverage_ledger_json"] is True
    assert payload["surfaces"]["capability_ledger_json"] is True
    assert payload["surfaces"]["artifact_contracts_json"] is True
    assert payload["surfaces"]["reconstruction_checklist_json"] is True
    assert payload["complete"] is True


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
    assert payload["workspace"] == f"{payload['date']}-support-desk"
    assert run_dir.is_dir()
    assert run_dir == project / ".specify" / "prd-runs" / payload["workspace"]
    assert (run_dir / "scan-packets").is_dir()
    assert (run_dir / "worker-results").is_dir()
    assert (run_dir / "master").is_dir()
    assert (run_dir / "exports").is_dir()
    assert (run_dir / "workflow-state.md").is_file()
    assert (run_dir / "prd-scan.md").is_file()
    assert (run_dir / "coverage-ledger.md").is_file()
    assert (run_dir / "coverage-ledger.json").is_file()
    assert (run_dir / "capability-ledger.json").is_file()
    assert (run_dir / "artifact-contracts.json").is_file()
    assert (run_dir / "reconstruction-checklist.json").is_file()
    workflow_state = (run_dir / "workflow-state.md").read_text(encoding="utf-8")
    assert "- active_command: `sp-prd`" in workflow_state
    assert "- phase_mode: `analysis-only`" in workflow_state
    assert payload["surfaces"] == {
        "workspace": True,
        "evidence": True,
        "scan_packets": True,
        "worker_results": True,
        "master": True,
        "exports": True,
        "workflow_state": True,
        "prd_scan": True,
        "coverage_ledger": True,
        "coverage_ledger_json": True,
        "capability_ledger_json": True,
        "artifact_contracts_json": True,
        "reconstruction_checklist_json": True,
        "master_pack": False,
        "prd_export": False,
        "reconstruction_appendix": False,
        "data_model": False,
        "integration_contracts": False,
        "runtime_behaviors": False,
    }
    assert payload["complete"] is True


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh is not available")
def test_powershell_prd_status_scan_reports_scan_mode_and_completion(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-ready-prd-scan"
    for dirname in ("evidence", "scan-packets", "worker-results", "master", "exports"):
        (run_dir / dirname).mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "workflow-state.md": "- active_command: `sp-prd-scan`\n",
        "prd-scan.md": "# PRD Scan\n",
        "coverage-ledger.md": "# Coverage Ledger\n",
        "coverage-ledger.json": "{}\n",
        "capability-ledger.json": "{}\n",
        "artifact-contracts.json": "{}\n",
        "reconstruction-checklist.json": "{}\n",
    }.items():
        (run_dir / relative).write_text(content, encoding="utf-8")

    payload = _run_json(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(POWERSHELL_HELPER),
            str(project),
            "status-scan",
            "260504-ready-prd-scan",
        ]
    )

    assert payload["mode"] == "status-scan"
    assert payload["workspace"] == "260504-ready-prd-scan"
    assert payload["workspace_path"] == str(run_dir.resolve())
    assert payload["surfaces"]["workspace"] is True
    assert payload["surfaces"]["evidence"] is True
    assert payload["surfaces"]["scan_packets"] is True
    assert payload["surfaces"]["worker_results"] is True
    assert payload["surfaces"]["workflow_state"] is True
    assert payload["surfaces"]["prd_scan"] is True
    assert payload["surfaces"]["coverage_ledger"] is True
    assert payload["surfaces"]["coverage_ledger_json"] is True
    assert payload["surfaces"]["capability_ledger_json"] is True
    assert payload["surfaces"]["artifact_contracts_json"] is True
    assert payload["surfaces"]["reconstruction_checklist_json"] is True
    assert payload["complete"] is True


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
    assert payload["status_file"] == str(project / ".specify" / "prd" / "status.json")
    assert payload["freshness"]["status_file_exists"] is True
    assert payload["freshness"]["freshness"] == "missing"
    assert payload["freshness"]["latest_run"] == payload["workspace"]
    status_payload = json.loads((project / ".specify" / "prd" / "status.json").read_text(encoding="utf-8"))
    assert status_payload["freshness"] == "missing"
    assert status_payload["last_refresh_basis"] == "prd-scan-init"
    assert payload["surfaces"]["prd_scan"] is True
    assert payload["surfaces"]["coverage_ledger_json"] is True
    assert payload["surfaces"]["capability_ledger_json"] is True
    assert payload["surfaces"]["artifact_contracts_json"] is True
    assert payload["surfaces"]["reconstruction_checklist_json"] is True
    state_path = Path(payload["workspace_path"]) / "workflow-state.md"
    state_content = state_path.read_text(encoding="utf-8")
    assert "- active_command: `sp-prd`" in state_content
    assert "- phase_mode: `analysis-only`" in state_content
    assert "## Allowed Artifact Writes" in state_content
    assert "## Forbidden Actions" in state_content
    assert "## Authoritative Files" in state_content
    assert "## Next Command" in state_content


def test_python_prd_helper_wrapper_supports_prd_scan_mode(tmp_path: Path):
    project = _setup_project(tmp_path)
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        payload = specify_cli._run_prd_helper("init-scan", run_slug="Proxy Audit")
    finally:
        os.chdir(old_cwd)

    assert payload["mode"] == "init-scan"
    assert payload["status_file"] == str(project / ".specify" / "prd" / "status.json")
    assert payload["freshness"]["status_file_exists"] is True
    assert payload["freshness"]["freshness"] == "missing"
    assert payload["freshness"]["latest_run"] == payload["workspace"]
    status_payload = json.loads((project / ".specify" / "prd" / "status.json").read_text(encoding="utf-8"))
    assert status_payload["freshness"] == "missing"
    assert status_payload["last_refresh_basis"] == "prd-scan-init"
    assert payload["surfaces"]["prd_scan"] is True
    assert payload["surfaces"]["coverage_ledger_json"] is True
    assert payload["surfaces"]["capability_ledger_json"] is True
    assert payload["surfaces"]["artifact_contracts_json"] is True
    assert payload["surfaces"]["reconstruction_checklist_json"] is True
    state = (Path(payload["workspace_path"]) / "workflow-state.md").read_text(encoding="utf-8")
    assert "- active_command: `sp-prd-scan`" in state
    assert "- phase_mode: `analysis-only`" in state


def test_python_prd_helper_wrapper_supports_prd_build_status(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-proxy-audit"
    (run_dir / "master").mkdir(parents=True)
    (run_dir / "exports").mkdir()
    for relative, content in {
        "workflow-state.md": "- active_command: `sp-prd-build`\n",
        "master/master-pack.md": "# Master Pack\n",
        "exports/prd.md": "# PRD\n",
        "exports/reconstruction-appendix.md": "# Reconstruction Appendix\n",
        "exports/data-model.md": "# Data Model\n",
        "exports/integration-contracts.md": "# Integration Contracts\n",
        "exports/runtime-behaviors.md": "# Runtime Behaviors\n",
    }.items():
        (run_dir / relative).write_text(content, encoding="utf-8")

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        payload = specify_cli._run_prd_helper("status-build", run_slug="260504-proxy-audit")
    finally:
        os.chdir(old_cwd)

    assert payload["mode"] == "status-build"
    assert payload["workspace"] == "260504-proxy-audit"
    assert payload["workspace_path"] == str(run_dir.resolve())
    assert payload["surfaces"]["workspace"] is True
    assert payload["surfaces"]["master"] is True
    assert payload["surfaces"]["exports"] is True
    assert payload["surfaces"]["workflow_state"] is True
    assert payload["surfaces"]["master_pack"] is True
    assert payload["surfaces"]["prd_export"] is True
    assert payload["surfaces"]["reconstruction_appendix"] is True
    assert payload["surfaces"]["data_model"] is True
    assert payload["surfaces"]["integration_contracts"] is True
    assert payload["surfaces"]["runtime_behaviors"] is True
    assert payload["complete"] is True


@pytest.mark.skipif(os.name == "nt", reason="direct bash helper path execution is POSIX-only")
def test_bash_prd_helper_supports_prd_build_status(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-proxy-audit"
    (run_dir / "master").mkdir(parents=True)
    (run_dir / "exports").mkdir()
    (run_dir / "master" / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    (run_dir / "exports" / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (run_dir / "workflow-state.md").write_text("- active_command: `sp-prd-build`\n", encoding="utf-8")

    payload = _run_json(["bash", str(BASH_HELPER), str(project), "status-build", "260504-proxy-audit"])

    assert payload["mode"] == "status-build"
    assert payload["surfaces"]["master_pack"] is True
    assert payload["surfaces"]["prd_export"] is True


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh is not available")
def test_powershell_prd_helper_supports_prd_build_status(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-proxy-audit"
    (run_dir / "master").mkdir(parents=True)
    (run_dir / "exports").mkdir()
    (run_dir / "master" / "master-pack.md").write_text("# Master Pack\n", encoding="utf-8")
    (run_dir / "exports" / "prd.md").write_text("# PRD\n", encoding="utf-8")
    (run_dir / "workflow-state.md").write_text("- active_command: `sp-prd-build`\n", encoding="utf-8")

    payload = _run_json(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(POWERSHELL_HELPER),
            str(project),
            "status-build",
            "260504-proxy-audit",
        ]
    )

    assert payload["mode"] == "status-build"
    assert payload["workspace"] == "260504-proxy-audit"
    assert payload["workspace_path"] == str(run_dir.resolve())
    assert payload["surfaces"]["workspace"] is True
    assert payload["surfaces"]["master"] is True
    assert payload["surfaces"]["exports"] is True
    assert payload["surfaces"]["workflow_state"] is True
    assert payload["surfaces"]["master_pack"] is True
    assert payload["surfaces"]["prd_export"] is True
    assert payload["surfaces"]["reconstruction_appendix"] is False
    assert payload["surfaces"]["data_model"] is False
    assert payload["surfaces"]["integration_contracts"] is False
    assert payload["surfaces"]["runtime_behaviors"] is False
    assert payload["complete"] is False


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
