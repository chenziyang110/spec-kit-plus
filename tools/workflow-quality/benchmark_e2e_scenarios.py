#!/usr/bin/env python3
"""Compare trusted scenario helpers on identical synthetic v1/v2 books.

Imports explicit trusted Python files. Never pass untrusted modules. Every
measured check/audit must match baseline output exactly; audits intentionally
have no execution evidence and cannot establish product or visual coverage.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import tempfile
import time

DIMENSIONS = ("happy_path input_partitions input_boundaries object_lifecycle external_mutation event_order "
              "permissions conflict_concurrency repeat_cancel_retry interruption_recovery persistence_consistency "
              "environment_compatibility visual_interaction cross_feature").split()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot import trusted helper: {path}")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def model(root, operations=1, events=1, version=2):
    source = root / "contract.txt"
    source.write_text("Synthetic benchmark; no application was executed.\n", encoding="utf-8")
    result = {"schema_version": version, "scope": "synthetic benchmark", "source_revision": "fixture-v1",
              "sources": [{"path": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}],
              "requirements": [{"id": "R1", "source_ref": source.name, "assertion": "Synthetic expected outcome"}],
              "operations": [], "scenarios": [], "discovery_gaps": [], "exclusions": []}
    if version == 2:
        result["conditions"] = []
    for i in range(operations):
        identity = f"op-{i}"
        result["operations"].append({
            "id": identity, "title": identity, "entrypoint": "Synthetic only", "source_refs": [source.name],
            "assumptions": ["Synthetic object exists"], "side_effects": False,
            "dimensions": {d: {"disposition": "applicable" if d in {"happy_path", "external_mutation", "event_order"} else "not_applicable",
                               "reason": "Bounded synthetic benchmark, not product discovery", "source_refs": [source.name]}
                           for d in DIMENSIONS},
            "checkpoints": [{"id": "before", "observation": "Synthetic checkpoint"}],
            "events": [{"id": f"event-{j}", "change": "Synthetic perturbation", "checkpoints": ["before"]}
                       for j in range(events)]})
        if version == 2:
            result["conditions"].append({"id": identity + "/condition", "operation": identity, "dimension": "happy_path",
                                         "kind": "example", "title": "Synthetic outcome", "source_refs": [source.name],
                                         "requirements": ["R1"], "variants": [{"id": "main", "input": "synthetic",
                                                                                          "expected": "Synthetic expected outcome"}]})
        for j in range(events):
            scenario = {"id": f"{identity}/scenario-{j}", "operation": identity, "title": "Synthetic scenario",
                        "dimensions": ["happy_path", "external_mutation", "event_order"], "requirements": ["R1"],
                        "technique": ["event-sequence"], "priority": "normal", "preconditions": ["No product execution"],
                        "steps": [{"id": "change", "actor": "fixture", "action": "Synthetic perturbation", "observe": "Synthetic outcome"}],
                        "perturbations": [{"event": f"event-{j}", "checkpoint": "before", "step_id": "change"}],
                        "oracles": [{"id": "observe", "channel": "cli", "assertion": "Synthetic expected outcome", "check": "Not executed"}],
                        "execution": "runner", "cleanup": ["Temporary benchmark files only"], "safety": ["No commands from input"]}
            if version == 2:
                scenario["condition_bindings"] = [{"condition": identity + "/condition", "variant": "main",
                                                   "step_ids": ["change"], "oracle_ids": ["observe"]}]
            result["scenarios"].append(scenario)
    return result


def benchmark(baseline_path, candidate_path, repeats=5):
    baseline = module(baseline_path, "scenario_benchmark_baseline")
    candidate = module(candidate_path, "scenario_benchmark_candidate")
    records = []
    with tempfile.TemporaryDirectory(prefix="scenario-benchmark-") as directory:
        root = Path(directory)
        for name, ops, events, version in (("small-v2", 1, 2, 2), ("timing-v1", 1, 1000, 1),
                                            ("timing-v2", 1, 1000, 2), ("many-operations-v2", 500, 2, 2)):
            book = model(root, ops, events, version)
            original = deepcopy(book)
            trace = {"schema_version": 1, "book_sha256": baseline.sha(book), "source_revision": book["source_revision"],
                     "run_id": "no-execution", "target": "synthetic", "executor": {"kind": "runner", "name": "not-executed"},
                     "started_at": "2026-10-10T00:00:00Z", "finished_at": "2026-10-10T00:00:00Z", "evidence": [], "results": []}
            row = {"name": name, "scenarios": len(book["scenarios"]), "timing_obligations": ops * events,
                   "schema_version": version}
            for action in ("check", "audit"):
                args = (book, root) if action == "check" else (book, trace, root)
                expected = getattr(baseline, action)(*args)
                samples = {"baseline": [], "candidate": []}
                for iteration in range(repeats):
                    order = (("baseline", baseline), ("candidate", candidate))
                    for label, helper in (order if iteration % 2 == 0 else reversed(order)):
                        started = time.perf_counter()
                        observed = getattr(helper, action)(*args)
                        samples[label].append(time.perf_counter() - started)
                        if observed != expected or book != original:
                            raise ValueError(f"{name}/{action}/{label}: changed output or input")
                medians = {key: statistics.median(value) for key, value in samples.items()}
                row[action] = {"seconds": samples, "median_seconds": medians,
                               "speedup": medians["baseline"] / medians["candidate"],
                               "output_sha256": hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()}
            records.append(row)
    return {"claim": "synthetic-performance-only", "timestamp": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(), "platform": platform.platform(), "repeats": repeats,
            "baseline_sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
            "candidate_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(), "models": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", type=Path, default=Path(__file__).resolve().parents[2] / "scripts/shared/e2e_scenarios.py")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    print(json.dumps(benchmark(args.baseline, args.candidate, args.repeats), indent=2))


if __name__ == "__main__":
    main()
