---
description: Use when a project needs a DESIGN.md design-system contract, design-system synthesis, UI style refinement, or design readiness audit before UI work proceeds.
workflow_contract:
  when_to_use: A project needs product-wide interface style, design-system tokens, platform UI rules, or design readiness review before specification, planning, tasks, or implementation.
  primary_objective: Produce, refine, synthesize, or audit the root `DESIGN.md` design-system contract without implementing UI code.
  primary_outputs: '`DESIGN.md`, `.specify/design/design-state.md`, `.specify/design/references.md`, `.specify/design/options.md`, and `.specify/design/review.md`; stable design rules in `.specify/memory/project-rules.md` only when they should become shared project defaults.'
  default_handoff: 'After user review, recommend exactly one next command: `/sp.discussion`, `/sp.specify`, `/sp.plan`, or the originally blocked workflow.'
---

{{spec-kit-include: ../command-partials/design/shell.md}}

{{spec-kit-include: ../command-partials/common/semantic-work-contract.md}}

{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}
