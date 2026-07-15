---
name: spx-fast
description: Lean direct-change workflow for advanced coding models. Use for a truly trivial, local, low-risk change with a known solution and a small verification surface.
---

# SPX Fast

Read `references/project-cognition.md`, using cognition intent `implement`.
Use `references/scope-gate.md` when eligibility is not immediately obvious.
Read `references/consequence-gate.md` when work can affect lifecycle operations,
running objects, concurrent work, destructive behavior, shared state, downstream
consumers, compatibility, security-sensitive behavior, or multiple plausible
product behaviors.
Read `references/ui-quality-gate.md` for any user-visible UI change.

Use this leader-direct path only when the change is obvious, local, and normally
touches no more than three files. It must not cross a shared contract, registry,
dependency, migration, security boundary, or unresolved product decision. Route
unknown root causes to `$spx-debug`, expanding but bounded work to `$spx-quick`,
and feature-level behavior to `$spx-specify`.
When the consequence gate triggers, do not edit on the fast path: route bounded
consequences to `$spx-quick` and route broader or user-owned consequences to
`$spx-specify`. When it stands down, report the concrete no-trigger reason.

UI is fast-eligible only for a narrow change that follows an approved existing
pattern, has no unresolved visual/product choice, and can be checked at the real
entry point. A bootstrap/missing design system routes to `$spx-design`; a new
surface, reference-driven fidelity target, or multi-state responsive change
routes to `$spx-quick` or `$spx-specify`.

Inspect the current diff and the cognition-selected live paths. Before any
non-obvious path read or edit, resolve the path and prove the resolved path
remains inside the repository. Refuse a credential, secret, private key, token,
or similarly sensitive path; if containment or sensitivity is uncertain, stop
and request an explicit safe path.

Make the smallest coherent change while preserving unrelated work. A behavior
change must run a failing automated test or executable repro before production
edits. If there is no reliable automated test surface, hand off to `$spx-quick`
or `$spx-specify` and stop; documentation, formatting, and mechanically
provable non-behavior changes may use a direct before/after check.
Run the smallest meaningful verification after editing. If the edit propagates
to generated, mirrored, registered, or downstream consumer surfaces, leave fast
and route the complete change through `$spx-quick` or `$spx-specify`.
For eligible UI, include a representative visual capture and runtime diagnostics,
plus a structure snapshot when semantics, hierarchy, focus, or interaction
changes, and perform visual inspection;
code or style tests alone do not close the change.

Create no spec, plan, tasks, quick workspace, delegation packet, or lifecycle
artifact. Close out cognition with canonical workflow `fast` when repository
behavior changed. Report the outcome, changed paths, exact verification, and
residual risk. This invocation authorizes only this workflow stage; report any
escalation as a handoff and do not invoke another workflow in this run.
