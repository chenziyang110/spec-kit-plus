---
name: spec-kit-project-learning
description: Use this skill whenever you discover reusable operational knowledge in a Spec Kit Plus repository, such as a repeated pitfall, recovery trick, user preference, project constraint, false lead, or tooling trap. It teaches when the memory system should trigger, what kind of learning to record, how to store it, and how to promote it into durable project memory without trapping it in one workflow run or chat session.
origin: spec-kit-plus
---

# Spec Kit Project Learning

This skill is about the memory system itself.

Its job is to teach an agent:

- when a run has discovered reusable knowledge,
- how that knowledge should be recorded,
- where it should live,
- when it should be promoted,
- and how future runs should benefit from it.

It is not a catalog of `sp-*` workflows. Other routing and workflow skills decide
which active workflow should run. This skill decides how reusable knowledge should be
captured and preserved once a run exposes it.

## Core Principle

Do not keep reusable operational knowledge in transient chat memory.

If a run uncovers something that would help later work avoid the same mistake, route
faster, recover earlier, or honor a repeated user/project constraint, that knowledge
should enter the shared memory system.

The user should not have to manually remind the agent to remember recurring pitfalls.
Memory capture is part of correct workflow execution.

## What Counts As Memory-Worthy Knowledge

Capture memory when the run exposes reusable knowledge such as:

- a repeated bug pattern or implementation trap
- a recovery sequence that repeatedly saves time
- a user correction that will matter again later
- a project constraint that affects multiple later tasks
- a tooling or environment trap that masquerades as an application bug
- a false lead pattern that wastes investigation time
- a validation gap that should change future execution
- a planning or workflow omission that keeps recurring
- a near miss that future runs should avoid

Good trigger heuristic:

- If future you would benefit from seeing this before starting a related task, it is memory-worthy.

## Memory Layers

Spec Kit Plus uses four layers:

1. **Principle Layer**: `.specify/memory/constitution.md`
   - Slow-changing MUST/SHOULD governance.

2. **Stable Rules**: `.specify/memory/project-rules.md`
   - Strong reusable project defaults and constraints.

3. **Confirmed Learnings**: `.specify/memory/project-learnings.md`
   - Confirmed reusable learnings that are important but not yet principle-level.

4. **Runtime Candidates**: `.planning/learnings/candidates.md` and `review.md`
   - Newly observed or still-noisy learnings awaiting confirmation or promotion.

## Learning Types

Use the smallest accurate type:

- `pitfall`: repeated implementation or testing trap
- `recovery_path`: repeatable recovery sequence
- `user_preference`: repeated user correction or preference
- `project_constraint`: reusable project constraint
- `workflow_gap`: repeated upstream omission
- `routing_mistake`: wrong workflow entry or route correction
- `verification_gap`: missing or broken validation path
- `state_surface_gap`: durable state failed to preserve needed context
- `map_coverage_gap`: handbook/project-map lacked needed truth
- `tooling_trap`: environment, shell, toolchain, watcher, or dev-surface trap
- `false_lead_pattern`: misleading diagnosis pattern
- `near_miss`: late-avoided risky path
- `decision_debt`: vague deferred decision that keeps causing downstream cost

## Required Behavior

### 1. Consume memory before deeper work

Before broad execution or diagnosis, the workflow should load shared memory first:

- constitution
- project rules
- project learnings
- relevant candidate learnings when they still matter

This should happen as part of workflow behavior. It should not depend on the user
explicitly asking for memory to be loaded.

### 2. Capture reusable knowledge during the run

When the run exposes reusable knowledge, record it.

Do not silently adapt local behavior and leave the lesson trapped in the current chat,
task file, or session transcript.

### 3. Review memory before terminal closeout

Before a workflow closes in a terminal state, it should either:

- capture the reusable learning, or
- explicitly record that no reusable learning exists and why

The closeout review exists to stop the same pitfall from being rediscovered endlessly.

### 4. Promote when the evidence is strong enough

Promotion rules:

- New or uncertain observations go to candidates.
- Confirmed reusable observations move to `project-learnings.md`.
- Stable cross-workflow defaults move to `project-rules.md`.

## Start-Time Memory Effects

Treat `learning start` as required preflight memory, not optional telemetry.

- Confirmed project rules and confirmed project learnings should surface as start-time warnings for later relevant work.
- Single high-signal candidates should still appear in start-time warnings so the next run does not rediscover the same issue from scratch.
- Repeated candidates, including repeated high-signal candidates, should auto-promote instead of staying stuck in the candidate layer forever.

Native hooks are an optional enhancement. Without native hooks, the shared
`{{specify-subcmd:learning start}}`, `{{specify-subcmd:hook review-learning}}`, and
`{{specify-subcmd:hook capture-learning}}` path must still execute correctly and preserve the
same memory guarantees.

## Command Surface

These are the memory-system primitives:

- `{{specify-subcmd:learning status}}`
- `{{specify-subcmd:learning start --command <command-name>}}`
- `{{specify-subcmd:learning capture --command <command-name> --type <type> --summary "..." --evidence "..."}}`
- `{{specify-subcmd:learning capture-auto --command <command-name> ...}}`
- `{{specify-subcmd:learning promote --recurrence-key <key> --target <learning|rule>}}`

## First-Party Learning Hooks

Use this hook surface when memory handling needs product-level enforcement or richer
signal capture:

- `{{specify-subcmd:hook signal-learning --command <command-name> ...}}`
- `{{specify-subcmd:hook review-learning --command <command-name> --terminal-status <status> ...}}`
- `{{specify-subcmd:hook capture-learning --command <command-name> --type <type> --summary "..." --evidence "..."}}`
- `{{specify-subcmd:hook inject-learning --command <command-name> --type <type> --summary "..."}}`

The terminal review-learning surface is intentionally narrow: use the real
`review-learning` helper shape above and do not add removed artifact-origin
helper options back into examples or generated guidance.

## When To Prefer Each Surface

- Use `learning start` to load and expose relevant memory before deeper work.
- Use `signal-learning` when friction signals suggest the run has memory value.
- Use `capture-learning` when you already know the reusable lesson and want to store it structurally.
- Use `capture-auto` when durable workflow state already contains enough evidence to infer the lesson.
- Use `review-learning` before terminal closeout so memory capture cannot be silently skipped.
- Use `promote` when recurrence or explicit confirmation justifies moving a learning into a stronger layer.

Typical durable-state sources include:

- `implement-tracker.md`
- quick-task `STATUS.md`
- debug session files
- `testing-state.md`
- `workflow-state.md` when it preserves route reasons, false starts, hidden dependencies, or reusable constraints

## Capture Heuristics

Capture when one or more of these happened:

- multiple retries were needed
- the hypothesis changed more than once
- validation failed repeatedly
- the user corrected the same kind of mistake again
- the agent followed a false lead before finding the real cause
- an environment/toolchain issue looked like a code bug
- the same project constraint had to be rediscovered
- a missing test or missing state surface caused preventable rework

If the run was painful, surprising, or repeatedly avoidable, it probably deserves memory.

## Promotion Heuristics

Promote to `project-learnings.md` when:

- the learning has recurred,
- or the evidence is already strong and cross-stage useful,
- or the user explicitly confirmed it should be remembered.

Promote to `project-rules.md` when:

- it is a stable default,
- it should shape many later workflows,
- and violating it would predictably create repeated cost.

## Injection Goal

The memory system is not complete when a lesson is merely stored.

The lesson should influence future work by being surfaced at the right time:

- before related execution starts,
- before the same route mistake repeats,
- before the same tooling trap gets misdiagnosed,
- or before the same project constraint is forgotten.

That is why `inject-learning` exists: to route prevention back into the right shared
surface.

## Behavioral Rules

- **Do NOT** wait for the user to explicitly say “remember this” when the run clearly exposed reusable knowledge.
- **Do NOT** trap durable lessons in chat history, task-local notes, or one workflow artifact.
- **Do NOT** write everything into `constitution.md`.
- **Do NOT** leave repeated high-signal findings stuck in the candidate layer forever.
- **Do NOT** close a terminal workflow without either captured memory or an explicit review rationale.
- Keep `project-rules.md` stricter than `project-learnings.md`.
