{{spec-kit-include: ../common/user-input.md}}

## Objective

Execute a small, ad-hoc task through a lightweight planning and validation path without entering the full `specify -> plan -> tasks` workflow.

This command will skip the full feature-spec workflow while preserving lightweight planning and verification.

Use this for work that is too large for `sp-fast` but still too small or too well understood to justify a full spec flow: small bug fixes, small features, focused UX adjustments, template tweaks, or narrow CLI behavior changes.

Before the lightweight path starts substantive execution, make the agent's understanding visible in one initial full checkpoint so the user can confirm or correct the direction. Later material changes use the delta-only amendment contract instead of repeating that checkpoint.

## Context

- Primary inputs: the user's request, quick-task workspace state, CLI-selected Learning, the task-local project cognition query bundle with readiness and returned `minimal_live_reads`, and the smallest workflow-local state files needed for the touched area.
- The leader owns `STATUS.md`, lane selection, join points, validation, and final summary state.
- Quick mode is the resumable middle lane between `sp-fast` and the full specification workflow.
- Continue in quick only when any `CA-###` consequence obligations are bounded in `STATUS.md` with affected objects, lifecycle states, dependency impact, recovery/validation proof, coverage gaps, and stop-and-reopen conditions.
- Before substantive execution, present one Understanding Checkpoint using the fixed Quick Checkpoint card below. Keep the approval surface to user-owned outcome, visible result, scope, recommended approach, assumptions and risks, completion evidence, and reconfirmation triggers. Technical execution belongs to the agent. For applicable UI work, append the independent UI Confirmation card and ask for one combined confirmation; record both decisions in quick `STATUS.md`.

## Quick Checkpoint Card

{{spec-kit-include: checkpoint-card.md}}
