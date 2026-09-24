"""Synthetic rollout fixtures; no private sessions or paid model calls."""
from __future__ import annotations

import copy
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "workflow-quality"
sys.path.insert(0, str(TOOLS))
try:
    exporter = importlib.import_module("export_codex_usage")
    metrics = importlib.import_module("measure_execution_usage")
finally:
    sys.path.pop(0)

LABELS = {"run_id": "synthetic-run", "role": "leader", "stage": "quick", "purpose": "work"}
THREAD = "00000000-0000-4000-8000-000000000001"
SECRET = "PRIVATE_PROMPT_TOOL_OUTPUT_SECRET"


def record(kind, payload):
    return {"timestamp": "2026-09-15T00:00:00Z", "type": kind, "payload": payload}


def usage(inputs=100, cached=40, outputs=20, reasoning=5):
    return dict(zip(exporter.TOKEN_FIELDS, (inputs, cached, outputs, reasoning, inputs + outputs)))


def add(left, right):
    return {key: left[key] + right[key] for key in exporter.TOKEN_FIELDS}


def token(total, last):
    return record("event_msg", {"type": "token_count", "info": {
        "total_token_usage": total, "last_token_usage": last,
    }, "rate_limits": {"private_unused_value": SECRET}})


def header(**values):
    return record("session_meta", {"id": THREAD, "cwd": SECRET, "base_instructions": SECRET, **values})


def fixture():
    delta = usage()
    return [header(), record("turn_context", {"model": "fixture-model", "cwd": SECRET}),
            record("response_item", {"type": "message", "content": SECRET}),
            token(delta, delta)]


def encoded(rows):
    return ("\n".join(json.dumps(row) for row in rows) + "\n").encode()


def extract(rows, **labels):
    return exporter.extract_calls(io.BytesIO(encoded(rows)), **(LABELS | labels))


def run_record(**overrides):
    return {"schema": metrics.SCHEMA, "kind": "run", "run_id": LABELS["run_id"],
            "case_id": "synthetic-fixture", "variant": "adapter-test", "outcome": "accepted",
            "acceptance_evidence": "test:fixture-not-product-acceptance", "expected_calls": None,
            **overrides}


class CodexUsageExportTests(unittest.TestCase):
    def test_duplicate_rate_snapshots_do_not_double_count(self):
        rows = fixture()
        rows += [copy.deepcopy(rows[-1]), record("event_msg", {"type": "token_count", "info": None})]
        calls, report = extract(rows)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["input_tokens"], 100)
        self.assertEqual(report["nonadvancing_snapshots"], 1)
        self.assertEqual(report["rate_limit_only_events"], 1)
        self.assertEqual(report["trace_completeness"], "not-established")

    def test_distinct_calls_with_identical_usage_are_retained(self):
        rows = fixture() + [token(add(usage(), usage()), usage())]
        calls, _ = extract(rows)
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0]["call_id"], calls[1]["call_id"])
        group = metrics.summarize(calls + [run_record(expected_calls=2)])["groups"][0]
        self.assertEqual(group["usage"]["total_tokens"]["total"], 240)
        self.assertEqual(group["usage"]["cached_input_tokens"]["total"], 80)
        self.assertEqual(group["usage"]["uncached_input_tokens"]["total"], 120)
        self.assertIsNone(group["usage"]["cost_usd"]["total"])

    def test_existing_analyzer_keeps_completeness_unknown(self):
        calls, _ = extract(fixture())
        group = metrics.summarize(calls + [run_record()])["groups"][0]
        self.assertEqual(group["usage"]["total_tokens"]["observed_sum"], 120)
        self.assertIsNone(group["usage"]["total_tokens"]["total"])
        self.assertIsNone(group["tokens_per_accepted_run"])

    def test_reexport_produces_stable_ids_and_analyzer_detects_overlap(self):
        first, _ = extract(fixture())
        again, _ = extract(fixture())
        self.assertEqual(first, again)
        with self.assertRaisesRegex(metrics.UsageError, "duplicate call"):
            metrics.summarize(first + again + [run_record()])

    def test_model_switch_does_not_reattribute_replayed_usage(self):
        rows = fixture()
        rows += [record("turn_context", {"model": "fixture-model-2"}), copy.deepcopy(rows[-1]),
                 token(add(usage(), usage()), usage())]
        calls, _ = extract(rows)
        self.assertEqual([c["model"] for c in calls], ["fixture-model", "fixture-model-2"])

    def test_model_reroute_uses_observed_target(self):
        rows = fixture() + [record("event_msg", {"type": "model_reroute", "from_model": "fixture-model",
                                                  "to_model": "fixture-model-2"}),
                            token(add(usage(), usage()), usage())]
        calls, _ = extract(rows)
        self.assertEqual(calls[-1]["model"], "fixture-model-2")
        rows[-2]["payload"]["from_model"] = "wrong-model"
        with self.assertRaisesRegex(metrics.UsageError, "reroute"):
            extract(rows)

    def test_no_conversation_or_paths_in_export(self):
        rows = fixture() + [record("event_msg", {"type": "task_complete", "last_agent_message": SECRET})]
        calls, report = extract(rows)
        output = json.dumps([calls, report])
        self.assertNotIn(SECRET, output)
        self.assertNotIn(THREAD, output)
        self.assertTrue(all(c["kind"] == "call" for c in calls))
        self.assertIsNone(calls[0]["duration_ms"])
        self.assertIsNone(calls[0]["cost_usd"])
        self.assertEqual(report["acceptance"], "not-inferred")

    def test_failed_turn_usage_is_not_removed(self):
        rows = fixture() + [record("event_msg", {"type": "error", "message": SECRET})]
        calls, _ = extract(rows)
        self.assertEqual(len(calls), 1)
        summary = metrics.summarize(calls + [run_record(outcome="failed")])["groups"][0]
        self.assertEqual(summary["failed_runs"], 1)
        self.assertEqual(summary["usage"]["total_tokens"]["observed_sum"], 120)

    def test_fresh_child_thread_does_not_collide_with_parent(self):
        parent, _ = extract(fixture())
        rows = fixture()
        rows[0]["payload"].update(id="00000000-0000-4000-8000-000000000002", session_id=THREAD,
                                    parent_thread_id=THREAD)
        child, _ = extract(rows, role="worker")
        self.assertNotEqual(parent[0]["call_id"], child[0]["call_id"])
        summary = metrics.summarize(parent + child + [run_record()])["groups"][0]
        self.assertEqual(set(summary["breakdown"]["role"]), {"leader", "worker"})

    def test_reject_inherited_history(self):
        for key, value in [("forked_from_id", THREAD), ("history_base", {}),
                           ("subagent_history_start_ordinal", 0)]:
            with self.subTest(field=key), self.assertRaisesRegex(metrics.UsageError, "inherited or forked"):
                rows = fixture()
                rows[0]["payload"][key] = value
                extract(rows)

    def test_reject_missing_header_model_and_mixed_sessions(self):
        variants = [fixture()[1:], [header(), token(usage(), usage())], fixture() + [header()],
                    [header(id="not-a-uuid")], [header()], []]
        for rows in variants:
            with self.subTest(rows=len(rows)), self.assertRaises(metrics.UsageError):
                extract(rows)

    def test_reject_gaps_resets_and_changed_usage_components(self):
        for changed in [usage(300), usage(1, 0, 1, 0), usage(100, 41)]:
            with self.subTest(total=changed), self.assertRaisesRegex(metrics.UsageError, "continuity"):
                extract(fixture() + [token(changed, usage())])
        with self.assertRaisesRegex(metrics.UsageError, "continuity"):
            extract([header(), record("turn_context", {"model": "fixture-model"}),
                     token(add(usage(), usage()), usage())])

    def test_reject_synthetic_context_fill(self):
        fake = dict.fromkeys(exporter.TOKEN_FIELDS, 0)
        fake["total_tokens"] = 200_000
        with self.assertRaisesRegex(metrics.UsageError, "synthetic"):
            extract(fixture() + [token(fake, fake)])

    def test_reject_malformed_token_shapes(self):
        bad = [None, [], {}, usage() | {"input_tokens": True}, usage() | {"output_tokens": -1},
               usage() | {"cached_input_tokens": 101}, usage() | {"reasoning_output_tokens": 21},
               usage() | {"input_tokens": 2**63}, usage() | {"total_tokens": 120.0},
               usage() | {"future_tokens": 2}, usage() | {"cache_write_input_tokens": 1},
               usage() | {"cache_write_input_tokens": False}]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(metrics.UsageError):
                extract(fixture() + [token(value, value)])

    def test_zero_cache_write_extension_is_compatible(self):
        rows = fixture()
        for value in rows[-1]["payload"]["info"].values():
            value["cache_write_input_tokens"] = 0
        self.assertEqual(len(extract(rows)[0]), 1)

    def test_reject_history_rewrites(self):
        rewrites = [record("compacted", {}), record("event_msg", {"type": "context_compacted"}),
                    record("event_msg", {"type": "thread_rolled_back"})]
        for row in rewrites:
            with self.subTest(row=row), self.assertRaises(metrics.UsageError):
                extract(fixture() + [row])

    def test_invalid_json_errors_do_not_echo_values(self):
        for raw in [b'{"private":"' + SECRET.encode(), b'{"' + SECRET.encode() + b'":1,"' + SECRET.encode() + b'":2}',
                    b'{"private":NaN}', b'{"private":"\xff"}', b'[]']:
            with self.subTest(raw=raw):
                with self.assertRaises(metrics.UsageError) as caught:
                    exporter.extract_calls(io.BytesIO(raw), **LABELS)
                self.assertNotIn(SECRET, str(caught.exception))

    def test_missing_info_is_not_a_rate_limit_only_event(self):
        with self.assertRaisesRegex(metrics.UsageError, "missing its info"):
            extract(fixture() + [record("event_msg", {"type": "token_count"})])

    def test_limits_fail_instead_of_silently_truncating(self):
        for name, limit in [("MAX_ROLLOUT_LINE_BYTES", 20), ("MAX_ROLLOUT_BYTES", 20), ("MAX_CALLS", 0)]:
            with self.subTest(limit=name), patch.object(exporter, name, limit), self.assertRaises(metrics.UsageError):
                extract(fixture())

    def test_zero_initial_snapshot_and_blank_lines_are_not_calls(self):
        zero = dict.fromkeys(exporter.TOKEN_FIELDS, 0)
        rows = fixture()
        rows.insert(1, token(zero, zero))
        calls, report = exporter.extract_calls(io.BytesIO(b'\n' + encoded(rows) + b'\r\n'), **LABELS)
        self.assertEqual(len(calls), 1)
        self.assertEqual(report["nonadvancing_snapshots"], 1)

    def test_caller_metadata_is_validated_not_inferred(self):
        for override in [{"purpose": "guessed"}, {"role": ""}, {"stage": "invalid\nlabel"}, {"run_id": " x "}]:
            with self.subTest(override=override), self.assertRaises(metrics.UsageError):
                extract(fixture(), **override)

    def test_input_growth_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.jsonl"
            path.write_bytes(encoded(fixture()))
            original = exporter.extract_calls
            def growing(stream, **labels):
                result = original(stream, **labels)
                with path.open("ab") as output:
                    output.write(b'\n')
                return result
            with patch.object(exporter, "extract_calls", side_effect=growing):
                with self.assertRaisesRegex(metrics.UsageError, "changed during export"):
                    exporter.export_file(path, **LABELS)

    def test_input_is_unchanged_and_cli_output_is_consumable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rollout = root / "private-session.jsonl"
            raw = encoded(fixture() + [token(add(usage(), usage()), usage())])
            rollout.write_bytes(raw)
            command = [sys.executable, str(TOOLS / "export_codex_usage.py"), str(rollout)]
            for key, value in LABELS.items():
                command += ["--" + key.replace("_", "-"), value]
            result = subprocess.run(command, capture_output=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(rollout.read_bytes(), raw)
            self.assertNotIn(SECRET.encode(), result.stdout + result.stderr)
            calls = root / "calls.jsonl"
            calls.write_bytes(result.stdout)
            evaluation = root / "evaluation.jsonl"
            evaluation.write_text(json.dumps(run_record()) + "\n", encoding="utf-8")
            analyzed = subprocess.run([sys.executable, str(TOOLS / "measure_execution_usage.py"),
                                       str(calls), str(evaluation)], capture_output=True, check=False, timeout=10)
            self.assertEqual(analyzed.returncode, 0, analyzed.stderr)
            group = json.loads(analyzed.stdout)["groups"][0]
            self.assertEqual(group["usage"]["total_tokens"]["observed_sum"], 240)
            self.assertIsNone(group["tokens_per_accepted_run"])
            self.assertEqual(json.loads(result.stderr)["observed_calls"], 2)

    def test_cli_error_has_no_partial_stdout_or_private_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / (SECRET + ".jsonl")
            path.write_bytes(encoded(fixture()) + b'{"private":"' + SECRET.encode())
            args = [str(path), "--run-id", "r", "--role", "worker", "--stage", "quick", "--purpose", "work"]
            result = subprocess.run([sys.executable, str(TOOLS / "export_codex_usage.py"), *args],
                                    capture_output=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b'')
            self.assertNotIn(SECRET.encode(), result.stderr)
            path.unlink()
            result = subprocess.run([sys.executable, str(TOOLS / "export_codex_usage.py"), *args],
                                    capture_output=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b'')
            self.assertNotIn(SECRET.encode(), result.stderr)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO checks require POSIX")
    def test_fifo_is_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fifo"
            os.mkfifo(path)
            with self.assertRaisesRegex(metrics.UsageError, "regular file"):
                exporter.export_file(path, **LABELS)


if __name__ == "__main__":
    unittest.main()
