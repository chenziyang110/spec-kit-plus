---
description: Analyze the current codebase and generate or refresh the handbook navigation system.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Objective

Generate or refresh the canonical handbook/project-map navigation system for
the current codebase.

This workflow is the explicit brownfield mapping entrypoint. When another
workflow needs fresh navigation coverage, it should run `/sp-map-codebase`
before continuing.

If `$ARGUMENTS` names a subsystem, workflow, or focus area, use it to bias the
scout and refresh emphasis, but still keep all canonical map outputs globally
coherent.

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

Rules:

- Refresh the handbook/project-map navigation system when these files already
  exist; do not default to skipping.
- Keep still-correct, high-signal content; rewrite stale, duplicated, vague,
  or low-value content.
- The refreshed map must make task-relevant coverage sufficient for any touched
  area it claims to cover.
- Task-relevant coverage is insufficient when the touched area is named only
  vaguely, lacks ownership or placement guidance, or lacks workflow,
  constraint, integration, or regression-sensitive testing guidance.
- Each touched area must include workflow, constraint, integration, or regression-sensitive testing guidance somewhere in the combined handbook/project-map output.
- If legacy `项目技术文档.md` exists, mine it only for still-useful structure,
  terminology, ownership hints, and risk framing, then migrate that value into
  the canonical outputs above.
- Legacy `项目技术文档.md` is not a source of truth and must not be recreated as
  an active technical reference.
- do not create `.planning/codebase/`, a second mapping tree, or any alternate
  source-of-truth document.

## Outline

1. **Load the mapping contract**
   - Read `.specify/memory/constitution.md` if present.
   - Read `PROJECT-HANDBOOK.md` and all existing `.specify/project-map/*.md`
     files if present.
   - Read `.specify/templates/project-handbook-template.md` and
     `.specify/templates/project-map/*.md` if present so the generated output
     follows the local navigation contract.
   - If the local template copies are missing, derive the contract from the
     existing handbook/project-map section structure and current repository
     conventions.

2. **Select the execution strategy**
   - Before broad scouting begins, assess workload shape and the current agent
     capability snapshot, then apply the shared policy contract:
     `choose_execution_strategy(command_name="map-codebase", snapshot, workload_shape)`.
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
   - Read only the live files needed to establish current facts for:
     - system shape and entrypoints
     - directory ownership and write surfaces
     - conventions and testing patterns
     - external integrations and runtime assumptions
     - user and maintainer workflows
     - operational caveats, recovery paths, and risky coordination points
   - Always capture actual file paths when naming code, config, scripts, or
     tests.
   - Distinguish current repository facts from recommendations. The map should
     describe what is true now, not what might be nice later.

4. **Generate or refresh the topical map**
   - `ARCHITECTURE.md` must explain layers, abstractions, truth ownership, main
     flows, and cross-cutting concerns.
   - `STRUCTURE.md` must answer where code lives, what each major directory
     owns, and where new code should go.
   - `CONVENTIONS.md` must answer how code is written, named, imported, tested,
     and documented in this repository.
   - `INTEGRATIONS.md` must capture external tools, services, env/config, CI,
     and runtime assumptions.
   - `WORKFLOWS.md` must capture user flows, maintainer flows, adjacent-flow
     risks, and entry/handoff surfaces.
   - `TESTING.md` must capture test layers, smallest meaningful checks, and
     regression-sensitive areas.
   - `OPERATIONS.md` must capture startup, recovery, troubleshooting, and
     operator notes.
   - For each touched area discovered during scouting, ensure the combined
     handbook/project-map outputs give explicit ownership or placement guidance
     plus at least one of workflow, constraint, integration, or
     regression-sensitive testing guidance.

5. **Generate or refresh `PROJECT-HANDBOOK.md`**
   - Keep it concise enough to be the first-read navigation artifact.
   - Preserve the old single-entry-document strengths by making it easy to
     establish system shape quickly:
     - system summary
     - shared surfaces
     - risky coordination points
     - topic map
     - update triggers
     - recent structural changes
   - Do not duplicate deep topical content there; route to the topical docs.

6. **Run a consistency pass**
   - Ensure `PROJECT-HANDBOOK.md` and `.specify/project-map/*.md` agree on
     paths, ownership, and workflow names.
   - Remove duplicate truth blocks when a topic belongs in a topical document
     instead of the root handbook.
   - If touched-area coverage is still missing, stale, too broad, or
     task-relevant coverage is insufficient after the first draft, replace
     guesswork with targeted live-file reads and update the affected
     documents.

7. **Report completion**
   - Summarize which canonical map files were created or refreshed.
   - Call out the highest-signal risky coordination points or stale areas that
     were clarified.
   - Recommend the next workflow:
     - brownfield requirement work -> `/sp-specify`
     - design/task/implementation work that was blocked on navigation -> resume
       the invoking workflow now that the map is refreshed
