{{spec-kit-include: ../common/user-input.md}}

## Objective

Execute a small, ad-hoc task through a lightweight planning and validation path without entering the full `specify -> plan -> tasks` workflow.

This command will skip the full feature-spec workflow while preserving lightweight planning and verification.

Use this for work that is too large for `sp-fast` but still too small or too well understood to justify a full spec flow: small bug fixes, small features, focused UX adjustments, template tweaks, or narrow CLI behavior changes.

Before the lightweight path starts substantive execution, make the agent's understanding visible once so the user can confirm or correct the direction.

## Context

- Primary inputs: the user's request, quick-task workspace state, passive learning files, the task-local project cognition query bundle with readiness and returned `minimal_live_reads`, and the smallest workflow-local state files needed for the touched area.
- The leader owns `STATUS.md`, lane selection, join points, validation, and final summary state.
- Quick mode is the resumable middle lane between `sp-fast` and the full specification workflow.
- Continue in quick only when any `CA-###` consequence obligations are bounded in `STATUS.md` with affected objects, lifecycle states, dependency impact, recovery/validation proof, coverage gaps, and stop-and-reopen conditions.
- Before substantive execution, present one Understanding Checkpoint covering the understood problem, planned outcome, scope boundary, execution approach, and validation evidence; wait for user confirmation and record it in quick `STATUS.md`.
