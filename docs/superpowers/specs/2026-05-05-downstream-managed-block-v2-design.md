# Downstream Managed Block V2 Design

**Date:** 2026-05-05  
**Scope:** Generated downstream `CLAUDE.md` / `AGENTS.md` managed Spec Kit Plus block  
**Primary Goal:** Improve downstream agent execution reliability by strengthening mechanism-level guidance, artifact semantics, and truth-surface usage without overloading the managed block with low-value detail.

## Problem Statement

The current downstream managed block successfully teaches that Spec Kit Plus has workflows, memory, project-map, testing surfaces, and delegated execution rules. It does **not** yet teach enough about:

- which generated artifacts own which kinds of truth
- which project-map documents answer which classes of questions
- when an agent must read a specific artifact before proceeding
- which artifacts are execution inputs versus documentation outputs
- which mechanism surfaces must be executed rather than paraphrased in chat

This gap causes the most common downstream failures:

1. agents know a file exists but do not know why it matters
2. agents continue from branch name or chat memory instead of state truth
3. agents summarize completion in chat without executing the required helper, hook, or artifact write
4. agents treat testing artifacts as generic notes instead of contractual workflow inputs
5. agents consume atlas content too broadly or too narrowly because the managed block does not explain reading scope by document role

The goal of V2 is to make downstream agents more operationally correct, not merely more informed.

## Design Goals

1. Keep the managed block short enough to remain readable as an always-read startup surface.
2. Add high-value mechanism guidance that materially changes downstream execution behavior.
3. Avoid duplicating long workflow-template detail, command-shape catalogs, or volatile per-file enumerations.
4. Preserve integration-neutral product truth while allowing integration-specific invocation syntax elsewhere.
5. Teach artifact and atlas semantics in a way that reduces guessing and chat-only compliance.

## Non-Goals

- Reproducing full workflow templates inside the managed block
- Enumerating every helper command shape
- Duplicating the full PRD reconstruction artifact inventory
- Embedding implementation-plan detail for individual workflows
- Turning the managed block into a full operator handbook

## Recommended Managed Block Strategy

Use a **layered strong-constraint block**:

1. **Execution Rules**
   - route first
   - read the right truth surfaces
   - do not substitute chat memory for durable state
   - do not substitute chat summaries for runtime/mechanism execution

2. **Artifact Semantics**
   - explain what each artifact family does
   - explain when it constrains later work
   - explain what it must not be mistaken for

3. **Atlas Reading Responsibilities**
   - explain which root project-map document answers which category of question
   - instruct the agent to read the smallest relevant set

4. **Recovery and Delegation Guarantees**
   - lane-first recovery
   - structured handoff requirements
   - refresh-or-dirty enforcement for stale map state

This yields stronger downstream execution without turning the block into a bloated reference manual.

## Required Additions

### 1. Source-of-Truth Enforcement

This must be explicit.

Downstream agents must be told:

- resume, closeout, and next-step selection must start from durable state surfaces
- current branch and chat context are secondary hints, not truth sources
- if a workflow has a state artifact, that artifact must be read before continuing

Recommended wording direction:

- "For resume, next-step routing, and workflow closeout, read the relevant durable state file first. Do not continue from branch name or chat memory alone when `workflow-state.md`, `testing-state.md`, quick-task `STATUS.md`, or project-map freshness state already exist."

### 2. No Chat-Only Completion

This is one of the highest-value additions.

Downstream agents must be told:

- completion claims are invalid unless required artifacts, hooks, helpers, or state updates actually happened
- analysis claims are invalid if the required atlas or state surfaces were not actually read
- a workflow cannot be considered complete merely because the agent produced a convincing summary

Recommended wording direction:

- "Do not substitute chat narration for workflow execution. If a workflow requires an artifact write, hook/helper execution, or state update, perform it explicitly rather than describing it as though it happened."

### 3. Atlas Reading Responsibilities

The managed block should explain what each root project-map document is for.

This belongs in downstream instructions because it changes how agents choose context and avoids random repo-wide scanning.

Recommended role mapping:

- `PROJECT-HANDBOOK.md`
  - root navigation artifact
  - choose the smallest relevant project-map topics before broad source reads
- `.specify/project-map/root/ARCHITECTURE.md`
  - architecture boundaries, truth ownership, change propagation, core seams
- `.specify/project-map/root/STRUCTURE.md`
  - directory ownership, shared write surfaces, file placement
- `.specify/project-map/root/WORKFLOWS.md`
  - workflow paths, state lifecycles, handoffs, recovery semantics
- `.specify/project-map/root/TESTING.md`
  - smallest meaningful checks, regression-sensitive areas, verification expectations

Recommended wording direction:

- "Read atlas content by role, not by filename accumulation. Use `PROJECT-HANDBOOK.md` to choose the smallest relevant topic set, then read `ARCHITECTURE.md`, `STRUCTURE.md`, `WORKFLOWS.md`, or `TESTING.md` only when the task needs their specific truth."

### 4. Testing Artifact Semantics

This is important enough to promote into the managed block because `sp-test-scan` and `sp-test-build` outputs become real downstream control surfaces.

Recommended semantics:

- `TEST_SCAN.md`
  - evidence and module risk scan
  - not the executable build contract
- `TEST_BUILD_PLAN.md` / `.json`
  - executable testing-system build lanes and validation commands
  - primary `sp-test-build` inputs
- `UNIT_TEST_SYSTEM_REQUEST.md`
  - brownfield testing-program input for later scoped spec/planning work
- `TESTING_CONTRACT.md`
  - durable testing obligations that later workflows should honor automatically
- `TESTING_PLAYBOOK.md`
  - operator and maintainer runbook for test execution
- `COVERAGE_BASELINE.json`
  - observed baseline data, not acceptance proof by itself
- `testing-state.md`
  - `sp-test-*` recovery and next-step truth

Recommended wording direction:

- "Treat testing artifacts by role. `TEST_SCAN.md` is scan evidence, `TEST_BUILD_PLAN.*` is the build blueprint, `TESTING_CONTRACT.md` is the durable downstream testing rule surface, and `testing-state.md` is the recovery truth for `sp-test-*` workflows."

### 5. Learning / Memory Semantics

The managed block should explain memory layers in terms of authority and usage.

Recommended semantics:

- `constitution.md`
  - principle-level rules
- `project-rules.md`
  - stable defaults and reusable constraints
- `project-learnings.md`
  - confirmed reusable experience
- `candidates.md`
  - lower-confidence candidate learnings only read when relevant

Recommended wording direction:

- "Treat the learning layer as workflow-execution infrastructure, not as optional notes. `constitution.md` holds principle-level rules, `project-rules.md` holds stable defaults, `project-learnings.md` holds confirmed reusable lessons, and candidate learnings should only influence work when relevant to the touched area."

### 6. Delegation Evidence Rule

This should be explicit because it is a major operational failure mode.

Recommended wording direction:

- "Subagent completion requires a structured handoff, result file, or runtime-managed result. Do not treat idle state or a chat summary as completion evidence."

### 7. Refresh-or-Dirty Hard Rule

The current direction is right, but downstream wording should enforce the binary choice.

Recommended wording direction:

- "If project-map freshness is not trustworthy, either complete a refresh and finalize it with `project-map complete-refresh`, or mark the atlas dirty with `project-map mark-dirty` and route the next brownfield workflow through `sp-map-scan -> sp-map-build`. Do not continue under known-stale atlas state without choosing one of those paths."

## Recommended Adjustments to Existing Content

### 1. Make `sp-teams` More Integration-Neutral

Current downstream guidance should not imply that durable team runtime is universal.

Recommended adjustment:

- replace Codex-specific phrasing with:
  - "Use the integration's durable team/runtime surface only when durable team state, explicit join-point tracking, or lifecycle control beyond one in-session subagent burst is required. For integrations that expose `sp-teams`, use it only in those cases."

This preserves product truth while avoiding Claude-facing confusion.

### 2. Add `sp-map-scan` and `sp-map-build` to Workflow Routing

They should appear explicitly as routable workflows, not only as a brownfield side note.

Recommended routing entries:

- `sp-map-scan` for repository-current-state atlas evidence gathering
- `sp-map-build` for compiling refreshed handbook/project-map outputs from scan inputs

### 3. Clarify Canonical Identity vs Invocation Syntax

The managed block should distinguish:

- canonical workflow identity: `sp-*`
- actual user invocation syntax: integration-specific

Recommended wording direction:

- "Treat `sp-*` names as canonical workflow identities. Actual invocation syntax depends on the integration and should be taken from generated integration-specific surfaces rather than assumed from this managed block."

## Recommended Removals or Downscopes

### 1. Downscope PRD Artifact Enumeration

The current long-form artifact list under `.specify/prd-runs/<run-id>/` is too detailed for the managed block.

Replace long enumerations with:

- "The `.specify/prd-runs/<run-id>/` tree, including its workflow state plus scan/build artifacts, is the current-state PRD reconstruction truth surface."

### 2. Downscope Long Command-Shape Catalogs

Command-shape lists are useful in docs and workflow templates but too granular for a startup managed block.

Keep only:

- mechanism surfaces exist and must be executed when required
- integration-specific invocation syntax belongs elsewhere

### 3. Downscope Full `spec-lint` Detail

The managed block should not carry the full light/standard/deep matrix.

Keep only:

- `spec-lint` is the mechanical quality gate before planning when enabled
- non-zero result means fix spec artifacts before moving to `sp-plan`

## Proposed Managed Block V2

```md
<!-- SPEC-KIT:BEGIN -->

## Spec Kit Plus Managed Rules

- `[AGENT]` marks an action the AI must explicitly execute.
- `[AGENT]` is independent from `[P]`.

## Workflow Mainline

- Treat `specify -> plan` as the default path.
- Use `clarify` only when an existing spec needs deeper analysis before planning.
- Use `deep-research` only when requirements are clear but feasibility or the implementation chain must be proven before planning; its findings and Planning Handoff become inputs to `plan`.
- Use `prd-scan -> prd-build` as the canonical existing-project reverse-PRD lane when the user needs repository-first current-state product documentation. Treat `prd` as deprecated compatibility-only routing into that pair.

## Workflow Activation Discipline

- If there is even a 1% chance an `sp-*` workflow or passive skill applies, route before any response or action, including clarifying questions, file reads, shell commands, repository inspection, code edits, test runs, or summaries.
- Do not inspect first outside the workflow; repository inspection belongs inside the selected workflow.
- Name the selected workflow or passive skill in one concise line, then continue under that contract.
- Treat `sp-*` names as canonical workflow identities. Actual invocation syntax depends on the integration and should be taken from generated integration-specific surfaces rather than assumed from this managed block.

## Brownfield Context Gate

- `PROJECT-HANDBOOK.md` is the root navigation artifact.
- Deep project knowledge lives under `.specify/project-map/`.
- Before planning, debugging, or implementing against existing code, read `PROJECT-HANDBOOK.md` and the smallest relevant `.specify/project-map/*.md` files.
- Read atlas content by role:
  - `PROJECT-HANDBOOK.md`: choose the smallest relevant topic set before broad source reads.
  - `root/ARCHITECTURE.md`: architecture boundaries, truth ownership, change propagation, and core seams.
  - `root/STRUCTURE.md`: directory ownership, shared write surfaces, and file-placement rules.
  - `root/WORKFLOWS.md`: workflow paths, handoffs, state lifecycles, and recovery semantics.
  - `root/TESTING.md`: smallest meaningful checks, regression-sensitive areas, and verification expectations.
- If handbook/project-map coverage is missing, stale, or too broad, run `sp-map-scan` followed by `sp-map-build` before continuing.
- Treat git-baseline freshness in `.specify/project-map/index/status.json` as the truth source. If the atlas is not trustworthy, either complete a refresh and finalize it with `project-map complete-refresh`, or mark it dirty with `project-map mark-dirty` and route the next brownfield workflow through `sp-map-scan -> sp-map-build`. Do not continue under known-stale atlas state without choosing one of those paths.

## Project Memory

- Passive project memory lives under `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`.
- Treat the learning layer as workflow-execution infrastructure, not as optional notes.
- `.specify/memory/constitution.md` is the principle-level source of truth when present.
- `.specify/memory/project-rules.md` holds stable defaults and reusable constraints.
- `.specify/memory/project-learnings.md` holds confirmed reusable lessons.
- `.planning/learnings/candidates.md` is a lower-confidence candidate layer and should influence work only when relevant to the touched area.

## Workflow Routing

- Use `sp-fast` only for trivial, low-risk local changes that do not need planning artifacts.
- Use `sp-quick` for bounded tasks that need lightweight tracking but not the full `specify -> plan -> tasks -> implement` flow.
- Use `sp-auto` when repository state already records the recommended next step and the user wants one continue entrypoint instead of naming the exact workflow manually.
- Use `sp-specify` when scope, behavior, constraints, or acceptance criteria need explicit alignment before planning.
- Use `sp-map-scan` when repository-current-state atlas evidence must be gathered before deeper brownfield work.
- Use `sp-map-build` when refreshed handbook/project-map outputs must be compiled from scan inputs.
- Use `sp-prd-scan` when an existing repository needs the heavy read-only current-state reconstruction scan before final PRD synthesis, and `sp-prd-build` once that scan package is ready to compile.
- Use `sp-deep-research` when a clear requirement still lacks a proven implementation chain and needs coordinated research, optional multi-agent evidence gathering, or a disposable demo before planning.
- Use `sp-debug` when diagnosis or root-cause analysis is still required before a fix path is trustworthy.
- Use `sp-test-scan` for project-level testing evidence and build planning, and `sp-test-build` for leader-managed testing-system construction.

## Artifact Priority

- `workflow-state.md` under the active feature directory is the stage/status source of truth for resumable workflow progress. Read it before resume, next-step routing, or workflow closeout; do not continue from branch name or chat memory alone when it exists.
- `alignment.md` and `context.md` under the active feature directory carry locked decisions from `sp-specify` into planning.
- `plan.md` under the active feature directory is the implementation design source of truth once planning begins.
- `tasks.md` under the active feature directory is the execution breakdown source of truth once task generation begins.
- `.specify/prd-runs/<run-id>/`, including its workflow state and scan/build artifacts, is the current-state PRD reconstruction truth surface. Treat it as documentation output unless later work explicitly adopts it as planning input.
- `.specify/testing/testing-state.md` is the recovery and next-step truth for `sp-test-*`.
- Treat testing artifacts by role:
  - `TEST_SCAN.md`: scan evidence and module risk findings, not the executable build contract.
  - `TEST_BUILD_PLAN.md` / `.json`: build-ready testing-system lanes and validation commands; primary `sp-test-build` inputs.
  - `UNIT_TEST_SYSTEM_REQUEST.md`: brownfield testing-program input for later scoped spec/planning work.
  - `TESTING_CONTRACT.md`: durable downstream testing obligations that later workflows should honor automatically.
  - `TESTING_PLAYBOOK.md`: operator and maintainer runbook for test execution.
  - `COVERAGE_BASELINE.json`: observed baseline data, not acceptance proof by itself.

## Execution and Closeout Rules

- Do not substitute chat narration for workflow execution. If a workflow requires an artifact write, helper/hook execution, validation run, or state update, perform it explicitly rather than describing it as though it happened.
- For resume, next-step routing, and closeout, read the relevant durable state surface first (`workflow-state.md`, `.specify/testing/testing-state.md`, quick-task `STATUS.md`, or project-map freshness state) before deciding what happens next.
- If the active workflow has a truth-owning artifact set, do not claim completion until those artifacts exist and any required validation or closeout mechanism has run truthfully.

## Delegated Execution Defaults

- Dispatch native subagents by default for independent, bounded lanes when parallel work materially improves speed, quality, or verification confidence.
- Use a validated `WorkerTaskPacket` or equivalent execution contract before subagent work begins.
- Do not dispatch from raw task text alone.
- Wait for each subagent's structured handoff before integrating or marking work complete. Idle state or a chat summary is not completion evidence.
- Use the integration's durable team/runtime surface only when durable team state, explicit join-point tracking, result files, or lifecycle control beyond one in-session subagent burst is required.

## Map Maintenance

- If a change alters architecture boundaries, ownership, workflow names, integration contracts, or verification entry points, refresh `PROJECT-HANDBOOK.md` and the affected `.specify/project-map/*.md` files.
- If a full refresh can be completed now, run `sp-map-scan` followed by `sp-map-build`, then finalize with `project-map complete-refresh`.
- Otherwise use `project-map mark-dirty` as the manual override/fallback and explicitly route the next brownfield workflow through `sp-map-scan` followed by `sp-map-build`.
- Do not treat consumed handbook/project-map context as self-maintaining; the agent changing map-level truth is responsible for keeping the atlas current.

- Preserve content outside this managed block.
<!-- SPEC-KIT:END -->
```

## Tradeoffs

### What This Improves

- reduces branch-first and chat-memory resume errors
- reduces chat-only "done" claims
- teaches agents what atlas documents are for instead of only naming them
- makes testing artifacts operationally meaningful rather than decorative
- keeps the block integration-neutral while preserving strong routing behavior

### What This Intentionally Leaves Out

- full helper command-shape catalogs
- long PRD artifact file lists
- per-workflow procedural detail already owned by templates
- deep `spec-lint` matrices

## Adoption Guidance

1. Update both shared context-update generators:
   - `scripts/bash/update-agent-context.sh`
   - `scripts/powershell/update-agent-context.ps1`
2. Keep downstream managed-block assertions in tests aligned with the new wording.
3. Prefer contract-level assertions in tests:
   - source-of-truth enforcement
   - atlas document role semantics
   - testing artifact semantics
   - no chat-only completion language
4. Avoid growing the managed block with helper syntax inventories unless a failure pattern proves they must live there.

## Spec Self-Review

### Placeholder Scan

No placeholders, TODOs, or open drafting markers remain.

### Internal Consistency

The design consistently recommends a layered strong-constraint managed block, not a full workflow-template duplication strategy.

### Scope Check

This is appropriately scoped to one change surface: downstream managed context generation and its contract semantics.

### Ambiguity Check

Potential ambiguity around `sp-teams` was resolved by explicitly moving to integration-neutral wording.

## User Review Gate

This document is the design proposal for the downstream managed block V2. Review it before any implementation pass that changes the generated `CLAUDE.md` / `AGENTS.md` managed block text.
