# sp-discussion Design

## Summary

Add `sp-discussion` as a resumable pre-specification discussion workflow for ideas that are not mature enough for `sp-specify`.

The workflow acts from a combined senior technical expert and senior product manager perspective. It helps the user refine the product intent, discover missing requirements, evaluate implementation paths against the current project, and preserve the discussion as durable project artifacts. It does not automatically create a feature branch, generate a formal spec package, route to `sp-specify`, plan implementation, or edit source code.

The confirmed direction is a template-driven workflow with structured artifacts, not a new Python runtime state machine.

## Goals

- Preserve multi-turn requirement discussion so context survives compaction, session restarts, or later continuation.
- Guide users from rough ideas toward a complete requirements document that can later be supplied to `sp-specify`.
- Keep the discussion grounded in current project reality through project cognition and targeted read-only code evidence.
- Provide multiple strong technical implementation paths when the product idea can be implemented in meaningfully different ways.
- Keep handoff to `sp-specify` explicit and user-controlled.
- Install and document the workflow across supported integrations as an ordinary `sp-*` product surface.

## Non-Goals

- Do not automatically detect that a discussion is ready for `sp-specify`.
- Do not automatically run or invoke `sp-specify`.
- Do not create feature branches or feature directories.
- Do not write `spec.md`, `plan.md`, `tasks.md`, or implementation artifacts.
- Do not edit source code or tests.
- Do not build a debug-style Python state graph in this increment.
- Do not make `sp-discussion` Codex-only.

## User Experience

`sp-discussion` is used when the user has an idea, direction, feature concept, workflow improvement, or vague product request that needs discussion before formal specification.

The workflow starts by creating or resuming a discussion session under:

```text
.specify/discussions/<slug>/
```

Session selection is explicit enough to avoid merging unrelated ideas:

- A user-provided slug is normalized to lowercase ASCII, trims leading and trailing separators, replaces non-alphanumeric runs with `-`, collapses duplicate separators, and caps the display slug at a readable length.
- If a generated slug collides with an existing discussion, append a date or short numeric suffix rather than overwriting.
- Valid session statuses are `active`, `blocked`, `handoff-ready`, `completed`, and `abandoned`.
- Incomplete sessions are `active`, `blocked`, or `handoff-ready`.
- If the user specifies a slug, resume or create that slug according to the user's wording.
- If the user does not specify a slug and exactly one incomplete discussion exists, resume it.
- If multiple incomplete discussions exist, list the candidates with slug, status, summary, and `updated_at`, then ask the user to choose one or explicitly start a new discussion.
- Sort candidates by `updated_at` in `discussion-state.md`; fall back to the state file modification time only when `updated_at` is missing.
- A new discussion is created only when the user explicitly asks for a new discussion, supplies a new slug/topic, or chooses "new" after seeing multiple candidates.

The workflow asks one high-impact question at a time. It behaves like a senior product manager by clarifying goal, users, scenarios, scope, non-goals, acceptance criteria, permissions, exceptions, and success signals. It behaves like a senior technical expert by grounding the idea in the current project, identifying affected surfaces, and offering implementation paths when technical choices affect the requirement shape.

When the user explicitly requests handoff, for example by saying to feed the result into `sp-specify`, `sp-discussion` creates or refreshes `handoff-to-specify.md`. It should then tell the user to invoke the integration-appropriate `sp-specify` command with that handoff as input. It must not silently switch workflows.

## Core Artifacts

Each discussion session owns these files:

- `discussion-state.md`: Independent durable state source for the discussion session. It records `active_command: sp-discussion`, `state_surface: discussion-state`, status, slug, topic summary, current stage, next question, readiness notes, allowed writes, forbidden actions, authoritative files, `updated_at`, and the next command only when explicitly requested by the user.
- `discussion-log.md`: Decision-log style process history. It records key user inputs, important clarifying questions, user choices, rejected alternatives, recommendation rationale, and significant requirement changes. It is not a near-verbatim transcript.
- `requirements.md`: The current mature requirements document. It records goal, users, scenarios, scope, non-goals, functional requirements, acceptance criteria, dependencies, risks, and unresolved-question summary.
- `technical-options.md`: A technical options board. It records 2-3 viable implementation paths when relevant, including recommended option, impacted modules or files, trade-offs, risks, test strategy, migration considerations, rollback considerations, and reasons rejected options were not chosen.
- `project-context.md`: Project-grounding evidence. It records project cognition artifacts read, project-map or graph evidence, targeted read-only source evidence when needed, and clear separation between evidence and inference.
- `open-questions.md`: Remaining unresolved questions grouped by blocking level.
- `handoff-to-specify.md`: Created or refreshed only on explicit user request. It summarizes the confirmed requirements, chosen or open technical direction, key context, known constraints, and unresolved questions that `sp-specify` should preserve instead of rediscovering.

## State Model And Workflow Contract

The command frontmatter should describe:

- `when_to_use`: A rough idea or requirement needs a resumable product/technical discussion before formal specification.
- `primary_objective`: Build a durable discussion package that matures the idea into requirements and technical options suitable for explicit handoff to `sp-specify`.
- `primary_outputs`: The session artifacts under `.specify/discussions/<slug>/`.
- `default_handoff`: Stay in `sp-discussion` until the user explicitly asks to hand off. Only then produce `handoff-to-specify.md` and instruct the user to invoke `sp-specify`.

The state contract is intentionally independent from feature `workflow-state.md`:

- `discussion-state.md` is the source of truth for `sp-discussion`.
- `templates/workflow-state-template.md` remains feature-oriented and should not be extended with `sp-discussion` in this increment.
- `src/specify_cli/hooks/state_validation.py` should not add `sp-discussion` to `EXPECTED_WORKFLOW_STATE` in this increment.
- Shared workflow-state hooks do not validate `discussion-state.md` unless a later implementation explicitly adds a discussion serializer and hook boundary.
- A dedicated discussion-state template may be added, for example `templates/discussion-state-template.md`, and copied into generated projects as a discussion runtime artifact.

The discussion state records `phase_mode: discussion-only`, but that value belongs to `discussion-state.md`, not the feature `workflow-state.md` contract.

Suggested stages:

1. `session-intake`
2. `context-grounding`
3. `idea-framing`
4. `question-loop`
5. `technical-options`
6. `requirements-synthesis`
7. `handoff-on-request`

## Project Cognition And Code Reads

`sp-discussion` uses a staged cognition gate. Product framing may begin before project cognition is available, because rough ideas often need basic product shaping before the workflow can know whether existing-code facts matter.

Allowed before the cognition gate:

- session creation or resume
- user goal framing
- audience and scenario clarification
- scope, non-goal, and success-signal questions
- recording unknowns and assumptions

Forbidden before the cognition gate:

- project-specific technical recommendations
- affected module, file, or API claims
- implementation path recommendations
- source-code reads
- testing strategy claims tied to existing code

Before `context-grounding`, `technical-options`, affected-surface analysis, or source-grounded recommendations, the workflow uses the project cognition runtime:

1. Read `.specify/project-cognition/status.json`.
2. Read `.specify/project-cognition/slices/change.json`.
3. Read graph claims, conflicts, nodes, or edges only when ownership, adjacency, or implementation placement remains unclear.

Freshness handling follows the shared project cognition contract once the workflow reaches a stage that needs project-specific technical grounding:

- `missing`: stop and route the user to `sp-map-scan -> sp-map-build`.
- `stale`: stop and route the user to `sp-map-update`.
- `support_drift`: stop for support-surface cleanup without reflexively routing to `sp-map-update`.
- `partial_refresh`: stop and follow `recommended_next_action`.
- `possibly_stale`: inspect affected graph scope and route to localized refresh if coverage is not safe enough.

If the idea is clearly greenfield or does not depend on existing project structure, the workflow may stand down from the project cognition gate for that discussion stage. It must record the reason in `project-context.md` and avoid making existing-code placement claims.

Code reads are allowed only after cognition grounding and only when they help locate relevant implementation surfaces or evaluate technical options. Source inspection must stay read-only. The workflow must not run implementation loops, edit code, edit tests, or treat source reads as a substitute for missing cognition coverage.

## Technical Options Board

When the user idea depends on implementation strategy, `sp-discussion` must present multiple paths before locking the requirement direction. The default is 2-3 options:

- Minimal viable path: the smallest change that satisfies the confirmed requirement.
- Architecture-correct path: the path that best aligns with current boundaries and long-term maintainability.
- Expansion-ready path: the path that supports future variants, integrations, or scale when those are plausible and worth discussing.

Each option should include:

- product behavior enabled
- impacted modules, files, APIs, or workflows
- implementation complexity
- migration or compatibility concerns
- testing and verification strategy
- risks and failure modes
- rollback or de-scope path
- recommendation and rationale

The workflow recommends a path but does not silently decide for the user. User confirmation updates `requirements.md`, `technical-options.md`, and `discussion-log.md`.

## Relationship To sp-specify

`sp-discussion` is upstream of `sp-specify`, but it is not a replacement for it.

`sp-specify` remains the formal feature creation and planning-ready spec package workflow. It owns feature branch creation, `FEATURE_DIR`, `specify-draft.md`, `spec.md`, `alignment.md`, `context.md`, and `workflow-state.md`.

`sp-discussion` owns pre-spec discussion state under `.specify/discussions/<slug>/`. Its handoff file should be written so `sp-specify` can start from confirmed facts and avoid re-asking settled questions, while still running its own required brainstorming kernel and specification contract.

`sp-specify` must be updated to consume an explicit discussion handoff:

- If the user invokes `sp-specify` with a path to `.specify/discussions/<slug>/handoff-to-specify.md`, or pastes a discussion handoff block, `sp-specify` reads that handoff before parsing the feature request.
- The handoff becomes an authoritative input to the `sp-specify` brainstorming kernel, not a bypass around it.
- `sp-specify` records `entry_source: sp-discussion` and the handoff path in the generated feature artifacts.
- Confirmed requirements, confirmed non-goals, settled decisions, and selected technical direction seed the appropriate brainstorming truth artifacts and compiled spec artifacts.
- Open questions from the handoff become explicit unknowns with blocking level, resolver, and latest resolution phase instead of being lost or re-asked blindly.
- `references.md` or `context.md` should cite the discussion handoff and relevant project-context evidence.
- `sp-specify` may reopen a confirmed discussion conclusion only when repository evidence, constitution rules, or user correction contradicts it; the reopen reason must be recorded.

`handoff-to-specify.md` should have a stable structure:

- frontmatter with `source_command: sp-discussion`, `discussion_slug`, `status: handoff-ready`, `updated_at`, and `source_files`
- confirmed product goal and users
- confirmed scope and non-goals
- confirmed scenarios and acceptance signals
- selected or still-open technical direction
- project-context evidence and inference notes
- unresolved questions with blocking levels
- instructions for `sp-specify` about which decisions are settled and which must still be resolved

Automatic readiness detection is forbidden. Handoff is produced only when the user explicitly asks for it.

## Integration Surface

Implementation should update the normal workflow surfaces:

- Add `templates/commands/discussion.md`.
- Add `templates/command-partials/discussion/shell.md`.
- Add a discussion-state template or equivalent command-local bootstrap contract for `.specify/discussions/<slug>/discussion-state.md`.
- Do not update `templates/workflow-state-template.md` for `sp-discussion` in this increment.
- Do not add `sp-discussion` to `EXPECTED_WORKFLOW_STATE` unless the implementation also adds a serializer and validation contract for `discussion-state.md`.
- Update `templates/commands/specify.md` so explicit discussion handoff paths or pasted handoff blocks are read and mapped into `sp-specify` artifacts.
- Update workflow routing guidance so rough ideas, requirement exploration, and not-yet-ready feature concepts route to `sp-discussion`.
- Update project-map gate guidance to recognize `sp-discussion` as a brownfield discussion workflow that uses `slices/change.json`.
- Update `SKILL_DESCRIPTIONS` and add a CLI help entrypoint for `discussion`.
- Update README, quickstart, installation, and handbook surfaces where skill maps or workflow guidance list support/core workflows.
- Update integration tests so Markdown, TOML, and skills-based integrations generate `sp-discussion` correctly.
- Update hook/state validation tests only if `discussion-state.md` is validated by shared hooks in this increment.

The workflow should be available across supported integrations. Codex receives it as `.codex/skills/sp-discussion/SKILL.md`; other integrations receive their normal command or skill form.

## Testing Strategy

Tests should verify:

- The new command template has frontmatter and includes the discussion shell partial.
- Generated skills/commands include `sp-discussion` for skills, Markdown command, and TOML command integrations.
- Routing guidance mentions `sp-discussion` for rough ideas and explicitly preserves `sp-specify` for formal specification.
- Documentation skill maps include `discussion` in the correct group.
- Discussion state uses `.specify/discussions/<slug>/discussion-state.md`, not feature `workflow-state.md`.
- Shared workflow-state hooks do not validate `sp-discussion` unless a dedicated discussion serializer and hook contract is added.
- `sp-specify` reads explicit `handoff-to-specify.md` paths or pasted handoff blocks and maps them into its brainstorming/spec artifacts.
- The discussion command forbids source/test edits and automatic `sp-specify` handoff.
- The discussion command requires explicit user instruction before writing `handoff-to-specify.md`.
- The discussion command includes the senior technical expert plus senior product manager role language.
- The command allows product framing before the project cognition gate, but requires cognition grounding before technical options, affected-surface claims, or source reads.

## Risks And Mitigations

- Risk: `sp-discussion` duplicates `sp-specify` brainstorming.
  Mitigation: keep `sp-discussion` as pre-spec durable discussion only; `sp-specify` still owns formal spec compilation.

- Risk: agents automatically hand off when they infer readiness.
  Mitigation: make explicit user instruction a hard gate before `handoff-to-specify.md`.

- Risk: the workflow becomes vague chat instead of durable product work.
  Mitigation: require artifact updates before stopping, especially `discussion-state.md`, `discussion-log.md`, `requirements.md`, and `open-questions.md`.

- Risk: technical analysis becomes implementation work.
  Mitigation: allow only targeted read-only source inspection after project cognition grounding and forbid source/test edits.

- Risk: technical options are generic rather than project-specific.
  Mitigation: require project-context evidence and affected surface notes for any implementation recommendation.

- Risk: discussion state conflicts with feature workflow state validation.
  Mitigation: keep `discussion-state.md` independent in this increment and do not register it with feature `workflow-state.md` hooks.

- Risk: `sp-specify` ignores discussion handoff and repeats already-settled discovery.
  Mitigation: add an explicit handoff consumption contract to `sp-specify` and require handoff-derived facts, decisions, and unknowns to be persisted in generated spec artifacts.

## Acceptance Criteria

- Users can invoke `sp-discussion` across generated integrations.
- A discussion session can be resumed from `.specify/discussions/<slug>/` without relying on chat history.
- Multiple incomplete discussions without an explicit slug are listed for user selection instead of being merged by guesswork.
- The workflow preserves process decisions and a current requirements draft.
- The workflow can present multiple technical implementation paths grounded in project context.
- The workflow never automatically invokes or routes into `sp-specify`.
- `handoff-to-specify.md` is created only on explicit user request.
- `sp-specify` can consume an explicit discussion handoff and preserve settled decisions while still running its own specification contract.
- Documentation explains when to use `discussion` versus `specify`.
