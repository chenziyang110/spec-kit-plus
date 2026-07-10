Trigger: before quick-task execution, broad reads, delegation, or validation commands.

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

Resolve discussion handoff intake before quick-task execution.

Classify the supplied arguments before creating or resuming substantive quick-task execution:

- normal quick-task request
- `.specify/discussions/<slug>/handoff-to-specify.md`
- `.specify/discussions/<slug>/handoff-to-specify.json`
- `.specify/discussions/<slug>/handoff.md` or `.specify/discussions/<slug>/handoff.json` when a generated project has adopted neutral filenames
- a discussion `<slug>` whose workspace contains the unified handoff pair
- no arguments with exactly one unconsumed `status: handoff-ready` discussion whose `recommended_consumer` is `sp-quick` or whose JSON `consumer_eligibility.sp-quick.status` is `ready`

The `handoff-to-specify.*` filenames are compatibility names for a single unified `discussion_requirement_contract`. Do not look for or require `handoff-to-quick.*`, and do not create a second quick-specific handoff.

When a discussion handoff is selected, treat it as authoritative upstream input for the quick task and set:

- `SOURCE_HANDOFF_MD`
- `SOURCE_HANDOFF_JSON`
- `SOURCE_DISCUSSION_SLUG`

Require both Markdown and JSON companions. Missing Markdown or JSON is `blocked_by_handoff_integrity`; route back to `sp-discussion` to refresh the unified handoff instead of reconstructing it here.

Parse the JSON before quick-task execution and require:

- `entry_source: sp-discussion`
- `handoff_kind: discussion_requirement_contract` when present; legacy discussion handoffs without this field may continue only if all other gates pass
- canonical JSON `status: handoff-ready`
- a non-empty `review_digest` matching the current canonical handoff
- `quality_gate.status: user_confirmed` or `quality_gate.status: user-confirmed`
- `hard_unknown_count: 0`
- `open_conflict_count: 0`
- `consumer_eligibility.sp-quick.status: ready`
- a bounded `agent_requirement_contract.scope.in` with explicit exclusions in `scope.out`
- no planning constraint, consequence obligation, or reopen condition that requires specification first

If `consumer_eligibility.sp-quick.status` is blocked, the planning constraints require specification, the consequence model is unbounded, or the scope no longer fits one bounded quick-task workspace, stop and route to `{{invoke:specify}}` or back to `{{invoke:discussion}}` according to the handoff's `recommended_consumer` and blocker reason.

When a discussion handoff is accepted for quick, read only the agent-facing requirement contract first:

- `agent_requirement_contract.target_need`
- `agent_requirement_contract.constraints`
- `agent_requirement_contract.success_criteria`
- `agent_requirement_contract.design_direction`
- `agent_requirement_contract.optimal_solution_approach`
- `agent_requirement_contract.scope`
- `must_preserve`
- `discussion_decision_digest`
- `reopen_conditions` or `stop_and_reopen_conditions`

Read `discussion-log.jsonl`, `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` only when the unified handoff is stale, incomplete, contradictory, or explicitly references those files for evidence. Record inspected files in `source_files_read`.

Seed `STATUS.md` from the handoff before substantive work:

- `source_discussion_slug`
- `source_handoff_md`
- `source_handoff_json`
- `review_digest`
- `source_files_read`
- `locked_direction`
- `must_preserve`
- `reopen_conditions`
- `handoff_consumer: sp-quick`

Do not skip the Understanding Checkpoint. The accepted discussion handoff prepares the checkpoint; it does not replace user confirmation. Initialize or update `STATUS.md` with `understanding_confirmed: false`, then present the Quick Checkpoint from `agent_requirement_contract`, `planning_constraints`, and `must_preserve`.

## Understanding Checkpoint

`sp-quick` has one default understanding checkpoint before substantive execution. This is not a full spec, not a `sp-plan` substitute, and not a detailed task-plan approval. It exists so the user can confirm that the quick-task direction is correct before the workflow runs to completion.

After the constitution gate, quick workspace initialization, project cognition query, and any bounded `minimal_live_reads`, present one concise user-facing checkpoint card. Use the user's language for the card content and confirmation prompt when practical. Keep it compact, but do not omit important specifics: include concrete files, commands, workflows, constraints, validation evidence, and known uncertainty when they are already known. If a row is genuinely unknown, write `Unknown: [why it matters]` instead of leaving it vague.

Use this shape. The row labels should be localized to the user's language when practical; keep the meaning of the canonical fields. The checkpoint should give the user confidence to approve or correct the work: `Issue` must explain the bad behavior, where it appears, why it matters, and what the user is not asking for; `Implementation plan` must be a concrete ordered sequence, not a vague promise to investigate. Keep the checkpoint plain text for terminal output: do not use HTML tags or inline line-break markup. Format multi-step plans as semicolon-separated numbered clauses inside the table cell; if the plan is too long to read cleanly, put a short summary in the cell and add a normal Markdown numbered list immediately below the table. Do not reuse the placeholder text as content; replace each bracketed item with task-specific steps.

```markdown

## Quick Checkpoint

| Item | Current understanding |
| --- | --- |
| Issue | [2-4 concrete sentences: the specific problem/request in the user's terms, where it appears, why it matters, and the nearest thing that is not being requested] |
| Target outcome | [the concrete result this quick task should deliver] |
| Boundaries | Will change: [specific areas, files, commands, workflows, or behavior]. Will not change: [specific non-goals]. Escalate if: [condition that no longer fits quick]. |
| Known facts / assumptions | [repository evidence, handoff facts, minimal reads, explicit user constraints, and any safe assumption being made while unknowns remain] |
| Affected surfaces | [implementation, docs, tests, generated assets, state files, CLI/API surfaces, or consumers expected to be touched or checked] |
| Implementation plan | 1. [task-specific first step]; 2. [task-specific second step]; 3. [task-specific third step]; 4. [task-specific fourth step, if needed]; 5. [task-specific verification or closeout step] |
| Next action | [the first implementation, delegation, or preparation action after confirmation] |
| Validation evidence | [tests, commands, manual checks, changed-surface sweep, or other evidence required before closeout] |
| Stop condition | [the exact discovery or risk that will stop quick execution and require a user decision or escalation] |

Reply with `confirm`/`确认` to continue, or `revise: ...`/`修改：...` with corrections.
```

Wait for user confirmation before code edits, broad repository analysis, delegation, implementation commands, or validation commands. If the user corrects the understanding, revise the checkpoint once with the corrected direction and ask for confirmation again.

Create or update `STATUS.md` with `understanding_confirmed: false` before any map maintenance handoff, broad repository analysis, delegation, implementation command, or validation command. Record the confirmed checkpoint in `STATUS.md`. `understanding_confirmed: false` blocks substantive execution on resume. While it is false, only read the minimal context needed to reconstruct or revise the checkpoint; you must not proceed to code edits, broad repository analysis, delegation, validation commands, `{{invoke:map-update}}`, `{{invoke:map-scan}}`, or `{{invoke:map-build}}` until the checkpoint is confirmed and `STATUS.md` is updated.

## Workflow Quality Requirements

- Confirm project cognition freshness and valid quick-task entry before deeper execution.
- Keep `STATUS.md` current as the durable quick-task source of truth for scope, lane state, blockers, verification, and terminal status.
- Validate each `WorkerTaskPacket` or equivalent execution contract before dispatch and require a structured handoff before accepting delegated work.
- Update durable state before compaction-risk transitions, join points, delegated fan-out, or any stop where resume will depend on more than the visible conversation.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader quick-task context.
- Open only learning detail docs linked from quick-task-relevant index entries.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.

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
