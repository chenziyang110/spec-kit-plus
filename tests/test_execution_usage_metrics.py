"""Offline usage accounting tests; fixtures are synthetic, not real savings."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools/workflow-quality/measure_execution_usage.py"
spec = importlib.util.spec_from_file_location("execution_usage_metrics", SCRIPT)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def run_record(run_id="r1", **changes):
    record = dict(schema=metrics.SCHEMA, kind="run", run_id=run_id, case_id="small-fix",
                  variant="baseline", outcome="accepted", expected_calls=1,
                  acceptance_evidence="tests/report.json", elapsed_ms=100, human_wait_ms=20)
    record.update(changes)
    return record


def call_record(run_id="r1", call_id="c1", **changes):
    record = dict(schema=metrics.SCHEMA, kind="call", run_id=run_id, call_id=call_id,
                  model="test-model", role="leader", stage="implement", purpose="work",
                  usage_kind="delta", measurement="reported", input_tokens=100,
                  cached_input_tokens=40, output_tokens=20, duration_ms=80, cost_usd="0.12")
    record.update(changes)
    return record


def group(*records):
    return metrics.summarize(records)["groups"][0]


class ExecutionUsageMetricsTests(unittest.TestCase):
    def test_cached_tokens_are_subset_not_additional_tokens(self):
        result = group(run_record(), call_record())
        self.assertEqual(result["usage"]["total_tokens"]["total"], 120)
        self.assertEqual(result["usage"]["uncached_input_tokens"]["total"], 60)
        self.assertEqual(result["tokens_per_accepted_run"], 120)

    def test_missing_cache_does_not_hide_known_total_input(self):
        call = call_record(cached_input_tokens=None)
        result = group(run_record(), call)
        self.assertEqual(result["usage"]["input_tokens"]["total"], 100)
        self.assertIsNone(result["usage"]["uncached_input_tokens"]["total"])

    def test_missing_usage_is_unknown_not_zero(self):
        result = group(run_record(), call_record(input_tokens=None, cached_input_tokens=None, cost_usd=None))
        self.assertIsNone(result["usage"]["total_tokens"]["total"])
        self.assertIsNone(result["tokens_per_accepted_run"])
        self.assertIsNone(result["cost_usd_per_accepted_run"])
        self.assertEqual(result["usage"]["output_tokens"]["total"], 20)
        self.assertEqual(result["usage"]["input_tokens"]["unknown_calls"], 1)

    def test_failed_attempt_and_worker_cost_count_towards_success(self):
        result = group(
            run_record(expected_calls=2), call_record(),
            call_record(call_id="worker-1", role="worker"),
            run_record("r2", outcome="failed", acceptance_evidence=None), call_record("r2"))
        self.assertEqual(result["tokens_per_accepted_run"], 360)
        self.assertEqual(result["cost_usd_per_accepted_run"], "0.36")
        self.assertEqual(result["acceptance_rate"], 0.5)
        self.assertEqual(result["breakdown"]["role"]["worker"]["observed_calls"], 1)

    def test_no_success_never_reports_zero_cost_per_success(self):
        result = group(run_record(outcome="blocked", acceptance_evidence=None), call_record())
        self.assertIsNone(result["tokens_per_accepted_run"])
        self.assertIsNone(result["cost_usd_per_accepted_run"])

    def test_missing_exported_calls_invalidate_complete_totals(self):
        result = group(run_record(expected_calls=2), call_record())
        self.assertEqual(result["incomplete_trace_runs"], 1)
        self.assertEqual(result["usage"]["total_tokens"]["observed_sum"], 120)
        self.assertIsNone(result["usage"]["total_tokens"]["total"])
        self.assertIsNone(result["breakdown"]["role"]["leader"]["tokens"]["total"])

    def test_unknown_expected_count_is_not_assumed_complete(self):
        result = group(run_record(expected_calls=None), call_record())
        self.assertIsNone(result["usage"]["input_tokens"]["total"])

    def test_zero_calls_only_zero_when_explicitly_complete(self):
        result = group(run_record(expected_calls=0))
        self.assertEqual(result["usage"]["total_tokens"]["total"], 0)
        self.assertEqual(result["cost_usd_per_accepted_run"], "0")
        self.assertIsNone(result["workflow_control_token_share"])

    def test_more_calls_than_manifest_is_error(self):
        with self.assertRaises(metrics.UsageError):
            group(run_record(expected_calls=0), call_record())

    def test_duplicates_and_orphans_rejected(self):
        for records in ((run_record(), run_record()),
                        (run_record(), call_record(), call_record()),
                        (run_record(), call_record("orphan")), (), (call_record(),)):
            with self.subTest(records=len(records)), self.assertRaises(metrics.UsageError):
                metrics.summarize(records)

    def test_cumulative_estimated_and_extra_content_rejected(self):
        for changes in ({"usage_kind": "cumulative"}, {"measurement": "estimated"},
                        {"prompt": "secret-prompt"}, {"reasoning_tokens": 10},
                        {"cost_usd": 0.12}, {"cost_usd": "NaN"}, {"cost_usd": "-1"}):
            with self.subTest(changes=changes), self.assertRaises(metrics.UsageError):
                metrics.validate_record(call_record(**changes))

    def test_invalid_counts_are_not_coerced(self):
        for field in metrics.COUNT_FIELDS:
            for value in (True, -1, 1.5, "2", 2**63):
                with self.subTest(field=field, value=value), self.assertRaises(metrics.UsageError):
                    metrics.validate_record(call_record(**{field: value}))
        for changes in ({"cached_input_tokens": 101}, {"input_tokens": None},
                        {"purpose": "unclassified"}, {"call_id": " "}):
            with self.assertRaises(metrics.UsageError):
                metrics.validate_record(call_record(**changes))

    def test_accepted_run_requires_evidence_and_manifest(self):
        for changes in ({"acceptance_evidence": None}, {"acceptance_evidence": " "},
                        {"human_wait_ms": 101}, {"outcome": "success"}):
            with self.assertRaises(metrics.UsageError):
                metrics.validate_record(run_record(**changes))
        record = run_record()
        del record["expected_calls"]
        with self.assertRaises(metrics.UsageError):
            metrics.validate_record(record)

    def test_variant_separation_order_independence_and_no_input_mutation(self):
        records = [call_record("r2"), run_record(), call_record(), run_record("r2", variant="candidate")]
        before = copy.deepcopy(records)
        result = metrics.summarize(records)
        self.assertEqual(result, metrics.summarize(reversed(records)))
        self.assertEqual(records, before)
        self.assertEqual([g["variant"] for g in result["groups"]], ["baseline", "candidate"])

    def test_wall_time_is_run_duration_not_sum_of_parallel_calls(self):
        result = group(run_record(expected_calls=2), call_record(), call_record(call_id="c2", role="worker"))
        self.assertEqual(result["elapsed"]["observed_p50_ms"], 100)
        self.assertEqual(result["human_wait"]["observed_p95_ms"], 20)

    def test_missing_timing_has_explicit_coverage(self):
        result = group(run_record(elapsed_ms=None), call_record())
        self.assertEqual(result["elapsed"]["unknown_runs"], 1)
        self.assertIsNone(result["elapsed"]["observed_p50_ms"])

    def test_control_share_requires_complete_usage(self):
        result = group(run_record(expected_calls=2), call_record(),
                       call_record(call_id="c2", purpose="workflow-control"))
        self.assertEqual(result["workflow_control_token_share"], 0.5)
        result = group(run_record(expected_calls=3), call_record(purpose="workflow-control"))
        self.assertIsNone(result["workflow_control_token_share"])

    def test_decimal_costs_are_not_binary_floats(self):
        result = group(run_record(expected_calls=2), call_record(cost_usd="0.1"),
                       call_record(call_id="c2", cost_usd="0.2"))
        self.assertEqual(result["usage"]["cost_usd"]["total"], "0.3")

    def test_jsonl_and_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            records = [run_record(), call_record()]
            path.write_text("\n\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
            self.assertEqual(metrics.read_jsonl([path]), records)
            proc = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["groups"][0]["tokens_per_accepted_run"], 120)

    def test_bad_jsonl_diagnostics_do_not_echo_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.jsonl"
            for content in (b'{"private":"SECRET_TEXT",}', b'\xffSECRET_TEXT',
                            b'{"schema":"workflow-usage-v1","schema":"SECRET_TEXT"}',
                            b'{"value": NaN, "private": "SECRET_TEXT"}',
                            b'x' * (metrics.MAX_LINE_BYTES + 1)):
                path.write_bytes(content)
                with self.assertRaises(metrics.UsageError) as raised:
                    metrics.read_jsonl([path])
                self.assertNotIn("SECRET_TEXT", str(raised.exception))
            proc = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main()
