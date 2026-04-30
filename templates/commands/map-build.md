---
description: Use when `sp-map-scan` has produced a complete scan package and you need to build or refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/**`.
workflow_contract:
  when_to_use: A completed scan package exists and the canonical handbook/project-map atlas must be built or refreshed from it.
  primary_objective: Validate the scan package, dispatch read-only explorer packets, write the canonical atlas, and prove reverse coverage closure.
  primary_outputs: '`PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, `.specify/project-map/modules/<module-id>/*.md`, `.specify/project-map/index/status.json`, `.specify/project-map/map-state.md`, and `.specify/project-map/worker-results/*.json`.'
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
- `.specify/project-map/map-state.md` if present
- `PROJECT-HANDBOOK.md` if present
- `.specify/project-map/index/*.json` if present
- `.specify/project-map/root/*.md` if present
- `.specify/project-map/modules/**` if present

If any scan-package file is missing, `sp-map-build` must not guess and continue.
Produce a scan gap report and route back to `/sp-map-scan`.

## Project Map State Protocol

- `MAP_STATE_FILE=.specify/project-map/map-state.md` is the resumable scan/build state surface for `sp-map-build`.
- [AGENT] Create or resume `MAP_STATE_FILE` before substantial atlas build work.
- Read `.specify/templates/project-map/map-state-template.md` when available.
- If `MAP_STATE_FILE` exists with `active_command: sp-map-build` and non-terminal build state, resume from it instead of rebuilding intent from chat memory.
- Track at least:
  - `active_command: sp-map-build`
  - `status: validating | executing-packets | synthesizing | reverse-validating | blocked | complete`
  - `scan_status`
  - `build_status: pending | executing | blocked | complete`
  - `focus`
  - `selected_modules`
  - `selected_topics`
  - `current_packet`
  - `accepted_packet_results`
  - `rejected_packet_results`
  - `failed_readiness_checks`
  - `failed_reverse_coverage_checks`
  - `next_action`
  - `next_command`
  - `handoff_reason`
  - `open_gaps`

## Process

1. Validate that the `sp-map-scan` package is present and complete.
2. Refuse atlas writing when readiness checks fail, and report the smallest safe `sp-map-scan` repair.
3. Select the execution strategy and dispatch read-only explorer lanes only when the scan packets justify it.
4. Execute every accepted scan packet against the live repository and build a packet evidence intake before writing atlas files.
5. Write the canonical handbook/project-map atlas from accepted packet evidence.
6. Prove reverse coverage validation before reporting success.
7. Finalize freshness with `project-map complete-refresh` after a successful full refresh.

## Non-Negotiable Build Semantics

`sp-map-build` is not a scaffold, migration, or file-moving command. Creating
directories, copying existing markdown into a new layout, creating JSON index
files, or updating path references is not a successful atlas build by itself.

Existing `PROJECT-HANDBOOK.md` and `.specify/project-map/**` documents are
inputs, not evidence. Existing claims may be retained only after they are
revalidated against live repository paths named by the scan package. If a claim
cannot be tied to a packet result with `paths_read` and confidence, rewrite it
as `Unknown-Stale`, move it to the appropriate unknowns section, or route back
to `/sp-map-scan`.

Before any final atlas write, the leader must produce a packet evidence intake
in `MAP_STATE_FILE` and, when file writes are available,
`.specify/project-map/worker-results/<packet-id>.json` with one row per scan
packet:

- packet ID
- owned ledger row IDs
- live `paths_read`
- key facts accepted into atlas targets
- atlas targets updated or explicitly confirmed current
- confidence (`Verified`, `Inferred`, or `Unknown-Stale`)
- remaining unknowns or blockers

A structural-only refresh is a failed build. If the build summary cannot name
the live paths read for each accepted packet and the atlas targets changed or
confirmed from those reads, report the build as blocked instead of successful.

## Validate Scan Inputs Before Execution

- [AGENT] Read `.specify/project-map/map-scan.md`, `.specify/project-map/coverage-ledger.md`, `.specify/project-map/coverage-ledger.json`, and every `.specify/project-map/scan-packets/*.md` file before selecting work.
- If none of those scan artifacts exist, stop and route to `/sp-map-scan`; do not rebuild the scan from chat memory inside `sp-map-build`.
- Treat `.specify/project-map/coverage-ledger.json` as the machine-readable row source when it exists. Use `coverage-ledger.md` and `map-scan.md` only as human-readable context when both exist.
- Refuse atlas writing unless `coverage-ledger.json` parses as JSON and its summary proves no unresolved `unknown` rows, critical rows without packets, or critical/important rows without atlas targets.
- Refuse atlas writing unless every referenced packet exists and exposes `lane_id`, `ledger_row_ids`, `required_reads`, `expected_outputs`, `atlas_targets`, and `result_handoff_path`.
- Record selected packets, skipped packets, readiness failures, and the current join point in `MAP_STATE_FILE`.

## Compile And Validate MapBuildPacket Inputs

- [AGENT] Compile a `MapBuildPacket` from each accepted scan packet before dispatch or leader-local execution.
- A valid `MapBuildPacket` must include:
  - `lane_id`
  - `mode: read_only`
  - `ledger_row_ids`
  - `scope`
  - `required_reads`
  - `required_questions`
  - `expected_outputs`
  - `atlas_targets`
  - `forbidden_actions`
  - `minimum_verification`
  - `result_handoff_path`
- Hard rule: do not dispatch from raw scan prose or raw Markdown checklist items alone.
- Hard rule: `MapBuildPacket` execution is read-only until the leader synthesizes accepted results into final atlas writes.
- Hard rule: a packet that cannot identify concrete repository paths or globs to read is not executable and must route back to `/sp-map-scan`.

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
In `single-lane` execution, the leader must perform the same packet reads
directly; skipping subagents does not skip packet execution.

Every explorer result must include:

- lane_id
- reported_status: done | done_with_concerns | blocked | needs_context
- paths_read
- key_facts
- recommended_atlas_updates
- confidence
- unknowns
- minimum_verification
- result_handoff_path

The leader must not accept packet results without paths read, packet results
that only summarize without evidence, or results that omit required unknowns.
The leader must compare accepted packet facts against the existing handbook and
project-map docs before deciding that a target can be left unchanged.
Idle subagent output is not an accepted result. The leader must record rejected
results in `MAP_STATE_FILE` with the reason and retry or rescan policy.

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
- `.specify/project-map/map-state.md`
- `.specify/project-map/worker-results/<packet-id>.json`

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
- every final atlas target is backed by at least one accepted packet evidence row or is explicitly marked unchanged after live revalidation
- no final report claims success for a structural-only refresh
- `MAP_STATE_FILE` records accepted packet results, rejected packet results, failed readiness checks, failed reverse coverage checks, and the next command
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
- Include the accepted and rejected packet result counts from `MAP_STATE_FILE`.
- Include the most recent reverse coverage validation evidence so later workflows can see what was actually checked.
- Call out the highest-signal risky coordination points or stale areas that were clarified.
- Recommend the blocked workflow that required fresh navigation coverage.
