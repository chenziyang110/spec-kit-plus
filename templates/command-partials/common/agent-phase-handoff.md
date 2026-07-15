## Agent Phase Handoff

Phase handoff is an agent-only control surface. Human-facing explanation belongs in the visible reply or in project documents that have independent review value; it must not be duplicated into a handoff.

- The previous phase's canonical JSON contract is the next phase's primary input.
- Use the compact transition shape from `templates/agent-phase-transition-schema.json`: `status`, `source_ref`, `semantic_delta`, `required_refs`, `blockers`, `next_action`, and recovery only when blocked.
- Carry the minimum sufficient context: include a fact only when omitting it could change the next action, lose a requirement or obligation, force rediscovery, weaken verification, or prevent safe recovery.
- Preserve decisions, acceptance criteria, evidence provenance, `MP-*`, `CA-###`, and stop/reopen conditions by stable reference. Do not copy their full bodies into every downstream artifact.
- Protected `MP-*` and `CA-###` obligations must not drop between phases. A downstream phase may resolve or reopen them, but may not silently omit them.
- Carry the locked implementation-target reference. A cross-project transition must not silently point to the current repository when the confirmed target differs.
- Consume project rules and Learning through `learning start --command <classic-command-name> -> list -> show`; run selected `show_argv` only. Constitution remains at `.specify/memory/constitution.md`; never parse Learning storage.
- Capture at owning closeout only when the lesson would change a future action; prefer `learning capture-auto`.
- A rendered Markdown view is never an agent handoff authority. Do not require Markdown/JSON companion agreement.
- Revalidate upstream truth only when its revision changed, evidence became stale, live repository facts contradict it, or the current phase discovers a scope, boundary, feasibility, or risk change.
- If `semantic_delta` is empty, do not repeat upstream questions, approach selection, or user confirmation.

## Deterministic Workflow Runtime

For a feature-bearing `specify -> plan -> tasks -> implement -> accept` stage,
the CLI owns phase order and `workflow-state.md`. Do not author or advance
`workflow-state.md` by hand.

- After `FEATURE_DIR` is known, run `{{specify-subcmd:workflow show --feature-dir <feature-dir> --format json}}`. If state is missing at the first feature stage, run `{{specify-subcmd:workflow enter --command specify --feature-dir <feature-dir> --format json}}`.
- On entry to `plan`, `tasks`, `implement`, or `accept`, use the current revision with `{{specify-subcmd:workflow transition --to <this-stage> --feature-dir <feature-dir> --expected-revision <revision> --format json}}` before writing that stage's artifacts. The command validates the completed source-stage artifacts and refuses skips, stale revisions, or incomplete handoffs with exit `10`.
- The destination command owns the transition. A completed stage recommends the next command but must not execute `workflow transition` to that next stage in the same invocation.
- Use `{{specify-subcmd:workflow next --feature-dir <feature-dir> --format json}}` for the compact next action. Execute only its structured `next_argv`; do not reconstruct flags from prose.
- After safe agent recovery is exhausted, persist the blocker through `{{specify-subcmd:workflow block --input <blocker-json-or-> --format json}}`. Obtain its exact input shape with `{{specify-subcmd:api schema workflow-block-input --format json}}`; preserve the returned resume argv and human tutorial.
- After explicit human acceptance and the acceptance-owned closeout both succeed, run `{{specify-subcmd:workflow closeout --feature-dir <feature-dir> --expected-revision <revision> --format json}}`. It validates acceptance artifacts before marking the feature workflow complete.

For every blocked exit, including a pre-feature discussion that cannot use the
feature runtime yet, follow
`.specify/templates/workflow-blocker-template.md` and its schema. Report the
exact cause, sanitized evidence, attempted recovery and result, affected scope,
smallest next action, observable unblock criteria, and exact resume point. Keep
agent-capable repair agent-owned. When authority, credentials, a protected
system, physical access, or human judgment is genuinely required, add the full
Human Action Guide: goal, prerequisites, safety notes, numbered exact actions,
expected result and safe failure branch for every action, independent
verification, sanitized evidence to return, and the exact resume command.
