# Discussion Split Handoff Design

## Summary

Strengthen `sp-discussion` so a large, exploratory direction can be discussed first and then assessed for whether it is ready for one bounded `sp-specify` handoff or needs requirement splitting inside the same discussion session.

This design does not add a new `sp-split` workflow. The split decision and split artifacts belong to `sp-discussion`. `sp-specify` remains the consumer of one bounded feature handoff at a time and acts as a guardrail when a discussion handoff crosses the selected candidate boundary.

The intended flow is:

```text
sp-discussion
  -> handoff assessment
    -> ready-for-specify: write a bounded handoff and continue to sp-specify
    -> split-required: write split-plan.md, select one candidate, then write a candidate handoff
    -> continue-discussion: keep clarifying in sp-discussion
```

For multi-stage work, the discussion session keeps a candidate backlog. After one candidate is implemented, the user can return to the same `sp-discussion` slug and continue with the next recommended candidate instead of restarting the whole conversation.

## Goals

- Keep the user experience discussion-first: the user discusses the large direction before any split decision is forced.
- Avoid adding another user-facing workflow command for requirement splitting.
- Prevent oversized `handoff-to-specify.md` files from carrying multiple independent feature candidates into one formal spec.
- Let `sp-discussion` maintain a durable candidate backlog for staged delivery.
- Let the user continue second and later stages from the same discussion without restating the original direction.
- Keep `sp-specify` focused on one bounded candidate while preserving a guardrail against sibling-scope creep.
- Preserve compatibility with existing `.specify/discussions/<slug>/handoff-to-specify.md` intake.
- Keep artifact ownership clear: `sp-discussion` owns discussion and split artifacts; `sp-specify` consumes them and records consumed metadata in feature artifacts.

## Non-Goals

- Do not add `sp-split`, `sp-breakdown`, or another split-only workflow.
- Do not make `sp-discussion` create feature branches, feature directories, `spec.md`, `plan.md`, `tasks.md`, or implementation artifacts.
- Do not let `sp-discussion` perform implementation planning or task decomposition.
- Do not let `sp-specify` silently merge sibling candidate scopes into one feature.
- Do not require `sp-specify`, `sp-plan`, `sp-tasks`, or `sp-implement` to directly edit `split-plan.md`.
- Do not build an automatic cross-workflow completion sync in the first increment.
- Do not make the design Codex-only.

## Current Context

`sp-discussion` already stores resumable pre-specification artifacts under `.specify/discussions/<slug>/` and writes `handoff-to-specify.md` only after explicit user request.

`sp-specify` already consumes discussion handoffs and has a decomposition gate. It can decompose a coherent feature into capabilities, but it should not become the place where a broad program direction is converted into several separately valuable spec candidates.

The gap is the point after the user says the discussion is done. Today, the handoff can either become one large `handoff-to-specify.md` or rely on `sp-specify` to detect the overbreadth later. That makes the second stage awkward: after one piece ships, the user has no durable backlog that remembers the original split and recommends the next candidate.

## Core Design

When the user explicitly asks to hand off a discussion, `sp-discussion` first runs a handoff assessment instead of immediately writing `handoff-to-specify.md`.

The assessment has three possible decisions:

- `ready-for-specify`: the mature discussion describes one coherent feature boundary. `sp-discussion` writes a bounded handoff for `sp-specify`.
- `split-required`: the mature discussion contains multiple independently valuable candidates, release tracks, business domains, validation packages, or implementation chains. `sp-discussion` enters split mode and writes `split-plan.md`.
- `continue-discussion`: the issue is not overbreadth. The discussion still lacks critical goal, user, scope, success, boundary, or open-question closure. `sp-discussion` returns to the question loop.

The assessment is triggered only by explicit user intent to hand off, continue to the next workflow, feed the discussion to `sp-specify`, or start the next stage. It is not a background readiness detector.

## Handoff Assessment

`sp-discussion` writes or refreshes:

```text
.specify/discussions/<slug>/handoff-assessment.md
```

The file records:

```text
# Handoff Assessment

## Decision
- status: ready-for-specify | split-required | continue-discussion
- rationale: <why this decision was selected>
- decided_at: <ISO-8601 timestamp>

## Assessment Dimensions
- feature_coherence: <one coherent feature or several outcomes>
- independent_value: <whether sub-parts can ship and be accepted independently>
- planning_shape: <whether sub-parts need different plan/data/contracts/testing shapes>
- implementation_dependency: <serial prerequisites, sibling work, or independent tracks>
- validation_split: <one acceptance package or multiple proof packages>
- risk_profile: <whether some parts need research while others are ready>

## Required Next Action
- next_action: write-handoff | enter-split-mode | continue-discussion
- user_choice_required: true | false
```

The status drives the next step. The rationale must cite discussion artifacts such as `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, or explicit user confirmation.

## Split Mode Inside sp-discussion

When the assessment status is `split-required`, `sp-discussion` writes:

```text
.specify/discussions/<slug>/split-plan.md
```

`split-plan.md` is a candidate backlog, not an implementation plan and not a task list. It decomposes the large direction into spec candidates that can each be handed to `sp-specify` independently.

Each candidate has a stable ID:

```text
CAND-001
CAND-002
CAND-003
```

Each candidate has one status:

```text
not-started | handoff-ready | handed-off | in-progress | completed | deferred | blocked
```

Candidate statuses mean:

- `not-started`: the candidate exists in the backlog but is not ready to hand off.
- `handoff-ready`: the candidate is bounded enough to produce a candidate handoff.
- `handed-off`: `sp-discussion` wrote a candidate handoff for it.
- `in-progress`: evidence suggests a feature workflow has started for it.
- `completed`: evidence or user confirmation indicates the candidate is done.
- `deferred`: the user or discussion explicitly postponed it.
- `blocked`: the candidate needs more discussion, research, or prerequisite work.

The backlog records recommended order and dependency notes so the user can resume later stages.

## split-plan.md Shape

`split-plan.md` should use this structure:

```text
# Discussion Split Plan

## Source Discussion
- slug: <slug>
- assessment_path: .specify/discussions/<slug>/handoff-assessment.md
- source_files:
  - discussion-state.md
  - requirements.md
  - technical-options.md
  - project-context.md
  - open-questions.md

## Original Direction
<short summary of the large direction>

## Split Rationale
<why one spec would be unsafe, incoherent, or too broad>

## Candidate Backlog

### CAND-001: <title>
- status: handoff-ready
- goal: <candidate outcome>
- scope: <current candidate scope>
- non_goals: <sibling or future work excluded from this candidate>
- acceptance_signals: <what proves this candidate is done>
- dependencies: <candidate IDs or external prerequisites>
- risks: <planning or implementation risks>
- recommended_next_step: sp-specify | continue-discussion | deep-research-later | defer
- handoff_path: .specify/discussions/<slug>/handoffs/CAND-001-handoff-to-specify.md | none
- feature_dir: <feature dir when known, otherwise none>
- completion_evidence: <path, user confirmation, or none>

## Recommended Sequence
<ordered stages and why>

## Resume Guidance
<how to continue after the current candidate is implemented>
```

`deep-research-later` is a candidate recommendation only. `sp-discussion` does not run deep research. A later `sp-specify` or plan gate decides whether `sp-deep-research` is required before planning.

## Candidate Handoffs

When the user chooses a candidate, `sp-discussion` writes a candidate-specific handoff:

```text
.specify/discussions/<slug>/handoffs/CAND-001-handoff-to-specify.md
```

For compatibility, it also writes or refreshes:

```text
.specify/discussions/<slug>/handoff-to-specify.md
```

The candidate-specific handoff is canonical. The legacy path is a full readable copy of the latest selected candidate handoff so existing `sp-specify` usage keeps working. It must not be a pointer-only file because existing intake expects the supplied path to contain the user-reviewable handoff artifact.

Candidate handoff frontmatter:

```yaml
source_command: sp-discussion
discussion_slug: <slug>
candidate_id: CAND-001
candidate_title: <title>
status: handoff-ready
source_split_plan: .specify/discussions/<slug>/split-plan.md
updated_at: <ISO-8601 timestamp>
source_files:
  - requirements.md
  - technical-options.md
  - project-context.md
  - split-plan.md
```

Candidate handoff body:

```text
## Candidate Scope
## Confirmed Product Goal And Users
## In Scope
## Out Of Scope
## Acceptance Signals
## Prior Candidates And Dependencies
## Deferred Candidates
## Project Context Evidence
## Open Questions
## Must-Preserve Ledger
## Instructions For sp-specify
```

The Must-Preserve Ledger follows the existing discussion-to-specify fidelity design. Candidate handoffs should include only ledger items that shape the selected candidate plus any dependency, non-goal, or deferred-sibling item needed to prevent scope drift.

## Candidate JSON Companions

Candidate-specific handoffs must also have machine-readable JSON companions:

```text
.specify/discussions/<slug>/handoffs/CAND-001-handoff-to-specify.json
```

For compatibility, `sp-discussion` also writes or refreshes the latest legacy JSON copy:

```text
.specify/discussions/<slug>/handoff-to-specify.json
```

The candidate JSON is canonical for that candidate. The legacy JSON is a full latest-candidate copy, not a pointer. Whenever `sp-discussion` refreshes `.specify/discussions/<slug>/handoff-to-specify.md` for the latest selected candidate, it must refresh `.specify/discussions/<slug>/handoff-to-specify.json` in the same operation. This prevents a stale legacy JSON mirror from describing a previous candidate while the legacy Markdown describes the current one.

Candidate JSON should mirror the prior discussion-to-specify fidelity schema and add split metadata:

```json
{
  "version": 1,
  "source_command": "sp-discussion",
  "discussion_slug": "<slug>",
  "candidate_id": "CAND-001",
  "candidate_title": "<title>",
  "status": "handoff-ready",
  "source_split_plan": ".specify/discussions/<slug>/split-plan.md",
  "source_markdown": ".specify/discussions/<slug>/handoffs/CAND-001-handoff-to-specify.md",
  "latest_legacy_markdown": ".specify/discussions/<slug>/handoff-to-specify.md",
  "source_files": [
    "requirements.md",
    "technical-options.md",
    "project-context.md",
    "split-plan.md"
  ],
  "prior_candidates": [],
  "deferred_candidates": [],
  "stage_scope_boundary": "<current candidate boundary>",
  "reopen_condition": "<when to return to sp-discussion>",
  "must_preserve": []
}
```

Markdown and JSON must agree on `discussion_slug`, `candidate_id`, `candidate_title`, `status`, `source_split_plan`, and every Must-Preserve Ledger item ID, type, claim, blocking level, owner, latest resolve phase, and status. If candidate Markdown and candidate JSON disagree, `sp-specify` must block and tell the user to refresh the `sp-discussion` handoff. If the legacy Markdown and legacy JSON disagree on the selected candidate ID, `sp-specify` must block rather than choosing one representation.

If a candidate Markdown handoff exists but the candidate JSON is missing, `sp-specify` may reconstruct the JSON into the active feature's `brainstorming/handoff-to-specify.json` and record the reconstruction source. If the legacy Markdown exists but the legacy JSON is stale or missing, `sp-specify` may continue only when it can read the candidate-specific JSON or reconstruct the JSON from the supplied Markdown; it must report the legacy mirror mismatch as a handoff repair advisory. If only JSON exists and Markdown is missing, the handoff is invalid because the user-reviewable source is absent.

## Multi-Stage Continuation

The second-stage experience is part of the design.

After the first candidate is handed off and implemented, the user should be able to return to the same discussion and say a natural request such as:

```text
continue this discussion's next stage
```

`sp-discussion` then reads `discussion-state.md` and `split-plan.md`, inspects candidate statuses, and recommends the next candidate.

The recommendation rules:

- Prefer the first `handoff-ready` or `not-started` candidate whose dependencies are completed or explicitly waived.
- Do not recommend a candidate whose dependency is incomplete unless the user accepts an override risk.
- If multiple candidates are ready, list the recommended one and the viable alternatives, then ask the user to choose.
- If no candidate is ready, resume discussion on the blocker for the next likely candidate.
- If all candidates are completed or deferred, mark the split plan as completed or ask whether deferred candidates should remain in the backlog.

First increment completion sync is low coupling:

- `split-plan.md` records `handoff_path`, optional `feature_dir`, and `completion_evidence`.
- On resume, `sp-discussion` may inspect referenced feature artifacts when paths are present.
- If evidence is insufficient, it asks the user whether the previous candidate is completed, in progress, blocked, or only handed off.
- `sp-discussion` updates `split-plan.md` from that evidence or user confirmation.

This avoids requiring downstream workflows to write back into discussion artifacts.

## Top-Level Discussion Status During Split Backlog

A discussion with an active split backlog remains incomplete until every candidate is `completed`, `deferred`, or explicitly abandoned by the user. This keeps normal session resume behavior working for "continue the next stage" requests.

Top-level `discussion-state.md` status should be derived from the backlog:

- `handoff-ready`: at least one candidate handoff is ready for the user to pass to `sp-specify`, and no blocker prevents that candidate from being the recommended next stage.
- `active`: split mode is active, there is remaining candidate work, and `sp-discussion` can continue selection, clarification, or backlog maintenance.
- `blocked`: the next viable candidate is blocked by unresolved discussion, missing project grounding, or a dependency that the user has not waived.
- `completed`: all candidates are completed or deferred, or the user explicitly closes the discussion as done.
- `abandoned`: the user explicitly abandons the discussion.

`split_plan_status` refines the top-level status:

- `active`: a split plan exists and no candidate has been handed off yet.
- `partially-handed-off`: at least one candidate is `handed-off`, `in-progress`, or `completed`, and at least one candidate remains `not-started`, `handoff-ready`, `deferred`, or `blocked`.
- `completed`: all candidates are `completed` or `deferred`, or the user closes the backlog.
- `blocked`: no next candidate can be selected without resolving a blocker.

`sp-discussion` must not mark the discussion `completed` merely because the first candidate handoff was written.

## discussion-state.md Extensions

`templates/discussion-state-template.md` should add stages for assessment and split mode:

```text
current_stage:
  session-intake
  idea-framing
  context-grounding
  question-loop
  technical-options
  requirements-synthesis
  handoff-assessment
  split-mode
  candidate-selection
  handoff-on-request
```

It should also add:

```text
## Handoff Assessment

- handoff_assessment_status: not-run | ready-for-specify | split-required | continue-discussion
- handoff_assessment_path: handoff-assessment.md | none
- handoff_assessment_decided_at: <timestamp or none>

## Split Plan

- split_plan_status: none | active | partially-handed-off | completed | blocked
- split_plan_path: split-plan.md | none
- active_candidate: CAND-xxx | none
- next_recommended_candidate: CAND-xxx | none
```

The existing `handoff_requested_by_user` field remains. Handoff assessment does not run unless the user explicitly requests handoff or continuation to the next stage.

## sp-specify Consumption

`sp-specify` should support both paths:

```text
.specify/discussions/<slug>/handoff-to-specify.md
.specify/discussions/<slug>/handoffs/CAND-001-handoff-to-specify.md
```

When the supplied path is Markdown, `sp-specify` should look for the same-stem JSON companion first. For a candidate handoff, that is `handoffs/CAND-001-handoff-to-specify.json`. For the legacy latest handoff, that is `handoff-to-specify.json`. If the Markdown frontmatter contains `candidate_id`, `sp-specify` may also use `source_split_plan` to locate and validate the candidate entry in `split-plan.md`.

When a candidate handoff is present, `sp-specify` records these fields into the active feature artifacts, especially `brainstorming/handoff-to-specify.json`, `context.md`, `references.md`, and `workflow-state.md` where appropriate:

- `entry_source: sp-discussion`
- `discussion_slug`
- `candidate_id`
- `candidate_title`
- `source_split_plan`
- `handoff_path`
- `prior_candidates`
- `deferred_candidates`
- `stage_scope_boundary`
- `reopen_condition`

Rules for candidate intake:

- The current feature spec covers one candidate.
- Sibling candidates named in `split-plan.md` are out of scope unless the user returns to `sp-discussion` and selects a new candidate handoff.
- If the user asks inside `sp-specify` to include a sibling candidate, `sp-specify` runs the decomposition gate.
- If the request is only internal capability decomposition within the selected candidate, `sp-specify` may continue.
- If the request crosses the candidate boundary, `sp-specify` stops and tells the user to return to `sp-discussion` to update or select the candidate.
- If a legacy handoff has no `candidate_id`, `sp-specify` follows existing discussion intake. If it detects that the handoff is too broad for one spec, it stops and tells the user to run `sp-discussion` split mode for that discussion slug.

`sp-specify` should not directly update `split-plan.md` in the first increment. It should report the source discussion and candidate ID in its completion output and tell the user to return to the same `sp-discussion` slug after implementation to continue the next stage.

## Ownership And Compatibility

Artifact ownership:

- `sp-discussion` owns `discussion-state.md`, `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, `handoff-assessment.md`, `split-plan.md`, `handoffs/*.md`, and the legacy latest `handoff-to-specify.md`.
- `sp-specify` consumes discussion artifacts and owns its active feature directory.
- `sp-plan`, `sp-tasks`, and `sp-implement` consume feature artifacts, not discussion artifacts.

Compatibility:

- Existing single-handoff discussions continue to work.
- Candidate-specific handoffs are the preferred new path.
- The legacy `handoff-to-specify.md` remains available as a full readable latest selected candidate handoff copy.
- The legacy `handoff-to-specify.json` remains available as a full latest selected candidate JSON copy and must be refreshed with the legacy Markdown.
- Existing `sp-specify` discussion intake text should be expanded to mention candidate-specific handoff paths and latest-copy semantics.

## Error Handling

- If `handoff-assessment.md` says `split-required` but `split-plan.md` is missing, `sp-discussion` regenerates `split-plan.md` from the discussion artifacts instead of asking the user to write it manually.
- If the user asks for the next stage and multiple candidates are eligible, `sp-discussion` lists the recommendation and alternatives, then asks the user to choose.
- If the user selects a candidate whose dependencies are not completed, `sp-discussion` allows override only after recording the risk in `split-plan.md` and the candidate handoff.
- If a candidate handoff already exists, `sp-discussion` refreshes it only for that candidate and does not overwrite other candidate handoffs.
- If the legacy latest `handoff-to-specify.md` exists, `sp-discussion` may replace it with the latest selected candidate copy, but the canonical candidate handoff remains under `handoffs/`.
- If the legacy latest `handoff-to-specify.json` exists, `sp-discussion` must replace it with the latest selected candidate JSON copy in the same refresh operation as the legacy Markdown.
- If `sp-specify` receives a candidate handoff whose scope is inconsistent with `split-plan.md`, it stops and asks the user to return to `sp-discussion` to repair the candidate or split plan.
- If `sp-specify` receives mismatched candidate Markdown and JSON, or mismatched legacy Markdown and JSON, it blocks with a handoff integrity error unless it can safely reconstruct JSON from the supplied Markdown and record a repair advisory.
- If `split-plan.md` records a completed candidate but no evidence is present, `sp-discussion` asks for user confirmation on resume before relying on that status.

## Implementation Surface

Implementation should update the normal generated workflow surfaces:

- `templates/commands/discussion.md`: add handoff assessment, split mode, candidate selection, multi-stage continuation, candidate handoff creation, and split-plan ownership.
- `templates/command-partials/discussion/shell.md`: ensure the discussion shell guidance names the new discussion artifacts and does not imply `handoff-to-specify.md` is the only handoff output.
- `templates/discussion-state-template.md`: add assessment and split-plan state fields.
- `templates/commands/specify.md`: expand discussion handoff intake to support candidate-specific handoff paths, selected candidate scope, sibling boundary checks, and legacy latest-copy behavior.
- `templates/brainstorming-handoff-specify-template.json` or the current brainstorming handoff template surface: add candidate metadata, source split plan, sibling/deferred candidate fields, scope boundary, reopen condition, and JSON integrity expectations.
- `src/specify_cli/hooks/artifact_validation.py` and related artifact validation tests when they validate discussion handoff or brainstorming handoff shapes: accept candidate metadata and reject ambiguous stale handoff mirrors where applicable.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: route large rough directions to `sp-discussion`, then let `sp-discussion` assess whether split mode is needed.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: keep the staged discussion cognition gate compatible with split mode when split rationale uses project-specific technical evidence.
- `README.md`: document discussion assessment, split mode, candidate backlog, and next-stage continuation.
- `PROJECT-HANDBOOK.md` and `templates/project-handbook-template.md`: update workflow contract generation guidance and workflow overview.
- Tests in `tests/test_alignment_templates.py`, integration tests, and command surface tests: assert the new handoff and split contracts are generated across supported integration surfaces.

No workflow-state hook contract change is required for `sp-discussion` because discussion state remains independent from feature `workflow-state.md`.

## Testing Strategy

Tests should prove:

- `templates/commands/discussion.md` includes `handoff-assessment`, `split-mode`, `candidate-selection`, `split-plan.md`, and `handoffs/CAND-xxx-handoff-to-specify.md`.
- `templates/discussion-state-template.md` contains the new assessment and split-plan state fields.
- `templates/commands/specify.md` accepts candidate-specific handoff paths and preserves `candidate_id`, `source_split_plan`, `stage_scope_boundary`, and deferred candidates.
- Candidate handoffs include `.md` and `.json` companions under `handoffs/`, and the legacy latest `.md` and `.json` copies refresh together.
- Mismatched candidate Markdown/JSON and stale legacy Markdown/JSON are blocked or reported according to the integrity rules.
- `sp-specify` guidance says the current feature covers one candidate and must not silently include sibling candidates.
- A split backlog keeps the top-level discussion status incomplete until every candidate is completed, deferred, or explicitly abandoned.
- README and handbook text explain returning to the same discussion slug for second and later stages.
- Generated command or skill surfaces include the new discussion split language for Markdown, TOML, and skills-based integrations.
- Existing legacy handoff tests still pass for `.specify/discussions/<slug>/handoff-to-specify.md`.
- New tests prove `handoff-to-specify.md` is no longer the only valid discussion handoff path.
- Project cognition gate tests still allow product framing before source-grounded split rationale, while requiring cognition grounding before technical split claims.

## Acceptance Criteria

- A user can finish a large `sp-discussion`, request handoff, and receive either a direct bounded handoff or a split-plan-backed candidate selection.
- A split-required discussion produces durable candidate IDs and statuses.
- Selecting `CAND-001` creates a canonical candidate handoff and updates the legacy latest handoff path.
- Selecting `CAND-001` creates canonical candidate Markdown and JSON handoffs, then refreshes both legacy latest handoff copies.
- After `CAND-001` is implemented, the user can resume the same discussion and ask for the next stage without restating the original direction.
- `sp-specify` can consume a candidate handoff and preserve the candidate boundary in feature artifacts.
- `sp-specify` blocks instead of silently folding sibling candidates into the selected feature.
- The implementation requires no new user-facing split workflow command.
