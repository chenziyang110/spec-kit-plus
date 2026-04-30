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
- Use `specify hook preflight --command deep-research --feature-dir "$FEATURE_DIR"` before deeper workflow execution so stale brownfield routing or invalid workflow entry is caught by the shared product guardrail layer.
- After `WORKFLOW_STATE_FILE` is created or resumed, use `specify hook validate-state --command deep-research --feature-dir "$FEATURE_DIR"` so the shared validator confirms `workflow-state.md` matches the `sp-deep-research` contract.
- Before final handoff, use `specify hook validate-artifacts --command deep-research --feature-dir "$FEATURE_DIR"` so the required `deep-research.md` and `workflow-state.md` set is machine-checked.
- Before compaction-risk transitions or after prototype evidence is synthesized, use `specify hook checkpoint --command deep-research --feature-dir "$FEATURE_DIR"` to emit a resume-safe checkpoint payload from `workflow-state.md`.

## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command deep-research --format json` when available so the research pass sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader command-local context.
- Review `.planning/learnings/candidates.md` only when it still contains candidates relevant to feasibility, hidden dependencies, prototype failures, or repeated research gaps.
- [AGENT] When feasibility friction appears, run `specify hook signal-learning --command deep-research ...` with route-change, false-start, hidden-dependency, command-failure, or validation-failure counts.
- [AGENT] Before final completion or blocked reporting, run `specify hook review-learning --command deep-research --terminal-status <resolved|blocked> ...`.
- [AGENT] Prefer `specify learning capture-auto --command deep-research --feature-dir "$FEATURE_DIR" --format json` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `specify hook capture-learning --command deep-research ...` when the durable state does not capture the reusable lesson cleanly.

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
- [AGENT] Dispatch subagents when independent tracks can run in parallel and that materially improves evidence quality or speed. Keep work local when the next coordinator decision is blocked on a single tightly coupled fact.
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
- [AGENT] Join all subagent results before writing final conclusions. Resolve contradictions by preferring runnable spike evidence, current repository evidence, primary documentation, then secondary sources in that order. Mark conflicts that remain unresolved instead of hiding them.
- [AGENT] The coordinator must convert subagent packets into `Research Agent Findings`, `Synthesis Decisions`, and `Planning Handoff`; do not paste raw subagent output as the final artifact.
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
   - targeted live files only when the handbook/project-map cannot prove the current implementation pattern
   - external docs, API references, release notes, examples, or research material when they materially affect feasibility

4. **Decide whether this gate is needed**:
   - Skip deep research and recommend `/sp.plan` when all target capabilities already have a known implementation path in the repository or the work is only a minor adjustment to existing behavior.
   - When skipping, still write a lightweight `deep-research.md` using `**Status**: Not needed`, `Feasibility Decision`, `Planning Handoff`, and `Next Command`; do not invent `CAP/TRK/EVD/PH` IDs for work that is already proven.
   - Continue when any capability depends on an unproven API, library, algorithm, platform behavior, data volume, permission boundary, external integration, performance envelope, generated-code workflow, native/plugin bridge, or other path where planning would otherwise guess.
   - If the uncertainty is a requirement gap rather than feasibility risk, recommend `/sp.clarify` and update `workflow-state.md` with that route reason.

5. **Build a capability feasibility matrix**:
   For each capability or module slice, record:
   - stable capability ID (`CAP-###`)
   - capability name
   - desired outcome
   - current evidence from the repository
   - unknown implementation-chain link
   - research questions
   - independent research track owner when delegation is useful
   - whether a disposable demo is required
   - proof target: what evidence would be enough to plan safely
   - result status: `proven`, `constrained`, `not viable`, `blocked`, or `not needed`

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
   - **Recommended approach**: [Existing implementation path `/sp.plan` should use]
   - **Reason**: [Why no feasibility evidence or spike is required]
   - **Constraints `/sp.plan` must preserve**: [Existing boundary, behavior, or constraint]

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

   | Evidence ID | Supports | Source Tier | Source / Path | Reproduced Locally | Recency / Version | Confidence | Plan Impact | Limitations |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | EVD-001 | CAP-001 / PH-001 | [repo-evidence / runnable-spike / primary-docs / official-example / standard / secondary-source / inference] | [URL, file path, or spike path] | [yes / no / not applicable] | [date/version/not time-sensitive] | [high / medium / low] | [blocking / constraining / informative] | [what this does not prove] |

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

   ## Planning Traceability Index

   | Handoff ID | Plan Consumer | Supported By | Evidence Quality | Required Plan Action |
   | --- | --- | --- | --- | --- |
   | PH-001 | [architecture / module boundary / data model / validation / risk] | CAP-001, TRK-001, EVD-001, SPK-001 | [highest relevant confidence and plan impact] | [what `/sp.plan` must include] |

   ## Sources

   - [Source title](URL) -> [why it matters]

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
    - [AGENT] before final completion text, capture any new `workflow_gap`, `project_constraint`, or `decision_debt` learning through `specify learning capture --command deep-research ...`
    - Use the user's current language for explanatory text while preserving literal command names, file paths, and fixed status values exactly as written.

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
