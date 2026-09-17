"""Real log/CLI/Go/Git checks of the verifier, not product integration evidence."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/workflow-quality/verify_quick_rollout.py"
spec = importlib.util.spec_from_file_location("quick_rollout_evidence_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
MODULE = "example.invalid/rollout"


def events(package=MODULE, cases=None):
    cases = runner.GO_CASES if cases is None else cases
    return [{"Action": "pass", "Package": package, "Test": name} for name in cases] + [
        {"Action": "pass", "Package": package}]


def write_log(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def test_all_thirteen_shadow_entrypoints_are_required():
    assert len(runner.SHADOW_ENTRYPOINT_CASES) == 13
    assert len(set(runner.SHADOW_ENTRYPOINT_CASES)) == 13
    assert set(runner.SHADOW_ENTRYPOINT_CASES) <= set(runner.GO_CASES)


@pytest.mark.parametrize("missing", runner.SHADOW_ENTRYPOINT_CASES)
def test_each_missing_entrypoint_blocks(tmp_path, missing):
    path = write_log(tmp_path / "go.jsonl", [e for e in events() if e.get("Test") != missing])
    with pytest.raises(runner.EvidenceError, match="Required Go"):
        runner.inspect_go_log(path, MODULE)


@pytest.mark.parametrize("action", ["run", "output", "pause", "cont"])
def test_unfinished_test_blocks_even_after_root_pass(tmp_path, action):
    rows = [{"Action": action, "Package": MODULE, "Test": "TestUnfinished"}] + events()
    with pytest.raises(runner.EvidenceError, match="unfinished"):
        runner.inspect_go_log(write_log(tmp_path / "go.jsonl", rows), MODULE)


def test_started_or_entirely_missing_package_cannot_disappear(tmp_path):
    path = tmp_path / "go.jsonl"
    write_log(path, events() + [{"Action": "start", "Package": MODULE + "/other"}])
    with pytest.raises(runner.EvidenceError, match="unfinished"):
        runner.inspect_go_log(path, MODULE)
    write_log(path, events())
    with pytest.raises(runner.EvidenceError, match="inventoried"):
        runner.inspect_go_log(path, MODULE, expected_packages=(MODULE, MODULE + "/other"))


def test_package_with_tests_cannot_skip_but_no_test_package_can(tmp_path):
    other = MODULE + "/other"
    path = write_log(tmp_path / "go.jsonl", events() + [{"Action": "skip", "Package": other}])
    assert runner.inspect_go_log(path, MODULE)["fail"] == 0
    with pytest.raises(runner.EvidenceError, match="inventoried"):
        runner.inspect_go_log(path, MODULE, expected_packages=(MODULE, other))


@pytest.mark.parametrize("bad", [
    '{"Action":"fail","Action":"pass","Package":"x"}',
    '{"Action":"pass","Package":"x","Package":"y"}',
    '{"Action":"output","Package":"x","Elapsed":NaN}',
    '{"Action":"output","Package":"x","Elapsed":Infinity}',
    '{"Action":null,"Package":"x"}',
    '{"Action":"run","Package":[],"Test":"T"}',
    '{"Action":"output","Package":"x","Test":null}',
])
def test_ambiguous_or_malformed_events_are_rejected(tmp_path, bad):
    path = write_log(tmp_path / "go.jsonl", events())
    with path.open("a") as stream:
        stream.write(bad + "\n")
    with pytest.raises(runner.EvidenceError):
        runner.inspect_go_log(path, MODULE)


def test_newer_go_build_events_fail_closed(tmp_path):
    path = write_log(tmp_path / "go.jsonl", events() + [
        {"Action": "build-output", "ImportPath": MODULE + "/other", "Output": "build diagnostic"},
        {"Action": "build-fail", "ImportPath": MODULE + "/other"}])
    with pytest.raises(runner.EvidenceError, match="did not pass"):
        runner.inspect_go_log(path, MODULE)


@pytest.mark.parametrize("value", ["", "foreign/only\n", MODULE + "\n" + MODULE + "\n",
                                        MODULE + "\n" + MODULE + "/with space\n"])
def test_bad_package_inventory_rejected(tmp_path, value):
    p = tmp_path / "packages.txt"
    p.write_text(value)
    with pytest.raises(runner.EvidenceError):
        runner.read_go_packages(p, MODULE)


def test_inventory_accepts_native_line_endings_and_blank_template_lines(tmp_path):
    p = tmp_path / "packages.txt"
    p.write_bytes((MODULE + "\r\n\r\n" + MODULE + "/context\r\n").encode())
    assert runner.read_go_packages(p, MODULE) == (MODULE, MODULE + "/context")


def test_required_context_cases_cannot_be_replaced_by_package_success(tmp_path):
    path = write_log(tmp_path / "go.jsonl", events() + events(MODULE + "/context", ()))
    with pytest.raises(runner.EvidenceError, match="/context"):
        runner.inspect_go_log(path, MODULE, required_groups=runner.required_go_groups(MODULE))


def inspector(log, inventory, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), "--inspect-go-log", str(log),
                           "--go-packages", str(inventory), "--module", MODULE, *extra],
                          text=True, capture_output=True, timeout=20)


def test_actual_inspector_cli_never_claims_to_execute_tests(tmp_path):
    log, inventory = tmp_path / "go.jsonl", tmp_path / "packages.txt"
    inventory.write_text(MODULE + "\n" + MODULE + "/context\n")
    write_log(log, events() + events(MODULE + "/context", runner.CONTEXT_CASES))
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    run = inspector(log, inventory)
    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report["status"] == "passed"
    assert report["tests_executed_by_inspector"] is False
    assert report["release_authorized"] is False
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    write_log(log, events())
    run = inspector(log, inventory)
    assert run.returncode == 1
    assert json.loads(run.stdout)["status"] == "failed"
    assert "Traceback" not in run.stderr


def test_inspector_missing_files_cannot_pass(tmp_path):
    result = inspector(tmp_path / "missing-log", tmp_path / "missing-inventory")
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "failed"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(not shutil.which("go"), reason="local Go toolchain required")
def test_real_two_package_go_run_and_truncated_copy(tmp_path):
    # This runs a whole tiny stdlib-only module, not spec-kit-plus's runtime.
    (tmp_path / "go.mod").write_text(f"module {MODULE}\n\ngo 1.20\n")
    (tmp_path / "main_test.go").write_text('package fixture\nimport "testing"\nfunc TestRoot(t *testing.T) {}\n')
    (tmp_path / "child").mkdir()
    (tmp_path / "child/child_test.go").write_text(
        'package child\nimport "testing"\nfunc TestChild(t *testing.T) {}\n'
        'func TestNativeSkip(t *testing.T) {t.Skip("platform fixture")}\n')
    env = runner.checkout_environment()
    env.update(GOWORK="off", GOTOOLCHAIN="local", GOPROXY="off", GOFLAGS="")
    packages = runner.execute(["go", "list", "-f", runner.GO_TEST_PACKAGE_TEMPLATE, "./..."],
                              tmp_path, tmp_path, "inventory", 60, env)
    assert packages["status"] == "passed"
    expected = runner.read_go_packages(tmp_path / "inventory.stdout.log", MODULE)
    assert set(expected) == {MODULE, MODULE + "/child"}
    run = runner.execute(["go", "test", "-count=1", "-json", "./..."],
                         tmp_path, tmp_path, "actual", 60, env)
    assert run["exit_code"] == 0
    log = tmp_path / "actual.stdout.log"
    result = runner.inspect_go_log(log, MODULE, ("TestRoot",), expected_packages=expected,
                                   required_groups={MODULE + "/child": ("TestChild",)})
    assert result == {"pass": 2, "skip": 1, "fail": 0}
    # Real interleaved stream: remove only the child's terminal package record.
    data = [json.loads(line) for line in log.read_text().splitlines()]
    incomplete = [e for e in data if not (e["Package"] == MODULE + "/child" and
                                         e["Action"] == "pass" and "Test" not in e)]
    with pytest.raises(runner.EvidenceError, match="unfinished"):
        runner.inspect_go_log(write_log(tmp_path / "truncated.jsonl", incomplete), MODULE,
                              ("TestRoot",), expected_packages=expected)


@pytest.mark.skipif(not shutil.which("git"), reason="Git required")
def test_real_git_identity_cannot_be_redirected_by_environment(tmp_path, monkeypatch):
    repos = [tmp_path / "selected", tmp_path / "foreign"]
    expected = []
    for n, repo in enumerate(repos):
        repo.mkdir()
        env = runner.checkout_environment()
        for args in [("init", "-q"), ("-c", "user.name=fixture", "-c", "user.email=test@example.invalid",
                    "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + os.devnull,
                    "commit", "--allow-empty", "-qm", str(n))]:
            subprocess.run(["git", "-C", str(repo), *args], env=env, check=True, capture_output=True)
        expected.append(runner.git_value(repo, "rev-parse", "HEAD"))
    assert expected[0] != expected[1]
    monkeypatch.setenv("GIT_DIR", str(repos[1] / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(repos[0]))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.bare")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    assert runner.git_value(repos[0], "rev-parse", "HEAD") == expected[0]
    assert Path(runner.git_value(repos[0], "rev-parse", "--show-toplevel")) == repos[0]


@pytest.mark.parametrize("job_id", ["go", "native"])
def test_ci_uses_same_inventory_and_inspector_without_ignoring_errors(job_id):
    import yaml
    workflow = yaml.load((ROOT / ".github/workflows/test.yml").read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"][job_id]
    steps = job["steps"]
    names = [step["name"] for step in steps]
    assert names.index("Inventory runtime test packages") < names.index("Run native runtime tests")
    assert names.index("Run native runtime tests") < names.index("Verify required runtime evidence")
    inventory = steps[names.index("Inventory runtime test packages")]
    audit = steps[names.index("Verify required runtime evidence")]
    assert runner.GO_TEST_PACKAGE_TEMPLATE in inventory["run"]
    assert "--inspect-go-log go-test-results.jsonl" in audit["run"]
    assert "--go-packages go-test-packages.txt" in audit["run"]
    assert audit["if"] == "${{ !cancelled() }}"
    assert "continue-on-error" not in job
    assert all("continue-on-error" not in step for step in steps)
    assert "|| true" not in audit["run"]
    defaults = job.get("defaults", {}).get("run", {})
    assert audit.get("working-directory", defaults.get("working-directory")) == "tools/specify-runtime"
    uploads = [step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@")]
    for path in ("go-test-results.jsonl", "go-test-packages.txt", "go-evidence-audit.json", "test-source.txt"):
        assert path in uploads[0]["with"]["path"]


def test_inspector_supports_argparse_equals_form(tmp_path):
    result = subprocess.run([sys.executable, str(SCRIPT), f"--inspect-go-log={tmp_path / 'missing'}",
                             "--go-packages", str(tmp_path / "inventory"), "--module", MODULE],
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 1
    assert json.loads(result.stdout)["schema"] == "quick-go-evidence-v1"



def test_completed_benchmark_is_not_a_required_test_pass(tmp_path):
    rows = events() + [
        {"Action": "output", "Package": MODULE, "Test": "BenchmarkExample", "Output": "diagnostic"},
        {"Action": "bench", "Package": MODULE, "Test": "BenchmarkExample"},
    ]
    path = write_log(tmp_path / "go.jsonl", rows)
    assert runner.inspect_go_log(path, MODULE)["pass"] == len(runner.GO_CASES)
    with pytest.raises(runner.EvidenceError, match="Required Go"):
        runner.inspect_go_log(path, MODULE, ("BenchmarkExample",))
