{{spec-kit-include: ../common/user-input.md}}

## Objective

Execute a non-trivial task through a tracked direct-delivery path without first entering the formal `specify -> plan -> tasks` workflow.

This command skips the formal feature-spec workflow while scaling task-local planning, decomposition, consequence analysis, and verification to the work.

Use this whenever the requested outcome is clear enough for direct implementation but needs resumable state: focused fixes and tweaks, larger features, cross-cutting changes, multi-capability delivery, architecture or migration work, compatibility or rollout changes, and acceptance-heavy implementation are all valid quick tasks.

Before the lightweight path starts substantive execution, make the agent's understanding visible in one initial full checkpoint so the user can confirm or correct the direction. Later material changes use the delta-only amendment contract instead of repeating that checkpoint.

## Context

- Primary inputs: the user's request, quick-task workspace state, CLI-selected Learning, the task-local project cognition query bundle with readiness and returned `minimal_live_reads`, and the smallest workflow-local state files needed for the touched area.
- The leader owns `STATUS.md`, lane selection, join points, validation, and final summary state.
- Quick mode is the resumable direct-delivery lane after `sp-fast`; it is an alternative to a formal specification workflow, not a size band below it.
- Keep every `CA-###` consequence obligation traceable in `STATUS.md` or a referenced task-local planning artifact with affected objects, lifecycle states, dependency impact, recovery/validation proof, coverage gaps, and stop-and-reopen conditions. Broad consequence scope increases planning and validation depth inside quick; it does not require `sp-specify`.
- Before substantive execution, present one Understanding Checkpoint using the fixed Quick Checkpoint card below. Keep the approval surface to the user-owned overall outcome, visible result, scope, ordered work items and their dependencies, work-item acceptance, recommended approach, assumptions and risks, overall completion evidence, and reconfirmation triggers. The same table handles one work item or a large ordered set. Technical implementation sequencing belongs to the agent. For applicable UI work, append the independent UI Confirmation card and ask for one combined confirmation; persist both decisions through the registered quick/status artifact CLI, never by editing `STATUS.md` directly.

## Quick Checkpoint Card

{{spec-kit-include: checkpoint-card.md}}
