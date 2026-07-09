Trigger: when an explicit handoff request is accepted after boundary lock.

Purpose: preserve unified handoff file rules, agent-facing requirement contract fields, Must-Preserve ledger requirements, JSON companion rules, and conflict blockers.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.

## Unified Discussion Handoff

Handoff is explicit-user-request only and follows handoff assessment.

Write exactly one current handoff pair:

- `.specify/discussions/<slug>/handoff-to-specify.md`
- `.specify/discussions/<slug>/handoff-to-specify.json`

These filenames are compatibility names for the unified discussion handoff. Do not write a second quick-specific pair such as `handoff-to-quick.md` or `handoff-to-quick.json`. The same handoff is a `discussion_requirement_contract` that may be consumed by `sp-specify` or `sp-quick` when that consumer's gate passes.

Both files are mandatory. Missing Markdown is invalid because the user-reviewable source is absent. Missing JSON is invalid because downstream workflows need structured boundary, review, and Must-Preserve status. Do not reconstruct a missing JSON companion during handoff; refresh the handoff in `sp-discussion` instead.

`specification-input.md`, `discussion-state.md`, and other discussion source files are supporting evidence only. They are not substitutes for the required handoff pair and must not be offered as a bypass for `handoff-to-specify.md` plus `handoff-to-specify.json`.

The handoff Markdown and JSON must agree on `handoff_kind`, `handoff_goal`, `discussion_slug`, `consumer_eligibility`, `recommended_consumer`, context boundary fields, implementation target fields, quality gate status, Must-Preserve IDs, Senior Consequence Analysis status, and open blockers.

### Handoff Request-Changes Repair

When a handoff review returns `request-changes`, or a downstream consumer reports `blocked_by_handoff_integrity`, the repair belongs to `sp-discussion`. Do not ask `sp-specify`, `sp-quick`, or another consumer to reconstruct, infer, or silently patch the handoff pair.

Refresh `handoff-to-specify.md` and `handoff-to-specify.json` together from the current discussion source files, then run handoff self-review again before asking the user to approve `handoff-ready`. Keep the discussion in draft/user-review state until the refreshed pair passes self-review and the user confirms it.

The refreshed JSON companion must include the downstream consumption fields needed by `sp-specify` and `sp-quick`:

- `version`
- `status`
- `entry_source: sp-discussion`
- `discussion_slug`
- `source_handoff`
- `source_handoff_json`
- `source_files_read`
- `handoff_status`
- `planning_gate_status`
- `coverage_status`
- `hard_unknown_count`
- `open_conflict_count`
- `quality_gate`
- `consumer_eligibility`
- `recommended_consumer`
- `source_evidence`
- `blocking_unknowns`
- `downstream_instructions`
- `discussion_decision_digest`

Synchronize every protected fact carried in Markdown into JSON, especially source evidence, Must-Preserve IDs and claims, `CA-###` obligations, hard/soft unknown status, open conflict status, quality gate status, planning gate status, and coverage status. If Markdown has evidence entries that JSON omits, or JSON has stale draft status while Markdown claims readiness, keep the handoff blocked and refresh the pair in `sp-discussion`.

Soft unknowns that remain open must be carried forward explicitly with owner, latest resolve phase, and stop-and-reopen condition, or marked as waived/non-blocking assumptions with why they do not change scope, acceptance, planning readiness, or downstream implementation authority.

## Agent-Facing Requirement Contract

The unified handoff is primarily for downstream agents, not a transcript. Write the main handoff body as a requirement definition contract:

You are the Agent owning the requirement definition. Discuss only the target need, constraints, success criteria, design direction, and optimal solution approach. Do not describe current execution or implementation progress.

The agent-facing contract must include:

- `handoff_kind`: `discussion_requirement_contract`
- `agent_requirement_contract.target_need`: the target need in product-owner language
- `agent_requirement_contract.constraints`: hard constraints, non-goals, forbidden drift, compatibility boundaries, and relevant project rules
- `agent_requirement_contract.success_criteria`: observable success criteria and acceptance signals
- `agent_requirement_contract.design_direction`: selected product, UX, workflow, or technical design direction without implementation progress narration
- `agent_requirement_contract.optimal_solution_approach`: the recommended approach and why it best preserves the user's intent
- `agent_requirement_contract.scope`: `in`, `out`, and `deferred` scope
- `consumer_eligibility`: independent readiness verdicts for `sp-specify` and `sp-quick`
- `recommended_consumer`: `sp-specify`, `sp-quick`, or `continue-discussion`
- `quick_task_candidate`: bounded quick-task scope, excluded scope, expected changed surfaces, validation route, consequence model, whether `requires_spec_first`, and a Quick Checkpoint seed

Do not put current execution status, artifact write progress, "I checked X" narration, or workflow bookkeeping in the agent-facing contract unless it is evidence, a source file reference, or a readiness gate field. Keep recovery and audit details in `discussion-state.md`, `discussion-log.md`, or reviewer-only sections.

The handoff must include:

- `handoff_goal`: one concrete statement of what is being handed downstream
- `consumer_eligibility`: readiness for `sp-specify` and `sp-quick`, each with status and reason
- `recommended_consumer`: the recommended next consumer or `continue-discussion`
- `quick_task_candidate`: quick-task boundedness, excluded scope, changed surfaces, validation route, consequence model, `requires_spec_first`, and Quick Checkpoint seed
- `context_boundary`: `current_project_root`, `current_project_roles`, `target_project_root`, `target_project_roles`, `reference_projects`, `external_systems`, `path_status`, `boundary_confidence`, and `boundary_unknowns`
- role objects in `current_project_roles` and `target_project_roles`, each with `role`, `scope`, `evidence_source`, and `notes`
- `implementation_target`: actual project to change, target root path when local, target paths or modules, target paths still to verify, target project cognition status, and the statement that current project cognition cannot prove another project's implementation facts
- `source_evidence`: structured evidence entries with `source_type`, `evidence_status`, `source`, `claim`, optional `project_cognition_route`, optional `live_code_evidence`, optional `needs_refresh`, and optional `notes`. Project cognition route entries are advisory unless paired with live code, test, script, config, docs, external source, explicit assumption, or user confirmation evidence.
- `blocking_unknowns`: hard unknowns that block readiness and soft unknowns with owner, latest resolve phase, and stop-and-reopen condition
- `downstream_instructions`: settled decisions, assumptions to preserve, conflicts requiring return to `sp-discussion`, capability map, dependencies, planning constraints, deferred scope, and reopen conditions. Do not include an ordered implementation sequence; sequencing belongs to `sp-plan`.
- `discussion_decision_digest`: the compact decision-intent layer that downstream consumers must preserve instead of flattening the discussion into generic requirements. Include `locked_direction`, `rejected_alternatives`, `accepted_tradeoffs`, `experience_commitments`, `review_criteria_carried_forward`, and `must_not_dilute`. Source each item from `requirements.md`, `technical-options.md`, `project-context.md`, the `Handoff Reviewer Guide`, or explicit user confirmation. This digest must not let downstream workflows rediscover or flatten the selected direction, rejected alternatives, accepted tradeoffs, UI/TUI experience commitments, review criteria, or forbidden simplifications.
- `ui_discussion`: `ui_discussion_status`, confirmed UI decisions, deferred UI decisions, interaction expectations, state requirements, accessibility expectations, and whether ASCII sketches are present
- `ui_sketch_reference`: Markdown section reference for ASCII sketches when `ui_sketches_present` is true
- `handoff_reviewer_guide`: a human-facing Markdown section named `Handoff Reviewer Guide` that tells an experienced product or engineering reviewer what decision they are being asked to make, what to review first, when to approve, and when to request changes. Write it for someone who does not know Spec Kit internals.
- `quality_gate`: `status`, `self_reviewed_at`, `user_review_required`, `user_confirmed_at`, and `blocked_reasons`

## Must-Preserve Ledger

When the user explicitly requests handoff, `handoff-to-specify.md` must include a Must-Preserve Ledger. The ledger preserves only semantic units that would cause product or implementation drift if lost.

Ledger item types:

- `goal`
- `scope`
- `non_goal`
- `scenario`
- `decision`
- `reference`
- `tradeoff`
- `blocking_question`

Each ledger item must include:

- `id`: stable `MP-###`
- `type`: one of the ledger item types
- `claim`: the exact conclusion to preserve
- `source`: source file, reference, or user confirmation
- `downstream_requirement`: how later artifacts must carry this forward
- `blocking_level`: `hard` or `soft`
- `owner`: `user`, `evidence`, `downstream-contract`, or `risk-waiver`
- `latest_resolve_phase`: latest phase allowed to resolve or carry the item
- `status`: `pending`, `mapped`, `resolved`, `deferred`, `superseded`, or `dropped`
- `deferred_to`: downstream phase when status is `deferred`
- `stop_and_reopen_condition`: required for deferred items
- `superseded_by`: replacement item or conflict resolution when status is `superseded`
- `mapped_to`: empty in discussion handoff; populated by `sp-specify`

Include ledger items for confirmed goals, selected scope, non-goals, acceptance-shaping scenarios, selected decisions, critical references, selected or rejected trade-offs whose rationale matters, and blocking open questions.

## Handoff JSON Companion

When `handoff-to-specify.md` is written, also write `.specify/discussions/<slug>/handoff-to-specify.json` with the same ledger item IDs and key fields. These remain compatibility names for the single unified discussion handoff.

The Markdown and JSON forms must agree on every ledger item's `id`, `type`, `claim`, `blocking_level`, `owner`, `latest_resolve_phase`, and `status`.

For UI-facing work, the JSON companion must preserve `ui_discussion_status`, `ui_sketches_present`, `ui_sketch_summary`, and `ui_sketch_reference`. Markdown is the primary carrier for raw ASCII sketches; JSON records only structured status, summary, and reference fields.

If an existing Markdown handoff and JSON companion disagree, block and refresh the handoff instead of choosing one silently.

## Conflict Blocker

If an `MP-*` item conflicts with repository evidence, constitution rules, project rules, project cognition evidence, or architecture constraints, do not silently reinterpret, downgrade, or replace the discussion conclusion. Block and ask the user to choose keep, revise, drop, or defer with an explicit risk contract.

Do not mark the discussion `handoff-ready` until every confirmed or critical item is represented in the Must-Preserve Ledger. Deferred items require `deferred_to`, `owner`, `latest_resolve_phase`, and `stop_and_reopen_condition`. The handoff must preserve `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` fields for downstream coverage.

When the Senior Consequence Analysis Gate triggers, also write or refresh `handoff-to-specify.json` as a mandatory machine-readable mirror of triggered gate status, consequence analysis, `CA-###` obligations, coverage gaps, and stop-and-reopen conditions. Markdown and JSON handoffs must agree on obligation IDs, claims, blocking level, owner, latest resolve phase, status, and stop-and-reopen condition before the discussion can become `handoff-ready`.

After writing a draft handoff, ask the user to review it with the unified frontstage contract and the `Handoff Reviewer Guide`. Tell the user to invoke the generated integration's `sp-specify` or `sp-quick` command form with the same handoff path only after the handoff self-review passes, `quality_gate.status` records user confirmation, and that consumer's `consumer_eligibility` status is ready. Do not invoke it yourself.
