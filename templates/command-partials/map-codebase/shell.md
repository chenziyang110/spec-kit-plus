{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate or refresh the canonical handbook/project-map navigation system for the current codebase.

## Context

- Primary inputs: the live codebase, any existing handbook/project-map artifacts, passive learning files, and optional focus hints from `$ARGUMENTS`.
- This command owns the canonical navigation outputs; it must not create an alternate mapping tree.
- The resulting map should make later `sp-*` workflows safer by replacing guesswork with current repository evidence.
