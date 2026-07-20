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

For each ready task:

- confirm authoritative inputs, dependencies, acceptance, likely write scope,
  and must-preserve obligations;
- establish RED or a credible before-state for behavior changes;
- implement the complete outcome and update generated/mirrored consumers;
- verify the real entry point and material boundaries, not only an isolated
  helper;
- record changed paths, checks, obligation evidence, blockers, and recovery.

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

For UI tasks, apply the packet `ui_contract` as binding scope. Run the visual convergence loop at the real entry point: render the required states and
viewports, capture stable screenshots or platform output, inspect against
`DESIGN.md`, `ui-brief.md`, prior surfaces, and original references, repair
concrete drift, then recapture. Check overflow, console, keyboard/focus, and
accessibility when applicable. Persist difference inventory and accepted
deviations for approximate/high fidelity. tests passed is not visual acceptance;
unavailable comparison is `pending-human-review` with an exact review target.
Before accepting the task, persist its lifecycle `ui_verification` with
`applicable: true`, `evidence_scope: task`, typed structure/visual/runtime
evidence refs, passing runtime evidence, visual comparison, fidelity status,
reviewer, and human-review ref when relevant.
`pending-human-review` blocks accepted closeout until that review is resolved.

Perform task-level review on drift, parallel joins, write-scope changes,
validation failure, worker concern, obligation conflict, real-entrypoint gaps,
or an oversized unreviewed window. This does not replace the mandatory
post-implementation system Review. Repair only understood local failures;
reopen planning or debugging when upstream truth or root cause is unknown.

Every cross-workflow route is a handoff-and-stop boundary. Hand off unknown root
causes to `$spx-debug`, missing/invalid design truth to `$spx-design`, durable
team execution to `$spx-implement-teams`, and independent lane closeout to
`$spx-integrate`; do not run any of them inline in this invocation.

Before completion, run
`{{specify-subcmd:implement closeout --feature-dir <feature-dir> --format json}}`
when available.

Successful closeout must return a trusted `implementation_handoff` with its
source revision, implementation fingerprint, official entrypoints, and required
system Review scenarios. Hand off to `$spx-review` and stop. Do not route
directly to `$spx-accept`; implementation tests, task-level agent review, and
technical closeout do not substitute for integrated product Review or a later
human verdict.

Before stopping, update owned rich `workflow-state.md` evidence/resume fields
truthfully, including the Review handoff. Then run the workflow runtime
`complete-stage` command with the current revision. It records
`implement/completed` only in CLI-owned `workflow-runtime.json`; it does not update
rich `workflow-state.md` fields such as `active_command`, `phase_mode`, or
`next_command`. Do not execute
the returned transition or set `active_command: sp-review`; the separately
invoked Review workflow claims that phase only when it actually starts.
