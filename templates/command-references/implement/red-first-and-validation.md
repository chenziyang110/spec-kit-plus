Trigger: before code-writing, test execution, or validation closeout.

Purpose: preserve change-set RED-first expectations, cheap task checks, bounded logical validation gates, retryable attempts, validation evidence, and no-greenwashing rules.

Preserved Contract: implementation must prove a truthful change-set baseline before behavior changes and verify completed work without multiplying heavyweight gates per Txx.

## Shared Logical-Gate Budget

Use one durable validation ledger shared across Implement and Review. The budget
counts three logical gates (`baseline`, `convergence`, `delivery`), not physical
tool invocations. Each gate owns one or more attempts against source
fingerprints. Runner timeout, process termination, cancellation, harness
failure, or environment loss closes only the current attempt as `interrupted`;
it does not consume another logical gate or become a test failure. Persist gate
id, attempt id, owner, source fingerprint, scope, commands/scenarios, verdict or
interruption kind, evidence, and cumulative gate/attempt counts. Carry this
ledger unchanged in `implementation-handoff.json`.

Require `task-index.validation_policy` to declare exactly:

```yaml
mode: feature_epochs
max_epochs: 3
budget_scope: implement-review
budget_ref: implementation-review/validation-runs.json
heavy_gate_owner: leader
```

Before allocating work, run:

```text
{{specify-subcmd:implement validation-status --feature-dir <feature-dir> --format json}}
```

Immediately before a Leader-owned baseline or convergence wave, run:

```text
{{specify-subcmd:implement validation-start --feature-dir <feature-dir> --stage implement --purpose <baseline|convergence> --command '<cmd>' [--command '<cmd2>'] [--task-id T001] [--task-id T002] [--fingerprint <sha>] --format json}}
```

Omit `--fingerprint` to bind the current implementation snapshot automatically.
Immediately after the wave, run:

```text
{{specify-subcmd:implement validation-finish --feature-dir <feature-dir> --run-id <Vn> --status <passed|failed|interrupted> [--failure-kind <assertion|verification|harness|environment|runner_timeout|runner_terminated|cancelled|unknown>] --evidence-ref <ref> [--evidence-ref <ref2>] --summary '<text>' --format json}}
```

Use the returned gate id, attempt id, counts, recovery action, and ledger ref;
never hand-edit the ledger or infer capacity from chat history.

The combined workflow may open at most three logical gates:

1. optional change-set RED or credible baseline before production edits;
2. Implement convergence over the affected test/build surface;
3. integrated system Review delivery.

Allocate them dynamically; do not open an optional gate merely to fill a slot.
For a RED/baseline gate, `passed` means the expected pre-change failure or
credible before-state was observed; reserve `failed` for an inconclusive,
misconfigured, or unexpectedly behaving baseline.
Only the Leader opens or closes a gate attempt. Resumes, joins, task
transitions, subagents, and passive skills reuse the ledger. An
`interrupted` attempt may retry the same gate and fingerprint. A real assertion
or verification failure may retry the same gate only after source/configuration
changes produce a new fingerprint. A passed gate may also receive a fresh
attempt when later repairs change that fingerprint. Attempts never steal the
reserved delivery gate. Never open a fourth logical gate, and never record a
timeout or runner kill as `failed` or `passed`.

After `runner_timeout`, do not immediately rerun the full command. First decide
whether the suite legitimately exceeds the execution ceiling or stopped making
progress. Preserve the last completed shard/test and the first incomplete test
in evidence. Run that test in isolation with the runner's open-handle,
process-exit, leaked-service, or equivalent diagnostics. Repair a local hang,
fixture defect, or orphan process as agent-owned work. If the suite is simply
long, split the same gate command into deterministic bounded shards and record
all shard commands under the same attempt/gate; sharding is not another logical
gate or validation attempt.

If the evidence cannot be obtained now, keep dependency-safe work moving. A
human may explicitly transfer a precisely scoped low/medium-risk blocker to
Review by first proposing
`{{specify-subcmd:implement deferral-propose --feature-dir <feature-dir> --input <proposal.json> --format json}}`
and, only after the human confirms that exact proposal digest, recording
`{{specify-subcmd:implement deferral-confirm --feature-dir <feature-dir> --deferral-id <DEF-id> --proposal-sha256 <sha> --confirmation-source <source> --statement '<exact-human-statement>' --format json}}`.
The proposal must identify blocker/task/acceptance refs, exact excluded
behavior, residual risk, claims withheld, and the Review reopen condition.
Deferral means unresolved and transferred to Review; it never means passed and
expires at Review. It cannot waive high/critical, security, data-integrity,
core-startup, or required acceptance failures. Local assertion failures,
fixable test fixtures, leaked processes, and diagnosable hangs remain
agent-owned and are not eligible merely because a human is willing to skip
them.

## Current Task Gate

Before code changes:

1. Validate current task dependencies, required refs, expected write scope,
   forbidden drift, acceptance, and verification route. If delegated, validate
   the just-in-time WorkerTaskPacket; leader-direct work uses the same task gate
   without packet boilerplate.
2. For parallel lanes, require zero overlapping writes and an explicit join
   validation target. Serialize overlapping work.
3. Group related behavior-changing Txx items into a coherent change-set. Write or
   select the smallest tests/repro checks before production edits, then let the
   Leader execute them together in the optional RED/baseline gate. One honest
   expected failure may cover several mapped Txx items; record the mapping.
4. If an honest RED state cannot be produced without spending a disproportionate
   gate, record the credible before-state, reason, and residual risk. Block when
   acceptance cannot ultimately be proven.
5. Per-Txx task checks are cheap, deterministic, and local: inspect the diff,
   parse/format touched files, validate schemas/contracts, or perform an
   equivalent non-suite static check. They do not start services, browsers,
   builds, test suites, coverage, integration tests, or E2E. Record test impact
   and the checks the Leader must include in the next gate attempt.

## Convergence And Closeout

After the change:

1. Do not rerun RED/GREEN or a heavyweight gate per Txx. After cheap task checks
   and join review, record bounded implementation completion and continue with
   dependency-safe work while feature verification remains pending.
2. After the coherent change-set is integrated, the Leader opens one convergence
   gate and runs the mapped affected tests/build checks once in an attempt against its source
   fingerprint. Cache or reuse exact command results only for that unchanged
   fingerprint.
3. Record commands, outcomes, changed paths, covered Txx ids, and remaining
   manual checks once in the ledger; task lifecycles reference that gate attempt
   instead of copying command output.
4. Real-entrypoint and UI matrices belong to a coordinated integrated attempt, not
   every microtask. Do not run the full viewport/state capture loop per Txx.
5. Do not claim success from task markers, worker narration, unrelated passing
   tests, or stale fingerprint evidence.
