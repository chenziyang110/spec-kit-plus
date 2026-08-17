---
description: Use when a planning-ready spec still has feasibility risk and needs coordinated research, evidence packets, or disposable demo spikes before implementation planning.
workflow_contract:
  when_to_use: The current spec package exists, but one or more capabilities do not yet have a credible implementation chain.
  primary_objective: Coordinate focused research and isolated prototype evidence, synthesize implementation-chain decisions, and produce a planning handoff before /sp-plan.
  primary_outputs: 'Runtime-owned Deep Research lifecycle artifacts under `FEATURE_DIR/research/` plus `research-evidence/`, the compatible `FEATURE_DIR/deep-research.md` projection, optional `FEATURE_DIR/research-spikes/`, and updated `alignment.md`, `context.md`, `references.md`, and `workflow-state.md`.'
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
Shared or overlapping write/path scopes among packets force serial `one-subagent`; a parallel conflict is not permission for unrecorded leader research. If no safe validated lane exists, record `subagent-blocked` and stop before substantive research.

## Runtime Lifecycle

Deep Research is runtime-lifecycle-owned. The canonical lifecycle is:

`init -> status -> track-prepare -> track-lease -> (track-submit -> track-accept | track-reject; or track-yield) -> synthesize -> audit-prepare -> audit-accept -> validate -> publish -> verify-handoff`

Invoke those transitions only through the runtime command surface:

```text
specify-runtime deep-research init
specify-runtime deep-research status
specify-runtime deep-research track-prepare
specify-runtime deep-research track-lease
specify-runtime deep-research track-submit
specify-runtime deep-research track-reject
specify-runtime deep-research track-accept
specify-runtime deep-research track-yield
specify-runtime deep-research synthesize
specify-runtime deep-research audit-prepare
specify-runtime deep-research audit-accept
specify-runtime deep-research validate
specify-runtime deep-research publish
specify-runtime deep-research verify-handoff
specify-runtime deep-research not-needed
```

Use `not-needed` instead of the full track lifecycle only when repository
evidence already proves every planning-critical implementation chain.

`deep-research.md` is the compatible derived projection for human review and
legacy readers. Do not treat it as the canonical mutable research ledger when
runtime lifecycle surfaces are present.


## Pre-Execution Checks

**Check for extension hooks (before deep research)**:
- Run `{{specify-subcmd:specify-runtime hook extension-plan --event before_deep_research --format json}}`; never inspect or parse extension storage directly.
- Offer each returned `optional: true` invocation. Execute each returned `optional: false` invocation and wait for its result before proceeding.
- If `actionable_count` is zero, continue silently.

**Maintain workflow quality without hook choreography**:
- Confirm project cognition freshness and valid workflow entry before deeper research begins.
- Keep `workflow-state.md` current as the durable research-session truth for
  allowed artifact writes, next action, and exit criteria; it does not own
  required-stage order or runtime revision.
- Verify the final runtime lifecycle outputs before handoff and refresh the
  compatible `deep-research.md` projection only from runtime-backed results.
- Update durable state before compaction-risk transitions, prototype-evidence synthesis handoffs, or any stop where resume will depend on more than the visible conversation.

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

## Workflow Phase Lock

- [AGENT] Before any artifact or rich-state write, run `{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`. `FEATURE_DIR/workflow.json` is CLI-owned and this auxiliary workflow must not write it. The expected required-stage owner is `specify`. If the runtime is missing, corrupt, at another stage, or already completed, stop with its blocker or a typed owner handoff naming the observed stage, expected owner, affected files, exact next action, unblock criteria, and resume argv; do not overwrite either state surface to force entry.
- [AGENT] Create `WORKFLOW_STATE_FILE` when absent with `{{specify-subcmd:specify-runtime artifact scaffold --kind workflow-state --path <feature-dir>/workflow-state.md --format json}}`; otherwise query it first with targeted `artifact show`. Mutate it only through fresh leases and `artifact patch` before substantial research.
- Treat `WORKFLOW_STATE_FILE` as the resume/evidence source of truth after
  compaction for this research command: allowed writes, forbidden actions,
  authoritative files, next action, and exit criteria. It is not the
  required-stage phase lock.
- Set or update the state for this run only through leased artifact patches, with at least:
  - `active_command: sp-deep-research`
  - `phase_mode: research-only`
  - `allowed_artifact_writes: deep-research.md, research-spikes/, research/state.json, research/track-manifest.json, research/handoffs/, research/rejections/, research/synthesis.json, research/audit-request.json, research/audit.json, research/handoff-to-plan.json, research-evidence/, alignment.md, context.md, references.md, workflow-state.md`
  - `forbidden_actions: edit production source code, edit tests, fix build/tooling, implement behavior, commit prototype code as production`
  - `authoritative_files: spec-contract.json, alignment.md, context.md, references.md, research/state.json, research/track-manifest.json, research/rejections/, research/synthesis.json, research/audit.json, research/handoff-to-plan.json, research-evidence/`
  - `track_exit_states`: per TRK-### exit state
  - `evidence_packet_acceptance`: accepted and rejected packet lists with reasons
  - `failed_readiness_checks`: list of check IDs that failed
  - `open_gaps`: gap ID, description, severity, and linked CAP/TRK IDs
  - `entry_source`: `sp-specify` | `sp-clarify` (which command routed here)
  - `research_mode`: `full-research` | `supplement-research`
- Do not edit production code, production tests, migrations, release config, or implementation artifacts from `sp-deep-research`.
- When resuming after compaction, query `WORKFLOW_STATE_FILE` through `artifact show` before proceeding.

## Multi-Agent Research Orchestration

- [AGENT] Treat the current session as the research coordinator. The coordinator owns scope control, join points, runtime track progression, conflict resolution, canonical synthesis, and the compatible `deep-research.md` projection.
- [AGENT] Before delegating, split the feasibility problem into independent research tracks only when the tracks can run in parallel without sharing write targets. Good tracks include:
  - repository implementation-pattern evidence
  - external API/library/platform feasibility
  - data shape, migration, permission, performance, or integration constraints
  - alternative approach comparison
  - disposable demo/spike validation
- [AGENT] Dispatch subagents when independent tracks can run in parallel and that materially improves evidence quality or speed. When the next coordinator decision is blocked on a single tightly coupled fact, either create one safe packetized evidence lane for that fact or stop for escalation/recovery with the blocker recorded.
- [AGENT] Give each subagent one bounded track, one expected output shape, and one CLI-owned artifact scope. Research-only subagents return evidence packets inline. Demo/spike subagents may submit text/code only under `FEATURE_DIR/research-spikes/<track-slug>/` through `specify-runtime artifact`; they never write those paths directly.
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
- [AGENT] After each subagent returns, apply the runtime-owned evidence packet acceptance protocol:
  - **ACCEPT** when: `paths_read` is non-empty, `finding` is specific and evidence-backed, core question is answered, and no production files were edited.
  - **REJECT** when: `paths_read` is empty or missing, `finding` is empty or only speculative, core question is unanswered, or the subagent edited production source files.
  - Accept a valid submitted packet only through `deep-research track-accept`.
    Reject an invalid packet only through `deep-research track-reject`; the
    runtime snapshots the submitted result and reason under
    `research/rejections/` before requeueing it.
  - For rejected packets: use the runtime-provided single retry with clarified instructions. A second `track-reject` exhausts the retry, marks the generation blocked, and preserves the rejection history for audit; do not force-accept or overwrite the failed result.
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
- [AGENT] The coordinator must convert subagent packets into canonical runtime synthesis, audit, and handoff artifacts plus the compatible `Research Agent Findings`, `Synthesis Decisions`, and `Planning Handoff` projection; do not paste raw subagent output as the final artifact.
- [AGENT] After accepting a subagent evidence packet, build the complete packet
  fields and evidence-quality rubric in memory, then pass them only in the
  matching `specify-runtime deep-research track-submit` result. The runtime
  validates identity and source provenance and materializes
  `FEATURE_DIR/research-evidence/<EVD-###>.json`. This enables:
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
- Use the same IDs in the canonical runtime state, track manifest, synthesis,
  audit, handoff-to-plan, and `research-evidence/` surfaces.
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
   - If `FEATURE_DIR` is not already explicit, use a validated managed Run feature subject or the helper's unique paths-only result; stop on ambiguity instead of inferring the feature from a private Git ref or branch name.
   - When `SPECIFY_RUN_MANAGED=1`, verify the current directory equals `SPECIFY_RUN_WORKSPACE` before reading or writing research artifacts.
   - `FEATURE_DIR`
   - `FEATURE_SPEC`
   - optional downstream paths if returned
   - If JSON parsing fails, abort and instruct the user to verify the feature branch environment.
   - Set `ALIGNMENT_FILE` to `FEATURE_DIR/alignment.md`.
   - Set `CONTEXT_FILE` to `FEATURE_DIR/context.md`.
   - Set `REFERENCES_FILE` to `FEATURE_DIR/references.md`.
   - Set `DEEP_RESEARCH_FILE` to `FEATURE_DIR/deep-research.md`.
   - Set `SPIKES_DIR` to `FEATURE_DIR/research-spikes`.
   - Set `RESEARCH_STATE_FILE` to `FEATURE_DIR/research/state.json`.
   - Set `TRACK_MANIFEST_FILE` to `FEATURE_DIR/research/track-manifest.json`.
   - Set `RESEARCH_HANDOFFS_DIR` to `FEATURE_DIR/research/handoffs`.
   - Set `RESEARCH_REJECTIONS_DIR` to `FEATURE_DIR/research/rejections`.
   - Set `RESEARCH_SYNTHESIS_FILE` to `FEATURE_DIR/research/synthesis.json`.
   - Set `RESEARCH_AUDIT_REQUEST_FILE` to `FEATURE_DIR/research/audit-request.json`.
   - Set `RESEARCH_AUDIT_FILE` to `FEATURE_DIR/research/audit.json`.
   - Set `HANDOFF_TO_PLAN_FILE` to `FEATURE_DIR/research/handoff-to-plan.json`.
   - Set `RESEARCH_EVIDENCE_DIR` to `FEATURE_DIR/research-evidence`.
   - Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.
   - If `alignment.md` or `references.md` is absent, create it only with `artifact scaffold --kind alignment` or `--kind references`; recover a missing bootstrap `context.md` only with `--kind specify-context`. Query existing views and patch named sections rather than submitting a full stable template.

2. **Create or resume the workflow state and runtime lifecycle**:
   - Create it when absent with `specify-runtime artifact scaffold --kind workflow-state --path <feature-dir>/workflow-state.md`; otherwise query it through targeted `artifact show` and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
   - Initialize or resume the canonical Deep Research lifecycle only through `specify-runtime deep-research init`, `deep-research status`, `deep-research track-prepare`, `deep-research track-lease`, `deep-research track-submit`, `deep-research track-reject`, `deep-research track-accept`, `deep-research track-yield`, `deep-research synthesize`, `deep-research audit-prepare`, `deep-research audit-accept`, `deep-research validate`, `deep-research publish`, and `deep-research verify-handoff`.
   - Determine entry source:
     - If the prior `active_command` in `workflow-state.md` was `sp-specify` →
       `entry_source: sp-specify`, `research_mode: full-research`
     - If the prior `active_command` was `sp-clarify` →
       `entry_source: sp-clarify`, `research_mode: supplement-research`
     - If undetermined → default to `full-research`
   - In `supplement-research` mode, preserve existing evidence and only research
     newly added or changed capabilities.
   - Record entry source and research mode in the runtime-owned research state,
     The runtime refreshes the compatible `deep-research.md` projection from
     canonical state; never patch that projection manually.
   - Persist the following only through fresh `artifact prepare` plus targeted `artifact patch` calls:
     - `active_command: sp-deep-research`
     - `phase_mode: research-only`
     - `allowed_artifact_writes: deep-research.md, research-spikes/, research/state.json, research/track-manifest.json, research/handoffs/, research/rejections/, research/synthesis.json, research/audit-request.json, research/audit.json, research/handoff-to-plan.json, research-evidence/, alignment.md, context.md, references.md, workflow-state.md`
     - `forbidden_actions: edit production source code, edit tests, fix build/tooling, implement behavior, commit prototype code as production`
     - `authoritative_files: spec-contract.json, alignment.md, context.md, references.md, research/state.json, research/track-manifest.json, research/rejections/, research/synthesis.json, research/audit.json, research/handoff-to-plan.json, research-evidence/`

3. **Load current spec package and repository context**:
   - Query `FEATURE_SPEC`, `FEATURE_DIR/alignment.md`, `FEATURE_DIR/context.md`, `FEATURE_DIR/references.md`, runtime-owned Deep Research lifecycle artifacts, the compatible `FEATURE_DIR/deep-research.md` projection, and `.specify/memory/constitution.md` through `specify-runtime artifact show`, starting with summary and targeted sections.
   - project rules, compact `learning start --command deep-research` results, and only selected `learning show` records returned by `specify-runtime learning`; never probe Learning storage paths
   - **Project cognition gate:** query the active project's runtime before broad
     repository reads.

     Run or emulate:

     ```text
     {{specify-subcmd:specify-runtime cognition compass --intent research --query="$ARGUMENTS" --format json}}
     ```

     After the default compass packet, run the advanced `lexicon -> semantic_intake -> query` path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, use `specify-runtime cognition lexicon --mode catalog` as the alias catalog, write agent-authored `semantic_intake` and `concept_decisions`, then run `specify-runtime cognition query --query-plan "<query_plan_json>"`; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `repository_search_terms`, project-language search terms, and facet coverage; do not search only the raw user words before source search. Agent-owned semantic normalization remains mandatory: `agent_normalization` and raw lexicon ranking are bootstrap signals only; if `agent_normalization` is omitted, treat it as `required=false`; use `write_semantic_intake_from_alias_catalog` when needed. Raw lexicon ranking is only a bootstrap; CJK or mixed CJK/ASCII input still requires agent-owned normalization even when positive raw lexical matches exist. The agent still owns translation. Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`.

     Use the returned readiness:

     - `query_ready`: read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons.
     - `review`: perform only the returned `minimal_live_reads` before continuing and inspect `coverage_diagnostics`.
     - `needs_rebuild`: route by `recommended_next_action.action_id`, not readiness alone. Preserve resumable actions such as `complete_scan_packets`; only `action_id=project_cognition.rebuild` may consume `rebuild_reasons[]` and `recommended_next_action.workflow_routes.classic.steps` as a rebuild handoff.
     - `blocked`: report the blocking runtime issue and continue with live evidence only where this workflow allows degraded navigation.
     - **CARRY FORWARD**: Treat specify-runtime cognition results as repository-grounded
       starting context. Preserve cited capabilities, constraints, affected
       surfaces, and verification routes in runtime track results and synthesis
       inputs, and distinguish repository facts from external research findings.
   - From `FEATURE_DIR/alignment.md`, extract:
     - `Feasibility / Deep Research Gate` status per capability
     - `Planning Gate Recommendation`
     - Capabilities marked `Needed before plan` → these are the research targets
     - Capabilities marked `Not needed` or `Completed` → skip, do not research
     - Capabilities marked `Blocked` → preserve blocker, record reason, do not research unless unblocked
   - targeted live files only when the project cognition runtime cannot prove the current implementation pattern
   - external docs, API references, release notes, examples, or research material when they materially affect feasibility

3b. **Detect staleness and prior evidence**:
    - If a prior runtime workspace exists, run `deep-research status` first.
      A stale source-specification digest blocks reuse; reinitialize with the
      returned current revision before creating replacement tracks. Use the
      canonical state, accepted handoffs, synthesis, and evidence objects for
      comparison; `deep-research.md` is review context only.
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
    - When skipping, use the runtime `not-needed` publish path so the canonical lifecycle records the decision and the compatible `deep-research.md` projection carries the exact `**Status**: Not needed` marker. Do not invent `CAP/TRK/EVD/PH` IDs for work that is already proven.
   - Continue when any capability depends on an unproven API, library, algorithm, platform behavior, data volume, permission boundary, external integration, performance envelope, generated-code workflow, native/plugin bridge, or other path where planning would otherwise guess.
- If the uncertainty is a requirement gap, recommend `/sp.clarify` and patch the route reason in `workflow-state.md` through a leased `specify-runtime artifact patch`.

5. **Build a capability feasibility matrix from the spec's capability decomposition**:
   - Start from the capability list in `spec.md`. Each spec capability maps to one CAP-###.
   - Do not invent new capability names; use the spec's decomposition as the source of truth.
   - If a selected spec capability is too broad for focused research, stop and
     route it back to Specify or Clarify for a new valid `CAP-###` decomposition;
     Deep Research must not invent suffixed capability IDs outside the bound
     `feasibility_gate.capability_refs` set.
- For each capability, query its feasibility section from `alignment.md` with `specify-runtime artifact show --section` and take action:

   | Alignment Status | Action |
   |-----------------|--------|
   | `Needed before plan` | Create research track, assign TRK-### |
   | `Not needed` | Mark `proven` or `not needed`, skip |
   | `Completed` | Preserve existing evidence, skip |
   | `Blocked` | Record blocker, do not research |

5b. **Consequence-Sensitive Research Tracks**:
   - If the Senior Consequence Analysis Gate is triggered or upstream artifacts carry `CA-###` consequence obligations, create research tracks for any unproven affected object, state-behavior matrix entry, dependency impact, recovery behavior, validation route, or coverage gap that planning would otherwise guess.
   - Each consequence-sensitive `TRK-###` must name the linked `CA-###` obligation, the stop-and-reopen condition it can clear or confirm, the evidence needed, and the downstream workflow that must consume the result.
   - Research outputs must not drop `CA-###` consequence obligations; carry them into `Planning Handoff`, `Synthesis Decisions`, `Validation implications`, and residual risks until they are resolved or explicitly deferred.
   - If evidence disproves an upstream consequence assumption, preserve the obligation as blocked, record the stop-and-reopen condition, and route back to `/sp.clarify` instead of handing ambiguous semantics to `/sp.plan`.
   - When a consequence obligation is proven enough for planning, record the evidence ID, affected objects, lifecycle states covered, dependency impact, recovery and validation contract, remaining coverage gaps, and whether the obligation is still open.

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
   - Persist `execution_model`, `dispatch_shape`, `execution_surface`, join
     points, and any blocked reason in the compact workflow resume state. The
     runtime-owned manifest separately records the concrete track, worker,
     attempt, and acceptance identities; do not claim unsupported state fields.
   - Decision order is fixed:
     - One safe validated track -> `one-subagent` on `native-subagents` when available.
      - Two or more safe isolated tracks -> `parallel-subagents` on `native-subagents` when available.
      - No safe lane, overlapping write scopes, missing contract, or unavailable delegation -> `subagent-blocked` with a recorded reason and the lifecycle paused before `track-submit`.
   - For `deep-research`, one safe track uses one subagent; two or more safe,
     independent tracks with disjoint CLI-owned artifact scopes may run in
     parallel. Research-only tracks return evidence packets inline; demo tracks
     submit only under their assigned `FEATURE_DIR/research-spikes/<track-slug>/`
     through `specify-runtime artifact`.
   - Required join points:
     - before final conflict resolution
     - before writing `Synthesis Decisions`
     - before writing `Planning Handoff`
   - Carry strategy, rationale, any `subagent-blocked` condition, artifact scopes,
     and join points in `workflow-state.md`; let the runtime manifest own only
     its validated tracks and lease/attempt state. Refresh `deep-research.md`
     only through runtime synthesis/publication.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.

7. **Plan and run coordinated research**:
   - Create research tracks from the capability matrix before searching broadly.
   - For each track, assign a stable track ID (`TRK-###`) and define the exact question, evidence target, likely sources, whether a spike is needed, and how the result will affect `/sp.plan`.
   - Use runtime lifecycle ownership for each track: `track-prepare` creates the bounded track contract, `track-lease` reserves mutable scope, `track-submit` records the result channel payload, `track-accept` resolves acceptance, `track-reject` snapshots the rejected attempt and performs the bounded retry transition, and `track-yield` preserves resumable joins.
   - Dispatch every substantive track to a bounded subagent according to the
     Multi-Agent Research Orchestration contract; use parallel dispatch only
     for two or more independent tracks with disjoint write scopes.
   - If subagent dispatch is unavailable or low-confidence, record `subagent-blocked`, capture which tracks could not be dispatched, and stop before substantive research until the block is resolved or explicitly escalated.
   - Search and read only sources that answer a named feasibility question.
   - Prefer primary docs, official examples, standards, changelogs, release notes, library docs, code examples from the dependency itself, and current repository evidence.
   - Patch accepted external sources and implementation-chain impact into `references.md` through the artifact CLI.
   - Separate facts from inference. If one source is weak or unverified, say so.
   - Preserve rejected alternatives with explicit reasons when they matter to planning.
   - Convert every completed track into an evidence packet with stable evidence IDs (`EVD-###`), evidence quality ratings, limitations, and a track exit state.

8. **Run isolated demo validation when needed**:
   - Assign a stable spike ID (`SPK-###`) and create the smallest runnable spike under `SPIKES_DIR` when docs and repository evidence cannot prove feasibility. Every text/code spike file is created or changed through `artifact prepare` plus inline `artifact submit`/leased `artifact patch`; import binary evidence through `specify-runtime evidence import`. Never write a spike file directly.
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
   - Capture command, exit status, relevant output summary, and evidence path in the completed `research-spikes/SPK-###/manifest.json`; reference it from the matching `track-submit` payload.
   - If the environment cannot run the spike, record exactly what is missing and whether planning can still proceed with a manual-risk note.

9. **Synthesize research into planning decisions**:
   - Compare evidence packets across tracks.
   - Resolve conflicts and record why one source or demo result won over another.
   - Record every conflict and its resolution in the `Contradiction Resolution Log`.
   - Each contradiction row records Conflict, Evidence A, Evidence B, Resolution, Priority Basis, and Suppressed Reason.
   - Unresolved conflicts must be marked `BLOCKED` and escalated; do not hide them.
   - Identify the recommended approach, rejected approaches, and constraints `/sp.plan` must preserve.
   - Translate demo observations into planning implications rather than leaving them as raw logs.
   - Identify module boundaries, API/library choices, data flow notes, operational constraints, and validation implications that planning must account for.
   - Assign stable Planning Handoff IDs (`PH-###`) to each decision or constraint that `/sp.plan` must consume.
   - For each planning-critical Capability Card, record Purpose, Owner, Truth lives, Entry points, downstream consumers, safe/forbidden extension points, Key contracts, Change propagation, Minimum verification, Failure modes, and Confidence.
   - Put every intentionally skipped dimension in `Research Exclusions` with Excluded Area, Reason, Revisit Condition, and Recorded By.

10. **Publish the canonical handoff and compatible projection**:
   - Pass semantic findings into `deep-research synthesize`; do not create `synthesis.json` or `deep-research.md` directly.
   - Prepare and accept the identity-separated audit, then run `deep-research validate` and `deep-research publish` with the current `--expected-revision` returned by the preceding command.
   - The runtime writes canonical synthesis, audit, evidence, and `research/handoff-to-plan.json`, then derives `deep-research.md`. Query the projection for human review but never scaffold or patch it.
   - Use `.specify/templates/examples/deep-research/` only as semantic-quality guidance for constructing command payloads; never copy an example into a runtime-owned artifact.
11. **Update upstream artifacts when research changes planning readiness**:
- Patch the relevant `alignment.md` section through a leased `artifact patch`:
     - add feasibility result, capability status, implementation-chain confidence, Planning Handoff readiness, and Planning Gate Recommendation
     - recommend `/sp.deep-research` only when more feasibility work remains
     - recommend `/sp.plan` only when every planning-critical capability is
       `plannable`, `constrained_but_plannable`, or covered by the runtime's
       evidence-backed `not_needed` publication
- Patch the relevant `context.md` section through a leased `artifact patch`:
     - add implementation-chain evidence, Planning Handoff summary, spike paths, external constraints, rejected options, and residual risks that `/sp.plan` must preserve
- Patch the relevant `references.md` section through a leased `artifact patch`:
     - add external sources and reusable insights

12. **Run an artifact review gate**:
- Load `deep-research.md`, `alignment.md`, and `context.md` only through targeted `specify-runtime artifact show` calls, then review the returned views for:
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
- If any check fails, refuse handoff, submit the failed checks through `deep-research audit-accept` as a rejected audit when the audit lane is active, update `workflow-state.md` through its registered artifact owner, and do not publish a plan-consumable handoff.

    ```markdown
    ## Reverse Coverage Validation

    | CAP ID | Has PH? | PH IDs | Has Evidence? | Evidence IDs | Proven / Clean? |
    |--------|---------|--------|---------------|-------------|-----------------|
    | CAP-001 | PASS | PH-001, PH-002 | PASS | EVD-001, SPK-001 | PASS |
    | CAP-002 | FAIL | — | — | — | FAIL: No PH assigned |

    **Decision**: [PASS / FAIL — if FAIL, refuse handoff]
    ```

13. **Patch `WORKFLOW_STATE_FILE` through `specify-runtime artifact patch`**:
    - Acquire a fresh lease and record through targeted section/frontmatter patches:
      - `active_command: sp-deep-research`
      - `phase_mode: research-only`
      - current authoritative files
      - exit criteria for feasibility completion
      - next action required before handoff
      - `next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`

14. **Report completion**:
    - [AGENT] first run `{{specify-subcmd:specify-runtime hook validate-artifacts --command deep-research --feature-dir <feature-dir> --format json}}`; refuse the planning handoff until the Go gate accepts the final research sections, cited evidence objects, and workflow state
    - [AGENT] verify the runtime-published handoff before recommending `/sp.plan`; report the accepted handoff ref, source hash, revision, claim, and consumed `PH-###` / `EVD-###` / `SPK-###` ids
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
    - [AGENT] before final completion text, if auto-capture did not preserve a reusable `workflow_gap`, `project_constraint`, or `decision_debt`, use the manual `learning capture` helper surface.
      Required options: `--command`, `--type`, `--summary`, `--evidence`
    - Use the user's current language for explanatory text while preserving literal command names, file paths, and fixed status values exactly as written.

## Readiness Refusal Rules

Before `deep-research validate` and `deep-research publish` allow the workflow
to recommend `/sp.plan`, run every check
below. If **any** check fails, refuse handoff, produce a gap report, and
set `next_command` to `/sp.clarify` or mark the phase as blocked.

- [ ] Every CAP has at least one PH-ID assigned
- [ ] Every PH-ID traces to at least one evidence ID (`EVD-###`, `SPK-###`, or live repository path)
- [ ] No CAP remains `blocked` or `not viable`; requirement redesign routes
      back through Specify or Clarify before a new Deep Research generation
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
- Disposable demos, research spikes, and proof artifacts validate feasibility for the user's intended capability. They are not a replacement product scope and must not be reframed as the delivered product unless the user explicitly confirms that reduced scope.
- Do not require this command for existing capability tweaks where the repository already shows the path.
- Do not advance to `/sp.plan` when a required capability is still `blocked` or
  `not viable`. A user-approved redesign must first update the specification
  and start a new digest-bound Deep Research generation.
- Keep all prototype work isolated under `FEATURE_DIR/research-spikes/`.
- Do not edit source code, tests, migrations, or production config from this command.
- Do not hand off to `/sp.plan` with only raw research notes; synthesize findings into `Planning Handoff`, constraints, rejected options, and residual risks.
## Post-Execution Checks

**Check for extension hooks (after deep research)**:
- Run `{{specify-subcmd:specify-runtime hook extension-plan --event after_deep_research --format json}}`; never inspect or parse extension storage directly.
- Offer each returned `optional: true` invocation. Execute each returned `optional: false` invocation and wait for its result before closing.
- If `actionable_count` is zero, continue silently.
