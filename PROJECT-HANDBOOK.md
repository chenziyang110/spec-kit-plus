# Project Handbook

**Last Updated:** 2026-05-02
**Purpose:** Root navigation artifact for this repository.

## System Summary

`spec-kit-plus` is a Python-first CLI and asset-packaging repository for practical Spec-Driven Development workflows across local AI coding agents. The primary product surface is the `specify` command implemented in `src/specify_cli/__init__.py`; it initializes projects, installs agent-specific workflow files, manages project cognition freshness and compatibility exports, exposes testing/learning/hook/eval helper surfaces, and provides the Codex-only `sp-teams` runtime path.

The repository has three mapped runtime modules:

- `specify-cli-core`: Python CLI, integration registry, project cognition freshness and compatibility-export helpers, learning/testing/eval helpers, execution packet/result contracts, hooks, orchestration policy, and Codex team Python control plane.
- `templates-generated-surfaces`: workflow command templates, command partials, passive skills, project-map/testing templates, scripts, and worker prompts that are copied or transformed into downstream projects.
- `agent-teams-engine`: bundled optional Node/TypeScript plus Rust runtime assets for Codex team coordination.

## System Boundaries

This repository owns the `specify` CLI, bundled templates/scripts, supported-agent integration adapters, project-map/testing workflow contracts, extension/preset managers, and optional Codex team runtime packaging. It coordinates with external agent CLIs, Git, uv/pip packaging, Node/npm, Cargo/Rust, optional MCP dependencies, tmux/psmux, and GitHub Actions. It does not own upstream agent CLI behavior, external MCP server implementations, terminal multiplexers, or the user's global `specify` installation.

## High-Value Capabilities

- **Project initialization and generated agent surfaces**: `specify init` resolves `--ai` or `--integration`, installs command/skill/workflow files, copies scripts/templates, and records integration manifests. Read `src/specify_cli/__init__.py`, `src/specify_cli/integrations/**`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Generated-project repair and compatibility diagnostics**: `specify check` now surfaces broken project launchers and stale generated runtime assets, and `specify integration repair` refreshes shared/runtime-managed generated assets in place without overwriting user-edited workflow content. Read `src/specify_cli/__init__.py`, `src/specify_cli/integrations/base.py`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Passive project learning memory**: generated projects use `.specify/memory/learnings/INDEX.md` as the thin first-read learning layer and may link each reusable lesson to one detail markdown document under `.specify/memory/learnings/`. `project-learnings.md` remains a compatibility summary; new captures write index/detail memory first, and workflow closeout applies the Learning Reflex before reusable lessons are left only in chat or workflow state.
- **Workflow contract generation**: `templates/commands/`, `templates/command-partials/`, and `templates/passive-skills/` define `sp-*` behavior for downstream agents. `sp-specify` is now a public entry shell with an internal brainstorming kernel that locks brainstorming truth artifacts (`facts`, `route`, `intent`, `complexity`), applies deterministic routing, and then compiles the familiar spec package before it routes to `plan`, `clarify`, or `deep-research`. The downstream chain now carries structured handoff contracts through `sp-plan`, `sp-tasks`, and `sp-implement` so execution consumes locked intent instead of reinterpreting chat history. Read `templates/commands/**`, `templates/command-partials/**`, and `modules/templates-generated-surfaces/WORKFLOWS.md`.
- **Lossless `sp-specify` state**: `sp-specify` is lossless-state backed for new feature packages. The trusted recovery source is `brainstorming/journal.ndjson` plus JSON stage artifacts indexed by `brainstorming/stage-manifest.json`; Markdown is not a trusted recovery source. Final artifacts carry `compiled_from` / source-map references so planning can trace major claims to event IDs or evidence IDs.
- **Pre-spec discussion**: `sp-discussion` stores resumable product/technical discussions under `.specify/discussions/<slug>/`, produces technical options and requirements drafts, and only hands off after explicit user request. Handoff now begins with `handoff-assessment.md`: one bounded result writes latest-copy `handoff-to-specify.md` and `handoff-to-specify.json` with a Must-Preserve Ledger, coverage status, and planning gate status. Broad directions stay inside `sp-discussion` through `split-plan.md` candidate backlog entries and canonical `handoffs/<candidate_id>-handoff-to-specify.md` and `handoffs/<candidate_id>-handoff-to-specify.json` files, with `CAND-001` and `CAND-002` as examples. After one candidate ships, return to the same discussion slug to select the next stage; downstream workflows must preserve each protected ledger item or block for a user decision.
- **Existing-project PRD extraction**: `sp-prd-scan -> sp-prd-build` is the canonical heavy reconstruction PRD lane for reverse-extracting repository-first current-state product documentation from code, docs, tests, routes, UI/API surfaces, and atlas evidence. Substantive scans are subagent-mandatory, critical claims target `L4 Reconstruction-Ready`, and `config-contracts.json` is part of the scan contract surface. `sp-prd-build` compiles from the scan package into the expanded reconstruction archive; `exports/README.md` is the package navigation entry, `exports/prd.md` remains the primary reader-facing PRD, and `sp-prd-build` must not reread the repository. `sp-prd` is deprecated compatibility-only routing into that pair, which remains a peer workflow path to `sp-specify` with no automatic planning handoff.
- **Concurrent lane runtime**: `src/specify_cli/lanes/` adds lane-local durable state, reconcile-before-resume routing, and dedicated lane closeout primitives for independent feature execution.
- **Enriched task contract generation**: `sp-tasks` produces subagent-ready task contracts with agent role assignment, context navigation pointers, write/read/forbidden scope boundaries, verify commands, and escalation strategy — enabling `sp-implement` to dispatch subagents directly without leader clarification.
- **Analyze/tasks convergence contract**: `sp-analyze` must finish a complete blocker bundle before choosing the single recommended next command, while `sp-tasks` must run an analyze-compatible task self-audit before handoff. repeated `tasks -> analyze -> tasks` loops are abnormal. No more than one task-layer remediation cycle is expected, and missing upstream truth routes directly to `plan`, `clarify`, or `deep-research` before regenerated tasks return to `analyze`.
- **Spec quality gate (`spec-lint`)**: `tools/spec-lint/` is a zero-dependency Go binary that mechanically validates spec artifact sets against 8 tiered quality checks before `sp-plan`. Install scripts, CI cross-compilation, and the quality gate spec live alongside the tool. Read `templates/spec-quality-gate.md`.
- **Brownfield cognition lifecycle**: Generated projects use `.specify/project-cognition/status.json` plus agent-planned `project-cognition query` task-local bundles as the default brownfield runtime truth surface, while `.specify/project-cognition/project-cognition.db` is the canonical graph store. Workflows first call `project-cognition lexicon`, have the agent translate raw user intent into a `query_plan` using returned map terms, then call `project-cognition query --query-plan`. `specify project-map ...` remains a legacy CLI alias for existing projects, but new workflows should not read or require `.specify/project-map/**`. For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build`. That pair is complete only when scan acceptance and build acceptance pass: `project-cognition validate-scan --format json` and `project-cognition validate-build --format json`. After that, normal code changes should use `sp-map-update` for bounded incremental refresh from changed paths. Return to `sp-map-scan -> sp-map-build` only when the baseline is missing, unusable, schema-incompatible, explicitly being rebuilt, or invalidated by broad architecture replacement. Uncertain closure is recorded by `map-update` as partial/low-confidence facts, known unknowns, and `minimal_live_reads`; it is not by itself a reason to rebuild. Project cognition ignore rules live in root `.cognitionignore` or `.specify/project-cognition/.cognitionignore`; they are gitignore-compatible, apply to `map-scan`, `map-build`, and `map-update`, and excluded paths must not enter project cognition graph evidence, runtime route indexes, or `minimal_live_reads`. When using another local directory as a reference, check for `.specify/` first and run `cognition discover --root <path> --format json`; use another project's cognition only when `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db` exist, `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is true. If the reference is stale, blocked, or incomplete, do not treat legacy `.specify/project-map/**` outputs as current truth; fall back to minimal live reads or refresh that reference with `map-scan -> map-build` or `map-update`. After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself; update the git-baseline freshness metadata with `project-cognition record-refresh` or `project-cognition complete-refresh` unless validation reports `needs_rebuild`. Recorded refresh and ready refresh are different outcomes: `partial_refresh` means refresh data was recorded but readiness still failed. Support drift is not runtime-truth staleness and should be resolved as support-surface cleanup, not reflexively routed to `map-update`. Same-feature `sp-implement` resume may continue with warning when dirty fallback metadata was recorded by that feature's prior implement run, but upstream brownfield entrypoints and other features still require refresh first.
- **Delegated execution contracts**: `src/specify_cli/execution/`, `src/specify_cli/hooks/`, and `src/specify_cli/orchestration/` define packet/result schemas, quality hooks, subagents-first dispatch selection, and state surfaces.
- **Codex team runtime**: `src/specify_cli/codex_team/`, `src/specify_cli/mcp/`, and `extensions/agent-teams/engine/` provide optional Codex team orchestration, state, MCP facade, and bundled engine assets.
- **Testing and verification**: Python pytest layers, integration/template contract tests, Codex-team tests, and engine build checks protect generated behavior.

## How To Read This Project

- Start here for orientation.
- The runtime atlas now resolves to two workflow handbooks.
- Read `DEBUG-HANDBOOK.md` for `sp-debug` and `BUILD-HANDBOOK.md` for the major non-debug workflows.
- **First stop for any task**: use the project cognition routes described here. Repo-local `.specify/` state is not committed source-of-truth for this repository.
- For generated projects, read `.specify/project-cognition/status.json` plus the agent-planned task-local project cognition query bundle before broad brownfield work.
- Treat project cognition as the primary runtime truth surface.
- Use `.cognitionignore` or `.specify/project-cognition/.cognitionignore` to exclude vendored, generated, archived, or nested-reference projects from project cognition. The rules are gitignore-compatible and affect `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence.
- When referencing another local directory, run `cognition discover --root <path> --format json` after checking for `.specify/`. Use that directory's cognition only when `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db` exist, `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is true; otherwise fall back to minimal live reads.
- Supporting project-map outputs are support-only or reference-only.
- The refresh workbench still contains `map-scan` / `map-build` scan packets and refresh workbench artifacts for rebuilding the handbooks.
- `specify project-map ...` remains a legacy CLI alias for existing projects, but new workflows should not read or require `.specify/project-map/**`.
- Fall back to live code reads only when cognition coverage is missing, stale, too broad, or marked low confidence.
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

Use `CA-###` IDs for consequence obligations that must survive handoff from `discussion` to `specify`, `plan`, `tasks`, `analyze`, and `implement`. `fast` upgrades when the gate triggers; `quick` may continue only when the consequence model is bounded; `debug` traces the dependency loop and rejects surface-only fixes.

## Shared Surfaces

- `src/specify_cli/__init__.py`: top-level Typer app, command registration, init flow, project-map/hook/learning/testing/eval/team helper commands.
- `src/specify_cli/launcher.py`: persisted project launcher binding, generated-project compatibility diagnostics, and runtime launcher helpers.
- `src/specify_cli/lanes/`: lane registry cache, lane-local durable state, lease helpers, reconcile logic, root-level lane resolution, and integrate closeout helpers.
- `src/specify_cli/integrations/base.py` and `src/specify_cli/integrations/__init__.py`: integration registry, shared generation bases, template processing, passive skill installation, manifest behavior.
- `templates/`: command templates, command partials, passive skills, project-map/testing templates, worker prompts, constitution/spec/plan/tasks artifacts.
- `scripts/bash/` and `scripts/powershell/`: generated helper layer and freshness/context-update scripts.
- `src/specify_cli/execution/`, `src/specify_cli/hooks/`, `src/specify_cli/orchestration/`: packet/result schemas, workflow hooks, subagents-first dispatch/state/review helpers.
- `src/specify_cli/codex_team/` and `extensions/agent-teams/engine/`: optional Codex team runtime and bundled engine.
- `tools/spec-lint/`: spec quality gate binary, install scripts, CI cross-compilation workflow.

## Risky Coordination Points

- Editing `src/specify_cli/__init__.py` can change CLI help, routing, init behavior, hook surfaces, and tests across many areas.
- Editing `templates/commands/`, `templates/command-partials/`, or `templates/passive-skills/` changes generated downstream behavior for multiple agents.
- Editing `src/specify_cli/integrations/base.py` affects most generated integrations.
- Editing `src/specify_cli/project_map_status.py` or freshness scripts affects brownfield workflow gating.
- Editing Codex team installer/runtime files can affect `.codex/config.toml`, `.specify/teams/*`, worker state, MCP behavior, and engine packaging.

## Change-Propagation Hotspots

- Agent registration metadata propagates into CLI help, integration generation tests, README guidance, generated file paths, and tool checks.
- Generated runtime compatibility rules propagate into `specify check`, integration install/switch/repair flows, generated `.specify/config.json`, generated hook/settings assets, and generated shared scripts.
- Template wording propagates into every generated agent surface and template assertion tests.
- Lane registry semantics and reconcile rules propagate into root-level routing, workflow templates, feature-creation scripts, hook diagnostics, and generated documentation.
- Subagents-first dispatch vocabulary propagates into orchestration tests, generated workflow tests, integration tests, README/quickstart guidance, context scripts, and project-map docs.
- Workflow-handbook guidance now propagates from `templates/project-handbook-template.md`, workflow command templates, packet context helpers, and handbook-validation rules into initialized projects, map refresh helpers, and tests.
- Packet/result schema changes propagate into execution helpers, hooks, Codex team runtime, generated workflow prompts, and contract tests.
- Project cognition freshness changes propagate into Python helpers, Bash/PowerShell scripts, hook commands, and brownfield gates.
- Engine packaging changes propagate through `pyproject.toml` force-includes, `extensions/agent-teams/engine/`, Codex team installer/runtime tests, and release artifacts.

## Change Impact Guide

- Change CLI command wiring or init behavior: read `root/ARCHITECTURE.md`, `root/WORKFLOWS.md`, and `modules/specify-cli-core/OVERVIEW.md`.
- Change an integration adapter: read `root/INTEGRATIONS.md`, `root/CONVENTIONS.md`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- Change workflow templates or passive skills: read `root/WORKFLOWS.md`, `modules/templates-generated-surfaces/WORKFLOWS.md`, and template tests. For `sp-prd-scan -> sp-prd-build`, preserve the heavy reconstruction contract: repository-first current-state PRD extraction, subagent-mandatory substantive scans, `L4 Reconstruction-Ready` critical claims, `config-contracts.json` in the contract surface, `sp-prd-build` as scan-package compilation rather than a second repository scan, `sp-prd` compatibility-only routing, and no automatic planning handoff.
- Change hooks, packets, orchestration, or Codex team runtime: read `root/ARCHITECTURE.md`, `root/OPERATIONS.md`, and relevant module docs.
- Change packaging, CI, devcontainer, extension, or preset surfaces: read `root/STRUCTURE.md`, `root/INTEGRATIONS.md`, and `root/OPERATIONS.md`.
- Change launcher binding, generated runtime compatibility, or generated-project repair flows: read `root/OPERATIONS.md`, `root/INTEGRATIONS.md`, and `modules/specify-cli-core/ARCHITECTURE.md`.

## Verification Entry Points

- Focused map regression: `pytest tests/test_map_scan_build_template_guidance.py tests/test_project_map_layered_contract.py tests/test_project_map_status.py -q`
- Full Python regression: `uv run --extra test pytest -q -n auto`
- Integration surface: `pytest tests/integrations -q`
- Hooks/execution/orchestration: `pytest tests/hooks tests/execution tests/orchestration -q`
- Codex team runtime: `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q`
- spec-lint: `cd tools/spec-lint && go vet ./... && go build -o /dev/null .`
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

- CLI command registration, generated workflow names, integration directories, packet/result schemas, hook events, testing workflow state, project-map freshness rules, extension/preset schemas, packaging force-includes, or Codex team runtime installation assumptions change.

## Recent Structural Changes

- The runtime atlas is being rewritten around `.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, `project-cognition lexicon`, and agent-planned `project-cognition query --query-plan` task-local bundles.
- Ordinary `sp-*` workflows should treat project cognition consumption as the hard gate before source-level work.
- Supporting handbook artifacts remain available as compatibility/export surfaces, but are no longer the primary runtime truth path.
- Testing workflow guidance now centers `sp-test-scan` and `sp-test-build`.
