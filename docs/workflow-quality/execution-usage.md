# Execution usage accounting

## Scope

`measure_execution_usage.py` is an offline, standard-library-only analyzer for
metadata exported by an agent host or evaluation harness. It complements
`measure_workflow_costs.py`, which measures source/artifact text volume.

It does not collect usage automatically, invoke models, change workflow policy,
price models, convert bytes to billed tokens, or verify acceptance evidence.
Host adapters and real-project A/B runs are still separate work. Do not label
synthetic fixtures or estimator output as production telemetry.

## Run

From the repository root, with Python 3.11 or newer:

```sh
python tools/workflow-quality/measure_execution_usage.py trace.jsonl
```

Multiple files may contain disjoint pieces of the same run. Duplicate run or
call records fail rather than double-count. The analyzer writes JSON to stdout;
invalid input exits with code 2 and does not emit a partial success summary.
It performs no network access or workflow writes.

A deliberately **synthetic** smoke example is included:

```sh
python tools/workflow-quality/measure_execution_usage.py \
  tools/workflow-quality/examples/usage.synthetic.jsonl
```

That example has two attempts, one accepted and one failed, and includes a
worker and reviewer. Its 3,300 total tokens and USD 0.031 are invented fixture
values, not measured costs or evidence of savings.

## JSONL contract: workflow-usage-v1

Every line is an object with `schema`, `kind`, and a nonblank `run_id`. Input is
strict UTF-8; duplicate JSON keys, unknown fields, and non-finite numbers fail.
Blank lines are ignored. Each line is limited to 1 MiB including its newline.
Only metadata belongs here: never export prompts, code, responses, or secrets.
Errors do not echo record values. Identifiers/labels are at most 200 characters,
with no control characters or surrounding whitespace.

### Run record

| Field | Contract |
| --- | --- |
| `kind` | `run` |
| `case_id`, `variant` | Nonblank workload and configuration identifiers |
| `outcome` | `accepted`, `failed`, or `blocked`, assigned by an external evaluator |
| `expected_calls` | Required nonnegative integer, or null when completeness is unknown; includes all leader, worker, reviewer and retry calls |
| `acceptance_evidence` | Required nonblank reference for accepted runs; optional or null otherwise |
| `elapsed_ms` | Optional measured end-to-end duration, including human wait; null when unavailable |
| `human_wait_ms` | Optional measured subset of elapsed time; null when unavailable |

Exactly one run record is allowed per `run_id`. The evidence reference is a
pointer supplied by the evaluator, not a proof checked by this analyzer.
Export failed and blocked attempts too. One accepted run is the denominator
unit; it is not a count of distinct features shipped.

### Call record

| Field | Contract |
| --- | --- |
| `kind` | `call` |
| `call_id` | Unique within a run; every retry and worker call has its own ID |
| `model`, `role`, `stage` | Nonblank labels for breakdowns; host supplies them |
| `purpose` | `work`, `workflow-control`, or `verification`; exporter classification, not inferred by the analyzer |
| `usage_kind`, `measurement` | Exactly `delta` and `reported`; cumulative/estimated input is rejected |
| `input_tokens` | Optional total reported input INCLUDING cache-hit input |
| `cached_input_tokens` | Optional cache-read subset of input; requires known input and cannot exceed it |
| `output_tokens` | Optional reported output INCLUDING any billed reasoning tokens already counted by the provider |
| `duration_ms` | Optional per-call duration; not substituted for run elapsed time |
| `cost_usd` | Optional externally reported USD amount as a nonnegative decimal string; no float, currency conversion, or inferred pricing |

Missing usage stays unknown. Counts are nonnegative integers (not booleans,
strings, or floats), at most 2^63 - 1. Dollar strings have at most 12 digits
before and after the decimal point. Cache writes must already be included in
normalized total input; their pricing is only represented in reported cost.
An adapter must normalize provider semantics before export. Reasoning and
cache-hit tokens must never be added again as separate token categories.

## Interpreting the summary

Groups are independent per `variant`. Each usage metric contains:

- `observed_sum`: sum of available reported values, not necessarily the total;
- `unknown_calls`: observed calls lacking that metric;
- `total`: present only when every run's expected call count matches and every
  observed call has the metric; otherwise null.

A smaller observed call count than the manifest keeps totals unknown. More
calls than declared is an error. A null manifest count never proves completeness.
An explicit zero-call run may report zero usage; absent telemetry may not.

`tokens_per_accepted_run` and `cost_usd_per_accepted_run` divide costs of **all**
accepted, failed and blocked attempts by accepted runs. They remain null when
usage is incomplete or no run was accepted. Role, stage, model and purpose
breakdowns include workers. `workflow_control_token_share` is a token share,
not a monetary-cost share, and is unknown if total usage is incomplete or zero.

Elapsed and human-wait statistics report their known/unknown run counts. P50 is
the sample median; P95 uses the nearest-rank convention on the observed sample.
Parallel call durations are never summed to pretend they are wall-clock time.

Compare like-for-like case sets, source revisions, tools, models and environment
budgets, with repeated samples and an independent acceptance oracle. The tool
does not declare a winner, statistical significance, or 98% quality retention.
Incomplete telemetry and changed workloads must not be mistaken for savings.

## Validation

The analyzer and subprocess CLI tests require no third-party dependency:

```sh
python -m unittest discover -s tests -p test_execution_usage_metrics.py -v
```

They cover cache accounting, unknown metrics, incomplete exports, failed/worker
costs, zero successes, duplicate/cumulative records, metadata-only validation,
exact decimal sums, timing coverage and CLI success/error behavior.
