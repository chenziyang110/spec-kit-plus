---
description: Use when handbook/project-map coverage is missing, stale, or insufficient and you need to generate the complete scan package required before atlas construction.
workflow_contract:
  when_to_use: A workflow needs reliable handbook/project-map coverage and the current navigation artifacts are missing, stale, or too weak for the touched area.
  primary_objective: Generate a complete project-relevant inventory, coverage ledger, and scan packet set for `sp-map-build`.
  primary_outputs: '`.specify/project-map/map-scan.md`, `.specify/project-map/coverage-ledger.md`, `.specify/project-map/coverage-ledger.json`, `.specify/project-map/scan-packets/*.md`, and `.specify/project-map/map-state.md`.'
  default_handoff: /sp-map-build after the scan package passes readiness checks.
---

{{spec-kit-include: ../command-partials/map-scan/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


This workflow is the explicit brownfield scan entrypoint. When another workflow
needs fresh navigation coverage, it should run `/sp-map-scan` first and then
`/sp-map-build`.

If `$ARGUMENTS` names a subsystem, workflow, or focus area, use it to bias
classification and packet priority, but still keep the scan package globally
coherent for all project-relevant surfaces.

## Guardrails

## Hard Boundary

- `sp-map-scan` must not write final atlas truth.
- `sp-map-scan` must not edit `PROJECT-HANDBOOK.md`, `.specify/project-map/QUICK-NAV.md`, `.specify/project-map/index/*.json`, `.specify/project-map/root/*.md`, or `.specify/project-map/modules/**`.
- `sp-map-scan` writes only the scan package:
  - `.specify/project-map/map-scan.md`
  - `.specify/project-map/coverage-ledger.md`
  - `.specify/project-map/coverage-ledger.json`
  - `.specify/project-map/scan-packets/<lane-id>.md`
  - `.specify/project-map/map-state.md`
- Scan packets are executable read instructions for `sp-map-build`, not final
  atlas evidence. `sp-map-scan` may identify what must be read and where the
  result should land, but `sp-map-build` must still execute the packet reads
  against the live repository before writing atlas truth.

## Project Map State Protocol

- `MAP_STATE_FILE=.specify/project-map/map-state.md` is the resumable scan/build state surface for `sp-map-scan` and `sp-map-build`.
- [AGENT] Create or resume `MAP_STATE_FILE` before substantial scan work.
- Read `.specify/templates/project-map/map-state-template.md` when available.
- If `MAP_STATE_FILE` exists with `active_command: sp-map-scan` and non-terminal scan state, resume from it instead of rebuilding intent from chat memory.
- Track at least:
  - `active_command: sp-map-scan`
  - `status: scanning | synthesizing | blocked | ready-for-build`
  - `scan_status: pending | scanning | blocked | complete`
  - `build_status`
  - `focus`
  - `selected_modules`
  - `selected_topics`
  - `current_packet`
  - `scan_artifacts`
  - `next_action`
  - `next_command`
  - `handoff_reason`
  - `open_gaps`

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command map-scan --format json}}` when available so passive learning files exist, the current scan sees relevant shared project memory, and repeated high-signal candidates can be auto-promoted at start.
- [AGENT] When scan friction appears, run `{{specify-subcmd:hook signal-learning --command map-scan ...}}` with route-change, false-start, hidden-dependency, uncategorized-row, or packet-rewrite counts so atlas blind spots become explicit learning signals.
- [AGENT] Before reporting completion or a blocked scan, use the `review-learning` helper surface; use `--decision none` only when no reusable `map_coverage_gap`, `workflow_gap`, `state_surface_gap`, or `project_constraint` exists.
  Command shape: `{{specify-subcmd:hook review-learning --command map-scan --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"}}`
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command map-scan --feature-dir "$FEATURE_DIR" --format json}}` when workflow state already preserves route reasons, false starts, hidden dependencies, or reusable constraints.
- [AGENT] When durable state does not capture the reusable lesson cleanly, use the manual `capture-learning` hook surface for structured scan learnings.
  Required options: `--command`, `--type`, `--summary`, `--evidence`

## Output Contract

The only canonical outputs for this command are:

- `.specify/project-map/map-scan.md`
- `.specify/project-map/coverage-ledger.md`
- `.specify/project-map/coverage-ledger.json`
- `.specify/project-map/scan-packets/<lane-id>.md`
- `.specify/project-map/map-state.md`

Do not create `.planning/codebase/`, a second mapping tree, or any alternate
source-of-truth document. The scan package is a task package for
`sp-map-build`; it is not the final atlas.

## Process

1. **Recover the mapping baseline**
   - Read `.specify/memory/constitution.md` if present.
   - [AGENT] Read `.specify/project-map/index/status.json` if present to recover the current map baseline, dirty state, previous refresh metadata, and module `deep_stale` warnings.
   - [AGENT] Read `.specify/project-map/index/atlas-index.json`, `.specify/project-map/index/modules.json`, and `.specify/project-map/index/relations.json` if present.
   - [AGENT] Read `.specify/project-map/QUICK-NAV.md` if present so the scan preserves the current Layer 1 routing contract.
   - [AGENT] Read `PROJECT-HANDBOOK.md` and existing `.specify/project-map/root/*.md` files if present.
   - If local project-map templates exist under `.specify/templates/project-map/`, read them so scan packets target the local atlas shape.

2. **Select the scan dispatch shape**
   - [AGENT] Before broad inventory begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="map-scan", snapshot, workload_shape)`.
   - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
   - Decision order is fixed:
     - One safe validated scan lane -> `one-subagent` on `native-subagents` when available.
     - Two or more safe read-only inventory lanes -> `parallel-subagents` on `native-subagents` when available.     - No safe lane, missing packet, or unavailable delegation -> `subagent-blocked` with a recorded reason.
   - Current-runtime native subagents are the default when safe read-only inventory lanes exist.
   - For `one-subagent`, dispatch one read-only scout once a validated `MapScanPacket` or equivalent scan contract exists. If the packet is incomplete, compile the missing packet fields before dispatch; if dispatch is unavailable, record `subagent-blocked` with the blocker and stop for escalation or recovery before broad inventory begins.
   - If collaboration is justified, keep `map-scan` lanes read-only and limited to inventory, classification, and packet drafting.
   - Recommended scan lanes:
     - source, architecture, and module boundaries
     - templates, generated surfaces, and workflow prompts
     - scripts, hooks, runtime state, and operations
     - integrations, adapters, and external runtime assumptions
     - tests, docs, packaging, release, and verification surfaces
   - Required join points:
     - before finalizing `coverage-ledger.json`
     - before writing `scan-packets/*.md`
   - The leader owns final ledger normalization and packet quality even when subagents help with inventory.
   - Raw inventory notes or raw chat summaries are not sufficient subagent inputs or outputs. Each dispatched lane needs a validated `MapScanPacket` and must return a structured handoff with inspected paths, coverage rows touched, findings, confidence, blockers, and recommended packet updates.
   - Idle subagent output is not an accepted scan result. The leader must wait for every dispatched scan lane and consume its structured handoff before finalizing the ledger, writing scan packets, or marking the scan complete.

3. **Perform full project-relevant inventory**
   - [AGENT] Enumerate the project-relevant repository tree, including nested directories.
   - Use file-list-driven evidence first:
     - `rg --files`
     - Git-tracked files
     - targeted directory listing where hidden project config or state surfaces may not appear in `rg --files`
   - Inventory must include:
     - source roots such as `src/`, package directories, and extension runtimes
     - tests, fixtures, contract tests, smoke tests, and testing utilities
     - templates, passive skills, command templates, worker prompts, and generated downstream surfaces
     - scripts, shell helpers, PowerShell helpers, and workflow helper tools
     - project configuration, lockfiles, lint/test config, devcontainer config, and CI workflow files
     - docs, README files, workflow docs, release docs, and upgrade docs
     - project state surfaces such as `.specify/`, `PROJECT-HANDBOOK.md`, and project-map templates
     - integration adapters, MCP/config/runtime installer surfaces, and supported agent adaptation layers
     - packaging, release, bundled asset, and distribution metadata surfaces
   - These buckets may be recorded without file-by-file deep reading:
     - `.git/`
     - `.venv/` and other virtual environments
     - `.pytest_cache/`, `.ruff_cache/`, and similar tool caches
     - `dist/`, `build/`, temporary output, generated logs, and smoke-test output
     - external dependency, vendor, or cache directories
   - Excluded buckets still appear in the coverage ledger with `excluded_from_deep_read: true`, reason, owner/category, and when-to-revisit condition.

4. **Run Coverage Classification**
   - Every project-relevant directory or file family must receive one category:
     - `source`
     - `test`
     - `template-generated-surface`
     - `script`
     - `config`
     - `documentation`
     - `runtime`
     - `integration`
     - `packaging-release`
     - `state-artifact`
     - `vendor-cache-build-output`
     - `unknown`
   - `unknown` is a scan failure unless the item is explicitly marked as blocked with a concrete next read needed.
   - `sp-map-build` must not accept a scan package that still contains unresolved `unknown` coverage rows.

5. **Assign reading depth**
   - Each ledger row must choose one reading depth:
     - `inventory`: existence, category, ownership, and revisit condition are enough
     - `sampled`: representative files were read to establish a pattern
     - `deep-read`: the lane must read the relevant files, entrypoints, or contracts closely before atlas writing
   - Critical and important surfaces cannot be left at `inventory` depth unless they are excluded buckets with a clear reason.

6. **Run Criticality Scoring**
   - Each row must be scored:
     - `critical`: required for architecture, workflow, API, integration, runtime, security, packaging, or verification correctness
     - `important`: meaningful for future maintainers, but not a central boundary
     - `low-risk`: can be bucketed or summarized, with a revisit condition
   - Critical rows require a scan packet, an atlas target, and a verification route.
   - Important rows require an atlas target or an explicit grouping under another surface.
   - Low-risk rows require owner/category and revisit condition.

7. **Generate scan packets**
   - [AGENT] Generate `scan-packets/<lane-id>.md` files that `sp-map-build` can execute directly.
   - Treat each scan packet as a `MapScanPacket` contract. The packet may be Markdown, but it must expose the required fields clearly enough for `sp-map-build` to compile a validated `MapBuildPacket`.
   - Each packet must include:
     - `lane_id`
     - `mode: read_only`
     - `scope`
     - `ledger_row_ids`
     - `required_reads`
     - `excluded_paths`
     - `required_questions`
     - `expected_outputs`
     - `atlas_targets`
     - `forbidden_actions`
     - `result_handoff_path`
     - `join_points`
     - `minimum_verification`
     - `blocked_conditions`
   - Record packet paths, selected strategy, join points, and build handoff readiness in `MAP_STATE_FILE`.

8. **Generate Layer 1 retrieval source material**
   - [AGENT] Record the raw source material that `sp-map-build` will need to synthesize a dictionary-style Layer 1 entry surface.
   - For every high-value issue cluster, capture at least:
     - task route candidates
     - symptom route candidates
     - shared-surface hotspot candidates
     - verification route candidates
     - propagation-risk route candidates
   - Each candidate must point back to concrete ledger rows or packet scopes instead of freeform prose.
   - If a critical or important surface cannot yet be reached from one of those retrieval dimensions, record it as a scan gap rather than assuming `sp-map-build` will invent the route.

## Required Scan Dimensions

The scan package must preserve these dimensions as required fields or packet
questions:

1. **Project shape and stack**
   - project type, technology stack, build tooling, deployment shape

2. **Architecture overview**
   - architecture pattern, layers, core abstractions, truth ownership, boundaries, cross-cutting concerns

3. **Directory ownership**
   - directory responsibilities, major subdirectories, write surfaces, shared coordination files, placement guidance

4. **Module dependency graph**
   - module relationships, import/require direction, strong coupling, risky cycles, shared surfaces

5. **Core code elements**
   - core classes, interfaces, abstract types, enums, major functions, utility modules, state/data models

6. **Entry and API surfaces**
   - CLI commands, routes, controllers, exported endpoints, method families, parameter semantics, return shapes, error contracts

7. **Data and state flows**
   - data lineage, runtime events, state lifecycle, state transitions, persistence/cache checkpoints, handoff fields

8. **User and maintainer workflows**
   - entry-to-exit flows, handoffs, adjacent workflow risks, operator flows, recovery paths

9. **Integrations and protocol boundaries**
   - external tools/services, integration adapters, IPC/bridge/native-host seams, message/pipe/protocol semantics, runtime assumptions

10. **Build, release, and runtime**
    - build pipeline, packaging, bundled assets, release workflow, startup paths, runtime topology, recovery instructions

11. **Testing and verification**
    - test layers, test directories, smallest meaningful checks, regression-sensitive areas, minimum verification commands

12. **Risk, security, observability, and evolution**
    - change propagation, security boundaries, permission model, observability, failure modes, decision history, known unknowns, low-confidence areas

13. **Template and generated-surface propagation**
    - source templates, generated command/skill surfaces, integration-specific transformations, downstream file paths, tests that lock the generated behavior

14. **Coverage reverse index**
    - every critical or important surface must name the final atlas document where it will be explained

15. **Layer 1 retrieval inputs**
    - task routes, symptom routes, shared-surface hotspots, verification routes, and propagation-risk routes must all be derivable from scan outputs without ad hoc atlas writing

## `map-scan.md` Structure

`map-scan.md` must include:

1. Run metadata
2. Repository scope and exclusions
3. Scan strategy and subagent use
4. Coverage summary
5. Module and topic candidates
6. Critical surfaces
7. Scan packet index
8. Join points
9. Build readiness checklist
10. Known scan gaps
11. Handoff to `sp-map-build`
12. Layer 1 retrieval candidates

## `coverage-ledger.json` Shape

The JSON contract should stay simple enough for tests and hooks:

```json
{
  "version": 1,
  "generated_by": "sp-map-scan",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "repo_root": ".",
  "focus": "",
  "rows": [
    {
      "id": "SURF-001",
      "path_glob": "templates/commands/*.md",
      "category": "template-generated-surface",
      "owner": "workflow templates",
      "module_id": "specify-cli-core",
      "criticality": "critical",
      "reading_depth": "deep-read",
      "scan_packet": "SCAN-templates-workflows",
      "atlas_targets": [
        ".specify/project-map/root/WORKFLOWS.md",
        ".specify/project-map/modules/specify-cli-core/WORKFLOWS.md"
      ],
      "verification": "pytest tests/test_*template* -q",
      "excluded_from_deep_read": false,
      "exclusion_reason": "",
      "when_to_revisit": "workflow template behavior changes",
      "status": "ready"
    }
  ],
  "blockers": [],
  "summary": {
    "unknown_rows": 0,
    "critical_rows_without_packet": 0,
    "rows_without_atlas_target": 0
  }
}
```

## Scan Packet Template

Each `scan-packets/<lane-id>.md` must use this structure:

````markdown
# SCAN-<id>: <title>

## MapScanPacket

```json
{
  "lane_id": "SCAN-<id>",
  "mode": "read_only",
  "scope": ["<path or subsystem>"],
  "ledger_row_ids": ["SURF-001"],
  "required_reads": ["<path or glob>"],
  "excluded_paths": ["<path or glob> - reason - when to revisit"],
  "required_questions": ["What owns this surface?"],
  "expected_outputs": [
    "paths_read",
    "key_facts",
    "confidence",
    "unknowns",
    "minimum_verification",
    "recommended_atlas_updates"
  ],
  "atlas_targets": [".specify/project-map/root/ARCHITECTURE.md"],
  "forbidden_actions": ["edit files", "install dependencies", "rewrite atlas docs"],
  "result_handoff_path": ".specify/project-map/worker-results/SCAN-<id>.json"
}
```

## Scope

- Ledger rows:
- Paths:
- Project area:

## Required Reads

- <path or glob> - reason

## Excluded Paths

- <path or glob> - reason - when to revisit

## Required Questions

- What owns this surface?
- Where does the truth live?
- What entrypoints, contracts, state fields, or handoffs matter?
- What consumes or feeds this surface?
- How does change propagate?
- What should future work extend here?
- What should future work avoid extending here?
- What minimum verification proves this surface still works?
- What unknowns or low-confidence claims remain?

## Expected Evidence

- paths_read:
- key_facts:
- confidence:
- unknowns:
- minimum_verification:
- recommended_atlas_updates:
- result_handoff_path:

## Atlas Targets

- <PROJECT-HANDBOOK.md or .specify/project-map path>

## Join Points

- <join point and pass condition>

## Blocked Conditions

- <condition that must route back to sp-map-scan>
````

## Build Readiness Checklist

The scan is not complete until all checks pass:

- every project-relevant row is categorized
- no row remains `unknown` without a blocker
- every critical row has a scan packet
- every critical or important row has an atlas target
- every scan packet has required questions and expected evidence format
- every excluded bucket has a reason and revisit condition
- every scan packet can be executed by a read-only explorer without relying on unstated context

If any checklist item fails, continue scanning before handing off.

## Report Completion

- [AGENT] Before reporting completion, capture any new `pitfall`, `workflow_gap`, `map_coverage_gap`, or `project_constraint` learning through `{{specify-subcmd:learning capture --command map-scan ...}}`.
- [AGENT] Before reporting completion, use the `review-learning` helper surface.
  Command shape: `{{specify-subcmd:hook review-learning --command map-scan --terminal-status <resolved|blocked> --decision <captured|none|deferred> --rationale "<why>"}}`
- Summarize the scan-package outputs created or refreshed.
- State whether `sp-map-build` is ready to begin.
- Recommend `/sp-map-build` only when the build readiness checklist is green.
