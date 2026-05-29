---
name: spec-kit-project-cognition-gate
description: "Use when changing, reviewing, planning against, or debugging an existing Spec Kit Plus codebase. Consult the agent-planned project cognition query bundle as advisory navigation, then prove technical claims from live evidence."
origin: spec-kit-plus
---

# Spec Kit Project Cognition Gate

This passive skill is the brownfield advisory navigation layer, not a hard workflow gate.

## Complementary Passive Skills

- `spec-kit-workflow-routing` owns route selection into the correct `sp-*` workflow
  before implementation, planning, or debugging proceeds.
- `spec-kit-project-learning` owns the shared memory capture layer after context is
  loaded. Once this gate is satisfied, follow that skill's learning-start and
  learning-capture expectations for the active workflow.

## Advisory Navigation

Before code edits, investigation, planning against existing code, or architectural
judgment in an established Spec Kit Plus repository:

- Use the direct `project-cognition` query planning flow required by the active
  workflow contract to retrieve the task-local project cognition bundle. Run
  `project-cognition lexicon` first to get graph-backed project concept candidates
  from the active project cognition graph. The user request ranks and filters
  existing project concepts; it does not create project concepts. Choose
  task-relevant `selected_concepts`, record considered but unsafe or irrelevant
  `rejected_concepts`, write per-concept `concept_decisions`, carry
  `lexicon_generation_id` in the `query_plan`, and then run
  `project-cognition query --query-plan`.
  Treat raw graph JSON artifacts as obsolete runtime surfaces.
- Treat `concept_candidates` as structured project concept candidates, not a
  flat keyword list. Resolve broad, conflicting, or unknown candidates through
  the returned readiness state; do not widen live repository reads beyond the
  returned `route_pack` and `minimal_live_reads`.
- For `sp-discussion`, product framing may begin before the cognition gate. Before
  technical options, affected-surface claims, source-code reads, or
  source-grounded recommendations, use the active workflow's launcher-backed project cognition query planning flow to retrieve the task-local project
  cognition bundle. Use `project-cognition lexicon --intent discussion` and
  `project-cognition query --intent discussion` for discussion grounding. Do not
  use `--intent plan` from `sp-discussion`.
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
- Treat project cognition as advisory navigation and coverage metadata. Use it
  to choose minimal live reads, ownership hints, consumers, state surfaces,
  verification routes, and coverage gaps. Do not treat it as authoritative
  evidence for current behavior; prove project facts from live repository files.
- A project-cognition query is not complete when it returns JSON. It is complete
  only when readiness is interpreted as advisory navigation, `minimal_live_reads`
  constrains inspection, live evidence proves technical claims, and relevant
  facts are carried into the next workflow artifact or execution state.
- Extract and carry forward `selected_concepts`, `rejected_concepts`,
  `selection_reason`, `concept_decisions`, `lexicon_generation_id`, the matched
  capability or symptom, affected nodes and subgraph, `route_pack`,
  `minimal_live_reads`, missing coverage, evidence traces, verification routes,
  ambiguity, conflicts, and weak coverage.
- Treat project cognition under `.specify/project-cognition/` as an advisory navigation surface. Legacy project-map exports are not evidence for current project behavior and `templates/project-map/**` is historical compatibility/export only.
- Read `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`
  when they exist.

## Cross-Project Reference Directories

- When inspecting or comparing another local directory, check whether that
  directory or its children contain `.specify/` first. A referenced directory may
  be a downstream Spec Kit project even when it is outside the current repo.
- Prefer `project-cognition discover --root <path> --format json` to enumerate nested
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
  more source files. Treat the reference map as supplemental navigation, not as
  evidence by itself.
- For blocked, stale, or incomplete references, do not treat legacy
  `.specify/project-map/**` outputs as current truth. Fall back to minimal live
  reads and recommend `{{invoke:map-update}}` for localized stale coverage, weak
  reference coverage, external/manual changed-path map maintenance, or ordinary
  existing-baseline gaps after a usable reference baseline.
- For brownfield missing or unusable reference baselines, recommend
  `{{invoke:map-scan}} -> {{invoke:map-build}}`. Recommend scan/build for a
  reference project only for brownfield first/missing/unusable baseline, schema
  failure, zero active-generation `path_index` rows outside `greenfield_empty`,
  `explicit_rebuild_requested`, or `baseline_identity_invalid`.

## Command Surface Discipline

- Treat the live `specify --help` output as the only authoritative CLI command surface.
- Before suggesting or running a `specify <subcommand>` invocation while satisfying this gate, verify that it exists in `specify --help` or `specify <subcommand> --help`.
- Do not invent, paraphrase, or "normalize" unsupported CLI names such as `specify create-feature`.
- Feature creation remains `{{invoke:specify}}` plus the generated create-feature script at `.specify/scripts/bash/create-new-feature.sh` or `.specify/scripts/powershell/create-new-feature.ps1`, not a separate branch-creation command.

## Freshness State Guidance

- If the project cognition runtime is missing for a brownfield project, continue with live repository
  evidence and recommend the canonical `sp-map-scan -> sp-map-build` workflow only as
  external baseline maintenance. When giving the user an explicit command to type, write
  `{{invoke:map-scan}} -> {{invoke:map-build}}`.
- If `baseline_kind=greenfield_empty`, continue with workflow artifacts and live
  requirements. Do not recommend map-scan -> map-build solely because the graph
  has no paths.
- If the project cognition runtime is stale for a localized touched area, continue
  with live repository evidence and recommend `sp-map-update` first when map
  maintenance is useful. When giving the user an explicit
  command to type, write `{{invoke:map-update}}`.
- If changed paths are missing from project cognition `path_index`, let
  `sp-map-update` classify the gap first. Adoptable paths get provisional
  coverage, uncertain paths return `minimal_live_reads`, and ordinary
  existing-baseline gaps stay in `{{invoke:map-update}}`.
- Treat repository boundary accounting as separate from graph evidence. `.cognitionignore` exclusions and automatic exclusions explain why a path is outside graph-facing coverage; they do not become project cognition evidence.
- For `map-update`, changed-path accounting must explain every candidate path before readiness can be considered useful.
- If the freshness state is `support_drift`, stop and tell the user to resolve
  support-surface drift; do not reflexively route to `sp-map-update`.
- If the freshness state is `partial_refresh`, tell the user the refresh was
  recorded but readiness did not pass; follow the reported
  `recommended_next_action` instead of implying success.
- If project cognition readiness is `blocked`, report the runtime issue as
  degraded advisory map state. Ordinary discussion may continue with product
  framing or bounded live evidence; recommend a map maintenance workflow only
  when the user asks for map maintenance or handoff needs evidence that live
  reads cannot provide.
- Preserve the distinction between the machine freshness field and public state
  guidance: `freshness` records factual state, while `recommended_next_action`
  tells the operator what to do next.
- Use `map-update` for ordinary existing-baseline gaps. Use `map-scan -> map-build`
  only for brownfield first/missing/unusable baseline, schema failure, zero active-generation
  path_index rows outside `greenfield_empty`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
  Uncertain closure can be recorded by `sp-map-update` as partial/low-confidence
  facts, known unknowns, and `minimal_live_reads`.
- Entry-time stale or weak cognition is still an advisory navigation concern unless the user explicitly requested map maintenance. A workflow may continue from live evidence when entry guidance allows it. That entry routing rule does not waive closeout ownership.
- Workflow-owned mutation closeout is not an external map-maintenance handoff. If the active workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, or behavior-bearing docs, closeout must run inline project cognition update from the workflow-owned ledger.
- Inline update uses the current lower-level runtime path: append closeout evidence with `project-cognition delta append` when a delta session exists, then run `project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json`; without a delta session, run `project-cognition update --changed-path "<path>" --scope "<affected-scope>" --reason workflow-finalize --format json`.
- A persisted update_id with non-ready readiness is `review` or `partial_refresh`, not `dirty`. Use `project-cognition mark-dirty --reason "<reason>" --format json` only when inline update is unavailable, fails before recording useful update data, cannot safely identify workflow-owned scope, is blocked by runtime state, or verification/workflow completion is not trustworthy. Dirty only when inline update cannot complete.
- `sp-map-update` is for manual/external maintenance and follow-up repair after user edits, interrupted workflows, or explicit operator map-maintenance requests. It is external map maintenance, not routine cleanup for changes this workflow just made. In shared routing summaries, sp-map-update is for manual/external maintenance.
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
