---
name: spx-fast
description: Lean direct-change workflow for advanced coding models. Use for a truly trivial, local, low-risk change with a known solution and a small verification surface.
---

# SPX Fast

Read `references/project-cognition.md`, using cognition intent `implement`.
Use `references/scope-gate.md` when eligibility is not immediately obvious.

Use this leader-direct path only when the change is obvious, local, and normally
touches no more than three files. It must not cross a shared contract, registry,
dependency, migration, security boundary, or unresolved product decision. Route
unknown root causes to `$spx-debug`, expanding but bounded work to `$spx-quick`,
and feature-level behavior to `$spx-specify`.

Inspect the current diff and the cognition-selected live paths. Make the smallest
coherent change while preserving unrelated work. Establish a failing test or
credible baseline first when behavior changes and an automated surface exists.
Run the smallest meaningful verification after editing. If the edit propagates
to generated, mirrored, registered, or downstream consumer surfaces, leave fast
and route the complete change through `$spx-quick` or `$spx-specify`.

Create no spec, plan, tasks, quick workspace, delegation packet, or lifecycle
artifact. Close out cognition with canonical workflow `fast` when repository
behavior changed. Report the outcome, changed paths, exact verification, and
residual risk.
