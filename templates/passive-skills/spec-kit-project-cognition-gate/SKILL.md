---
name: spec-kit-project-cognition-gate
description: "Use when changing, reviewing, planning against, or debugging an existing Spec Kit Plus codebase. Require the agent-planned project cognition query bundle first, or route to map refresh when cognition coverage is missing or stale."
origin: spec-kit-plus
---

# Spec Kit Project Cognition Gate

This passive skill is the brownfield hard gate, not the route selection layer.

## Complementary Passive Skills

- `spec-kit-workflow-routing` owns route selection into the correct `sp-*` workflow
  before implementation, planning, or debugging proceeds.
- `spec-kit-project-learning` owns the shared memory capture layer after context is
  loaded. Once this gate is satisfied, follow that skill's learning-start and
  learning-capture expectations for the active workflow.

## Hard Gate

Before code edits, investigation, planning against existing code, or architectural
judgment in an established Spec Kit Plus repository:

- Use the launcher-backed project cognition query planning flow required by the
  active workflow contract to retrieve the task-local project cognition bundle.
  Run `project-cognition lexicon` first, inspect the returned
  `concept_candidates`, choose task-relevant `selected_concepts`, record
  non-selected or unsafe `rejected_concepts`, and include a
  `selection_reason`. Translate that bounded selection into a `query_plan`
  containing `selected_concepts`, `rejected_concepts`, `expanded_queries`, and
  `paths`, then run `project-cognition query --query-plan`.
  Treat raw graph JSON artifacts as obsolete runtime surfaces.
- Treat `concept_candidates` as structured project concept candidates, not a
  flat keyword list. Resolve broad, conflicting, or unknown candidates through
  the returned readiness state; do not widen live repository reads beyond the
  returned `route_pack` and `minimal_live_reads`.
- For `sp-discussion`, product framing may begin before the cognition gate. Before
  technical options, affected-surface claims, source-code reads, or
  source-grounded recommendations, use the active workflow's launcher-backed
  project cognition query planning flow to retrieve the task-local project
  cognition bundle.
- Project cognition is project-scoped. Current project cognition proves only
  current project facts.
- In `sp-discussion`, if the implementation target is another repository or
  external project, lock `target_project_root` before source-grounded technical
  claims.
- Reference project cognition is supplemental-only and cannot replace target
  evidence.
- If target root is unknown, block technical options and handoff readiness;
  continue only with product framing and explicit unknowns.
- If target root is known but target cognition is stale or missing, use target
  cognition, minimal live reads in the target, user confirmation, or explicit
  assumptions. Do not ask the user to rebuild current-project cognition for
  target files.
- Treat the project cognition runtime as the cross-project cognition reference:
  explicit-only, supplemental-only, fresh-only, and minimal read before broader
  live-code inspection.
- A project-cognition query is not complete when it returns JSON. It is complete
  only when readiness drives routing, `minimal_live_reads` constrains
  inspection, and relevant facts are carried into the next workflow artifact or
  execution state.
- Extract and carry forward `selected_concepts`, `rejected_concepts`,
  `selection_reason`, the matched capability or symptom, affected nodes and
  subgraph, `route_pack`, `minimal_live_reads`, missing coverage, evidence
  traces, verification routes, ambiguity, conflicts, and weak coverage.
- Treat project cognition under `.specify/project-cognition/` as the runtime truth surface. Legacy project-map exports are not the default runtime truth path.
- Read `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`
  when they exist.

## Cross-Project Reference Directories

- When inspecting or comparing another local directory, check whether that
  directory or its children contain `.specify/` first. A referenced directory may
  be a downstream Spec Kit project even when it is outside the current repo.
- Prefer `cognition discover --root <path> --format json` to enumerate nested
  `.specify/` candidates before broad live reads. Treat its `projects` entries as
  project-cognition candidates and its `specify_candidates` entries as the
  broader set of Spec Kit-shaped directories.
- Use another project's cognition only when
  `.specify/project-cognition/status.json` exists,
  `.specify/project-cognition/project-cognition.db` exists,
  `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is
  true.
- For ready references, read only the fresh project cognition artifacts needed
  for the comparison, then use the returned minimal read order before inspecting
  more source files.
- For blocked, stale, missing, or incomplete references, do not treat legacy
  `.specify/project-map/**` outputs as current truth. Fall back to minimal live
  reads, or ask the user to refresh that reference project with
  `{{invoke:map-scan}} -> {{invoke:map-build}}` or `{{invoke:map-update}}` as
  appropriate.

## Command Surface Discipline

- Treat the live `specify --help` output as the only authoritative CLI command surface.
- Before suggesting or running a `specify <subcommand>` invocation while satisfying this gate, verify that it exists in `specify --help` or `specify <subcommand> --help`.
- Do not invent, paraphrase, or "normalize" unsupported CLI names such as `specify create-feature`.
- Feature creation remains `{{invoke:specify}}` plus the generated create-feature script at `.specify/scripts/bash/create-new-feature.sh` or `.specify/scripts/powershell/create-new-feature.ps1`, not a separate branch-creation command.

## Freshness State Guidance

- If the project cognition runtime is missing, route through the canonical
  `sp-map-scan -> sp-map-build` workflow detour before continuing. When giving
  the user an explicit command to type, write
  `{{invoke:map-scan}} -> {{invoke:map-build}}`.
- If the project cognition runtime is stale for a localized touched area, route
  through `sp-map-update` first. When giving the user an explicit
  command to type, write `{{invoke:map-update}}`.
- If the freshness state is `support_drift`, stop and tell the user to resolve
  support-surface drift; do not reflexively route to `sp-map-update`.
- If the freshness state is `partial_refresh`, tell the user the refresh was
  recorded but readiness did not pass; follow the reported
  `recommended_next_action` instead of implying success.
- Preserve the distinction between the machine freshness field and public state
  guidance: `freshness` records factual state, while `recommended_next_action`
  tells the operator what to do next.
- Route through `{{invoke:map-scan}} -> {{invoke:map-build}}` only when the
  baseline is missing, unusable, schema-incompatible, explicitly being rebuilt,
  or invalidated by broad architecture replacement. Uncertain closure should be
  recorded by `sp-map-update` as partial/low-confidence facts, known unknowns,
  and `minimal_live_reads`.
- Treat that detour as a user-invoked workflow handoff. Do not silently switch into
  `sp-map-update`, `sp-map-scan`, or `sp-map-build` yourself from another workflow;
  stop and tell the user which map workflow to run.
- Do not rely on generic framework instinct, chat memory, or prior sessions when the
  project cognition runtime should be the source of truth.

## Senior Consequence Analysis Relationship

Project cognition is necessary but not sufficient. Use it first to identify ownership, consumers, state surfaces, verification routes, and coverage gaps. Then run the Senior Consequence Analysis Gate when lifecycle, running-state, destructive-operation, shared-state, downstream consumer, compatibility, or multiple-behavior semantics matter.

The gate output must name affected objects, state behavior, dependency impact, recovery and validation, and coverage gaps. Preserve the Affected Object Map, State-Behavior Matrix, Dependency Impact Table, Recovery And Validation Contract, and Coverage Gaps. If project cognition cannot decide product semantics, record the gap and route to the appropriate workflow instead of treating the graph as authoritative.

## Scope Guard

- This gate applies even if the user asks for a direct code change without mentioning
  Spec Kit workflows.
- Stand down only when the task is clearly greenfield and does not depend on any
  existing project structure, conventions, or runtime surface.
