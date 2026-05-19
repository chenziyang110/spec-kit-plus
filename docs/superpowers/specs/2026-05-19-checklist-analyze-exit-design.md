# Checklist And Analyze Default-Path Exit Design

## Context

Spec Kit Plus currently teaches the generated feature workflow as:

```text
specify -> plan -> tasks -> analyze -> implement
```

`sp-plan` also recommends `sp-checklist` as a follow-up quality check. This makes
`sp-checklist` and `sp-analyze` feel like downstream safety nets for quality that
should already be enforced by `sp-plan`, `sp-tasks`, and `sp-implement`.

The requested product direction is to remove `sp-checklist` and `sp-analyze` from
the default workflow path while keeping them available for manual diagnostics and
legacy compatibility. The default path should optimize for doing each stage
correctly the first time, not for catching preventable misses in a later audit.

## Goals

- Make the default generated workflow:

  ```text
  specify -> plan -> tasks -> implement
  ```

- Remove `sp-checklist` and `sp-analyze` from default handoffs, recommended next
  commands, README mainline guidance, and new workflow-state transitions.
- Move the useful quality checks from `sp-checklist` and `sp-analyze` into the
  completion contracts for `sp-plan`, `sp-tasks`, and `sp-implement`.
- Preserve `sp-checklist` and `sp-analyze` as optional manual diagnostic and
  compatibility commands for existing projects and explicit user requests.
- Keep legacy `/sp.analyze` state readable so old generated projects can recover
  or migrate instead of failing mysteriously.

## Non-Goals

- Do not delete the `sp-checklist` or `sp-analyze` command templates in this
  change.
- Do not remove compatibility code that recognizes existing `/sp.analyze`
  workflow-state values.
- Do not weaken the quality bar by merely changing documentation. The old
  downstream checks must become upstream completion criteria.
- Do not make `sp-implement` reinterpret product intent from chat history when a
  structured task handoff exists.

## Proposed Behavior

### `sp-plan`

`sp-plan` becomes responsible for proving that planning artifacts are coherent
before task decomposition starts. Its default handoff should point only to
`sp-tasks`.

Before completion, `sp-plan` must verify:

- requirement and plan readiness are explicit enough for task generation
- locked decisions, must-preserve items, and consequence obligations survive
  into plan artifacts
- `Implementation Constitution` appears when boundary-sensitive work requires it
- dispatch compilation hints exist when task packets need guardrails
- validation strategy, risk handling, and open assumptions are visible
- planning lane handoffs are consumed, deferred, or blocked with evidence

`sp-checklist` may still exist as a manually invoked review aid, but `sp-plan`
should not recommend it as the next normal step.

### `sp-tasks`

`sp-tasks` becomes the primary pre-implementation quality gate. It should produce
an implementation-ready task package or route directly to the highest invalid
upstream stage. It should not hand off to `sp-analyze` as the normal path.

Before completion, `sp-tasks` must verify:

- buildable `FR-*` items and buildable success criteria map to tasks,
  checkpoints, or explicit deferrals
- locked planning decisions and must-preserve obligations survive into tasks,
  packets, guardrails, or stop-and-reopen conditions
- `Implementation Constitution` rules are represented in the task guardrail
  index or equivalent task-local rules
- `DP1`, `DP2`, and `DP3` packet readiness are satisfied as far as task
  generation can prove
- reference fidelity behavior maps to tasks, checkpoints, join points, or
  explicit deferrals
- unmapped tasks are justified or removed
- dependency ordering and parallel batches have no obvious write-set conflicts
- accepted task-generation handoffs are consumed, deferred, escalated, or blocked

If the task package is clean, `sp-tasks` writes `next_command: /sp.implement` and
emits or updates `handoff-to-implement.json`. If it finds missing upstream truth,
it routes directly to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research` with the
blocking evidence.

### `sp-implement`

`sp-implement` should trust a clean, structured task handoff instead of requiring
an analyze gate. It should block only when the workflow state points to an
upstream repair command or when the task package lacks the required execution
contract.

Before dispatch, `sp-implement` must verify:

- `workflow-state.md` permits `/sp.implement` or equivalent cleared execution
  state
- `handoff-to-implement.json`, `task-index.json`, and task packets preserve
  required objectives, scopes, guardrails, validation commands, and stop
  conditions
- each ready `WorkerTaskPacket` passes pre-dispatch validation
- missing quality evidence routes to the owning upstream stage, usually
  `sp-tasks`, instead of telling the user to run `sp-analyze`

Legacy `/sp.analyze` states may still be recognized with compatibility wording,
but newly generated task packages should not create that state.

## Compatibility Strategy

`sp-checklist` remains available for explicit requirement-quality checklist
generation. Its guidance should say it is optional and diagnostic, not part of
the default delivery path.

`sp-analyze` remains available for explicit read-only artifact diagnostics,
revalidation of existing projects, and compatibility with old task packages. Its
guidance should say it is optional and diagnostic, not the default
pre-implementation gate.

Hook and state-validation code should continue to understand `sp-analyze` so
existing generated projects remain recoverable. New templates and new docs should
prefer `tasks -> implement`.

## Affected Surfaces

- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`
- `templates/commands/checklist.md`
- `templates/commands/analyze.md`
- `templates/tasks-template.md`
- `templates/workflow-state-template.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- shared command partials for plan, tasks, implement, checklist, and analyze
- workflow boundary, state validation, preflight, prompt guard, and statusline
  hook code where default transitions or messages mention `analyze`
- README, PROJECT-HANDBOOK, generated project-map workflow guidance, and tests
  that assert the old default path

## Acceptance Criteria

- README and generated workflow guidance teach `plan -> tasks -> implement` as
  the normal post-planning path.
- `templates/commands/plan.md` default handoff no longer recommends checklist.
- `templates/commands/tasks.md` default handoff points to implement for clean
  task generation.
- `templates/commands/tasks.md` and `templates/tasks-template.md` rename the
  analyze-compatible self-audit into a built-in implementation-readiness gate.
- `templates/commands/implement.md` no longer instructs new projects to stop and
  run `sp-analyze` before implementation.
- New workflow-state defaults can represent a clean tasks-to-implement handoff.
- `sp-checklist` and `sp-analyze` remain present and documented as optional
  diagnostics or compatibility tools.
- Tests assert the new default path while retaining compatibility coverage for
  legacy `sp-analyze` state.

## Verification Plan

- Run focused template guidance tests covering alignment, tasks reporting, and
  README guidance.
- Run hook tests that cover workflow-state, preflight, session-state, and
  workflow-boundary behavior after the transition changes.
- Run integration or generated-asset tests that verify generated command
  handoffs render without `checklist` or `analyze` in the default path.
- Run the broader relevant test subset if shared state-validation or hook policy
  code changes.

## Risks

- Existing tests may encode the old workflow as desired behavior; they need to be
  updated carefully so compatibility expectations are not confused with default
  path expectations.
- Some old generated projects may still have `next_command: /sp.analyze`. The
  implementation must preserve readable recovery paths for these states.
- Moving checks upstream can create duplicate wording unless the task readiness
  gate is named clearly and old analyze-specific remediation language is removed
  from the default path.
