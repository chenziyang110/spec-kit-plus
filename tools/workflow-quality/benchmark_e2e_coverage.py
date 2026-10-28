#!/usr/bin/env python3
"""Compare exact E2E plan/audit outputs and measure local helper performance.

Use a trusted pre-change source file as --baseline. No runner/product is
executed; all manifests and evidence are synthetic fixtures. JSON goes to
stdout. A mismatch is an error, never a speedup. There is deliberately no
wall-clock CI threshold. The imported files execute Python code: do not pass
untrusted modules.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_record(root: Path, name: str, content: str) -> dict:
    path = root / name
    path.write_text(content, encoding="utf-8")
    return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def workloads(root: Path):
    record = file_record(root, "source.txt", "synthetic source fixture")
    shapes = [("small", 3, 2, 2, 0), ("binary-10", 10, 2, 2, 0),
              ("ternary-7", 7, 3, 2, 0), ("mandatory-ternary-7", 7, 3, 2, 24),
              ("three-way", 6, 3, 3, 8), ("exhaustive", 4, 3, "exhaustive", 0),
              ("shared-evidence", 1, 128, "exhaustive", 0)]
    for name, width, cardinality, strength, mandatory_count in shapes:
        factors = {f"f{i}": [str(j) for j in range(cardinality)] for i in range(width)}
        mandatory = [{f"f{i}": str((number // cardinality ** i) % cardinality) for i in range(width)}
                     for number in range(mandatory_count)]
        yield name, {"schema_version": 1, "scope": "synthetic performance fixture",
                     "source_revision": "fixture", "sources": [record], "exclusions": [],
                     "requirements": [{"id": "R1", "source": "source.txt", "assertion": "fixture"}],
                     "journeys": [{"id": name, "requirements": ["R1"], "steps": ["act", "observe"],
                                   "factors": factors, "strength": strength,
                                   "exclude": [], "mandatory": mandatory}]}


def results_for(root: Path, model: dict, plan: dict) -> dict:
    tests = file_record(root, "test.txt", "synthetic test fixture, not a product test")
    # Shared native evidence is typically repeated in every passed-case record.
    # Exercise that I/O shape as well as tiny planner-focused fixtures.
    content = '{"fixture":true}'
    if model["journeys"][0]["id"] == "shared-evidence":
        content = '{"fixture":"' + "x" * (4 * 1024 * 1024 - len('{"fixture":""}')) + '"}'
    evidence = file_record(root, "evidence.json", content)
    return {"schema_version": 1, "manifest_sha256": plan["manifest_sha256"],
            "source_revision": model["source_revision"], "run_id": "benchmark-fixture",
            "target": "fixture", "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:01:00Z", "command": ["synthetic-fixture"],
            "exit_code": 0, "test_sources": [tests], "evidence": [evidence],
            "cases": [{"id": case["id"], "status": "passed", "test_ref": tests["path"],
                       "asserted_requirements": case["requirements"], "evidence": [evidence]}
                      for case in plan["cases"]]}


def compare_calls(baseline, candidate, repeats: int) -> dict:
    expected = baseline()
    if candidate() != expected:
        raise ValueError("baseline/candidate output mismatch")
    samples = {"baseline": [], "candidate": []}
    functions = {"baseline": baseline, "candidate": candidate}
    # Alternate order to reduce fixed warm-cache/thermal ordering bias.
    for iteration in range(repeats):
        order = ("baseline", "candidate") if iteration % 2 == 0 else ("candidate", "baseline")
        for name in order:
            start = time.perf_counter()
            actual = functions[name]()
            elapsed = time.perf_counter() - start
            if actual != expected:
                raise ValueError(f"{name}: nondeterministic output")
            samples[name].append(elapsed)
    before = statistics.median(samples["baseline"])
    after = statistics.median(samples["candidate"])
    return {"outputs_equal": True, "baseline_median_seconds": before,
            "candidate_median_seconds": after, "speedup": before / after,
            "samples_seconds": samples}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, default=ROOT / "scripts/shared/e2e_coverage.py")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args(argv)
    if not 1 <= args.repeats <= 100:
        parser.error("--repeats must be between 1 and 100")
    try:
        baseline = load_module(args.baseline, "e2e_benchmark_baseline")
        candidate = load_module(args.candidate, "e2e_benchmark_candidate")
        reports = []
        with tempfile.TemporaryDirectory(prefix="e2e-planner-benchmark-") as directory:
            root = Path(directory)
            for name, model in workloads(root):
                plan = baseline.plan(model, root)
                results = results_for(root, model, plan)
                reports.append({"workload": name, "planned_cases": len(plan["cases"]),
                                "shared_evidence_bytes": (root / "evidence.json").stat().st_size,
                                "plan": compare_calls(lambda: baseline.plan(model, root),
                                                      lambda: candidate.plan(model, root), args.repeats),
                                "audit": compare_calls(lambda: baseline.audit(model, results, root),
                                                       lambda: candidate.audit(model, results, root), args.repeats)})
        report = {"schema_version": 1, "claim": "synthetic_helper_benchmark_only",
                  "timestamp": datetime.now(timezone.utc).isoformat(),
                  "python": sys.version, "platform": platform.platform(), "repeats": args.repeats,
                  "baseline_sha256": hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
                  "candidate_sha256": hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
                  "workloads": reports}
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(json.dumps({"claim": "invalid", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
