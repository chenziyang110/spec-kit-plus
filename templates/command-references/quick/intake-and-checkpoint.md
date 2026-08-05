Trigger: before quick-task execution, broad reads, delegation, or validation commands, and whenever a material discovery may invalidate the confirmed quick boundary.

Purpose: preserve required context, understanding checkpoint, direct-delivery eligibility, in-workflow scale-up rules, and consequence coverage.

Preserved Contract: quick work starts only after scope and outcome confirmation, then scales its own planning, batches, and verification instead of requiring a formal-spec upgrade when the task grows.

## Required Context Inputs

{{spec-kit-include: ../../command-partials/common/context-loading-gradient.md}}

**Project cognition gate:** query the active project's runtime before broad
repository reads.

Run or emulate:

```text
{{specify-subcmd:specify-runtime cognition compass --intent implement --query="$ARGUMENTS" --format json}}
```

After the default compass packet, run the advanced `lexicon -> semantic_intake -> query` path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, use `specify-runtime cognition lexicon --mode catalog` as the alias catalog, write agent-authored `semantic_intake` and `concept_decisions`, then run `specify-runtime cognition query --query-plan "<query_plan_json>"`; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `repository_search_terms`, project-language search terms, and facet coverage; do not search only the raw user words before source search. Agent-owned semantic normalization remains mandatory: `agent_normalization` and raw lexicon ranking are bootstrap signals only; if `agent_normalization` is omitted, treat it as `required=false`; use `write_semantic_intake_from_alias_catalog` when needed. Raw lexicon ranking is only a bootstrap; CJK or mixed CJK/ASCII input still requires agent-owned normalization even when positive raw lexical matches exist. The agent still owns translation. Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`.

Use the returned readiness only to prepare the Understanding Checkpoint and
write early quick-task state:

- `query_ready`: read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons.
- `review`: perform only the returned `minimal_live_reads` before continuing and inspect `coverage_diagnostics`.
- `needs_rebuild`: route by `recommended_next_action.action_id`, not readiness alone. Preserve resumable actions such as `complete_scan_packets`; only `action_id=project_cognition.rebuild` may use `rebuild_reasons[]` and `recommended_next_action.workflow_routes.classic.steps` for the rebuild handoff.
- `blocked`: report the blocking runtime issue and continue with live evidence only where this workflow allows degraded navigation.
- **CARRY FORWARD**: Patch the selected capability, minimal reads, validation route,
  and known risk into quick-task `STATUS.md` through a leased `specify-runtime artifact patch` call before implementation
  proceeds.

Treat task-relevant coverage as insufficient when the touched area still lacks
ownership, placement, workflow, integration, or verification guidance before
choosing the quick-task lane shape.

## Discussion Handoff Intake

Apply [handoff consumption](handoff-consumption.md) once. Use canonical `SOURCE_CONTRACT` plus `SOURCE_DISCUSSION_SLUG`; do not duplicate its parsing, source sweep, or eligibility checks here.

When the confirmed contract introduces no quick-stage `semantic_delta`, stage the
Quick checkpoint with `source.kind=discussion`, `semantic_delta=false`, and the
handoff `review_digest`. Runtime marks the checkpoint `inherited`, projects the
Decision Checkpoint summary plus Delivery Map, and continues without repeated
user confirmation. Otherwise stage only the changed decision delta.

## Understanding Checkpoint

`sp-quick` has one default Decision Checkpoint before substantive execution.
This is not a full spec, not a `sp-plan` substitute, and not approval of the
agent's construction plan. It confirms user-owned product decisions only.

After the constitution gate, quick workspace initialization, project cognition
query, and any bounded `minimal_live_reads`, stage a structured
`quick-confirmation-v1` contract through runtime:

```text
{{specify-subcmd:specify-runtime quick checkpoint-stage <quick-id> --input-json '<decision+delivery>' --format json}}
{{specify-subcmd:specify-runtime quick checkpoint-show <quick-id> --view decision --format json}}
{{specify-subcmd:specify-runtime quick checkpoint-show <quick-id> --view delivery --format json}}
```

Present the runtime Decision Checkpoint and Delivery Map views. Do not hand-author
a freeform two-column approval table for multi-item work. The Decision Checkpoint
contains only user-owned decisions: goal, user-visible result, scope, ordered
`Q1`/`Q2`/... deliverables and product-level dependencies, independent acceptance
for every work item, recommended approach, assumptions and risks, overall
completion evidence, and the reconfirmation trigger. Delivery Map shows waves,
parallelism, join points, and integration gates for awareness only.

Never ask the user to approve subagent count, file split, batch choreography,
test command order, or worker packet details. Those remain agent-owned and may
change through `checkpoint-stage --delivery-only` after confirmation without
reopening approval.

When the task affects a user-visible UI surface, append the UI Confirmation
card and include `decision.ui_confirmation` in the staged contract. Ask once for
staged non-inherited checkpoints; the user may confirm both or revise only
scope, UI, dependency, acceptance, or another named decision.

{{spec-kit-include: ../../command-partials/quick/checkpoint-card.md}}

For staged checkpoints, wait for user confirmation, then bind it with:

```text
{{specify-subcmd:specify-runtime quick checkpoint-confirm <quick-id> --digest <confirmation_digest> --format json}}
```

Inherited discussion handoffs with no semantic delta do not wait for a second
confirmation. If the user corrects the understanding, re-stage only the changed
decision fields and confirm the new digest.

Create `STATUS.md` with `artifact scaffold --kind quick-status`. Runtime
`checkpoint-stage` / `checkpoint-confirm` own the structured confirmation file
and project the Understanding Checkpoint and Execution sections. Prefer those
commands over freeform section rewriting for checkpoint fields.
`understanding_confirmed: false` blocks substantive execution on entry and
resume until the runtime-managed checkpoint is confirmed or inherited.
Before any map-maintenance handoff, use the artifact CLI to scaffold or patch `STATUS.md` with `understanding_confirmed: false`. Until the checkpoint is confirmed, you must not proceed to code edits, broad repository analysis, delegation, validation commands, or map maintenance; read only enough targeted context to revise the decision contract. Do not start execution routing while `understanding_confirmed: false`. Do not dispatch until the artifact CLI has patched `understanding_confirmed: true` or runtime inheritance has set it. Start execution only after a leased `specify-runtime artifact patch` sets `understanding_confirmed: true` in `STATUS.md`, or after `quick checkpoint-confirm` / inherited stage has done so. The first concrete execution action after understanding confirmation should follow the Delivery Map pulse, not vague waiting text.

## Quick Checkpoint Amendments

The confirmed checkpoint remains valid while repository evidence only adds
files, call sites, tests, or implementation details needed to deliver the same
confirmed outcome within the confirmed boundary, risk, and authority. Patch
`STATUS.md` through `specify-runtime artifact patch` and continue; do not reopen confirmation for that ordinary causal
closure.

Reopen confirmation only when new evidence materially changes the confirmed
problem or outcome, an included or excluded boundary, a confirmed work item,
deliverable-level order or dependency, work-item acceptance, user-visible
behavior, risk, authority, migration or compatibility obligations, an
independent capability, or an explicit stop condition. Set
`understanding_confirmed: false` and pause substantive work before requesting
the new decision.

Before presenting the amendment, explain in user-facing prose:

- the new evidence and the exact trigger;
- why the previous confirmation no longer covers the proposed work;
- the consequence of omitting the newly discovered work;
- the current mutation state, including what has and has not changed and the
  safe pause point; and
- the incremental decision the user owns and why repository evidence cannot
  resolve it.

Only after that explanation, present `## Quick Checkpoint Amendment` by
re-staging a delta Decision Checkpoint through `quick checkpoint-stage` with
`semantic_delta=true` and a delta summary. Present only the changed rows or
decisions plus one concise `Unchanged` statement; do not repeat the full initial
Quick Checkpoint. Ask the user to confirm or revise that delta, then
`checkpoint-confirm` the new digest before resuming. If the user already
explicitly approved the exact delta in the message that supplied it, confirm
that digest instead of requesting a duplicate confirmation.

When the material delta is UI-only, keep the
`## Quick Checkpoint Amendment` heading. Include only the changed UI Confirmation rows.
State that the main checkpoint is unchanged. The reason-first explanation still
comes before this delta; do not replay either complete initial table.

## Workflow Quality Requirements

- Confirm project cognition freshness and valid quick-task entry before deeper execution.
- Keep `STATUS.md` current as the durable quick-task source of truth for scope, lane state, blockers, verification, and terminal status.
- Validate each `WorkerTaskPacket` or equivalent execution contract before dispatch and require a structured handoff before accepting delegated work.
- Update durable state before compaction-risk transitions, join points, delegated fan-out, or any stop where resume will depend on more than the visible conversation.
- Query `.specify/memory/constitution.md` through `specify-runtime artifact show` as governance, then use the Learning CLI summary intake before broader quick-task context. Expand only selected matching records with `learning show`.
- Learning Reflex: before final closeout, run `learning capture-auto` from `STATUS.md` when a reusable signal exists; do not edit Learning storage files directly.

## Scope Gate

Use `sp-quick` when all of these are true:
- The user wants direct implementation rather than first producing a formal feature specification.
- The requested outcome and current scope can be confirmed through the Understanding Checkpoint.
- The work is non-trivial enough to benefit from resumable state, task-local planning, decomposition, or verification.
- The workflow can preserve the complete confirmed scope, user-owned decisions, consequence obligations, and acceptance evidence in the quick workspace.

If the task is trivial and local:
- `{{invoke:fast}}` is the lower-overhead recommendation before a quick workspace exists; an already active quick task may still complete it without changing workflows.

The following are **not** reasons to leave quick: task size, file count, module
count, cross-cutting behavior, architecture work, multiple capabilities or user
journeys, migration, compatibility, rollout, shared-state impact, long-lived
implementation, or many acceptance criteria. Increase task-local planning and
validation depth instead of shrinking the request or requiring
`{{invoke:specify}}`.

Quick can handle larger tasks through deeper task-local planning, multiple batches,
explicit joins, and acceptance coverage, including multiple
independent capabilities.

`{{invoke:specify}}` remains a separate formal specification workflow. Mention
or hand off to it only when the user explicitly chooses to replace the active
quick workflow with a spec-first flow; never infer that choice from complexity,
risk breadth, or artifact count.
A move from Quick to Specify is not automatic.

If the task is a bug fix or regression but the root cause is still unknown:
- Use `{{invoke:debug}}` instead of treating `sp-quick` as a symptom-fix lane.

## Scale Up Within Quick

When the task grows, preserve the same confirmed outcome and expand the quick
workspace deliberately:

- Create an absent task-local `PLAN.md` with `specify-runtime artifact scaffold --kind quick-plan`, then deepen it only through leased section patches when architecture, migration, rollout,
  compatibility, multiple capabilities, or a long execution chain needs durable
  design and sequencing.
- Split execution into dependency-aware lanes and multiple ready batches. Record
  joins, integration checks, and the acceptance slice each batch advances in
  `STATUS.md`; a quick task is not limited to one batch or one capability.
- Keep a concrete acceptance matrix and full affected-surface sweep for
  acceptance-heavy work. Compact its active status in `STATUS.md` and put the
  expanded evidence in the task-local plan or summary.
- Use focused research and checkpoint amendments for newly discovered facts or
  user-owned product decisions. A material decision pauses execution until it is
  confirmed, but it does not change the workflow automatically.
- Preserve the user's full scope. Complexity is a planning and dispatch input,
  never a reason to invent a smaller quick outcome.

The task becomes `blocked` only for a concrete unresolved decision, missing
authority, unavailable external dependency, unsafe overlap, or failed recovery
with no safe next action. Record the exact unblock and resume point. Size or
planning depth alone is not a blocker.

## Quick Consequence Coverage

Quick may own consequence models with many affected objects, user-level
lifecycle decisions, non-local lifecycle choices, broad compatibility handling,
multi-capability scope, shared-state semantics, destructive policy, or
downstream consumer negotiation. Breadth changes the amount of
planning and evidence required, not workflow eligibility.
Broad consequential work remains in Quick once its outcome is confirmed.

- If the Senior Consequence Analysis Gate stands down, patch the reason into the relevant `STATUS.md` section through a leased `specify-runtime artifact patch`.
- If it triggers, record affected objects, state behavior, dependency impact, recovery and validation, project cognition evidence, coverage gaps, and every `CA-###` obligation before the owning execution batch starts.
- Keep `STATUS.md` compact. When the consequence material is large, place the expanded tables in task-local `PLAN.md` and record stable references plus active statuses in `STATUS.md` and worker packets.
- Resolve user-owned lifecycle, compatibility, migration, destructive-policy, shared-state, and downstream-consumer decisions through the Quick Checkpoint Amendment contract. Do not route them to `{{invoke:specify}}` merely because they are broad.
- If the task is a defect and the dependency loop is unknown, use `{{invoke:debug}}` rather than guessing inside `sp-quick`.
