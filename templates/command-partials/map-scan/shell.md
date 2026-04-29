{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a complete project-relevant scan package for the current codebase.

## Context

- Primary inputs: the live repository tree, any existing handbook/project-map artifacts, passive learning files, and optional focus hints from `$ARGUMENTS`.
- This command owns scan-package outputs only; it must not write final atlas truth.
- The resulting scan package must let `sp-map-build` construct the handbook/project-map atlas without inventing scan scope.
