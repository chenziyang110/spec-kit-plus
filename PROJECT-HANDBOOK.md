# Project Handbook

**Last Updated:** 2026-05-02
**Purpose:** Root navigation artifact for this repository.

## System Summary

`spec-kit-plus` is a Python-first CLI and asset-packaging repository for practical Spec-Driven Development workflows across local AI coding agents. The primary product surface is the `specify` command implemented in `src/specify_cli/__init__.py`; it initializes projects, installs agent-specific workflow files, manages project-map freshness, exposes testing/learning/hook/eval helper surfaces, and provides the Codex-only `sp-teams` runtime path.

The repository has three mapped runtime modules:

- `specify-cli-core`: Python CLI, integration registry, project-map freshness, learning/testing/eval helpers, execution packet/result contracts, hooks, orchestration policy, and Codex team Python control plane.
- `templates-generated-surfaces`: workflow command templates, command partials, passive skills, project-map/testing templates, scripts, and worker prompts that are copied or transformed into downstream projects.
- `agent-teams-engine`: bundled optional Node/TypeScript plus Rust runtime assets for Codex team coordination.

## System Boundaries

This repository owns the `specify` CLI, bundled templates/scripts, supported-agent integration adapters, project-map/testing workflow contracts, extension/preset managers, and optional Codex team runtime packaging. It coordinates with external agent CLIs, Git, uv/pip packaging, Node/npm, Cargo/Rust, optional MCP dependencies, tmux/psmux, and GitHub Actions. It does not own upstream agent CLI behavior, external MCP server implementations, terminal multiplexers, or the user's global `specify` installation.

## High-Value Capabilities

- **Project initialization and generated agent surfaces**: `specify init` resolves `--ai` or `--integration`, installs command/skill/workflow files, copies scripts/templates, and records integration manifests. Read `.specify/project-map/root/INTEGRATIONS.md` and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Generated-project repair and compatibility diagnostics**: `specify check` now surfaces broken project launchers and stale generated runtime assets, and `specify integration repair` refreshes shared/runtime-managed generated assets in place without overwriting user-edited workflow content. Read `.specify/project-map/root/OPERATIONS.md` and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Workflow contract generation**: `templates/commands/`, `templates/command-partials/`, and `templates/passive-skills/` define `sp-*` behavior for downstream agents. Read `.specify/project-map/root/WORKFLOWS.md` and `modules/templates-generated-surfaces/WORKFLOWS.md`.
- **Existing-project PRD extraction**: `sp-prd` is the repository-first current-state PRD lane for reverse-extracting product documentation from code, docs, tests, routes, UI/API surfaces, and atlas evidence. It is a peer workflow to `sp-specify` and does not automatically hand off to planning.
- **Concurrent lane runtime**: `src/specify_cli/lanes/` adds lane-local durable state, reconcile-before-resume routing, and dedicated lane closeout primitives for independent feature execution.
- **Enriched task contract generation**: `sp-tasks` produces subagent-ready task contracts with agent role assignment, context navigation pointers, write/read/forbidden scope boundaries, verify commands, and escalation strategy — enabling `sp-implement` to dispatch subagents directly without leader clarification.
- **Spec quality gate (`spec-lint`)**: `tools/spec-lint/` is a zero-dependency Go binary that mechanically validates spec artifact sets against 8 tiered quality checks before `sp-plan`. Install scripts, CI cross-compilation, and the quality gate spec live alongside the tool. Read `templates/spec-quality-gate.md`.
- **Brownfield atlas lifecycle**: `map-scan -> map-build` is the required stale/missing context gate. It produces scan packets, worker-result evidence, layered root/module docs, and freshness metadata. Read `.specify/project-map/root/OPERATIONS.md`.
- **Delegated execution contracts**: `src/specify_cli/execution/`, `src/specify_cli/hooks/`, and `src/specify_cli/orchestration/` define packet/result schemas, quality hooks, subagents-first dispatch selection, and state surfaces. Read `.specify/project-map/root/ARCHITECTURE.md`.
- **Codex team runtime**: `src/specify_cli/codex_team/`, `src/specify_cli/mcp/`, and `extensions/agent-teams/engine/` provide optional Codex team orchestration, state, MCP facade, and bundled engine assets. Read `.specify/project-map/modules/agent-teams-engine/OVERVIEW.md`.
- **Testing and verification**: Python pytest layers, integration/template contract tests, Codex-team tests, and engine build checks protect generated behavior. Read `.specify/project-map/root/TESTING.md`.

## How To Read This Project

- Start here for orientation.
- **First stop for any task**: use the atlas routes described here and in `templates/project-map/QUICK-NAV.md` — repo-local `.specify/` state is not committed source-of-truth for this repository.
- The handbook is the index-first entrypoint.
- For generated projects, read `.specify/project-map/index/atlas-index.json` and `.specify/project-map/index/status.json` before broad brownfield work.
- Treat the combined handbook/project-map set as an atlas-style technical encyclopedia.
- The root topical docs explain cross-module architecture, workflows, integrations, testing, operations, structure, and conventions.
- Module docs explain module-local ownership and drill-down routes.
- Fall back to live code reads only when topical coverage is missing, stale, too broad, or marked low confidence.

## Quick Navigation (Layer 1)

For generated projects, open `.specify/project-map/QUICK-NAV.md` first. In this repository, use `templates/project-map/QUICK-NAV.md` plus the handbook's `Where To Read Next` / `Topic Map` sections. Layer 1 is now a dictionary-style atlas entry surface rather than a thin route table.

- **Layer 1 (routing)**: `QUICK-NAV.md` — task routes, symptom routes, shared-surface hotspots, verification routes, and propagation-risk routes
- **Layer 2 (summary)**: `root/ARCHITECTURE.md` capability cards — module-at-a-glance
- **Layer 3 (detail)**: `modules/<name>/OVERVIEW.md` — full technical detail
- **Layer 4 (source)**: Live code — when docs are missing or stale

The entry layer should help answer:

- which module most likely owns the touched area
- which root topic should be read next
- which verification entrypoints matter after the change
- which shared surfaces or propagation risks make the change unsafe to treat as local

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
- Layered atlas routing now propagates from `templates/project-handbook-template.md`, `templates/project-map/QUICK-NAV.md`, `templates/project-map/index/atlas-index.json`, and `templates/project-map/map-state-template.md` into initialized projects, map refresh helpers, and project-map tests.
- Packet/result schema changes propagate into execution helpers, hooks, Codex team runtime, generated workflow prompts, and contract tests.
- Project-map freshness changes propagate into Python helpers, Bash/PowerShell scripts, hook commands, and brownfield gates.
- Engine packaging changes propagate through `pyproject.toml` force-includes, `extensions/agent-teams/engine/`, Codex team installer/runtime tests, and release artifacts.

## Change Impact Guide

- Change CLI command wiring or init behavior: read `root/ARCHITECTURE.md`, `root/WORKFLOWS.md`, and `modules/specify-cli-core/OVERVIEW.md`.
- Change an integration adapter: read `root/INTEGRATIONS.md`, `root/CONVENTIONS.md`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- Change workflow templates or passive skills: read `root/WORKFLOWS.md`, `modules/templates-generated-surfaces/WORKFLOWS.md`, and template tests. For `sp-prd`, preserve repository-first current-state PRD extraction and no automatic planning handoff.
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
- Generated-project `.specify/project-map/index/status.json`: freshness and module coverage status.
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

- `templates/project-map/QUICK-NAV.md` - Layer 1 routing table for generated-project atlases
- `templates/project-map/index/atlas-index.json` - atlas entry summary and next lookup pointers
- `templates/project-map/index/modules.json` - module registry and module document paths
- `templates/project-map/index/relations.json` - cross-module dependencies and shared surfaces
- Generated-project `.specify/project-map/index/status.json` - atlas freshness and module status
- `templates/project-map/root/ARCHITECTURE.md` - canonical root architecture template for generated-project atlases
- `templates/project-map/root/STRUCTURE.md` - canonical root structure template for generated-project atlases
- `templates/project-map/root/CONVENTIONS.md` - canonical root conventions template for generated-project atlases
- `templates/project-map/root/INTEGRATIONS.md` - canonical root integrations template for generated-project atlases
- `templates/project-map/root/WORKFLOWS.md` - canonical root workflows template for generated-project atlases
- `templates/project-map/root/TESTING.md` - canonical root testing template for generated-project atlases
- `templates/project-map/root/OPERATIONS.md` - canonical root operations template for generated-project atlases

## Update Triggers

- CLI command registration, generated workflow names, integration directories, packet/result schemas, hook events, testing workflow state, project-map freshness rules, extension/preset schemas, packaging force-includes, or Codex team runtime installation assumptions change.

## Recent Structural Changes

- The layered project-map atlas now treats `QUICK-NAV.md` as the canonical Layer 1 routing surface and includes it in canonical atlas outputs and freshness requirements.
- Layer 1 now behaves like a dictionary-style atlas entry surface with symptom routing, shared-surface hotspots, verification routes, and propagation-risk routes.
- Ordinary `sp-*` workflows now treat atlas consumption as a hard gate before source-level work, instead of a warn-only layered hint.
- The layered project-map atlas now has explicit scan packets, worker-result evidence, root/module docs, reverse coverage validation, and freshness completion.
- Testing workflow guidance now centers `sp-test-scan` and `sp-test-build`.
