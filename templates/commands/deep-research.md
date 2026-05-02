---
description: Use when a planning-ready spec still has feasibility risk and needs coordinated research, evidence packets, or disposable demo spikes before implementation planning.
workflow_contract:
  when_to_use: The current spec package exists, but one or more capabilities do not yet have a credible implementation chain.
  primary_objective: Coordinate focused research and isolated prototype evidence, synthesize implementation-chain decisions, and produce a planning handoff before /sp-plan.
  primary_outputs: '`FEATURE_DIR/deep-research.md` with `Planning Handoff`, optional `FEATURE_DIR/research-spikes/`, updated `alignment.md`, `context.md`, `references.md`, and `workflow-state.md`.'
  default_handoff: /sp-plan when feasibility is proven or explicitly accepted; otherwise /sp-clarify for requirement gaps or stop with blocked research risks.
handoffs:
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Build the implementation plan using the Planning Handoff, research-agent findings, and demo evidence from deep-research.
    send: true
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --paths-only
  ps: scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
---

{{spec-kit-include: ../command-partials/deep-research/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Pre-Execution Checks

**Check for extension hooks (before deep research)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_deep_research` key.
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

**Run first-party workflow quality hooks once `FEATURE_DIR` is known**:
- Use `{{specify-subcmd:hook preflight --command deep-research --feature-dir "$FEATURE_DIR"}}` before deeper workflow execution so stale brownfield routing or invalid workflow entry is caught by the shared product guardrail layer.
- After `WORKFLOW_STATE_FILE` is created or resumed, use `{{specify-subcmd:hook validate-state --command deep-research --feature-dir "$FEATURE_DIR"}}` so the shared validator confirms `workflow-state.md` matches the `sp-deep-research` contract.
- Before final handoff, use `{{specify-subcmd:hook validate-artifacts --command deep-research --feature-dir "$FEATURE_DIR"}}` so the required `deep-research.md` and `workflow-state.md` set is machine-checked.
- Before compaction-risk transitions or after prototype evidence is synthesized, use `{{specify-subcmd:hook checkpoint --command deep-research --feature-dir "$FEATURE_DIR"}}` to emit a resume-safe checkpoint payload from `workflow-state.md`.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command deep-research --format json}}` when available so the research pass sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader command-local context.
- Review `.planning/learnings/candidates.md` only when it still contains candidates relevant to feasibility, hidden dependencies, prototype failures, or repeated research gaps.
- [AGENT] When feasibility friction appears, run `{{specify-subcmd:hook signal-learning --command deep-research ...}}` with route-change, false-start, hidden-dependency, command-failure, or validation-failure counts.
- [AGENT] Before final completion or blocked reporting, run `{{specify-subcmd:hook review-learning --command deep-research --terminal-status <resolved|blocked> ...}}`.
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command deep-research --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `{{specify-subcmd:hook capture-learning --command deep-research ...}}` when the durable state does not capture the reusable lesson cleanly.

## Workflow Phase Lock

- [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial research.
- Read `templates/workflow-state-template.md`.
- If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
- Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth on resume after compaction for the current command, allowed artifact writes, forbidden actions, authoritative files, next action, and exit criteria.
- Set or update the state for this run with at least:
  - `active_command: sp-deep-research`
  - `phase_mode: research-only`
  - `allowed_artifact_writes: deep-research.md, research-spikes/, alignment.md, context.md, references.md, workflow-state.md`
  - `forbidden_actions: edit production source code, edit tests, fix build/tooling, implement behavior, commit prototype code as production`
  - `authoritative_files: spec.md, alignment.md, context.md, references.md, deep-research.md`
  - `track_exit_states`: per TRK-### exit state
  - `evidence_packet_acceptance`: accepted and rejected packet lists with reasons
  - `failed_readiness_checks`: list of check IDs that failed
  - `open_gaps`: gap ID, description, severity, and linked CAP/TRK IDs
  - `entry_source`: `sp-specify` | `sp-clarify` (which command routed here)
  - `research_mode`: `full-research` | `supplement-research`
- Do not edit production code, production tests, migrations, release config, or implementation artifacts from `sp-deep-research`.
- When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.

## Multi-Agent Research Orchestration

- [AGENT] Treat the current session as the research coordinator. The coordinator owns scope control, join points, conflict resolution, and the final `deep-research.md` synthesis.
- [AGENT] Before delegating, split the feasibility problem into independent research tracks only when the tracks can run in parallel without sharing write targets. Good tracks include:
  - repository implementation-pattern evidence
  - external API/library/platform feasibility
  - data shape, migration, permission, performance, or integration constraints
  - alternative approach comparison
  - disposable demo/spike validation
- [AGENT] Dispatch subagents when independent tracks can run in parallel and that materially improves evidence quality or speed. When the next coordinator decision is blocked on a single tightly coupled fact, either create one safe packetized evidence lane for that fact or stop for escalation/recovery with the blocker recorded.
- [AGENT] Give each subagent one bounded track, one expected output shape, and one write scope. Research-only subagents should return evidence packets in their final response. Demo/spike subagents may write only under `FEATURE_DIR/research-spikes/<track-slug>/`.
- [AGENT] Do not duplicate work across subagents. If two tracks overlap, assign one owner and ask the other to focus on a distinct risk or alternative.
- [AGENT] Require every subagent to return an evidence packet with:
  - `track`
  - `question`
  - `sources_or_repo_evidence`
  - `finding`
  - `confidence: high | medium | low`
  - `planning_implications`
  - `constraints_for_sp_plan`
  - `rejected_options`
  - `residual_risks`
  - `spike_artifacts` when applicable
- [AGENT] After each subagent returns, apply the evidence packet acceptance protocol:
  - **ACCEPT** when: `paths_read` is non-empty, `finding` is specific and evidence-backed, core question is answered, and no production files were edited.
  - **REJECT** when: `paths_read` is empty or missing, `finding` is empty or only speculative, core question is unanswered, or the subagent edited production source files.
  - Record every acceptance and rejection in `workflow-state.md`.
  - For rejected packets: retry once with clarified instructions. If the retry also fails, mark the track as `blocked`, record `subagent-blocked` with the rejection reason, and escalate.
  - Do not silently ignore or synthesize rejected evidence packets.

  ```markdown
  ## Evidence Packet Acceptance

  | Track | Subagent | Status | Reason if Rejected | Action |
  |-------|----------|--------|--------------------|--------|
  | TRK-001 | agent-1 | ACCEPTED | — | — |
  | TRK-002 | agent-2 | REJECTED | No paths_read | Retry once |
  | TRK-003 | agent-3 | REJECTED | Edited source file | BLOCKED, escalate |
  ```
- [AGENT] Join all subagent results before writing final conclusions. Resolve contradictions by preferring runnable spike evidence, current repository evidence, primary documentation, then secondary sources in that order. Mark conflicts that remain unresolved instead of hiding them.
- [AGENT] The coordinator must convert subagent packets into `Research Agent Findings`, `Synthesis Decisions`, and `Planning Handoff`; do not paste raw subagent output as the final artifact.
- [AGENT] After accepting a subagent evidence packet, persist it as
  `FEATURE_DIR/research-evidence/<EVD-###>.json` with the full evidence packet
  fields plus the evidence quality rubric. This enables:
  - independent audit without re-parsing `deep-research.md`
  - direct citation by `/sp.plan` via evidence ID
  - safe context-compaction recovery
- [AGENT] If subagent dispatch is unavailable or unsafe, record the decision as `subagent-blocked` with the concrete reason, preserve the decomposed tracks as blocked work, and stop for escalation or recovery instead of continuing as coordinator-only execution.

## Traceability and Evidence Quality Contract

- Assign stable IDs before running research so later planning can cite specific evidence instead of paraphrasing it:
  - capability IDs: `CAP-001`, `CAP-002`, ...
  - research track IDs: `TRK-001`, `TRK-002`, ...
  - evidence IDs: `EVD-001`, `EVD-002`, ...
  - spike IDs: `SPK-001`, `SPK-002`, ...
  - Planning Handoff item IDs: `PH-001`, `PH-002`, ...
- Use the IDs consistently across `Capability Feasibility Matrix`, `Research Agent Findings`, `Implementation Chain Evidence`, `Demo / Spike Evidence`, `Synthesis Decisions`, and `Planning Handoff`.
- Every handoff item must trace back to at least one evidence ID, spike ID, repository path, or source reference.
- Grade each evidence item using this rubric:
  - **Source tier**: `repo-evidence | runnable-spike | primary-docs | official-example | standard | secondary-source | inference`
  - **Reproduced locally**: `yes | no | not applicable`
  - **Recency**: [date, version, or `not time-sensitive`]
  - **Confidence**: `high | medium | low`
  - **Plan impact**: `blocking | constraining | informative`
  - **Limitations**: [what the evidence does not prove]
- Stop each research track when it reaches one of these exit states:
  - `enough-to-plan`
  - `constrained-but-plannable`
  - `blocked`
  - `not-viable`
  - `user-decision-required`
  - `stale-needs-revalidation` — prior evidence may no longer be valid due to dependency or platform changes
- Do not continue researching a track once it has enough evidence to support a planning decision. Convert the result into a handoff item and move on.
- For every spike, record the reproducibility contract:
  - hypothesis
  - setup/env
  - command
  - expected result
  - actual result
  - cleanup note
  - what this does not prove

## Outline

1. **Setup**: Run `{SCRIPT}` from repo root once (`--json --paths-only` / `-Json -PathsOnly`). Parse:
   - `FEATURE_DIR`
   - `FEATURE_SPEC`
   - optional downstream paths if returned
   - If JSON parsing fails, abort and instruct the user to verify the feature branch environment.
   - Set `ALIGNMENT_FILE` to `FEATURE_DIR/alignment.md`.
   - Set `CONTEXT_FILE` to `FEATURE_DIR/context.md`.
   - Set `REFERENCES_FILE` to `FEATURE_DIR/references.md`.
   - Set `DEEP_RESEARCH_FILE` to `FEATURE_DIR/deep-research.md`.
   - Set `SPIKES_DIR` to `FEATURE_DIR/research-spikes`.
   - Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.

2. **Create or resume the workflow state**:
   - Read `templates/workflow-state-template.md`.
   - If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
   - Determine entry source:
     - If the prior `active_command` in `workflow-state.md` was `sp-specify` →
       `entry_source: sp-specify`, `research_mode: full-research`
     - If the prior `active_command` was `sp-clarify` →
       `entry_source: sp-clarify`, `research_mode: supplement-research`
     - If undetermined → default to `full-research`
   - In `supplement-research` mode, preserve existing evidence and only research
     newly added or changed capabilities.
   - Record entry source and research mode in `deep-research.md` Research
     Orchestration section.
   - Persist at least:
     - `active_command: sp-deep-research`
     - `phase_mode: research-only`
     - `allowed_artifact_writes: deep-research.md, research-spikes/, alignment.md, context.md, references.md, workflow-state.md`
     - `forbidden_actions: edit production source code, edit tests, fix build/tooling, implement behavior, commit prototype code as production`
     - `authoritative_files: spec.md, alignment.md, context.md, references.md, deep-research.md`

3. **Load current spec package and repository context**:
   - `FEATURE_SPEC`
   - `FEATURE_DIR/alignment.md`
   - `FEATURE_DIR/context.md`
   - `FEATURE_DIR/references.md` if present
   - `FEATURE_DIR/deep-research.md` if present
   - `.specify/memory/constitution.md` if present
   - `.specify/memory/project-rules.md` if present
   - `.specify/memory/project-learnings.md` if present
   - `PROJECT-HANDBOOK.md` if present
   - the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md`
   - From `FEATURE_DIR/alignment.md`, extract:
     - `Feasibility / Deep Research Gate` status per capability
     - `Planning Gate Recommendation`
     - Capabilities marked `Needed before plan` → these are the research targets
     - Capabilities marked `Not needed` or `Completed` → skip, do not research
     - Capabilities marked `Blocked` → preserve blocker, record reason, do not research unless unblocked
   - targeted live files only when the handbook/project-map cannot prove the current implementation pattern
   - external docs, API references, release notes, examples, or research material when they materially affect feasibility

3b. **Detect staleness and prior evidence**:
    - If `FEATURE_DIR/deep-research.md` already exists from a prior run, compare
      new findings against prior conclusions.
    - For each CAP with prior evidence, check whether dependencies (library
      versions, API endpoints, platform behavior) have changed since the last
      research pass.
    - Mark CAPs with potentially stale evidence as `stale-needs-revalidation`
      and prioritize their research tracks.
    - Record staleness triggers (version bumps, deprecation notices, etc.) in
      the track description.

    ```markdown
    ## Differential Evidence Analysis

    | CAP ID | Previous Conclusion | Previous Evidence | New Evidence | Status Change |
    |--------|--------------------|--------------------|--------------|---------------|
    | CAP-001 | proven | EVD-001 | EVD-005 confirms | Unchanged |
    | CAP-002 | constrained | EVD-002 | SPK-003 disproves | **OVERTURNED** → blocked |
    | CAP-003 | proven (2026-03) | EVD-004 | lib X v3→v4 | **STALE** → revalidate |
    ```

4. **Decide whether this gate is needed**:
   - Skip deep research and recommend `/sp.plan` when all target capabilities already have a known implementation path in the repository or the work is only a minor adjustment to existing behavior.
   - When skipping, still write a lightweight `deep-research.md` using `**Status**: Not needed`, `Feasibility Decision`, `Planning Handoff`, and `Next Command`; do not invent `CAP/TRK/EVD/PH` IDs for work that is already proven.
   - Continue when any capability depends on an unproven API, library, algorithm, platform behavior, data volume, permission boundary, external integration, performance envelope, generated-code workflow, native/plugin bridge, or other path where planning would otherwise guess.
   - If the uncertainty is a requirement gap rather than feasibility risk, recommend `/sp.clarify` and update `workflow-state.md` with that route reason.

5. **Build a capability feasibility matrix from the spec's capability decomposition**:
   - Start from the capability list in `spec.md`. Each spec capability maps to one CAP-###.
   - Do not invent new capability names; use the spec's decomposition as the source of truth.
   - If a spec capability is too broad for focused research, split it into sub-capabilities (CAP-001a, CAP-001b) and note the split in `alignment.md`.
   - For each capability, read its feasibility status from `alignment.md` and take action:

   | Alignment Status | Action |
   |-----------------|--------|
   | `Needed before plan` | Create research track, assign TRK-### |
   | `Not needed` | Mark `proven` or `not needed`, skip |
   | `Completed` | Preserve existing evidence, skip |
   | `Blocked` | Record blocker, do not research |

   For each capability or module slice, record:
   - stable capability ID (`CAP-###`) — mapped from spec capability name
   - capability name (from spec.md)
   - desired outcome (from spec.md)
   - current evidence from the repository
   - unknown implementation-chain link
   - research questions
   - independent research track owner when delegation is useful
   - whether a disposable demo is required
   - proof target: what evidence would be enough to plan safely
   - result status: `proven`, `constrained`, `not viable`, `blocked`, or `not needed`

   Before finalizing the matrix, check each CAP against the preset research dimensions.
   At minimum, confirm or mark "not applicable" for:
   - permissions / auth boundary
   - data volume / performance envelope
   - error / exception / rollback flow
   - concurrency / consistency
   - logging / observability
   - migration / compatibility
   - external dependency SLO / failure mode
   - template / generated-code propagation
   - minimum verifiable test path

6. **Select the research dispatch shape**:
   - [AGENT] Before research fan-out begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="deep-research", snapshot, workload_shape)`.
   - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
   - Decision order is fixed:
     - One safe validated track -> `one-subagent` on `native-subagents` when available.
     - Two or more safe isolated tracks -> `parallel-subagents` on `native-subagents` when available.
     - No safe lane, overlapping write scopes, missing contract, or unavailable delegation -> `subagent-blocked` with a recorded reason.
   - For `deep-research`, safe fan-out means at least two independent research tracks with disjoint write scopes. Research-only tracks return evidence packets; demo tracks write only under their assigned `FEATURE_DIR/research-spikes/<track-slug>/`.
   - Required join points:
     - before final conflict resolution
     - before writing `Synthesis Decisions`
     - before writing `Planning Handoff`
   - Record the chosen strategy, reason, any `subagent-blocked` condition, selected research tracks, write scopes, and join points in `deep-research.md`.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.

7. **Plan and run coordinated research**:
   - Create research tracks from the capability matrix before searching broadly.
   - For each track, assign a stable track ID (`TRK-###`) and define the exact question, evidence target, likely sources, whether a spike is needed, and how the result will affect `/sp.plan`.
   - If two or more tracks are independent and subagent dispatch is available, dispatch bounded subagents according to the Multi-Agent Research Orchestration contract.
   - If subagent dispatch is unavailable or low-confidence, record `subagent-blocked`, capture which tracks could not be dispatched, and stop before substantive research until the block is resolved or explicitly escalated.
   - Search and read only sources that answer a named feasibility question.
   - Prefer primary docs, official examples, standards, changelogs, release notes, library docs, code examples from the dependency itself, and current repository evidence.
   - Cite external sources in `references.md` and summarize how each source affects the implementation chain.
   - Separate facts from inference. If one source is weak or unverified, say so.
   - Preserve rejected alternatives with explicit reasons when they matter to planning.
   - Convert every completed track into an evidence packet with stable evidence IDs (`EVD-###`), evidence quality ratings, limitations, and a track exit state.

8. **Run isolated demo validation when needed**:
   - Assign a stable spike ID (`SPK-###`) and create the smallest runnable spike under `SPIKES_DIR` when docs and repository evidence cannot prove feasibility.
   - Keep the spike intentionally disposable: no production imports unless read-only, no edits outside `FEATURE_DIR/research-spikes/`, no migration or test-suite changes.
   - Define the spike before writing it:
     - hypothesis
     - inputs / fixture data
     - setup/env
     - expected pass condition
     - commands to run
     - actual result capture format
     - cleanup or non-persistence note
     - what this does not prove
   - Run the spike command if the local environment supports it.
   - Capture command, exit status, relevant output summary, and evidence path in `deep-research.md`.
   - If the environment cannot run the spike, record exactly what is missing and whether planning can still proceed with a manual-risk note.

9. **Synthesize research into planning decisions**:
   - Compare evidence packets across tracks.
   - Resolve conflicts and record why one source or demo result won over another.
   - Record every conflict and its resolution in the `Contradiction Resolution Log`.
   - Unresolved conflicts must be marked `BLOCKED` and escalated; do not hide them.
   - Identify the recommended approach, rejected approaches, and constraints `/sp.plan` must preserve.
   - Translate demo observations into planning implications rather than leaving them as raw logs.
   - Identify module boundaries, API/library choices, data flow notes, operational constraints, and validation implications that planning must account for.
   - Assign stable Planning Handoff IDs (`PH-###`) to each decision or constraint that `/sp.plan` must consume.

10. **Write `deep-research.md`**:
   Use `.specify/templates/examples/deep-research/` as the output-shape reference when available:
   - `not-needed.md` for `**Status**: Not needed`
   - `docs-only-evidence.md` when repository evidence and primary documentation are enough
   - `spike-required.md` when a disposable demo proves the implementation chain

   Use the lightweight structure below only when the gate is not needed:

   ```markdown
   # Deep Research: [FEATURE NAME]

   **Feature Branch**: `[###-feature-name]`
   **Created**: [DATE]
   **Status**: Not needed

   ## Feasibility Decision

   - **Recommendation**: Proceed to `/sp.plan`
   - **Reason**: [Why repository evidence already proves the implementation chain]
   - **Planning handoff readiness**: Not needed

   ## Planning Handoff

   - **Handoff IDs**: Not needed
   - **Status**: All capabilities have proven implementation chains in repository
   - **Recommended approach**: [Existing implementation path `/sp.plan` should use]
   - **Constraints `/sp.plan` must preserve**: [Existing boundary, behavior, or constraint]
   - **PH items**: None (all capabilities proven — no research-generated handoff items)

   ## Planning Handoff Readiness Checklist

   - [ ] All capabilities have proven implementation chains in repository
   - [ ] `alignment.md` updated with `Not needed` feasibility status
   - [ ] `context.md` updated
   - [ ] `workflow-state.md` updated with `next_command: /sp.plan`

   ## Next Command

   - `/sp.plan`
   ```

   Use the full structure below when any capability needed research, evidence, or a disposable spike:

   ```markdown
   # Deep Research: [FEATURE NAME]

   **Feature Branch**: `[###-feature-name]`
   **Created**: [DATE]
   **Status**: [Ready for plan | Ready for plan with constraints | Blocked | Not needed]

   ## Feasibility Decision

   - **Recommendation**: [Proceed to `/sp.plan` | Proceed with constraints | Run `/sp.clarify` | Stop / redesign]
   - **Reason**: [Short evidence-based rationale]
   - **Planning handoff readiness**: [Complete | Complete with constraints | Incomplete]

   ## Capability Feasibility Matrix

   | Capability ID | Capability | Unknown Link | Evidence Needed | Proof Method | Result |
   | --- | --- | --- | --- | --- | --- |
   | CAP-001 | [Name] | [What was uncertain] | [Proof target] | [docs / repo evidence / demo] | [proven / constrained / blocked / not needed] |

   ## Research Orchestration

   - **Execution model**: subagent-mandatory
   - **Dispatch shape**: [one-subagent | parallel-subagents | subagent-blocked]
   - **Execution surface**: native-subagents
   - **Reason**: [safe-one-subagent | safe-parallel-subagents | native-subagents-supported | no-safe-delegated-lane | unsafe-write-sets | packet-not-ready | runtime-no-subagents | low-delegation-confidence]
   - **Selected tracks**:
     - [track] -> [research-only evidence packet | demo spike write scope]
   - **Join points**:
     - before final conflict resolution
     - before writing `Synthesis Decisions`
     - before writing `Planning Handoff`

   ## Research Agent Findings

   | Track ID | Agent / Mode | Question | Evidence IDs | Confidence | Exit State | Planning Implication |
   | --- | --- | --- | --- | --- | --- | --- |
   | TRK-001 | [child agent name or subagent-blocked status] | [Question] | EVD-001, SPK-001 | [high / medium / low] | [enough-to-plan / constrained-but-plannable / blocked / not-viable / user-decision-required] | [What `/sp.plan` must use] |

   ## Evidence Quality Rubric

   | Evidence ID | Supports | Source Tier | Source / Path | Reproduced Locally | Recency / Version | Confidence | Plan Impact | Limitations | Persisted |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | EVD-001 | CAP-001 / PH-001 | [repo-evidence / runnable-spike / primary-docs / official-example / standard / secondary-source / inference] | [URL, file path, or spike path] | [yes / no / not applicable] | [date/version/not time-sensitive] | [high / medium / low] | [blocking / constraining / informative] | [what this does not prove] | research-evidence/EVD-001.json |

   ## Implementation Chain Evidence

   ### [Capability Name]

   - **Capability ID**: CAP-001
   - **Chain**: [trigger/input -> module/API/library -> state/output -> validation]
   - **Repository evidence**: [EVD IDs, files, patterns, existing behavior]
   - **External evidence**: [EVD IDs, source links or references.md entries]
   - **Demo evidence**: [SPK IDs, spike path and command result, or not needed]
   - **Planning constraints**: [rules `/sp.plan` must preserve]
   - **Residual risk**: [remaining uncertainty]

   ## Demo / Spike Evidence

   - **Spike ID**: SPK-001
   - **Spike**: [name]
   - **Hypothesis**: [what it proves]
   - **Path**: `research-spikes/[name]`
   - **Setup / env**: [runtime, dependency, fixture, credentials placeholder, or not required]
   - **Command**: `[command]`
   - **Expected result**: [observable pass condition]
   - **Actual result**: [passed / failed / not run, with summary]
   - **Evidence summary**: [short result]
   - **Cleanup note**: [what remains disposable or how to remove it]
   - **What this does not prove**: [limits of the spike]
   - **Planning implication**: [what design or validation decision follows]

   ## Spike Log

   - **Spike**: [name]
   - **Hypothesis**: [what it proves]
   - **Path**: `research-spikes/[name]`
   - **Command**: `[command]`
   - **Result**: [passed / failed / not run]
   - **Evidence summary**: [short result]

   ## Synthesis Decisions

   - **Recommended approach**: [PH-001 -> approach and why]
   - **Rejected options**:
     - [option] -> [evidence-based reason and evidence IDs]
   - **Conflict resolution**:
     - [conflict] -> [resolution and evidence priority]
   - **Plan constraints**:
     - PH-### -> [constraint `/sp.plan` must preserve]

   ## Contradiction Resolution Log

   When two or more evidence items produce conflicting findings, record the
   resolution. Unresolved contradictions must be marked `BLOCKED` and escalated.

   | Conflict | Evidence A | Evidence B | Resolution | Priority Basis | Suppressed Reason |
   |----------|-----------|-----------|------------|----------------|-------------------|
   | [e.g. API version] | EVD-002: v3 | EVD-005: v2 | v3 accepted | spike > docs | EVD-005 was outdated |
   | [unresolved] | EVD-007: pattern A | SPK-003: pattern B | **BLOCKED** | — | Contradictory runnable evidence |

   ## Planning Handoff

   - **Handoff IDs**: PH-001, PH-002, ...
   - **Recommended approach**: PH-001 -> [implementation direction `/sp.plan` should start from; trace to CAP/TRK/EVD/SPK IDs]
   - **Architecture implications**: PH-002 -> [components, layering, boundaries, sequencing; trace to CAP/TRK/EVD/SPK IDs]
   - **Module boundaries**: PH-003 -> [owners and interfaces to preserve; trace to CAP/TRK/EVD/SPK IDs]
   - **API / library choices**: PH-004 -> [selected APIs/libraries and why; trace to CAP/TRK/EVD/SPK IDs]
   - **Data flow notes**: PH-005 -> [inputs, state, outputs, side effects; trace to CAP/TRK/EVD/SPK IDs]
   - **Demo artifacts to reference**: PH-006 -> [`research-spikes/...` and command result; trace to SPK IDs]
   - **Constraints `/sp.plan` must preserve**:
     - PH-### -> [constraint; trace to CAP/TRK/EVD/SPK IDs]
   - **Validation implications**: PH-### -> [tests/checks the plan should include later; trace to CAP/TRK/EVD/SPK IDs]
   - **Residual risks requiring design mitigation**:
     - PH-### -> [risk; trace to CAP/TRK/EVD/SPK IDs]
   - **Decisions already proven by research**:
     - PH-### -> [decision; trace to CAP/TRK/EVD/SPK IDs]

   - **PH consumption contract**:
     - `mandatory` — `/sp.plan` must consume this PH; omitting it is a plan error.
     - `optional` — `/sp.plan` may defer if the plan does not need it.
     - `user-decision` — `/sp.plan` must ask the user before consuming or deferring.

     Each PH item in the Traceability Index must carry its consumption contract in
     the `Mandatory?` column.

   ## Capability Cards

   For each high-value or planning-critical capability, emit a capability card:

   ### CAP-001: [Capability Name]

   | Field | Detail |
   |-------|--------|
   | **Purpose** | [What this capability achieves] |
   | **Owner** | [Owning module / service / surface] |
   | **Truth lives** | [Code path, data table, config, or external service] |
   | **Entry points** | [CLI command, API route, event handler, hook] |
   | **Downstream consumers** | [What depends on this capability] |
   | **Extend here** | [Safe extension points] |
   | **Do not extend here** | [Fragile or contract-locked areas] |
   | **Key contracts** | [Input shape, output shape, side effects, invariants] |
   | **Change propagation** | [What breaks when this changes] |
   | **Minimum verification** | [Command or check that proves this works] |
   | **Failure modes** | [Known ways this can fail] |
   | **Confidence** | [Verified / Inferred / Unknown-Stale] |

   ## Research Exclusions

   Areas, surfaces, or dimensions intentionally not researched in this pass.

   | Excluded Area | Reason | Revisit Condition | Recorded By |
   |---------------|--------|-------------------|-------------|
   | [e.g. performance profiling] | [Not in feature scope] | [Before production deploy] | [Coordinator / TRK-###] |

   Every unverified dimension from the preset research checklist that was marked
   "not applicable" or "deferred" must appear here with a revisit condition.

   ## Planning Traceability Index

   | PH ID | CAP ID | TRK ID | Evidence IDs | Evidence Quality | Plan Consumer | Required Plan Action | Mandatory? |
   |-------|--------|--------|-------------|-------------------|---------------|----------------------|------------|
   | PH-001 | CAP-001 | TRK-001 | EVD-001, SPK-001 | HIGH / blocking | architecture | Use pattern X | mandatory |
   | PH-002 | CAP-001 | TRK-002 | EVD-003 | MEDIUM / constraining | data-model | Consider limit Y | optional |

   ## Sources

   - [Source title](URL) -> [why it matters]

   ## Planning Handoff Readiness Checklist

   - [ ] All CAPs have explicit exit status (`proven` / `constrained` / `blocked` / `not-viable`)
   - [ ] All PH items trace to evidence (EVD/SPK/repo path)
   - [ ] All spike results recorded with pass/fail outcome
   - [ ] All residual risks explicitly linked to evidence IDs
   - [ ] All research exclusions have revisit conditions
   - [ ] `alignment.md` updated with feasibility result and Planning Gate Recommendation
   - [ ] `context.md` updated with implementation-chain evidence, constraints, rejected options
   - [ ] `references.md` updated with external sources
   - [ ] `workflow-state.md` updated with exit criteria and `next_command`
   - [ ] Reverse Coverage Validation passed (all CAP→PH→Evidence chains closed)
   - [ ] Readiness Refusal Rules all PASS

   ## Next Command

   - [`/sp.plan` | `/sp.clarify` | stop with blocker]
   ```

11. **Update upstream artifacts when research changes planning readiness**:
   - Update `alignment.md`:
     - add feasibility result, capability status, implementation-chain confidence, Planning Handoff readiness, and Planning Gate Recommendation
     - recommend `/sp.deep-research` only when more feasibility work remains
     - recommend `/sp.plan` only when every planning-critical capability is proven, constrained enough, not needed, or explicitly force-accepted
   - Update `context.md`:
     - add implementation-chain evidence, Planning Handoff summary, spike paths, external constraints, rejected options, and residual risks that `/sp.plan` must preserve
   - Update `references.md`:
     - add external sources and reusable insights

12. **Run an artifact review gate**:
    - Review `deep-research.md`, `alignment.md`, and `context.md` for:
      - unproven capability chains presented as facts
      - demos with no pass condition
      - source claims without source attribution
      - subagent findings copied without coordinator synthesis
      - missing or vague research orchestration strategy when multiple tracks were available
      - missing `Planning Handoff` decisions for capabilities that affect plan structure
      - production-code edits from the research phase
      - feasibility risks not reflected in the Planning Gate Recommendation
    - If issues remain, revise the artifacts before handoff.

12b. **Run reverse coverage validation**:
    - Prove every CAP has at least one PH-ID.
    - Prove every PH-ID traces back to at least one evidence item (`EVD-###`, `SPK-###`, or live repository path).
    - Prove every `proven` CAP has no remaining unresolved unknown links.
    - Prove every `blocked` CAP has a concrete block reason and next action.
    - Prove every accepted evidence packet was consumed by at least one PH or explicitly deferred.
    - If any check fails, refuse handoff and write gaps back to `workflow-state.md`.

    ```markdown
    ## Reverse Coverage Validation

    | CAP ID | Has PH? | PH IDs | Has Evidence? | Evidence IDs | Proven / Clean? |
    |--------|---------|--------|---------------|-------------|-----------------|
    | CAP-001 | PASS | PH-001, PH-002 | PASS | EVD-001, SPK-001 | PASS |
    | CAP-002 | FAIL | — | — | — | FAIL: No PH assigned |

    **Decision**: [PASS / FAIL — if FAIL, refuse handoff]
    ```

13. **Write or update `WORKFLOW_STATE_FILE`**:
    - Record:
      - `active_command: sp-deep-research`
      - `phase_mode: research-only`
      - current authoritative files
      - exit criteria for feasibility completion
      - next action required before handoff
      - `next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`

14. **Report completion**:
    - branch or feature directory
    - deep-research artifact path
    - spike paths and command results, if any
    - research tracks and subagent evidence packet summary, if any
    - proven capabilities
    - constrained or blocked capabilities
    - Planning Handoff summary for `/sp.plan`
    - updated alignment/context/reference paths
    - recommended next command
    - whether the feature is ready for `/sp.plan`
    - [AGENT] before final completion text, capture any new `workflow_gap`, `project_constraint`, or `decision_debt` learning through `{{specify-subcmd:learning capture --command deep-research ...}}`
    - Use the user's current language for explanatory text while preserving literal command names, file paths, and fixed status values exactly as written.

## Readiness Refusal Rules

Before writing final `deep-research.md` and recommending `/sp.plan`, run every
check below. If **any** check fails, refuse handoff, produce a gap report, and
set `next_command` to `/sp.clarify` or mark the phase as blocked.

- [ ] Every CAP has at least one PH-ID assigned
- [ ] Every PH-ID traces to at least one evidence ID (`EVD-###`, `SPK-###`, or live repository path)
- [ ] No CAP remains `blocked` without an explicit user force-accept recorded in `alignment.md`
- [ ] No `proven` CAP still has unresolved unknown links in its implementation chain
- [ ] Every dispatched subagent returned an accepted evidence packet; rejected packets were retried or escalated
- [ ] `dispatch_shape: subagent-blocked` is recorded with a concrete block reason and escalation path
- [ ] Every spike with a defined hypothesis was run and has a captured pass/fail result

When refusal happens, output a gap report inline before the refusal decision:

```markdown
## Readiness Refusal Report

| Check | Status | Affected IDs | Missing / Reason |
|-------|--------|-------------|-------------------|
| All CAPs have PH | FAIL | CAP-003 | No PH assigned |
| All PHs trace to evidence | FAIL | PH-005 | No EVD/SPK/repo path |
| ... | PASS | — | — |

**Decision**: Handoff refused. Next command: `/sp.clarify`
```

## Rules

- Use this command to produce research evidence and a planning handoff, not to design the full architecture.
- Prefer a small, runnable proof over broad speculative prose when the question is "can this work?"
- Do not require this command for existing capability tweaks where the repository already shows the path.
- Do not advance to `/sp.plan` when a required capability is still `blocked` or `not viable` unless the user explicitly accepts a redesign or force-proceed risk.
- Keep all prototype work isolated under `FEATURE_DIR/research-spikes/`.
- Do not edit source code, tests, migrations, or production config from this command.
- Do not hand off to `/sp.plan` with only raw research notes; synthesize findings into `Planning Handoff`, constraints, rejected options, and residual risks.

## Post-Execution Checks

**Check for extension hooks (after deep research)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.after_deep_research` key.
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
