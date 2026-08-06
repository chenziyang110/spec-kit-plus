---
name: spx-fast
description: Lean direct-change workflow for advanced coding models. Use for a truly trivial, local, low-risk change with a known solution and a small verification surface.
---

# SPX Fast

Read `references/project-learning.md` only for its explicit skip/escalation policy.
Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/run-bootstrap.md`.
Use `references/scope-gate.md` when eligibility is not immediately obvious.
Read `references/consequence-gate.md` when work can affect lifecycle operations,
running objects, concurrent work, destructive behavior, shared state, downstream
consumers, compatibility, security-sensitive behavior, or multiple plausible
product behaviors.
Read `references/ui-quality-gate.md` for any user-visible UI change.

`$spx-fast` always starts a new run. Record that new run with `specify-runtime run create`, then execute only through `specify-runtime run supervise`; do not resume another workflow's run.

Use this leader-direct path only when the change is obvious, local, and normally
touches no more than three files. It must not cross a shared contract, registry,
dependency, migration, security boundary, or unresolved product decision. Route
unknown root causes to `$spx-debug`, and all expanding or larger direct-delivery
work to `$spx-quick`.
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
edits. If there is no reliable automated test surface, hand off to `$spx-quick`
and stop; documentation, formatting, and mechanically
provable non-behavior changes may use a direct before/after check.
Run the smallest meaningful verification after editing. If the edit propagates
to generated, mirrored, registered, or downstream consumer surfaces, leave fast
and route the complete change through `$spx-quick`.
For eligible UI, include a representative visual capture and runtime diagnostics,
plus a structure snapshot when semantics, hierarchy, focus, or interaction
changes, and perform visual inspection;
code or style tests alone do not close the change.

Create no spec, plan, tasks, quick workspace, delegation packet, or lifecycle
artifact. When repository behavior changed, run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-fast --intent implement --format json}}`
then update/finalize (or mark-dirty) and
`{{specify-subcmd:specify-runtime cognition mutation-receipt --workflow sp-fast --scope-dir <project-or-workspace> --result-state ready|no_op|mark-dirty|partial --reason "<text>" --format json}}`
before claiming the fast change complete—project cognition must keep improving
with explicit workflow-owned paths, fill returned agent-owned fields, and execute
structured `update_argv`. Apply the receipt-bound finalizer gate in
`references/project-cognition.md` before any clean claim. Report the outcome, changed paths, exact verification, and
residual risk. This invocation authorizes only this workflow stage; report any
escalation as a handoff and do not invoke another workflow in this run.
