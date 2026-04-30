---
description: Use when a new or changed feature request needs guided requirement discovery and a planning-ready specification package.
workflow_contract:
  when_to_use: A new or changed feature request needs a planning-ready specification package instead of immediate implementation.
  primary_objective: 'Produce the specification artifact set grounded in repository reality: `spec.md`, `alignment.md`, `context.md`, and supporting references when needed.'
  primary_outputs: '`FEATURE_DIR/spec.md`, `FEATURE_DIR/alignment.md`, `FEATURE_DIR/context.md`, `FEATURE_DIR/references.md`, and `FEATURE_DIR/workflow-state.md`.'
  default_handoff: /sp-plan once planning-critical ambiguity and feasibility risk are reduced far enough; otherwise stay in clarification, recommend /sp-clarify, or route uncertain implementation chains through /sp-deep-research.
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

**Run first-party workflow quality hooks once `FEATURE_DIR` is known**:
- Use `specify hook preflight --command specify --feature-dir "$FEATURE_DIR"` before deeper workflow execution so the shared product guardrail layer can block stale or invalid entry conditions.
- After `WORKFLOW_STATE_FILE` is created or resumed, use `specify hook validate-state --command specify --feature-dir "$FEATURE_DIR"` so the shared state validator confirms `workflow-state.md` matches the `sp-specify` contract.
- Before final handoff, use `specify hook validate-artifacts --command specify --feature-dir "$FEATURE_DIR"` so the required `spec.md`, `alignment.md`, `context.md`, and `workflow-state.md` set is machine-checked rather than trusted from chat narration.
- Before any compaction-risk transition or after major artifact synthesis, use `specify hook checkpoint --command specify --feature-dir "$FEATURE_DIR"` to emit a resume-safe checkpoint payload from `workflow-state.md`.

## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command specify --format json` when available so passive learning files exist, the current specification run sees relevant shared project memory, and repeated candidates, including repeated high-signal candidates, can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader command-local context.
- Review `.planning/learnings/candidates.md` only when it still contains candidate learnings relevant to specification after the passive start step, especially repeated workflow gaps, user preferences, or project constraints for the touched area.
- [AGENT] When specification friction appears, run `specify hook signal-learning --command specify ...` with user-correction, route-change, scope-change, false-start, or hidden-dependency counts.
- [AGENT] Before final completion or blocked reporting, run `specify hook review-learning --command specify --terminal-status <resolved|blocked> ...`; use `--decision none --rationale "..."` only when no reusable `workflow_gap`, `user_preference`, `decision_debt`, or `project_constraint` exists.
- [AGENT] Prefer `specify learning capture-auto --command specify --feature-dir "$FEATURE_DIR" --format json` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `specify hook capture-learning --command specify ...` when the durable state does not capture the reusable lesson cleanly.
- Treat this as a passive shared-memory layer, not as a separate user workflow. Do not redirect the user into a dedicated learning-management command.

## Workflow Phase Lock

- [AGENT] Create or resume `WORKFLOW_STATE_FILE` immediately after `FEATURE_DIR` is known.
- Read `templates/workflow-state-template.md`.
- Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth on resume after compaction for the current command, allowed artifact writes, forbidden actions, authoritative files, next action, and exit criteria.
- Set or update the state for this run with at least:
  - `active_command: sp-specify`
  - `phase_mode: planning-only`
  - `forbidden_actions: edit source code, edit tests, fix build/tooling, implement behavior, run implementation-oriented fix loops`
- Do not implement code, edit source files, edit tests, or run implementation-oriented fix loops from `sp-specify`.
- When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.

## Outline

The text the user typed after `/sp.specify` is the starting point, not the finished requirement package. Your responsibility is to analyze the whole feature first, decompose it into capabilities, and emit a planning-ready requirement package with confidence tracking rather than a surface summary.

1. Parse the user description.
   - If empty: ERROR "No feature description provided".

2. Generate a concise short name (2-4 words) for the branch.
   - Keep it descriptive and action-oriented when possible.

3. Create the feature branch by running the script once with `--json`/`-Json` and `--short-name`/`-ShortName`.
   - Before running the script, check if `.specify/init-options.json` exists and read `branch_numbering`.
   - If the value is `"timestamp"`, add `--timestamp` or `-Timestamp`.
   - If the value is `"sequential"` or missing, use default numbering.
   - Do not pass `--number`.
   - Parse `BRANCH_NAME`, `SPEC_FILE`, and `FEATURE_DIR` from the JSON response.
   - Set `ALIGNMENT_FILE` to `FEATURE_DIR/alignment.md`.
   - Set `CONTEXT_FILE` to `FEATURE_DIR/context.md`.
   - Set `REFERENCES_FILE` to `FEATURE_DIR/references.md`.
   - Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.
   - [AGENT] Create or resume `WORKFLOW_STATE_FILE` immediately after `FEATURE_DIR` is known.
   - Read `templates/workflow-state-template.md`.
   - If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
   - Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth for `sp-specify`.
   - Persist at least these fields for the active pass:
     - `active_command: sp-specify`
     - `phase_mode: planning-only`
     - `allowed_artifact_writes: spec.md, alignment.md, context.md, references.md, workflow-state.md, checklists/requirements.md`
     - `forbidden_actions: edit source code, edit tests, fix build/tooling, implement behavior, run implementation-oriented fix loops`
     - `authoritative_files: spec.md, alignment.md, context.md, references.md`
   - When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.

4. Ensure repository navigation system exists.
   - Check whether `.specify/project-map/index/status.json` exists.
   - If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - [AGENT] If freshness is `missing` or `stale`, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the current request, run `/sp-map-scan` followed by `/sp-map-build` before continuing. If only `review_topics` are non-empty, review those topic files before deciding whether the existing map is still sufficient.
   - Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
   - Check whether `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md` exist.
   - [AGENT] If the navigation system is missing, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - Task-relevant coverage is insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
   - Treat task-relevant coverage as a coverage-model check, not just a file-presence check. Coverage is also insufficient when the handbook/project-map set cannot yet tell you:
     - owning surfaces and truth locations
     - consumer or adjacent surfaces likely to be affected
     - change-propagation hotspots
     - verification entry points
     - known unknowns or stale evidence boundaries
   - [AGENT] If task-relevant coverage is insufficient for the current request, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - Treat `PROJECT-HANDBOOK.md` as the root navigation artifact and use `Topic Map` to choose the smallest relevant topical documents for the touched area.

5. Load context.
   - Read `templates/spec-template.md`.
   - Read `templates/alignment-template.md`.
   - Read `templates/context-template.md`.
   - Read `templates/references-template.md`.
   - Read `templates/workflow-state-template.md`.
   - Read `.specify/memory/constitution.md` if present.
   - Read `.specify/memory/project-rules.md` if present.
   - Read `.specify/memory/project-learnings.md` if present.
   - If `.planning/learnings/candidates.md` exists, inspect only the entries relevant to specification so repeated workflow gaps, user preferences, and project constraints are not rediscovered from scratch.
   - [AGENT] Read `PROJECT-HANDBOOK.md` if present and treat it as the primary codebase-scout input for brownfield understanding.
   - Read the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md`.
   - If `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` exists and the request is about brownfield testing-system construction, read it and treat it as the primary brownfield testing-program input before clarification. Extract module priority waves, `small / medium / large` policy, scenario matrix expectations, allowed testability refactors, coverage goals, and CI gate expectations from it.
   - From the handbook navigation system, extract the current module ownership, reusable components/services/hooks, integration points, truth-owning surfaces, adjacent workflows, key entities, architectural constraints, change-propagation hotspots, verification entry points, and known unknowns relevant to the request.
   - If the topical coverage for the touched area is missing, stale, or too broad, or task-relevant coverage is insufficient, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then inspect the minimum live files still needed to replace guesswork with evidence before asking planning-critical questions.
   - Read repository context relevant to the request.
   - Read existing specs/docs if relevant.
   - Read user-supplied references, examples, or linked material when they materially affect the requirement package.

6. Run a codebase scout before clarification.
   - Treat `PROJECT-HANDBOOK.md` as the default scout artifact for understanding the existing system shape.
   - Use `Topic Map` to choose the smallest relevant topical documents before broad file reads.
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

7. Infer task classification.
   Infer exactly one:
   - greenfield project
   - existing feature addition
   - bug fix
   - technical refactor
   - docs/config/process change
   - Task classification changes which requirement dimensions are probed. Use the inferred class to choose the questioning path instead of reusing one generic flow for every request.

   Briefly tell the user your inferred classification and allow correction before continuing.

8. Analyze the whole feature before decomposing it.
   Build a top-down understanding grounded in the project handbook and touched-area topical map plus any targeted live-file reads. It must cover:
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

9. Choose alignment mode and collaboration strategy.
   - Lightweight mode for local, context-rich changes.
   - Deep mode for greenfield, multi-capability, or materially ambiguous work.
   - [AGENT] Before decomposition begins, assess the current workload shape and agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="specify", snapshot, workload_shape)`.
   - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
   - Decision order is fixed:
     - One safe validated lane -> `one-subagent` on `native-subagents` when available.
     - Two or more safe isolated lanes -> `parallel-subagents` on `native-subagents` when available.     - No safe lane, overlapping writes, missing contract, or unavailable delegation -> `subagent-blocked` with a recorded reason.
   - If collaboration is justified, keep `specify` lanes limited to:
     - repository and local context analysis
     - external references and supporting material analysis
     - ambiguity, risk, and gap analysis
   - Required join points:
     - before capability decomposition
     - before writing `spec.md`, `alignment.md`, and `context.md`
   - Record the chosen strategy, reason, any blocked dispatch or escalation decision, selected lanes, and join points in `alignment.md`.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.

10. Decomposition gate.
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

11. Capability decomposition.
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

12. Run task-type mandatory clarity gates.

    Greenfield project:
    - target users
    - core problem
    - first-release scope
    - out-of-scope boundary
    - core user flows
    - key domain entities
    - success criteria
    - hard constraints if any

    Existing feature addition:
    - affected module or workflow
    - impacted surfaces and consumers
    - intended users
    - relationship to existing behavior
    - compatibility expectations
    - data/state impact
    - trigger/event source when behavior depends on a cross-component signal
    - contract/protocol boundary when the feature crosses services, processes, runtimes, or stored event seams
    - retry/dedup/idempotency expectations for async or event-driven behavior
    - acceptance criteria

    Bug fix:
    - current incorrect behavior
    - expected correct behavior
    - reproduction conditions
    - impact scope
    - affected surfaces and change-propagation path
    - regression-sensitive areas
    - completion criteria

    Technical refactor:
    - reason for change
    - change boundary
    - affected surfaces and compatibility boundaries
    - behavior that must remain unchanged
    - risk tolerance
    - migration/transition allowance
    - completion criteria

    Docs/config/process change:
    - Treat this as a planning-critical questioning surface, not a passive cleanup request.
    - Before normal alignment release, collect every planning-critical dimension below: changed artifact, change objective, affected users or teams, compatibility/process constraints, validation method, and completion criteria.
    - Ask for the changed artifact.
    - Ask for the change objective.
    - Ask for the affected users or teams.
    - Ask for compatibility/process constraints.
    - Ask for the validation method.
    - Ask for completion criteria.
    - Do not treat missing answers in this path as passive housekeeping detail or low-priority cleanup context.

    Rules:
    - If an item is already clear from context, do not ask.
    - If it is low-risk and inferable, adopt a default silently and record it later under `Analysis Confidence -> Low-Risk Inferences`.
    - If it is high-impact and unclear, ask.

13. Run an implementation-oriented analysis pass before concluding alignment.
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

13b. Run an engineering-completeness gate for boundary-sensitive work.
    - Trigger this gate when the feature crosses a service/process/runtime boundary, depends on async or event delivery, creates user-visible persisted state, or adds configuration that changes delivery behavior.
    - Confirm or explicitly defer, with reason, at minimum:
      - trigger or event source
      - payload, identifiers, ordering, or delivery contract
      - state lifecycle, retention, archival, or cleanup expectations
      - retry, deduplication, idempotency, or replay expectations
      - user-visible failure, stale-state, or recovery behavior
      - configuration surface and when changes take effect
      - observability or support evidence needed to diagnose failures
    - If repository evidence can answer one of these, use the scout summary or targeted live-file reads instead of asking the user to restate codebase facts.
    - If the user gives a broad answer such as "we can make the internals detailed later", either turn it into a concrete checklist for confirmation or mark it as an explicit deferred risk.
    - Do not treat this gate as implementation brainstorming; stay at the level of requirement-shaping contracts, lifecycle expectations, and planning safety.

13c. Run a feasibility and implementation-chain gate.
    - For each capability, decide whether the implementation chain is already credible enough for planning.
    - Treat the chain as credible when repository evidence, retained references, or prior working behavior clearly show:
      - trigger/input
      - owning module, API, service, library, or integration surface
      - state/output path
      - validation evidence or acceptance proof
    - Route to `/sp.deep-research` before `/sp.plan` when a capability depends on an unproven API, library, algorithm, platform behavior, data volume, permission boundary, external integration, native/plugin bridge, generated-code workflow, performance envelope, or other unknown where planning would otherwise guess.
    - Prefer `/sp.deep-research` when the real question is "can this work?" and a small disposable demo under `FEATURE_DIR/research-spikes/` would prove the path.
    - Treat `/sp.deep-research` as a research-to-plan handoff path: its `deep-research.md` must preserve findings, demo evidence, rejected options, constraints, and a `Planning Handoff` that `/sp.plan` can consume.
    - Do not require `/sp.deep-research` for minor adjustments to capabilities that already exist in the project and have a clear implementation path.
    - Record feasibility status in `alignment.md` as `Not needed`, `Needed before plan`, `Completed`, or `Blocked`.
    - If feasibility risk is actually a requirement ambiguity, keep it in `sp-specify` or route to `/sp.clarify` instead of treating it as research.

14. Identify gray areas before concluding alignment.
   - Identify 3-5 planning-relevant gray areas: decisions that could reasonably go multiple ways and would materially change implementation, planning, or testing.
   - Derive gray areas from the combination of user intent, `PROJECT-HANDBOOK.md`, and targeted repository evidence instead of from a generic question catalog.
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
     - Synthesize these decisions into `context.md` so downstream planning does not rely on reconstructing them from prose alone.

15. Run a high-impact ambiguity scan.
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

16. Clarification loop.
    - **Question output hard gate**: before generating any clarification question, confirmation, or bounded selection, check whether a native structured question tool is available in the current runtime.
    - If a native structured question tool is available, you MUST use it.
    - Do not render the textual fallback block when the native tool is available.
    - Do not self-authorize textual fallback because the question seems simple, short, or easy to express in plain text.
    - Only fall back after the native tool is unavailable or the tool call fails. If a native tool call fails once, retry once before falling back.
    - Keep the interaction feeling like guided requirement discovery rather than a shallow questionnaire.
    - Ask only high-value questions.
    - Before asking a planning-critical question, check whether `PROJECT-HANDBOOK.md` or touched-area topical documents already answer it; do not ask the user for facts the codebase can supply.
    - Use grouped questions for simple/local changes.
    - Use one question at a time for complex/high-risk cases.
    - Ask at most one unanswered high-impact question per message.
    - Let unresolved gray areas drive the next question; do not rotate through generic requirement categories once the active gray area is known.
    - Keep the active gray area open until the decision is specific enough that a downstream planner would not need to reopen it for behavior, boundary, or acceptance-shaping detail.
    - Make the next question build directly on the user's most recent answer rather than resetting to generic prompts.
    - Use the previous answer to choose the next narrowing move, not a recycled generic checklist question.
    - Use code-aware follow-ups when possible: reference the current module, workflow, entity, command, or reusable pattern named in the handbook/project-map navigation system or repository evidence so the question is about the real decision fork, not an abstract category.
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

17. Final Validation & Release.
    This single gate replaces the old multi-step release sequence. Complete all three sub-checks before reporting completion.

    **A. Artifact Self-Review**: Review the written `spec.md`, `alignment.md`, and `context.md` for:
    - placeholders, TODOs, or `[NEEDS CLARIFICATION]` markers
    - contradictions or capability drift between artifacts
    - missing capability checkpoints or weak acceptance proof
    - requirement-vs-implementation language drift
    - If the selected strategy supports collaboration and the workload justified it, use one read-only reviewer lane to inspect the draft artifact set for the same failure modes.
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

    **C. Release Decision**: Decide exactly one:
    - `Aligned: ready for plan` — use when: mandatory clarity gates are resolved, capability decomposition is bounded, no unresolved high-impact ambiguity remains, no `[NEEDS CLARIFICATION]` markers exist, the spec can be planned and tested coherently.
    - `Force proceed with known risks` — use only when the user explicitly accepts that unresolved planning risk will be carried into downstream work.
    - If neither condition is met, continue clarification.

    After the release decision is made, ask the user to review the written artifact set and make the next path explicit:
    - proceed to `/sp.plan`
    - revise current artifacts
    - continue analysis with `/sp.clarify`
    - prove feasibility with `/sp.deep-research`

    Do not release `Aligned: ready for plan` when the current understanding still depends on taste words, implicit defaults, or untested assumptions. Do not release for cross-boundary or event-driven features when trigger source, contract identifiers, lifecycle/retention, failure path, or configuration semantics are still fuzzy.

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
    - task classification
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
    **Tier**: light | standard | deep (choose based on task classification and boundary sensitivity)

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
    - [ ] Task classification is recorded
    - [ ] Release decision is recorded
    - [ ] Release decision is either `Aligned: ready for plan` or `Force proceed with known risks`
    - [ ] High-risk capabilities have checkpoints for purpose, boundary, and acceptance proof
    - [ ] Feasibility gate is recorded; unproven implementation chains route to `/sp.deep-research`
    - [ ] High-impact decision forks are resolved or explicitly force-carried
    - [ ] Locked decisions are preserved in context.md
    - [ ] workflow-state.md records `sp-specify` with planning-only restrictions
    - [ ] Remaining risks are empty for normal completion

    ## Notes

    - Items marked incomplete require spec updates before `/sp.plan`
    - Items marked [lint] can be verified automatically with `spec-lint`
    - `spec-lint` exit code 0 = all [lint] checks pass; exit code 1 = failures present
    - For tier selection: light (small bug fix, local change), standard (new capability, cross-module), deep (new system, protocol boundary, security-sensitive)
    ```

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
    - readiness for the next phase (`/sp.plan` for the mainline, `/sp.clarify` when deeper analysis is still needed, or `/sp.deep-research` when feasibility must be proven first)
    - recommended review follow-up: `/sp.clarify` when the user wants one more targeted repair pass over the written spec package before planning
    - if this pass reveals that the current atlas is now too weak for the touched area, or that the spec introduced new modules, workflows, integration boundaries, verification surfaces, or ownership facts the current handbook/project-map does not yet capture, mark `.specify/project-map/index/status.json` dirty through the project-map freshness helper and recommend `/sp-map-scan` followed by `/sp-map-build` before later brownfield execution work proceeds
    - [AGENT] before final completion text, capture any new `workflow_gap`, `user_preference`, or `project_constraint` learning through `specify learning capture --command specify ...`
    - keep lower-signal items as candidates and use `specify learning promote --target learning ...` only after explicit confirmation or proven recurrence
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
