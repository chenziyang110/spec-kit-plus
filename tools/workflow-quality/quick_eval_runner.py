"""Generate conservative Quick adaptive execution benchmark reports.

This tool aggregates already collected evidence. It does not execute agents,
decide acceptance, or infer quality from lower token usage.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MODES = {
    "worker-full",
    "worker-compact",
    "direct-full",
    "direct-compact",
}


def load_records(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("record must be an object")
            records.append(item)
    return records


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}
    for record in records:
        mode = record.get("mode")
        if mode not in MODES:
            raise ValueError(f"unsupported mode: {mode}")
        group = groups.setdefault(mode, {
            "runs": 0,
            "tokens": 0,
            "accepted": 0,
            "human_intervention": 0,
            "duration_ms": 0,
            "unknown_quality": 0,
        })
        group["runs"] += 1
        group["tokens"] += record.get("input_tokens", 0) + record.get("output_tokens", 0)
        group["duration_ms"] += record.get("duration_ms", 0)
        if record.get("accepted") is True:
            group["accepted"] += 1
        elif record.get("accepted") is None:
            group["unknown_quality"] += 1
        if record.get("human_intervention") is True:
            group["human_intervention"] += 1

    for group in groups.values():
        runs = group["runs"]
        group["accepted_rate"] = None if runs == 0 else group["accepted"] / runs
        group["tokens_per_run"] = None if runs == 0 else group["tokens"] / runs

    return {
        "schema": "quick-adaptive-eval-report-v1",
        "groups": groups,
        "rules": {
            "quality_from_tokens": False,
            "missing_acceptance_is_unknown": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = summarize(load_records(args.input))
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
