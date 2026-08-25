{{spec-kit-include: ../common/user-input.md}}

{{spec-kit-include: ../common/context-sufficiency-choice.md}}

{{spec-kit-include: ../common/design-intelligence.md}}

## Objective

Execute a non-trivial task through a tracked direct-delivery path without first entering the formal `specify -> plan -> tasks` workflow.

This command skips the formal feature-spec workflow while scaling task-local planning, decomposition, consequence analysis, and verification to the work.

Use this whenever the requested outcome is clear enough for direct implementation but needs resumable state: focused fixes and tweaks, larger features, cross-cutting changes, multi-capability delivery, architecture or migration work, compatibility or rollout changes, and acceptance-heavy implementation are all valid quick tasks.

Before the full Quick branch starts substantive execution, stage one runtime-owned
Decision Checkpoint so the user can confirm product decisions once. Show the
Delivery Map for awareness only. Later material product changes use the
delta-only amendment contract; execution-only rearranges never re-confirm.

## Context

- Primary inputs: the user's request, quick-task workspace state, CLI-selected Learning, the task-local project cognition query bundle with readiness and returned `minimal_live_reads`, and the smallest workflow-local state files needed for the touched area.
- The leader owns `STATUS.md`, lane selection, join points, validation, and final summary state.
- Quick mode is the resumable direct-delivery lane after `sp-fast`; it is an alternative to a formal specification workflow, not a size band below it.
- Keep every `CA-###` consequence obligation traceable in `STATUS.md` or a referenced task-local planning artifact with affected objects, lifecycle states, dependency impact, recovery/validation proof, coverage gaps, and stop-and-reopen conditions. Broad consequence scope increases planning and validation depth inside quick; it does not require `sp-specify`.
- Before substantive execution in the full Quick branch, stage `quick-confirmation-v1` through
  `specify-runtime quick checkpoint-stage` and present the runtime Decision
  Checkpoint plus Delivery Map. Keep the approval surface to user-owned outcome,
  visible result, scope, ordered work items and dependencies, work-item
  acceptance, recommended approach, assumptions and risks, overall completion
  evidence, and reconfirmation triggers. Delivery Map, waves, subagents, file
  splits, and test order are agent-owned and never require approval. For
  discussion handoffs with no semantic delta, inherit the digest and skip
  re-confirmation. For applicable UI work, keep UI Confirmation independent in
  state, fold its readable `界面方向` section into the same human card, and ask
  once on staged non-inherited checkpoints.
- **UI change? UI Audit then design-before-code.** When the request changes
  user-visible UI, run **UI Audit** first (hierarchy weak? spacing inconsistent?
  missing pointer/keyboard/touch feedback, empty/populated/partial/error/
  permission/offline behavior, retry/undo/recovery, or stretch/overflow rules?
  generic card layout? DNA drift?), then the
  **Quick Design Loop**: (1) audit issues list, (2) analyze current UI and design
  sources / system model, (3) identify the design issue, (4) propose before→after
  against DNA/dials/anti-slop, (5) implement the smallest coherent change,
  (6) visual review at real entry points (capture → inspect → fix → recapture).
  Preserve the confirmed `interaction_matrix`, `editing_matrix`, `data_state_matrix`, component
  `interaction_modes` / `data_scenarios`, and responsive `stretch_behavior` /
  `overflow_behavior`. Preserve event sequence, immediate feedback, focus,
  repeat, cancellation, and pending behavior. Exercise risk-based input × data × size combinations,
  including active resize, rather than only a populated pointer happy path. Do
  not jump straight from request to CSS/production edits for UI work.

## Quick Checkpoint Card

{{spec-kit-include: checkpoint-card.md}}

## Professional UI Contract Continuity

Quick preserves the confirmed affected subset of `surface_catalog`,
`scenario_matrix`, `interaction_matrix`, `editing_matrix`, `data_state_matrix`,
`accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, and `usability_validation`, including
component governance and iconography. It may not silently downgrade approved
truth. Verify risk-based or pairwise scenarios, not an unbounded Cartesian
product, and leave required target-user human review explicit.
