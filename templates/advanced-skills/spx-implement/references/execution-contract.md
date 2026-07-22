# Execution lifecycle

Treat task checkboxes and prior status as claims until the live diff, required
evidence, and fresh verification support them. On an uncertain resume or a
terminal-looking tracker, run
`{{specify-subcmd:implement resume-audit --feature-dir <feature-dir> --format json}}`
before editing.

On entry or resume, stop and hand off to `$spx-analyze` when persisted state
requires an Analyze Gate, that gate is active/blocked or stale, or task-index
`source_revision` and current plan/task consistency cannot be trusted. Do not
run it inline. `gate_status: not-run` alone remains optional.

## Shared validation epochs

Use one durable validation-epoch ledger shared across Implement and Review. An
epoch is a Leader-authorized heavyweight verification wave against one source
fingerprint, even when it coordinates multiple commands or read-only observation
lanes. Persist id, owner, fingerprint, scope, commands/scenarios, result, failure,
covered Txx ids, and cumulative count. Carry the ledger unchanged through
`implementation-handoff.json`; do not reset it on resume or phase transition.

Require `task-index.validation_policy` to declare exactly:

```yaml
mode: feature_epochs
max_epochs: 3
budget_scope: implement-review
budget_ref: implementation-review/validation-runs.json
heavy_gate_owner: leader
```

Call
`{{specify-subcmd:implement validation-status --feature-dir <feature-dir> --format json}}`
before allocation. Immediately before a Leader-owned baseline or convergence
wave, call:

```text
{{specify-subcmd:implement validation-start --feature-dir <feature-dir> --stage implement --purpose <baseline|convergence> --command '<cmd>' [--command '<cmd2>'] [--task-id T001] [--task-id T002] [--fingerprint <sha>] --format json}}
```

Omit `--fingerprint` to bind the current implementation snapshot automatically.
Immediately after the wave, call:

```text
{{specify-subcmd:implement validation-finish --feature-dir <feature-dir> --run-id <Vn> --status <passed|failed> --evidence-ref <ref> [--evidence-ref <ref2>] --summary '<text>' --format json}}
```

Trust the returned run id, remaining budget, and ledger ref; do not hand-edit the
ledger.

The combined workflow permits at most three epochs: optional change-set
RED/baseline, Implement convergence, and integrated Review or final post-repair
revalidation. Allocate them dynamically. For a RED/baseline epoch, `passed`
means the expected pre-change failure or credible before-state was observed;
`failed` means that baseline was inconclusive, misconfigured, or unexpected. A
failed epoch may be repaired only if
another remains. Do not retry a failed command against the unchanged
fingerprint; change the source/configuration first or keep the failure as
blocking evidence. The third failed epoch blocks with exact evidence and
recovery criteria. Never start a fourth validation epoch.

For each ready task:

- confirm authoritative inputs, dependencies, acceptance, likely write scope,
  and must-preserve obligations;
- map behavior changes to the coherent change-set RED/baseline epoch, or stage a
  test-authoring-only lane before production edits;
- implement the complete outcome and update generated/mirrored consumers;
- run only cheap task checks such as bounded diff inspection,
  parse/format/schema checks, or another non-suite local static check;
- record changed paths, task checks, test impact, obligation evidence, blockers,
  and recovery; dependency-safe work may advance while feature verification
  remains pending.

Workers must not run a test suite, full build, startup, E2E flow, or browser
capture per Txx. The Leader opens one convergence epoch after integrating the
change-set and runs affected gates once. Task lifecycles reference the resulting
epoch instead of copying its command output.

## External and human verification blockers

When required evidence can only come from protected CI, a remote system, or a
human action, keep the task checkbox unchecked and its lifecycle status
`blocked`; local implementation completion is not task acceptance. Render each
blocker from `.specify/templates/task-lifecycle-schema.json#/$defs/blocker` and
fill every required field; do not reconstruct this stable schema from prose.

Keep the feature `executing` or `validating` while another dependency-safe task
can continue; mark the feature blocked only when no ready work remains. A
`mandatory_for_completion` blocker must not be converted to `accepted`, checked
off, or `resolved` before its evidence exists.

Do not push, trigger remote CI, or perform another external write without the
required authorization. For a commit needed to obtain mandatory protected-CI
evidence, first validate the checkpoint explicitly with
`{{specify-subcmd:hook validate-commit --commit-message <message> --feature-dir <feature-dir> --commit-intent external-evidence-checkpoint}}`.
Proceed only when that validation passes. On Claude or Gemini native hooks,
carry the same intent on the actual commit as
`git -c specify.commitIntent=external-evidence-checkpoint commit -m "<message>"`;
the hook binds it to the active feature and revalidates the task-local mandatory
external blocker. The resulting commit is a non-final checkpoint: it does not
finalize the workflow or authorize push, CI, or acceptance. Ordinary final
commits retain the terminal-state gate.

For UI tasks, apply the packet `ui_contract` as binding scope. Workers inspect
the original references and return changed surfaces, required states/viewports,
and visual risks. Do not run the full viewport/state capture loop per Txx.
Instead, run the visual convergence loop once for the integrated surface/source
fingerprint in a Leader-owned epoch: render the matrix at the official real
entry point, capture stable screenshots or platform output, inspect against
`DESIGN.md`, `ui-brief.md`, prior surfaces, and original references, repair
concrete drift while budget remains, then recapture in a later epoch. Check
overflow, console, keyboard/focus, and accessibility when applicable. Persist
typed structure/visual/runtime evidence with `evidence_scope: integrated`, plus
difference inventory and accepted deviations for approximate/high fidelity.
Tests passed is not visual acceptance; unavailable comparison is
`pending-human-review` with an exact review target and blocks verified closeout.

Perform task-level review on drift, parallel joins, write-scope changes,
validation failure, worker concern, obligation conflict, real-entrypoint gaps,
or an oversized unreviewed window. This does not replace the mandatory
post-implementation system Review. Repair only understood local failures;
reopen planning or debugging when upstream truth or root cause is unknown.

Give every discovered gap an orthogonal classification. `implementation_gap`
means upstream behavior is clear but code/wiring/tests are wrong;
`traceability_gap` means supported behavior lacks task/CA/validation mapping;
`upstream_truth_gap` means user-visible behavior, recovery/retry/cancel,
interaction escalation, lifecycle, requirement, design, or architecture truth
is missing or contradictory. Repair implementation gaps locally; repair safe
task traceability or reopen Tasks/Plan; stop and reopen the owning upstream
workflow for an upstream truth gap. A new behavior/test with no requirement,
acceptance, or CA ref is not an implementation-only repair.

Every cross-workflow route is a handoff-and-stop boundary. Hand off unknown root
causes to `$spx-debug`, missing/invalid design truth to `$spx-design`, durable
team execution to `$spx-implement-teams`, and independent lane closeout to
`$spx-integrate`; do not run any of them inline in this invocation.

Before completion, run
`{{specify-subcmd:implement closeout --feature-dir <feature-dir> --format json}}`
when available.

Successful closeout must return a trusted `implementation_handoff` with its
source revision, implementation fingerprint, official entrypoints, and required
system Review scenarios, plus the validation-epoch ledger and remaining budget.
Revalidate the handoff against the live Spec, Plan,
and Tasks and preserve their exact complete `acceptance_refs` denominator,
`acceptance_denominator_sha256`, and frozen Human Acceptance Universe
(`human_acceptance_obligations`, `human_acceptance_scenarios`, and
`human_acceptance_contract_sha256`) unchanged;
never omit an item, downgrade `required`, or reconstruct the contract from
prose. Review must continue the shared epoch ledger and must not reset it.
Implement must not create, infer, or prefill `reviewed_runtime_targets`;
only `$spx-review` creates those immutable targets after final integrated
evidence and snapshot validation. Hand off to `$spx-review` and stop. Do not route
directly to `$spx-accept`; implementation tests, task-level agent review, and
technical closeout do not substitute for integrated product Review or a later
human verdict.

Before stopping, update owned rich `workflow-state.md` evidence/resume fields
truthfully, including the Review handoff. Then run the workflow runtime
`complete-stage` command with the current revision. It records
`implement/completed` only in CLI-owned `workflow.json`; it does not update
rich `workflow-state.md` fields such as `active_command`, `phase_mode`, or
`next_command`. Do not execute
the returned transition or set `active_command: sp-review`; the separately
invoked Review workflow claims that phase only when it actually starts.
