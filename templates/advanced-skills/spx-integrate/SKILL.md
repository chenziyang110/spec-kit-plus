---
name: spx-integrate
description: Independent feature-lane integration and closeout for advanced coding models. Use when isolated lanes are implementation-complete and need readiness, overlap, sequencing, and recovery checks before mainline merge or PR follow-through.
---

# SPX Integrate

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `implement`, and
`references/integration-contract.md`. Read `references/consequence-gate.md`
when integration crosses a shared state, migration, compatibility, security, or
generated-consumer boundary. Read `references/ui-quality-gate.md` when any lane
is UI-bearing.

Discover candidates with `{{specify-subcmd:specify-runtime integrate}}`. For each selected lane,
inspect its recorded ownership, feature/workflow state, branch and worktree,
implementation closeout evidence, current diff, dependency order, overlapping
writes, drift from mainline, unresolved conflicts, and required combined
verification.

This invocation establishes readiness, closeout, recovery, and dependency-order
guidance; it does not authorize a Git merge. The `integrate` helper only inspects and closes lane state.
Do not run merge, rebase, cherry-pick, or an
equivalent history-changing operation, and do not edit conflict markers,
production code, tests, or generated consumers to force readiness. If no
integrated tree already exists, report the exact merge/PR handoff and stop.

When an integrated tree already exists, validate it without claiming that this
workflow created it. Treat copied files, green isolated tests, or a clean merge
as inputs rather than lane closeout. Provide conflict-resolution guidance from
the authoritative spec/plan and live consumers. Unknown behavior hands off to
`$spx-debug` and unfinished feature work hands off to `$spx-implement`; every
cross-flow route is a handoff and stop boundary, never an inline invocation.

Run the combined real-entrypoint checks after the integrated tree exists. For
UI-bearing lanes, recapture the required viewport/state evidence from the
integrated tree and inspect it against the task UI contracts. If integration
drift needs source edits, hand off to `$spx-implement` and stop; unresolved
comparison remains `pending-human-review`.
Only
when readiness and verification pass may you close a lane with
`{{specify-subcmd:specify-runtime integrate --feature-dir <feature-dir> --close}}`. Preserve a
blocked lane and its recovery evidence instead of forcing terminal state.

For actual integrated repository changes, run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-integrate --intent implement --format json}}`
with explicit integration-owned paths, fill returned agent-owned fields, and execute
structured `update_argv`. Apply the receipt-bound finalizer gate in
`references/project-cognition.md` before any clean claim. Report
lane order, overlap/conflict decisions, checks run, closed lanes, and remaining
mainline or PR actions.
