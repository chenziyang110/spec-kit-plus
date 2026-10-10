"""Audit shared evidence without per-case file reads or stale closeout claims."""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("e2e_evidence_subject", ROOT / "scripts/shared/e2e_coverage.py")
e2e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e2e)


def record(root, name, content=b"fixture"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {"path": name, "sha256": hashlib.sha256(content).hexdigest()}


def frozen_run(root, count=4):
    source = record(root, "app.txt")
    test = record(root, "test.txt")
    evidence = record(root, "evidence/shared.bin", b"shared log\x00" * 4096)
    model = {
        "schema_version": 1, "scope": "evidence I/O fixture", "source_revision": "fixture-v1",
        "sources": [source], "requirements": [{"id": "R1", "source": "app.txt", "assertion": "unchanged"}],
        "journeys": [{"id": "j", "requirements": ["R1"], "steps": ["act", "observe"],
                      "factors": {"value": [str(i) for i in range(count)]}, "strength": "exhaustive"}],
    }
    planned = e2e.plan(model, root)
    results = {
        "schema_version": 1, "manifest_sha256": planned["manifest_sha256"], "source_revision": "fixture-v1",
        "run_id": "fixture", "target": "fixture", "started_at": "2026-10-10T00:00:00Z",
        "finished_at": "2026-10-10T00:00:01Z", "command": ["fixture"], "exit_code": 0,
        "test_sources": [test], "evidence": [deepcopy(evidence)],
        "cases": [dict(id=c["id"], status="passed", test_ref="test.txt", asserted_requirements=["R1"],
                       evidence=[deepcopy(evidence)]) for c in planned["cases"]],
    }
    return model, results


@pytest.mark.parametrize("count", [1, 8, 64, 1000])
def test_shared_evidence_has_two_reads_regardless_of_case_count(tmp_path, monkeypatch, count):
    model, results = frozen_run(tmp_path, count)
    counts = Counter()
    original = Path.open
    def counted(path, *args, **kwargs):
        if path == tmp_path / "evidence/shared.bin":
            counts["shared"] += 1
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", counted)
    report = e2e.audit(model, results, tmp_path)
    assert report["statuses"]["passed"] == count
    assert counts["shared"] == 2  # First use and a mandatory fresh closeout read.


@pytest.mark.parametrize("victim", ["app.txt", "test.txt", "evidence/shared.bin"])
@pytest.mark.parametrize("action", ["change", "delete", "replace"])
def test_late_drift_never_returns_a_completion_claim(tmp_path, monkeypatch, victim, action):
    model, results = frozen_run(tmp_path)
    tail = record(tmp_path, "evidence/tail.bin", b"last independent observation")
    results["cases"][-1]["evidence"] = [tail]
    original = Path.open
    fired = False
    def mutate_on_last_evidence(path, *args, **kwargs):
        nonlocal fired
        if path == tmp_path / tail["path"] and not fired:
            fired = True
            target = tmp_path / victim
            if action == "change":
                target.write_bytes(b"changed after initial validation")
            elif action == "delete":
                target.unlink()
            else:
                replacement = tmp_path / "replacement.bin"
                replacement.write_bytes(b"replacement object")
                replacement.replace(target)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", mutate_on_last_evidence)
    with pytest.raises((e2e.CoverageError, OSError)):
        e2e.audit(model, results, tmp_path)
    assert fired


@pytest.mark.parametrize("victim", ["app.txt", "test.txt", "evidence/shared.bin"])
def test_no_cross_invocation_cache(tmp_path, victim):
    model, results = frozen_run(tmp_path)
    assert e2e.audit(model, results, tmp_path)["claim"] == "complete_against_frozen_scope"
    (tmp_path / victim).write_bytes(b"changed between calls")
    with pytest.raises(e2e.CoverageError, match="stale or changed"):
        e2e.audit(model, results, tmp_path)


@pytest.mark.parametrize("mutation", ["wrong-sha", "invalid-sha", "unknown-field", "duplicate", "empty", "bad-entry"])
def test_each_case_record_is_validated_even_when_its_file_was_seen(tmp_path, mutation):
    model, results = frozen_run(tmp_path)
    last = results["cases"][-1]["evidence"]
    if mutation == "wrong-sha":
        last[0]["sha256"] = "0" * 64
    elif mutation == "invalid-sha":
        last[0]["sha256"] = "invalid"
    elif mutation == "unknown-field":
        last[0]["misspelled"] = True
    elif mutation == "duplicate":
        last.append(deepcopy(last[0]))
    elif mutation == "empty":
        last.clear()
    else:
        last[0] = "not an object"
    with pytest.raises(e2e.CoverageError):
        e2e.audit(model, results, tmp_path)


@pytest.mark.parametrize("status", ["passed", "failed", "skipped", "blocked", "not_run", "flaky", "absent"])
def test_optimization_keeps_every_status_and_full_scope(tmp_path, status):
    model, results = frozen_run(tmp_path)
    missing_id = results["cases"][0]["id"]
    if status == "absent":
        results["cases"].pop(0)
    else:
        results["cases"][0]["status"] = status
    before = deepcopy((model, results))
    report = e2e.audit(model, results, tmp_path)
    assert (model, results) == before
    assert report["planned_cases"] == 4
    assert sum(report["statuses"].values()) == 4
    assert report["claim"] == ("complete_against_frozen_scope" if status == "passed" else "incomplete")
    assert report["statuses"]["passed"] == (4 if status == "passed" else 3)
    if status != "passed":
        assert report["gaps"] == [{"id": missing_id, "journey": "j", "status": "not_run" if status == "absent" else status}]
        assert report["journeys"][0]["missing_interactions"]


def test_incomplete_run_still_rechecks_sources(tmp_path, monkeypatch):
    model, results = frozen_run(tmp_path)
    results["cases"] = []
    original = Path.open
    def changed_source(path, *args, **kwargs):
        if path == tmp_path / "evidence/shared.bin":
            (tmp_path / "app.txt").write_bytes(b"drift")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", changed_source)
    with pytest.raises(e2e.CoverageError, match="sources"):
        e2e.audit(model, results, tmp_path)


def test_public_verifier_reads_fresh_bytes_on_every_call(tmp_path):
    entry = record(tmp_path, "standalone.bin")
    assert e2e.verify_files(tmp_path, [entry], "direct") == {"standalone.bin"}
    (tmp_path / "standalone.bin").write_bytes(b"changed")
    with pytest.raises(e2e.CoverageError, match="direct"):
        e2e.verify_files(tmp_path, [entry], "direct")


def test_hashing_does_not_materialize_whole_files(tmp_path, monkeypatch):
    model, results = frozen_run(tmp_path)
    def forbidden_read_bytes(path):
        raise AssertionError("audit must stream files, not materialize complete reports")
    monkeypatch.setattr(Path, "read_bytes", forbidden_read_bytes)
    assert e2e.audit(model, results, tmp_path)["claim"] == "complete_against_frozen_scope"


def test_repeated_symlink_evidence_cannot_escape_at_closeout(tmp_path, monkeypatch):
    model, results = frozen_run(tmp_path)
    tail = record(tmp_path, "evidence/tail.bin")
    outside = tmp_path.parent / (tmp_path.name + "-outside.bin")
    outside.write_bytes(b"outside")
    results["cases"][-1]["evidence"] = [tail]
    original = Path.open
    fired = False
    def redirect(path, *args, **kwargs):
        nonlocal fired
        if path == tmp_path / tail["path"] and not fired:
            fired = True
            target = tmp_path / "evidence/shared.bin"
            target.unlink()
            try:
                target.symlink_to(outside)
            except (OSError, NotImplementedError):
                pytest.skip("platform does not permit symlinks")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", redirect)
    with pytest.raises(e2e.CoverageError, match="escapes root"):
        e2e.audit(model, results, tmp_path)
    assert fired


def test_benchmark_exercises_valid_shared_json_evidence(tmp_path):
    import json
    spec = importlib.util.spec_from_file_location(
        "e2e_io_benchmark", ROOT / "tools/workflow-quality/benchmark_e2e_coverage.py")
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    workloads = list(benchmark.workloads(tmp_path))
    assert len(workloads) == 7
    model = next(model for name, model in workloads if name == "shared-evidence")
    planned = e2e.plan(model, tmp_path)
    results = benchmark.results_for(tmp_path, model, planned)
    assert len(planned["cases"]) == 128
    data = (tmp_path / "evidence.json").read_bytes()
    assert len(data) == 4 * 1024 * 1024
    assert isinstance(json.loads(data)["fixture"], str)
    assert all(case["evidence"] == results["evidence"] for case in results["cases"])
    assert e2e.audit(model, results, tmp_path)["claim"] == "complete_against_frozen_scope"
