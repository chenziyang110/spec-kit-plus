# Project Handbook

**Last Updated:** 2026-05-02
**Purpose:** Root navigation artifact for this repository.

## System Summary

`spec-kit-plus` is a Python-first CLI and asset-packaging repository for practical Spec-Driven Development workflows across local AI coding agents. The primary product surface is the `specify` command implemented in `src/specify_cli/__init__.py`; it initializes projects, installs agent-specific workflow files, manages project cognition freshness and compatibility exports, exposes testing/learning/hook/eval helper surfaces, and provides the Codex-only `sp-teams` runtime path.

The repository has three mapped runtime modules:

- `specify-cli-core`: Python CLI, integration registry, project cognition freshness and compatibility-export helpers, learning/testing/eval helpers, execution packet/result contracts, hooks, orchestration policy, and Codex team Python control plane.
- `templates-generated-surfaces`: workflow command templates, command partials, passive skills, project-map compatibility/export templates, scripts, and worker prompts that are copied or transformed into downstream projects.
- `agent-teams-engine`: bundled optional Node/TypeScript plus Rust runtime assets for Codex team coordination.

## System Boundaries

This repository owns the `specify` CLI, bundled templates/scripts, supported-agent integration adapters, project-map compatibility/export templates, extension/preset managers, and optional Codex team runtime packaging. It coordinates with external agent CLIs, Git, uv/pip packaging, Node/npm, Cargo/Rust, optional MCP dependencies, tmux/psmux, and GitHub Actions. It does not own upstream agent CLI behavior, external MCP server implementations, terminal multiplexers, or the user's global `specify` installation.

## High-Value Capabilities

- **Project initialization and generated agent surfaces**: `specify init` resolves `--ai` or `--integration`, installs command/skill/workflow files, copies scripts/templates, and records integration manifests. Read `src/specify_cli/__init__.py`, `src/specify_cli/integrations/**`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Generated-project repair and compatibility diagnostics**: `specify check` now surfaces broken project launchers and stale generated runtime assets, and `specify integration repair` refreshes shared/runtime-managed generated assets in place without overwriting user-edited workflow content. Read `src/specify_cli/__init__.py`, `src/specify_cli/integrations/base.py`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Passive project learning memory**: generated projects use `.specify/memory/learnings/INDEX.md` as the thin first-read learning layer and may link each reusable lesson to one detail markdown document under `.specify/memory/learnings/`. `project-learnings.md` remains a compatibility summary; new captures write index/detail memory first, and workflow closeout applies the Learning Reflex before reusable lessons are left only in chat or workflow state.
- **Workflow contract generation**: `templates/commands/`, `templates/command-partials/`, and `templates/passive-skills/` define `sp-*` behavior for downstream agents. `sp-specify` is now a collaborative reviewed specification flow with an internal brainstorming kernel that locks brainstorming truth artifacts (`facts`, `route`, `intent`, `complexity`), asks one question at a time, decomposes semantic terms, compares approaches, writes and self-reviews artifacts, asks for user review, and then compiles the familiar spec package before routing to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`. Discussion-originated specs must read discussion source files and record capability-like upstream signals in `source_signal_disposition` instead of trusting only the handoff summary. `sp-plan` and `sp-tasks` now use adaptive execution: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, and `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`. Light mode runs leader-inline for low-risk single-lane artifact work. Standard mode uses native-subagent dispatch when available, degrades leader-inline with `capability_degraded: true` only when native subagents are unavailable and no high-risk trigger is present, and blocks as `subagent-blocked` when there is no safe lane or the work cannot be packetized safely. Heavy or safety-critical work blocks when native subagents are unavailable or the work is unpacketizable. Managed-team fallback is not part of adaptive plan/tasks dispatch. Structured planning and task-generation handoffs remain required when delegated lanes are used. Read `templates/commands/**`, `templates/command-partials/**`, and `modules/templates-generated-surfaces/WORKFLOWS.md`.
- **User-confirmed product scope**: Generated workflows preserve the user's confirmed product scope. Workflow routing may choose the lightest safe command surface, but it must not convert the user's product intent into a smaller MVP or first-story release. Scope reduction requires user confirmation, including when a named constraint forces a scope decision.
- **Semantic `sp-specify` traceability**: `sp-specify` preserves intent through `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`, `checklists/requirements.md`, and a minimal compatibility `brainstorming/handoff-to-specify.json`. `alignment.md` is the semantic traceability surface for `Semantic Term Decisions`, `Upstream Intent Disposition`, and `Out-Of-Scope Conflicts`; no upstream capability-like signal should disappear between discussion and spec.
- **Pre-spec discussion**: `sp-discussion` classifies each user turn, asks only for product judgment or genuine boundary/evidence conflicts, uses project cognition as advisory navigation, proves technical facts from live repository evidence, treats live evidence as the source of truth, appends compact ordinary-turn events, and refreshes structured discussion artifacts only at semantic checkpoints. It stores resumable product/technical discussions under `.specify/discussions/<slug>/`, runs a Context Boundary Gate before technical options or handoff generation, and drafts the unified handoff only after explicit user request and boundary lock; the handoff becomes ready only after self-review and user confirmation. Cross-project requests must lock the target project root (`target_project_root`); current project cognition cannot prove another project's implementation facts. The valid handoff is one unified handoff pair: `handoff-to-specify.md` plus `handoff-to-specify.json`, with `handoff_goal`, `context_boundary`, `implementation_target`, evidence provenance, `quality_gate`, Must-Preserve Ledger, coverage status, and planning gate status. Downstream workflows must preserve each protected item or block for a user decision.
- **Existing-project PRD extraction**: `sp-prd-scan -> sp-prd-build` is the canonical heavy reconstruction PRD lane for reverse-extracting repository-first current-state product documentation from code, docs, tests, routes, UI/API surfaces, and atlas evidence. Substantive scans are subagent-mandatory, critical claims target `L4 Reconstruction-Ready`, and `config-contracts.json` is part of the scan contract surface. `sp-prd-build` compiles from the scan package into the expanded reconstruction archive; `exports/README.md` is the package navigation entry, `exports/prd.md` remains the primary reader-facing PRD, and `sp-prd-build` must not reread the repository. `sp-prd` is deprecated compatibility-only routing into that pair, which remains a peer workflow path to `sp-specify` with no automatic planning handoff.
- **Concurrent lane runtime**: `src/specify_cli/lanes/` adds lane-local durable state, reconcile-before-resume routing, and dedicated lane closeout primitives for independent feature execution.
- **Enriched task contract generation**: `sp-tasks` produces the minimum executable task contract in light mode and enriched subagent-ready task contracts in standard/heavy mode when downstream delegated implementation needs packets.
- **Tasks/implement default contract**: `sp-tasks` must run an implementation-readiness self-audit before handoff. Clean completion writes `next_command: /sp.implement`, `gate_status: cleared`, and `highest_invalid_stage: none`; `sp-analyze` remains an optional diagnostic and legacy revalidation route only when explicitly invoked or recorded in existing state. If `analyze` is run, it should finish a complete blocker bundle before choosing the next command. repeated `tasks -> analyze -> tasks` loops are abnormal; only use `analyze` again when explicitly required by legacy or diagnostic state. Missing upstream truth routes directly to `plan`, `clarify`, or `deep-research`.
- **Spec quality gate (`spec-lint`)**: `tools/spec-lint/` is a zero-dependency Go binary that mechanically validates spec artifact sets against 8 tiered quality checks before `sp-plan`. Install scripts, CI cross-compilation, and the quality gate spec live alongside the tool. Read `templates/spec-quality-gate.md`.
- **Brownfield cognition lifecycle**: Generated projects use `.specify/project-cognition/status.json` plus agent-planned `project-cognition query` task-local bundles as an advisory project cognition index, while `.specify/project-cognition/project-cognition.db` is the canonical graph store for map queries. Workflows first call `project-cognition lexicon`, have the agent translate raw user intent into a `query_plan` using returned map terms, then call `project-cognition query --query-plan` when the map is available. New generated workflows treat these as advisory navigation inputs. Map points, code proves: technical claims must be backed by live project evidence. If the map is stale, weak for localized coverage, blocked, or likely incomplete, ordinary workflows continue with live repository evidence and apply the map-update-first routing policy. Use `map-update` for ordinary existing-baseline gaps. Use `map-scan -> map-build` only for first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`. Map-specific workflows and validation commands still validate their own artifacts; recorded refresh and ready refresh are different outcomes, and `partial_refresh` means refresh data was recorded but readiness still failed. A first brownfield cognition baseline is map-maintenance complete only after `project-cognition validate-scan --format json` and `project-cognition validate-build --format json` pass. After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself; update the git-baseline freshness metadata with `project-cognition record-refresh` or `project-cognition complete-refresh` unless validation reports `needs_rebuild`. Generated projects require `PROJECT_COGNITION_BIN` or `project-cognition` on PATH for direct project-cognition helpers; helper scripts prefer `PROJECT_COGNITION_BIN` when set and otherwise call `project-cognition` from PATH. Project cognition ignore rules live in root `.cognitionignore` or `.specify/project-cognition/.cognitionignore`; they are gitignore-compatible, apply to `map-scan`, `map-build`, and `map-update`, and excluded paths must not enter project cognition graph evidence, route indexes, or `minimal_live_reads`.
- **Delegated execution contracts**: `src/specify_cli/execution/`, `src/specify_cli/hooks/`, and `src/specify_cli/orchestration/` define packet/result schemas, quality hooks, adaptive and mandatory dispatch selection, and state surfaces.
- **Codex team runtime**: `src/specify_cli/codex_team/`, `src/specify_cli/mcp/`, and `extensions/agent-teams/engine/` provide optional Codex team orchestration, state, MCP facade, and bundled engine assets.
- **Testing and verification**: Python pytest layers, integration/template contract tests, Codex-team tests, and engine build checks protect generated behavior.

## How To Read This Project

- Start here for orientation.
- The runtime atlas now resolves to two workflow handbooks.
- Read `DEBUG-HANDBOOK.md` for `sp-debug` and `BUILD-HANDBOOK.md` for the major non-debug workflows.
- **First stop for any task**: use the project cognition routes described here. Repo-local `.specify/` state is not committed source-of-truth for this repository.
- For generated projects, read `.specify/project-cognition/status.json` plus the agent-planned task-local project cognition query bundle before broad brownfield work.
- Treat project cognition as an advisory navigation index. Code, tests, scripts, configuration, and authoritative docs are the evidence sources.
- Use `.cognitionignore` or `.specify/project-cognition/.cognitionignore` to exclude vendored, generated, archived, or nested-reference projects from project cognition. The rules are gitignore-compatible and affect `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence.
- When referencing another local directory, run `project-cognition discover --root <path> --format json` after checking for `.specify/`. Use that directory's cognition only when `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db` exist, `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is true; otherwise fall back to minimal live reads. Do not treat legacy `.specify/project-map/**` outputs as current truth.
- Supporting project-map outputs are support-only or reference-only compatibility/export surfaces.
- The refresh workbench still contains `map-scan` / `map-build` scan packets and refresh workbench artifacts for rebuilding the handbooks.
- Legacy project-map artifacts may still exist in old projects, but there is no Python runtime alias and new workflows should not call or require `.specify/project-map/**`.
- Fall back to live code reads only when cognition coverage is missing, stale, too broad, or marked low confidence.
- If changed paths are missing from project cognition `path_index`, let `sp-map-update` classify the gap first. Normal code changes should use `sp-map-update` for bounded incremental refresh from changed paths. Uncertain closure is recorded by `map-update` as partial/low-confidence facts when needed. Adoptable paths get provisional coverage, uncertain paths return `minimal_live_reads`, and ordinary existing-baseline gaps remain `sp-map-update` work.
- `sp-debug` should use the project cognition query bundle as its default intake. Its deeper Stage 1A/1B observer-contract flow remains available when map coverage is missing, ambiguous, stale, or contradicted by evidence.
- Preserve the state vocabulary: `fresh`, `missing`, `stale`, `support_drift`, `partial_refresh`, and `possibly_stale` are machine freshness states; `recommended_next_action` is the public operator guidance.

## Project Cognition Routes

For generated projects, use project cognition first:

- `.specify/project-cognition/status.json` — freshness, coverage, stale paths, and refresh metadata
- `.specify/project-cognition/project-cognition.db` — canonical SQLite graph store
- `project-cognition lexicon` plus `project-cognition query --query-plan` bundle — map terms for agent query planning, task-local cognition bundles, readiness, and `minimal_live_reads`
- When shell quoting makes inline JSON brittle, use `project-cognition query --query-plan-file <path>` instead. The query plan accepts `path_hints`/`reason` as aliases for `paths`/`selection_reason`.

The cognition model should help answer:

- which workflow-specific cognition slice owns the current task
- which graph claims, conflicts, or slices must be read before source work begins
- which propagation risks and verification routes matter before changing code
- what remains unknown and therefore needs live repository confirmation
- whether the factual freshness state is runtime staleness, support drift, or a partial refresh that still blocks readiness

## Senior Consequence Analysis Gate

Project cognition is necessary but not sufficient for dependency analysis. It gives workflow agents ownership, consumers, state surfaces, change-propagation facts, verification routes, conflicts, and known unknowns. `sp-map-build` and the project cognition runtime provide the evidence layer, but the Senior Consequence Analysis Gate turns those facts into product and implementation obligations.

When work involves lifecycle operations, running or concurrent objects, destructive actions, shared state, downstream consumers, compatibility, security, or multiple plausible behaviors, workflows must preserve:

- Affected Object Map
- State-Behavior Matrix
- Dependency Impact Table
- Recovery And Validation Contract
- Coverage Gaps

For example, "close team" must consider running workers, queued tasks, late result submission, heartbeat state, `status`, `await`, `resume`, `cleanup`, idempotency, and validation evidence before the workflow can claim the feature is ready for the next stage.

Use `CA-###` IDs for consequence obligations that must survive handoff from `discussion` to `specify`, `plan`, `tasks`, and `implement`; `analyze` consumes the same obligations only when run as an optional diagnostic or legacy revalidation pass. `fast` upgrades when the gate triggers; `quick` may continue only when the consequence model is bounded; `debug` traces the dependency loop and rejects surface-only fixes.

## Shared Surfaces

- `src/specify_cli/__init__.py`: top-level Typer app, command registration, init flow, project-map/hook/learning/testing/eval/team helper commands.
- `src/specify_cli/launcher.py`: persisted project launcher binding, generated-project compatibility diagnostics, and runtime launcher helpers.
- `src/specify_cli/lanes/`: lane registry cache, lane-local durable state, lease helpers, reconcile logic, root-level lane resolution, and integrate closeout helpers.
- `src/specify_cli/integrations/base.py` and `src/specify_cli/integrations/__init__.py`: integration registry, shared generation bases, template processing, passive skill installation, manifest behavior.
- `templates/`: command templates, command partials, passive skills, project-map/testing templates, worker prompts, constitution/spec/plan/tasks artifacts.
- `scripts/bash/` and `scripts/powershell/`: generated helper layer and freshness/context-update scripts.
- `src/specify_cli/execution/`, `src/specify_cli/hooks/`, `src/specify_cli/orchestration/`: packet/result schemas, workflow hooks, adaptive plan/tasks dispatch plus mandatory-subagent dispatch/state/review helpers.
- `src/specify_cli/codex_team/` and `extensions/agent-teams/engine/`: optional Codex team runtime and bundled engine.
- `tools/spec-lint/`: spec quality gate binary, install scripts, CI cross-compilation workflow.
- `tools/project-cognition/`: standalone Go project cognition runtime binary, install scripts, and acceptance-gate validators.

## Risky Coordination Points

- Editing `src/specify_cli/__init__.py` can change CLI help, routing, init behavior, hook surfaces, and tests across many areas.
- Editing `templates/commands/`, `templates/command-partials/`, or `templates/passive-skills/` changes generated downstream behavior for multiple agents.
- Editing `src/specify_cli/integrations/base.py` affects most generated integrations.
- Editing `tools/project-cognition/`, `src/specify_cli/project_cognition_tool.py`, or freshness scripts affects brownfield workflow gating.
- Editing Codex team installer/runtime files can affect `.codex/config.toml`, `.specify/teams/*`, worker state, MCP behavior, and engine packaging.

## Change-Propagation Hotspots

- Agent registration metadata propagates into CLI help, integration generation tests, README guidance, generated file paths, and tool checks.
- Generated runtime compatibility rules propagate into `specify check`, integration install/switch/repair flows, generated `.specify/config.json`, generated hook/settings assets, and generated shared scripts.
- Template wording propagates into every generated agent surface and template assertion tests.
- Lane registry semantics and reconcile rules propagate into root-level routing, workflow templates, feature-creation scripts, hook diagnostics, and generated documentation.
- Adaptive and mandatory dispatch vocabulary propagates into orchestration tests, generated workflow tests, integration tests, README/quickstart guidance, context scripts, and project-map docs.
- Workflow-handbook guidance now propagates from `templates/project-handbook-template.md`, workflow command templates, packet context helpers, and handbook-validation rules into initialized projects, map refresh helpers, and tests.
- Packet/result schema changes propagate into execution helpers, hooks, Codex team runtime, generated workflow prompts, and contract tests.
- Project cognition freshness changes propagate into the Go runtime, Python external-tool bridge, Bash/PowerShell scripts, hook commands, and brownfield gates.
- Engine packaging changes propagate through `pyproject.toml` force-includes, `extensions/agent-teams/engine/`, Codex team installer/runtime tests, and release artifacts.

## Change Impact Guide

- Change CLI command wiring or init behavior: read `root/ARCHITECTURE.md`, `root/WORKFLOWS.md`, and `modules/specify-cli-core/OVERVIEW.md`.
- Change an integration adapter: read `root/INTEGRATIONS.md`, `root/CONVENTIONS.md`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- Change workflow templates or passive skills: read `root/WORKFLOWS.md`, `modules/templates-generated-surfaces/WORKFLOWS.md`, and template tests. For `sp-prd-scan -> sp-prd-build`, preserve the heavy reconstruction contract: repository-first current-state PRD extraction, subagent-mandatory substantive scans, `L4 Reconstruction-Ready` critical claims, `config-contracts.json` in the contract surface, `sp-prd-build` as scan-package compilation rather than a second repository scan, `sp-prd` compatibility-only routing, and no automatic planning handoff.
- Change hooks, packets, orchestration, or Codex team runtime: read `root/ARCHITECTURE.md`, `root/OPERATIONS.md`, and relevant module docs.
- Change packaging, CI, devcontainer, extension, or preset surfaces: read `root/STRUCTURE.md`, `root/INTEGRATIONS.md`, and `root/OPERATIONS.md`.
- Change launcher binding, generated runtime compatibility, or generated-project repair flows: read `root/OPERATIONS.md`, `root/INTEGRATIONS.md`, and `modules/specify-cli-core/ARCHITECTURE.md`.

## Verification Entry Points

- Focused project cognition regression: `cd tools/project-cognition && go test ./... && cd ../.. && pytest tests/test_project_map_freshness_scripts.py tests/contract/test_hook_cli_surface.py -q`
- Full Python regression: `uv run --extra test pytest -q -n auto`
- Integration surface: `pytest tests/integrations -q`
- Hooks/execution/orchestration: `pytest tests/hooks tests/execution tests/orchestration -q`
- Codex team runtime: `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q`
- spec-lint: `cd tools/spec-lint && go vet ./... && go build -o /dev/null .`
- project-cognition: `cd tools/project-cognition && go vet ./... && go build -o /dev/null .`
- Packaging sanity: `uv build`
- Bundled engine sanity: `npm --prefix extensions/agent-teams/engine run build`

## Known Unknowns

- External agent CLIs can change behavior outside this repository; adapter claims should be verified against upstream docs when external surfaces change.
- The Rust crates under `extensions/agent-teams/engine/crates/` were sampled for this atlas; run a targeted Rust packet before changing Rust runtime semantics.
- The global `specify` executable on a developer machine may lag this checkout. Prefer `PYTHONPATH=src; python -m specify_cli ...` or an editable install when validating local source behavior.

## Low-Confidence Areas

- `agent-teams-engine` Rust internals: Inferred from manifests, representative source, and tests rather than exhaustive source tracing.
- Release packaging beyond GitHub release creation: sampled from workflow files and `pyproject.toml`, but publishing details should be rechecked before changing distribution automation.
- Historical `.planning/**` artifacts are useful context but not always current product truth; `.planning/STATE.md` is the current planning status source.

## Atlas Views

- `templates/project-map/index/atlas-index.json`: machine-readable atlas summary and next-read routes for generated projects.
- `templates/project-map/index/modules.json`: module registry, owned roots, and module doc paths for generated projects.
- `templates/project-map/index/relations.json`: cross-module dependencies and shared-surface expansion routes for generated projects.
- Generated-project `.specify/project-cognition/status.json` plus the `project-cognition query` task-local bundle: freshness, module coverage, stale paths, and refresh metadata.
- `root/ARCHITECTURE.md`: cross-module architecture, contracts, dependency graph, capability cards.
- `root/STRUCTURE.md`: directory ownership, critical file families, placement rules.
- `root/CONVENTIONS.md`: naming, generated-surface, state, compatibility, and review conventions.
- `root/INTEGRATIONS.md`: supported agent adapters, external tool boundaries, MCP/runtime seams, security boundaries.
- `root/WORKFLOWS.md`: user and maintainer flows, state transitions, map/test/implement/debug behavior.
- `root/TESTING.md`: test layers, verification matrix, command selection.
- `root/OPERATIONS.md`: build, install, freshness, runtime state, recovery, troubleshooting.

## Where To Read Next

- Add or change workflow behavior: `root/WORKFLOWS.md`, then `modules/templates-generated-surfaces/WORKFLOWS.md`.
- Add or change an agent integration: `root/INTEGRATIONS.md`, then `modules/specify-cli-core/ARCHITECTURE.md`.
- Change CLI internals: `modules/specify-cli-core/OVERVIEW.md`, then `modules/specify-cli-core/ARCHITECTURE.md`.
- Change Codex team runtime or bundled engine: `modules/agent-teams-engine/OVERVIEW.md`, then `root/OPERATIONS.md`.
- Diagnose test failures: `root/TESTING.md`, then the module `TESTING.md` for the affected area.

## Topic Map

- `.specify/project-cognition/status.json` - default generated-project runtime status, freshness, coverage, stale paths, and refresh metadata
- `.specify/project-cognition/project-cognition.db` - canonical generated-project SQLite graph store
- `project-cognition lexicon` plus `project-cognition query --query-plan` bundle - default generated-project route to map terms, task-local bundles, readiness, and `minimal_live_reads`
- `DEBUG-HANDBOOK.md` - compatibility/export debug view
- `BUILD-HANDBOOK.md` - compatibility/export build/change view
- `templates/project-map/**` is retained only for legacy compatibility review and must not be installed or required by new generated projects.

## Update Triggers

- CLI command registration, generated workflow names, integration directories, packet/result schemas, hook events, testing workflow state, project-map compatibility/export rules, extension/preset schemas, packaging force-includes, or Codex team runtime installation assumptions change.

## Recent Structural Changes

- The runtime atlas is being rewritten around `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, `project-cognition lexicon`, and agent-planned `project-cognition query --query-plan` task-local bundles.
- Ordinary `sp-*` workflows should treat project cognition consumption as advisory navigation before source-level work.
- Supporting handbook artifacts remain available as compatibility/export surfaces, but are no longer the primary evidence path.
