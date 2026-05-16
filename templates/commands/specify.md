---
description: Use when a new or changed feature request needs guided requirement discovery and a planning-ready specification package.
workflow_contract:
  when_to_use: A new or changed feature request needs a planning-ready specification package instead of immediate implementation.
  primary_objective: 'Produce a planning-ready specification package grounded in repository reality by first locking the deterministic brainstorming truth layer and then compiling the final specification artifact set.'
  primary_outputs: '`FEATURE_DIR/brainstorming/facts.json`, `FEATURE_DIR/brainstorming/route.json`, `FEATURE_DIR/brainstorming/intent.json`, `FEATURE_DIR/brainstorming/complexity.json`, `FEATURE_DIR/brainstorming/handoff-to-specify.json`, `FEATURE_DIR/specify-draft.md`, `FEATURE_DIR/spec.md`, `FEATURE_DIR/alignment.md`, `FEATURE_DIR/context.md`, `FEATURE_DIR/references.md`, and `FEATURE_DIR/workflow-state.md`.'
  default_handoff: '`final-handoff-decision` chooses `/sp.plan`, `/sp.clarify`, or `/sp.deep-research` after facts-lock, route-lock, intent-lock, complexity-lock, and the compiled specification package complete cleanly.'
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

{{spec-kit-include: ../command-partials/common/subagent-execution.md}}


## Pre-Execution Checks

**Check for extension hooks (before specification)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_specify` key.
{{spec-kit-include: ../command-partials/common/extension-hooks-body.md}}

**Maintain workflow quality without hook choreography**:
- Confirm project cognition freshness and valid workflow entry before deeper specification work begins.
- Keep `workflow-state.md` current as the durable source of truth for phase, allowed artifact writes, next action, and exit criteria.
- Verify the final `spec.md`, `alignment.md`, `context.md`, and `workflow-state.md` package before handoff instead of relying on chat narration.
- Update durable state before compaction-risk transitions, major artifact synthesis handoffs, or any stop where resume will depend on more than the visible conversation.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command specify --format json}}` when available so passive learning files exist and the current specification run sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader command-local context.
- Open only learning detail docs linked from relevant index entries, especially repeated workflow gaps, user preferences, or project constraints for the touched area.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- [AGENT] When specification friction exposes route changes, false starts, hidden dependencies, validation gaps, or reusable constraints, make sure `workflow-state.md` captures that durable context.
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command specify --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints.
- [AGENT] When the durable state does not capture the reusable lesson cleanly, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.
- Treat this as a passive shared-memory layer, not as a separate user workflow. Do not redirect the user into a dedicated learning-management command.

{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}

**Project cognition gate:** query the active project's runtime before broad
repository reads.

Run or emulate:

```text
{{specify-subcmd:project-cognition lexicon --intent plan --query="$ARGUMENTS" --format json}}
# Agent: generate <query_plan_json> from raw user intent plus returned map terms.
{{specify-subcmd:project-cognition query --intent plan --query-plan "<query_plan_json>" --format json}}
```

Use the returned readiness:

- `ready`: continue with the returned task-local bundle.
- `review`: perform only the returned `minimal_live_reads` before continuing.
- `ambiguous`: ask the user to select the intended candidate.
- `needs_update`: record a planning advisory, perform the returned `minimal_live_reads`, and continue without requiring `{{invoke:map-update}}` during `sp-specify`.
- `needs_rebuild`: route through `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- `blocked`: stop and report the blocking runtime issue.
- **CARRY FORWARD**: Write project-cognition ownership, affected surfaces,
  reusable assets, verification routes, and known unknowns into `context.md`
  and the brainstorming handoff where they materially shape the downstream
  plan. Do not leave these facts only in the transient query output.

## Workflow Phase Lock

- [AGENT] Create or resume `WORKFLOW_STATE_FILE` immediately after `FEATURE_DIR` is known.
- Read `templates/workflow-state-template.md`.
- Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth on resume after compaction for the current command, allowed artifact writes, forbidden actions, authoritative files, next action, and exit criteria.
- Write `active_command` and `status` under `## Current Command`.
- Write `phase_mode` and `summary` under `## Phase Mode`.
- Write only lifecycle progression fields under `## Fixed Lifecycle State`, preserving the lock state for the brainstorming kernel.
- Set or update the state for this run with at least:
  - `active_command: sp-specify`
  - `status: active`
  - `phase_mode: planning-only`
  - `current_stage: facts-lock`
  - `current_domain: none`

  - `current_domain: request-truth`
  - `next_action`
  - `blocker_reason`
  - `final_handoff_decision: pending`
  - `forbidden_actions: edit source code, edit tests, fix build/tooling, implement behavior, run implementation-oriented fix loops`
- Do not implement code, edit source files, edit tests, or run implementation-oriented fix loops from `sp-specify`.
- When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.
- If native hook policy redirects a prompt-entry phase jump, return to `WORKFLOW_STATE_FILE`; repeated or explicit phase jumps are blocked by shared workflow policy.

## Brainstorming Kernel

- `sp-specify` is the public entry shell and must begin with the internal
  brainstorming kernel.
- The kernel progresses through these deterministic locks in order:
  1. `facts-lock`
  2. `route-lock`
  3. `intent-lock`
  4. `complexity-lock`
- Persist each lock result before progressing.
- If a conclusion is not written to the relevant truth file, it is not a valid
  workflow conclusion.
- Conversation memory is not a valid handoff surface.
- Dynamic is allowed only when it is derived from persisted facts and explicit
  rules.
- Dynamic routing is allowed only when it is derived from persisted facts and
  explicit rules.
- Route selection is valid only when `route.json` records a primary route,
  matched rules, and any rejected-route reasoning.
- Complexity selection is valid only when `complexity.json` records the chosen
  complexity level and the matched trigger rules.
- Ask exactly one unresolved high-impact question per turn unless the current
  scope has already been reduced to local low-risk clarification.
- Do not ask a second high-impact question before the first one is closed.
- Grouped questions are allowed only when the current domain is already narrowed to a local low-risk scope that does not change architecture, boundaries, or acceptance shape.
- Unknown is not an ignored value.
- Unknown is a pending decision object.
- Every unresolved `unknown` must carry `field`, `question`,
  `blocking_level`, `resolver`, `latest_resolve_phase`, and `status`.
- Use `resolve-now`, `resolve-by-evidence`, `defer-with-contract`, or
  `waive-with-risk` explicitly instead of silently carrying ambiguity.
- Reopen the current domain when contradiction, hidden dependency,
  project-boundary conflict, or a completeness-threatening omission is found.
- Reopen upstream truth explicitly when later discovery invalidates a locked
  conclusion; reopen is a first-class workflow action.

## Discussion Handoff Intake

If the user invokes `sp-specify` with an explicit path to `.specify/discussions/<slug>/handoff-to-specify.md`, `.specify/discussions/<slug>/handoffs/<candidate_id>-handoff-to-specify.md`, or pastes a discussion handoff block, read that handoff before parsing the feature request. Selected candidate IDs are stable split-plan IDs such as `CAND-001` or `CAND-002`; do not assume only the first candidate can be handed off.

- Treat the discussion handoff as an authoritative input to the brainstorming kernel, not a bypass around it.
- When the supplied path is Markdown, look for the same-stem JSON companion first. For a candidate handoff, read `handoffs/<candidate_id>-handoff-to-specify.json` with the same selected candidate ID and filename stem, for example `handoffs/CAND-002-handoff-to-specify.json`. For the legacy latest handoff, read `handoff-to-specify.json` and treat both files as latest selected candidate copies.
- If candidate Markdown and candidate JSON disagree on `discussion_slug`, `candidate_id`, `candidate_title`, `status`, `source_split_plan`, or any Must-Preserve Ledger item `id`, `type`, `claim`, `blocking_level`, `owner`, `latest_resolve_phase`, or `status`, treat it as a Markdown/JSON mismatch, block with a handoff integrity error, set `coverage_status: blocked_by_handoff_integrity`, and tell the user to refresh the `sp-discussion` handoff.
- If legacy latest Markdown and legacy latest JSON disagree on the selected `candidate_id`, block rather than choosing one representation.
- If candidate Markdown exists but candidate JSON is missing, reconstruct the active feature copy into `brainstorming/handoff-to-specify.json`, record the reconstruction source, and report a handoff repair advisory.
- If JSON exists but Markdown is missing, reject the handoff because the user-reviewable source is absent.
- Record `entry_source: sp-discussion` and the handoff path or pasted discussion handoff marker in the generated feature artifacts.
- Copy the Must-Preserve Ledger into `FEATURE_DIR/brainstorming/handoff-to-specify.json`.
- When `candidate_id` is present, record `discussion_slug`, `candidate_id`, `candidate_title`, `source_split_plan`, `source_handoff`, `source_handoff_json`, `prior_candidates`, `deferred_candidates`, `stage_scope_boundary`, and `reopen_condition` in `brainstorming/handoff-to-specify.json`; cite the handoff path or pasted marker in `context.md`, `references.md`, or `workflow-state.md` according to artifact responsibility.
- The current feature spec covers one candidate. Sibling candidates named in `split-plan.md` are out of scope unless the user returns to `sp-discussion` and selects a new candidate handoff.
- If the user asks inside `sp-specify` to include a sibling candidate, run the decomposition gate. Continue only for internal capability decomposition within the selected candidate. If the request crosses the candidate boundary, stop and tell the user to return to `sp-discussion` to update or select the candidate.
- Preserve confirmed requirements, confirmed non-goals, settled decisions, selected technical direction, critical references, trade-off rationale, candidate boundaries, prior dependencies, and deferred sibling candidates in `facts.json`, `intent.json`, `complexity.json`, `handoff-to-specify.json`, `specify-draft.md`, `spec.md`, `alignment.md`, `context.md`, or `references.md` according to the existing `sp-specify` artifact responsibilities.
- Convert open questions from the handoff into explicit unknowns with `field`, `question`, `blocking_level`, `resolver`, `latest_resolve_phase`, `status`, and a user-visible reopen reason when the unknown can reopen upstream discussion truth.
- Cite the discussion handoff, candidate JSON companion when present, `source_split_plan`, and relevant `project-context.md` evidence in `references.md` or `context.md`.
- Do not re-ask settled discussion questions unless repository evidence, constitution rules, or user correction contradicts the handoff.
- If a settled discussion conclusion conflicts with repository evidence, constitution rules, project rules, project cognition evidence, or architecture constraints, block and ask the user to choose keep, revise, drop, or defer with an explicit risk contract. Do not silently reinterpret the ledger item.
- If a settled discussion conclusion is reopened, record the reopen reason before changing the derived spec package.
- Do not directly update `split-plan.md` from `sp-specify`; `sp-discussion` owns discussion backlog state.

## Discussion Fidelity Coverage Gate

When `entry_source` is `sp-discussion`, coverage and planning readiness are separate.

- `coverage_status`: `not_started | incomplete | complete | blocked_by_handoff_integrity`
- `planning_gate_status`: `ready | blocked_by_hard_unknowns | blocked_by_conflict | blocked_by_incomplete_coverage | blocked_by_handoff_integrity`

Before recommending `/sp.plan`, write `hard_unknown_count` and `open_conflict_count` to `brainstorming/handoff-to-specify.json`.

Coverage can be complete only when every active `MP-*` item is mapped to at least one artifact, and every resolved, superseded, dropped, or deferred item carries the required evidence fields.

Planning can be ready only when coverage is complete, no hard unknowns remain open, and no conflicts remain open.

## Outline

The text the user typed when invoking this workflow is the starting point, not the finished requirement package. Your responsibility is to run the internal brainstorming kernel, persist truth in deterministic locks, and only then compile a planning-ready requirement package. Conversation memory is not a valid handoff surface; only persisted truth files and compiled artifacts count.

1. Parse the user description.
   - If empty: ERROR "No feature description provided".

{{spec-kit-include: ../command-partials/common/pre-analysis-protocol.md}}

Generate the pre-analysis output as the first section of `context.md`.

2. Generate a concise short name (2-4 words) for the branch.
   - Keep it descriptive and action-oriented when possible.

3. Create the feature branch by running the script once with `--json`/`-Json` and `--short-name`/`-ShortName`.
   - Treat the live `specify --help` output as the only authoritative CLI command surface. Before suggesting or running any `specify <subcommand>` helper, verify it exists in `specify --help` or `specify <subcommand> --help`.
   - Treat `sp-specify` plus the generated create-feature script as the supported feature-creation path. Do not infer or recommend a separate branch-creation CLI family.
   - Do not invent unsupported CLI names such as `specify create-feature`, even as a shorthand or guessed compatibility alias.
   - The generated feature-creation helpers live at `.specify/scripts/bash/create-new-feature.sh` and `.specify/scripts/powershell/create-new-feature.ps1`.
   - Run `{SCRIPT}` from the repo root. Use the shell-appropriate `--json`/`-Json` and `--short-name`/`-ShortName` form instead of inventing a separate `specify` subcommand.
   - Before running the script, check if `.specify/init-options.json` exists and read `branch_numbering`.
   - If the value is `"timestamp"`, add `--timestamp` or `-Timestamp`.
   - If the value is `"sequential"` or missing, use default numbering.
   - Do not pass `--number`.
   - If the feature-creation script exits non-zero, stop immediately. Surface the exact stderr/stdout failure to the user, do not guess fallback command names, and do not call `specify lane register` until `BRANCH_NAME`, `FEATURE_DIR`, `LANE_ID`, and `LANE_WORKTREE` were actually returned by the script.
   - Parse `BRANCH_NAME`, `SPEC_FILE`, `FEATURE_DIR`, `LANE_ID`, and `LANE_WORKTREE` from the JSON response.
   - Set `ALIGNMENT_FILE` to `FEATURE_DIR/alignment.md`.
   - Set `CONTEXT_FILE` to `FEATURE_DIR/context.md`.
   - Set `SPECIFY_DRAFT_FILE` to `FEATURE_DIR/specify-draft.md`.
   - Set `REFERENCES_FILE` to `FEATURE_DIR/references.md`.
   - Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.
   - Set `BRAINSTORMING_FACTS_FILE` to `FEATURE_DIR/brainstorming/facts.json`.
   - Set `BRAINSTORMING_ROUTE_FILE` to `FEATURE_DIR/brainstorming/route.json`.
   - Set `BRAINSTORMING_INTENT_FILE` to `FEATURE_DIR/brainstorming/intent.json`.
   - Set `BRAINSTORMING_COMPLEXITY_FILE` to `FEATURE_DIR/brainstorming/complexity.json`.
   - Set `HANDOFF_TO_SPECIFY_FILE` to `FEATURE_DIR/brainstorming/handoff-to-specify.json`.
   - Register or refresh the lane immediately with `{{specify-subcmd:lane register --lane-id "$LANE_ID" --feature-dir "$FEATURE_DIR" --branch "$BRANCH_NAME" --worktree "$LANE_WORKTREE" --command specify}}`.
   - [AGENT] Create or resume `WORKFLOW_STATE_FILE` immediately after `FEATURE_DIR` is known.
   - Read `templates/workflow-state-template.md`.
   - If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
   - Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth for `sp-specify`.
   - Structure the file using the explicit sections from `templates/workflow-state-template.md`:
     - `## Current Command` for `active_command` and `status`
     - `## Phase Mode` for `phase_mode` and `summary`
     - `## Fixed Lifecycle State` for lifecycle progression fields
   - Persist at least these fields for the active pass:
     - `active_command: sp-specify`
     - `status: active`
     - `phase_mode: planning-only`
     - `current_stage: facts-lock`
     - `current_domain: none`

     - `current_domain: request-truth`
     - `next_action`
     - `blocker_reason`
     - `final_handoff_decision: pending`
     - `allowed_artifact_writes: brainstorming/facts.json, brainstorming/route.json, brainstorming/intent.json, brainstorming/complexity.json, brainstorming/handoff-to-specify.json, spec.md, alignment.md, context.md, references.md, specify-draft.md, workflow-state.md, checklists/requirements.md`
     - `forbidden_actions: edit source code, edit tests, fix build/tooling, implement behavior, run implementation-oriented fix loops`
     - `authoritative_files: brainstorming/facts.json, brainstorming/route.json, brainstorming/intent.json, brainstorming/complexity.json, brainstorming/handoff-to-specify.json, spec.md, alignment.md, context.md, references.md, specify-draft.md`
   - When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.
   - If native hook policy redirects a prompt-entry phase jump, return to `WORKFLOW_STATE_FILE`; repeated or explicit phase jumps are blocked by shared workflow policy.

4. Create or resume the brainstorming truth layer.
   - Read or create:
     - `FEATURE_DIR/brainstorming/facts.json`
     - `FEATURE_DIR/brainstorming/route.json`
     - `FEATURE_DIR/brainstorming/intent.json`
     - `FEATURE_DIR/brainstorming/complexity.json`
     - `FEATURE_DIR/brainstorming/handoff-to-specify.json`
   - Treat these files as the authoritative truth layer for lock-state
     progression before the final specification package is compiled.

5. Ensure project cognition runtime exists and record planning advisory state.
   - Check whether `.specify/project-cognition/status.json` exists.
   - If it exists, use the project cognition freshness helper for the active script variant to assess freshness before trusting the current project cognition baseline.
   - [AGENT] If freshness is `missing`, stop and tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that rebuild before continuing.
   - [AGENT] If freshness is `stale`, record a planning advisory, continue with minimal live reads from the query result, and do not require `{{invoke:map-update}}` during artifact-only `sp-specify` work.
   - [AGENT] If freshness is `support_drift`, record a planning advisory about support-surface drift and continue only with evidence-backed reads; do not reflexively route to `{{invoke:map-update}}`.
   - [AGENT] If freshness is `partial_refresh`, record a planning advisory that the refresh was incomplete, preserve `recommended_next_action`, and continue only when query results plus minimal live reads are sufficient for requirement discovery.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. For artifact-only `sp-specify` work, record a planning advisory for any overlapping topics, review those topic files and minimal live reads, and continue without requiring `{{invoke:map-scan}}`/`{{invoke:map-build}}`.
   - Check whether `.specify/project-cognition/status.json` exists at the repository root.
   - [AGENT] If the project cognition runtime is missing, stop and tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that refresh before continuing.
   - Task-relevant coverage is insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
   - Treat task-relevant coverage as a coverage-model check, not just a file-presence check. Coverage is also insufficient when the project cognition runtime cannot yet tell you:
     - owning surfaces and truth locations
     - consumer or adjacent surfaces likely to be affected
     - change-propagation hotspots
     - verification entry points
     - known unknowns or stale evidence boundaries
   - [AGENT] If task-relevant coverage is insufficient for the current request, record a planning advisory, continue with minimal live reads and targeted clarification, and do not require a project cognition refresh during `sp-specify`.
   - Do not treat legacy export artifacts as the primary runtime read path for this workflow.

6. Load context.
   - Read `templates/spec-template.md`.
   - Read `templates/alignment-template.md`.
   - Read `templates/context-template.md`.
   - Read `templates/references-template.md`.
   - Read `templates/workflow-state-template.md`.
   - Read `.specify/memory/constitution.md` if present.
   - Read `.specify/memory/project-rules.md` if present.
   - Read `.specify/memory/learnings/INDEX.md` if present.
   - Open only linked learning detail docs relevant to specification so repeated workflow gaps, user preferences, and project constraints are not rediscovered from scratch.
   - [AGENT] Query project cognition with `{{specify-subcmd:project-cognition lexicon --intent plan --query="$ARGUMENTS" --format json}}`, then generate a query_plan from returned map terms, then run `{{specify-subcmd:project-cognition query --intent plan --query-plan "<query_plan_json>" --format json}}`.
   - If `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` exists and the request is about brownfield testing-system construction, read it and treat it as the primary brownfield testing-program input before clarification. Preserve these stronger brownfield testing inputs: module priority waves, covered-module policy, `small / medium / large` policy, scenario matrix expectations, local integration seam expectations, allowed testability refactors, coverage goals, CI gate expectations, and command-tier expectations for `fast smoke`, `focused`, and `full`.
   - From the project cognition runtime, extract the current module ownership, reusable components/services/hooks, integration points, truth-owning surfaces, adjacent workflows, key entities, architectural constraints, change-propagation hotspots, verification entry points, and known unknowns relevant to the request.
   - If the topical coverage for the touched area is missing, stale, or too broad, or task-relevant coverage is insufficient, record a planning advisory in the feature artifacts, inspect the minimum live files still needed to replace guesswork with evidence, and ask targeted planning-critical questions instead of requiring a project cognition refresh during artifact-only specification work.
   - Read repository context relevant to the request.
   - Read existing specs/docs if relevant.
   - Read user-supplied references, examples, or linked material when they materially affect the requirement package.

## Draft Capture and Resume Discipline

- [AGENT] Create or resume `SPECIFY_DRAFT_FILE` immediately after `FEATURE_DIR` is known.
- Treat `SPECIFY_DRAFT_FILE` as the durable clarification ledger and resume anchor for `sp-specify`.
- Treat `SPECIFY_DRAFT_FILE` as the content ledger for the whole discovery run,
  not as a per-capability scratchpad.
- After every clarification answer, update `SPECIFY_DRAFT_FILE` before asking the next question.
- Record at least: the intent-analysis summary, current stage, current domain, confirmed facts, low-risk inferences, unresolved items, recent question-batch disposition, adversarial-review findings, completeness gaps, and the next question target.
- If a later answer invalidates the current path, reopen the current domain instead of layering contradictory requirements into the ledger.

## Brainstorming Lock Flow

- `sp-specify` no longer assumes the request already starts in feature-spec
  shape.
## Brainstorming Kernel Lock Flow
- Treat `SPECIFY_DRAFT_FILE` as the human-readable companion ledger for the whole discovery run, but treat the JSON files under `FEATURE_DIR/brainstorming/` as the authoritative truth layer.
- `sp-specify` is the public entry shell; internally it must complete the brainstorming kernel before writing or releasing the compiled specification package.
- Only `final-handoff-decision` may decide whether the canonical next command is `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.
- Always execute these six stages in order:
  1. `facts-lock`
  2. `route-lock`
  3. `intent-lock`
  4. `complexity-lock`
  5. `compile-to-specify`
  6. `final-handoff-decision`
- Lock the truth layer first, then compile the familiar specification package.
- The previous fixed heavy discovery lifecycle terms (`intent-analysis`, `intent-confirmation`, `question-batch`, `batch-adversarial-review`, `completeness-audit`) may appear only as compatibility labels inside the draft ledger; the deterministic lock state is authoritative.
- Persist every lock update immediately:
  - `facts-lock` writes `brainstorming/facts.json`.
  - `route-lock` writes `brainstorming/route.json`.
  - `intent-lock` writes `brainstorming/intent.json`.
  - `complexity-lock` writes `brainstorming/complexity.json`.
  - `compile-to-specify` writes `brainstorming/handoff-to-specify.json` before `spec.md`, `alignment.md`, `context.md`, or `references.md` are treated as release candidates.
- Use only these three bounded subagent roles for this command when the runtime supports them:
  - `intent-analyst`
  - `adversarial-reviewer`
  - `completeness-auditor`
- Ask questions only for unresolved fields, rule predicates, contradictions, hard unknowns, or soft unknowns that need an explicit downstream contract.
- Ask exactly one unresolved high-impact question per turn; do not ask a second high-impact question before the first one is closed.
- Grouped questions are allowed only when the current domain is already narrowed to a local low-risk scope.
- If a request spans multiple independently valuable deliverables, decompose it into capabilities before detailed clarification. Present the proposed capability split and help the user decompose it into bounded capabilities inside the same spec first; default to one spec with capability decomposition when the work still belongs to one coherent feature boundary.
- Analyze the whole feature first before asking detailed questions about one capability, so sibling capabilities and validation shape are not missed.
- Deterministic questioning rule: every question must name the lock it advances, the exact unresolved field or rule predicate, and the artifact that will be updated after the answer.
- Do not ask broad exploratory questions after a narrower field-level question can close the lock.
- Do not use freeform brainstorming chat as a substitute for field closure.
- `facts-lock` closes explicit repo/PRD/reference-sensitive predicates.
- `route-lock` closes the primary work-shape route from explicit predicates and is valid only when `route.json` records a primary route, matched rules, rejected routes, and any blocking unknowns.
- `intent-lock` closes goal, non-goals, success criteria, must-preserve invariants, and allowed optimization scope.
- `complexity-lock` closes the fixed complexity ladder and is valid only when `complexity.json` records one chosen level from `T1 Local`, `T2 Structured`, `T3 Cross-Boundary`, or `T4 Reconstruction` plus matched trigger rules.
- Dynamic is allowed only after the persisted facts can justify it. Dynamic routing only means route selection derived from `facts.json`, explicit route rules, and recorded rejected-route reasoning; it is not permission to improvise from chat.
- Unknown is a pending decision object, not a default exit state.
- Unknown is not an ignored value. Each unresolved unknown must record at least `field`, `question`, `blocking_level`, `resolver`, `latest_resolve_phase`, and `status`.
- Resolve every unknown through exactly one disposition:
  - `resolve-now`: ask or inspect now because the lock cannot close without it.
  - `resolve-by-evidence`: read cited repo, doc, or reference evidence and update the owning truth file.
  - `defer-with-contract`: carry a soft unknown with an explicit downstream owner, latest resolve phase, and risk statement.
  - `waive-with-risk`: proceed only with an explicit accepted risk and planning impact.
- Hard unknowns block handoff. Do not hand off past the current gate while a hard unknown remains unresolved.
- Soft unknowns may pass only when `handoff-to-specify.json`, `alignment.md`, and `context.md` name the owner, risk, latest resolve phase, and stop-and-reopen condition.
- Reopen upstream truth instead of silently mutating compiled artifacts when later evidence contradicts a lock.
- The compiled artifacts are projections of the lock truth. Conversation memory is not a valid handoff surface.
- Compile the locked truth layer into `spec.md`, `alignment.md`, `context.md`, and `references.md` only after the required hard unknowns are resolved.
- Only `final-handoff-decision` may decide whether the canonical next command is `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.

## Adversarial Review Contract

- Use `.specify/templates/worker-prompts/specify-observer.md` as the default read-only adversarial-review contract whenever the current integration can dispatch the `adversarial-reviewer` lane.
- The adversarial review output must be written into `SPECIFY_DRAFT_FILE`.
- The leader must not ignore adversarial blockers; each blocker must be resolved, inferred, deferred, or force-carried explicitly before the domain can close.

## Brainstorming Lock State

- Preserve one deterministic lock flow for all `sp-specify` runs and persist lock state through `current_stage`, `current_domain`, `next_action`, `blocker_reason`, and `final_handoff_decision`.

6. Run a codebase scout before clarification.
   - Treat the project cognition runtime as the default scout artifact for understanding the existing system shape.
   - Build a concise internal scout summary for the request area that names:
     - owning modules or workflows
     - truth-owning surfaces and shared coordination surfaces
     - reusable components, services, hooks, commands, or schemas
     - integration boundaries and upstream/downstream dependencies
     - change-propagation hotspots, consumer surfaces, and neighboring surfaces likely to require review
     - adjacent user flows or screens that this work could accidentally break
     - verification entry points and regression-sensitive checks
     - known unknowns, stale evidence boundaries, or observability gaps
     - existing patterns that should bias the questions toward real decision forks
   - If the topical coverage is too broad, stale, or silent on the touched area, read the minimum targeted live files needed to replace guesswork with evidence.
   - Use the scout summary to eliminate low-value questions, sharpen gray areas, and detect when the user's request conflicts with existing repository patterns.

7. Run `facts-lock`.
   Build a top-down understanding grounded in the `project-cognition query` bundle and any returned targeted live-file reads. It must cover:
   - what the user is probably trying to achieve
   - what a complete usable version of the capability likely includes
   - intended users and roles
   - first-release scope boundaries
   - critical constraints and assumptions
   - dependencies or preconditions that materially affect planning
   - the currently owning modules, services, screens, commands, or workflows that this request would extend, replace, or bypass
   - the truth-owning surfaces, consumer surfaces, and change-propagation hotspots that shape how this request spreads through the current system
   - reusable code paths or existing patterns that should shape the questioning instead of forcing the user to rediscover repository facts
   - the verification entry points and regression-sensitive surfaces that will need proof before release
   - the known unknowns, stale evidence boundaries, or weakly mapped surfaces that could force more clarification

8. Run `route-lock`.
   - Read `brainstorming/facts.json`.
   - Select a primary route only from persisted fact evidence and explicit route rules.
   - Record matched rules, rejected routes, blocking unknowns, and route confidence in `brainstorming/route.json`.
   - If route predicates are missing, ask the smallest deterministic question that closes the missing predicate, or resolve it by evidence before continuing.

9. Run `intent-lock`.
   - Read `brainstorming/facts.json` and `brainstorming/route.json`.
   - Lock the goal, non-goals, success criteria, must-preserve invariants, allowed optimization scope, and open questions in `brainstorming/intent.json`.
   - Do not use chat-only conclusions as a substitute for persisted goal, invariant, or scope fields.
   - If a decision would change product goal, compatibility promise, acceptance shape, or non-goal boundary, keep questioning or reopen the owning lock.

10. Run `complexity-lock`.
   - Read `brainstorming/facts.json`, `brainstorming/route.json`, and `brainstorming/intent.json`.
   - Choose exactly one complexity level from `T1 Local`, `T2 Structured`, `T3 Cross-Boundary`, or `T4 Reconstruction`.
   - Record matched trigger rules, scope, execution mode, and any deferred soft unknowns in `brainstorming/complexity.json`.
   - Use `T3 Cross-Boundary` when the change crosses service/process/runtime boundaries, changes shared contracts, or affects multiple owning surfaces.
   - Use `T4 Reconstruction` when the request requires reference reconstruction, behavioral equivalence, cross-language porting, or broad redesign from an existing source of truth.

11. Run lock confirmation.
   - Give the user a short current-understanding summary naming the likely intended outcome and the major affected surfaces.
   - Treat this as a cheap misunderstanding-correction gate, not a full approval ceremony.

12. Choose collaboration strategy for the bounded lock-support roles.
   - [AGENT] Before domain questioning begins, assess the current workload shape and agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="specify", snapshot, workload_shape)`.
   - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
   - Keep delegated `sp-specify` lanes limited to the bounded lock-support roles:
     - `intent-analyst`
     - `adversarial-reviewer`
     - `completeness-auditor`
   - Record the chosen strategy, reason, any blocked dispatch decision, selected lanes, and join points in `alignment.md`.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.

13. Run deterministic questioning and adversarial review inside the active lock.
   - Process the domains in this exact order:
     - `goal-and-users`
     - `triggers-and-primary-flow`
     - `boundaries-and-non-goals`
     - `failure-paths-exceptions-and-permissions`
     - `dependencies-constraints-and-upstream-downstream-impact`
     - `acceptance-and-completeness-gap-closure`
   - Each `question-batch` may ask at most three questions and must stay within one domain.
   - Use repository and handbook evidence to close obvious items, but do not skip domain recording.
   - After every answered batch, run `batch-adversarial-review` before proceeding.

14. Analyze the whole feature before decomposing it.
   Build a top-down understanding grounded in the `project-cognition query` bundle and any returned targeted live-file reads. It must cover:
   - the feature goal
   - intended users and roles
   - first-release scope
   - business and workflow outcomes
   - critical constraints and assumptions
   - dependencies or preconditions that materially affect planning
   - the currently owning modules, services, screens, commands, or workflows that this request would extend, replace, or bypass
   - the truth-owning surfaces, consumer surfaces, and change-propagation hotspots that shape how this request spreads through the current system
   - reusable code paths or existing patterns that should shape the questioning instead of forcing the user to rediscover repository facts
   - the verification entry points and regression-sensitive surfaces that will need proof before release
   - the known unknowns, stale evidence boundaries, or weakly mapped surfaces that could force more clarification
   - release-shaping risks or external references

15. Decomposition gate.
   - If the request spans multiple independent subsystems, business domains, or release tracks, do not continue as though it were one bounded feature.
   - Default to one spec with capability decomposition when the work still belongs to one coherent feature boundary.
   - Stop and help the user decompose it into bounded capabilities inside the same spec first.
   - If the request contains 2 or more distinct deliverables, enhancements, or behavior changes that would independently change implementation or validation shape, present the capability split before asking any detailed clarification question about one capability.
   - Do not jump straight into a detailed gray-area question while multiple sibling capabilities are still unsplit or unprioritized.
   - Only escalate to separate specs or clearly phased releases when one spec would no longer be coherent to plan or test.
   - Present the proposed capability split in user-facing language and ask the user to confirm which capability should be clarified first while keeping the work in the current spec unless the user explicitly wants separate specs or phased release planning.
   - Do not spend one clarification pass collecting requirements for multiple independent capabilities.
   - Only continue once the current spec scope is narrow enough to be planned and tested coherently.
   - If the request is already one bounded capability, say so briefly and continue inside the current spec.

16. Capability decomposition.
    - Decompose the request into capabilities before detailed gray-area questioning.
    - Decompose the analyzed feature into bounded capabilities.
    - For brownfield testing-system work seeded by `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md`, default capability decomposition to foundation work plus module priority waves instead of vague subsystem buckets.
    - Record the purpose of each capability, what scenarios it supports, and how it depends on other capabilities or prerequisites.
    - Separate user-visible capabilities from enabling/supporting capabilities where that improves planning clarity.
    - Note whether each capability is:
      - confirmed by direct evidence,
      - inferred as a low-risk default,
      - or unresolved and still requiring a decision.
    - Run a short checkpoint for each high-risk capability before moving on:
      - purpose / outcome
      - boundary and non-goals
      - acceptance proof
    - If any checkpoint still depends on fuzzy language, reopen clarification for that capability instead of moving on to a sibling capability.
    - If capability boundaries remain unclear, continue clarifying until the decomposition is planning-ready or the user explicitly force proceeds.

17. Run lock completeness audit.
    - Run this only after the active lock domains and their adversarial checks have been processed.
    - Evaluate the whole feature, not only the most recent domain.
    - Explicitly test for missing capability, missing boundaries, missing adjacent effects, and domain-normal omissions that would make the feature unusable.
    - If a critical gap remains, reopen the relevant domain and return to `question-batch` instead of forcing a handoff.

18. Run implementation-oriented completeness checks.

19. Run an implementation-oriented analysis pass before concluding alignment.
    Cover at minimum:
    - scenario and usage path coverage
    - capability sequencing or dependency constraints
    - data, entity, or state implications
    - compatibility and migration expectations
    - external integrations or handoff dependencies
    - impacted surfaces and change-propagation expectations
    - verification entry points and minimum evidence expectations
    - known unknowns or stale evidence boundaries that could change planning safety
    - acceptance-test shaping details
    - planning-sensitive risks and gaps

16b. Run an engineering-completeness gate for boundary-sensitive work.
    - Trigger this gate when the feature crosses a service/process/runtime boundary, depends on async or event delivery, creates user-visible persisted state, or adds configuration that changes delivery behavior.
    - Confirm or explicitly defer, with reason, at minimum:
      - trigger/event source when behavior depends on a cross-component signal
      - trigger or event source
      - payload, identifiers, ordering, or delivery contract
      - state lifecycle, retention, archival, or cleanup expectations
      - retry/dedup/idempotency expectations for async or event-driven behavior
      - retry, deduplication, idempotency, or replay expectations
      - user-visible failure, stale-state, or recovery behavior
      - configuration surface and when changes take effect
      - observability or support evidence needed to diagnose failures
    - If repository evidence can answer one of these, use the scout summary or targeted live-file reads instead of asking the user to restate codebase facts.
    - If the user gives a broad answer such as "we can make the internals detailed later", either turn it into a concrete checklist for confirmation or mark it as an explicit deferred risk.
    - Do not treat this gate as implementation brainstorming; stay at the level of requirement-shaping contracts, lifecycle expectations, and planning safety.

19c. Run a feasibility and implementation-chain gate.
    - For each capability, decide whether the implementation chain is already credible enough for planning.
    - Treat the chain as credible when repository evidence, retained references, or prior working behavior clearly show:
      - trigger/input
      - owning module, API, service, library, or integration surface
      - state/output path
      - validation evidence or acceptance proof
    - If a capability depends on an unproven API, library, algorithm, platform behavior, data volume, permission boundary, external integration, native/plugin bridge, generated-code workflow, performance envelope, or other unknown where planning would otherwise guess, mark it as a feasibility concern that must be resolved before planning.
    - Prefer a disposable proof under `FEATURE_DIR/research-spikes/` when the real question is "can this work?" and evidence is still missing.
    - Treat deep research as the research-to-plan proof path when feasibility evidence is required: its `deep-research.md` must preserve findings, demo evidence, rejected options, constraints, and a `Planning Handoff` that `/sp.plan` can consume.
    - Do not require deep research for minor adjustments to capabilities that already exist in the project and have a clear implementation path.
    - Record feasibility status in `alignment.md` as `Not needed`, `Needed before plan`, `Completed`, or `Blocked`.
    - If the issue is actually requirement ambiguity rather than implementation proof, keep resolving it inside `sp-specify` until `final-handoff-decision` determines the appropriate next command.

19d. Identify gray areas before concluding alignment.
   - Identify 3-5 planning-relevant gray areas: decisions that could reasonably go multiple ways and would materially change implementation, planning, or testing.
   - Derive gray areas from the combination of user intent, the project cognition runtime, and targeted repository evidence instead of from a generic question catalog.
   - Prefer feature-specific decision surfaces over generic categories.
   - Do not use generic labels like "UX", "behavior", or "data handling" when a more concrete decision point can be named from the actual codebase and request.
   - Good gray areas name the concrete fork in outcome, for example `empty-state recovery`, `permission downgrade behavior`, `sync trigger timing`, or `existing dashboard card reuse`.
   - Each gray area should be captured internally with:
     - a concrete decision label
     - why the decision changes implementation or test shape
     - which codebase evidence or owning module made this gray area relevant
     - what additional detail is still missing before a planner could safely proceed
   - For each high-impact gray area, default to resolving at least these decision dimensions unless one is genuinely not applicable:
     - desired happy-path behavior
     - edge case or failure-path behavior
     - compatibility, migration, or neighboring-workflow impact
     - acceptance proof: what evidence would show this decision was implemented correctly
   - Typical gray-area domains include workflow behavior, role/permission handling, data/state transitions, compatibility or migration behavior, failure handling, external integrations, and validation approach.
   - When a high-impact gray area still has multiple viable requirement shapes, switch into decision-fork mode.
   - In decision-fork mode, present 2-3 concrete options that differ in behavior, boundary, compatibility, or acceptance proof.
   - Lead with the recommended option and one short rationale sentence.
   - Use this mode only for a requirement-shaping decision, not as open-ended solution ideation.
   - Do not use this mode for implementation architecture brainstorming, framework/tool selection, or low-risk defaults that do not materially change planning.
   - Use the gray-area list to decide what to ask next rather than falling back to generic catch-all questions.
     - Record resolved gray-area outcomes under `Locked Decisions` when they are fixed enough for planning.
     - Record user-approved flexibility under `Claude Discretion`.
     - Record cited specs, ADRs, examples, or policies under `Canonical References`.
     - Record out-of-scope ideas surfaced during clarification under `Deferred / Future Ideas`.
     - If repository evidence or user intent indicates reference-preserving or rewrite-style work, add `Fidelity Requirements` to `spec.md` and record a behavior-level `Reference Behavior Inventory` rather than only a module or feature label.
     - Synthesize these decisions into `context.md` so downstream planning does not rely on reconstructing them from prose alone.

19e. Run a high-impact ambiguity scan.
    Detect unresolved ambiguity affecting:
    - scope
    - users/roles
    - security/permissions
    - workflow behavior
    - data/entities
    - compatibility
    - acceptance tests
    - success criteria
    - rollout/migration impact
    - capability boundaries
    - dependency sequencing

    The user saying "I already explained it" is not sufficient reason to stop. Judge clarity from the perspective of a future planner, implementer, and tester.
    If planning-critical ambiguity remains around scope, workflow behavior, constraints, or success criteria, continue clarification instead of releasing normal alignment.

19. Clarification loop.
    - **Question output hard gate**: before generating any clarification question, confirmation, or bounded selection, check whether a native structured question tool is available in the current runtime.
    - If a native structured question tool is available, you MUST use it.
    - Do not render the textual fallback block when the native tool is available.
    - Do not self-authorize textual fallback because the question seems simple, short, or easy to express in plain text.
    - Only fall back after the native tool is unavailable or the tool call fails. If a native tool call fails once, retry once before falling back.
    - Keep the interaction feeling like guided requirement discovery rather than a shallow questionnaire.
    - Ask only high-value questions.
    - Before asking a planning-critical question, check whether the project cognition runtime or targeted repository evidence already answer it; do not ask the user for facts the codebase can supply.
    - Use grouped questions for simple/local changes.
    - Use one question at a time for complex/high-risk cases.
    - Ask at most one unanswered high-impact question per message.
    - Let unresolved gray areas drive the next question; do not rotate through generic requirement categories once the active gray area is known.
    - Keep the active gray area open until the decision is specific enough that a downstream planner would not need to reopen it for behavior, boundary, or acceptance-shaping detail.
    - Make the next question build directly on the user's most recent answer rather than resetting to generic prompts.
    - Use the previous answer to choose the next narrowing move, not a recycled generic checklist question.
    - Use code-aware follow-ups when possible: reference the current module, workflow, entity, command, or reusable pattern named in the project cognition runtime or repository evidence so the question is about the real decision fork, not an abstract category.
    - If the user already described the desired UX in natural language, translate it into behavior and confirm the boundary instead of forcing a transport or browser-API choice.
    - When the active gray area crosses a service, process, runtime, or storage boundary, stay on the engineering contract until trigger, identifiers, lifecycle, failure behavior, and configuration semantics are specific enough for planning.
    - If the user's answer is vague, shallow, or contradictory, respond with a targeted narrowing question, example, or recommendation tied to the planning-critical ambiguity.
    - Do not accept long but still ambiguous answers as sufficient.
    - Challenge contradictions or vague answers when important ambiguity remains.
    - Keep stronger follow-up behavior tied to planning-relevant ambiguity, not generic conversation depth.
    - Apply a specificity test before leaving a gray area: if a different planner or implementer would still need to ask clarifying questions to execute safely, keep drilling into that area instead of moving on.
    - Do not leave a gray area merely because the user expressed a preference; stay on it until behavior boundaries, failure handling, compatibility impact, and acceptance-shaping detail are either fixed, intentionally deferred, or explicitly granted as `Claude Discretion`.
    - For high-impact gray areas, treat the default minimum depth as: happy path, failure path, compatibility impact, and acceptance proof. If one of those dimensions is not applicable, say so explicitly instead of skipping it silently.
    - Treat the following as anti-surface warning signs that require another narrowing question instead of release:
      - the user only states a preference word such as "simple", "intuitive", "robust", or "clean" without concrete behavior
      - the user chooses an option but the boundary conditions, failure behavior, or affected neighboring workflow remain unclear
      - the user confirms a direction but there is still no acceptance proof for how success will be judged
      - the requested behavior appears to conflict with the current owning module or existing repository pattern and the difference has not been explained
    - Concrete examples that MUST trigger another narrowing question instead of release:
      - "make it more intuitive"
      - "handle permissions normally"
      - "keep it compatible"
      - "show an error if something goes wrong"
      - "use the existing pattern"
      - "it should feel fast"
      - "just validate the data properly"
      - "admins can handle the special cases"
      - "don't break existing clients"
      - "the internal data structure can be detailed later"
      - "just send the event to the next service"
      - "follow the existing hook pattern"
    - For answers like those, the next question must convert the vague intent into concrete behavior, edge handling, compatibility scope, or acceptance evidence rather than acknowledging and moving on.
    - Treat these as category-specific anti-surface gaps unless they are made concrete:
      - vague success standard: words like "fast", "smooth", "easy", "clear", or "works well" without observable success criteria
      - vague data rule: words like "valid", "clean", "normalized", or "properly formatted" without explicit field rules, transitions, or rejection behavior
      - vague permission boundary: words like "normal permissions", "admin behavior", or "authorized users" without role/action matrix or downgrade/override behavior
      - vague compatibility claim: phrases like "keep compatibility" or "don't break clients" without naming the preserved interface, version boundary, migration expectation, or failure mode
      - vague event contract: phrases like "emit a hook", "send the event", or "forward it to relay" without naming the trigger source, identifiers, payload boundary, or retry behavior
      - vague lifecycle claim: phrases like "keep it until the user sees it" or "store it for later" without read/unread states, retention, or cleanup behavior
    - Use recommendation and example scaffolding when they help the user answer more clearly without forcing a rigid response path.
    - Use the user's current language for all user-visible clarification content, including questions, summaries, status updates, and the current-understanding restatement.
    - Default to concise clarification turns: after the user answers, ask the next question directly unless a recap is necessary.
    - Do not restate the full current understanding after every answer.
    - Use at most a one-line checkpoint when helpful, for example `Confirmed so far:` or `Still open:`.
    - Reserve the full current-understanding recap for moments when it adds clear value: the user asks for a recap, the thread has become long enough that context may drift, a contradiction must be reconciled, or you are about to conclude alignment.
    - When you do restate current understanding, organize it in grouped sections by information layer, not as a flat list.
    - Keep grouped recaps compact; omit sections that would be empty, repetitive, or low-value.
    - Keep progress tracking scoped to the current capability or bounded spec slice rather than to a fixed global question budget.
    - Do not present the clarification loop as a fixed total such as `2 / 5`.
    - When using a native structured question tool, map the same stage header plus topic label into the native header or title field, the prompt into the native question field, the options into the native option list, and the recommendation rationale into the recommended option description or equivalent metadata instead of rendering the textual block verbatim.
    - Treat the shared open question block structure below as fallback-only text format guidance; render the textual block only when the native tool is unavailable or the tool call fails after retry.
    - Each textual fallback open question block must present, in order: a stage header, question header, prompt, example when useful, recommendation, options, and reply instruction.
    - Keep the stage header minimal: `SPECIFY SESSION` plus the current capability-scoped progress marker, for example `Capability 1 / 3 | Question 2`.
    - Use the question header for a short topic label only.
    - Default to a one-sentence prompt. Put extra context into the example line, grouped sub-points, or recommendation line instead of turning the prompt into a paragraph.
    - Include a one-line `Example` row whenever the topic benefits from a concrete case.
    - When you present options, mark exactly one option in the recommendation with a `[ RECOMMENDED ]` badge and follow it with a single short rationale sentence.
    - Keep the open block visually structured through ordering, spacing, and labels rather than right-side borders or closed ASCII framing.
    - Do not rely on interactive selection widgets. Assume the user will answer in plain text.
    - After the options, explicitly invite natural-language replies, for example: `Reply naturally, for example: "A", "选 C", "我选推荐项"`.
    - Accept common natural-language answer forms such as `A`, `选A`, `我选 C`, `推荐的那个`, or a short paraphrase that clearly matches one option.
    - After parsing the answer, acknowledge it with one lightweight confirmation line and continue, for example: `Recorded: C - Normalize first`.
    - Do not repeat the same question in both the summary and the follow-up ask.
    - If the runtime exposes separate progress/commentary and final reply channels, keep the acknowledgment and open question block together in the final reply only.
    - In those runtimes, commentary/progress updates may mention internal progress briefly but must not restate the current clarification question, options, or the same preamble used in the final reply.
    - The user should see the current clarification question exactly once.
    - If you include a grouped recap and are about to ask the next question immediately, summarize it briefly under `Outstanding Questions` instead of restating the full wording there.
    - Save the full synthesis for the alignment-ready turn, the written artifacts (`alignment.md`, `context.md`, `spec.md`, `references.md`), or when the user explicitly asks to see everything collected so far.
    - Do not turn this into a freeform brainstorming workflow.
    - each clarification turn should contain at most one short checkpoint or one grouped recap, plus one question block.

20. Apply `final-handoff-decision`.
    - Before releasing `Aligned: ready for plan`, provide a grouped recap that covers goal, users and roles, scope boundaries, locked decisions, technical constraints or assumptions, and outstanding questions.
    - Explicitly ask the user to confirm or correct the current understanding before the final handoff decision is locked.
    - Treat this as an explicit pre-release check rather than a courtesy recap.
    - If the user corrects the recap, update the active understanding and continue clarification.
    - If planning-critical gaps remain after the recap, do not release `Aligned: ready for plan`.
    - Only this stage may record `/sp.plan`, `/sp.clarify`, or `/sp.deep-research` as the canonical next command.
    - Clarify planning-critical ambiguity before release; if it survives this pass, keep the package unresolved and route to `/sp.clarify`.
    - Use `/sp.plan` when the requirement package is planning-ready.
    - Use `/sp.clarify` when the package is salvageable but planning-critical ambiguity still remains.
    - Use `/sp.deep-research` when the requirements are clear enough but a planning-critical implementation chain still needs external proof or a disposable demo.

    Use this open question block structure in the user's current language when rendering the textual fallback block.
    Use this fallback open question block structure when the native structured question tool is unavailable:

    ```text
    Stage header
    SPECIFY SESSION - Capability 1 / 3 | Question 2

    Question header
    [Short topic label]

    Prompt
    [One-sentence question stem]

    Example
    [One-line concrete example]

    Recommendation
    [ RECOMMENDED ] [Option letter]
    [One short rationale sentence]

    Options
    A. [Option text]
    B. [Option text]
    C. [Option text]
    D. [Option text]

    Reply instruction

    Reply naturally, for example: "A", "选 C", "我选推荐项"
    ```

21. Final Validation & Release.
    This single gate replaces the old multi-step release sequence. Complete all three sub-checks before reporting completion.

    **A. Artifact Self-Review**: Review the written `spec.md`, `alignment.md`, and `context.md` for:
    - placeholders, TODOs, or `[NEEDS CLARIFICATION]` markers
    - contradictions or capability drift between artifacts
    - missing capability checkpoints or weak acceptance proof
    - requirement-vs-implementation language drift
    - If the current artifact review is marked high-risk by the workflow's fixed review trigger, a read-only reviewer lane MUST run before handoff.
    - If no high-risk review trigger is present, a reviewer lane MUST NOT be added.
    - Review routing is condition-triggered, not preference-triggered.
    - If planning-critical issues are found, revise current artifacts, re-run validation (Step 25), and repeat this self-review.

    **B. User Confirmation**: Present a grouped recap covering goal, users and roles, scope boundaries, locked decisions, technical constraints, and outstanding questions.
    - Explicitly ask the user to confirm or correct the current understanding.
    - If the user corrects the recap, update the active understanding and continue clarification.
    - If planning-critical gaps remain after the recap, do not release.

    Use this grouped recap structure in the user's current language:

    ```text
    [Current understanding heading]

    [Business Goals]
    - [Requested outcome]
    - [Why it matters / intended business value]

    [Users & Roles]
    - [Target users / audience]
    - [Relevant roles or permission groups]

    [Scope Boundaries]
    - [First-release scope]
    - [Out-of-scope boundary]

    [Business Rules]
    - [Expected behaviors / capabilities]
    - [Rules, workflows, or policy constraints]

    [Technical Constraints / Assumptions]
    - [Given platform, integration, architecture, or deployment constraints]

    [Confirmed Decisions]
    - [Decisions already fixed enough to plan against]

    [Outstanding Questions]
    - [Open question / confirmation still needed]
    ```

    **C. Release Decision**: Decide exactly one release state.
    - If mandatory clarity gates are resolved, capability decomposition is bounded, no unresolved high-impact ambiguity remains, and no feasibility-proof gate is active, release state MUST be `Aligned: ready for plan` and `next_command` MUST be `/sp.plan`.
    - If planning-critical ambiguity remains, release state MUST remain unresolved and `next_command` MUST be `/sp.clarify`.
    - If requirements are clear enough but implementation feasibility is still unproven, release state MUST remain unresolved and `next_command` MUST be `/sp.deep-research`.
    - `Force proceed with known risks` is valid only when the user explicitly accepts the named unresolved risks.
    - No alternative next command is valid for the current state.

    After the release decision is made, ask the user to review the written artifact set and report the single valid next path for the current state.
    - If `next_command = /sp.plan`, tell the user the package is ready for `{{invoke:plan}}`.
    - If `next_command = /sp.clarify`, tell the user the package must continue through `{{invoke:clarify}}`.
    - If `next_command = /sp.deep-research`, tell the user the package must continue through `{{invoke:deep-research}}`.
    - If the user requests artifact edits, remain in `sp-specify`, update the artifacts, and repeat the artifact review gate. Do not emit a second alternative next command.

26. Run an artifact review gate before handoff.
    - Review the written artifact set before handoff, not just the conversational understanding.
    - Run a self-review across `spec.md`, `alignment.md`, and `context.md` for:
      - placeholders/TODOs
      - contradictions or capability drift
      - missing capability checkpoints
      - requirement-vs-implementation drift
    - If the current artifact review is marked high-risk by the workflow's fixed review trigger, a read-only reviewer lane MUST run before handoff.
    - If no high-risk review trigger is present, a reviewer lane MUST NOT be added.
    - Review routing is condition-triggered, not preference-triggered.
    - If the review finds planning-critical issues, revise current artifacts, re-run validation, and repeat the artifact review gate.
    - Ask the user to review the written artifact set before handoff. If the user requests changes, remain in `sp-specify`, update the artifacts, re-run validation, and repeat the artifact review gate. Do not present multiple downstream command options; report only the single valid `next_command` for the current state.
    - Do not present `{{invoke:plan}}` as ready until the written artifact set passes this gate.

    Do not release `Aligned: ready for plan` when the current understanding still depends on taste words, implicit defaults, or untested assumptions. Do not release for cross-boundary or event-driven features when trigger source, contract identifiers, lifecycle/retention, failure path, or configuration semantics are still fuzzy.
    You must not declare `Aligned: ready for plan` while planning-critical adversarial-review blockers remain untreated.
    You must not declare `Aligned: ready for plan` when the fixed domain sequence or completeness audit still leaves a planning-critical omission unresolved.

20. Write `spec.md` to `SPEC_FILE` using the template structure.
    Requirements:
    - clean result-state document only
    - no `[NEEDS CLARIFICATION]`
    - no speculative implementation details presented as facts
    - include the analyzed whole-feature overview
    - include scenarios and usage paths
    - include capability decomposition
    - include implementation-oriented analysis suitable for planning
    - include trigger / contract / lifecycle / failure / configuration semantics when the feature is boundary-sensitive
    - include alignment state showing confirmed vs inferred vs unresolved
    - include risks and gaps that could affect planning
    - requirements must be testable
    - scope must be bounded
    - emit a planning-ready requirement package rather than a surface summary

21. Write `alignment.md` to `ALIGNMENT_FILE`.
    It must include:
    - fixed heavy discovery lifecycle summary
    - current aligned understanding
    - confirmed facts
    - low-risk inferences
    - unresolved items
    - engineering closure for boundary-sensitive features: trigger source, contract boundary, lifecycle/retention, failure/retry semantics, configuration surface
    - capability checkpoints for high-risk capabilities
    - feasibility / deep research gate status, including capabilities that need proof before planning
    - high-impact decision-fork outcomes
    - clarification summary
    - release decision:
      - `Aligned: ready for plan`
      - or `Force proceed with known risks`
    - downstream planning impact
    - artifact review gate outcome
    - reason for the release decision

22. Write `context.md` to `CONTEXT_FILE`.
    It must include:
    - phase or feature boundary
    - locked decisions
    - contract and lifecycle notes for boundary-sensitive behavior
    - configuration surface and effective timing when settings shape behavior
    - capability checkpoints
    - decision fork outcomes
    - Claude discretion
    - canonical references
    - existing code insights when relevant
    - specific user signals that would change implementation shape
    - outstanding questions when force proceeding
    - deferred or future ideas
      - enough implementation context that downstream planning does not need to reconstruct these decisions from prose scattered across other artifacts
      - fidelity requirements and reference behavior inventory when the feature is reference-sensitive or rewrite-style

23. Write `references.md` to `REFERENCES_FILE` when any meaningful source material was used.
    It must include, for each retained source:
    - source
    - description
    - relevance
    - reusable insights
    - spec impact mapping
    - After the artifact set is current, write or update `WORKFLOW_STATE_FILE` so it records:
      - `active_command: sp-specify`
      - `phase_mode: planning-only`
      - `current_stage`
      - `current_domain`
      - `next_action`
      - `blocker_reason`
      - `final_handoff_decision`
      - current authoritative files
      - exit criteria for planning readiness
      - the next action required before handoff
      - `next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`

24. Generate or update `FEATURE_DIR/checklists/requirements.md` with these validation items:

    ```markdown
    # Specification Quality Checklist: [FEATURE NAME]

    **Purpose**: Validate specification completeness and engineering readiness before planning
    **Created**: [DATE]
    **Feature**: [Link to spec.md]
    **Alignment Report**: [Link to alignment.md]
    **Lifecycle**: fixed heavy discovery

    ## Content Quality

    - [ ] No implementation choice locked as sole path (technical context for grounding is allowed)
    - [ ] No framework/library version pinning in spec
    - [ ] No technology choice used as acceptance criterion
    - [ ] Focused on user value and business needs
    - [ ] Written for non-technical stakeholders
    - [ ] All mandatory sections completed

    ## Requirement Completeness

    - [ ] No [NEEDS CLARIFICATION] markers remain
    - [ ] Requirements are testable and unambiguous
    - [ ] Success criteria are measurable
    - [ ] Scope boundaries are explicit
    - [ ] All acceptance scenarios are defined
    - [ ] Edge cases are identified
    - [ ] Dependencies and assumptions identified
    - [ ] Capability decomposition is planning-ready
    - [ ] Confirmed vs inferred vs unresolved states are recorded per capability (min 80% coverage)
    - [ ] Boundary-sensitive features record trigger source, contract boundary, lifecycle/retention, failure semantics, and configuration surface

    ## Specification Engineering Completeness

    Run `spec-lint -dir <FEATURE_DIR> -tier <tier>` to mechanically verify items marked with [lint].

    ### Scout & Context (light+)
    - [ ] [lint] Scout summary covers >= 3/6 topics: ownership, reusable assets, change-propagation, integration, verification, known unknowns
    - [ ] [lint] Each capability labeled confirmed / inferred / unresolved
    - [ ] [lint] Execution model recorded in workflow-state.md or alignment.md (subagent-mandatory or single-agent with rationale)

    ### Impact & Quality (standard+)
    - [ ] [lint] Change-propagation matrix present in context.md (table: change surface → direct consumers → indirect consumers → risk)
    - [ ] [lint] Non-functional dimensions probed: performance, security, reliability, observability (min 2/4)
    - [ ] Error/failure paths include user-visible behavior descriptions (what the end user sees, not just internal state)
    - [ ] [lint] Configuration items declare effective-when (immediate, next session, after restart, etc.)
    - [ ] [lint] Test strategy note per capability (test type, platform coverage)

    ### Deep-Only (deep)
    - [ ] Non-functional requirements quantified with specific thresholds (not just mentioned)
    - [ ] All error paths have explicit user-visible behavior contracts
    - [ ] All configuration items have effective-when declarations

    ## Alignment Readiness

    - [ ] alignment.md exists
    - [ ] context.md exists
    - [ ] workflow-state.md exists
    - [ ] Fixed lifecycle state is recorded
    - [ ] Release decision is recorded
    - [ ] Release decision is either `Aligned: ready for plan` or `Force proceed with known risks`
    - [ ] High-risk capabilities have checkpoints for purpose, boundary, and acceptance proof
    - [ ] Feasibility gate is recorded; unproven implementation chains record canonical `/sp.deep-research` as the next workflow token
    - [ ] High-impact decision forks are resolved or explicitly force-carried
    - [ ] Locked decisions are preserved in context.md
    - [ ] workflow-state.md records `sp-specify` with planning-only restrictions
    - [ ] Remaining risks are empty for normal completion

    ## Notes

    - Items marked incomplete require spec updates before planning.
    - Items marked [lint] can be verified automatically with `spec-lint`
    - `spec-lint` exit code 0 = all [lint] checks pass; exit code 1 = failures present
    - For tier selection: light (small bug fix, local change), standard (new capability, cross-module), deep (new system, protocol boundary, security-sensitive)
    ```

{{spec-kit-include: ../command-partials/common/gate-self-check.md}}

25. Re-run validation after edits. Normal completion must pass all required checks.

26. Re-run the Final Validation & Release self-review (Step 17A) if artifacts were edited. Normal completion must pass all required checks.

27. Report completion with:
    - branch name
    - spec file path
    - alignment report path
    - context file path
    - workflow-state file path
    - references file path when created
    - checklist results
    - release decision
    - readiness for the next phase (`{{invoke:plan}}` for the mainline, `{{invoke:clarify}}` when deeper analysis is still needed, or `{{invoke:deep-research}}` when feasibility must be proven first)
    - recommended review follow-up: `{{invoke:clarify}}` when the user wants one more targeted repair pass over the written spec package before planning
    - cognition follow-up: if artifact-only specification work identifies future modules, workflows, integration boundaries, verification surfaces, or ownership facts that the current query-backed runtime does not yet encode, record that as an advisory in `workflow-state.md`, `alignment.md`, or `context.md`; do not mark project cognition dirty or require a refresh until actual source/runtime changes make the runtime truth out of date
    - [AGENT] before final completion text, if auto-capture did not preserve a reusable `workflow_gap`, `user_preference`, or `project_constraint`, use the manual `learning capture` helper surface.
      Required options: `--command`, `--type`, `--summary`, `--evidence`
    - leave one-off runs as `--decision none` with no reusable lesson; store reusable lessons as index/detail entries, and use `{{specify-subcmd:learning promote --target learning ...}}` only after explicit confirmation or proven recurrence
    - only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or a repeated recurrence that should become shared project memory
    - Use the user's current language for the completion report and any explanatory text, while preserving literal command names, file paths, and fixed status values exactly as written.

28. **Check for extension hooks**: After reporting completion, check if `.specify/extensions.yml` exists in the project root.
    - If it exists, read it and look for entries under the `hooks.after_specify` key.
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

## Quick Guidelines

- Focus on **WHAT** users need, **WHY** they need it, and what a planner must preserve.
- Start with whole-feature analysis before writing capability details.
- Decompose into capabilities only after the whole feature is understood.
- Distinguish confirmed facts, low-risk inferences, and unresolved items explicitly.
- Avoid HOW to implement unless a dependency, constraint, or planning risk must be named.
- Write for business stakeholders and planners, not only developers.
- Do not embed checklists in the spec itself.
- Low-risk defaults may be adopted silently.
- High-impact ambiguity must be resolved or explicitly force-continued.
- Preserve maintainable wording and avoid brittle, surface-only summaries.

### Section Requirements

- **Mandatory sections**: Must be completed for every feature.
- **Optional sections**: Include only when relevant to the feature.
- When a section doesn't apply, remove it entirely (do not leave "N/A").

### For AI Generation

1. Do not guess high-impact decisions that materially affect scope, UX, compatibility, security, data shape, acceptance testing, capability boundaries, or downstream planning.
2. Use low-risk defaults quietly and record them in `alignment.md` plus the alignment state in `spec.md` when relevant.
3. If the user thinks they have explained the request clearly but important ambiguity remains, keep clarifying.
4. Think like a planner and tester: if a requirement cannot be planned or tested reliably, it is not aligned enough yet.
5. Normal completion requires no open clarification markers.
6. If the user insists on continuing anyway, allow `Force proceed with known risks`, but record the unresolved items and likely downstream impact.
7. Match the user's current language for all user-visible output unless a literal command name, file path, or fixed status value must remain unchanged.
8. Do not treat MVP minimization as the default strategy; scope the first release to a coherent, quality-appropriate slice unless the user explicitly asks for a smaller release.
