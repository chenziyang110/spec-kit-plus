{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a complete project-relevant scan package for the current codebase.

## Context

- Primary inputs: git-baseline diff data when available, live repository surfaces, existing atlas/reference artifacts, passive learning files, and optional focus hints from `$ARGUMENTS`.
- This command owns scan-package outputs only; it must not write final atlas truth.
- Derived atlas/workbench artifacts such as `PROJECT-HANDBOOK.md` and `.specify/project-map/**` may be read as reference inputs but must not become scan targets.
- The resulting scan package must let `sp-map-build` construct the handbook/project-map atlas from live-surface evidence without inventing scan scope.
- Maintain `.specify/project-map/map-state.md` as the resumable scan/build state surface.
