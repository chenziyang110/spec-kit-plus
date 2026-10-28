---
name: spx-auto
description: State-aware workflow continuation for advanced coding models. Use when the user wants to resume or execute the safest next SPX step without naming the exact workflow.
---

# SPX Auto

Read `references/project-learning.md` and apply its consume-only policy.
Read `references/project-cognition.md`, using cognition intent `ask`, and
`references/routing-contract.md`.
Read `references/ui-quality-gate.md` when the request or active state is
UI-bearing.

Inspect only enough state to identify the highest trustworthy stage: current
diff, active feature/test-design/implementation/quick/debug state, recoverable discussion handoff,
task completion evidence, and cognition readiness. Treat status labels and
checked boxes as claims until their required artifacts and live evidence agree.

Select exactly one next SPX workflow, read that Skill, and continue immediately
when its boundary is clear. Prefer resuming existing valid state over creating a
new lane. Do not use auto to bypass a user-owned decision, external-write
authorization, destructive action, or a blocked validation gate.
Stop after that workflow returns; do not invoke a second workflow in the same
invocation. Report any downstream route as a handoff only.

Pass `auto_default_recommendation: true` only to that selected workflow. It may
accept one explicit safe default that preserves current intent and scope. Never
use it for scope reduction, destructive or irreversible action, security or
credential decisions, external cost, or unresolved planning ambiguity.
Keep this hint turn-local; never persist it as the canonical next route.

For Quick, `auto_default_recommendation` cannot confirm a pending Decision
Checkpoint, select **Direct change (Recommended)**, approve a UI direction or
substitute for required human acceptance. Resume only an unchanged exact
human-approved decision or validated inherited binding. When proposal approval
is pending, gather safe bounded read-only evidence under Quick's intake gates,
present current findings, concrete change, impact, risks and verification, then
wait for the real human reply. An Auto recommendation is never the user's Quick
approval. Material decision deltas retain reason-first amendment confirmation;
execution-only rearranges do not re-confirm.

For Debug, `auto_default_recommendation` cannot grant repair or
`diagnostic-enablement` consent, select **Direct fix (Recommended)**, or
substitute for final human verification. Continue repair only when unchanged and
already covered by exact human-approved decision content and its current
binding. When repair or diagnostic consent is pending, present concise findings
and the concrete proposed plan, then wait for a real human reply under the
Debug confirmation contract. For pending final human verification, present the
verification evidence and wait for the user's result; an Auto recommendation
is never the user's Debug approval or verification.
Safe bounded diagnosis remains available under Debug's intake gates before the
repair checkpoint.

Create no separate auto state, report, or orchestration layer. If evidence is
ambiguous, state the competing routes and ask only for the decision the
repository cannot resolve. Report the selected route and the concrete state
signal that justified it.
