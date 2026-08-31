---
name: spx-fast
description: Lean leader-direct workflow for advanced coding models. Use for a truly trivial, local, low-risk change that still needs consume-only Learning, Project Cognition, targeted verification, and lightweight review.
---

# SPX Fast

Read `references/project-learning.md`. Run Learning intake before Project
Cognition:
`{{specify-subcmd:specify-runtime learning start --command fast --format json}}`
Fast uses consume-only Learning: expand only a
task-relevant card through its `show_argv`; do not parse Learning storage and do
not capture or promote from this workflow.
Read `references/project-cognition.md`, using cognition intent `implement`,
only after Learning intake.
Read `references/execution-bootstrap.md`.
Read `references/autonomous-blocker-recovery.md` before treating any execution
or validation failure as terminal.
Use `references/scope-gate.md` when eligibility is not immediately obvious.
Read `references/consequence-gate.md` when work can affect lifecycle operations,
running objects, concurrent work, destructive behavior, shared state, downstream
consumers, compatibility, security-sensitive behavior, or multiple plausible
product behaviors.
Read `references/ui-quality-gate.md` for any user-visible UI change.

Work directly in the current worktree with exact task identity `fast:<task-id>`.
Use the shared execution bootstrap: announce complete planned scope, checkpoint
selection, refresh the overview, and require the all-or-none
`specify-runtime execution guard` before the first source write. Zero confirmed
write scope blocks mutation. Checkpoint validation and call
`specify-runtime execution complete` only after fresh passing validation and
terminal workflow state; preserve unrelated work and external approval gates.

Use this leader-direct path only when the change is obvious, local, and normally
touches no more than three files. It must not cross a shared contract, registry,
dependency, migration, security boundary, or unresolved product decision. Route
unknown root causes to `$spx-debug`, and all expanding or larger direct-delivery
work to `$spx-quick`.
Those are entry routes before Fast edits. When an active Fast gate exposes a
blocker, enter autonomous recovery mode inside Fast: preserve the evidence,
diagnose with Debug-grade discipline, expand registered scope only for the
causal repair, and continue in the same invocation. Do not invoke `$spx-quick`
or `$spx-debug` automatically. Return to the failed check after recovery; pause
only for a new product decision or genuine human/external boundary.
When the consequence gate triggers, do not edit on the fast path: route every
consequence-bearing implementation to `$spx-quick`, where user-owned decisions
use the Quick checkpoint. `$spx-specify` remains available only when the user
explicitly selected a formal spec-first workflow. When the gate stands down,
report the concrete no-trigger reason.

UI is fast-eligible only for a narrow change that follows an approved existing
pattern, has no unresolved visual/product choice, and can be checked at the real
entry point. A bootstrap/missing design system routes to `$spx-design`; a new
surface, reference-driven fidelity target, or multi-state responsive change
routes to `$spx-quick`.

Inspect the current diff and the cognition-selected live paths. Before any
non-obvious path read or edit, resolve the path and prove the resolved path
remains inside the repository. Refuse a credential, secret, private key, token,
or similarly sensitive path; if containment or sensitivity is uncertain, stop
and request an explicit safe path.

Make the smallest coherent change while preserving unrelated work. A behavior
change must run a failing automated test or executable repro before production
edits. If an active failure has no reliable automated test surface, build the
smallest viable harness as Fast-owned recovery work and register its scope;
documentation, formatting, and mechanically
provable non-behavior changes may use a direct before/after check.
Run the smallest meaningful verification after editing. If the edit propagates
to generated, mirrored, registered, or downstream consumer surfaces as part of
the causal repair, sweep and verify those surfaces inside recovery mode. New
unrelated product scope remains an explicit `$spx-quick` handoff.
For eligible UI, include a representative visual capture and runtime diagnostics,
plus a structure snapshot when semantics, hierarchy, focus, or interaction
changes, and perform visual inspection;
code or style tests alone do not close the change.

The same leader then performs one Lightweight Review; use no review subagent
and no worker packet. Review the complete changed diff against the declared
write scope and requested acceptance, check for an obvious regression, missed
consumer, security issue, or consequence drift, and confirm the targeted
verification exercises the changed behavior. Repair only in-scope defects,
then rerun the affected targeted verification and review the diff again. Expand
registered scope for a causal blocker repair; route only unrelated product
growth to `$spx-quick`. This Lightweight
Review does not claim the independent system Review contract owned by
`$spx-review`.

Create no spec, plan, tasks, quick workspace, delegation packet, or lifecycle
artifact. When repository behavior changed, run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-fast --scope-dir <project-or-workspace> --scope-mode explicit --intent implement --format json}}`
with explicit workflow-owned paths, fill returned agent-owned fields, and execute
structured `apply_argv` before claiming the fast change complete. Shared apply
owns update, validation, eligible finalization, and receipt; only an update
failure uses mark-dirty plus a standalone dirty receipt. Apply the gate in
`references/project-cognition.md` before any clean claim. Report the outcome,
changed paths, exact verification, Lightweight Review evidence, and residual
risk. This invocation authorizes only this workflow stage. An explicit
user-selected replacement workflow remains a handoff; do not invoke another
workflow in this run. An autonomous repair under
`references/autonomous-blocker-recovery.md` remains internal to Fast and must
continue to the recorded failed gate.
