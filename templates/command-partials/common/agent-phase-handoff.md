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

For a feature-bearing `specify -> plan -> tasks -> implement -> review -> accept` stage,
the CLI owns phase order in `FEATURE_DIR/workflow.json`. Do not author
or advance `workflow.json` by hand. `workflow-state.md` remains the rich
workflow-owned evidence and resume surface for Learning, clarification,
research, analysis, and profile-specific details; the phase runtime must not overwrite
or parse it as its revision authority. Read `workflow-state.md` only through
`specify-runtime artifact show`; mutate it only through an authorized
`artifact prepare` / `artifact submit` lease.

- After `FEATURE_DIR` is known, run `{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`. If state is missing at the first feature stage, run `{{specify-subcmd:specify-runtime workflow enter --command specify --feature-dir <feature-dir> --format json}}`.
- On entry to `plan`, `tasks`, `implement`, `review`, or `accept`, use the current revision with `{{specify-subcmd:specify-runtime workflow transition --to <this-stage> --feature-dir <feature-dir> --expected-revision <revision> --format json}}` before writing that stage's artifacts. The command validates the completed source-stage artifacts and refuses skips, stale revisions, or incomplete handoffs with exit `10`.
- After the owning stage finishes its artifact closeout, run `{{specify-subcmd:specify-runtime workflow complete-stage --feature-dir <feature-dir> --expected-revision <revision> --format json}}`. The runtime validates the stage artifacts, records non-terminal `status: completed`, and returns the one legal transition argv; do not edit phase state manually.
- `completed` closes only the current stage. Every non-terminal stage keeps exactly one legal successor; only completed `accept` is terminal.
- The destination command owns the returned transition. A completed stage recommends the next command but must not execute `specify-runtime workflow transition` to that next stage in the same invocation.
- Use `{{specify-subcmd:specify-runtime workflow next --feature-dir <feature-dir> --format json}}` for the compact next action. While a stage is active its `next_argv` completes that stage; after completion it transitions to the successor. Execute only structured argv and do not reconstruct flags from prose.
- When fresh evidence invalidates an earlier required stage, preserve the stale
  artifacts for audit and reopen the highest invalid stage with
  `{{specify-subcmd:specify-runtime workflow reopen --to <specify|plan|tasks|implement|review> --feature-dir <feature-dir> --expected-revision <revision> --reason <compact-reason> --evidence <sanitized-evidence> --invalidated-artifacts <artifact> --format json}}`.
  Repeat `--evidence` and `--invalidated-artifacts` as needed. The CLI permits
  a strict backward move or reactivation of the same completed non-accept stage,
  including `implement` and `review`; an active same-stage owner simply continues. Honor any
  persisted blocker before retrying. Failed acceptance uses
  `accept route-repair`, never generic reopen. Every non-human-access acceptance
  failure first reopens Review; the Review Leader diagnoses it, dispatches an
  independent Fix and revalidation cycle, and may reopen an upstream truth
  owner only after proving that correct implementation is impossible under the
  current requirement, design, or architecture truth. After any repair, rerun
  the full frozen Human Acceptance Universe; preserve no stale human PASS.
- After safe agent recovery is exhausted, persist the blocker through `{{specify-subcmd:specify-runtime workflow block --input <blocker-json-or-> --format json}}`. Obtain its exact input shape with `{{specify-subcmd:api schema workflow-block-input --format json}}`; the runtime rejects replacement of an unresolved blocker and returns the human tutorial, a safe read-only `show_argv`, and a structured `data.resolution_action`. While evidence is missing, `next_argv` is intentionally empty.
- When the recorded unblock criteria are proven, append each sanitized evidence item to the runtime-returned `resolution_action.base_argv` using its declared `--resolution-evidence` required input, then execute that argv. This invokes `specify-runtime workflow resolve`, preserves the full prior blocker audit, and reactivates the same stage; do not reconstruct other flags or clear blocker state manually.
- After explicit human acceptance, run the acceptance-owned `accept closeout` command and execute its successful response's `next_argv` verbatim. That revision-bound argv invokes `specify-runtime workflow closeout`; do not reconstruct it from prose or a remembered revision. It validates and snapshots acceptance evidence before marking the feature workflow complete.

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
