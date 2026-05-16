{{spec-kit-include: ../common/user-input.md}}

## Objective

Turn arbitrary incoming work into a planning-ready specification package by
first locking a deterministic brainstorming truth layer that is grounded in
repository reality and explicit enough to hand off into implementation
planning.

## Context

- Primary inputs: the user's request, the current repository state, passive learning files, and the task-local project cognition query bundle with readiness and returned `minimal_live_reads`.
- Brainstorming truth lives under the active `FEATURE_DIR/brainstorming/`, especially `journal.ndjson`, `stage-manifest.json`, `domains.json`, `evidence-index.json`, `facts.json`, `route.json`, `intent.json`, `complexity.json`, and `handoff-to-specify.json`.
- Compiled working state lives under the active `FEATURE_DIR`, especially `spec.md`, `alignment.md`, `context.md`, `references.md`, and `workflow-state.md`.
- This command is specification-only. It is not permission to implement code.

## Process

- Establish or resume the active feature workspace, workflow-state file, `BRAINSTORMING_JOURNAL_FILE`, `BRAINSTORMING_STAGE_MANIFEST_FILE`, and brainstorming truth files.
- Create or resume `BRAINSTORMING_JOURNAL_FILE` and `BRAINSTORMING_STAGE_MANIFEST_FILE` immediately after `FEATURE_DIR` is known, before relying on workflow-state, draft Markdown, or chat history.
- Markdown is not a trusted recovery source; JSON stage artifacts plus `brainstorming/journal.ndjson` are the trusted recovery and compile contract.
- On resume, replay `brainstorming/journal.ndjson`, validate `brainstorming/stage-manifest.json`, and regenerate stale stage artifacts before continuing.
- If journal replay and a compiled stage artifact disagree, journal replay wins and the stage artifact must be regenerated before continuing.
- Load just enough repository context to understand ownership, constraints, and adjacent surfaces.
- Progress through `intake`, `evidence-intake`, `facts-lock`, `route-lock`, `intent-lock`, `complexity-lock`, `domain-clarification`, `consequence-risk`, `specify-compile`, and `release-decision`, asking deterministic questions only for unresolved fields or rule predicates.
- Append journal events for user input, evidence, questions, answers, decisions, reopens, artifact compilation, and checkpoints.
- Write `checkpoint_written` before compaction-risk transitions and treat `checkpoint_written.event_id` as `last_checkpoint_id`.
- Clarify planning-critical ambiguity and decompose the request into capabilities before compiling the locked truth layer into the specification artifact set.
- Validate stage artifacts against `brainstorming/stage-manifest.json`, then compile the final specification artifact set from structured stage state plus cited journal and evidence events.
- Preserve triggered senior consequence analysis as `CA-###` obligations with affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and stop-and-reopen conditions.
- Decide whether the package is ready for `/sp-plan` or still needs another clarification/enhancement pass.

## Output Contract

- Write or update the mandatory brainstorming truth artifacts:
  `brainstorming/journal.ndjson`, `brainstorming/stage-manifest.json`,
  `brainstorming/domains.json`, `brainstorming/evidence-index.json`,
  `brainstorming/facts.json`, `brainstorming/route.json`,
  `brainstorming/intent.json`, `brainstorming/complexity.json`, and
  `brainstorming/handoff-to-specify.json`.
- Write or update `spec.md`, `alignment.md`, `context.md`, and `references.md`
  when needed.
- Treat structured handoff truth as authoritative when it exists; do not rely on
  chat-only conclusions.
- Preserve `compiled_from`, `last_event_id`, and `last_checkpoint_id` metadata so the final package can be reconstructed from JSON stage artifacts and the journal.
- Report what was locked, what remains open, and the recommended next command.
- Do not imply planning readiness when planning-critical ambiguity still remains.

## Guardrails

- Do not edit source code, tests, or implementation files from `sp-specify`.
- Do not skip planning-critical clarification just because the request sounds simple.
- Do not treat conversation memory or Markdown as a valid recovery surface; persisted JSON truth files and `brainstorming/journal.ndjson` are the handoff source.
- Do not treat this summary block as the workflow itself; the detailed contract below remains authoritative.
