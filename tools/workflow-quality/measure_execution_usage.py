"""Summarize reported per-call usage without treating unknown telemetry as zero.

Consumes metadata-only workflow-usage-v1 JSONL. Does not invoke an agent, price
models, infer acceptance, or convert source bytes into billed tokens.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "workflow-usage-v1"
MAX_LINE_BYTES = 1_048_576
COUNT_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "duration_ms")
BASE_KEYS = {"schema", "kind", "run_id"}
CALL_KEYS = BASE_KEYS | {
    "call_id", "model", "role", "stage", "purpose", "usage_kind", "measurement",
    "cost_usd", *COUNT_FIELDS,
}
RUN_KEYS = BASE_KEYS | {
    "case_id", "variant", "outcome", "expected_calls", "acceptance_evidence",
    "elapsed_ms", "human_wait_ms",
}


class UsageError(ValueError):
    """Invalid or ambiguous telemetry; never include raw record values."""


def _label(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise UsageError(f"{key} must be a nonblank string of at most 200 characters")
    if value != value.strip() or any(ord(c) < 32 for c in value):
        raise UsageError(f"{key} contains whitespace padding or control characters")
    return value


def _count(record: dict[str, Any], key: str) -> int | None:
    value = record.get(key)
    if value is not None and (type(value) is not int or not 0 <= value <= 2**63 - 1):
        raise UsageError(f"{key} must be a nonnegative integer or null")
    return value


def validate_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise UsageError(f"each record must be an object with schema {SCHEMA}")
    kind = record.get("kind")
    if kind not in ("call", "run"):
        raise UsageError("kind must be call or run")
    if set(record) - (CALL_KEYS if kind == "call" else RUN_KEYS):
        raise UsageError("unknown record fields; export metadata only, not prompts or responses")
    _label(record, "run_id")
    if kind == "call":
        for key in ("call_id", "model", "role", "stage"):
            _label(record, key)
        if record.get("usage_kind") != "delta" or record.get("measurement") != "reported":
            raise UsageError("calls require reported per-call deltas, not cumulative or estimated usage")
        if record.get("purpose") not in ("work", "workflow-control", "verification"):
            raise UsageError("purpose must be work, workflow-control, or verification")
        for key in COUNT_FIELDS:
            _count(record, key)
        cached, total = record.get("cached_input_tokens"), record.get("input_tokens")
        if cached is not None and (total is None or cached > total):
            raise UsageError("cached_input_tokens requires input_tokens and must be its subset")
        cost = record.get("cost_usd")
        if cost is not None and (not isinstance(cost, str) or not re.fullmatch(r"\d{1,12}(?:\.\d{1,12})?", cost)):
            raise UsageError("cost_usd must be a nonnegative decimal string or null")
    else:
        for key in ("case_id", "variant"):
            _label(record, key)
        if record.get("outcome") not in ("accepted", "failed", "blocked"):
            raise UsageError("outcome must be accepted, failed, or blocked")
        if "expected_calls" not in record:
            raise UsageError("expected_calls is required; use null when trace completeness is unknown")
        for key in ("expected_calls", "elapsed_ms", "human_wait_ms"):
            _count(record, key)
        elapsed, wait = record.get("elapsed_ms"), record.get("human_wait_ms")
        if elapsed is not None and wait is not None and wait > elapsed:
            raise UsageError("human_wait_ms cannot exceed elapsed_ms")
        if record.get("outcome") == "accepted" or record.get("acceptance_evidence") is not None:
            _label(record, "acceptance_evidence")
    return dict(record)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise UsageError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(_: str) -> Any:
    raise UsageError("non-finite JSON number")


def read_jsonl(paths: Iterable[Path]) -> list[dict[str, Any]]:
    records = []
    for path in paths:
        with path.open("rb") as stream:
            line_number = 0
            while raw := stream.readline(MAX_LINE_BYTES + 1):
                line_number += 1
                if len(raw) > MAX_LINE_BYTES:
                    raise UsageError(f"{path.name}:{line_number}: record exceeds size limit")
                if not raw.strip():
                    continue
                try:
                    record = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                                        parse_constant=_reject_constant)
                    records.append(validate_record(record))
                except (UnicodeError, ValueError, RecursionError) as exc:
                    # JSONDecodeError text can contain excerpts; only our typed
                    # diagnostics are safe to echo from possibly private input.
                    detail = str(exc) if isinstance(exc, UsageError) else "invalid UTF-8 JSON record"
                    raise UsageError(f"{path.name}:{line_number}: {detail}") from None
    return records


def _metric(calls: list[dict[str, Any]], field: str, complete: bool) -> dict[str, Any]:
    values = [c[field] for c in calls if c.get(field) is not None]
    if field == "cost_usd":
        # Sum reported decimal values without binary-float or context rounding.
        with localcontext() as context:
            context.prec = max(28, 24 + len(str(max(len(values), 1))))
            value = sum((Decimal(v) for v in values), Decimal(0))
    else:
        value = sum(values)
    total: Any = format(value, "f") if field == "cost_usd" else value
    return {"observed_sum": total, "unknown_calls": len(calls) - len(values),
            "total": total if complete and len(values) == len(calls) else None}


def _timing(runs: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = sorted(r[field] for r in runs if r.get(field) is not None)
    return {"known_runs": len(values), "unknown_runs": len(runs) - len(values),
            "observed_p50_ms": statistics.median(values) if values else None,
            "observed_p95_ms": values[math.ceil(0.95 * len(values)) - 1] if values else None}


def summarize(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    runs: dict[str, dict[str, Any]] = {}
    calls_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    call_ids: set[tuple[str, str]] = set()
    for raw in records:
        record = validate_record(raw)
        run_id = record["run_id"]
        if record["kind"] == "run":
            if run_id in runs:
                raise UsageError("duplicate run record; input files may overlap")
            runs[run_id] = record
        else:
            key = (run_id, record["call_id"])
            if key in call_ids:
                raise UsageError("duplicate call record; retries need distinct call IDs")
            call_ids.add(key)
            calls_by_run[run_id].append(record)
    if not runs:
        raise UsageError("no completed run records")
    if set(calls_by_run) - set(runs):
        raise UsageError("call record has no matching run record")
    complete_runs: dict[str, bool] = {}
    for run_id, run in runs.items():
        count, expected = len(calls_by_run[run_id]), run["expected_calls"]
        if expected is not None and count > expected:
            raise UsageError("observed calls exceed expected_calls")
        complete_runs[run_id] = expected is not None and count == expected
    variants: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs.values():
        variants[run["variant"]].append(run)
    groups = []
    for variant, group in sorted(variants.items()):
        calls = [call for run in group for call in calls_by_run[run["run_id"]]]
        complete = all(complete_runs[r["run_id"]] for r in group)
        accepted = sum(r["outcome"] == "accepted" for r in group)
        # Input includes cache hits; reasoning tokens must already be included
        # in output. Neither is added a second time.
        enriched = []
        for call in calls:
            c = dict(call)
            i, o, h = (c.get(k) for k in ("input_tokens", "output_tokens", "cached_input_tokens"))
            c["total_tokens"] = i + o if i is not None and o is not None else None
            c["uncached_input_tokens"] = i - h if i is not None and h is not None else None
            enriched.append(c)
        usage = {field: _metric(enriched, field, complete) for field in (
            "input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens", "total_tokens", "cost_usd")}
        total, cost = usage["total_tokens"]["total"], usage["cost_usd"]["total"]
        control = [c for c in enriched if c["purpose"] == "workflow-control"]
        control_total = _metric(control, "total_tokens", complete)["total"]
        breakdown = {}
        for axis in ("role", "stage", "model", "purpose"):
            buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for call in enriched:
                buckets[call[axis]].append(call)
            breakdown[axis] = {name: {"observed_calls": len(rows),
                "tokens": _metric(rows, "total_tokens", complete)} for name, rows in sorted(buckets.items())}
        groups.append({
            "variant": variant, "runs": len(group), "accepted_runs": accepted,
            "failed_runs": sum(r["outcome"] == "failed" for r in group),
            "blocked_runs": sum(r["outcome"] == "blocked" for r in group),
            "acceptance_rate": accepted / len(group),
            "case_ids": sorted({r["case_id"] for r in group}),
            "observed_calls": len(calls),
            "incomplete_trace_runs": sum(not complete_runs[r["run_id"]] for r in group),
            "usage": usage,
            "tokens_per_accepted_run": total / accepted if total is not None and accepted else None,
            "cost_usd_per_accepted_run": format(Decimal(cost) / accepted, "f") if cost is not None and accepted else None,
            "workflow_control_token_share": control_total / total if total and control_total is not None else None,
            "elapsed": _timing(group, "elapsed_ms"), "human_wait": _timing(group, "human_wait_ms"),
            "breakdown": breakdown,
        })
    return {"schema": "workflow-usage-summary-v1", "groups": groups,
            "limits": ["Acceptance is supplied by an external evaluator; evidence references are not verified here.",
                       "Completeness is relative to exporter-reported expected_calls.",
                       "Different case sets, environments, or sample counts do not establish an A/B improvement.",
                       "No prices or missing usage are inferred; observed sums are not complete totals."]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces", type=Path, nargs="+", help="Metadata-only JSONL trace files.")
    args = parser.parse_args(argv)
    try:
        result = summarize(read_jsonl(args.traces))
    except (OSError, UsageError) as exc:
        print(f"usage measurement failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
