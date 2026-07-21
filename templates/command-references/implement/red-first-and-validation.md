Trigger: before code-writing, test execution, or validation closeout.

Purpose: preserve change-set RED-first expectations, cheap task checks, bounded validation epochs, validation evidence, and no-greenwashing rules.

Preserved Contract: implementation must prove a truthful change-set baseline before behavior changes and verify completed work without multiplying heavyweight gates per Txx.

## Shared Validation-Epoch Budget

Use one durable validation-epoch ledger shared across Implement and Review. An
epoch is one Leader-authorized heavyweight verification wave against one source
fingerprint; it may contain multiple coordinated commands and scenarios, but
splitting them across workers does not create independent budgets. Persist its
id, owner, source fingerprint, scope, commands/scenarios, result, failure
summary, and cumulative consumed count in execution state and carry it unchanged
in `implementation-handoff.json`.

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
{{specify-subcmd:implement validation-finish --feature-dir <feature-dir> --run-id <Vn> --status <passed|failed> --evidence-ref <ref> [--evidence-ref <ref2>] --summary '<text>' --format json}}
```

Use the returned run id, remaining budget, and ledger ref; never hand-edit the
ledger or infer capacity from chat history.

The combined workflow may consume at most three epochs:

1. optional change-set RED or credible baseline before production edits;
2. Implement convergence over the affected test/build surface;
3. integrated system Review or, when an earlier epoch was skipped, the final
   post-repair revalidation.

Allocate them dynamically; do not run an optional epoch merely to fill a slot.
For a RED/baseline epoch, `passed` means the expected pre-change failure or
credible before-state was observed; reserve `failed` for an inconclusive,
misconfigured, or unexpectedly behaving baseline.
Only the Leader opens or closes an epoch. Resumes, joins, task transitions,
subagents, and passive skills reuse the ledger and must not start another run.
A failed epoch may lead to a bounded repair only when another epoch remains.
Do not retry a failed command against the unchanged fingerprint; change the
source/configuration first or preserve the failure as blocking evidence.
The third failed epoch blocks with evidence and exact recovery criteria. Never
start a fourth validation epoch.

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
   Leader execute them together in the optional RED/baseline epoch. One honest
   expected failure may cover several mapped Txx items; record the mapping.
4. If an honest RED state cannot be produced without spending a disproportionate
   epoch, record the credible before-state, reason, and residual risk. Block when
   acceptance cannot ultimately be proven.
5. Per-Txx task checks are cheap, deterministic, and local: inspect the diff,
   parse/format touched files, validate schemas/contracts, or perform an
   equivalent non-suite static check. They do not start services, browsers,
   builds, test suites, coverage, integration tests, or E2E. Record test impact
   and the gates the Leader must include in the next epoch.

## Convergence And Closeout

After the change:

1. Do not rerun RED/GREEN or a heavyweight gate per Txx. After cheap task checks
   and join review, record bounded implementation completion and continue with
   dependency-safe work while feature verification remains pending.
2. After the coherent change-set is integrated, the Leader opens one convergence
   epoch and runs the mapped affected tests/build gates once against its source
   fingerprint. Cache or reuse exact command results only for that unchanged
   fingerprint.
3. Record commands, outcomes, changed paths, covered Txx ids, and remaining
   manual checks once in the epoch ledger; task lifecycles reference that epoch
   instead of copying command output.
4. Real-entrypoint and UI matrices belong to a coordinated integrated epoch, not
   every microtask. Do not run the full viewport/state capture loop per Txx.
5. Do not claim success from task markers, worker narration, unrelated passing
   tests, or stale fingerprint evidence.
