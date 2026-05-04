import json
import os
import shutil
import subprocess
import importlib.util
from pathlib import Path

import pytest

import specify_cli


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASH_HELPER = PROJECT_ROOT / "scripts" / "bash" / "prd-state.sh"
POWERSHELL_HELPER = PROJECT_ROOT / "scripts" / "powershell" / "prd-state.ps1"


def _load_prd_state_runtime():
    runtime_path = PROJECT_ROOT / "scripts" / "shared" / "prd-state.py"
    spec = importlib.util.spec_from_file_location("prd_state_runtime_for_tests", runtime_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_PRD_STATE = _load_prd_state_runtime()
SCAN_DIRECTORY_SURFACES = _PRD_STATE.SCAN_DIRECTORY_SURFACES
SCAN_FILE_SURFACES = _PRD_STATE.SCAN_FILE_SURFACES
BASE_SCAN_JSON_SURFACES = _PRD_STATE.BASE_SCAN_JSON_SURFACES
HEAVY_SCAN_JSON_SURFACES = _PRD_STATE.HEAVY_SCAN_JSON_SURFACE_PATHS
BASE_BUILD_SURFACES = _PRD_STATE.BASE_BUILD_SURFACES
HEAVY_BUILD_EXPORT_SURFACES = _PRD_STATE.HEAVY_BUILD_EXPORT_SURFACES
ALL_SURFACE_KEYS = tuple(
    [
        *SCAN_DIRECTORY_SURFACES,
        *SCAN_FILE_SURFACES,
        *BASE_SCAN_JSON_SURFACES,
        *HEAVY_SCAN_JSON_SURFACES,
        *BASE_BUILD_SURFACES,
        *HEAVY_BUILD_EXPORT_SURFACES,
    ]
)
INIT_SCAN_PRESENT_KEYS = tuple(
    [
        *SCAN_DIRECTORY_SURFACES,
        *SCAN_FILE_SURFACES,
        *BASE_SCAN_JSON_SURFACES,
        *HEAVY_SCAN_JSON_SURFACES,
    ]
)
PARTIAL_SCAN_PRESENT_KEYS = ("workspace", "evidence", "workflow_state")
MINIMAL_BUILD_PRESENT_KEYS = (
    "workspace",
    "master",
    "exports",
    "workflow_state",
    "master_pack",
    "prd_export",
)
BUILD_EXPORT_FIXTURES = {
    "workflow-state.md": "- active_command: `sp-prd-build`\n",
    "master/master-pack.md": "# Master Pack\n",
    "exports/prd.md": "# PRD\n",
    "exports/reconstruction-appendix.md": "# Reconstruction Appendix\n",
    "exports/data-model.md": "# Data Model\n",
    "exports/integration-contracts.md": "# Integration Contracts\n",
    "exports/runtime-behaviors.md": "# Runtime Behaviors\n",
    "exports/config-contracts.md": "# Config Contracts\n",
    "exports/protocol-contracts.md": "# Protocol Contracts\n",
    "exports/state-machines.md": "# State Machines\n",
    "exports/error-semantics.md": "# Error Semantics\n",
    "exports/verification-surface.md": "# Verification Surface\n",
    "exports/reconstruction-risks.md": "# Reconstruction Risks\n",
}


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


def _expected_surfaces(present_keys: tuple[str, ...]) -> dict[str, bool]:
    present = set(present_keys)
    return {key: key in present for key in ALL_SURFACE_KEYS}


def _assert_scan_artifacts_created(run_dir: Path) -> None:
    for relative in SCAN_DIRECTORY_SURFACES.values():
        path = run_dir if relative == "." else run_dir / relative
        assert path.is_dir()
    for relative in (
        *SCAN_FILE_SURFACES.values(),
        *BASE_SCAN_JSON_SURFACES.values(),
        *HEAVY_SCAN_JSON_SURFACES.values(),
    ):
        assert (run_dir / relative).is_file()


def _assert_workflow_state_scan_contract(workflow_state: str, active_command: str) -> None:
    assert f"- active_command: `{active_command}`" in workflow_state
    assert "- phase_mode: `analysis-only`" in workflow_state
    assert "## Allowed Artifact Writes" in workflow_state
    assert "## Forbidden Actions" in workflow_state
    assert "## Authoritative Files" in workflow_state
    assert "## Next Command" in workflow_state


def _create_ready_scan_run(project: Path) -> Path:
    run_dir = project / ".specify" / "prd-runs" / "260504-ready-prd-scan"
    for dirname in ("evidence", "scan-packets", "worker-results", "master", "exports"):
        (run_dir / dirname).mkdir(parents=True, exist_ok=True)
    for relative, content in {
        "workflow-state.md": "- active_command: `sp-prd-scan`\n",
        "prd-scan.md": "# PRD Scan\n",
        "coverage-ledger.md": "# Coverage Ledger\n",
        **{relative: "{}\n" for relative in BASE_SCAN_JSON_SURFACES.values()},
        **{relative: "{}\n" for relative in HEAVY_SCAN_JSON_SURFACES.values()},
    }.items():
        (run_dir / relative).write_text(content, encoding="utf-8")
    return run_dir


def _assert_ready_scan_status(payload: dict, run_dir: Path) -> None:
    assert payload["mode"] == "status-scan"
    assert payload["workspace"] == "260504-ready-prd-scan"
    assert payload["workspace_path"] == str(run_dir.resolve())
    for key in (
        "workspace",
        "evidence",
        "scan_packets",
        "worker_results",
        "workflow_state",
        "prd_scan",
        "coverage_ledger",
        *BASE_SCAN_JSON_SURFACES,
        *HEAVY_SCAN_JSON_SURFACES,
    ):
        assert payload["surfaces"][key] is True
    assert payload["complete"] is True


def _create_minimal_build_run(project: Path) -> Path:
    run_dir = project / ".specify" / "prd-runs" / "260504-proxy-audit"
    (run_dir / "master").mkdir(parents=True)
    (run_dir / "exports").mkdir()
    for relative in ("workflow-state.md", "master/master-pack.md", "exports/prd.md"):
        (run_dir / relative).write_text(BUILD_EXPORT_FIXTURES[relative], encoding="utf-8")
    return run_dir


def _assert_minimal_build_status(payload: dict, run_dir: Path) -> None:
    assert payload["mode"] == "status-build"
    assert payload["workspace"] == "260504-proxy-audit"
    assert payload["workspace_path"] == str(run_dir.resolve())
    for key in MINIMAL_BUILD_PRESENT_KEYS:
        assert payload["surfaces"][key] is True
    for key in (
        "reconstruction_appendix",
        "data_model",
        "integration_contracts",
        "runtime_behaviors",
        *HEAVY_BUILD_EXPORT_SURFACES,
    ):
        assert payload["surfaces"][key] is False
    assert payload["complete"] is False


@pytest.mark.skipif(os.name == "nt", reason="direct bash helper path execution is POSIX-only")
def test_bash_prd_init_creates_run_workspace_and_emits_json(tmp_path: Path):
    project = _setup_project(tmp_path)

    payload = _run_json(["bash", str(BASH_HELPER), str(project), "init", "Checkout Audit"])

    assert payload["mode"] == "init"
    assert payload["slug"] == "checkout-audit"
    assert payload["workspace"] == f"{payload['date']}-checkout-audit"
    run_dir = Path(payload["workspace_path"])
    assert run_dir == project / ".specify" / "prd-runs" / payload["workspace"]
    _assert_scan_artifacts_created(run_dir)
    _assert_workflow_state_scan_contract(
        (run_dir / "workflow-state.md").read_text(encoding="utf-8"),
        "sp-prd",
    )
    assert payload["surfaces"] == _expected_surfaces(INIT_SCAN_PRESENT_KEYS)
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
    assert payload["surfaces"] == _expected_surfaces(PARTIAL_SCAN_PRESENT_KEYS)
    assert payload["complete"] is False


@pytest.mark.skipif(os.name == "nt", reason="direct bash helper path execution is POSIX-only")
def test_bash_prd_status_scan_reports_scan_mode_and_completion(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = _create_ready_scan_run(project)

    payload = _run_json(["bash", str(BASH_HELPER), str(project), "status-scan", "260504-ready-prd-scan"])

    _assert_ready_scan_status(payload, run_dir)


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
    assert run_dir == project / ".specify" / "prd-runs" / payload["workspace"]
    _assert_scan_artifacts_created(run_dir)
    _assert_workflow_state_scan_contract(
        (run_dir / "workflow-state.md").read_text(encoding="utf-8"),
        "sp-prd",
    )
    assert payload["surfaces"] == _expected_surfaces(INIT_SCAN_PRESENT_KEYS)
    assert payload["complete"] is True


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh is not available")
def test_powershell_prd_status_scan_reports_scan_mode_and_completion(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = _create_ready_scan_run(project)

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

    _assert_ready_scan_status(payload, run_dir)


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
    for key in (
        "prd_scan",
        *BASE_SCAN_JSON_SURFACES,
        *HEAVY_SCAN_JSON_SURFACES,
    ):
        assert payload["surfaces"][key] is True
    state_path = Path(payload["workspace_path"]) / "workflow-state.md"
    _assert_workflow_state_scan_contract(state_path.read_text(encoding="utf-8"), "sp-prd")


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
    for key in (
        "prd_scan",
        *BASE_SCAN_JSON_SURFACES,
        *HEAVY_SCAN_JSON_SURFACES,
    ):
        assert payload["surfaces"][key] is True
    state = (Path(payload["workspace_path"]) / "workflow-state.md").read_text(encoding="utf-8")
    assert "- active_command: `sp-prd-scan`" in state
    assert "- phase_mode: `analysis-only`" in state


def test_python_prd_helper_wrapper_supports_prd_build_status(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = project / ".specify" / "prd-runs" / "260504-proxy-audit"
    (run_dir / "master").mkdir(parents=True)
    (run_dir / "exports").mkdir()
    for relative, content in BUILD_EXPORT_FIXTURES.items():
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
    for key in (
        "workspace",
        "master",
        "exports",
        "workflow_state",
        *BASE_BUILD_SURFACES,
        *HEAVY_BUILD_EXPORT_SURFACES,
    ):
        assert payload["surfaces"][key] is True
    assert payload["complete"] is True


@pytest.mark.skipif(os.name == "nt", reason="direct bash helper path execution is POSIX-only")
def test_bash_prd_helper_supports_prd_build_status(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = _create_minimal_build_run(project)

    payload = _run_json(["bash", str(BASH_HELPER), str(project), "status-build", "260504-proxy-audit"])

    _assert_minimal_build_status(payload, run_dir)


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh is not available")
def test_powershell_prd_helper_supports_prd_build_status(tmp_path: Path):
    project = _setup_project(tmp_path)
    run_dir = _create_minimal_build_run(project)

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

    _assert_minimal_build_status(payload, run_dir)


def test_prd_helper_script_prefers_bundled_core_pack_scripts(tmp_path: Path, monkeypatch):
    core_pack = tmp_path / "core_pack"
    bundled_script = core_pack / "scripts" / ("powershell" if os.name == "nt" else "bash")
    bundled_script.mkdir(parents=True)
    bundled_shared = core_pack / "scripts" / "shared"
    bundled_shared.mkdir(parents=True)
    expected_script = bundled_script / ("prd-state.ps1" if os.name == "nt" else "prd-state.sh")
    expected_script.write_text("# bundled prd helper\n", encoding="utf-8")
    expected_shared = bundled_shared / "prd-state.py"
    expected_shared.write_text("# bundled shared prd helper\n", encoding="utf-8")

    source_root = tmp_path / "source-without-helper"
    source_root.mkdir()
    monkeypatch.setattr(specify_cli, "_locate_core_pack", lambda: core_pack)
    monkeypatch.setattr(specify_cli, "_project_root_from_source", lambda: source_root)

    _interpreter, script_path = specify_cli._prd_helper_script()

    assert script_path == expected_script
    assert expected_shared.exists()
