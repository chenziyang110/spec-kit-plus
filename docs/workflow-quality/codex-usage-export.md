# Codex rollout usage export

`tools/workflow-quality/export_codex_usage.py` is an opt-in, local adapter for
`measure_execution_usage.py`. It turns supported Codex rollout snapshots into
metadata-only `workflow-usage-v1` call records. It does not start an agent,
search the home directory, install hooks, contact an API, or publish telemetry.
The existing analyzer and generated Classic/Advanced workflows are unchanged.

## Supported input and trust boundary

Use one explicit, stable, complete JSONL rollout for a fresh Codex thread. It
must begin with a `session_meta` record with a thread UUID. Usage needs a
preceding `turn_context` model. Supported `model_reroute` events update that
observed attribution. This is a shape-based adapter, not a promise that all
Codex releases or logs are compatible. Attribution is to the recorded model
identifier, not a verified billing SKU or provider invoice.

The adapter deliberately rejects forked/inherited history, compaction, rollback,
missing model context, unsupported token fields, nonzero cache-write accounting,
truncated input, counter resets and gaps. Fresh child threads with their own
UUIDs are supported; inherited child histories are not. Do not delete events or
edit counters to make an unsupported log pass. Add a separately tested,
lineage-aware adapter when those histories are needed.

All emitted calls receive the caller-supplied `run_id`, `role`, `stage` and
`purpose`. Use a dedicated thread for a homogeneous stage/purpose, or label the
whole session at an appropriately coarse level. Do not classify a mixed session
as entirely workflow-control to obtain a control-cost estimate. This exporter
does not infer per-call purpose from prompts. Caller labels and model identifiers
are still metadata that should be inspected before sharing.

## Export and analyze

Run from a source checkout with Python 3.11 or later. No additional Python
packages are required for these two tools. Copy a finished or paused rollout to
a private local snapshot before exporting; the tool checks file metadata for
changes during its read. That check is not a filesystem snapshot or protection
against adversarial edits.

```sh
python tools/workflow-quality/export_codex_usage.py /local/snapshot.jsonl \
  --run-id evaluation-001 --role leader --stage quick --purpose work \
  > leader-usage.jsonl 2> leader-export-report.json
```

Use a **new output path**, never the rollout path: shell redirection can truncate
an input before Python starts. Check the exit code before consuming output. A
validation failure returns exit code 2 with no call records on stdout. Diagnostics
omit raw log text, JSON keys/values and input filenames. The tool reads raw logs
only locally; it does not export prompts, responses, tool output, working-directory
paths or raw thread UUIDs. Exported call IDs contain deterministic thread/counter
hashes, which are pseudonymous identifiers rather than anonymization guarantees.

`purpose` must be `work`, `workflow-control`, or `verification`. Export each fresh
worker/reviewer rollout separately, using the same `run_id` for the same evaluated
attempt and the appropriate role. Include failure/retry usage; do not retain only
successful workers. A new evaluated attempt needs its own run ID. Stable IDs allow
the analyzer to detect overlapping imports within a run. Assigning the same log
to different run IDs cannot be detected as overlap by that analyzer.

The exporter emits **call rows only**. It never translates `task_complete`,
`turn_complete`, a zero exit code, or the end of a file into successful acceptance.
An independent evaluator supplies a separate `run` row:

```json
{"schema":"workflow-usage-v1","kind":"run","run_id":"evaluation-001","case_id":"case-001","variant":"candidate","outcome":"blocked","expected_calls":null,"elapsed_ms":null,"human_wait_ms":null}
```

This row is a format example, not an evaluation result. Record the actual outcome.
An `accepted` outcome also requires an actual `acceptance_evidence` reference;
the analyzer validates its presence, not the referenced evidence itself.

```sh
python tools/workflow-quality/measure_execution_usage.py \
  leader-usage.jsonl worker-usage.jsonl evaluation.jsonl
```

Omit `worker-usage.jsonl` when no worker file exists. Leave `expected_calls` null
unless an independent request inventory establishes completeness across all
participating threads, including failed and unreported requests. Do not fill it
with the exporter's `observed_calls`. With unknown completeness, the analyzer
reports observed sums but leaves complete totals and tokens-per-accepted-run
unknown. The exporter's stderr report always states that completeness and
acceptance are not established.

## Accounting rules

For every advancing `token_count.info`, the adapter requires the component-wise
identity `new total_token_usage = previous total_token_usage + last_token_usage`.
The initial total is zero. Only the **reported last delta** is emitted; cumulative
counters are used for continuity and duplicate detection, not converted into a
fabricated call when events are missing.

A repeated, unchanged cumulative snapshot emits no new call, even when it carries
a stale nonzero last delta. Two distinct calls with identical deltas are retained
when the cumulative counters advance. Null-info rate-limit events are ignored.
A coherent chain still cannot prove that all billable requests were logged;
zero-usage or unreported calls are not reconstructed.

Input includes cached-input tokens. Output includes reasoning-output tokens.
Neither subset is added again. Total must equal input plus output. Nonzero
cache-write tokens are unsupported by the current output schema and are rejected,
not silently discarded. Known context-window saturation can synthesize counters
that do not have this accounting identity; those records fail validation rather
than masquerading as provider-reported usage.

`cost_usd` and per-call `duration_ms` remain null. No price lookup, timestamp-delta
latency estimate, byte-to-token conversion or missing-value-as-zero rule is used.
The adapter has bounded input sizes (8 MiB per line, 1 GiB per file, 100,000
emitted calls) and rejects over-limit data instead of truncating the measurement.

## Protocol references

Inspected on 2026-09-15; upstream `main` is not a frozen format guarantee:

- [Official Codex protocol definitions](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/protocol.rs):
  `TokenUsage`, `TokenUsageInfo`, `TokenCountEvent`, `ModelRerouteEvent`,
  `update_with`, `add_assign` and `fill_to_context_window`.
- [Official rollout fixtures](https://github.com/openai/codex/blob/main/codex-rs/app-server/tests/common/rollout.rs):
  session/thread envelopes and representative token-count events. A fixture with
  a nonzero prior cumulative balance is intentionally not accepted as a complete
  fresh-thread export by this adapter.

## Verification and limits

```sh
python -m unittest discover -s tests -p test_codex_usage_export.py -v
python -m pytest tests/test_codex_usage_export.py -q
```

The 25 tests use synthetic local fixtures. They cover repeated snapshots, distinct
identical-usage calls, model changes/reroutes, parent/child IDs, continuity gaps,
malformed/synthetic counters, unsupported history, privacy-sensitive errors,
input growth/limits and FIFO rejection. One subprocess test invokes the actual
exporter and the unchanged actual analyzer end to end, checks the input bytes are
unchanged and verifies that incomplete totals remain unknown. No parser or
analyzer substitute is used in that test.

These tests are not a real-user rollout evaluation, a paid provider-usage audit,
a complete repository/Go/installed-profile regression, native Windows execution
or cloud CI evidence. No production token, latency, quality-retention or cost
saving percentage follows from synthetic fixture counts. Help/show discovery,
adaptive delegation, shared-state scheduling and continuous stage execution are
not modified by this adapter.
