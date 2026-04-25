{{spec-kit-include: ../common/user-input.md}}

## Objective

Execute a small, ad-hoc task through a lightweight planning and validation path without entering the full `specify -> plan -> tasks` workflow.

This command will skip the full feature-spec workflow while preserving lightweight planning and verification.

Use this for work that is too large for `sp-fast` but still too small or too well understood to justify a full spec flow: small bug fixes, small features, focused UX adjustments, template tweaks, or narrow CLI behavior changes.

## Context

- Primary inputs: the user's request, quick-task workspace state, passive learning files, and the handbook/project-map set.
- The leader owns `STATUS.md`, lane selection, join points, validation, and final summary state.
- Quick mode is the resumable middle lane between `sp-fast` and the full specification workflow.
