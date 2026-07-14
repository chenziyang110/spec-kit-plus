---
name: spx-ask
description: Lean, evidence-backed project Q&A for advanced coding models. Use when the user wants to understand repository facts, architecture, status, impact, or workflow choices without changing files.
---

# SPX Ask

Read `references/project-cognition.md`, using cognition intent `ask`.
Read `references/evidence-contract.md` for architecture, status, or impact
claims. Read `references/artifact-explanation.md` only for generated workflow
artifacts or lane state.

Answer the question from the smallest sufficient live repository evidence set.
Lead with the conclusion, cite concrete paths, and distinguish verified facts,
evidence-backed inference, and remaining unknowns. Project cognition selects
where to look; the live repository proves the answer.

Remain read-only. Do not create workflow state, handoffs, reports, memory, or
planning artifacts. Avoid commands that mutate dependencies, caches, generated
assets, or application state. Recommend another SPX skill only when the user is
asking for follow-on action; do not switch workflows automatically.
