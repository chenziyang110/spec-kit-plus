---
description: Use when `specify-runtime design` must route one prompt to create, refine, or audit the root DESIGN.md design-system contract, optionally synthesizing supplied references, before UI work proceeds.
workflow_contract:
  when_to_use: A project needs product-wide interface style, design-system tokens, platform UI rules, or design readiness review before specification, planning, tasks, or implementation.
  primary_objective: Route the user's prompt to create, refine, or audit; treat synthesis as an input strategy; obtain approval of an inspectable HTML direction when design truth changes; and use `specify-runtime design` to maintain the root `DESIGN.md` without implementing application UI.
  primary_outputs: '`DESIGN.md`, `.specify/design/design-state.md`, `.specify/design/design-brief.md`, immutable `.specify/design/previews/round-NN.html` review boards, `.specify/design/references.md`, `.specify/design/options.md`, and `.specify/design/review.md`; stable design rules in `.specify/memory/project-rules.md` only when they should become shared project defaults.'
  default_handoff: 'After user review, recommend exactly one next command under the consumer contract: `/sp.discussion`, `/sp.specify`, `/sp.quick`, or the still-valid originally blocked workflow.'
---

{{spec-kit-include: ../command-partials/design/shell.md}}

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.
[AGENT] At entry or resume, read `references/task-router.md`. Before closeout or approval adoption, read `references/consumer-contract.md`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying shared semantic contracts.

- [semantic work contract](references/semantic-work-contract.md)
- [task router](references/task-router.md)
- [consumer contract](references/consumer-contract.md)

{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}
