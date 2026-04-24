---
description: Analyze the current codebase and generate or refresh the handbook navigation system.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Objective

**⚠️ CRITICAL: [AGENT] markers denote MANDATORY execution**
All actions marked with **[AGENT]** are hard-coded procedural guardrails. The AI agent **MUST** explicitly execute these actions and is strictly forbidden from skipping them or simulating them in memory.

Generate or refresh the canonical handbook/project-map navigation system for
the current codebase.

This workflow is the explicit brownfield mapping entrypoint. When another
workflow needs fresh navigation coverage, it should run `/sp-map-codebase`
before continuing.

If `$ARGUMENTS` names a subsystem, workflow, or focus area, use it to bias the
scout and refresh emphasis, but still keep all canonical map outputs globally
coherent.

Treat this workflow as the repository's comprehensive technical-documentation
generator. The resulting handbook/project-map system must serve as a durable
technical asset for onboarding, architecture review, technical-debt assessment,
and refactor planning. Analyze both macro architecture and micro
implementation-level details; do not stop at repository shape or shallow
navigation summaries.

## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command map-codebase --format json` when available so passive learning files exist, the current mapping run sees relevant shared project memory, and repeated non-high-signal candidates can be auto-promoted into shared learnings at start.

## Output Contract

The only canonical outputs are:

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/ARCHITECTURE.md`
- `.specify/project-map/STRUCTURE.md`
- `.specify/project-map/CONVENTIONS.md`
- `.specify/project-map/INTEGRATIONS.md`
- `.specify/project-map/WORKFLOWS.md`
- `.specify/project-map/TESTING.md`
- `.specify/project-map/OPERATIONS.md`

Supporting metadata written alongside the canonical map:

- `.specify/project-map/status.json`

Rules:

- Refresh the handbook/project-map navigation system when these files already
  exist; do not default to skipping.
- Keep still-correct, high-signal content; rewrite stale, duplicated, vague,
  or low-value content.
- The refreshed map must make task-relevant coverage sufficient for any touched
  area it claims to cover.
- Layering exists so map consumers can read detail on demand instead of re-reading one monolithic technical document.
- Do not treat layering as permission to discard technical detail.
- The topical map must preserve the level of detail needed to replace a legacy project technical document while still splitting that detail across the canonical topical files.
- Task-relevant coverage is insufficient when the touched area is named only
  vaguely, lacks ownership or placement guidance, or lacks workflow,
  constraint, integration, or regression-sensitive testing guidance.
- Treat the map as a coverage system, not just a navigation summary.
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
- Each touched area must include workflow, constraint, integration, or regression-sensitive testing guidance somewhere in the combined handbook/project-map output.
- For each high-value capability, core module, or critical workflow, emit at least one capability card.
- Capability cards must capture: Purpose, Owner, Truth lives, Entry points, Downstream consumers, Extend here, Do not extend here, Key contracts, Change propagation, Minimum verification, Failure modes, and Confidence.
- Confidence must use only: Verified, Inferred, or Unknown-Stale.
- When a capability card is marked Inferred or Unknown-Stale, summarize that gap again in Known Unknowns, Low-Confidence Areas, or both.
- If legacy `项目技术文档.md` exists, mine it only for still-useful structure, terminology, ownership hints, and risk framing, then migrate that value into the canonical outputs above.
- Legacy `项目技术文档.md` is not a source of truth and must not be recreated as an active technical reference.
- When the repository already contains older technical writeups, treat them as
  optional supporting evidence only. Reuse still-correct terminology,
  structure, ownership hints, and risk framing, but keep the canonical output
  in `PROJECT-HANDBOOK.md` plus `.specify/project-map/*.md`.
- do not create `.planning/codebase/`, a second mapping tree, or any alternate
  source-of-truth document.

## Outline

1. **Load the mapping contract**
   - Read `.specify/memory/constitution.md` if present.
   - [AGENT] Read `.specify/project-map/status.json` if present to recover the current map baseline, dirty state, and previous refresh metadata.
   - [AGENT] Read `PROJECT-HANDBOOK.md` and all existing `.specify/project-map/*.md` files if present.
   - Read `.specify/templates/project-handbook-template.md` and
     `.specify/templates/project-map/*.md` if present so the generated output
     follows the local navigation contract.
   - If the local template copies are missing, derive the contract from the
     existing handbook/project-map section structure and current repository
     conventions.

2. **Select the execution strategy**
   - [AGENT] Before broad scouting begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_execution_strategy(command_name="map-codebase", snapshot, workload_shape)`.
   - Strategy names are canonical and must be used exactly:
     `single-agent`, `native-multi-agent`, `sidecar-runtime`.
   - Decision order is fixed:
     - If the work does not justify safe fan-out -> `single-agent`
       (`no-safe-batch`)
     - Else if `snapshot.native_multi_agent` -> `native-multi-agent`
       (`native-supported`)
     - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime`
       (`native-missing`)
     - Else -> `single-agent` (`fallback`)
   - If collaboration is justified, keep `map-codebase` lanes limited to:
     - architecture and structure mapping
     - conventions and testing mapping
     - integrations and runtime mapping
     - workflows, operations, and risky coordination mapping
   - Required join points:
     - before writing `PROJECT-HANDBOOK.md`
     - before the final consistency pass across all map documents
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
     - `PROJECT-HANDBOOK.md` -> project architecture overview summary,
       cross-cutting hotspots, and topic routing
     - `ARCHITECTURE.md` -> top-level architecture pattern, major module
       dependency relationships, truth ownership, and critical component seams
     - `STRUCTURE.md` -> directory structure and responsibilities, including
       major directories and representative subdirectories
     - `CONVENTIONS.md` -> common patterns and conventions, naming rules,
       configuration customs, and utility locations
     - `INTEGRATIONS.md` -> APIs, external surfaces, protocol seams, platform
       assumptions, and integration boundaries
     - `WORKFLOWS.md` -> core data flows, request/command lifecycles, and
       entry-to-exit handoffs
     - `TESTING.md` -> verification routes that prove the mapped contracts and
       workflows
     - `OPERATIONS.md` -> build/deploy/runtime constraints, troubleshooting,
       and recovery paths
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

6. **Run a consistency pass**
   - [AGENT] Ensure `PROJECT-HANDBOOK.md` and `.specify/project-map/*.md` agree on paths, ownership, and workflow names.
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
   - If any checklist item fails, continue mapping before the completion
     report.

8. **Report completion**
   - [AGENT] Before reporting completion, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning through `specify learning capture --command map-codebase ...`.
   - [AGENT] After the refresh succeeds, finalize the refresh through the project-map freshness helper using `complete-refresh` so downstream workflows know the new baseline commit and refresh reason. Use `record-refresh` only for low-level/manual recovery when the standard completion path is unavailable.
   - Summarize which canonical map files were created or refreshed.
   - Call out the highest-signal risky coordination points or stale areas that
     were clarified.
   - Recommend the next workflow:
     - brownfield requirement work -> `/sp-specify`
     - design/task/implementation work that was blocked on navigation -> resume
       the invoking workflow now that the map is refreshed
