# sp-discussion Context Boundary And Handoff Quality Design

## Summary

Strengthen `sp-discussion` so it becomes a reliable pre-specification
requirement and context-boundary workflow, not a freeform discussion that can
drift into unsupported technical claims.

The design adds a hard **Context Boundary Gate** before project-specific
technical options, affected-file claims, or handoff generation. When the user's
request implies a target project, reference project, current-repository role,
external system, existing module, generated artifact source, or implementation
path that is unclear, `sp-discussion` must stop technicalization and ask
boundary questions until the execution target and evidence sources are explicit.

The design also upgrades the discussion handoff from a summary into a
reviewed, structured handoff contract. A handoff is not ready until it has a
concrete goal, target path context, evidence provenance, blocking unknowns,
Must-Preserve items, self-review status, and explicit user confirmation.
Downstream workflows then defensively reject bad handoffs instead of trying to
repair or reinterpret them.

This is a workflow contract and generated-template design. The first
implementation should update templates, passive skills, docs, and template
tests. A heavier runtime JSON schema validator is a follow-up, not part of the
first increment.

## Problem

`sp-discussion` already has useful structure: resumable discussion artifacts,
handoff assessment, split candidate handoffs, Must-Preserve Ledger fields, and
downstream discussion intake in `sp-specify`.

The remaining failure mode is more fundamental: the workflow does not lock the
context boundary early enough. A discussion can mention "add this capability to
another project" while the active workspace and project cognition belong to the
current repository. If the target project path is unknown, later stages cannot
honestly plan implementation. The current system can still drift into one of
these bad states:

- treating the current repository as the implementation target when it is only
  a reference source
- using the current project's cognition to prove facts about another project
- producing a handoff that does not say what exact goal is being handed off
- generating `specify -> plan -> tasks` artifacts that never name the target
  project root or target-relative paths
- blocking late in `sp-plan` with a project cognition error that should have
  been caught during discussion intake
- summarizing the discussion without preserving the user's actual objective,
  path, route, non-goals, and unresolved blockers

This specific cross-project case is only one example. The same class of bug
appears whenever a request depends on an unstated boundary: target project,
reference source, external system, existing module, generated output location,
integration owner, source-of-truth document, or evidence source.

## Reference: Superpowers Brainstorming

The design borrows the working shape from `superpowers:brainstorming`:

- inspect project context before detailed design
- ask one high-impact question at a time
- do not proceed from discussion into implementation behavior
- propose 2-3 approaches with trade-offs before locking direction
- present the design and get user approval
- write a durable design/spec artifact
- self-review for placeholders, contradictions, scope, and ambiguity
- require user review before transitioning to implementation planning

For spec-kit-plus, this maps to `sp-discussion` as:

- context boundary before source-grounded technical claims
- project/product question loop before technical options
- technical options before handoff selection
- handoff self-review before handoff readiness
- user handoff review before `sp-specify` is recommended
- defensive downstream intake in `sp-specify`, `sp-plan`, and `sp-tasks`

## Goals

- Prevent `sp-discussion` from drifting into project-specific technical claims
  when the execution target, reference source, or evidence boundary is unclear.
- Make cross-project and reference-implementation requests first-class rather
  than accidental edge cases.
- Require the target project path as soon as a request clearly says work must
  be performed in another project.
- Ensure handoff files state the goal, target, path expectations, evidence
  provenance, unknowns, non-goals, and downstream instructions clearly enough
  for `sp-specify -> sp-plan -> sp-tasks`.
- Require handoff self-review and user review before a discussion can become
  `handoff-ready`.
- Make downstream workflows reject incomplete or unconfirmed handoffs instead
  of silently interpreting them.
- Preserve existing split-mode and Must-Preserve Ledger behavior while adding
  boundary and quality gates.
- Keep the first increment integration-neutral and template-testable.

## Non-Goals

- Do not implement a full runtime JSON schema validator in the first increment.
- Do not change the mainline workflow names or the `specify -> plan -> tasks`
  progression.
- Do not make `sp-discussion` automatically invoke `sp-specify`.
- Do not let `sp-discussion` create feature branches, feature directories,
  `spec.md`, `plan.md`, `tasks.md`, source edits, or test edits.
- Do not require project cognition for clearly greenfield product framing.
- Do not make the current repository's project cognition authoritative for an
  external target project.
- Do not make this behavior Codex-only.

## Core Model

The workflow tracks three separate concepts:

1. **Current project**: the repository where the agent is currently running.
2. **Implementation target**: the project, root path, module, or external
   surface where the requested change will actually be planned and implemented.
3. **Reference source**: any project, module, document, UI, code path, or
   external artifact used for inspiration, comparison, or transfer evidence.

The current project may be the implementation target, a reference source, both,
or neither. The workflow must not infer that relationship silently.

The handoff must preserve the relationship explicitly so downstream workflows
know whether they should plan against the active repository, another local
repository, a supplied external source, or a target that is still blocked
because no path or access was provided.

## Context Boundary Gate

The Context Boundary Gate triggers semantically, not only by keyword. It should
trigger when the user request implies any unclear boundary involving:

- execution target project or target root
- current repository role
- reference project or source artifact
- external system or service boundary
- existing module, package, adapter, generated artifact, or workflow surface
- path where work must land
- source of truth for an existing behavior or module
- evidence source needed before making technical claims

When the gate triggers and the relevant boundary is not locked, `sp-discussion`
may continue only with boundary clarification and product framing. It must not:

- provide project-specific technical recommendations
- name affected files, modules, APIs, or tests as facts
- claim a target implementation path
- write handoff files
- mark the discussion `handoff-ready`
- tell the user to proceed to `sp-specify`

For the cross-project case, the default rule is strict:

- If the user asks to add or transfer functionality into another project,
  `sp-discussion` must lock the target project root immediately.
- If the target root is unknown, the workflow may continue discussing product
  goal, scope, non-goals, and success signals, but cannot enter technical
  options or handoff readiness.
- The handoff must say whether the active repository is the implementation
  target, a reference source, or unrelated to implementation.

## Discussion Flow

`sp-discussion` should use this staged flow:

1. `context-intake`
   - Identify current project root, user goal, current project role, target
     project, reference sources, external systems, path hints, and evidence
     sources.
   - Run the Context Boundary Gate.
   - If triggered and unresolved, ask one boundary question at a time.

2. `product-framing`
   - Clarify goal, users, scenario, scope, non-goals, success signals,
     constraints, and blocked unknowns.
   - Product framing may continue when target paths are missing, but it must
     not make target-specific implementation claims.

3. `context-grounding`
   - Enter only after relevant boundaries are locked.
   - Use current project cognition only for current project facts.
   - For an external target, confirm target root first. If it contains
     `.specify/`, inspect target project cognition readiness; if it lacks fresh
     cognition, treat that as target-project evidence status, not a defect in
     the current repository.
   - Treat reference project cognition as supplemental-only and fresh-only.

4. `question-loop`
   - Ask exactly one high-impact question per turn unless the remaining topic is
     local and low risk.
   - Track hard and soft unknowns in `open-questions.md`.

5. `technical-options`
   - Present 2-3 implementation paths when strategy affects requirements.
   - Include recommendation, trade-offs, risks, verification approach,
     rollback or de-scope path, and required evidence.
   - Do not present technical options when the Context Boundary Gate is still
     unresolved.

6. `handoff-assessment`
   - Decide whether the discussion is one bounded feature, split-required, or
     still needs discussion.
   - Preserve existing split-plan behavior for broad directions.

7. `handoff-draft`
   - Write Markdown and JSON only after explicit user request and a bounded
     handoff or selected candidate exists.
   - The handoff is a contract, not a prose summary.

8. `handoff-self-review`
   - Check placeholders, contradictions, missing goal, missing target path,
     unresolved hard unknowns, weak evidence provenance, Markdown/JSON drift,
     and Must-Preserve coverage.

9. `handoff-user-review`
   - Ask the user to review the handoff.
   - User confirmation is required before `handoff-ready`.

10. `handoff-ready`
   - Only after user confirmation. Then tell the user how to invoke
     integration-appropriate `sp-specify` with the handoff path.

## Handoff Contract

`handoff-to-specify.md` remains the user-readable artifact.
`handoff-to-specify.json` remains the machine-readable companion. Both forms
must agree on shared identity and status fields.

The handoff should include at least:

- `handoff_goal`
  - One concrete statement of what is being handed to `sp-specify`.
  - Generic language such as "continue the discussion result" is invalid.

- `context_boundary`
  - `current_project_root`
  - `current_project_role`: `implementation_target`, `reference_source`,
    `template_source`, `discussion_host`, `unrelated`, or a clearly explained
    equivalent
  - `target_project_root`
  - `target_project_role`
  - `reference_projects`
  - `external_systems`
  - `path_status`
  - `boundary_confidence`
  - `boundary_unknowns`

- `implementation_target`
  - actual project to change
  - target root path when local
  - target candidate paths or modules
  - required target paths still to verify
  - target project cognition status when available
  - statement that current project cognition cannot prove another project's
    implementation facts

- `source_evidence`
  - For each important conclusion, record whether the source is user
    confirmation, current project cognition, target project cognition,
    reference project cognition, live read, external source, or explicit
    assumption.

- `must_preserve`
  - Continue using `MP-###` items.
  - Must cover goal, scope, non-goals, critical decisions, acceptance signals,
    reference behavior, path constraints, risk acceptance, and blocking
    questions that would change downstream planning.

- `blocking_unknowns`
  - Hard unknowns block handoff readiness.
  - Soft unknowns require owner, latest resolve phase, and stop-and-reopen
    condition.

- `downstream_instructions`
  - Settled decisions that `sp-specify` must not re-ask.
  - Assumptions that must be preserved as assumptions.
  - Conflicts that require returning to `sp-discussion` or the user instead of
    silent reinterpretation.

- `quality_gate`
  - `status`: `draft`, `self_review_passed`, `user_confirmed`, or `blocked`
  - `self_reviewed_at`
  - `user_review_required`
  - `user_confirmed_at`
  - `blocked_reasons`

## Handoff Quality Gate

The handoff quality gate is mandatory. `sp-discussion` must not mark a handoff
ready when any of these checks fail:

- missing or vague `handoff_goal`
- Context Boundary Gate still unresolved
- cross-project request lacks `target_project_root`
- target path exists but evidence source is not named
- current repository role is not stated
- target project role is not stated
- Markdown and JSON disagree on shared fields
- hard unknowns remain open
- soft unknowns lack owner, latest resolve phase, or stop-and-reopen condition
- Must-Preserve Ledger omits goal, scope, non-goals, key decisions, acceptance
  signals, path constraints, or blocking questions
- quality gate lacks self-review status
- user has not reviewed and confirmed the handoff

Before user confirmation, the handoff can exist only as a draft. The workflow
must not recommend `sp-specify` until `quality_gate.status` records user
confirmation.

## Downstream Defensive Intake

### sp-specify

When `sp-specify` receives a discussion handoff, it must treat the handoff as an
authoritative input to the brainstorming kernel, not a bypass around it.

`sp-specify` should reject or route back when:

- `quality_gate.user_confirmed` or equivalent user-confirmed status is missing
- `handoff_goal` is missing or vague
- `context_boundary` is incomplete
- `target_project_root` is required but missing
- `current_project_role` or `target_project_role` is missing
- hard unknowns are still open
- Markdown and JSON disagree
- the handoff asks `sp-specify` to include sibling candidates outside the
  selected candidate boundary

When accepted, `sp-specify` must persist the boundary facts into
`brainstorming/handoff-to-specify.json`, `facts.json`, `context.md`,
`references.md`, and `workflow-state.md` according to each artifact's role.

If `target_project_root` differs from `current_project_root`, `sp-specify` must
state that the current project's cognition is not proof of target-project
implementation facts. It must record whether target evidence comes from target
cognition, minimal live reads, user confirmation, or explicit assumptions.

### sp-plan

`sp-plan` consumes `FEATURE_DIR/brainstorming/handoff-to-specify.json` as the
pre-plan truth package.

It must stop when:

- `planning_gate_status` is not `ready`
- `quality_gate.user_confirmed` is missing
- target project root is required but missing
- hard unknowns or open conflicts remain

For cross-project implementation, `sp-plan` must plan from the target project
context. It must not use the current project's cognition to prove target files
or target architecture. If the target project has no fresh cognition but the
target path exists, artifact-only planning may proceed only with explicit
minimal live reads, target path confirmation, and recorded risk. It must not
tell the user to run current-project `sp-map-scan -> sp-map-build` to fix target
coverage.

### sp-tasks

`sp-tasks` must inherit the implementation target into tasks and task packets.

Every implementation-shaping task should state:

- target root
- target-relative path or path discovery step
- evidence status
- relevant `MP-*` obligations
- boundary constraints and forbidden drift

Tasks must not silently point to the current repository unless the handoff says
the current repository is the implementation target. If a task uses a reference
project path, it must say why that path is reference-only or transfer evidence.

## Project Cognition Behavior

Project cognition is project-scoped. The Context Boundary Gate must preserve
that scoping explicitly:

- Current project cognition proves only current project facts.
- Target project cognition proves target project facts only when the target
  project has ready, fresh cognition and graph readiness.
- Reference cognition is supplemental-only, fresh-only, and cannot replace
  target evidence.
- If the target project root is unknown, the workflow blocks before technical
  options or handoff readiness.
- If the target root is known but target cognition is stale or missing,
  discussion may continue with product framing and explicit unknowns; durable
  planning claims require target evidence, minimal live reads, or a named
  blocker.

This prevents late failures where `sp-plan` asks current-repository cognition to
prove paths in another project.

## State And Template Fields

`templates/discussion-state-template.md` should gain state fields such as:

- `context_boundary_status`: `not-started`, `needs-user-input`, `locked`, or
  `blocked`
- `current_project_root`
- `current_project_role`
- `target_project_root`
- `target_project_role`
- `reference_sources`
- `external_systems`
- `boundary_blockers`
- `handoff_review_status`: `not-started`, `draft`, `self-review-passed`,
  `user-confirmed`, or `blocked`
- `handoff_user_confirmed_at`
- `handoff_blocker_reason`

`templates/brainstorming-handoff-specify-template.json` should gain:

- `handoff_goal`
- `context_boundary`
- `implementation_target`
- `source_evidence`
- `blocking_unknowns`
- `downstream_instructions`
- `quality_gate`

The existing candidate, split-plan, Must-Preserve, consequence analysis,
coverage, and planning gate fields remain.

## Implementation Scope

First increment:

- Update `templates/commands/discussion.md`.
- Update `templates/command-partials/discussion/shell.md`.
- Update `templates/discussion-state-template.md`.
- Update `templates/brainstorming-handoff-specify-template.json`.
- Update `templates/commands/specify.md`.
- Update `templates/commands/plan.md`.
- Update `templates/commands/tasks.md`.
- Update passive skill guidance for workflow routing and project cognition gate
  if needed.
- Update README, `PROJECT-HANDBOOK.md`, and
  `templates/project-handbook-template.md`.
- Add or update template and integration tests.

Follow-up increment:

- Add runtime JSON schema validation for discussion handoffs if template-only
  enforcement is not enough.
- Add stricter artifact validation around `quality_gate` and context boundary
  fields once downstream generated artifacts have stabilized.

## Test Strategy

Template tests should verify:

- `discussion.md` defines the Context Boundary Gate.
- `discussion.md` blocks technical options and handoff readiness when the gate
  is unresolved.
- `discussion.md` requires immediate target-root clarification for requests
  that move functionality into another project.
- `discussion.md` requires handoff self-review and user review.
- `discussion.md` forbids recommending `sp-specify` before user-confirmed
  handoff readiness.
- `discussion-state-template.md` includes boundary and review status fields.
- `brainstorming-handoff-specify-template.json` includes `handoff_goal`,
  `context_boundary`, `implementation_target`, `source_evidence`,
  `blocking_unknowns`, `downstream_instructions`, and `quality_gate`.
- `specify.md` rejects incomplete or unconfirmed discussion handoffs.
- `plan.md` refuses cross-project planning without target project context.
- `tasks.md` requires target root and target-relative path inheritance.
- Generated Markdown, TOML, and skills-based integrations preserve the updated
  guidance.

Docs tests should verify:

- README and project handbook describe `discussion` as a boundary-locking and
  handoff-quality workflow, not a freeform summary tool.
- Cross-project project cognition guidance states that current project
  cognition cannot prove another project's files.

## Acceptance Criteria

- `sp-discussion` asks boundary questions before technicalizing unclear
  cross-project, reference, external-system, or existing-module requests.
- A request to add functionality to another project cannot reach technical
  options or handoff readiness without a target project root.
- Handoffs include a concrete goal, target context, current repository role,
  evidence provenance, unknowns, downstream instructions, quality gate, and
  Must-Preserve obligations.
- A handoff cannot be `handoff-ready` until self-review passes and the user
  confirms the handoff.
- `sp-specify` refuses unconfirmed or boundary-incomplete handoffs.
- `sp-plan` does not use current project cognition as proof for an external
  implementation target.
- `sp-tasks` carries target root, target-relative path, evidence status, and
  relevant `MP-*` obligations into execution tasks.
- Tests prove that generated workflow guidance contains the boundary and
  handoff-quality contracts across supported integrations.

## Risks And Mitigations

- Risk: The gate blocks too early during exploratory product conversation.
  Mitigation: allow product framing before the gate is fully locked, but forbid
  source-grounded technical claims and handoff readiness.

- Risk: Handoff quality fields make simple discussions heavy.
  Mitigation: require the full gate only when the user requests handoff; keep
  normal discussion artifacts lightweight until then.

- Risk: Agents fill target path fields with guesses.
  Mitigation: require evidence provenance and block when target paths are
  inferred without user confirmation or target evidence.

- Risk: Downstream workflows duplicate `sp-discussion` logic.
  Mitigation: downstream workflows only validate intake and reject bad handoffs;
  they do not rerun the whole discussion flow.

- Risk: Template-only enforcement is weaker than schema validation.
  Mitigation: start with template and integration tests, then add a schema
  validator if real runs still produce malformed handoffs.

## Open Implementation Notes

- Keep the wording integration-neutral. Do not make the workflow depend on
  Codex-specific tooling.
- Preserve split-mode behavior from the existing discussion handoff design.
- Preserve Senior Consequence Analysis Gate fields and `CA-###` obligations in
  both Markdown and JSON handoffs.
- Prefer additive JSON fields so existing consumers can tolerate the new
  contract during transition.
- When updating tests, cover both command templates and generated integration
  surfaces so downstream users receive the same behavior.
