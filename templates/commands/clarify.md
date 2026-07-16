---
description: Use when an existing specification package has planning-critical gaps, weak analysis, or new constraints that should be absorbed before planning.
workflow_contract:
  when_to_use: The current spec package exists, but planning-critical ambiguity or new evidence makes /sp-plan unreliable.
  primary_objective: Strengthen the existing spec package without rerunning the entire `sp-specify` flow from scratch.
  primary_outputs: Updated `spec.md`, `alignment.md`, `context.md`, `references.md`, `workflow-state.md`, `clarification/handoffs/<lane-id>.json`, `clarification/evidence-index.json`, and `clarification/checkpoints.ndjson` inside the active `FEATURE_DIR`.
  default_handoff: /sp-plan if the package becomes planning-ready; otherwise continue clarification, run another repair pass, or route unproven feasibility through /sp-deep-research.
handoffs:
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Build the plan using the strengthened specification package.
    send: true
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --paths-only
  ps: scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
---

{{spec-kit-include: ../command-partials/clarify/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying shared semantic contracts.

- [semantic work contract](references/semantic-work-contract.md)

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Pre-Execution Checks

**Check for extension hooks (before clarification)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_clarify` key.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable.
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently.

## Outline

Goal: Strengthen an existing spec package after `/sp.specify` by closing planning-critical gaps, correcting misunderstandings, absorbing reference material better, and writing the improved results back into `spec.md`, `alignment.md`, `context.md`, and `references.md`.

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

1. Run `{SCRIPT}` from repo root once (`--json --paths-only` / `-Json -PathsOnly`). Parse:
   - If `FEATURE_DIR` is not already explicit, prefer `{{specify-subcmd:lane resolve --command clarify --ensure-worktree}}` before guessing from branch-only context.
   - When lane resolution returns a materialized lane worktree, continue clarification from that isolated worktree context so the repaired spec package stays bound to the active feature lane.
   - `FEATURE_DIR`
   - `FEATURE_SPEC`
   - optional downstream paths if returned
   - If JSON parsing fails, abort and instruct the user to verify the feature branch environment.
   - Set `ALIGNMENT_FILE` to `FEATURE_DIR/alignment.md`.
   - Set `CONTEXT_FILE` to `FEATURE_DIR/context.md`.
   - Set `REFERENCES_FILE` to `FEATURE_DIR/references.md`.
   - Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.

   Before any artifact or rich-state write, run `{{specify-subcmd:workflow show --feature-dir <feature-dir> --format json}}`. `FEATURE_DIR/workflow-runtime.json` is CLI-owned and this auxiliary workflow must not write it. The expected required-stage owner is `specify`. If the runtime is missing, corrupt, at another stage, or already completed, stop with its blocker or a typed owner handoff naming the observed stage, expected owner, affected files, exact next action, unblock criteria, and resume argv; do not overwrite either state surface to force entry.

2. Create or resume the workflow state:
   - Read `templates/workflow-state-template.md`.
   - If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
   - Treat `WORKFLOW_STATE_FILE` as the resume/evidence source of truth within
     `sp-clarify`; it does not own required-stage order or runtime revision.
   - Persist at least these fields for the active pass:
     - `active_command: sp-clarify`
     - `phase_mode: planning-only`
     - `allowed_artifact_writes: spec.md, alignment.md, context.md, references.md, clarification/handoffs/*.json, clarification/evidence-index.json, clarification/checkpoints.ndjson, workflow-state.md`
     - `forbidden_actions: edit source code, edit tests, fix build/tooling, implement behavior, run implementation-oriented fix loops`
     - `authoritative_files: spec.md, alignment.md, context.md, references.md, clarification/handoffs/*.json, clarification/evidence-index.json`
   - When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.

3. Load the current spec package and repo context:
   - `FEATURE_SPEC`
   - `FEATURE_DIR/alignment.md` if present
   - `FEATURE_DIR/context.md` if present
   - `FEATURE_DIR/references.md` if present
   - `.specify/memory/constitution.md` if present
   - `.specify/memory/project-rules.md` if present
   - compact `learning start --command clarify` results and only selected `learning show` records
   - **Project cognition gate:** query the active project's runtime before broad
     repository reads.

     Run or emulate:

     ```text
     {{specify-subcmd:project-cognition compass --intent plan --query="$ARGUMENTS" --format json}}
     ```

     After the default compass packet, run the advanced `lexicon -> semantic_intake -> query` path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, use `project-cognition lexicon --mode catalog` as the alias catalog, write agent-authored `semantic_intake` and `concept_decisions`, then run `project-cognition query --query-plan "<query_plan_json>"`; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `repository_search_terms`, project-language search terms, and facet coverage; do not search only the raw user words before source search. Agent-owned semantic normalization remains mandatory: `agent_normalization` and raw lexicon ranking are bootstrap signals only; if `agent_normalization` is omitted, treat it as `required=false`; use `write_semantic_intake_from_alias_catalog` when needed. Raw lexicon ranking is only a bootstrap; CJK or mixed CJK/ASCII input still requires agent-owned normalization even when positive raw lexical matches exist. The agent still owns translation. Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`.

     Use the returned readiness:

     - `query_ready`: read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons.
     - `review`: perform only the returned `minimal_live_reads` before continuing and inspect `coverage_diagnostics`.
     - `needs_rebuild`: route by `recommended_next_action.action_id`, not readiness alone. Preserve resumable actions such as `complete_scan_packets`; only `action_id=project_cognition.rebuild` may consume `rebuild_reasons[]` and `recommended_next_action.workflow_routes.classic.steps` as a rebuild handoff.
     - `blocked`: report the blocking runtime issue and continue with live evidence only where this workflow allows degraded navigation.
     - **CARRY FORWARD**: Use project-cognition facts to decide whether an
       apparent requirement gap is already answered by repository truth. Preserve
       selected ownership, boundary, ambiguity, and verification facts in the
       clarified spec package before routing back to planning.
   - relevant repository documentation and design artifacts when they materially affect the requested change

4. Identify what needs enhancement:
   - shallow or surface-level capability analysis
   - missing scenarios or usage paths
   - unresolved contradictions
   - underused reference material
   - newly provided requirements or constraints
   - unresolved gray areas that still change plan structure
   - unproven feasibility or implementation-chain links that make `/sp.plan` guess
   - missing locked decisions, canonical references, or deferred-scope notes
   - gaps that would make `/sp.plan` less reliable

5. Classify findings by severity:
   - high-impact gaps that require user confirmation
   - lower-risk gaps that can be safely converted into a validated artifact-update subagent lane from current context

6. Clarification loop for high-impact gaps:
   - Ask only the minimum number of questions required to make planning reliable again.
   - Do not use scope minimization as a shortcut to resolve ambiguity. Preserve the user's confirmed product scope; scope reduction requires user confirmation or a named constraint that blocks reliable planning.
   - Present exactly one unresolved high-impact question at a time.
   - Prefer questions that lock behavior, boundary handling, compatibility, or acceptance proof rather than reopening broad ideation.
   - Use the user's current language for user-visible questions and confirmations.
   - If repository evidence or retained references can answer the gap safely, packetize the artifact update as a validated subagent lane instead of asking the user to restate codebase facts.

7. When justified, use multi-agent research or analysis to deepen the spec:
   - parallelize only when the work naturally separates into independent research tracks
   - examples: external references, local codebase context, risk analysis, comparison of alternatives
   - keep the final output synthesized back into the main spec package instead of returning raw research noise
   - before dispatching any clarification lane, persist a `clarification_checkpoint` record to `clarification/checkpoints.ndjson` with the lane id, lane type, authoritative inputs, expected handoff path, and current workflow-state summary
   - each delegated clarification lane must persist the lane's structured handoff to `clarification/handoffs/<lane-id>.json` before the leader accepts the lane, waits at a join point, or updates `spec.md`, `alignment.md`, `context.md`, or `references.md`
   - update `clarification/evidence-index.json` after each accepted lane handoff with lane id, handoff path, source artifacts inspected, questions or constraints resolved, affected artifact sections, blocker status, and integration status
   - consume `clarification/evidence-index.json` before final artifact updates: for every accepted handoff, mark the handoff as `integrated`, `deferred`, or `blocked`, and name the target `spec.md`, `alignment.md`, `context.md`, or `references.md` section that consumed it
   - do not update `spec.md`, `alignment.md`, `context.md`, or `references.md` from chat-only lane results; if a lane reports only prose, idle state, or an unwritten handoff, mark `subagent-blocked`, write the blocker to `workflow-state.md`, and stop or re-dispatch with a valid handoff path
   - when resuming after compaction, re-read `workflow-state.md`, `clarification/checkpoints.ndjson`, `clarification/evidence-index.json`, and all accepted `clarification/handoffs/<lane-id>.json` files before continuing clarification synthesis

7a. Decide whether a separate feasibility gate is needed:
   - If the remaining issue is "what should the system do?", keep clarifying in this command.
   - If the remaining issue is "can this capability work with the available APIs, libraries, platform behavior, performance envelope, or integration boundary?", update `alignment.md` and `workflow-state.md` to recommend `/sp.deep-research`.
   - Prefer `/sp.deep-research` when a disposable demo under `FEATURE_DIR/research-spikes/` would prove the implementation chain before planning.
   - Record that `/sp.deep-research` must return a `Planning Handoff` with findings, demo evidence, constraints, rejected options, and recommended approach for `/sp.plan`.
   - Do not require `/sp.deep-research` for minor changes to existing capabilities that already have a clear implementation path in the repository.

7b. Consequence Clarification Lane:
   - If existing artifacts contain a triggered Senior Consequence Analysis Gate, preserve every `CA-###` consequence obligation from `spec.md`, `alignment.md`, `context.md`, `references.md`, and `workflow-state.md`.
   - Use clarification questions to resolve product semantics for affected objects, lifecycle states, dependency impact, recovery behavior, validation proof, and coverage gaps that still block planning.
   - For every clarified consequence obligation, record whether the obligation is resolved, deferred with a latest safe resolve phase, or converted into a stop-and-reopen condition.
   - Must not drop `CA-###` consequence obligations, stop-and-reopen conditions, stand-down reasons, or coverage gaps just because the current clarification pass focuses on another requirement.
   - If a consequence obligation cannot be answered from repository evidence or user clarification, preserve it as open and route to `/sp.deep-research` or `/sp.plan` only when that downstream workflow can carry the unresolved obligation safely.

8. Delegate artifact enhancements through a validated subagent lane:
   - Build one bounded `WorkerTaskPacket` for the artifact update lane when the write scope is safe and packetized.
   - Allowed writes are limited to `spec.md`, `alignment.md`, `context.md`, `references.md`, `workflow-state.md`, and the clarification evidence files under `clarification/` inside `FEATURE_DIR`.
   - The packet must list authoritative inputs, exact artifact sections to strengthen, allowed writes, forbidden actions, acceptance checks, verification evidence, and structured handoff format.
   - The subagent updates `spec.md`, `alignment.md`, `context.md`, `references.md`, and `workflow-state.md` as needed.
   - The subagent strengthens `Locked Decisions`, `Claude Discretion`, `Canonical References`, and `Deferred / Future Ideas` in `spec.md` when relevant.
   - The subagent strengthens `Locked Decisions For Planning`, `Outstanding Questions`, and `Planning Gate Recommendation` in `alignment.md`.
   - The subagent strengthens feasibility / deep research gate status when an implementation-chain proof is needed before planning.
   - The subagent strengthens `Locked Decisions`, `Claude Discretion`, `Canonical References`, `Existing Code Insights`, `Specific User Signals`, and `Outstanding Questions` in `context.md`.
   - The leader owns coordination, packet validation, user-question decisions, structured-handoff review, acceptance, final status, and state consistency.
   - Each accepted artifact-update lane handoff must be referenced from `clarification/evidence-index.json`, and the final artifact updates must name the handoff paths that shaped resolved questions, retained risks, or escalations.
   - Do not mark clarification complete while `clarification/evidence-index.json` contains an accepted handoff without an explicit consuming artifact section, deferral, or blocker reason.
   - If the artifact update lane cannot be safely packetized or delegated, record `subagent-blocked` in `workflow-state.md` with the escalation or recovery reason and stop instead of making the artifact edits.

9. Maintain a clean output contract:
   - preserve confirmed facts
   - expand low-risk inferences only when they are useful for planning
   - clearly identify what remains unresolved
   - do not imply the spec package is planning-ready if planning-critical gaps still remain

10. Report completion with:
   - sections touched
   - whether multi-agent research was used
   - updated paths
   - clarification evidence paths: `clarification/evidence-index.json`, `clarification/checkpoints.ndjson`, and accepted `clarification/handoffs/<lane-id>.json` files
   - remaining planning risks
   - recommended next command
   - whether the spec package is now ready for `/sp.plan`, still needs more clarification, or needs `/sp.deep-research` feasibility proof first
   - whether another `/sp.specify` or `/sp.clarify` pass is still justified before planning
   - updated `workflow-state.md` path
   - cognition follow-up: if artifact-only clarification work proves later implementation should refresh ownership, workflow, integration boundary, or verification-surface cognition, record that as an advisory in `workflow-state.md`, `alignment.md`, or `context.md`; do not mark project cognition dirty or require a refresh until actual source/runtime changes make the runtime truth out of date.
   - If this workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, follow the shared inline closeout contract:

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

## Presentation Contract

When communicating findings and completion, use a structured terminal presentation built from open blocks with:

- a stage header that identifies `clarify` and the current repair state
- a status block that summarizes whether the spec package was strengthened, partially strengthened, or is waiting on user confirmation
- an explanation block that explains what changed, which planning-critical gaps were reduced, and why it matters for planning
- a risk block that lists unresolved planning risks, remaining contradictions, or evidence gaps
- a next-step block that gives the recommended next command and whether more enhancement work is still needed before `/sp.plan`
- when the package is still not planning-ready, the next-step block must avoid implying an automatic handoff to `/sp.plan`

## Rules

- Use the user's current language for user-visible output unless literal command names, file paths, or fixed status values must remain unchanged.
- Do not re-run the entire `specify` flow from scratch unless the current spec is unusably wrong.
- Prefer targeted enhancement over full restatement.
- If new information materially changes scope or alignment, update `alignment.md` in the same pass.
- Treat `/sp.clarify` as the default rescue lane and repair lane when planning-critical ambiguity remains after `/sp.specify`.
- If high-impact ambiguity remains after enhancement, recommend another clarification pass instead of implying that `/sp.plan` is now safe.
- If requirements are clear but feasibility is unproven, recommend `/sp.deep-research` instead of implying that `/sp.plan` is now safe.

## Post-Execution Checks

**Check for extension hooks (after clarification)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.after_clarify` key.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable.
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently.
