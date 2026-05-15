{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a complete graph-native evidence baseline for the current codebase.

## Context

- Primary inputs: git-baseline diff data when available, live repository surfaces, existing reference artifacts, passive learning files as read-only workflow guidance, not scan evidence, and optional focus hints from `$ARGUMENTS`.
- This command owns graph-native evidence-baseline outputs only; it must not write final cognition truth.
- Legacy atlas artifacts such as `PROJECT-HANDBOOK.md` may be read only when explicitly relevant to migration or export parity; they must not become scan targets.
- `.specify/**` is workflow/runtime state, not project graph evidence; `.specify/**` paths may be read only for command operation or validation and must not become scan targets or graph paths.
- The resulting evidence baseline must let `sp-map-build` reconstruct the project cognition graph from live-surface evidence without inventing scan scope.
- Maintain `.specify/project-cognition/status.json` as the baseline state surface for graph-native cognition readiness.
