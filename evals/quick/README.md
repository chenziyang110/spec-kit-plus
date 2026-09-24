# Quick adaptive execution benchmark

Measure full-chain cost and independently accepted outcomes, not prompt length
alone. The checked-in fixtures exercise the evaluation plumbing; they are not
real Agent measurements or evidence of production quality retention.

## Reproducible task fixtures

`tasks.yaml` retains five case IDs. `fixtures.json` provides fixed task text,
initial source files and a frozen executable check for each ID:

| ID | Controlled fixture | Required behavior |
| --- | --- | --- |
| Q001 | Configuration | Change one value without altering adjacent settings |
| Q002 | Isolated feature | Normalize tags, preserve order and reject invalid input |
| Q003 | Cross-module change | Keep a decimal tax contract and pricing behavior consistent |
| Q004 | Permission change | Deny unknown roles/actions instead of expanding authority |
| Q005 | Recovery | Preserve missing/malformed checkpoint evidence; never silently reset it |

Prepare separate external workspaces for every mode and repetition:

```bash
python tools/workflow-quality/quick_eval_case.py prepare Q001 ../quick-Q001-direct-full
```

The command refuses existing destinations and output inside the source checkout.
It writes an immutable-input identity, TASK.md and a `project/` directory. Give
the selected Agent only the task and that editable project, with the write scope
from TASK.md. Keep the verifier and `tests/quick_fixture_reference.json` reference
solutions outside the Agent's readable/writable workspace for a real comparison.
The helper does not itself launch or sandbox Agents.

After execution, run the frozen functional check from the source checkout:

```bash
python tools/workflow-quality/quick_eval_case.py verify Q001 ../quick-Q001-direct-full
```

Each case has a content-addressed snapshot. Verification refuses retargeted task
metadata, changed fixture identity, out-of-scope files and symlinks; it rechecks
scope after project execution. An exit-0 process that does not finish the oracle
is not a passing check. Exit codes are 0 for preparation/functional-check success,
1 for a failed functional check and 2 for invalid input or blocked execution.
Python isolation flags are not a security sandbox: run untrusted Agent output
only in an appropriately isolated host. Human acceptance remains null even when
a functional check passes. No Agent tokens are invented by this helper.

## Execution matrix and observation contract

Compare worker-full, worker-compact, direct-full and direct-compact only where
the existing task's execution/authorization policy permits them. Do not weaken a
risk gate to fill a matrix cell. Hold task snapshot, starting repository, model,
settings, tools and environment fixed; record every attempt and rework cost.

`quick_adaptive_eval.py` owns shared record validation. The JSONL report CLI is:

```bash
python tools/workflow-quality/quick_eval_runner.py observations.jsonl --strict --output report.json
```

Strict records require `run_id`, `case_id`, `source_revision`, `model` and
`environment`. Preserve the fixture digest, model settings, attempt relationship
and independent acceptance evidence in `notes`. The existing usage exporter may
supply observed metrics, but associating them with the exact run is a separate,
verified harness responsibility. Never turn estimates into measured values.

Metrics accept non-negative integers or null. Booleans require real JSON
booleans or null. Duplicate run IDs are rejected globally. Legacy unidentified
records remain inspectable but cannot claim complete deduplication. Reports are
create-only and empty input is rejected.

## Report v2 semantics

`accepted_rate` uses known accepted/rejected outcomes, not unknown outcomes.
Always read `acceptance_coverage` alongside it; all-unknown means a null rate.
Metric `sum` describes observed values, while `total` is null unless every run
has that metric. `mean` uses observed samples and includes coverage.
`tokens_per_accepted_run` includes failed-run token cost and remains null if
any outcome/cost is unknown or there is no accepted run. It is a per-run metric,
not a deduplicated final-task cost or proof of fair experimental pairing.

The aggregator validates observations; it does not independently verify human
acceptance, task comparability, permissions or quality. Real multi-mode Agent
runs, host instrumentation, repeated samples and independent product acceptance
remain required before claiming cost reduction or retained quality.
