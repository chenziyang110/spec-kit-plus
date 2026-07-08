# Complete-First Plan and Tasks Scope Design

**Date:** 2026-07-08
**Status:** Draft for user review
**Owner:** Codex

## Summary

This design hardens `sp-plan` and `sp-tasks` so they preserve the complete
user-confirmed feature scope by default. Once `sp-specify` has produced an approved
specification package, planning and task generation should not reinterpret that work
as a smaller MVP, pilot, first release, `v1/v2`, `P0/P1`, or future-phase delivery
slice.

The intended behavior is complete-first:

- plan and task the requested scope as fully as possible
- use sequencing, dependencies, parallel batches, join points, and validation paths
  to make complex work executable
- block or route upstream only for real missing truth, conflict, safety, feasibility,
  or target-boundary problems
- allow deferral only when the user explicitly confirmed the deferral or the upstream
  artifact already records it as user-confirmed

Complexity alone is not a valid reason to shrink, split, defer, or block the task
package.

## Problem Statement

The repository already has partial scope-preservation controls:

- generated workflows preserve user-confirmed product scope
- scope reduction requires user confirmation
- `sp-tasks` must not infer a smaller release from User Story 1
- create/scaffold operations cannot degrade to template-only or documentation-only
  support without confirmation

Those rules point in the right direction, but they leave two practical gaps.

First, `sp-plan` does not state the complete-first rule as directly as `sp-tasks`.
It strongly protects operation-shaped capabilities, but an agent can still be tempted
to describe complex work as a later version or future phase.

Second, `sp-tasks` allows coarser later-phase placeholders when exact downstream
details depend on earlier join-point evidence. That rule is useful when it prevents
guesswork, but it needs a sharper boundary: coarser sequencing is not delivery
deferral. A task package may defer fine-grained decomposition until a named join
point, but it must still preserve the full confirmed delivery scope and include the
refinement or checkpoint work needed to finish it.

## Goals

- Make complete-first delivery preservation explicit in `sp-plan`, `sp-tasks`, and
  generated task templates.
- Prevent silent conversion of confirmed scope into `v1/v2`, `P0/P1`, MVP, pilot,
  first-release, later-phase, or future-work delivery slices.
- Keep legitimate execution ordering, dependency management, join points, and
  progressive refinement.
- Avoid over-blocking. Agents should continue planning and tasking difficult work
  whenever enough truth exists to do so safely.
- Preserve user-confirmed deferrals as an explicit exception with evidence, residual
  risk, and reopen conditions.

## Non-Goals

- Do not remove user-story priorities such as `P1`, `P2`, and `P3` when they are used
  only as ordering labels from `spec.md`.
- Do not forbid phases as execution-order sections in `tasks.md`.
- Do not force speculative low-level tasks for downstream work whose exact file edits
  depend on earlier join-point evidence.
- Do not remove legitimate blocker behavior when upstream truth is actually missing.
- Do not rewrite every use of the word `deferred`; some deferral statuses are valid
  for handoff accounting, remediation, or user-confirmed scope decisions.

## Approved Direction

### 1. Complete-First Scope Preservation

Add a shared rule to `sp-plan` and `sp-tasks`:

The active feature scope is the complete user-confirmed scope from `spec.md`,
`alignment.md`, `context.md`, `plan-contract.json`, and any approved discussion or
brainstorming handoff. Planning and task generation may choose execution order, batch
shape, and join points, but must not reduce delivery scope.

Forbidden scope-shrinking patterns include:

- "MVP first" when the user did not request an MVP
- `v1/v2` release slicing invented by the agent
- `P0/P1` delivery buckets invented by the agent
- "first release", "pilot", "prototype", or "future phase" as a way to omit
  confirmed behavior
- moving confirmed behavior to "later" without explicit user confirmation

### 2. Complexity Is Not A Deferral Trigger

Add an explicit rule:

If the work is complex but the scope and target are clear, continue by decomposing
the work into dependencies, serial steps, parallel-safe batches, join points,
validation tasks, and refinement checkpoints. Do not block, split into a separate
future version, or return upstream merely because the task graph is large.

Acceptable responses to complexity:

- add implementation guardrails
- add dependency ordering
- split by isolated write sets
- use parallel batches where safe
- add join-point validation
- add refinement tasks when later detail depends on earlier evidence
- add verification tasks and residual-risk notes

Unacceptable responses to complexity:

- shrink to a smaller MVP
- defer whole confirmed capabilities to a future phase
- ask the user to accept a reduced scope without a concrete named constraint
- block only because the plan is long or difficult

### 3. Hard Blockers Stay Narrow

`sp-plan` or `sp-tasks` should block or route upstream only when continuing would be
unsafe or speculative.

Valid blockers include:

- missing or conflicting user decision that materially changes scope or behavior
- hard unknown that changes architecture, data model, compatibility, or validation
- target project root or target-relative path cannot be identified without guessing
- safety, security, compliance, or data-loss risk cannot be handled through planning
- feasibility evidence is missing for a dependency that determines whether the
  requested capability can be built
- upstream artifacts contradict each other and no safe interpretation preserves scope
- adaptive execution policy requires blocking because heavy or safety-critical work
  lacks an execution-capable native subagent, or because the work cannot be packetized
  safely

Invalid blockers include:

- the feature is too large
- there are many tasks
- the agent would prefer a staged release
- implementation will require multiple phases or join points
- parallelization is not available for ordinary work

Runtime capability limits are a blocker only under the existing adaptive execution
policy for heavy, safety-critical, or unpacketizable work. They are not permission to
shrink scope, relabel confirmed work as a later version, or move confirmed behavior
to a future phase.

### 4. User-Confirmed Deferral Contract

Deferrals remain allowed only when they are explicitly user-confirmed or already
locked in an upstream artifact as user-confirmed.

Every valid deferral must record:

- confirmation source
- exact excluded behavior
- residual risk
- reopen or stop condition
- downstream artifact that must preserve the deferral

If the user did not confirm the deferral, the agent must either task the behavior,
create a refinement or validation checkpoint that still preserves it, or identify a
valid hard blocker.

### 5. Progressive Refinement Without Scope Loss

The existing guidance to keep later work coarser when details depend on join-point
evidence should be clarified, not removed.

Allowed:

- "After join point J1 validates the generated API shape, refine the remaining
  endpoint tasks using the validated contract."
- "Keep downstream file-specific tasks at the story level until the schema migration
  task produces the final table names."

Not allowed:

- "Do US1 now and leave US2/US3 for later."
- "Ship the MVP first; move the rest to v2."
- "Future phase: implement the remaining confirmed capability."

The distinction is whether the full confirmed scope remains inside the current
feature task package with explicit refinement or checkpoint work.

## Implementation Surfaces

The implementation should be shared-template-first.

Primary surfaces:

- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/plan-template.md`
- `templates/plan-contract-template.json`
- `templates/tasks-template.md`
- `templates/task-index-template.json`
- `templates/task-packet-template.json`
- `templates/implement-execution-state-template.json` when implementation handoff
  state consumes delivery scope, optimization scope, or deferral fields
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `PROJECT-HANDBOOK.md`
- `README.md`
- `tests/test_alignment_templates.py`

Secondary surfaces may be updated only if search shows direct drift:

- `templates/project-handbook-template.md`
- `scripts/bash/update-agent-context.sh`
- `scripts/powershell/update-agent-context.ps1`
- generated context block tests

## Testing Strategy

Add template-contract tests that assert:

1. `sp-plan` contains complete-first scope preservation language.
2. `sp-tasks` contains complete-first scope preservation language.
3. `tasks-template.md` distinguishes execution phases from delivery deferral.
4. Complexity alone is explicitly not a blocker or deferral trigger.
5. User-confirmed deferral requires all five deferral contract fields:
   confirmation source, exact excluded behavior, residual risk, reopen or stop
   condition, and downstream artifact that preserves the deferral.
6. Forbidden shrinking terms are rejected when used as suggested delivery scope:
   MVP, pilot, prototype, first release, `v1/v2`, `P0/P1`, later phase, and future
   work.
7. Existing legitimate priority labels such as user story `P1`, `P2`, and `P3`
   remain allowed as ordering labels.
8. Structured artifact templates preserve the same complete-first and deferral
   contract fields where they carry planning contracts, task indexes, task packets,
   or implementation execution state.

## Acceptance Criteria

The change is complete when:

1. `sp-plan` and `sp-tasks` explicitly say that confirmed scope must be planned and
   tasked complete-first.
2. `sp-tasks` tells agents to handle complexity through decomposition, ordering,
   batches, join points, refinement tasks, and validation instead of scope shrinking.
3. Blocking guidance is narrow and does not allow "too complex" as a standalone
   blocker, while preserving the existing adaptive blocker carve-out for heavy,
   safety-critical, or unpacketizable work without allowing scope reduction.
4. Deferrals require explicit user confirmation plus a recorded confirmation source,
   exact excluded behavior, residual risk, reopen or stop condition, and downstream
   artifact that preserves the deferral.
5. Generated `tasks.md` guidance makes clear that phases are execution order, not
   permission to move confirmed work out of the current delivery.
6. Regression tests protect the new wording and preserve existing legitimate `P1`,
   `P2`, and `P3` user-story priority labels.
7. Structured JSON templates that carry planning, task, packet, or implementation
   handoff state expose enough fields to preserve complete-first scope and the full
   deferral contract.

## Risks

- Too much anti-deferral language could accidentally make agents speculate about
  downstream details before join-point evidence exists.
- Too much complete-first pressure could discourage legitimate upstream escalation
  when the artifacts are contradictory or unsafe.
- Overly broad forbidden-term tests could catch unrelated technical uses such as
  schema `v1/v2` or semantic permission levels.

## Mitigations

- Preserve progressive refinement, but require it to stay inside the current feature
  scope.
- Keep a narrow valid-blocker list for missing truth, conflict, safety, feasibility,
  and target-boundary failures.
- Test forbidden shrinking terms in scope-delivery contexts rather than globally.
- Keep story priority labels explicitly allowed.

## Decision

Proceed with the complete-first scope-preservation hardening as a shared workflow
contract change.

The best implementation path is a targeted template and regression-test update that
strengthens existing scope-preservation rules without removing legitimate sequencing,
join points, user-confirmed deferrals, or upstream blockers.
