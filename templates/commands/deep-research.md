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
- [AGENT] Use native subagents or the integration's native delegation surface when available and when it materially improves evidence quality or speed. Keep work local when the next coordinator decision is blocked on a single tightly coupled fact.
- [AGENT] Give each child agent one bounded track, one expected output shape, and one write scope. Research-only agents should return evidence packets in their final response. Demo/spike agents may write only under `FEATURE_DIR/research-spikes/<track-slug>/`.
- [AGENT] Do not duplicate work across child agents. If two tracks overlap, assign one owner and ask the other to focus on a distinct risk or alternative.
- [AGENT] Require every child agent to return an evidence packet with:
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
- [AGENT] Join all child-agent results before writing final conclusions. Resolve contradictions by preferring runnable spike evidence, current repository evidence, primary documentation, then secondary sources in that order. Mark conflicts that remain unresolved instead of hiding them.
- [AGENT] The coordinator must convert child-agent packets into `Research Agent Findings`, `Synthesis Decisions`, and `Planning Handoff`; do not paste raw child-agent output as the final artifact.
- [AGENT] If no native multi-agent facility is available, perform the same track decomposition sequentially and record that orchestration mode as `single-lane research`.

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
   - Continue when any capability depends on an unproven API, library, algorithm, platform behavior, data volume, permission boundary, external integration, performance envelope, generated-code workflow, native/plugin bridge, or other path where planning would otherwise guess.
   - If the uncertainty is a requirement gap rather than feasibility risk, recommend `/sp.clarify` and update `workflow-state.md` with that route reason.

5. **Build a capability feasibility matrix**:
   For each capability or module slice, record:
   - capability name
   - desired outcome
   - current evidence from the repository
   - unknown implementation-chain link
   - research questions
   - independent research track owner when delegation is useful
   - whether a disposable demo is required
   - proof target: what evidence would be enough to plan safely
   - result status: `proven`, `constrained`, `not viable`, `blocked`, or `not needed`

6. **Select the research orchestration strategy**:
   - [AGENT] Before research fan-out begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_execution_strategy(command_name="deep-research", snapshot, workload_shape)`.
   - Strategy names are canonical and must be used exactly: `single-lane`, `native-multi-agent`, `sidecar-runtime`.
   - Decision order is fixed:
     - If the work does not justify safe fan-out -> `single-lane` (`no-safe-batch`)
     - Else if tracks have overlapping write scopes -> `single-lane` (`overlapping-write-sets`)
     - Else if `snapshot.native_multi_agent` -> `native-multi-agent` (`native-supported`)
     - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime` (`native-missing`)
     - Else -> `single-lane` (`fallback`)
   - For `deep-research`, safe fan-out means at least two independent research tracks with disjoint write scopes. Research-only tracks return evidence packets; demo tracks write only under their assigned `FEATURE_DIR/research-spikes/<track-slug>/`.
   - Required join points:
     - before final conflict resolution
     - before writing `Synthesis Decisions`
     - before writing `Planning Handoff`
   - Record the chosen strategy, reason, fallback if any, selected research tracks, write scopes, and join points in `deep-research.md`.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.

7. **Plan and run coordinated research**:
   - Create research tracks from the capability matrix before searching broadly.
   - For each track, define the exact question, evidence target, likely sources, whether a spike is needed, and how the result will affect `/sp.plan`.
   - If two or more tracks are independent and native multi-agent delegation is available, dispatch bounded child agents according to the Multi-Agent Research Orchestration contract.
   - If delegation is unavailable or low-value, run the tracks sequentially and still write evidence packets.
   - Search and read only sources that answer a named feasibility question.
   - Prefer primary docs, official examples, standards, changelogs, release notes, library docs, code examples from the dependency itself, and current repository evidence.
   - Cite external sources in `references.md` and summarize how each source affects the implementation chain.
   - Separate facts from inference. If one source is weak or unverified, say so.
   - Preserve rejected alternatives with explicit reasons when they matter to planning.
   - Convert every completed track into an evidence packet.

8. **Run isolated demo validation when needed**:
   - Create the smallest runnable spike under `SPIKES_DIR` when docs and repository evidence cannot prove feasibility.
   - Keep the spike intentionally disposable: no production imports unless read-only, no edits outside `FEATURE_DIR/research-spikes/`, no migration or test-suite changes.
   - Define the spike before writing it:
     - hypothesis
     - inputs / fixture data
     - expected pass condition
     - commands to run
     - cleanup or non-persistence note
   - Run the spike command if the local environment supports it.
   - Capture command, exit status, relevant output summary, and evidence path in `deep-research.md`.
   - If the environment cannot run the spike, record exactly what is missing and whether planning can still proceed with a manual-risk note.

9. **Synthesize research into planning decisions**:
   - Compare evidence packets across tracks.
   - Resolve conflicts and record why one source or demo result won over another.
   - Identify the recommended approach, rejected approaches, and constraints `/sp.plan` must preserve.
   - Translate demo observations into planning implications rather than leaving them as raw logs.
   - Identify module boundaries, API/library choices, data flow notes, operational constraints, and validation implications that planning must account for.

10. **Write `deep-research.md`**:
   Use this structure:

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

   | Capability | Unknown Link | Evidence Needed | Proof Method | Result |
   | --- | --- | --- | --- | --- |
   | [Name] | [What was uncertain] | [Proof target] | [docs / repo evidence / demo] | [proven / constrained / blocked / not needed] |

   ## Research Orchestration

   - **Strategy**: [single-lane | native-multi-agent | sidecar-runtime]
   - **Reason**: [no-safe-batch | overlapping-write-sets | native-supported | native-missing | fallback]
   - **Selected tracks**:
     - [track] -> [research-only evidence packet | demo spike write scope]
   - **Join points**:
     - before final conflict resolution
     - before writing `Synthesis Decisions`
     - before writing `Planning Handoff`

   ## Research Agent Findings

   | Track | Agent / Mode | Question | Evidence | Confidence | Planning Implication |
   | --- | --- | --- | --- | --- | --- |
   | [Track] | [child agent name or single-lane research] | [Question] | [Sources, repo files, or spike path] | [high / medium / low] | [What `/sp.plan` must use] |

   ## Implementation Chain Evidence

   ### [Capability Name]

   - **Chain**: [trigger/input -> module/API/library -> state/output -> validation]
   - **Repository evidence**: [files, patterns, existing behavior]
   - **External evidence**: [source links or references.md entries]
   - **Demo evidence**: [spike path and command result, or not needed]
   - **Planning constraints**: [rules `/sp.plan` must preserve]
   - **Residual risk**: [remaining uncertainty]

   ## Demo / Spike Evidence

   - **Spike**: [name]
   - **Hypothesis**: [what it proves]
   - **Path**: `research-spikes/[name]`
   - **Command**: `[command]`
   - **Result**: [passed / failed / not run]
   - **Evidence summary**: [short result]
   - **Planning implication**: [what design or validation decision follows]

   ## Spike Log

   - **Spike**: [name]
   - **Hypothesis**: [what it proves]
   - **Path**: `research-spikes/[name]`
   - **Command**: `[command]`
   - **Result**: [passed / failed / not run]
   - **Evidence summary**: [short result]

   ## Synthesis Decisions

   - **Recommended approach**: [approach and why]
   - **Rejected options**:
     - [option] -> [evidence-based reason]
   - **Conflict resolution**:
     - [conflict] -> [resolution and evidence priority]
   - **Plan constraints**:
     - [constraint `/sp.plan` must preserve]

   ## Planning Handoff

   - **Recommended approach**: [implementation direction `/sp.plan` should start from]
   - **Architecture implications**: [components, layering, boundaries, sequencing]
   - **Module boundaries**: [owners and interfaces to preserve]
   - **API / library choices**: [selected APIs/libraries and why]
   - **Data flow notes**: [inputs, state, outputs, side effects]
   - **Demo artifacts to reference**: [`research-spikes/...` and command result]
   - **Constraints `/sp.plan` must preserve**:
     - [constraint]
   - **Validation implications**: [tests/checks the plan should include later]
   - **Residual risks requiring design mitigation**:
     - [risk]
   - **Decisions already proven by research**:
     - [decision]

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
      - child-agent findings copied without coordinator synthesis
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
    - research tracks and child-agent evidence packet summary, if any
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
