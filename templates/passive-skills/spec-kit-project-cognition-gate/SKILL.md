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
  Run `project-cognition lexicon` first, translate the raw user request into a
  `query_plan` using returned map terms, then run `project-cognition query
  --query-plan`. Treat raw graph JSON artifacts as obsolete runtime surfaces.
- For `sp-discussion`, product framing may begin before the cognition gate. Before
  technical options, affected-surface claims, source-code reads, or
  source-grounded recommendations, use the active workflow's launcher-backed
  project cognition query planning flow to retrieve the task-local project
  cognition bundle.
- Treat the project cognition runtime as the cross-project cognition reference:
  explicit-only, supplemental-only, fresh-only, and minimal read before broader
  live-code inspection.
- Treat project cognition under `.specify/project-cognition/` as the runtime truth surface. Legacy project-map exports are not the default runtime truth path.
- Read `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`
  when they exist.

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
