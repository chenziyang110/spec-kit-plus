---
name: spx-deep-research
description: Focused pre-plan feasibility research for advanced coding models. Use when a planning-ready specification still lacks a credible implementation chain, external evidence, or a disposable proof.
---

# SPX Deep Research

Read `references/project-cognition.md`, using cognition intent `research`,
`references/research-contract.md`, and `references/consequence-gate.md` only on
its triggers.

Resolve the existing feature in paths-only mode. Start from the spec contract
and name the planning decision each research question must unlock. Use live
repository evidence first and current primary external sources when the answer
depends on an API, platform, standard, dependency, or recent behavior.

Run independent evidence lanes in parallel only when their questions and write
sets are truly separate. Build a disposable spike under the feature's
`research-spikes/` only when documentation and source cannot prove the
integration chain. Keep spikes out of production paths and record environment,
commands, output, limitations, and the claim they establish.

Write or update `deep-research.md` with concise findings, source attribution,
contradictions, confidence, rejected options, and a `Planning Handoff` that maps
each accepted result to architecture, task, verification, or risk implications.
Update referenced alignment/context evidence when required by the existing
feature package.

Do not implement production behavior. Continue to `$spx-plan` when feasibility
is proven or the remaining risk is explicitly accepted. Route requirement gaps
to `$spx-clarify`; otherwise stop with the smallest unresolved blocker.
