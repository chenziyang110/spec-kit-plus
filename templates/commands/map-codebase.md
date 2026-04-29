---
description: Use when handbook/project-map coverage is missing, stale, or insufficient and you need to generate or refresh the codebase navigation system from live code.
workflow_contract:
  when_to_use: A workflow needs reliable handbook/project-map coverage and the current navigation artifacts are missing, stale, or too weak for the touched area.
  primary_objective: Generate or refresh the canonical atlas-style technical encyclopedia directly from the live repository.
  primary_outputs: '`PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, `.specify/project-map/modules/<module-id>/*.md`, and `.specify/project-map/index/status.json`.'
  default_handoff: Return to the blocked workflow that required fresh navigation coverage.
---

{{spec-kit-include: ../command-partials/map-codebase/shell.md}}

This workflow is the explicit brownfield mapping entrypoint. When another
workflow needs fresh navigation coverage, it should run `/sp-map-codebase`
before continuing.

If `$ARGUMENTS` names a subsystem, workflow, or focus area, use it to bias the
scout and refresh emphasis, but still keep all canonical map outputs globally
coherent.

Treat this workflow as the repository's comprehensive technical-documentation
generator. The resulting handbook/project-map system must serve as an atlas-style technical encyclopedia and durable
technical asset for onboarding, architecture review, technical-debt assessment,
and refactor planning. Analyze both macro architecture and micro
implementation-level details; do not stop at repository shape or shallow
navigation summaries.

## Context

- Primary inputs: the live codebase, any existing handbook/project-map artifacts, passive learning files, and optional focus hints from `$ARGUMENTS`.
- This command owns the canonical navigation outputs; it must not create an alternate mapping tree.
- The resulting map should make later `sp-*` workflows safer by replacing guesswork with current repository evidence.

## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command map-codebase --format json` when available so passive learning files exist, the current mapping run sees relevant shared project memory, and repeated candidates, including repeated high-signal candidates, can be auto-promoted into shared learnings at start.
- [AGENT] When mapping friction appears, run `specify hook signal-learning --command map-codebase ...` with route-change, artifact-rewrite, false-start, or hidden-dependency counts so atlas blind spots become explicit learning signals.
- [AGENT] Before reporting completion or a blocked refresh, run `specify hook review-learning --command map-codebase --terminal-status <resolved|blocked> ...`; use `--decision none --rationale "..."` only when no reusable `map_coverage_gap`, `workflow_gap`, `state_surface_gap`, or `project_constraint` exists.
- [AGENT] Prefer `specify learning capture-auto --command map-codebase --feature-dir "$FEATURE_DIR" --format json` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `specify hook capture-learning --command map-codebase ...` for structured atlas learnings when the durable state does not capture the reusable lesson cleanly.

## Output Contract

The only canonical outputs are:

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/index/atlas-index.json`
- `.specify/project-map/index/modules.json`
- `.specify/project-map/index/relations.json`
- `.specify/project-map/index/status.json`
- `.specify/project-map/root/ARCHITECTURE.md`
- `.specify/project-map/root/STRUCTURE.md`
- `.specify/project-map/root/CONVENTIONS.md`
- `.specify/project-map/root/INTEGRATIONS.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `.specify/project-map/root/TESTING.md`
- `.specify/project-map/root/OPERATIONS.md`
- `.specify/project-map/modules/<module-id>/OVERVIEW.md`
- `.specify/project-map/modules/<module-id>/ARCHITECTURE.md`
- `.specify/project-map/modules/<module-id>/STRUCTURE.md`
- `.specify/project-map/modules/<module-id>/WORKFLOWS.md`
- `.specify/project-map/modules/<module-id>/TESTING.md`

Supporting metadata written alongside the canonical map:

- `.specify/project-map/index/status.json`

`status.json` must preserve the current freshness contract. At minimum it should carry:

- `version`
- `global`
- `modules`
- global freshness metadata
- module-local freshness metadata
- module `deep_status`

The layered index contract must also preserve:

- `atlas-index.json` as the entry summary, not the truth source
- `modules.json` as the canonical module registry
- `relations.json` as the cross-module routing source
- `status.json` as the global plus module freshness source
- `deep_stale` as the explicit signal that deep module content is not current enough to trust blindly

Rules:

- Refresh the handbook/project-map navigation system when these files already
  exist; do not default to skipping.
- Keep still-correct, high-signal content; rewrite stale, duplicated, vague,
  or low-value content.
- The refreshed map must make task-relevant coverage sufficient for any touched
  area it claims to cover.
- Layering exists so map consumers can read detail on demand instead of re-reading one monolithic technical document.
- Do not treat layering as permission to discard technical detail.
- The topical map must preserve the level of detail maintainers need without relying on any older monolithic technical writeup while still splitting that detail across the canonical topical files.
- Task-relevant coverage is insufficient when the touched area is named only
  vaguely, lacks ownership or placement guidance, or lacks workflow,
  constraint, integration, or regression-sensitive testing guidance.
- Treat the map as a coverage system, not just a navigation summary.
- Treat the combined handbook/project-map set as the repository's atlas-style technical encyclopedia, not as a folder tree with commentary.
- The machine index exists to route agents into the correct root or module docs before broad live-code reads.
- `atlas-index.json` must stay intentionally small so consumers use it for routing rather than for technical truth.
- Module-local truth should live under `.specify/project-map/modules/<module-id>/`, while cross-module and repository-wide truth should live under `.specify/project-map/root/`.
- Module `deep/` content does not need automatic full refresh. When deep detail is not refreshed, mark the owning module `deep_stale` in `status.json` and say so explicitly.
- The generated navigation system should collectively cover the equivalent of these seven technical-document chapters, distributed across the canonical outputs instead of recreated as one monolithic file:
  - project architecture overview
  - directory structure and responsibilities
  - key module dependency relationships
  - core classes and interfaces
  - core data flows
  - API inventory
  - common patterns and conventions
- When scouting reveals a high-value contract or implementation detail, keep it
  in the topical map instead of collapsing it into a one-line summary.
- High-value details typically include:
  - external or exported API contracts
  - core data models, state semantics, and handoff fields
  - IPC, bridge, native-host, message, pipe, or protocol seams
  - build, packaging, toolchain, platform, architecture, and runtime invariants
  - key components whose responsibilities, inputs/outputs, or downstream effects would change how future work is implemented or verified
- Do not collapse those details into vague summaries.
- For each important capability, subsystem, workflow, or risky touched area
  discovered during scouting, the combined handbook/project-map output must
  answer:
  - what owns it
  - where the truth lives
  - what other surfaces consume it or feed it
  - how change propagates into adjacent modules, workflows, configs, docs,
    scripts, operators, or tests
  - what minimum verification evidence proves the mapped surface still works
  - what important unknowns, assumptions, or stale coverage remain
- The atlas must explicitly cover:
  - component and module dependency graph
  - runtime data and event flows
  - state lifecycle
  - deployment and runtime topology
  - build and release pipeline dependencies
  - configuration and feature-control surfaces
  - observability design
  - failure-mode and recovery model
  - security boundaries and permission model
  - decision history and architecture evolution context
- Each touched area must include workflow, constraint, integration, or regression-sensitive testing guidance somewhere in the combined handbook/project-map output.
- For each high-value capability, core module, or critical workflow, emit at least one capability card.
- Capability cards must capture: Purpose, Owner, Truth lives, Entry points, Downstream consumers, Extend here, Do not extend here, Key contracts, Change propagation, Minimum verification, Failure modes, and Confidence.
- Confidence must use only: Verified, Inferred, or Unknown-Stale.
- When a capability card is marked Inferred or Unknown-Stale, summarize that gap again in Known Unknowns, Low-Confidence Areas, or both.
- When the repository already contains older technical writeups, treat them as
  optional supporting evidence only. Reuse still-correct terminology,
  structure, ownership hints, and risk framing, but keep the canonical output
  in `PROJECT-HANDBOOK.md` plus `.specify/project-map/*.md`.
- Capability-card prioritization does not waive area coverage.
- When an area does not receive a full capability card, still record its
  ownership or placement guidance, adjacent dependencies, and minimum
  verification route in the relevant topical document.
- do not create `.planning/codebase/`, a second mapping tree, or any alternate
  source-of-truth document.

## Process

- Recover the current handbook/project-map baseline if one exists.
- Scout the live repository deeply enough to refresh ownership, contracts, workflows, integrations, testing, and operations coverage.
- Synthesize that evidence back into the canonical handbook/project-map outputs.
- Update map freshness metadata before handing control back to the blocked workflow.
- A maintainer should be able to answer what breaks, what blocks, what propagates, and what proves the change safe after reading the refreshed atlas.

## First-Party Workflow Quality Hooks

- Before broad mapping work begins, use `specify hook preflight --command map-codebase --feature-dir "$REPO_ROOT/specs"` only when the local workflow needs a machine-readable guard result for map refresh entry; treat failures as a signal that the repository state must be repaired before continuing.
- Before compaction-risk transitions or after major map synthesis, use `specify hook checkpoint --command map-codebase --feature-dir "$REPO_ROOT/specs"` only if a workflow-state-backed wrapper has created the corresponding state artifact for this mapping run.
- After a successful full refresh, prefer `specify hook complete-refresh` as the shared product path that finalizes project-map freshness state.

## Guardrails

- Do not create alternate mapping outputs or a second source of truth.
- Do not collapse high-value technical detail into vague summaries.
- Do not claim sufficient coverage for an area when the map still lacks ownership, propagation, verification, or known-unknown framing.

## Outline

1. **Load the mapping contract**
   - Read `.specify/memory/constitution.md` if present.
   - [AGENT] Read `.specify/project-map/index/status.json` if present to recover the current map baseline, dirty state, previous refresh metadata, and any module `deep_stale` warnings.
   - [AGENT] Read `.specify/project-map/index/atlas-index.json`, `.specify/project-map/index/modules.json`, and `.specify/project-map/index/relations.json` if present.
   - [AGENT] Read `PROJECT-HANDBOOK.md` and all existing `.specify/project-map/root/*.md` files if present.
   - [AGENT] If an existing repository still uses the older flat `.specify/project-map/*.md` layout, treat those files as migration-era support evidence until the layered atlas is refreshed.
   - Read `.specify/templates/project-handbook-template.md` and
     `.specify/templates/project-map/*.md` if present so the generated output
     follows the local navigation contract.
   - If the local template copies are missing, derive the contract from the
     existing handbook/project-map section structure and current repository
     conventions.

2. **Select the execution strategy**
   - [AGENT] Before broad scouting begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_execution_strategy(command_name="map-codebase", snapshot, workload_shape)`.
   - Strategy names are canonical and must be used exactly:
     `single-lane`, `native-multi-agent`, `sidecar-runtime`.
   - Decision order is fixed:
     - If the work does not justify safe fan-out -> `single-lane`
       (`no-safe-batch`)
     - Else if `snapshot.native_multi_agent` -> `native-multi-agent`
       (`native-supported`)
     - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime`
       (`native-missing`)
     - Else -> `single-lane` (`fallback`)
   - [AGENT] If the selected strategy is `native-multi-agent`, dispatch bounded explorer subagents before doing broad leader-local scouting.
   - [AGENT] Do not continue with broad sequential exploration after selecting `native-multi-agent`; either launch the explorer lanes, or record the concrete fallback reason and re-select the strategy.
   - [AGENT] For a full repository refresh with no narrow focus, launch at least three independent explorer subagents when subagent dispatch is available. Use four subagents when the repository has separate architecture, workflow, integration, and testing/operations areas.
   - If collaboration is justified, keep `map-codebase` lanes limited to:
     - architecture and structure mapping
     - conventions and testing mapping
     - integrations and runtime mapping
     - workflows, operations, and risky coordination mapping
   - Explorer subagents are read-only evidence collectors. They must return file-path evidence, ownership facts, contracts, workflows, integrations, verification routes, known unknowns, and confidence notes; they must not write handbook/project-map artifacts directly.
   - Required join points:
     - before writing `PROJECT-HANDBOOK.md`
     - before the final consistency pass across all map documents
   - The leader must wait for every dispatched explorer lane at the documented join point, integrate the returned evidence, and note any missing lane or fallback reason in the mapping summary.
   - Keep user-visible wording integration-neutral in this shared template.

3. **Scout the codebase**
   - Start from the smallest high-signal evidence first: README, package
     manifests, top-level config, entrypoints, scripts, tests, and current
     navigation docs if present.
   - Run the scout like a comprehensive codebase technical-review pass. The
     scout must explicitly include:
     - macro scan and architecture identification
     - directory structure deep analysis
     - dependency relationships and module analysis
     - core code element review
     - data flow and API surface mapping
     - patterns and conventions synthesis
   - [AGENT] Read only the live files needed to establish current facts for:
      - system shape and entrypoints
      - runtime units, execution surfaces, and major capability surfaces
      - directory ownership and write surfaces
      - key consumer surfaces and shared coordination surfaces
      - conventions and testing patterns
      - external integrations and runtime assumptions
      - user and maintainer workflows
      - operational caveats, recovery paths, and risky coordination points
      - change-propagation hotspots, validation entry points, and known unknowns
      - high-value contracts, schemas, bridge seams, and invariants that future
        implementers would otherwise have to rediscover by re-reading the live
        code
      - project type, technology stack, and build tooling
      - top-level architecture pattern and deployment shape
      - major directories and representative subdirectories
      - import/require relationships, core modules, utility modules, and strong-coupling hotspots
      - core classes, abstract classes, interfaces, enums, and major functions
      - key business flows from entry to exit
      - route definitions, controllers, exported endpoints, or command surfaces
      - design patterns, naming rules, directory customs, configuration management, and utility locations
   - Always capture actual file paths when naming code, config, scripts, or
     tests.
   - Distinguish current repository facts from recommendations. The map should
     describe what is true now, not what might be nice later.
   - Prefer evidence that reveals propagation paths: entrypoints, registries,
     routing files, schema or contract definitions, UI or CLI consumers,
     background jobs, integration adapters, verification scripts, and operator
     playbooks.
   - Explicitly scout for:
      - exported entrypoints, method families, parameter semantics, return
        shapes, error fields, and compatibility promises
      - core data structures, state transitions, persistence fields, and
        handoff identifiers
      - protocol, IPC, bridge, or native-host boundaries and their message or
        lifecycle semantics
      - data lineage, event choreography, and runtime fan-out paths
      - entity lifecycle, state-machine transitions, and persistence or cache checkpoints
      - build, packaging, toolchain, platform, architecture, and runtime
        invariants
      - API methods, endpoint families, request/response shapes, and notable
        error contracts
      - dependency seams that reveal layering, coupling direction, or risky
        cycles
      - implementation elements whose names and responsibilities future
        maintainers would need during onboarding or refactor planning

4. **Generate or refresh the topical map**
   - [AGENT] Map the comprehensive scout into the canonical outputs instead of inventing a standalone technical-document file:
     - `PROJECT-HANDBOOK.md` -> project architecture overview summary, cross-cutting hotspots, and topic routing
     - `.specify/project-map/index/atlas-index.json` -> atlas entry summary, module count, and next lookup pointers
     - `.specify/project-map/index/modules.json` -> canonical module registry and module document paths
     - `.specify/project-map/index/relations.json` -> cross-module routing, shared surfaces, and dependency expansion paths
     - `.specify/project-map/root/*.md` -> repository-wide and cross-module topical truth
     - `.specify/project-map/modules/<module-id>/*.md` -> module-local truth, ownership, workflows, and testing
   - [AGENT] Root docs must carry cross-module truth; module docs must carry module-local truth. Do not push all technical detail back into the root layer.
   - [AGENT] For each high-value module, create at least `OVERVIEW.md`, `ARCHITECTURE.md`, `STRUCTURE.md`, `WORKFLOWS.md`, and `TESTING.md`.
   - [AGENT] When a module needs deeper detail, use controlled `deep/` categories: `capabilities/`, `workflows/`, `integrations/`, `runtime/`, and `references/`.
   - Every topical document should begin with a metadata block:
     ```markdown
     **Last Updated:** YYYY-MM-DD
     **Coverage Scope:** [what area this document covers]
     **Primary Evidence:** [main files, directories, commands, or tests used]
     **Update When:** [what changes should trigger edits here]
     ```
   - If local templates are absent, default to these section sets instead of free-form prose:
     - `ARCHITECTURE.md`: Pattern Overview, Layers, Core Abstractions, Main
       Flows, Truth Ownership and Boundaries, Cross-Cutting Concerns
     - `STRUCTURE.md`: Directory Layout, Directory Responsibilities, Key File
       Locations, Shared Coordination Files, Where To Add New Code
     - `CONVENTIONS.md`: Naming Patterns, Formatting and Linting, Imports and
       Exports, Error Handling, Comments and Docs, Testing Conventions
     - `INTEGRATIONS.md`: External Services and Tools, Environment
       Configuration, CI/CD and Release Surfaces, Runtime Dependencies,
       Integration Risks
     - `INTEGRATIONS.md` should also capture configuration and feature-control surfaces, compatibility rules, and security boundaries at usable depth
     - `WORKFLOWS.md`: Core User Flows, Core Maintainer Flows, Adjacent
       Workflow Risks, Entry Commands and Handoffs
     - `WORKFLOWS.md` should also capture runtime data and event flows plus key business and entity lifecycles
     - `TESTING.md`: Test Layers, Key Test Directories, Smallest Meaningful
       Checks, Regression-Sensitive Areas, When To Expand Verification
     - `TESTING.md` should also capture the test pyramid, quality gates, and change-impact verification matrix
     - `OPERATIONS.md`: Startup and Execution Paths, Runtime Constraints,
       Recovery and Resume, Troubleshooting Entry Points, Operator Notes
     - `OPERATIONS.md` should also capture deployment and runtime topology, observability design, and failure modes and recovery playbooks
   - `ARCHITECTURE.md` must explain layers, abstractions, truth ownership, main
     flows, change propagation paths, and cross-cutting concerns.
   - `STRUCTURE.md` must answer where code lives, what each major directory
     owns, what shared or consumer surfaces exist, and where new code should
     go.
   - `CONVENTIONS.md` must answer how code is written, named, imported, tested,
     and documented in this repository.
   - `INTEGRATIONS.md` must capture external tools, services, env/config, CI,
     runtime assumptions, contract boundaries, and integration risks.
   - `WORKFLOWS.md` must capture user flows, maintainer flows, failure or
     recovery paths, adjacent-flow risks, and entry/handoff surfaces.
   - `TESTING.md` must capture test layers, smallest meaningful checks,
     regression-sensitive areas, and verification entry points.
   - `OPERATIONS.md` must capture startup, recovery, troubleshooting, operator
     notes, and known runtime unknowns or stale evidence boundaries.
   - For each high-value workflow or capability in `TESTING.md`, record a
     runnable minimum verification path using repository-native commands or
     scripts when one exists. If none exists, explicitly mark
     `missing runnable verification`.
   - For each touched area discovered during scouting, ensure the combined
     handbook/project-map outputs give explicit ownership or placement guidance
     plus at least one of workflow, constraint, integration, or
     regression-sensitive testing guidance.
   - The topical documents must carry the deeper detail. `PROJECT-HANDBOOK.md`
     is the entrypoint, not the place to hide the only precise explanation.
   - For any high-value contract or implementation detail, record the responsibility, important inputs/outputs or fields, adjacent dependencies, compatibility constraints, and minimum verification route.
   - Do not stop at naming a file family or subsystem. Explain why the mapped
     surface matters and what a future change would need to preserve.
   - `ARCHITECTURE.md` should retain deeper component catalogs and technical
     boundaries for the subsystems that drive behavior or verification, not
     just a top-level layer summary.
   - `STRUCTURE.md` should retain deeper ownership notes for critical file
     families and key components instead of only listing folders.
   - `CONVENTIONS.md` should preserve project-specific contract conventions,
     state semantics, config propagation rules, and compatibility constraints,
     not just generic style notes.
   - `INTEGRATIONS.md` should preserve protocol seams, toolchain entrypoints,
     packaging paths, environment assumptions, and other integration invariants
     at usable depth.
   - `WORKFLOWS.md` should preserve the handoff detail that future work needs: method families, parameter semantics, return shapes, error fields, state transitions, compatibility notes, or invariants where those facts govern the flow.
   - `TESTING.md` and `OPERATIONS.md` should preserve the concrete validation,
     build, runtime, and troubleshooting detail needed to verify or recover the
     mapped surfaces without reverse-engineering the repository again.
   - Do not stop at repository shape. The refreshed map must make it hard to
     miss adjacent surfaces that would need review when the mapped area
     changes.
   - If the repository is too large to card every capability, prioritize the capabilities that are most central, most risky to change, shared by multiple workflows, or exposed at external boundaries.
   - When the repository exposes APIs or exported command/query surfaces, the
     refreshed map must inventory the major ones at usable depth instead of
     merely saying that such APIs exist.
   - When the repository has recognizable core classes, interfaces, abstract
     types, enums, or major functions, record the most important ones with
     their responsibilities, home modules, and why they matter.
   - When the repository contains key business or runtime flows, describe the
     entry-to-exit data path in enough detail that a maintainer could follow
     the handoffs without rediscovering them from scratch.

5. **Generate or refresh `PROJECT-HANDBOOK.md`**
   - [AGENT] Generate or refresh `PROJECT-HANDBOOK.md`.
   - `PROJECT-HANDBOOK.md` must stay concise and index-first so it remains the
     first-read navigation artifact.
   - Preserve the old single-entry-document strengths by making it easy to
     establish system shape quickly:
     - system summary
     - shared surfaces
     - risky coordination points
     - change-propagation hotspots
     - verification entry points
     - known unknowns or stale areas
     - topic map
     - update triggers
     - recent structural changes
   - Do not duplicate deep topical content there; route to the topical docs.
     The handbook should summarize and point, while the topical documents must
     carry the deeper detail.
   - Do not put code blocks, API inventories, or the only precise explanation in `PROJECT-HANDBOOK.md`.
   - Each subsystem or topic-map item in the handbook should stay to one short paragraph and end with an explicit route to the relevant topical file.

6. **Run a consistency pass**
   - [AGENT] Ensure `PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, and `.specify/project-map/modules/*/*.md` agree on paths, ownership, module IDs, and workflow names.
   - Remove duplicate truth blocks when a topic belongs in a topical document
     instead of the root handbook.
   - If touched-area coverage is still missing, stale, too broad, or
     task-relevant coverage is insufficient after the first draft, replace
     guesswork with targeted live-file reads and update the affected
     documents.

7. **Run the detail acceptance checklist before reporting completion**
   - Before reporting completion, confirm the detail acceptance checklist:
     - no critical topic document stops at directory names or file-family names without explaining responsibilities
     - high-value contracts keep concrete signatures, fields, return shapes, handoff data, or compatibility rules when those facts exist
     - workflow and integration sections preserve protocol seams, bridge semantics, or runtime invariants when those facts govern behavior
     - build, packaging, runtime, and recovery instructions remain actionable instead of being reduced to generic prose
     - the handbook stays index-first and points to the topic docs instead of duplicating them
     - high-value capabilities include owner, truth lives, extension guidance, change propagation, minimum verification, failure modes, and confidence
     - capability cards use the canonical confidence levels Verified, Inferred, or Unknown-Stale
     - the combined handbook/project-map output covers project type and stack,
       architecture shape, directory responsibilities, dependency
       relationships, core code elements, data flows, API surfaces, and
       patterns/conventions at usable depth
     - each major directory has at least one responsibility statement and one placement cue
     - each major API or command surface lists an entrypoint, owner, consumer, and verification route
     - each high-value workflow or capability records a runnable minimum verification path or the explicit marker `missing runnable verification`
   - If any checklist item fails, continue mapping before the completion
     report.

8. **Report completion**
   - [AGENT] Before reporting completion, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning through `specify learning capture --command map-codebase ...`.
   - [AGENT] Before reporting completion, run `specify hook review-learning --command map-codebase --terminal-status <resolved|blocked> --decision <captured|none|deferred> --rationale "<why>"` so atlas-refresh learning cannot be skipped.
   - [AGENT] After the refresh succeeds, finalize the refresh through the project-map freshness helper using `complete-refresh` so downstream workflows know the new baseline commit and refresh reason. Use `record-refresh` only for low-level/manual recovery when the standard completion path is unavailable.
   - Summarize which canonical map files were created or refreshed.
   - Call out the highest-signal risky coordination points or stale areas that
     were clarified.
   - Recommend the next workflow:
     - brownfield requirement work -> `/sp-specify`
     - design/task/implementation work that was blocked on navigation -> resume
       the invoking workflow now that the map is refreshed
