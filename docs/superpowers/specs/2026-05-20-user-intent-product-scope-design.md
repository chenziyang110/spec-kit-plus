# User-Intent Product Scope Design

Date: 2026-05-20
Status: Design approved in conversation; pending written-spec review

## Goal

Remove workflow bias toward default product minimization across the
`spec-kit-plus` generated workflow stack.

The workflows should preserve and implement the user's intended product shape.
They may clarify, sequence, de-risk, and verify that intent, but they must not
steer a user toward a smaller validation build, MVP-style slice, prototype, or
first-story release unless the user explicitly asks for that, the request itself
is framed that way, or a hard planning constraint requires a user-confirmed
scope decision.

The core product rule is:

> Scope belongs to the user. The workflow should help find the best
> implementation path for the user's intended product, not quietly convert the
> request into the smallest viable thing.

## Problem Statement

The current workflow text already contains an explicit guard against treating
MVP minimization as the default strategy. However, several generated workflow
surfaces still use phrases that can lead an agent to behave as though smaller
is better by default.

Examples include:

- `Minimal viable path` in the discussion technical options board
- `smallest coherent release slice` in task reporting guidance
- `User Story 1 ... First Release Candidate` in the shared tasks template
- `Release/Demo if ready` after the first user story
- "smallest safe route" language in workflow routing guidance, which is valid
  for command selection but can be misread as product-scope minimization

The failure mode is subtle. The workflow may not literally say "build an MVP",
but it can still nudge the downstream agent to ask, "What is the smallest thing
we can do first?" instead of, "What does the user actually want, and what is the
best product-quality way to deliver it?"

That is not the desired behavior for `spec-kit-plus`.

## Product Principle

The workflow should be user-intent preserving.

That means:

- Start from the user's desired product, capability, workflow, or business
  outcome.
- Clarify unclear scope without proposing smaller scope as the default answer.
- Treat scope reduction as a user decision, not an agent optimization.
- Plan the best implementation path for the intended product shape.
- Preserve quality, testing, compatibility, operations, error handling, data,
  security, and user experience obligations appropriate to the selected scope.
- Allow phased delivery only when it reflects user intent, an explicitly chosen
  delivery strategy, or a real constraint that has been named and accepted.

This does not mean every request must become the entire long-term product
vision. It means the workflow must not invent a smaller release strategy merely
because a smaller path is easier to plan or implement.

## Scope

This design covers wording and behavioral contracts for:

- `sp-discussion`
- `sp-specify`
- `sp-clarify`
- `sp-deep-research`
- `sp-plan`
- `sp-tasks`
- passive workflow routing guidance
- shared spec, plan, and tasks templates
- tests that guard generated workflow wording
- README and handbook guidance when they describe the generated user workflow

This design does not cover:

- forbidding phased delivery when the user asks for it
- forbidding prototypes, demos, pilots, or research spikes when they are
  explicitly requested or required as feasibility proof
- changing implementation quality gates into heavier process for every task
- removing lightweight workflows such as `sp-fast` or `sp-quick` for genuinely
  small user requests
- making every generated spec include an entire product roadmap

## Required Behavioral Contract

### Discussion

`sp-discussion` should discuss the user's product idea without biasing the user
toward a smaller validation build.

When implementation strategy affects requirements, the technical options board
should compare implementation paths that preserve the user's intended product
outcome. A minimal option may be included only when it is clearly user-requested
or presented as a trade-off requiring user choice.

Recommended option framing:

- `User-intent-aligned path`: the best path for the user's stated product goal
  under current constraints.
- `Architecture-correct path`: the path that best fits existing boundaries,
  maintainability, and long-term change.
- `Expansion-ready path`: the path that supports plausible future variants or
  scale when those are relevant to the user's goal.

The options board may still discuss de-scoping, rollback, phased rollout, or
proof work, but these should be risk-management tools, not default scope
selection.

### Specify

`sp-specify` should lock the user's intended product shape before planning. It
should ask clarification questions when scope is unclear, but it should not ask
questions that imply "should we make this smaller first?" unless there is an
actual scope conflict, planning blocker, or user signal.

The existing anti-MVP rule should be strengthened into a broader product-scope
contract:

- Do not treat product minimization as the default strategy.
- Do not convert the request into a smaller first release unless the user asks
  for that or confirms it after seeing the trade-off.
- Record user-confirmed scope, user-confirmed deferrals, and non-goals.
- When constraints require reducing scope, present the constraint and ask for a
  user decision.

### Clarify

`sp-clarify` should repair ambiguity without reopening scope in a smaller
direction by default.

Clarification questions should lock behavior, boundaries, compatibility,
acceptance proof, and planning-critical decisions. They should not use
minimization as a shortcut to resolve ambiguity.

### Deep Research

`sp-deep-research` remains a feasibility and evidence workflow. Disposable demos
and research spikes are valid only as proof mechanisms for an intended
capability, not as a default product replacement.

Research output should preserve the user's product goal and report whether the
implementation chain is credible. If research suggests a smaller or staged path,
that must be framed as a decision for the user or planner to accept, with risks
and trade-offs.

### Plan

`sp-plan` should design the best implementation approach for the confirmed
scope. It may sequence work, identify dependencies, and create architecture
phases, but it must not reinterpret the confirmed product scope as a smaller
release.

`quickstart.md` should validate the feature end-to-end through a representative
integration scenario. It should not be described as validating the smallest
possible scenario unless the feature scope itself is small.

### Tasks

`sp-tasks` should generate implementation tasks for the confirmed scope.

User stories may remain independently testable and priority-ordered, but the
template should not imply that User Story 1 is automatically the first release
candidate. A first release, demo, pilot, or staged delivery boundary should be
derived from confirmed scope and user-approved sequencing.

Task summaries should report "confirmed delivery scope" or "user-confirmed
delivery sequence" rather than "suggested first release scope" based on the
smallest coherent slice.

### Passive Routing

Workflow routing may still recommend the lightest safe command path for the
work the user actually asked for. That is a workflow-selection rule, not a
product-scope rule.

Routing guidance should explicitly distinguish:

- "smallest safe workflow" for choosing a command surface
- "user-confirmed product scope" for deciding what the feature should become

This prevents small-workflow guidance from leaking into product strategy.

## Scope Reduction Policy

The generated workflows may recommend or record reduced scope only when at
least one of these conditions is true:

1. The user explicitly asks for a smaller version, MVP, prototype, pilot,
   experiment, demo, proof of concept, or staged release.
2. The input requirement already defines a limited phase or release boundary.
3. A real constraint blocks reliable planning or implementation of the stated
   scope, and the workflow asks the user to choose how to adjust scope.
4. A feasibility proof is needed before planning, and the reduced artifact is
   clearly labeled as proof work rather than the product target.
5. The user approves a delivery sequence after seeing the trade-offs.

When none of these conditions is true, the workflows should preserve the stated
product scope and plan toward it.

## Language Changes

Avoid workflow phrases that imply default product minimization:

- `MVP first`
- `suggested MVP scope`
- `minimal viable path`
- `smallest coherent release slice`
- `first story release`
- `User Story 1 ... First Release Candidate`
- `Release/Demo if ready` immediately after User Story 1
- `smallest integration scenario` when describing product validation

Prefer phrases that preserve user intent:

- `user-intent-aligned path`
- `confirmed product scope`
- `confirmed delivery scope`
- `user-confirmed delivery sequence`
- `product-complete path for the selected scope`
- `representative end-to-end validation scenario`
- `scope reduction requires user confirmation`
- `deferrals must be user-confirmed or constraint-driven`

The implementation should update tests so these terms become durable regression
guards in generated workflow templates.

## Affected Surfaces

Expected implementation surfaces:

- `templates/commands/discussion.md`
- `templates/commands/specify.md`
- `templates/commands/clarify.md`
- `templates/commands/deep-research.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/spec-template.md`
- `templates/plan-template.md`
- `templates/tasks-template.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- related passive skills that mirror workflow routing, TDD, task shaping, or
  verification wording
- `tests/test_alignment_templates.py`
- integration or extension tests that assert generated command/skill wording
- README and handbook sections that teach generated workflow behavior

The implementation should search before editing:

```text
rg -n -i "MVP|minimum viable|minimal viable|smallest coherent|first release candidate|first-release scope|first release scope|Release/Demo|de-scope|smaller release|smallest integration scenario|User Story 1.*First Release" templates src scripts tests README.md PROJECT-HANDBOOK.md docs
```

## Testing Strategy

Tests should verify:

- generated command templates do not contain `minimal viable path`
- generated command templates do not contain `smallest coherent release slice`
- generated task templates do not describe User Story 1 as the automatic first
  release candidate
- generated task templates do not tell the agent to release or demo immediately
  after User Story 1 unless user-confirmed sequencing exists
- `sp-specify` contains a strong no-default-minimization rule
- `sp-discussion` technical options use user-intent-preserving labels
- `sp-plan` quickstart guidance uses representative end-to-end validation
  language
- routing guidance distinguishes command-surface minimization from product
  scope
- docs teach that scope reduction must be user-confirmed or constraint-driven

Tests should preserve the existing useful rule that clean workflow progress
still follows the canonical generated path:

```text
sp-specify -> sp-plan -> sp-tasks -> sp-implement
```

This design changes scope semantics, not the default workflow backbone.

## Acceptance Criteria

The change is complete when:

- downstream generated workflows no longer steer users toward MVP or smallest
  viable delivery by default
- discussion and specification stages preserve the user's intended product
  shape
- phased delivery appears only as a user-confirmed strategy, an explicit input
  shape, or a constraint-driven decision
- tasks are generated for confirmed scope rather than for an automatically
  minimized first release
- tests guard against reintroducing minimization language
- docs explain that the workflow optimizes implementation quality for user
  intent, not product scope reduction

## Open Implementation Notes

The implementation should avoid turning this into a broad wording-only cleanup.
The important behavior is not just replacing phrases. The templates must also
change the decision contract so agents know when they are allowed to propose or
record reduced scope.

Where the workflow still needs to talk about smaller artifacts, such as research
spikes, representative validation, rollback, or command routing, the text should
name the reason and boundary explicitly so agents do not mistake that guidance
for product strategy.
