---
description: Use when `sp-map-scan` has produced a complete scan package and you need to build or refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/**`.
workflow_contract:
  when_to_use: A completed scan package exists and the canonical handbook/project-map atlas must be built or refreshed from it.
  primary_objective: Validate the scan package, dispatch read-only explorer packets, write the canonical atlas, and prove reverse coverage closure.
  primary_outputs: '`PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, `.specify/project-map/modules/<module-id>/*.md`, and `.specify/project-map/index/status.json`.'
  default_handoff: Return to the blocked workflow that required fresh navigation coverage.
---

{{spec-kit-include: ../command-partials/map-build/shell.md}}

`sp-map-build` begins with validation, not writing.

This workflow is the explicit brownfield atlas construction entrypoint. It must
consume a completed `sp-map-scan` package and write only the canonical
handbook/project-map outputs.

## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command map-build --format json` when available so passive learning files exist, the current atlas build sees relevant shared project memory, and repeated high-signal candidates can be auto-promoted at start.
- [AGENT] When atlas build friction appears, run `specify hook signal-learning --command map-build ...` with route-change, artifact-rewrite, false-start, hidden-dependency, scan-gap, or reverse-coverage-failure counts so atlas blind spots become explicit learning signals.
- [AGENT] Before reporting completion or a blocked build, run `specify hook review-learning --command map-build --terminal-status <resolved|blocked> ...`; use `--decision none --rationale "..."` only when no reusable `map_coverage_gap`, `workflow_gap`, `state_surface_gap`, or `project_constraint` exists.
- [AGENT] Prefer `specify learning capture-auto --command map-build --feature-dir "$FEATURE_DIR" --format json` when workflow state already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `specify hook capture-learning --command map-build ...` for structured atlas learnings when durable state does not capture the reusable lesson cleanly.

## Required Inputs

Before writing final atlas documents, read:

- `.specify/project-map/map-scan.md`
- `.specify/project-map/coverage-ledger.md`
- `.specify/project-map/coverage-ledger.json`
- `.specify/project-map/scan-packets/*.md`
- `PROJECT-HANDBOOK.md` if present
- `.specify/project-map/index/*.json` if present
- `.specify/project-map/root/*.md` if present
- `.specify/project-map/modules/**` if present

If any scan-package file is missing, `sp-map-build` must not guess and continue.
Produce a scan gap report and route back to `/sp-map-scan`.

## Process

1. Validate that the `sp-map-scan` package is present and complete.
2. Refuse atlas writing when readiness checks fail, and report the smallest safe `sp-map-scan` repair.
3. Select the execution strategy and dispatch read-only explorer lanes only when the scan packets justify it.
4. Write the canonical handbook/project-map atlas from accepted packet evidence.
5. Prove reverse coverage validation before reporting success.
6. Finalize freshness with `project-map complete-refresh` after a successful full refresh.

## Readiness Refusal Rules

`sp-map-build` must refuse atlas writing when the scan package has:

- packet results without paths read
- packet results that only summarize without evidence
- unresolved critical rows
- unresolved `unknown` rows without a concrete blocker
- critical rows without scan packets
- critical or important rows without atlas targets
- excluded buckets without a reason and revisit condition
- scan packets without required questions or expected evidence format

When refusal happens, write or report a scan gap report that names:

- failed readiness check
- affected ledger row IDs
- missing packet or atlas target
- smallest safe `sp-map-scan` repair

## Execution Strategy

- [AGENT] Before explorer packet dispatch begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_execution_strategy(command_name="map-build", snapshot, workload_shape)`.
- Strategy names are canonical and must be used exactly: `single-lane`, `native-multi-agent`, `sidecar-runtime`.
- Decision order is fixed:
  - If the work does not justify safe fan-out -> `single-lane` (`no-safe-batch`)
  - Else if `snapshot.native_multi_agent` -> `native-multi-agent` (`native-supported`)
  - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime` (`native-missing`)
  - Else -> `single-lane` (`fallback`)
- If collaboration is justified, dispatch read-only explorer subagents for the scan packets declared in `.specify/project-map/scan-packets/`.
- Required join points:
  - before writing final atlas documents
  - before reverse coverage validation
- The leader must wait for every dispatched explorer lane at the documented join point, integrate the returned evidence, and note any missing lane or fallback reason in the build summary.

## Explorer Packet Dispatch

Explorer subagents are read-only evidence collectors. They must not write
`PROJECT-HANDBOOK.md` or `.specify/project-map/**` artifacts directly.

Every explorer result must include:

- paths_read
- key_facts
- confidence
- unknowns
- minimum_verification
- recommended_atlas_updates

The leader must not accept packet results without paths read, packet results
that only summarize without evidence, or results that omit required unknowns.

## Output Contract

This atlas output contract is the only final write surface for
`sp-map-build`.

The only canonical outputs for this command are:

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
- `.specify/project-map/modules/<module-id>/deep/**` when packeted and needed

Do not create `.planning/codebase/`, a second mapping tree, or any alternate
source-of-truth document.

## Guardrails

## Root and Module Document Detail Rules

- `PROJECT-HANDBOOK.md` must stay concise and index-first.
- Root docs carry cross-module truth; module docs carry module-local truth.
- Do not push all technical detail back into the root layer.
- Do not stop at repository shape.
- Do not stop at naming a file family or subsystem.
- No critical topic document may stop at directory names or file-family names without explaining responsibilities.
- High-value contracts must preserve concrete signatures, fields, return shapes, handoff data, compatibility rules, or protocol semantics when those facts exist.
- Workflow and integration sections must preserve protocol seams, bridge semantics, runtime invariants, method families, parameter semantics, return shapes, error fields, state transitions, compatibility notes, or invariants where those facts govern behavior.
- Build, packaging, runtime, and recovery instructions must remain actionable instead of being reduced to generic prose.
- High-value capabilities must include owner, truth lives, extension guidance, change propagation, minimum verification, failure modes, and confidence.
- Confidence must use only: Verified, Inferred, or Unknown-Stale.
- Unknown-Stale and Inferred claims must be repeated in Known Unknowns, Low-Confidence Areas, or module `deep_stale`.

For each high-value capability, core module, or critical workflow, emit at
least one capability card. Capability cards must capture:

- Purpose
- Owner
- Truth lives
- Entry points
- Downstream consumers
- Extend here
- Do not extend here
- Key contracts
- Change propagation
- Minimum verification
- Failure modes
- Confidence

## Reverse Coverage Validation

Before reporting success, `sp-map-build` must prove reverse coverage validation:

- every `critical` row appears in at least one final atlas target
- every `important` row appears in a final atlas target or an explicitly named grouped surface
- every scan packet is consumed
- every accepted packet result has paths read and confidence
- every command/API/integration/runtime entrypoint has owner, consumer, change propagation, and verification
- every low-confidence area is visible in Known Unknowns, Low-Confidence Areas, or module `deep_stale`
- every excluded bucket has a reason and revisit condition
- `PROJECT-HANDBOOK.md` stays index-first and routes to deeper topical docs

If any check fails, continue mapping or route back to `/sp-map-scan`; do not
report success.

## First-Party Workflow Quality Hooks

- Before broad atlas build work begins, use `specify hook preflight --command map-build --feature-dir "$REPO_ROOT/specs"` only when the local workflow needs a machine-readable guard result for map refresh entry.
- Before compaction-risk transitions or after major atlas synthesis, use `specify hook checkpoint --command map-build --feature-dir "$REPO_ROOT/specs"` only if a workflow-state-backed wrapper has created the corresponding state artifact for this build run.
- After a successful full refresh, prefer `specify hook complete-refresh` as the shared product path that finalizes project-map freshness state.

## Report Completion

- [AGENT] Before reporting completion, capture any new `pitfall`, `workflow_gap`, `map_coverage_gap`, or `project_constraint` learning through `specify learning capture --command map-build ...`.
- [AGENT] Before reporting completion, run `specify hook review-learning --command map-build --terminal-status <resolved|blocked> --decision <captured|none|deferred> --rationale "<why>"`.
- [AGENT] After the refresh succeeds, finalize the refresh through the project-map freshness helper using `complete-refresh` so downstream workflows know the new baseline commit and refresh reason. Use `record-refresh` only for low-level/manual recovery when the standard completion path is unavailable.
- Summarize which canonical map files were created or refreshed.
- Summarize which scan packets were consumed.
- Call out the highest-signal risky coordination points or stale areas that were clarified.
- Recommend the blocked workflow that required fresh navigation coverage.
