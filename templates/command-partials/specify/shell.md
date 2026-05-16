{{spec-kit-include: ../common/user-input.md}}

## Objective

Turn arbitrary incoming work into a planning-ready specification package by
first locking a deterministic brainstorming truth layer that is grounded in
repository reality and explicit enough to hand off into implementation
planning.

## Context

- Primary inputs: the user's request, the current repository state, passive learning files, and the task-local project cognition query bundle with readiness and returned `minimal_live_reads`.
- Brainstorming truth lives under the active `FEATURE_DIR/brainstorming/`, especially `facts.json`, `route.json`, `intent.json`, `complexity.json`, and `handoff-to-specify.json`.
- Compiled working state lives under the active `FEATURE_DIR`, especially `spec.md`, `alignment.md`, `context.md`, `references.md`, and `workflow-state.md`.
- This command is specification-only. It is not permission to implement code.

## Process

- Establish or resume the active feature workspace, workflow-state file, and brainstorming truth files.
- Load just enough repository context to understand ownership, constraints, and adjacent surfaces.
- Progress through `facts-lock`, `route-lock`, `intent-lock`, and `complexity-lock`, asking deterministic questions only for unresolved fields or rule predicates.
- Clarify planning-critical ambiguity and decompose the request into capabilities before compiling the locked truth layer into the specification artifact set.
- Compile the locked truth into the specification artifact set.
- Preserve triggered senior consequence analysis as `CA-###` obligations with affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and stop-and-reopen conditions.
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
- Report what was locked, what remains open, and the recommended next command.
- Do not imply planning readiness when planning-critical ambiguity still remains.

## Guardrails

- Do not edit source code, tests, or implementation files from `sp-specify`.
- Do not skip planning-critical clarification just because the request sounds simple.
- Do not treat conversation memory as a valid handoff surface; persisted truth files are the handoff source.
- Do not treat this summary block as the workflow itself; the detailed contract below remains authoritative.
