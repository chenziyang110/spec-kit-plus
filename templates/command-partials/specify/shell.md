{{spec-kit-include: ../common/user-input.md}}

## Objective

Turn the incoming request into a planning-ready specification package that is grounded in repository reality and explicit enough to hand off into implementation planning.

## Context

- Primary inputs: the user's request, the current repository state, passive learning files, and the handbook/project-map navigation system.
- Working state lives under the active `FEATURE_DIR`, especially `spec.md`, `alignment.md`, `context.md`, `references.md`, and `workflow-state.md`.
- This command is specification-only. It is not permission to implement code.

## Process

- Establish or resume the active feature workspace and workflow-state file.
- Load just enough repository context to understand ownership, constraints, and adjacent surfaces.
- Clarify planning-critical ambiguity, decompose the request into capabilities, and write the specification artifact set.
- Decide whether the package is ready for `/sp-plan` or still needs another clarification/enhancement pass.

## Output Contract

- Write or update `spec.md`, `alignment.md`, `context.md`, and `references.md` when needed.
- Report what was decided, what remains open, and the recommended next command.
- Do not imply planning readiness when planning-critical ambiguity still remains.

## Guardrails

- Do not edit source code, tests, or implementation files from `sp-specify`.
- Do not skip planning-critical clarification just because the request sounds simple.
- Do not treat this summary block as the workflow itself; the detailed contract below remains authoritative.
