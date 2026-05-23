---
description: Use when a new or changed feature request needs guided requirement discovery and a planning-ready specification package.
workflow_contract:
  when_to_use: A new or changed feature request needs a planning-ready specification package instead of immediate implementation.
  primary_objective: 'Produce a reviewed, planning-ready specification package through context exploration, one-question-at-a-time clarification, approach comparison, semantic term decomposition, artifact self-review, and user review.'
  primary_outputs: '`FEATURE_DIR/spec.md`, `FEATURE_DIR/alignment.md`, `FEATURE_DIR/context.md`, `FEATURE_DIR/references.md` when useful, `FEATURE_DIR/workflow-state.md`, `FEATURE_DIR/checklists/requirements.md`, and the minimal compatibility handoff `FEATURE_DIR/brainstorming/handoff-to-specify.json`.'
  default_handoff: 'After user review, recommend exactly one next command: `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.'
handoffs:
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Create a plan for the spec. I am building with...
  - label: Prove Feasibility Before Plan
    agent: sp.deep-research
    prompt: Prove the unverified implementation-chain risks recorded by sp-specify, then hand findings and demo evidence to sp-plan.
    send: true
scripts:
  sh: scripts/bash/create-new-feature.sh "{ARGS}"
  ps: scripts/powershell/create-new-feature.ps1 "{ARGS}"
---

{{spec-kit-include: ../command-partials/specify/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

## Pre-Execution Checks

**Check for extension hooks before specification**:
- Check whether `.specify/extensions.yml` exists in the project root.
- If it exists, read entries under `hooks.before_specify`.
{{spec-kit-include: ../command-partials/common/extension-hooks-body.md}}

**Set the working boundary**:
- Treat the user request as the starting point for a specification, not permission to implement.
- If no feature description was supplied, stop with: `ERROR: No feature description provided`.
- Verify the installed CLI surface with `specify --help` when command availability is uncertain; feature creation uses the generated create-feature script, not an imagined `specify create-feature` command.
- Run `{SCRIPT}` from the repo root to create or resume the feature workspace. For generated projects this resolves to `.specify/scripts/bash/create-new-feature.sh "$ARGUMENTS"` or `.specify/scripts/powershell/create-new-feature.ps1 "$ARGUMENTS"`; Codex-generated skills should run `.specify/scripts/bash/create-new-feature.sh "$ARGUMENTS"` from the repo root for the shell variant.
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
- Check whether `.specify/project-cognition/status.json` exists before trusting project cognition output.
- Run or emulate:

```text
{{specify-subcmd:project-cognition lexicon --intent plan --query="$ARGUMENTS" --format json}}
# Agent: generate <query_plan_json> from raw user intent plus returned map terms.
{{specify-subcmd:project-cognition query --intent plan --query-plan "<query_plan_json>" --format json}}
```

- Prefer project cognition when it is available and fresh, but use it as navigation guidance rather than a source that can override live files or user intent.
- When cognition reports `ready`, use the returned task-local bundle.
- When cognition reports `review`, `needs_update`, or partial coverage, perform the returned minimal live reads and continue with explicit assumptions.
- `needs_update`: record a planning advisory, perform the returned `minimal_live_reads`, and continue without requiring map maintenance during artifact-only specification work.
- If freshness is `stale`, record a planning advisory, perform minimal live reads, and continue when those reads provide enough evidence.
- If freshness is `possibly_stale`, inspect the reported changed paths and review topics, perform minimal live reads, and continue with explicit assumptions when sufficient.
- If task-relevant coverage is insufficient, record a planning advisory and continue with minimal live reads instead of guessing.
- For artifact-only `sp-specify` work, use the project cognition freshness helper as advisory navigation only. Freshness is `missing` when the runtime baseline is absent; freshness is `stale` when source changes may invalidate the returned map; freshness is `support_drift` when support surfaces changed; freshness is `partial_refresh` when the helper reports an incomplete refresh and a `recommended_next_action`; freshness is `possibly_stale` when changed paths overlap `must_refresh_topics` or `review_topics`.
- The coverage-model check should identify owning surfaces and truth locations, consumer or adjacent surfaces likely to be affected, change-propagation hotspots, verification entry points, and known unknowns or stale evidence boundaries.
- Coverage is insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- When cognition reports `ambiguous`, ask the user to select the intended candidate before writing artifacts.
- When cognition reports `needs_rebuild` or `blocked`, report the blocking issue and the required project-map command instead of guessing.
- Carry material repository facts into `context.md` and `alignment.md`; do not leave planning-relevant facts only in transient tool output.
- Cognition follow-up: if artifact-only specification work identifies future modules, workflows, integration boundaries, verification surfaces, or ownership facts that the current query-backed runtime does not yet encode, record that as an advisory in `workflow-state.md`, `alignment.md`, or `context.md`; do not mark project cognition dirty or require a refresh until actual source/runtime changes make the runtime truth out of date.

## Discussion Source-File Sweep

When `sp-specify` starts from `sp-discussion`, do not trust only the handoff summary.

- Read `handoff-to-specify.md` when supplied or discoverable.
- Read `handoff-to-specify.json` when present and preserve compatibility fields such as `entry_source: sp-discussion`, `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count`.
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
- Extract every upstream capability-like signal from the handoff and source files. Capability-like signals include words and phrases around capability, real, usable, works, end-to-end, fetch, probe, health, model, endpoint, integration, auth, `能力`, `真实`, and `可用`.
- For each signal, write exactly one `source_signal_disposition` row:
  - `preserved`
  - `in_scope`
  - `deferred`
  - `dropped`
  - `clarification_blocker`
- Planning readiness is blocked when a capability-like upstream signal has no disposition, when a narrowed interpretation is not user-confirmed, or when an upstream signal is put out of scope without confirmation and a reopen trigger.
- Preserve the disposition ledger in both `alignment.md` and the minimal compatibility `brainstorming/handoff-to-specify.json`.
- If Markdown and JSON mismatch on user-confirmed scope, quality gate, or must-preserve identity, record the mismatch and route back to refresh the handoff instead of silently repairing it.

## Clarification Loop

- The user's text is the starting point, not the finished requirement package. Analyze the whole feature first and produce a planning-ready requirement package, not a surface summary.
- Run the anti-surface warning signs check before treating the request as planning-ready. Words like "simple", "intuitive", "robust", or "clean" are not requirements when boundary conditions, failure behavior, or affected neighboring workflow remain unclear, when there is still no acceptance proof for how success will be judged, or when the proposed behavior may conflict with the current owning module or existing repository pattern.
- Do not release `Aligned: ready for plan` when the current understanding still depends on taste words, implicit defaults, untested assumptions, or missing behavior boundaries, failure handling, compatibility impact, and acceptance-shaping detail.
- Treat phrases such as "make it more intuitive", "handle permissions normally", "keep it compatible", "show an error if something goes wrong", "use the existing pattern", "it should feel fast", "just validate the data properly", "admins can handle the special cases", and "don't break existing clients" as prompts to convert the vague intent into concrete behavior, edge handling, compatibility scope, or acceptance evidence.
- Classify unresolved vague wording as a vague success standard, vague data rule, vague permission boundary, or vague compatibility claim. Terms such as "fast", "smooth", "easy", "clear", or "works well"; "valid", "clean", "normalized", or "properly formatted"; "normal permissions", "admin behavior", or "authorized users"; and "keep compatibility" or "don't break clients" require concrete acceptance-shaping details before planning handoff.
- Run an engineering-completeness gate for boundary-sensitive work. Capture the trigger/event source when behavior depends on a cross-component signal, payload, identifiers, ordering, or delivery contract, state lifecycle, retention, archival, or cleanup expectations, retry/dedup/idempotency expectations for async or event-driven behavior, user-visible failure, stale-state, or recovery behavior, configuration surface and when changes take effect, and observability or support evidence needed to diagnose failures.
- If the user already described the desired UX in natural language, preserve that product behavior while avoiding forcing a transport or browser-API choice unless the requirement truly demands it.
- Do not release for cross-boundary or event-driven features while the trigger or event source, retry, deduplication, idempotency, or replay expectations are still unknown.
- Conversation memory is not a valid handoff surface. An unknown is not an ignored value; record each unresolved planning-critical item as `resolve-now`, `resolve-by-evidence`, `defer-with-contract`, or `waive-with-risk`, and reopen upstream truth when the current specification depends on a missing or contradictory source.
- Ask one high-impact question at a time.
- Ask at most one unanswered high-impact question per message.
- Ask exactly one unresolved high-impact question per turn.
- A question is high-impact when its answer can change scope, acceptance, architecture, compatibility, security, data shape, external integration, UX behavior, migration path, or downstream planning.
- Run a high-impact ambiguity scan across targeted repository evidence and user-supplied references, examples, or linked material.
- Identify 3-5 planning-relevant gray areas before choosing the next single question.
- Derive gray areas from the combination of user intent, the project cognition runtime, and targeted repository evidence. Do not use generic labels like "UX", "behavior", or "data handling".
- Each gray area should be captured internally with: why the decision changes implementation or test shape, desired happy-path behavior, edge case or failure-path behavior, and compatibility, migration, or neighboring-workflow impact.
- Do not batch unrelated high-impact questions. Ask, receive the answer, update the understanding, then decide whether another question is still necessary.
- each clarification turn should contain at most one short checkpoint.
- Do not ask a second high-impact question before the first one is closed.
- Grouped questions are allowed only when the current domain is already narrowed to a local low-risk scope.
- Make the next question build directly on the user's most recent answer rather than resetting to generic prompts.
- If the user's answer remains vague, shallow, or contradictory, ask a targeted narrowing question, example, or recommendation. Do not accept long but still ambiguous answers as sufficient.
- Do not turn this into a freeform brainstorming workflow. Keep it as guided requirement discovery.
- Default to concise clarification turns. Do not restate the full current understanding after every answer. Save the full synthesis for the alignment-ready turn.
- Do not repeat the same question unless the user's answer changes the prior premise or explicitly asks to revisit it.
- If the runtime exposes separate progress/commentary and final reply channels, keep progress in commentary and ask the current clarification question in the final user-visible reply. The user should see the current clarification question exactly once.
- Before generating any clarification question, confirmation, or bounded selection, check whether a native structured question tool is available. If a native structured question tool is available, you must use it.
- When using a native structured question tool, map the same stage header plus topic label into the native header or title field.
- Do not render the textual fallback block when the native tool is available. Do not self-authorize textual fallback because the question seems simple. Only fall back after the native tool is unavailable or the tool call fails.
- Treat the shared open question block structure below as fallback-only text format guidance.
- Use this open question block structure in the user's current language when rendering the textual fallback block: stage header, question header, prompt, example, recommendation, options, and reply instruction.
- Keep recommendation and example scaffolding short and specific.
- Low-risk defaults may be adopted without interrupting the user, but record them as assumptions in `alignment.md`.
- If the user explicitly accepts unresolved risk, record the risk and use `Force proceed with known risks`; otherwise unresolved planning-critical ambiguity routes to `/sp.clarify`.

## Semantic Term Decomposition

- Decompose ambiguous product terms before writing the final spec.
- If the request contains 2 or more distinct deliverables, enhancements, or behavior changes that would independently change implementation or validation shape, decompose it into capabilities. Present the capability split before asking any detailed clarification question about one capability.
- Label that preview as the proposed capability split so the user can correct the grouping.
- Default to one spec with capability decomposition when the work still belongs to one coherent feature boundary.
- Help the user decompose it into bounded capabilities inside the same spec first.
- Only escalate to separate specs or clearly phased releases when one spec would no longer be coherent to plan or test.
- Do not jump straight into a detailed gray-area question while multiple sibling capabilities are still unsplit or unprioritized.
- confirm which capability should be clarified first while keeping the work in the current spec unless the user explicitly wants separate specs or phased release planning.
- Do not spend one clarification pass collecting requirements for multiple independent capabilities.
- If the request is already one bounded capability, say so briefly and continue inside the current spec.
- Use this section in `alignment.md` for high-value terms whose meanings could change the delivered product:

Use a simple row per term:

- Term: [ambiguous user term]
- Possible Meanings: [meaning A; meaning B; meaning C]
- Selected Meanings: [confirmed selected meanings]
- Excluded Meanings: [confirmed exclusions]
- User Confirmation: [who/when or missing]

- If selected or excluded meanings are missing user confirmation and the term is product-critical, keep the package out of planning-ready state.
- Scope reduction requires confirmation. Do not convert a broad request into an MVP, prototype, demo, or smaller delivery unless the user requested it or explicitly accepted the narrower version.

## Approach Comparison

- Present two or three approaches before committing to the spec shape.
- For a requirement-shaping decision, switch into decision-fork mode and present 2-3 concrete options when the choice changes behavior, boundary, compatibility, or acceptance proof.
- Do not use this mode for implementation architecture brainstorming.
- For each approach, summarize product fit, implementation risk, user-visible trade-offs, compatibility impact, and verification implications.
- Recommend one approach and explain why it best preserves the user's stated intent.
- If the user chooses a different approach, record that as a locked decision rather than re-litigating it later.

## Spec Section Approval

- Before final artifact release, present the intended spec section shape for user approval.
- The review preview must cover:
  - goal and users
  - confirmed scope
  - out-of-scope and deferred items
  - capability decomposition
  - acceptance proof
  - semantic term decisions
  - upstream signal dispositions
  - open questions or known risks
- If the user requests changes, update the working understanding before writing final artifacts.

## Artifact Writing Contract

Write the specification package after context intake, necessary clarification, semantic decomposition, approach comparison, and section approval.

- `spec.md` must capture the product requirement in planning-ready form with confirmed scope, scenarios, capability decomposition, requirements, acceptance proof, decision capture, and risks.
- `alignment.md` must capture current understanding, confirmed facts, assumptions, open questions, `Semantic Term Decisions`, `Upstream Intent Disposition`, `Out-Of-Scope Conflicts`, must-preserve coverage, and readiness decision.
- `context.md` must capture planning context, repository context, reuse notes, integration boundaries, product constraints, change propagation, locked decisions, canonical references, open questions, and deferred ideas.
- `references.md` is optional and should be written when external docs, repository examples, issue links, discussion artifacts, or user-provided references materially shaped the spec.
- `workflow-state.md` must record current stage, review state, source-file sweep status, source-signal disposition status, final handoff decision, and next command.
- `checklists/requirements.md` must exist for first-release compatibility and must validate the written spec, not resurrect legacy state machinery.
- `brainstorming/handoff-to-specify.json` must exist as a minimal compatibility handoff for downstream commands. It must include:
  - `version`
  - `status`
  - `entry_source`
  - `source_handoff`
  - `source_handoff_json`
  - `source_files_read`
  - `source_signal_disposition`
  - `must_preserve`
  - `coverage_status`
  - `planning_gate_status`
  - `hard_unknown_count`
  - `open_conflict_count`
  - `quality_gate`
- Preserve fidelity requirements and reference behavior inventory when the feature is reference-sensitive or rewrite-style.
- Preserve Senior Consequence Analysis Gate outputs as `CA-###` obligations when triggered: affected object map, state-behavior matrix, dependency impact table, recovery and validation contract, coverage gaps, lifecycle operations, running state behavior, destructive operations, shared state, downstream consumers, and stand-down reason.

## Artifact Self-Review

Before reporting completion, review the written artifacts, not just the chat summary. Review the written `spec.md`, `alignment.md`, and `context.md` as the minimum artifact set.

- No placeholders, TODOs, stale markers, or unresolved clarification markers remain unless the package is explicitly not planning-ready.
- If high-risk artifact review triggers, a read-only reviewer lane MUST run before handoff. If no high-risk review trigger is present, a reviewer lane MUST NOT be added. Review routing is condition-triggered, not preference-triggered.
- Requirements are testable and unambiguous.
- `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`, and the compatibility handoff do not contradict each other.
- Every discussion-originated capability-like upstream signal has a disposition row.
- Every deferred or dropped upstream signal has a source, reason, user confirmation status, and reopen trigger.
- Every out-of-scope conflict with upstream wording is recorded in `Out-Of-Scope Conflicts`.
- Acceptance proof matches the confirmed scope.
- UI/API wording in the spec does not imply deferred capabilities are already real.
- If the self-review finds planning-critical gaps, update the artifacts and repeat the review before closeout.

## User Review Gate

- Ask the user to review the written artifact set before planning.
- Present a current-understanding summary as a misunderstanding-correction gate and ask the user to confirm or correct the current understanding before the final handoff decision is locked.
- Summarize what was confirmed, what remains open, what was deferred or dropped, and what risk remains.
- Use the user's current language for the review summary and cover Business Goals, Users & Roles, confirmed product scope, user-confirmed delivery sequence, business rules, Technical Constraints / Assumptions, confirmed decisions, and Outstanding Questions.
- If the user requests artifact edits, stay in `sp-specify`, update the artifacts, and repeat artifact self-review.
- Recommend exactly one next command:
  - `/sp.plan` when the artifact package is `Aligned: ready for plan`.
  - `/sp.clarify` when planning-critical ambiguity remains.
  - `/sp.deep-research` when requirements are clear enough but feasibility, external evidence, or an implementation-chain proof is still needed.
- Do not present multiple next commands as equally valid.
- No alternative next command is valid for the current state.
- report the single valid next path for the current state. Do not emit a second alternative next command. Do not present multiple downstream command options.
- Only the user review gate may decide whether the canonical next command is `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.
- The completion state must preserve the literal `next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.

## Completion Report

Report completion in the user's current language while preserving literal paths, command names, and fixed status values.

Include:
- branch name
- `spec.md` path
- `alignment.md` path
- `context.md` path
- `references.md` path when created
- `workflow-state.md` path
- `checklists/requirements.md` path
- `brainstorming/handoff-to-specify.json` path
- source-file sweep status
- source-signal disposition status
- readiness decision
- single next command
- cognition follow-up for artifact-only advisory state, if relevant

## Extension Hooks

After the completion report, check whether `.specify/extensions.yml` exists.

- If it exists, read entries under `hooks.after_specify`.
- If YAML cannot be parsed, skip hook execution guidance silently.
- Filter out hooks where `enabled` is explicitly `false`.
- Treat hooks without `enabled` as enabled.
- Do not evaluate non-empty hook conditions directly; leave condition evaluation to the HookExecutor implementation.
{{spec-kit-include: ../command-partials/common/extension-hooks-after-body.md}}

## Quick Guidelines

- Focus on what users need, why they need it, and what a planner must preserve.
- Start with whole-feature understanding before capability details.
- Keep one high-impact question at a time.
- Compare two or three approaches before locking the spec shape.
- Make semantic term narrowing explicit and source-linked.
- Read discussion source files when a discussion handoff exists; the handoff summary is not enough.
- Distinguish confirmed facts, low-risk assumptions, unresolved questions, deferred scope, and dropped scope.
- Avoid implementation design except where a dependency, constraint, boundary, or planning risk must be named.
- Keep generated artifacts concise, reviewable, and useful to `/sp.plan`.
- Do not treat product minimization as the default strategy. Scope reduction requires user confirmation before it can shape `spec.md`.
- Before dispatching independent review or evidence work, use `choose_subagent_dispatch(command_name="specify", snapshot, workload_shape)` and record `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, and `execution_surface: native-subagents` when a validated isolated lane exists. Use `one-subagent` or `parallel-subagents` only for isolated review/evidence lanes, never for source edits.
- Record impacted surfaces and change-propagation expectations, major affected surfaces, verification entry points and minimum evidence expectations, and known unknowns or stale evidence boundaries that could change planning safety.
- Route to `/sp.clarify` when planning-critical ambiguity remains around scope, workflow behavior, constraints, or success criteria.
- Do not recommend `/sp.plan` until the written artifacts pass self-review and user review has been requested.
