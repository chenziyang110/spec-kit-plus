# Project Learning

Use the Learning CLI as the only agent-facing read surface. Do not parse the
learning index, detail Markdown, compatibility summary, or runtime candidate
files directly during normal execution.

## Intake

For every non-trivial workflow, run:

```text
specify learning start --command <classic-command-name> --format json
```

SPX and Classic share one namespace: pass `implement` for `spx-implement` and
`deep-research` for `spx-research`. Select by compact `summary`, `action`,
`applies_to`, and `trigger_signals`. Use `learning list` only to filter or page
more summaries. Execute one selected card's `show_argv` only when its triggers
match the active work. Live evidence overrides stale Learning.

`start`, `list`, and `show` are read-only. Never capture or promote while
consuming.

## Trigger And Capture

In owned `workflow-state.md`, record explicit semantic signals under
`## Learning Triggers` as `kind: compact evidence`; `capture-auto` maps the kind
to a Learning type and future action.

Treat user corrections, repeated attempts, route changes, blockers, recovery
paths, false leads, decisive signals, hidden dependencies, validation gaps,
tooling traps, state loss, cognition gaps, reusable constraints, and near misses
as capture signals. Skip routine outcomes, raw output, duplicates, and vague
speculation.

Prefer `learning capture-auto` from the owning durable workflow state. Use
manual `learning capture` only when state cannot express the lesson; provide a
one-line summary plus problem, imperative action, trigger signals, success
criteria, avoid items, exceptions, and concrete evidence when known.

Policies:

- `spx-fast`: skip unless it escalates.
- consume-only: accept, analyze, ask, auto, constitution, explain,
  implement-teams, taskstoissues, and team. Preserve a signal in owning state;
  do not violate the workflow write boundary to capture it.
- all other non-trivial skills: consume before deeper work and run
  `capture-auto` at terminal closeout when durable state contains a reusable
  signal; otherwise record an explicit no-learning decision in normal closeout.

The runtime `policy` field wins if these prompts drift.

## Progressive Detail Contract

`learning list` returns compact cards with `ref`, `summary`, `action`, type,
status, signal, occurrences, applicability, triggers, and `show_argv`.
`learning show` expands exactly one record into guidance, applicability,
evidence, provenance, and lifecycle groups.

Capture creates or merges a candidate. Confirmation/promotion is explicit;
reading must never silently promote. Project-rule promotion requires recurrence,
explicit confirmation, or stable cross-workflow governance value.
