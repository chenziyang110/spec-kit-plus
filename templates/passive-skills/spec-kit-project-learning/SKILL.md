---
name: spec-kit-project-learning
description: Use this skill whenever you discover reusable operational knowledge in a Spec Kit Plus repository, such as a repeated pitfall, recovery trick, user preference, project constraint, false lead, or tooling trap. It teaches when the memory system should trigger, what kind of learning to record, how to store it, and how to promote it into durable project memory without trapping it in one workflow run or chat session.
origin: spec-kit-plus
---

# Spec Kit Project Learning

This skill is about the memory system itself.

It is not a catalog of `sp-*` workflows. Other routing and workflow skills decide
which active workflow should run. This skill decides when reusable engineering
judgment should be captured, where it should live, and how future runs should
benefit from it.

## Project Memory And Reusable Engineering Judgment

Do not keep reusable operational knowledge in transient chat memory.

If a run uncovers something that would help later work avoid the same mistake,
route faster, recover earlier, or honor a repeated user/project constraint, that
knowledge should enter shared project memory. The user should not have to
manually remind the agent to remember recurring pitfalls.

Memory capture is part of correct workflow execution. It should preserve concise
index-level discoverability plus one detailed markdown document per lesson when
the lesson has enough evidence to help future work.

## Learning Reflex

Before final closeout, ask whether a future senior engineer would benefit from
seeing this lesson before related work.

If yes, update `.specify/memory/learnings/INDEX.md` and the lesson detail
document. Do not ask the user for routine permission to record low-risk project
memory. Do not bury reusable lessons only in chat, task files, workflow-state,
or terminal output.

If no, finish without creating noise. The goal is useful memory, not exhaustive
logging.

## Memory Layers

Spec Kit Plus uses four memory layers:

1. `.specify/memory/constitution.md`
   - Slow-changing MUST/SHOULD governance and cross-workflow principles.

2. `.specify/memory/project-rules.md`
   - Stable reusable project defaults, constraints, and preferences.

3. `.specify/memory/learnings/INDEX.md`
   - Searchable learning index with short summaries, recurrence keys, trigger
     signals, and links to detail documents.

4. `.specify/memory/learnings/<lesson>.md`
   - One detailed markdown document per lesson, including evidence, context,
     applicability, and validation notes.

Open the index first. Open only detail documents whose `applies_to` or
`trigger_signals` match the current work.

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
- `map_coverage_gap`: project cognition lacked needed truth
- `tooling_trap`: environment, shell, toolchain, watcher, or dev-surface trap
- `false_lead_pattern`: misleading diagnosis pattern
- `near_miss`: late-avoided risky path
- `decision_debt`: vague deferred decision that keeps causing downstream cost

## Required Behavior

### 1. Consume memory before deeper work

Before broad execution or diagnosis, load shared memory in this order:

1. constitution
2. project rules
3. learning index
4. relevant lesson detail documents

This should happen as part of workflow behavior. It should not depend on the
user explicitly asking for memory to be loaded.

### 2. Capture reusable knowledge during the run

When the run exposes reusable knowledge, record it in the learning index and
detail document.

Do not silently adapt local behavior and leave the lesson trapped in the current
chat, task file, or session transcript.

### 3. Review memory before terminal closeout

Before a workflow closes in a terminal state, it should either:

- capture or merge the reusable learning, or
- explicitly decide the run was one-off and no reusable learning exists

The closeout review exists to stop the same pitfall from being rediscovered.

### 4. Promote when the evidence is strong enough

Normal capture creates or updates an index/detail lesson. Promotion is separate.

Promote to `project-rules.md` or `constitution.md` only after recurrence,
explicit user confirmation, or stable cross-workflow governance value.

## What To Record

Record memory when the run exposes reusable knowledge such as:

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

- If future you would benefit from seeing this before starting a related task,
  it is memory-worthy.

## What To Skip

Skip capture when:

- the task was a routine one-off with no reusable lesson
- the observation is already covered by a matching learning detail document
- the note only restates command output without judgment
- the evidence is too vague to help future work
- the lesson belongs in a task-local artifact and has no cross-run value

Keep the learning index useful. Avoid turning it into a transcript.

## Start-Time Memory Effects

Treat `learning start` as required preflight memory for light and heavy work,
not optional telemetry. Required means the workflow must attempt it and report
its result; it does not mean a legacy learning-index parser failure may block
the primary workflow.

The start surface should make project rules and relevant learning index entries
visible before later work repeats the same mistake. Detail documents should be
opened selectively only when their triggers match the current task.

If `learning start --format json` reports `warnings`,
`learning_index_diagnostics`, skipped malformed entries, or helper
unavailability, continue with direct memory reads from
`.specify/memory/project-rules.md`, `.specify/memory/project-learnings.md`, and
`.specify/memory/learnings/INDEX.md` when those files exist. Treat those
diagnostics as preflight evidence to surface in the workflow, not as a hard gate
unless the active command explicitly declares learning as blocking.

Native hooks are an optional enhancement. Without native hooks, the shared
`{{specify-subcmd:learning start}}`, `{{specify-subcmd:learning capture}}`, and
`{{specify-subcmd:learning capture-auto}}` path must still preserve the same
memory guarantees.

## Command Surface

These are the memory-system primitives:

- `{{specify-subcmd:learning status}}`
- `{{specify-subcmd:learning start}}`
  - Command shape: `{{specify-subcmd:learning start --command implement --format json}}`
- `{{specify-subcmd:learning capture}}`
  - Required options: `--command`, `--type`, `--summary`, `--evidence`
- `{{specify-subcmd:learning capture-auto}}`
  - Command shape: `{{specify-subcmd:learning capture-auto --command implement --feature-dir "$FEATURE_DIR" --format json}}`
- `{{specify-subcmd:learning promote}}`
  - Command shape: `{{specify-subcmd:learning promote --recurrence-key cli.project-launcher-helper-drift --target learning}}`

Use `capture-auto` when durable workflow state already contains enough evidence
to infer the lesson. Use manual capture when durable state does not capture the
lesson cleanly.

Typical durable-state sources include:

- `implement-tracker.md`
- quick-task `STATUS.md`
- debug session files
- `workflow-state.md` when it preserves route reasons, false starts, hidden
  dependencies, validation gaps, or reusable constraints

## Direct Learning Helpers

Use direct learning helpers for low-noise memory lifecycle work. Do not turn ordinary workflow closeout into hook choreography.

- `{{specify-subcmd:learning start}}`
  - Command shape: `{{specify-subcmd:learning start --command <command-name> --format json}}`
- `{{specify-subcmd:learning capture-auto}}`
  - Command shape: `{{specify-subcmd:learning capture-auto --command <command-name> --format json}}`
  - Use this when durable workflow state already preserves route reasons, false starts, hidden dependencies, validation gaps, or reusable constraints.
- Manual memory capture
  - Update `.specify/memory/learnings/INDEX.md` and one linked detail markdown document when automatic capture cannot express the lesson clearly.
- `{{specify-subcmd:learning aggregate}}`
  - Command shape: `{{specify-subcmd:learning aggregate --format json}}`
- `{{specify-subcmd:learning promote}}`
  - Command shape: `{{specify-subcmd:learning promote --recurrence-key <key> --target learning|rule}}`

Hook-based learning commands remain compatibility and native-adapter internals. Normal `sp-*` workflow steps should not call them.

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

If the run was painful, surprising, or repeatedly avoidable, it probably
deserves memory.

## Promotion Heuristics

Promotion is separate from normal capture.

Promote to `project-rules.md` when:

- the learning has recurred
- it is a stable default
- it should shape many later workflows
- violating it would predictably create repeated cost

Promote to `constitution.md` when:

- the lesson is durable governance
- it applies across project areas
- the user explicitly confirms it or the evidence is strong enough to justify a
  principle-level constraint

## Injection Goal

The memory system is not complete when a lesson is merely stored.

The lesson should influence future work by being surfaced at the right time:

- before related execution starts
- before the same route mistake repeats
- before the same tooling trap gets misdiagnosed
- before the same project constraint is forgotten

That is why captured lessons must be surfaced through start-time memory,
relevant detail links, and promotion into stronger rule layers when justified.

## Behavioral Rules

- **Do NOT** wait for the user to explicitly say "remember this" when the run clearly exposed reusable knowledge.
- **Do NOT** trap durable lessons in chat history, task-local notes, or one workflow artifact.
- **Do NOT** write everything into `constitution.md`.
- **Do NOT** promote routine lessons during normal capture.
- **Do NOT** close a terminal workflow without either captured memory or an explicit review rationale.
- Keep `project-rules.md` stricter than learning detail documents.
