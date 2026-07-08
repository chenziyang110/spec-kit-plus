Trigger: when arguments are absent, a discussion handoff is supplied, or upstream discussion state affects feature creation.

Purpose: preserve handoff intake, project context, source-file sweep, and upstream signal disposition rules.

Preserved Contract: discussion handoff integrity, target boundary safety, source evidence sweep, and Discussion Decision Digest mapping must remain unchanged.

## Pre-Execution Checks

**Check for extension hooks before specification**:
- Check whether `.specify/extensions.yml` exists in the project root.
- If it exists, read entries under `hooks.before_specify`.
{{spec-kit-include: ../../command-partials/common/extension-hooks-body.md}}

**Resolve discussion handoff intake before feature creation**:
- Classify the supplied arguments before running `{SCRIPT}`:
  - normal feature description
  - `.specify/discussions/<slug>/handoff-to-specify.md`
  - `.specify/discussions/<slug>/handoff-to-specify.json`
  - `.specify/discussions/<slug>/handoff.md` or `.specify/discussions/<slug>/handoff.json` when a generated project has adopted neutral filenames
  - a discussion `<slug>` whose workspace contains the handoff pair
  - no arguments with exactly one unconsumed `status: handoff-ready` discussion whose `next_command` is `/sp.specify` or `sp-specify`
- If no feature description is supplied and there is no exactly-one unconsumed handoff-ready discussion, stop with: `ERROR: No feature description provided`.
- If multiple unconsumed `handoff-ready` discussions exist, stop before creating a feature workspace and ask the user for the specific slug or handoff path.
- When a discussion handoff is selected, treat it as the authoritative upstream input and set `SOURCE_HANDOFF_MD`, `SOURCE_HANDOFF_JSON`, and `SOURCE_DISCUSSION_SLUG`. Do not rediscover or switch to another handoff later in the run.
- Require both `handoff-to-specify.md` and `handoff-to-specify.json` before feature creation. Missing Markdown or JSON is `blocked_by_handoff_integrity`; route back to `sp-discussion` to refresh the pair instead of reconstructing it here.
- Parse the JSON before feature creation and require:
  - `entry_source: sp-discussion`
  - `handoff_kind: discussion_requirement_contract` when present; legacy discussion handoffs without this field may continue only if all other gates pass
  - `consumer_eligibility.sp-specify.status: ready` when `consumer_eligibility` is present
  - `handoff_status: handoff-ready` or source `discussion-state.md` `status: handoff-ready`
  - `planning_gate_status: ready`
  - `quality_gate.status: user_confirmed` or `quality_gate.status: user-confirmed`
  - `hard_unknown_count: 0`
  - `open_conflict_count: 0`
- Check the Markdown for `Handoff Reviewer Guide`, `Quality Gate`, `Must-Preserve Ledger`, and source evidence sections before creating a feature workspace.
- Check Markdown/JSON companion integrity for protected downstream facts: quality gate status, planning gate status, handoff status, `MP-*` IDs and claims, `CA-###` IDs and claims, hard unknowns, open conflicts, and structured `source_evidence` / settled-decision coverage. If the Markdown carries protected source evidence or settled decisions that the JSON omits, block before feature creation and return to `sp-discussion` to refresh the handoff pair.
- If `target_project_root` is present and differs from the current repository root, do not create a feature workspace in the wrong project. Ask the user to run the target project's `sp-specify` with this handoff path, or to confirm that the current repository is the intended target.
- Derive the feature description for `{SCRIPT}` from `handoff_goal` plus the confirmed implementation target summary. Do not pass the raw handoff file path, JSON path, or slug as the feature description.
- Preserve the selected source handoff path and slug for `workflow-state.md`, `alignment.md`, and `brainstorming/handoff-to-specify.json`.
- Treat `handoff-to-specify.*` as compatibility filenames for the unified `discussion_requirement_contract`. Do not require or generate a second consumer-specific discussion handoff.

**Confirmed discussion handoff default continuation**:
- A `handoff-ready` discussion with `quality_gate.status: user_confirmed` is already a user-reviewed upstream contract. Do not add another pre-artifact approval gate merely to re-approve the same recommended approach or section shape.
- When the handoff and source files support exactly one recommended approach, and that approach preserves the confirmed scope, does not narrow the product intent, does not defer or drop an upstream capability signal, does not waive a risk, and does not contradict explicit user input, record `approach_comparison_status: accepted-from-confirmed-handoff` and continue.
- When the proposed spec section shape is a direct projection of the confirmed handoff, has no requested changes, preserves every Must-Preserve item, and leaves no unresolved planning-critical ambiguity, record `section_approval_status: accepted-from-confirmed-handoff` and write the draft spec package.
- The user review gate after artifact writing remains mandatory. That is where the user reviews the produced `spec.md`, `alignment.md`, `context.md`, checklist, and compatibility handoff JSON.
- Ask before writing artifacts only when the decision would reduce scope, drop or defer user-requested capability, select between materially different valid approaches, resolve an out-of-scope conflict, accept unresolved risk, change the target project boundary, or rely on missing/conflicting evidence.
- Do not ask the user to reply `1`, `2`, or `3` when the only pending action is accepting one safe recommended approach or section shape from the confirmed handoff.

**Set the working boundary**:
- Treat the user request as the starting point for a specification, not permission to implement.
- If no feature description or accepted discussion handoff was supplied, stop with: `ERROR: No feature description provided`.
- Verify the installed CLI surface with `specify --help` when command availability is uncertain; feature creation uses the generated create-feature script, not an imagined `specify create-feature` command.
- Run `{SCRIPT}` from the repo root to create or resume the feature workspace using the normal feature description, or the handoff-derived feature description when discussion intake selected a handoff. The default feature workspace name uses a `YYYY-MM-DD-<slug>` prefix; legacy numeric prefixes require the script's explicit `--number` / `-Number` option. For generated projects this resolves to `.specify/scripts/bash/create-new-feature.sh "$ARGUMENTS"` or `.specify/scripts/powershell/create-new-feature.ps1 "$ARGUMENTS"`; Codex-generated skills should run `.specify/scripts/bash/create-new-feature.sh "$ARGUMENTS"` from the repo root for the shell variant.
- If the feature-creation script exits non-zero, stop and report the script error; do not call `specify lane register` or any invented branch command as a substitute.
- After the script succeeds, set:
  - `FEATURE_DIR`
  - `SPEC_FILE`
  - `ALIGNMENT_FILE`
  - `CONTEXT_FILE`
  - `REFERENCES_FILE`
  - `WORKFLOW_STATE_FILE`
- Create or update `workflow-state.md` before substantial analysis. Record `active_command: sp-specify`, `phase_mode: planning-only`, allowed artifact writes, `forbidden_actions`, current stage, next action, and exit criteria.
- Read `templates/workflow-state-template.md`.
- Create or resume `WORKFLOW_STATE_FILE` immediately after `FEATURE_DIR` is known.
- Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth on resume after compaction for the current command, allowed artifact writes, forbidden actions, authoritative files, next action, and exit criteria.
- When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.
- Record `next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research` once user review has been requested and the artifact self-review is complete.
- At the user review gate, record readiness for the next phase (`/sp-plan` for the mainline in integrations that render hyphenated command invocations) while preserving the literal `next_command` token as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.
- Do not edit source code, tests, implementation files, generated build output, or dependency files from this workflow.
- Do not implement code, edit source files, edit tests, or run implementation-oriented fix loops from `sp-specify`.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command specify --format json}}` when available so passive learning files exist and the current specification run sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order when they exist.
- Open only learning detail docs that clearly match the request, repeated workflow gaps, user preferences, or constraints for the affected area.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail document without asking for routine permission.
- Treat passive memory as advisory evidence. Repository evidence and explicit user confirmation outrank older memory.
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command specify --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, validation gaps, or reusable constraints.
- Before closeout, if this specification run exposes a reusable workflow gap, user preference, or project constraint, capture it in the learning layer or record why it is one-off.
- Required options: `--command`, `--type`, `--summary`, `--evidence`.

## Project Context Intake

- Explore project context just enough to understand ownership, constraints, adjacent surfaces, reusable patterns, compatibility boundaries, and likely verification routes.
- **UI Design System Intake**:
  - If the feature has user-interface scope, read `DESIGN.md` when present.
  - Capture Experience Requirements in `spec.md`.
  - Capture design-system readiness in `alignment.md` with `design_system_status`.
  - Capture relevant design references and gaps in `context.md`.
  - Treat missing or insufficient design system as a strong blocker for new product UI, redesign or rebrand, core workflow experience, multi-platform design decisions, and high-visibility customer-facing surfaces.
  - Treat missing design system as a soft risk for small internal form changes, narrow copy or state improvements, already-covered component variants, and low-risk CLI/TUI wording refinements.
- Check whether `.specify/project-cognition/status.json` exists before trusting project cognition output.
- Run or emulate:

```text
{{specify-subcmd:project-cognition compass --intent plan --query="$ARGUMENTS" --format json}}
```

After the default compass packet, run the advanced `lexicon -> semantic_intake -> query` path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, use `project-cognition lexicon --mode catalog` as the alias catalog, write agent-authored `semantic_intake` and `concept_decisions`, then run `project-cognition query --query-plan "<query_plan_json>"`; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `repository_search_terms`, project-language search terms, and facet coverage; do not search only the raw user words before source search. Agent-owned semantic normalization remains mandatory: `agent_normalization` and raw lexicon ranking are bootstrap signals only; if `agent_normalization` is omitted, treat it as `required=false`; use `write_semantic_intake_from_alias_catalog` when needed. Raw lexicon ranking is only a bootstrap; CJK or mixed CJK/ASCII input still requires agent-owned normalization even when positive raw lexical matches exist. The agent still owns translation. Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`.

- Prefer project cognition when it is available and fresh, but use it as navigation guidance rather than a source that can override live files or user intent.
- When compass reports `query_ready`, read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons.
- When compass reports `review` or partial coverage, perform the returned minimal live reads, inspect `coverage_diagnostics`, and continue with explicit assumptions.
- If freshness is `stale`, record a planning advisory, perform minimal live reads, and continue when those reads provide enough evidence.
- If freshness is `possibly_stale`, inspect the reported changed paths and review topics, perform minimal live reads, and continue with explicit assumptions when sufficient.
- If task-relevant coverage is insufficient, record a planning advisory and continue with minimal live reads instead of guessing.
- For artifact-only `sp-specify` work, use the project cognition freshness helper as advisory navigation only. Freshness is `missing` when the runtime baseline is absent; freshness is `stale` when source changes may invalidate the returned map; freshness is `support_drift` when support surfaces changed; freshness is `partial_refresh` when the helper reports an incomplete refresh and a `recommended_next_action`; freshness is `possibly_stale` when changed paths overlap `must_refresh_topics` or `review_topics`.
- The coverage-model check should identify owning surfaces and truth locations, consumer or adjacent surfaces likely to be affected, change-propagation hotspots, verification entry points, and known unknowns or stale evidence boundaries.
- Coverage is insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- When `compass_state=needs_semantic_intake`, write `semantic_intake` from project vocabulary, rerun compass with `--semantic-intake-file`, or use the advanced `lexicon -> semantic_intake -> query` path for explicit concept decisions.
- When cognition reports `needs_rebuild` or `blocked`, report the blocking issue and the required project-map command instead of guessing.
- Carry material repository facts into `context.md` and `alignment.md`; do not leave planning-relevant facts only in transient tool output.
- Cognition follow-up: if artifact-only specification work identifies future modules, workflows, integration boundaries, verification surfaces, or ownership facts that the current query-backed runtime does not yet encode, record that as an advisory in `workflow-state.md`, `alignment.md`, or `context.md`; do not mark project cognition dirty or require a refresh until actual source/runtime changes make the runtime truth out of date.
- If this workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, follow the shared inline closeout contract:

{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}

## Discussion Source-File Sweep

When `sp-specify` starts from `sp-discussion`, do not trust only the handoff summary.

- Use the `SOURCE_HANDOFF_MD`, `SOURCE_HANDOFF_JSON`, and `SOURCE_DISCUSSION_SLUG` selected by pre-feature-creation discussion handoff intake. If a handoff was supplied but intake did not run, stop and run intake before continuing.
- Read the agent-facing requirement contract first: `agent_requirement_contract.target_need`, `constraints`, `success_criteria`, `design_direction`, `optimal_solution_approach`, and `scope`.
- Confirm `consumer_eligibility.sp-specify.status` is `ready` when present; if it is blocked, route back to `sp-discussion` instead of forcing feature creation.
- Re-read `handoff-to-specify.md` and `handoff-to-specify.json` after `FEATURE_DIR` is known and preserve compatibility fields such as `entry_source: sp-discussion`, `handoff_status: handoff-ready`, `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count`.
- When `entry_source: sp-discussion` and `source_handoff` points under `.specify/discussions/<slug>/handoff-to-specify.md`, preserve that slug as the source discussion that must be marked consumed after this command successfully writes and self-reviews the feature specification package.
- Coverage and planning readiness are separate. Use `coverage_status` for upstream signal mapping completeness and `planning_gate_status` for whether downstream planning may proceed.
- Planning gate statuses include `ready`, `blocked_by_hard_unknowns`, `blocked_by_conflict`, `blocked_by_incomplete_coverage`, and `blocked_by_handoff_integrity`.
- Preserve the Must-Preserve Ledger. Every `MP-*` or `MP-###` item must be mapped, deferred, dropped, superseded, or converted into a conflict blocker with source and reopen details.
- Read the handoff-declared source files, not only the handoff summary.
- At minimum inspect these discussion source files when they exist:
  - `discussion-log.md`
  - `requirements.md`
  - `open-questions.md`
- Also inspect `technical-options.md` and `project-context.md` when present or named by the handoff.
- Record every inspected source in `source_files_read`.
- Extract every upstream capability-like signal from the handoff and source files. Capability-like signals include words and phrases around capability, real, usable, works, end-to-end, fetch, probe, health, model, endpoint, integration, auth, `new` command, `<tool> new`, create, scaffold, authoring, template creation, authoring workflow, CLI path, TUI path, `能力`, `真实`, and `可用`.
- For each signal, write exactly one `source_signal_disposition` row:
  - `preserved`
  - `in_scope`
  - `deferred`
  - `dropped`
  - `clarification_blocker`
- Planning readiness is blocked when a capability-like upstream signal has no disposition, when a narrowed interpretation is not user-confirmed, or when an upstream signal is put out of scope without confirmation and a reopen trigger.
- Treat create/scaffold/`new` command/authoring workflow wording as an operation-shaped capability signal, not as documentation garnish. If the user also asked for a small command surface, preserve the capability operation by mapping it to an explicit entry point such as a TUI route, core API, public CLI command, or user-confirmed deferral. Do not silently replace a confirmed create/scaffold operation with manual copy docs, a static template directory, or a template-only note.
- Maintain a capability preservation ledger for any operation-shaped signal whose entry point changes during normalization: upstream expression, selected entry point, artifacts that implement it, acceptance proof, and user confirmation for any narrowing.
- Preserve the disposition ledger in both `alignment.md` and the minimal compatibility `brainstorming/handoff-to-specify.json`.
- If Markdown and JSON mismatch on user-confirmed scope, quality gate, or must-preserve identity, record the mismatch and route back to refresh the handoff instead of silently repairing it.

### Discussion Decision Digest

When the source is `sp-discussion`, build a `Discussion Decision Digest`. This is not just a source-file-read checklist; it is the decision-intent layer that prevents `sp-specify` from flattening discussion value into generic requirements.

Derive the digest from `handoff-to-specify.md`, `handoff-to-specify.json`, `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, and the `Handoff Reviewer Guide`.

The digest must include:

- `locked_direction`: selected direction, source, rationale, and downstream artifact mapping.
- `rejected_alternatives`: option, rejection reason, source, and reopen condition when the alternative could reappear downstream.
- `accepted_tradeoffs`: accepted tradeoff, accepted risk, user confirmation or source, latest allowed resolve phase, and reopen condition.
- `experience_commitments`: UI/TUI shell, key flows, user-visible states, accessibility or copy constraints, `ui_discussion` status, and `ui_sketch_reference` when present.
- `review_criteria_carried_forward`: approval and change-request criteria from the `Handoff Reviewer Guide` that must still shape `sp-specify` artifact review.
- `must_not_dilute`: decisions downstream workflows must not simplify away, such as turning an approved TUI route into documentation-only support, a guided confirmation into a bare prompt, or a real operation into a manual copy step.

Treat every `must_not_dilute` item as a must not dilute constraint: if `sp-specify` cannot preserve it in requirements, acceptance proof, or planning context, block and return to `sp-discussion`.

Write the digest into `alignment.md#Discussion Decision Digest`, summarize it in `spec.md#Decision Capture`, carry planning-relevant items into `context.md#Discussion Decision Carry-Forward`, and mirror it in `brainstorming/handoff-to-specify.json` as `discussion_decision_digest`.

Planning readiness is incomplete when the selected direction, rejected alternatives that matter, accepted tradeoffs, UI/TUI experience commitments, or carried-forward review criteria appear in the discussion sources but have no digest entry and no artifact mapping.
