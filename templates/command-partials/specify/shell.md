{{spec-kit-include: ../common/user-input.md}}

## Objective

Turn arbitrary incoming work into a planning-ready specification package by
first locking a deterministic brainstorming truth layer that is grounded in
repository reality and explicit enough to hand off into implementation
planning.

## Context

- Primary inputs: the user's request, the current repository state, passive learning files, and the project cognition runtime (`.specify/project-cognition/status.json`, required slices, graph artifacts, and targeted live evidence).
- Working state lives under the active `FEATURE_DIR`, especially the
  `brainstorming/` truth artifacts plus `spec.md`, `alignment.md`, `context.md`,
  `references.md`, and `workflow-state.md`.
- This command is specification-only. It is not permission to implement code.

## Process

- Establish or resume the active feature workspace, workflow-state file, and
  brainstorming truth artifacts.
- Load just enough repository context to understand ownership, constraints, and adjacent surfaces.
- Lock facts, route, intent, and complexity before compiling the specification
  artifact set.
- Decide whether the package is ready for `/sp-plan` or still needs another clarification/enhancement pass.

## Output Contract

- Write or update the mandatory brainstorming truth artifacts:
  `brainstorming/facts.json`, `brainstorming/route.json`,
  `brainstorming/intent.json`, `brainstorming/complexity.json`, and
  `brainstorming/handoff-to-specify.json`.
- Write or update `spec.md`, `alignment.md`, `context.md`, and `references.md`
  when needed.
- Treat structured handoff truth as authoritative when it exists; do not rely on
  chat-only conclusions.
- Report what was decided, what remains open, and the recommended next command.
- Do not imply planning readiness when planning-critical ambiguity still remains.

## Guardrails

- Do not edit source code, tests, or implementation files from `sp-specify`.
- Do not skip planning-critical clarification just because the request sounds simple.
- Do not treat conversation memory as a valid handoff surface.
- Do not treat this summary block as the workflow itself; the detailed contract below remains authoritative.
