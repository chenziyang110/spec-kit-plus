{{spec-kit-include: ../common/user-input.md}}

{{spec-kit-include: ../common/context-sufficiency-choice.md}}

## Objective

Execute a non-trivial task through a tracked direct-delivery path without first entering the formal `specify -> plan -> tasks` workflow.

This command skips the formal feature-spec workflow while scaling task-local planning, decomposition, consequence analysis, and verification to the work.

Use this whenever the requested outcome is clear enough for direct implementation but needs resumable state: focused fixes and tweaks, larger features, cross-cutting changes, multi-capability delivery, architecture or migration work, compatibility or rollout changes, and acceptance-heavy implementation are all valid quick tasks.

First understand the request and inspect bounded current-state evidence. Before
the full Quick branch starts implementation, stage one runtime-owned Decision
Checkpoint that explains the findings, proposed change, impact and verification
so the user can confirm concrete product decisions once. Show the
Delivery Map for awareness only. Later material product changes use the
delta-only amendment contract; execution-only rearranges never re-confirm.

## Context

- Primary inputs: the user's request, quick-task workspace state, CLI-selected Learning, the task-local project cognition query bundle with readiness and returned `minimal_live_reads`, and the smallest workflow-local state files needed for the touched area.
- Before confirmation, use targeted existing source/log/test reads, safe bounded checks and read-only evidence workers to establish the current situation. For greenfield work, state the checked absence of an implementation and the available requirements; keep unknowns explicit. Product/test/harness writes, persistent instrumentation and implementation dispatch require runtime-confirmed or validated inherited decisions plus the normal Q-item and execution guards.
- The leader owns `STATUS.md`, lane selection, join points, validation, and final summary state.
- Quick mode is the resumable direct-delivery lane after `sp-fast`; it is an alternative to a formal specification workflow, not a size band below it.
- Keep every `CA-###` consequence obligation traceable in `STATUS.md` or a referenced task-local planning artifact with affected objects, lifecycle states, dependency impact, recovery/validation proof, coverage gaps, and stop-and-reopen conditions. Broad consequence scope increases planning and validation depth inside quick; it does not require `sp-specify`.
- Before substantive execution in the full Quick branch, stage `quick-confirmation-v1` through
  `specify-runtime quick checkpoint-stage` and present the runtime Decision
  Checkpoint; show the Delivery Map after confirmation. Keep the approval surface to current findings and their basis, user-owned outcome,
  visible result, scope, ordered work items and dependencies, work-item
  acceptance, recommended approach, assumptions and risks, overall completion
  evidence, and reconfirmation triggers. Delivery Map, waves, subagents, file
  splits, and test order are agent-owned and never require approval. For
  discussion handoffs with no semantic delta, inherit the digest and skip
  re-confirmation. For applicable UI work, keep UI Confirmation independent in
  state, fold its readable `界面方向` section into the same human card, and ask
  once on staged non-inherited checkpoints.
- Any UI-bearing scope must read `references/ui-design-intelligence.md`
  before UI decisions, UI confirmation, or user-visible output generation.
  Registered design truth remains the highest authority; use the selected
  `.specify/design/changes/<UD-ID>/design-change.md`, its immutable
  preview/approval/handoff artifacts, and the bound UI contract ahead of
  inferred style or implementation instinct.

## Quick Checkpoint Card

Before `specify-runtime quick checkpoint-stage`, before presenting the runtime
Decision Checkpoint / Delivery Map, and before recording or inheriting user
confirmation, read `references/intake-and-checkpoint.md`. That reference owns
the Quick Checkpoint Card contract, its confirmation modes, and the user-visible
checkpoint surface.
