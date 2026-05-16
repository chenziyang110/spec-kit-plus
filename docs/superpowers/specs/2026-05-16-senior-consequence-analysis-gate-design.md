# Senior Consequence Analysis Gate Design

## Summary

Add a shared **Senior Consequence Analysis Gate** across the primary entry and shaping workflows: `sp-discussion`, `sp-specify`, `sp-plan`, `sp-tasks`, `sp-fast`, `sp-quick`, and `sp-debug`. Adjacent workflows such as `sp-clarify`, `sp-deep-research`, `sp-analyze`, and `sp-implement` consume or preserve the same obligations where they already participate in the mainline.

The goal is to make generated workflows reason like a senior product manager and technical maintainer who has lived with the project for years. When a user asks for a capability such as "close a team", the workflow must not treat it as a one-line action. It must identify affected objects, current states, running work, upstream and downstream dependencies, failure behavior, recovery paths, and verification obligations before it claims the request is ready for the next workflow.

Project cognition remains the evidence base for ownership, consumers, shared surfaces, state surfaces, verification routes, conflicts, and known unknowns. The new gate consumes project cognition and turns it into a concrete consequence model. If project cognition does not encode enough lifecycle or control-state semantics, the workflow records a coverage gap and uses minimal live reads or routes to map maintenance according to the workflow's risk level.

This is a cross-workflow contract change, not a single integration tweak.

## Goals

- Make workflow agents proactively analyze dependency relationships, lifecycle states, running work, destructive operations, and downstream impact.
- Prevent vague outputs such as "consider dependencies" from passing as complete analysis.
- Ensure consequence analysis is preserved across `discussion -> specify -> plan -> tasks` instead of being rediscovered or dropped.
- Make `sp-fast`, `sp-quick`, and `sp-debug` use the same senior-maintainer lens for direct work and bug investigation.
- Use project cognition as the required evidence base without pretending it can fully infer product and runtime semantics by itself.
- Surface project cognition coverage gaps when lifecycle, control-state, or destructive-operation semantics are not encoded.
- Keep each workflow's responsibility distinct: discussion discovers, specify locks requirements, plan designs operations, tasks preserves execution obligations, fast/quick route safely, and debug proves root cause through the dependency loop.

## Non-Goals

- Do not implement source-code behavior as part of this design.
- Do not redesign the project cognition database schema in the first increment.
- Do not make `sp-map-build` alone responsible for product and lifecycle decisions.
- Do not add a new user-facing workflow command.
- Do not add heavyweight planning artifacts to `sp-fast`.
- Do not require every small text or docs change to run the full consequence gate.
- Do not make the design Codex-only.

## Current Context

The current workflows already have pieces of this behavior:

- `sp-discussion` has product and technical roles, project cognition gating, and a technical options board.
- `sp-specify` has fixed heavy discovery domains, including failure paths and dependencies.
- `sp-plan` consumes aligned specs and can add implementation constitution, research, data model, contracts, and quickstart artifacts.
- `sp-tasks` already generates dependency-aware tasks, write-set-aware parallel batches, guardrails, join points, and task packets.
- `sp-fast` and `sp-quick` already route away from unsafe direct work.
- `sp-debug` already distinguishes truth ownership, control state, observation state, closed loops, and related-risk review.
- `sp-map-build` publishes a query-backed project cognition runtime with nodes, edges, claims, conflicts, ownership, consumers, change propagation, and verification routes.

The gap is consistency and concreteness. The workflows can still treat a deceptively small feature as a local change without forcing a state-by-state analysis. They can also consume project cognition as context without proving that its facts shaped the artifact or execution state.

For example, "add a close team feature" must trigger questions and decisions such as:

- What happens to queued tasks?
- What happens to running workers?
- Are new tasks admitted while close is pending?
- Does close drain, cancel, detach, block, or force-kill workers?
- What happens if a worker submits a result while close is in progress?
- Is close idempotent after process interruption?
- What does `resume`, `await`, `cleanup`, `status`, and MCP status show?
- Which tests prove stale heartbeat, late result, double close, force close, and interrupted close behavior?

Those are not optional implementation details. They shape the product behavior, implementation design, task decomposition, and verification strategy.

## Core Concept

The shared gate has two steps:

```text
Project Cognition First -> Senior Consequence Analysis Second
```

### Step 1: Project Cognition First

When existing-system truth matters, the workflow must query project cognition before broad source inspection and before completing the current stage.

Consequence analysis can still trigger when project cognition is missing or not applicable, especially for new lifecycle semantics, destructive behavior, or greenfield product decisions. Project cognition is required when existing-system truth, consumers, state surfaces, ownership, verification routes, or change-propagation risk matter; it is not a prerequisite for recognizing that a request needs consequence analysis.

Relevant project cognition facts include:

- ownership and truth owners
- direct and indirect consumers
- state surfaces
- workflow, command, API, MCP, hook, template, or contract boundaries
- change-propagation hotspots
- verification entry points
- known unknowns
- conflicts and low-confidence claims
- minimal live reads

A project-cognition query is complete only when readiness drives routing, `minimal_live_reads` constrains inspection, and relevant facts are carried into the next workflow artifact or execution state.

### Step 2: Senior Consequence Analysis Second

If the request triggers the gate, the workflow must produce a concrete consequence model:

1. **Affected Object Map**
   - Names every meaningful object, state surface, user role, command, workflow, artifact, process, queue, result, or external dependency affected by the change.

2. **State-Behavior Matrix**
   - Names the important existing or proposed states and the expected behavior in each state.
   - For lifecycle features, this includes idle, active, running, queued, blocked, failed, partial, interrupted, stale, and completed states when relevant.

3. **Dependency Impact Table**
   - Names upstream callers, downstream consumers, adjacent workflows, background processes, data contracts, and verification surfaces affected by the decision.

4. **Recovery And Validation Contract**
   - Defines failure behavior, idempotency, retry, rollback or de-scope path, user-visible error behavior, observability, and the evidence required to prove correctness.

5. **Coverage Gaps**
   - Records what project cognition or minimal live reads could not establish, why it matters, and whether the current workflow may continue with an assumption, must ask the user, must route to clarification, or must request map maintenance.

## Trigger Conditions

The gate triggers when the request or discovered scope involves any of:

- lifecycle operations: create, start, stop, close, delete, archive, resume, retry, cleanup
- concurrent or running objects: running workers, claimed tasks, executing batches, active sessions, open transactions, pending jobs
- destructive or hard-to-reverse actions: delete, reset, cleanup, force, close, revoke, terminate
- shared state: queues, locks, leases, heartbeats, result stores, mailboxes, state files, indexes, registries
- upstream or downstream contracts: CLI, API, MCP, hooks, templates, generated artifacts, worker packets, protocol seams
- user-visible failure paths: timeout, partial success, permission denial, stale state, unavailable external service, inconsistent projections
- compatibility or migration concerns: existing projects, old state files, prior workflow artifacts, active sessions, generated command surfaces
- security, permission, billing, data retention, or audit implications
- multiple plausible behaviors where the choice changes product semantics or implementation shape

The gate may stand down for docs-only wording changes, trivial isolated fixes, or local refactors when the workflow records why no lifecycle, running-state, shared-surface, destructive-operation, or consumer-impact trigger applies.

## Example: Close Team

For a team runtime, the analysis might produce:

### Affected Object Map

- team phase
- worker roster
- task queue
- claimed tasks
- running worker processes
- worker heartbeat files
- result files
- mailboxes
- dispatch state
- events log
- `status`, `await`, `resume`, `cleanup`, `submit-result`, and MCP status surfaces

### State-Behavior Matrix

| State | Expected Close Behavior |
| --- | --- |
| `idle` | Close immediately and record `closed`. |
| `queued_tasks` | Stop admission, mark unstarted tasks as cancelled or blocked according to selected policy. |
| `running_workers` | Default to drain; wait for active workers to finish or reach timeout. |
| `submitting_result` | Allow result flush to complete or record a recoverable close blocker. |
| `stale_heartbeat` | Mark worker lost before deciding whether remaining work is blocked or cancelled. |
| `partial_failure` | Enter `closing_blocked`, preserve recovery action, and keep close idempotent. |
| `force_close_requested` | Require explicit destructive confirmation and record cancelled work. |

### Dependency Impact Table

| Surface | Impact |
| --- | --- |
| `resume` | Must not duplicate workers when a close is in progress. |
| `await` | Must distinguish dispatch completion from close completion. |
| `cleanup` | Must not remove state before shutdown settles. |
| `submit-result` | Must define late-result behavior during and after close. |
| MCP status | Must report `closing`, `closing_blocked`, and `closed` accurately. |
| events log | Must preserve audit and recovery evidence. |

### Recovery And Validation Contract

- Close is idempotent after interruption.
- New tasks are rejected once close begins.
- Running worker drain and timeout behavior are tested.
- Late result policy is tested.
- Stale heartbeat handling is tested.
- Double close does not corrupt state.
- Cleanup before close completion is blocked or clearly safe.

## Workflow Responsibilities

### `sp-discussion`

`sp-discussion` discovers consequence shape before formal specification.

Add a **Senior Maintainer Review** stage before technical options are finalized and before handoff assessment. The stage asks one high-impact question at a time when user decisions are needed, but it may propose senior defaults when the project evidence strongly suggests a safe path.

Artifacts:

- `requirements.md`: user-visible behavior, state rules, scope, non-goals, and acceptance signals
- `technical-options.md`: 2-3 concrete handling strategies with trade-offs, such as block, drain, cancel, detach, force, or defer
- `project-context.md`: project cognition facts, minimal live reads, inference notes, and coverage gaps
- `open-questions.md`: user decisions that materially affect behavior or implementation
- `handoff-to-specify.md`: user-reviewable must-preserve consequence items for `sp-specify`
- `handoff-to-specify.json`: machine-readable mirror of consequence obligations, state behavior, dependency impact, coverage gaps, and stop-and-reopen conditions
- `handoffs/CAND-###-handoff-to-specify.md`: candidate-specific consequence obligations when split mode selects one candidate from a larger discussion
- `handoffs/CAND-###-handoff-to-specify.json`: canonical candidate JSON mirror; the legacy latest `handoff-to-specify.md` and `handoff-to-specify.json` copies must refresh together when the selected candidate changes

Blocking rule:

- If the gate triggers and no concrete state-behavior matrix or dependency impact analysis exists, `sp-discussion` must not mark the discussion `handoff-ready`.
- If split mode is active, the selected candidate handoff must include only consequence obligations that shape that candidate plus dependency, non-goal, or deferred-sibling obligations needed to prevent scope drift.
- Markdown and JSON handoffs must agree on consequence obligation IDs, claims, blocking level, owner, latest resolve phase, and status. `sp-specify` must block or record a handoff repair advisory according to the existing handoff integrity rules rather than silently choosing one representation.

### `sp-specify`

`sp-specify` turns consequence analysis into planning-ready requirements.

Add a **Consequence Completeness Gate** after project cognition intake and before final alignment release.

Artifacts:

- `spec.md`: lifecycle states, user-visible behavior per state, failure semantics, non-goals, acceptance signals
- `alignment.md`: confirmed, inferred, unresolved, and force-carried consequence decisions
- `context.md`: affected objects, dependencies, state surfaces, project cognition evidence, coverage gaps, and downstream planning implications
- `references.md`: project cognition query, minimal live reads, discussion handoff, and source evidence
- `brainstorming/handoff-to-specify.json`: consequence obligations, state behavior, coverage gaps, stop-and-reopen conditions

Blocking rule:

- If lifecycle, destructive, running-state, or shared-state semantics materially affect planning and remain unresolved, `sp-specify` must not release `Aligned: ready for plan`.
- If the missing decision can be safely resolved by evidence, record it. If it requires user choice, ask. If requirements are clear but implementation feasibility remains unproven, route to `sp-deep-research`.

### `sp-plan`

`sp-plan` turns requirement-level consequence semantics into an implementation strategy.

Add an **Operational Consequence Design** section to planning synthesis.

Artifacts:

- `plan.md`: operational state machine, ordering, locking or lease behavior, idempotency, concurrency hazards, recovery path, observability, rollout, and verification strategy
- `research.md`: external or repository evidence needed for consequential implementation decisions
- `data-model.md`: required when states, events, persistence fields, retention rules, or recovery metadata change
- `contracts/`: required when CLI, API, MCP, protocol, or generated artifact contracts change
- `plan-contract.json`: consequence obligations and planning decisions that `sp-tasks` must preserve

Blocking rule:

- If `spec.md`, `alignment.md`, or `context.md` requires handling running, queued, failed, stale, partial, or destructive states, `sp-plan` must define how implementation handles them before handing off to `sp-tasks`.
- A plan that says only "implement close team" without close ordering, worker/result interactions, idempotency, and validation is incomplete.

### `sp-tasks`

`sp-tasks` ensures consequence decisions survive task decomposition.

Add **Consequence Obligation Mapping** to task generation.

Each relevant task, packet, or join point must include:

- objective
- write set
- affected state or dependency
- required references
- forbidden drift
- validation command or manual check
- done condition
- stop-and-reopen condition

Artifacts:

- `tasks.md`: consequence guardrail index, state/dependency task mapping, join points, validation notes
- `task-index.json`: task-to-obligation mapping when generated
- `task-packets/*.json`: per-task consequence obligations for implementers
- `handoff-to-tasks.json`: carried consequence obligations and stop-and-reopen conditions

Blocking rule:

- If `plan.md` contains lifecycle, dependency, or operational decisions and `tasks.md` does not map them to tasks, guardrails, checkpoints, or explicit deferrals, task generation must not complete normally.

### `sp-fast`

`sp-fast` uses the gate primarily as an upgrade trigger.

Rules:

- If the gate triggers, route to `sp-quick` or `sp-specify` unless the workflow can prove the change has no running-state, lifecycle, shared-state, destructive-operation, or consumer impact.
- Do not add planning artifacts to satisfy the gate on the fast path.
- Record the stand-down reason in the final report when staying on fast after a potential trigger.

### `sp-quick`

`sp-quick` may handle small bounded consequence work, but only with durable state.

Add consequence fields to `STATUS.md`:

- affected_objects
- state_behavior_matrix
- dependency_impact
- recovery_and_validation
- project_cognition_evidence
- coverage_gaps
- escalation_decision

Rules:

- Continue in quick only when the consequence model is bounded, implementation can fit one quick workspace, and validation evidence is concrete.
- Escalate to `sp-specify` when the change needs a durable feature contract, user-level lifecycle decisions, broad compatibility handling, or multi-capability scope.
- Escalate to `sp-debug` when the task is a bug/regression and root cause is unknown.

### `sp-debug`

`sp-debug` uses the same model for failure investigation.

Rules:

- Use project cognition to identify truth owners, state surfaces, consumers, verification routes, and known unknowns.
- Preserve control state vs observation state.
- Trace the dependency loop from input event to control decision to resource allocation to state transition to external observation.
- Identify adjacent risk targets affected by the same control-state dependency.
- Reject surface-only fixes that hide symptoms without restoring the owning loop.

Artifacts:

- debug session file: affected objects, dependency loop, control/observation state, candidate queue, root-cause evidence, adjacent risk targets
- result evidence: loop restoration proof and related-risk review

## Adjacent Workflows

The first increment does not make every adjacent workflow a producer of new consequence analysis, but it must prevent consequence obligations from being dropped after the primary workflows create them.

### `sp-clarify`

`sp-clarify` is a repair and deepening lane for specification ambiguity. When it receives an unresolved consequence gap from `sp-specify`, it must preserve the gap, ask or resolve the blocking decision, and update the same requirement-level artifacts rather than creating a parallel truth source.

Responsibilities:

- consume unresolved lifecycle, destructive-operation, dependency, or state-behavior gaps from `alignment.md`, `context.md`, and `brainstorming/handoff-to-specify.json`
- resolve them by user decision or evidence-backed clarification
- return the clarified consequence decisions to the canonical `sp-specify` artifact set

### `sp-deep-research`

`sp-deep-research` proves implementation-chain feasibility when requirements are clear but consequence-sensitive implementation choices need evidence.

Responsibilities:

- preserve consequence questions as research tracks when they depend on external tools, platform behavior, runtime libraries, or disposable demos
- include consequence-sensitive findings in the planning handoff
- keep residual risks and unproven chains traceable so `sp-plan` cannot weaken them into generic assumptions

### `sp-analyze`

`sp-analyze` is a downstream consistency gate before implementation. It should not create the first consequence model, but it must verify that task-generation artifacts preserved one.

Responsibilities:

- check that `tasks.md`, `handoff-to-tasks.json`, `task-index.json`, and task packets retain consequence obligations from `plan.md` and `plan-contract.json`
- block when lifecycle, dependency, state, recovery, validation, or stop-and-reopen obligations were dropped during task generation
- route back to `sp-tasks`, `sp-plan`, `sp-clarify`, or `sp-deep-research` depending on where the missing truth belongs

### `sp-implement`

`sp-implement` consumes the consequence obligations in task packets. It must not reinterpret or drop them during execution.

Responsibilities:

- ensure implementation lanes inherit task-level affected states, dependency guardrails, required references, validation commands, done conditions, and stop-and-reopen conditions
- stop and reopen upstream when an implementation lane discovers that a preserved consequence obligation is wrong, incomplete, or impossible under repository evidence
- include completion evidence proving the relevant obligation was honored, deferred under an approved condition, or returned upstream

## Project Cognition Relationship

`sp-map-build` is necessary but not sufficient.

It can support dependency analysis through:

- graph nodes and edges
- claims and conflicts
- ownership and truth-layer claims
- consumer and change-propagation facts
- verification routes
- queryable task-local bundles
- known unknowns and confidence

It cannot, by itself, fully decide product semantics such as whether a running worker should be drained, cancelled, detached, or force-killed during team close. Those choices require workflow-level consequence analysis and sometimes user decisions.

First increment:

- Strengthen workflow consumption of project cognition.
- Require workflows to record coverage gaps when lifecycle/control-state semantics are missing.
- Use minimal live reads when project cognition points to the right surfaces but does not answer the semantic question.
- Route to map maintenance only when the baseline is missing, stale, too weak for the touched area, or cannot safely bound the changed closure.

Future increment:

- Extend `sp-map-scan -> sp-map-build` to capture richer runtime semantics:
  - lifecycle states
  - control state vs observation state
  - queues, admission, claims, leases, heartbeats, result flows
  - destructive command semantics
  - recovery and resume paths
  - concurrent operation hazards
  - existing behavior claims for close/delete/archive/cleanup/force

## Template And Artifact Surface

Implementation should update these shared workflow templates:

- `templates/commands/discussion.md`
- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/fast.md`
- `templates/commands/quick.md`
- `templates/commands/debug.md`
- `templates/commands/clarify.md`
- `templates/commands/deep-research.md`
- `templates/commands/analyze.md`
- `templates/commands/implement.md`

The corresponding command partials should stay aligned with the command templates:

- `templates/command-partials/discussion/shell.md`
- `templates/command-partials/specify/shell.md`
- `templates/command-partials/plan/shell.md`
- `templates/command-partials/tasks/shell.md`
- `templates/command-partials/fast/shell.md`
- `templates/command-partials/quick/shell.md`
- `templates/command-partials/debug/shell.md`

Artifact templates should be updated where they carry workflow truth:

- `templates/discussion-state-template.md`
- `templates/spec-template.md`
- `templates/alignment-template.md`
- `templates/context-template.md`
- `templates/references-template.md`
- `templates/plan-template.md`
- `templates/tasks-template.md`
- `templates/brainstorming-handoff-specify-template.json`
- `templates/plan-contract-template.json`
- `templates/task-index-template.json`
- `templates/task-packet-template.json`
- `templates/implement-execution-state-template.json`
- `templates/debug.md`

Documentation surfaces should explain the new model:

- `README.md`
- `docs/quickstart.md`
- `PROJECT-HANDBOOK.md`
- `templates/project-handbook-template.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`

If the implementation changes generated workflow behavior across integrations, integration rendering tests should confirm the same contract appears in Markdown, TOML, and skills-based outputs.

## Enforcement Model

The word "cannot" in this design means two enforcement layers, depending on the artifact surface.

Prompt-contract enforcement applies where the workflow output is primarily Markdown or natural-language artifact synthesis. The command template must contain explicit blocking language, and template tests must assert that the gate, required sections, and routing rules exist. This prevents the generated workflow contract from omitting the behavior, but it still relies on the agent following the prompt.

Structured artifact enforcement applies where JSON or durable machine-readable state already exists. The implementation should add or extend validation for:

- discussion handoff JSON and candidate handoff JSON when consequence obligations are present
- `FEATURE_DIR/brainstorming/handoff-to-specify.json`
- `plan-contract.json`
- `handoff-to-tasks.json`
- `task-index.json`
- `task-packets/*.json`
- quick-task `STATUS.md` fields when the quick workspace contract is generated or checked
- debug session fields when the debug workflow validates observer/root-cause state

Structured validation should reject or block readiness when required consequence obligation fields are missing, contradictory, unmapped, or marked complete without evidence. Where no validator exists yet, the first increment should at least add template assertions and name the validation follow-up explicitly.

## Testing Strategy

Add template-level tests that assert the contract exists and is propagated.

Tests should verify:

- `discussion.md` contains `Senior Maintainer Review`, `Affected Object Map`, `State-Behavior Matrix`, `Dependency Impact Table`, `Recovery And Validation Contract`, handoff blocking language, JSON companion coverage, and candidate handoff coverage.
- `specify.md` contains `Consequence Completeness Gate` and blocks planning readiness when lifecycle, destructive, running-state, or shared-state semantics remain unresolved.
- `plan.md` contains `Operational Consequence Design` and requires state machine, ordering, concurrency, idempotency, recovery, and validation strategy.
- `tasks.md` contains `Consequence Obligation Mapping`, task-to-obligation mapping, state/dependency guardrails, and join point validation.
- `fast.md` treats consequence triggers as upgrade triggers unless a stand-down reason is recorded.
- `quick.md` adds consequence fields to the `STATUS.md` template and escalation rules.
- `debug.md` preserves control state, observation state, dependency loop, adjacent risk targets, and rejection of surface-only fixes.
- `spec-template.md`, `alignment-template.md`, `context-template.md`, `plan-template.md`, and `tasks-template.md` have fields or sections where consequence analysis can be preserved.
- `references-template.md`, `plan-contract-template.json`, `task-index-template.json`, and `task-packet-template.json` can carry consequence evidence, obligations, and stop-and-reopen conditions.
- `analyze.md` and `implement.md` consume consequence obligations without dropping task-packet guardrails.
- structured validators or contract tests reject missing consequence obligation fields where JSON or durable state exists.
- Docs explain that project cognition supports dependency analysis but does not replace the senior consequence gate.

Regression tests should also ensure the new language does not weaken existing project cognition rules, subagent dispatch rules, TDD gates, analyze gates, or discussion handoff fidelity.

## Acceptance Criteria

- A request such as "add a close team feature" naturally produces a state-aware analysis instead of a surface action.
- `sp-discussion` cannot hand off a lifecycle or destructive feature without affected objects, state behavior, dependency impact, and recovery/validation analysis.
- `sp-specify` cannot mark the package `Aligned: ready for plan` while planning-critical lifecycle or dependency semantics remain unresolved.
- `sp-plan` must define operational design details for lifecycle and running-state behavior before `sp-tasks`.
- `sp-tasks` must map operational consequence decisions to tasks, guardrails, packets, validation, or explicit deferrals.
- `sp-fast` upgrades when the work is no longer truly local and consequence-free.
- `sp-quick` records bounded consequence analysis in durable state or escalates.
- `sp-debug` traces failures through dependency loops and rejects surface-only fixes.
- Project cognition query results are consumed in artifacts or execution state, not merely read.
- Coverage gaps are explicit when project cognition cannot support lifecycle or control-state conclusions.

## Risks And Mitigations

- Risk: The gate becomes a verbose checklist that agents fill mechanically.
  Mitigation: Require concrete state rows, dependency entries, recovery behavior, and validation evidence. Empty or generic entries block progression.

- Risk: Small work is over-escalated.
  Mitigation: Allow explicit stand-down when no trigger applies or when `sp-fast` can prove locality and no consumer impact.

- Risk: Project cognition is treated as omniscient.
  Mitigation: Require coverage gap recording and minimal live reads when lifecycle semantics are not encoded.

- Risk: Artifacts become noisy.
  Mitigation: Include consequence sections only when the gate triggers, and keep entries tied to decisions that affect behavior, planning, tasking, or verification.

- Risk: Workflows duplicate the same content.
  Mitigation: Each workflow owns a different abstraction level: discovery, requirement contract, implementation strategy, executable guardrails, direct-work routing, or debug proof.

## Rollout Notes

The first implementation should change guidance and artifact templates, with tests proving cross-workflow propagation. It should not attempt a project cognition schema redesign.

After the workflow gate is stable, a follow-up design can extend `sp-map-scan` and `sp-map-build` so the cognition runtime directly models lifecycle states, control flows, destructive command semantics, recovery paths, and concurrent hazards.
