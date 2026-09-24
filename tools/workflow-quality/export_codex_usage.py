"""Export observed Codex rollout usage to metadata-only workflow-usage-v1 JSONL.

Reads one explicitly named, stable rollout. Never invokes Codex, scans CODEX_HOME,
infers acceptance/completeness, estimates prices, or exports conversation text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, BinaryIO, Iterator
from uuid import UUID

from measure_execution_usage import SCHEMA, UsageError, validate_record

MAX_ROLLOUT_LINE_BYTES = 8 * 1024 * 1024
MAX_ROLLOUT_BYTES = 1024 * 1024 * 1024
MAX_CALLS = 100_000
TOKEN_FIELDS = (
    "input_tokens", "cached_input_tokens", "output_tokens",
    "reasoning_output_tokens", "total_tokens",
)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise UsageError("duplicate JSON key in input")
        result[key] = value
    return result


def _constant(_: str) -> Any:
    raise UsageError("non-finite JSON number in input")


def _decode(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError):
        # Raw parser errors, keys and values can contain private conversation text.
        raise UsageError("invalid UTF-8 JSON object") from None
    if not isinstance(value, dict):
        raise UsageError("input record must be an object")
    return value


def _records(stream: BinaryIO) -> Iterator[tuple[int, dict[str, Any]]]:
    number = 0
    total_bytes = 0
    while raw := stream.readline(MAX_ROLLOUT_LINE_BYTES + 1):
        number += 1
        total_bytes += len(raw)
        if len(raw) > MAX_ROLLOUT_LINE_BYTES or total_bytes > MAX_ROLLOUT_BYTES:
            raise UsageError(f"line {number}: input size limit exceeded")
        if not raw.strip():
            continue
        try:
            yield number, _decode(raw)
        except UsageError as exc:
            raise UsageError(f"line {number}: {exc}") from None


def _tokens(value: Any) -> tuple[int, ...]:
    if not isinstance(value, dict) or set(value) - {*TOKEN_FIELDS, "cache_write_input_tokens"}:
        raise UsageError("unsupported token usage shape")
    counts = tuple(value.get(key) for key in TOKEN_FIELDS)
    if any(type(n) is not int or not 0 <= n <= 2**63 - 1 for n in counts):
        raise UsageError("token counts must be nonnegative signed-64-bit integers")
    inputs, cached, outputs, reasoning, total = counts
    if cached > inputs or reasoning > outputs or total != inputs + outputs:
        raise UsageError("inconsistent or synthetic token counts")
    cache_write = value.get("cache_write_input_tokens", 0)
    if type(cache_write) is not int or cache_write != 0:
        raise UsageError("cache-write token accounting is not supported by this adapter")
    return counts


def _model(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}", value):
        raise UsageError("missing or unsupported model identifier")
    return value


def _call(labels: dict[str, str], model: str, call_id: str, usage: tuple[int, ...]) -> dict[str, Any]:
    return validate_record({
        "schema": SCHEMA, "kind": "call", **labels,
        "call_id": call_id, "model": model,
        "usage_kind": "delta", "measurement": "reported",
        "input_tokens": usage[0], "cached_input_tokens": usage[1], "output_tokens": usage[2],
        "cost_usd": None, "duration_ms": None,
    })


def extract_calls(stream: BinaryIO, *, run_id: str, role: str, stage: str,
                  purpose: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return only cross-checked reported deltas, or reject the entire input.

    Cumulative counters are continuity/dedup evidence, never emitted as a call.
    A valid chain does NOT prove that every billable request was logged.
    """
    labels = {"run_id": run_id, "role": role, "stage": stage, "purpose": purpose}
    _call(labels, "validation-only", "validation-only", (0, 0, 0, 0, 0))
    calls: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "schema": "codex-usage-export-report-v1", "observed_calls": 0,
        "nonadvancing_snapshots": 0, "rate_limit_only_events": 0,
        "trace_completeness": "not-established", "acceptance": "not-inferred",
    }
    thread_key: str | None = None
    model: str | None = None
    previous = (0, 0, 0, 0, 0)
    for number, record in _records(stream):
        kind, payload = record.get("type"), record.get("payload")
        try:
            if not isinstance(kind, str) or not isinstance(payload, dict):
                raise UsageError("unsupported rollout envelope")
            if kind == "session_meta":
                if thread_key is not None:
                    raise UsageError("multiple session headers; export one unmerged rollout")
                if any(payload.get(key) is not None for key in (
                    "forked_from_id", "history_base", "subagent_history_start_ordinal",
                )):
                    raise UsageError("inherited or forked history requires a separate lineage-aware exporter")
                try:
                    identifier = str(UUID(payload["id"]))
                except (KeyError, ValueError, AttributeError, TypeError):
                    raise UsageError("session header requires a valid thread UUID") from None
                thread_key = hashlib.sha256(identifier.encode("ascii")).hexdigest()
                continue
            if thread_key is None:
                raise UsageError("rollout must begin with its session header")
            if kind == "turn_context":
                model = _model(payload.get("model"))
                continue
            if kind == "compacted":
                raise UsageError("compacted history requires a separate continuity-aware exporter")
            if kind != "event_msg":
                # Response items and all their text/tool outputs stay local.
                continue
            event = payload.get("type")
            if event in ("context_compacted", "thread_rolled_back"):
                raise UsageError("history rewrite requires a separate continuity-aware exporter")
            if event == "model_reroute":
                if model is None or _model(payload.get("from_model")) != model:
                    raise UsageError("model reroute does not match the observed context")
                model = _model(payload.get("to_model"))
                continue
            if event != "token_count":
                # In particular, task_complete/turn_complete is not acceptance.
                continue
            if "info" not in payload:
                raise UsageError("token_count is missing its info field")
            info = payload["info"]
            if info is None:
                report["rate_limit_only_events"] += 1
                continue
            if not isinstance(info, dict):
                raise UsageError("unsupported token_count info")
            cumulative = _tokens(info.get("total_token_usage"))
            latest = _tokens(info.get("last_token_usage"))
            if cumulative == previous:
                report["nonadvancing_snapshots"] += 1
                continue
            if cumulative != tuple(a + b for a, b in zip(previous, latest)):
                raise UsageError("token continuity gap, counter reset or non-additive update")
            if model is None:
                raise UsageError("usage has no preceding model context")
            if len(calls) >= MAX_CALLS:
                raise UsageError("export call limit exceeded")
            fingerprint = hashlib.sha256(json.dumps(cumulative).encode("ascii")).hexdigest()
            call_id = f"codex:{thread_key}:{fingerprint}"
            calls.append(_call(labels, model, call_id, latest))
            previous = cumulative
        except UsageError as exc:
            raise UsageError(f"line {number}: {exc}") from None
    if thread_key is None or not calls:
        raise UsageError("no attributable usage calls found")
    report["observed_calls"] = len(calls)
    return calls, report


def _snapshot(info: os.stat_result) -> tuple[int, ...]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def export_file(path: Path, **labels: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # O_NONBLOCK prevents an explicitly named FIFO from hanging before fstat.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_ROLLOUT_BYTES:
            raise UsageError("rollout must be a bounded regular file")
        result = extract_calls(stream, **labels)
        if _snapshot(before) != _snapshot(os.fstat(stream.fileno())):
            raise UsageError("rollout changed during export; use a stable snapshot")
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rollout", type=Path, help="One local Codex rollout JSONL snapshot.")
    for name in ("run-id", "role", "stage", "purpose"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        calls, report = export_file(args.rollout, run_id=args.run_id, role=args.role,
                                    stage=args.stage, purpose=args.purpose)
        # Validate everything before exposing even the first output record.
        output = "".join(json.dumps(c, ensure_ascii=False, allow_nan=False) + "\n" for c in calls)
    except UsageError as exc:
        print(f"Codex usage export failed: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Codex usage export failed: input I/O error (errno={exc.errno})", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True), file=sys.stderr)
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
