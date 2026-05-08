{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a complete graph-native evidence baseline for the current codebase.

## Context

- Primary inputs: git-baseline diff data when available, live repository surfaces, existing reference artifacts, passive learning files, and optional focus hints from `$ARGUMENTS`.
- This command owns graph-native evidence-baseline outputs only; it must not write final cognition truth.
- Derived atlas/workbench artifacts such as `PROJECT-HANDBOOK.md` and `.specify/project-map/**` may be read as reference inputs but must not become scan targets.
- The resulting evidence baseline must let `sp-map-build` reconstruct the project cognition graph from live-surface evidence without inventing scan scope.
- Maintain `.specify/project-cognition/status.json` as the baseline state surface for graph-native cognition readiness.
