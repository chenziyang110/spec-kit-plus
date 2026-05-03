---
description: Use when an existing specification package has planning-critical gaps, weak analysis, or new constraints that should be absorbed before planning.
workflow_contract:
  when_to_use: The current spec package exists, but planning-critical ambiguity or new evidence makes /sp-plan unreliable.
  primary_objective: Strengthen the existing spec package without rerunning the entire `sp-specify` flow from scratch.
  primary_outputs: Updated `spec.md`, `alignment.md`, `context.md`, `references.md`, and `workflow-state.md` inside the active `FEATURE_DIR`.
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

## Passive Project Learning Layer

- Run `{{specify-subcmd:learning start --command clarify --format json}}` when available so this repair pass can consume existing project rules and learnings.
- When clarification friction appears, run `{{specify-subcmd:hook signal-learning --command clarify ...}}` with user-correction, scope-change, route-change, false-start, or hidden-dependency counts.
- Before final completion or blocked reporting, run `{{specify-subcmd:hook review-learning --command clarify --terminal-status <resolved|blocked> ...}}`.
- Prefer `{{specify-subcmd:learning capture-auto --command clarify --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `{{specify-subcmd:hook capture-learning --command clarify ...}}` when the durable state does not capture the reusable lesson cleanly.

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

2. Create or resume the workflow state:
   - Read `templates/workflow-state-template.md`.
   - If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
   - Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth for `sp-clarify`.
   - Persist at least these fields for the active pass:
     - `active_command: sp-clarify`
     - `phase_mode: planning-only`
     - `allowed_artifact_writes: spec.md, alignment.md, context.md, references.md, workflow-state.md`
     - `forbidden_actions: edit source code, edit tests, fix build/tooling, implement behavior, run implementation-oriented fix loops`
     - `authoritative_files: spec.md, alignment.md, context.md, references.md`
   - When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.

3. Load the current spec package and repo context:
   - `FEATURE_SPEC`
   - `FEATURE_DIR/alignment.md` if present
   - `FEATURE_DIR/context.md` if present
   - `FEATURE_DIR/references.md` if present
   - `.specify/memory/constitution.md` if present
   - `.specify/memory/project-rules.md` if present
   - `.specify/memory/project-learnings.md` if present
   - `PROJECT-HANDBOOK.md` if present
   - the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md`
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
   - Present exactly one unresolved high-impact question at a time.
   - Prefer questions that lock behavior, boundary handling, compatibility, or acceptance proof rather than reopening broad ideation.
   - Use the user's current language for user-visible questions and confirmations.
   - If repository evidence or retained references can answer the gap safely, packetize the artifact update as a validated subagent lane instead of asking the user to restate codebase facts.

7. When justified, use multi-agent research or analysis to deepen the spec:
   - parallelize only when the work naturally separates into independent research tracks
   - examples: external references, local codebase context, risk analysis, comparison of alternatives
   - keep the final output synthesized back into the main spec package instead of returning raw research noise

7a. Decide whether a separate feasibility gate is needed:
   - If the remaining issue is "what should the system do?", keep clarifying in this command.
   - If the remaining issue is "can this capability work with the available APIs, libraries, platform behavior, performance envelope, or integration boundary?", update `alignment.md` and `workflow-state.md` to recommend `/sp.deep-research`.
   - Prefer `/sp.deep-research` when a disposable demo under `FEATURE_DIR/research-spikes/` would prove the implementation chain before planning.
   - Record that `/sp.deep-research` must return a `Planning Handoff` with findings, demo evidence, constraints, rejected options, and recommended approach for `/sp.plan`.
   - Do not require `/sp.deep-research` for minor changes to existing capabilities that already have a clear implementation path in the repository.

8. Delegate artifact enhancements through a validated subagent lane:
   - Build one bounded `WorkerTaskPacket` for the artifact update lane when the write scope is safe and packetized.
   - Allowed writes are limited to `spec.md`, `alignment.md`, `context.md`, `references.md`, and `workflow-state.md` inside `FEATURE_DIR`.
   - The packet must list authoritative inputs, exact artifact sections to strengthen, allowed writes, forbidden actions, acceptance checks, verification evidence, and structured handoff format.
   - The subagent updates `spec.md`, `alignment.md`, `context.md`, `references.md`, and `workflow-state.md` as needed.
   - The subagent strengthens `Locked Decisions`, `Claude Discretion`, `Canonical References`, and `Deferred / Future Ideas` in `spec.md` when relevant.
   - The subagent strengthens `Locked Decisions For Planning`, `Outstanding Questions`, and `Planning Gate Recommendation` in `alignment.md`.
   - The subagent strengthens feasibility / deep research gate status when an implementation-chain proof is needed before planning.
   - The subagent strengthens `Locked Decisions`, `Claude Discretion`, `Canonical References`, `Existing Code Insights`, `Specific User Signals`, and `Outstanding Questions` in `context.md`.
   - The leader owns coordination, packet validation, user-question decisions, structured-handoff review, acceptance, final status, and state consistency.
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
   - remaining planning risks
   - recommended next command
   - whether the spec package is now ready for `/sp.plan`, still needs more clarification, or needs `/sp.deep-research` feasibility proof first
   - whether another `/sp.specify` or `/sp.clarify` pass is still justified before planning
   - updated `workflow-state.md` path
   - if this repair pass proves the current handbook/project-map no longer captures the touched area's ownership, workflow, integration boundary, or verification surface accurately enough, mark `.specify/project-map/index/status.json` dirty through the project-map freshness helper and recommend `/sp-map-scan` followed by `/sp-map-build` before later brownfield implementation proceeds

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
