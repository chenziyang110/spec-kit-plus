Trigger: before quick-task execution, broad reads, delegation, or validation commands, and whenever a material discovery may invalidate the confirmed quick boundary.

Purpose: preserve required context, understanding checkpoint, quick checkpoint, scope gate, escalation triggers, and consequence boundary.

Preserved Contract: quick work starts only after bounded scope, checkpoint confirmation, and escalation checks are satisfied.

## Required Context Inputs

{{spec-kit-include: ../../command-partials/common/context-loading-gradient.md}}

**Project cognition gate:** query the active project's runtime before broad
repository reads.

Run or emulate:

```text
{{specify-subcmd:project-cognition compass --intent implement --query="$ARGUMENTS" --format json}}
```

After the default compass packet, run the advanced `lexicon -> semantic_intake -> query` path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, use `project-cognition lexicon --mode catalog` as the alias catalog, write agent-authored `semantic_intake` and `concept_decisions`, then run `project-cognition query --query-plan "<query_plan_json>"`; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `repository_search_terms`, project-language search terms, and facet coverage; do not search only the raw user words before source search. Agent-owned semantic normalization remains mandatory: `agent_normalization` and raw lexicon ranking are bootstrap signals only; if `agent_normalization` is omitted, treat it as `required=false`; use `write_semantic_intake_from_alias_catalog` when needed. Raw lexicon ranking is only a bootstrap; CJK or mixed CJK/ASCII input still requires agent-owned normalization even when positive raw lexical matches exist. The agent still owns translation. Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`.

Use the returned readiness only to prepare the Understanding Checkpoint and
write early quick-task state:

- `query_ready`: read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons.
- `review`: perform only the returned `minimal_live_reads` before continuing and inspect `coverage_diagnostics`.
- `needs_rebuild`: route through `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only for documented brownfield rebuild triggers: first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid.
- `blocked`: report the blocking runtime issue and continue with live evidence only where this workflow allows degraded navigation.
- **CARRY FORWARD**: Write the selected capability, minimal reads, validation route,
  and known risk into quick-task `STATUS.md` before implementation
  proceeds.

Treat task-relevant coverage as insufficient when the touched area still lacks
ownership, placement, workflow, integration, or verification guidance before
choosing the quick-task lane shape.

## Discussion Handoff Intake

Apply [handoff consumption](handoff-consumption.md) once. Use canonical `SOURCE_CONTRACT` plus `SOURCE_DISCUSSION_SLUG`; do not duplicate its parsing, source sweep, or eligibility checks here.

When the confirmed contract introduces no quick-stage `semantic_delta`, bind the Understanding Checkpoint to its `review_digest` and continue without repeated user confirmation. Otherwise use the checkpoint rules below for the changed decision only.

## Understanding Checkpoint

`sp-quick` has one default understanding checkpoint before substantive execution. This is not a full spec, not a `sp-plan` substitute, and not a detailed task-plan approval. It exists so the user can confirm that the quick-task direction is correct before the workflow runs to completion.

After the constitution gate, quick workspace initialization, project cognition query, and any bounded `minimal_live_reads`, present one concise user-facing checkpoint card. Use the user's language for the card content and confirmation prompt when practical. Keep it compact, but do not omit important specifics: include concrete files, commands, workflows, constraints, validation evidence, and known uncertainty when they are already known. If a row is genuinely unknown, write `Unknown: [why it matters]` instead of leaving it vague.

Use the exact card below. The main table contains only user-owned decisions:
request and outcome, user-visible result, scope, recommended approach,
assumptions and risks, completion evidence, and the reconfirmation trigger.
Technical execution belongs to the agent. Put affected surfaces, implementation
sequencing, and the next command in a short technical summary for awareness,
not as a request to approve technical details. Keep the checkpoint plain text
for terminal output: do not use HTML tags or inline line-break markup. Do not
reuse the placeholder text as content; replace each bracketed item with
task-specific facts.

When the task affects a user-visible UI surface, append the UI Confirmation
card from the fixed partial. It is a design proposal for this bounded
implementation, not a replacement for an approved project design direction.
Ask once after both cards; the user may confirm both or revise only scope, UI,
or another named decision.

{{spec-kit-include: ../../command-partials/quick/checkpoint-card.md}}

Wait for user confirmation before code edits, broad repository analysis, delegation, implementation commands, or validation commands. If the user corrects the understanding, revise the checkpoint once with the corrected direction and ask for confirmation again.

Create or update `STATUS.md` with `understanding_confirmed: false` before any map maintenance handoff, broad repository analysis, delegation, implementation command, or validation command. Record the confirmed checkpoint in `STATUS.md`. `understanding_confirmed: false` blocks substantive execution on resume. While it is false, only read the minimal context needed to reconstruct or revise the checkpoint; you must not proceed to code edits, broad repository analysis, delegation, validation commands, `{{invoke:map-update}}`, `{{invoke:map-scan}}`, or `{{invoke:map-build}}` until the checkpoint is confirmed and `STATUS.md` is updated.

## Quick Checkpoint Amendments

The confirmed checkpoint remains valid while repository evidence only adds
files, call sites, tests, or implementation details needed to deliver the same
confirmed outcome within the confirmed boundary, risk, and authority. Update
`STATUS.md` and continue; do not reopen confirmation for that ordinary causal
closure.

Reopen confirmation only when new evidence materially changes the confirmed
problem or outcome, an included or excluded boundary, user-visible behavior,
risk, authority, migration or compatibility obligations, an independent
capability, or an explicit stop condition. Set `understanding_confirmed: false`
and pause substantive work before requesting the new decision.

Before presenting the amendment, explain in user-facing prose:

- the new evidence and the exact trigger;
- why the previous confirmation no longer covers the proposed work;
- the consequence of omitting the newly discovered work;
- the current mutation state, including what has and has not changed and the
  safe pause point; and
- the incremental decision the user owns and why repository evidence cannot
  resolve it.

Only after that explanation, present `## Quick Checkpoint Amendment`. Include
only the changed rows or decisions plus one concise `Unchanged` statement; do
not repeat the full initial Quick Checkpoint. Ask the user to confirm or revise
that delta, then persist the amendment and confirmation before resuming. If the
user already explicitly approved the exact delta in the message that supplied
it, record that approval instead of requesting a duplicate confirmation.

When the material delta is UI-only, keep the
`## Quick Checkpoint Amendment` heading. Include only the changed UI Confirmation rows.
State that the main checkpoint is unchanged. The reason-first explanation still
comes before this delta; do not replay either complete initial table.

## Workflow Quality Requirements

- Confirm project cognition freshness and valid quick-task entry before deeper execution.
- Keep `STATUS.md` current as the durable quick-task source of truth for scope, lane state, blockers, verification, and terminal status.
- Validate each `WorkerTaskPacket` or equivalent execution contract before dispatch and require a structured handoff before accepting delegated work.
- Update durable state before compaction-risk transitions, join points, delegated fan-out, or any stop where resume will depend on more than the visible conversation.
- Read `.specify/memory/constitution.md` as governance, then use the Learning CLI summary intake before broader quick-task context. Expand only selected matching records with `learning show`.
- Learning Reflex: before final closeout, run `learning capture-auto` from `STATUS.md` when a reusable signal exists; do not edit Learning storage files directly.

## Scope Gate

Use `sp-quick` when all of these are true:
- The task is bounded and clearly described.
- The work is small but non-trivial.
- A lightweight plan is useful, but a full spec package would be overhead.
- Use this path when you want to skip the full `{{specify-subcmd:-> plan -> tasks -> implement}}` workflow for a bounded task.
- The task does not require a new long-lived feature spec under `.specify/features/<feature>/`.

If the task is trivial and local:
- Use `{{invoke:fast}}`.

If the task changes architecture, introduces broad product decisions, or needs a durable feature specification:
- Use `{{invoke:specify}}`.

If the task is a bug fix or regression but the root cause is still unknown:
- Use `{{invoke:debug}}` instead of treating `sp-quick` as a symptom-fix lane.

## Escalation Triggers

Upgrade to `{{invoke:specify}}` immediately if:
- The Senior Consequence Analysis Gate triggers and the work needs user-level lifecycle decisions, broad compatibility handling, multi-capability scope, destructive policy, shared-state semantics, downstream consumer negotiation, or acceptance criteria that cannot fit one bounded quick task.
- The task changes architecture or introduces cross-cutting behavior across multiple modules, workflows, or shared surfaces.
- The task touches a change-propagation hotspot, a truth-owning shared surface, or an area whose known unknowns make lightweight planning unsafe.
- The request now spans multiple independent capabilities, release tracks, or user journeys that no longer fit one bounded quick-task workspace.
- The work needs a new durable spec package, a long-lived feature boundary, or planning artifacts intended to survive beyond the quick task.
- The change has rollout, migration, compatibility, or neighboring-workflow impact that must be locked before implementation.
- The expected behavior cannot be stated with concrete acceptance criteria without first doing feature-level requirement alignment.
- The work started as a bug fix, but root-cause analysis is still unresolved, competing causes are still plausible, or the next safe step is diagnostic investigation rather than a bounded repair. In that case, route to `{{invoke:debug}}`.

## Quick Consequence Boundary

Continue in quick only when the consequence model is bounded: affected objects are few, lifecycle choices are local, dependency impact is limited, recovery is obvious, validation can run inside the quick-task loop, and every `CA-###` obligation can be recorded in `STATUS.md`.

- If the gate stands down, record the stand-down reason in `STATUS.md`.
- If the gate triggers but remains bounded, record affected objects, state behavior, dependency impact, recovery and validation, project cognition evidence, coverage gaps, and escalation decision before dispatch.
- If consequence analysis reveals user-level lifecycle decisions, broad compatibility handling, multi-capability scope, destructive policy, shared-state semantics, or downstream consumer negotiation, upgrade to `{{invoke:specify}}` immediately.
- If the task is a defect and the dependency loop is unknown, use `{{invoke:debug}}` rather than resolving consequence semantics inside `sp-quick`.
