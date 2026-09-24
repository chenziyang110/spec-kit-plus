"""Check additive CI coverage without weakening the original test gates."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.load((ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_original_check_surfaces_preserved():
    jobs = WORKFLOW["jobs"]
    assert {"ruff", "pytest", "go"} <= jobs.keys()
    assert jobs["go"]["runs-on"] == "ubuntu-latest"
    assert jobs["pytest"]["strategy"]["matrix"]["python-version"] == ["3.11", "3.12", "3.13"]
    assert WORKFLOW["permissions"] == {"contents": "read"}


def test_tests_not_hidden_by_fail_fast_or_continue_on_error():
    assert WORKFLOW["jobs"]["pytest"]["strategy"]["fail-fast"] == "false"
    assert WORKFLOW["jobs"]["native"]["strategy"]["fail-fast"] == "false"
    for job in WORKFLOW["jobs"].values():
        assert "continue-on-error" not in job
        for step in job["steps"]:
            assert "continue-on-error" not in step


def test_native_jobs_run_tests_not_just_cross_compile():
    native = WORKFLOW["jobs"]["native"]
    assert native["strategy"]["matrix"]["os"] == ["windows-latest", "macos-latest"]
    commands = "\n".join(step.get("run", "") for step in native["steps"])
    assert "go test -count=1 -json ./..." in commands
    assert "pytest tests/integrations/test_quick_optimization_installation.py" in commands
    assert "go vet ./..." in commands


def test_json_log_pipelines_use_explicit_bash():
    for name in ("go", "native"):
        assert WORKFLOW["jobs"][name]["defaults"]["run"]["shell"] == "bash"


def test_reports_bind_source_and_preserve_failure_evidence():
    for name in ("pytest", "go", "native"):
        steps = WORKFLOW["jobs"][name]["steps"]
        assert any("git rev-parse HEAD" in step.get("run", "") for step in steps)
        uploads = [step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@")]
        assert len(uploads) == 1
        assert uploads[0]["if"] == "${{ !cancelled() }}"
        assert uploads[0]["with"]["if-no-files-found"] == "error"
        assert "test-source.txt" in uploads[0]["with"]["path"]
