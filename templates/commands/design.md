---
description: Use when `specify-runtime design` must route one prompt to create, refine, or audit one bounded UI design change, optionally synthesizing supplied references, before UI work proceeds.
workflow_contract:
  when_to_use: A bounded UI change needs a direction, redesign audit, scoped token/component delta, platform rule, or readiness review before specification, planning, tasks, or implementation.
  primary_objective: Route the user's prompt to create, refine, or audit one `UD-*` workspace; treat synthesis as an input strategy; probe live visual capabilities; obtain approval of one image-primary concept when generation is available or one HTML-primary concept otherwise; export and register the immutable change contract; and never silently retarget existing consumers.
  primary_outputs: '`.specify/design/index.json`, `.specify/design/changes/<UD-ID>/design-change.md`, `.specify/design/changes/<UD-ID>/brief.md`, immutable `.specify/design/changes/<UD-ID>/previews/round-NN.<png|jpg|jpeg|webp|html>` visual rounds plus image prompts when applicable, `.specify/design/changes/<UD-ID>/design-contract.json`, and `.specify/design/changes/<UD-ID>/review.md`; no root design contract participates in selection or delivery, while stable rules enter `.specify/memory/project-rules.md` only through explicit promotion.'
  default_handoff: 'After user review, recommend exactly one next workflow owner under the consumer contract; when a persisted blocker prevents stage entry, name the target as recovery owner and carry the structured pending-recovery requirement without claiming that stage is already enterable.'
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
