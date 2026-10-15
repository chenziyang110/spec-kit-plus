"""Execute the actual CI lock steps with real uv in offline disposable projects.

No Specify source dependency is installed: this tests lock preparation, freezing
and evidence continuity, not a real specify-cli wheel or cloud CI execution.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/e2e-distribution.yml"
PREPARE = "Prepare and record the dependency lock"
VERIFY = "Verify the dependency lock stayed unchanged"
PROJECT = '''[project]
name = "e2e-lock-fixture"
version = "0.0.0"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
test = []
'''


def steps():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["wheel"]["steps"]


def script(name):
    return next(step["run"] for step in steps() if step.get("name") == name)


def invoke(argv, fixture):
    project, _, env = fixture
    # Windows can resolve a bare "bash" to System32's WSL launcher before PATH.
    # Bind the executable to the fixture PATH, including its native Git Bash.
    executable = shutil.which(argv[0], path=env["PATH"])
    assert executable is not None, f"Required executable is missing: {argv[0]}"
    return subprocess.run([executable, *argv[1:]], cwd=project, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="backslashreplace",
                          timeout=30, check=False)


def run_step(name, fixture):
    return invoke(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script(name)], fixture)


def passed(result):
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


@pytest.fixture
def lock_project(tmp_path):
    if not shutil.which("uv") or not shutil.which("bash"):
        pytest.skip("The CI lock integration checks require uv and bash")
    project = tmp_path / "project with spaces"
    evidence = tmp_path / "evidence with spaces"
    project.mkdir()
    evidence.mkdir()
    (project / "pyproject.toml").write_text(PROJECT, encoding="utf-8")
    (evidence / "source.txt").write_text("fixture-source-not-a-git-commit\n", encoding="utf-8")
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("UV_") and key not in {"VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME"}}
    env.update(UV_OFFLINE="1", UV_PYTHON_DOWNLOADS="never", UV_PYTHON=sys.executable,
               UV_CACHE_DIR=str(tmp_path / "isolated-cache"), E2E_WORK=evidence.as_posix(),
               PATH=str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", ""))
    return project, evidence, env


def test_frozen_sync_without_lock_reproduces_the_clean_checkout_failure(lock_project):
    result = invoke(["uv", "sync", "--frozen", "--extra", "test"], lock_project)
    assert result.returncode != 0
    assert "lockfile" in result.stderr.lower() and "--frozen" in result.stderr
    assert not (lock_project[0] / "uv.lock").exists()


def test_actual_prepare_allows_frozen_sync_run_and_export(lock_project):
    project, evidence, _ = lock_project
    passed(run_step(PREPARE, lock_project))
    lock = (project / "uv.lock").read_bytes()
    assert lock == (evidence / "uv.lock").read_bytes()
    record = json.loads((evidence / "dependency-lock.json").read_text(encoding="utf-8"))
    assert record["origin"] == "resolved-for-run"
    assert record["lock_sha256"] == hashlib.sha256(lock).hexdigest()
    assert record["source_revision"] == "fixture-source-not-a-git-commit"
    passed(invoke(["uv", "sync", "--frozen", "--extra", "test"], lock_project))
    ran = invoke(["uv", "run", "--frozen", "--extra", "test", "python", "-c",
                  "print('dependency-free fixture executed')"], lock_project)
    passed(ran)
    assert "dependency-free fixture executed" in ran.stdout
    passed(invoke(["uv", "export", "--frozen", "--no-dev", "--no-emit-project",
                   "--output-file", str(evidence / "dependencies.txt")], lock_project))
    passed(run_step(VERIFY, lock_project))
    assert (project / "uv.lock").read_bytes() == lock


def test_existing_valid_lock_is_checked_without_rewriting(lock_project):
    project, evidence, _ = lock_project
    passed(invoke(["uv", "lock"], lock_project))
    before = (project / "uv.lock").read_bytes()
    passed(run_step(PREPARE, lock_project))
    assert (project / "uv.lock").read_bytes() == before
    assert (evidence / "uv.lock").read_bytes() == before
    assert json.loads((evidence / "dependency-lock.json").read_text())["origin"] == "validated-existing"


@pytest.mark.parametrize("condition", ["stale", "malformed"])
def test_existing_invalid_lock_is_not_silently_regenerated(lock_project, condition):
    project, evidence, _ = lock_project
    passed(invoke(["uv", "lock"], lock_project))
    lock = project / "uv.lock"
    if condition == "stale":
        (project / "pyproject.toml").write_text(PROJECT.replace('"0.0.0"', '"0.0.1"'), encoding="utf-8")
    else:
        lock.write_text("This is not a TOML lockfile!", encoding="utf-8")
    before = lock.read_bytes()
    assert run_step(PREPARE, lock_project).returncode != 0
    assert lock.read_bytes() == before
    assert not (evidence / "uv.lock").exists()
    assert not (evidence / "dependency-lock.json").exists()


@pytest.mark.parametrize("changed", ["current", "snapshot", "record", "project", "source", "missing"])
def test_actual_final_step_rejects_dependency_evidence_drift(lock_project, changed):
    project, evidence, _ = lock_project
    passed(run_step(PREPARE, lock_project))
    targets = {"current": project / "uv.lock", "snapshot": evidence / "uv.lock",
               "project": project / "pyproject.toml", "source": evidence / "source.txt"}
    if changed == "record":
        path = evidence / "dependency-lock.json"
        record = json.loads(path.read_text())
        record["lock_sha256"] = "0" * 64
        path.write_text(json.dumps(record))
    elif changed == "missing":
        (project / "uv.lock").unlink()
    else:
        path = targets[changed]
        path.write_bytes(path.read_bytes() + b"\n# changed during verification\n")
    assert run_step(VERIFY, lock_project).returncode != 0


def test_prepare_refuses_to_overwrite_previous_dependency_evidence(lock_project):
    _, evidence, _ = lock_project
    passed(run_step(PREPARE, lock_project))
    before = {p.name: p.read_bytes() for p in evidence.iterdir()}
    assert run_step(PREPARE, lock_project).returncode != 0
    assert {p.name: p.read_bytes() for p in evidence.iterdir()} == before


def test_workflow_keeps_frozen_consumers_and_all_existing_installation_gates():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"]["wheel"]
    expected = {("ubuntu-latest", "3.11"), ("ubuntu-latest", "3.12"),
                ("ubuntu-latest", "3.13"), ("windows-latest", "3.13"), ("macos-latest", "3.13")}
    assert {(row["os"], row["python"]) for row in job["strategy"]["matrix"]["include"]} == expected
    ordered = [step.get("name") for step in job["steps"]]
    assert ordered.index(PREPARE) < ordered.index("Sync the repository test environment without changing the lock")
    assert ordered.index(VERIFY) > ordered.index("Exercise wheel-only init, both upgrade orders, user edits and repair")
    all_runs = "\n".join(step.get("run", "") for step in job["steps"])
    assert "uv sync --frozen --extra test" in all_runs
    assert "uv run --frozen --extra test --with hatchling pytest" in all_runs
    assert "uv run --frozen --extra test python" in all_runs
    assert "uv export --frozen" in all_runs
    for path in ("tests/integrations/test_e2e_installation.py", "tests/test_e2e_registration.py",
                 "tests/test_e2e_wheel_verifier.py", "tests/test_e2e_wheel_snapshot.py",
                 "tests/test_e2e_distribution_lock.py", "tests/e2e_samples/wheel_install_probe.py"):
        assert path in all_runs
    assert "--expected-wheel-sha256" in all_runs
    assert "Installation evidence is empty, skipped or failing" in all_runs
    artifact = next(step for step in job["steps"] if str(step.get("uses", "")).startswith("actions/upload-artifact@"))
    assert "/uv.lock" in artifact["with"]["path"]
    assert "/dependency-lock.json" in artifact["with"]["path"]
    assert "/probe/*.json" in artifact["with"]["path"]
    assert artifact["with"]["if-no-files-found"] == "error"
    assert workflow["permissions"] == {"contents": "read"}
    assert not any(step.get("continue-on-error") for step in job["steps"])
