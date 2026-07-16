---
name: spec-kit-project-learning
description: Consume and produce reusable project Learning through the Specify CLI. Use at the start and closeout of every non-trivial SP workflow, and whenever user correction, repeated attempts, route changes, blockers, false leads, hidden dependencies, validation failures, tooling traps, or reusable project constraints appear.
---

# Spec Kit Project Learning

Use the Learning CLI as the only agent-facing read surface. Do not parse
`.specify/memory/learnings/INDEX.md`, detail Markdown, compatibility summaries,
or `.planning/learnings/**` directly during normal workflow execution.

## Consume With Progressive Disclosure

1. Run `{{specify-subcmd:learning start --command <classic-command-name> --format json}}`.
2. Use the returned compact cards to identify matching trigger signals.
3. If more summaries are needed, run `{{specify-subcmd:learning list --command <classic-command-name> --format json}}`. Use `--query`, `--type`, `--status`, `--cursor`, or `--all` only when needed.
4. Run the selected card's `show_argv` for one Learning at a time. Do not expand every detail.
5. Apply guidance only when its applicability and trigger signals match live evidence. Current repository evidence overrides stale Learning.

Command shape: `{{specify-subcmd:learning list --command <command> --format json}}`
and then `{{specify-subcmd:learning show --ref <ref> --format json}}`.

SPX names map to the same Classic namespace: `spx-implement` consumes
`--command implement`; `spx-research` consumes `--command deep-research`.

`start`, `list`, and `show` are read-only. They must not capture, merge, confirm,
or promote Learning.

## Produce Learning

Prefer deterministic capture from durable workflow state:

```text
specify learning capture-auto --command <command> <state locator> --format json
```

Use manual capture only when durable state cannot express the lesson. Supply a
small agent-oriented record:

Required options: `--command`, `--type`, `--summary`, and `--evidence`.

- `--summary`: one-line identity
- `--problem`: failure mode or situation
- `--action`: imperative future action
- `--trigger`: observable activation signal; repeat as needed
- `--success`: observable proof the action worked; repeat as needed
- `--avoid`: tempting but harmful action; repeat as needed
- `--exception`: boundary where the guidance should not apply
- `--evidence`: concrete observation or stable reference
- `--type`, `--command`, and optionally `--recurrence-key`

The CLI derives safe defaults for omitted guidance fields, merges by recurrence
key, updates the compact index/detail projection, and preserves provenance.

Use the smallest accurate machine type: `pitfall`, `recovery_path`,
`user_preference`, `project_constraint`, `workflow_gap`, `routing_mistake`,
`verification_gap`, `state_surface_gap`, `map_coverage_gap`, `tooling_trap`,
`false_lead_pattern`, `near_miss`, or `decision_debt`.

## Trigger Rules

When the workflow owns `workflow-state.md`, persist explicit semantic signals
under `## Learning Triggers` as `kind: compact evidence`; `capture-auto` maps
the canonical kind to the appropriate Learning type and future action.

Capture or review a candidate when any of these occurs:

- the user corrects an assumption, default, route, or repeated behavior
- two or more attempts, retries, or hypothesis changes were needed
- a blocker required a non-obvious recovery path
- a false lead, rejected path, or decisive signal would save future work
- a hidden dependency or project constraint changed execution
- verification failed, was missing, or exposed a reusable gap
- environment/tooling behavior looked like a product defect
- workflow state failed to preserve information needed after resume
- cognition coverage omitted a truth-owning surface
- a near miss avoided a risky or destructive action

Skip routine outcomes, raw command output, duplicates, vague speculation, and
facts that belong only to the current task.

## Workflow Policies

- `skip`: `fast`. Do not start or capture Learning unless the task escalates.
- `consume-only`: `accept`, `analyze`, `ask`, `auto`, `constitution`, `explain`,
  `implement-teams`, `taskstoissues`, and `team`. Read relevant Learning; defer
  capture to the workflow that owns an allowed durable write surface.
- `consume-capture`: all other non-trivial workflows. Consume before deeper
  work and run `capture-auto` at terminal closeout when durable state contains a
  reusable signal; otherwise make an explicit no-learning decision.

The `policy` returned by `learning start/list` is authoritative if this list and
the installed runtime differ.

## Lifecycle

```text
workflow evidence
  -> candidate (capture / capture-auto)
  -> confirmed learning (explicit promote or confirmation)
  -> project rule (explicit promote after recurrence or stable governance value)
```

Reading never changes lifecycle state. A candidate becomes promotion-ready when
recurrence or signal strength justifies review; it is not silently promoted at
the start of an unrelated workflow.

## Agent Detail Contract

`learning list` returns compact cards: `ref`, `summary`, `action`, `type`,
`status`, `signal`, `occurrences`, `applies_to`, `trigger_signals`, and
`show_argv`.

`learning show` returns one full record grouped as:

- `guidance`: problem, action, avoid, success criteria, exceptions
- `applicability`: commands, trigger signals, scope
- `evidence`: observation, decisive signal, false starts, rejected paths, root-cause family
- `provenance`: source command, first/last seen, occurrences, source layer
- `lifecycle`: signal, pain score, injection targets, promotion hint

Treat the CLI record as the consumption contract. Storage files are runtime
implementation details and compatibility projections.

## Guardrails

- Do not create Learning merely to prove the reflex ran.
- Do not expand every detail document at workflow start.
- Do not let candidate Learning override constitution, explicit user direction,
  or current repository evidence.
- Do not promote during a read command.
- Do not write Learning from a consume-only workflow whose write boundary
  forbids it; preserve the signal in its owning durable state and route capture.
