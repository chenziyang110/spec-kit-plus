---
name: spx-auto
description: State-aware workflow continuation for advanced coding models. Use when the user wants to resume or execute the safest next SPX step without naming the exact workflow.
---

# SPX Auto

Read `references/project-cognition.md`, using cognition intent `ask`, and
`references/routing-contract.md`.
Read `references/ui-quality-gate.md` when the request or active state is
UI-bearing.

Inspect only enough state to identify the highest trustworthy stage: current
diff, active feature/lane/quick/debug state, recoverable discussion handoff,
task completion evidence, and cognition readiness. Treat status labels and
checked boxes as claims until their required artifacts and live evidence agree.

Select exactly one next SPX workflow, read that Skill, and continue immediately
when its boundary is clear. Prefer resuming existing valid state over creating a
new lane. Do not use auto to bypass a user-owned decision, external-write
authorization, destructive action, or a blocked validation gate.

Create no separate auto state, report, or orchestration layer. If evidence is
ambiguous, state the competing routes and ask only for the decision the
repository cannot resolve. Report the selected route and the concrete state
signal that justified it.
