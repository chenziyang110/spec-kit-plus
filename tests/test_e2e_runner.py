"""Native adapters plus real subprocess/SQLite E2E tests of a disposable CLI app.

Playwright JSON below is a labeled parser fixture, not browser-run evidence.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "scripts" / "shared"
# Import sibling helpers without importing the entire Specify CLI application.
for name in ("e2e_coverage", "e2e_runner"):
    spec = importlib.util.spec_from_file_location(name, SHARED / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
runner = sys.modules["e2e_runner"]
coverage = sys.modules["e2e_coverage"]

APP = '''import argparse, json, sqlite3
p = argparse.ArgumentParser()
p.add_argument("db")
p.add_argument("role", choices=["admin", "viewer"])
p.add_argument("amount", type=int)
a = p.parse_args()
with sqlite3.connect(a.db) as db:
    db.execute("create table if not exists orders (id text primary key, amount integer)")
    if a.role == "viewer":
        print(json.dumps({"denied": True, "count": db.execute("select count(*) from orders").fetchone()[0]}))
        raise SystemExit(3)
    db.execute("insert or ignore into orders values (?, ?)", ("order-one", a.amount))
    print(json.dumps(db.execute("select id, amount from orders").fetchall()))
'''


def save(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    (tmp_path / "app.py").write_text(APP, encoding="utf-8")
    model = {
        "schema_version": 1, "scope": "disposable CLI fixture", "source_revision": "fixture-one",
        "sources": [runner.file_record(tmp_path, "app.py")], "exclusions": [],
        "requirements": [{"id": "R1", "source": "app.py", "assertion": "permissions and exactly-once persistence"}],
        "journeys": [{"id": "orders", "requirements": ["R1"],
                      "steps": ["submit", "submit again", "read persisted state"],
                      "factors": {"role": ["admin", "viewer"], "amount": ["0", "10"]},
                      "strength": "exhaustive"}],
    }
    planned = coverage.plan(model, tmp_path)
    params = [(c["id"], c["parameters"]["role"], c["parameters"]["amount"]) for c in planned["cases"]]
    tests = '''import json, subprocess, sys
from pathlib import Path
import pytest
PARAMS = %r
@pytest.mark.parametrize("identity,role,amount", PARAMS, ids=[p[0] for p in PARAMS])
def test_order(identity, role, amount, tmp_path):
    argv = [sys.executable, "-S", "app.py", str(tmp_path / "orders.db"), role, amount]
    for attempt in range(2):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=5)
        if role == "viewer":
            assert result.returncode == 3
            assert json.loads(result.stdout) == {"denied": True, "count": 0}
        else:
            assert result.returncode == 0
            assert json.loads(result.stdout) == [["order-one", int(amount)]]
''' % params
    (tmp_path / "test_app.py").write_text(tests, encoding="utf-8")
    bindings = {
        "schema_version": 1, "manifest_sha256": planned["manifest_sha256"],
        "test_sources": [runner.file_record(tmp_path, "test_app.py")],
        "cases": [{"id": c["id"], "test_ref": "test_app.py",
                   "selector": f'test_app.py::test_order[{c["id"]}]',
                   "asserted_requirements": c["requirements"]} for c in planned["cases"]],
    }
    save(tmp_path / "manifest.json", model)
    save(tmp_path / "bindings.json", bindings)
    return tmp_path, model, planned, bindings


def launch(project, name="run", extra=None, timeout=30):
    root, _, _, bindings = project
    save(root / "bindings.json", bindings)
    return runner.execute(root / "manifest.json", root / "bindings.json", root,
                          f"test-results/{name}", "pytest", "disposable-local-cli",
                          ["test_app.py", "-q", *(extra or [])], timeout)


def modify_test(project, insertion):
    root, _, _, bindings = project
    path = root / "test_app.py"
    path.write_text(path.read_text().replace("    argv =", insertion + "\n    argv ="), encoding="utf-8")
    bindings["test_sources"] = [runner.file_record(root, "test_app.py")]


def test_real_cli_app_runs_all_cases_with_immutable_evidence(project):
    root, _, planned, _ = project
    report = launch(project)
    assert report["claim"] == "complete_against_frozen_scope"
    assert report["statuses"]["passed"] == len(planned["cases"]) == 4
    saved = coverage.load(root / "test-results/run/results.json")
    native = coverage.load(root / "test-results/run/native-report.json")
    assert len(native["events"]) == 12
    assert saved["run_id"] == native["run_id"]
    coverage.verify_files(root, saved["evidence"], "saved evidence")
    assert saved["command"][:3] == [sys.executable, "-m", "pytest"]
    with pytest.raises(FileExistsError):
        launch(project)


def test_filtered_collection_leaves_missing_cases_not_run(project):
    identity = project[2]["cases"][0]["id"]
    report = launch(project, extra=["-k", identity])
    assert report["claim"] == "incomplete"
    assert report["statuses"]["passed"] == 1
    assert report["statuses"]["not_run"] == 3
    assert report["journeys"][0]["missing_interactions"]


@pytest.mark.parametrize("statement,status", [
    ('pytest.skip("fixture skip")', "skipped"),
    ('pytest.xfail("fixture expected failure")', "skipped"),
    ('pytest.fail("fixture real failure")', "failed"),
])
def test_actual_pytest_nonpass_never_closes(project, statement, status):
    modify_test(project, "    " + statement)
    report = launch(project)
    assert report["claim"] == "incomplete"
    assert report["statuses"][status] == 4


def test_actual_xpass_is_not_clean_pass(project):
    root, _, _, bindings = project
    path = root / "test_app.py"
    path.write_text(path.read_text().replace('@pytest.mark.parametrize', '@pytest.mark.xfail(reason="known fixture", strict=False)\n@pytest.mark.parametrize'), encoding="utf-8")
    bindings["test_sources"] = [runner.file_record(root, "test_app.py")]
    report = launch(project)
    assert report["claim"] == "incomplete"
    assert report["statuses"]["passed"] == 0


def test_actual_teardown_failure_cannot_hide_passing_calls(project):
    root, _, _, bindings = project
    path = root / "test_app.py"
    path.write_text(path.read_text() + '\n@pytest.fixture(autouse=True)\ndef broken_teardown():\n    yield\n    pytest.fail("fixture teardown failure")\n', encoding="utf-8")
    bindings["test_sources"] = [runner.file_record(root, "test_app.py")]
    report = launch(project)
    assert report["statuses"]["failed"] == 4
    assert report["runner_exit_code"] != 0


@pytest.mark.parametrize("path", ["app.py", "test_app.py"])
def test_source_or_test_drift_during_execution_is_rejected(project, path):
    modify_test(project, f'    Path({path!r}).open("a").write("\\n# changed during run\\n")')
    with pytest.raises(coverage.CoverageError, match="post-run"):
        launch(project)
    assert not (project[0] / "test-results/run/coverage.json").exists()
    assert coverage.load(project[0] / "test-results/run/error.json")["claim"] == "invalid"


def test_disabled_reporter_cannot_reuse_stale_evidence(project):
    with pytest.raises(coverage.CoverageError, match="fresh native report"):
        launch(project, extra=["-p", "no:e2e_pytest_reporter"])


def test_timeout_is_invalid_and_retains_diagnostic(project):
    modify_test(project, '    __import__("time").sleep(20)')
    with pytest.raises(coverage.CoverageError, match="timed out"):
        launch(project, timeout=0.1)
    assert (project[0] / "test-results/run/error.json").exists()


def test_collection_only_cannot_claim_execution(project):
    report = launch(project, extra=["--collect-only"])
    assert report["claim"] == "incomplete"
    assert report["statuses"]["not_run"] == 4


def test_real_wrapper_cli_uses_real_exit_codes(project):
    root = project[0]
    argv = [sys.executable, str(SHARED / "e2e_runner.py"), str(root / "manifest.json"),
            "--bindings", str(root / "bindings.json"), "--root", str(root),
            "--runner", "pytest", "--target", "local-fixture", "--output-dir", "test-results/cli",
            "--", "test_app.py", "-q", "-k", project[2]["cases"][0]["id"]]
    result = subprocess.run(argv, text=True, capture_output=True, timeout=30)
    assert result.returncode == 1, result.stderr
    assert json.loads(result.stdout)["statuses"]["not_run"] == 3
    result = subprocess.run(argv, text=True, capture_output=True, timeout=30)
    assert result.returncode == 2
    assert json.loads(result.stderr)["claim"] == "invalid"


@pytest.mark.parametrize("path", ["../a", "/tmp/a", "C:/a", "C:\\a", "a\\b", "a/../b", "a//b", "./b", "a/"])
def test_cross_platform_path_rejection(path):
    with pytest.raises(coverage.CoverageError):
        runner.relative_name(path)


@pytest.mark.parametrize("change", ["missing", "extra", "stale", "assertion", "source", "selector", "project"])
def test_bindings_fail_before_start(project, change):
    root, _, planned, bindings = project
    if change == "missing":
        bindings["cases"].pop()
    elif change == "extra":
        bindings["cases"].append({"id": "E2E-" + "a" * 24})
    elif change == "stale":
        bindings["manifest_sha256"] = "stale"
    elif change == "assertion":
        bindings["cases"][0]["asserted_requirements"] = ["R99"]
    elif change == "source":
        bindings["cases"][0]["test_ref"] = "app.py"
    elif change == "selector":
        bindings["cases"][0]["selector"] = "no case id"
    else:
        bindings["cases"][0]["project"] = "chromium"
    with pytest.raises(coverage.CoverageError):
        runner.validate_bindings(bindings, planned, root, "pytest")
    assert not (root / "test-results").exists()


def pw_fixture(project):
    root, _, _, bindings = project
    bindings = deepcopy(bindings)
    for b in bindings["cases"]:
        b["selector"] = "checkout " + b["id"]
        b["project"] = "chromium"
    by_id = {b["id"]: b for b in bindings["cases"]}
    report = {"config": {"rootDir": str(root)}, "errors": [], "suites": [{"specs": [
        {"title": b["selector"], "file": b["test_ref"], "tests": [{
            "projectName": "chromium", "expectedStatus": "passed", "status": "expected",
            "results": [{"retry": 0, "status": "passed", "errors": []}]}]}
        for b in bindings["cases"]]}]}
    return report, by_id


def test_playwright_parser_fixture_clean_pass(project):
    report, bindings = pw_fixture(project)
    assert set(runner.playwright_outcomes(report, bindings, project[0]).values()) == {"passed"}


@pytest.mark.parametrize("change,expected", [
    ("retry", "flaky"), ("retry-only", "flaky"), ("skip", "skipped"),
    ("xfail", "skipped"), ("timeout", "failed"), ("no-results", "not_run"),
    ("errors", "not_run"),
])
def test_playwright_parser_fixture_nonpass(project, change, expected):
    report, bindings = pw_fixture(project)
    test = report["suites"][0]["specs"][0]["tests"][0]
    identity = next(iter(bindings))
    if change == "retry":
        test["results"].insert(0, {"status": "failed", "retry": 0})
        test["results"][-1]["retry"] = 1
    elif change == "retry-only":
        test["results"][0]["retry"] = 1
    elif change == "skip":
        test["results"][0]["status"] = "skipped"
    elif change == "xfail":
        test["expectedStatus"] = "failed"
    elif change == "timeout":
        test["results"][0]["status"] = "timedOut"
    elif change == "errors":
        test["results"][0]["errors"] = [{"message": "teardown failed"}]
    else:
        test["results"] = []
    assert runner.playwright_outcomes(report, bindings, project[0])[identity] == expected


@pytest.mark.parametrize("change", ["duplicate", "wrong-project", "wrong-source", "global-error", "bad-status", "zero-tests"])
def test_playwright_parser_fixture_rejects_drift(project, change):
    report, bindings = pw_fixture(project)
    spec = report["suites"][0]["specs"][0]
    if change == "duplicate":
        report["suites"][0]["specs"].append(deepcopy(spec))
    elif change == "wrong-project":
        spec["tests"][0]["projectName"] = "firefox"
    elif change == "wrong-source":
        spec["file"] = "app.py"
    elif change == "global-error":
        report["errors"] = [{"message": "global teardown failed"}]
    elif change == "bad-status":
        spec["tests"][0]["results"][0]["status"] = "ok"
    else:
        report["suites"] = []
    with pytest.raises(coverage.CoverageError):
        runner.playwright_outcomes(report, bindings, project[0])


def test_pytest_native_retry_and_missing_phase_are_not_passes(project):
    root, _, _, binding_value = project
    bindings = {b["id"]: b for b in binding_value["cases"]}
    binding = next(iter(bindings.values()))
    event = {"nodeid": binding["selector"], "file": "test_app.py", "phase": "call", "outcome": "passed", "wasxfail": False}
    report = {"schema_version": 1, "runner": "pytest", "run_id": "fixture", "exit_code": 0,
              "errors": [], "collected": [binding["selector"]], "events": [event]}
    assert runner.pytest_outcomes(report, bindings, "fixture", 0)[binding["id"]] == "not_run"
    report["events"] = [dict(event, phase="setup"), event, dict(event, phase="teardown"), event]
    assert runner.pytest_outcomes(report, bindings, "fixture", 0)[binding["id"]] == "flaky"
    with pytest.raises(coverage.CoverageError, match="another run"):
        runner.pytest_outcomes(report, bindings, "stale", 0)
    with pytest.raises(coverage.CoverageError, match="exit mismatch"):
        runner.pytest_outcomes(report, bindings, "fixture", 1)


def test_playwright_parser_fixture_failed_retries_remain_failed(project):
    report, bindings = pw_fixture(project)
    report["suites"][0]["specs"][0]["tests"][0]["results"] = [
        {"retry": 0, "status": "failed"}, {"retry": 1, "status": "failed"}]
    assert runner.playwright_outcomes(report, bindings, project[0])[next(iter(bindings))] == "failed"


def test_pytest_parser_fixture_failed_then_passed_retains_flaky(project):
    bindings = {b["id"]: b for b in project[3]["cases"]}
    binding = next(iter(bindings.values()))
    event = {"nodeid": binding["selector"], "file": "test_app.py", "phase": "call", "outcome": "passed", "wasxfail": False}
    events = [dict(event, phase="setup"), dict(event, outcome="failed"), dict(event, phase="teardown"),
              dict(event, phase="setup"), event, dict(event, phase="teardown")]
    report = {"schema_version": 1, "runner": "pytest", "run_id": "fixture", "exit_code": 0,
              "errors": [], "collected": [binding["selector"]], "events": events}
    assert runner.pytest_outcomes(report, bindings, "fixture", 0)[binding["id"]] == "flaky"


def test_output_cannot_use_workflow_state_directories(project):
    root = project[0]
    with pytest.raises(coverage.CoverageError, match="inside test-results"):
        runner.execute(root / "manifest.json", root / "bindings.json", root,
                       ".specify/run", "pytest", "fixture", ["test_app.py"])
    assert not (root / ".specify").exists()


def test_unknown_collection_is_not_ignored(project):
    bindings = {b["id"]: b for b in project[3]["cases"]}
    report = {"schema_version": 1, "runner": "pytest", "run_id": "fixture", "exit_code": 0,
              "errors": [], "collected": ["test_app.py::untracked_test"], "events": []}
    with pytest.raises(coverage.CoverageError, match="exactly one"):
        runner.pytest_outcomes(report, bindings, "fixture", 0)
