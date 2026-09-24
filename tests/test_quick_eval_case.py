"""Exercise real fixture preparation and frozen checks, not an Agent benchmark."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/workflow-quality/quick_eval_case.py"
spec = importlib.util.spec_from_file_location("quick_eval_case", SCRIPT)
case_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case_tool)
SOLUTIONS = json.loads((ROOT / "tests/quick_fixture_reference.json").read_text())


@pytest.mark.parametrize("case_id", sorted(SOLUTIONS))
def test_frozen_oracle_rejects_baseline_and_accepts_reference(tmp_path, case_id):
    target = tmp_path / case_id
    case_tool.prepare(case_id, target)
    assert case_tool.verify(case_id, target)["verification_status"] == "failed"
    for name, content in SOLUTIONS[case_id].items():
        (target / "project" / name).write_text(content, encoding="utf-8")
    report = case_tool.verify(case_id, target)
    assert report["verification_status"] == "passed", report
    assert report["oracle_completed"] is True
    assert report["accepted"] is None
    assert report["input_tokens"] is None
    assert report["agent_executed"] is None
    assert report["agent_launched_by_helper"] is False


def test_snapshot_is_repeatable_and_prepare_is_create_only(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    assert case_tool.prepare("Q001", one) == case_tool.prepare("Q001", two)
    with pytest.raises(FileExistsError):
        case_tool.prepare("Q001", one)
    assert (one / "project/config.py").exists()


def test_binding_change_is_rejected(tmp_path):
    case_tool.prepare("Q001", tmp_path / "run")
    (tmp_path / "run/TASK.md").write_text("different task")
    with pytest.raises(ValueError, match="binding changed"):
        case_tool.verify("Q001", tmp_path / "run")


def test_scope_and_symlink_checks(tmp_path):
    target = tmp_path / "run"
    case_tool.prepare("Q001", target)
    bad = target / "project/extra.py"
    bad.write_text("outside scope")
    with pytest.raises(ValueError, match="out-of-scope"):
        case_tool.verify("Q001", target)
    bad.unlink()
    try:
        bad.symlink_to(target / "project/config.py")
    except OSError:
        pytest.skip("Symlink creation is unavailable on this host")
    with pytest.raises(ValueError, match="symlinks"):
        case_tool.verify("Q001", target)


def test_exit_zero_without_oracle_completion_is_not_pass(tmp_path):
    target = tmp_path / "run"
    case_tool.prepare("Q001", target)
    (target / "project/config.py").write_text("import os\nos._exit(0)\n")
    report = case_tool.verify("Q001", target)
    assert report["exit_code"] == 0
    assert report["verification_status"] == "failed"
    assert report["oracle_completed"] is False


def test_real_case_cli(tmp_path):
    target = tmp_path / "run"
    prep = subprocess.run([sys.executable, str(SCRIPT), "prepare", "Q001", str(target)], text=True, capture_output=True, timeout=20)
    assert prep.returncode == 0, prep.stderr
    result = subprocess.run([sys.executable, str(SCRIPT), "verify", "Q001", str(target)], text=True, capture_output=True, timeout=20)
    assert result.returncode == 1
    assert json.loads(result.stdout)["accepted"] is None


def test_checks_scope_again_after_running_project_code(tmp_path):
    target = tmp_path / "run"
    case_tool.prepare("Q001", target)
    (target / "project/config.py").write_text(
        "from pathlib import Path\nPath('extra.py').write_text('unexpected')\nTIMEOUT_SECONDS = 45\nRETRIES = 3\n"
    )
    with pytest.raises(ValueError, match="out-of-scope"):
        case_tool.verify("Q001", target)


def test_prepare_refuses_source_checkout():
    with pytest.raises(ValueError, match="outside"):
        case_tool.prepare("Q001", ROOT / "must-not-create-fixture")
    assert not (ROOT / "must-not-create-fixture").exists()


def test_fixture_ids_match_existing_task_catalog():
    import yaml
    catalog = yaml.safe_load((ROOT / "evals/quick/tasks.yaml").read_text())
    bundle = json.loads(case_tool.BUNDLE.read_text())
    assert {item["id"] for item in catalog["tasks"]} == set(bundle["cases"]) == set(SOLUTIONS)
