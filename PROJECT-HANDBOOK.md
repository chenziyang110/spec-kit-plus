# Project Handbook

**Last Updated:** 2026-04-27
**Purpose:** Root navigation artifact for this repository.

## System Summary

`spec-kit-plus` is a Python-first CLI and asset-packaging repo for Spec-Driven Development. The root product is the `specify` command in `src/specify_cli/__init__.py`; it scaffolds new repos, installs agent-specific workflow surfaces, manages project-map freshness, exposes first-party workflow quality hooks, and optionally provisions the Codex-only `sp-teams` runtime.

The repo's runtime shape is a Python CLI monolith with layered subsystems: integration installers under `src/specify_cli/integrations/`, orchestration policy under `src/specify_cli/orchestration/`, delegated-execution packet/hook enforcement under `src/specify_cli/execution/` and `src/specify_cli/hooks/`, and an optional Node/Rust extension runtime under `extensions/agent-teams/engine/`. The bundled `templates/` and `scripts/` trees are product code, not documentation-only assets: changing them changes generated downstream repos.

## System Boundaries

This repository owns the `specify` CLI, its bundled templates/scripts, the integration registry for supported AI agents, and the optional Codex runtime packaging path. It coordinates with external agent CLIs, Git, uv/pip packaging, optional MCP servers, and the bundled agent-teams extension engine, but it does not own those upstream runtimes or their behavior once installed on user machines.

## High-Value Capabilities

- **Project initialization and scaffolding**: `specify init` materializes agent-specific command/skill trees plus shared `.specify/` infrastructure. Read `.specify/project-map/root/ARCHITECTURE.md` and `STRUCTURE.md`.
- **Workflow contract generation**: `templates/commands/`, `templates/command-partials/`, and `templates/passive-skills/` define the user-facing `sp-*` system. Read `.specify/project-map/root/WORKFLOWS.md` and `CONVENTIONS.md`.
- **Integration adaptation**: `src/specify_cli/integrations/` translates shared templates into Copilot, Claude, Codex, Gemini, Cursor, and other agent-specific output formats. Read `.specify/project-map/root/INTEGRATIONS.md`.
- **Atlas / freshness model**: `src/specify_cli/project_map_status.py` plus `project-map` and `hook complete-refresh` CLI surfaces govern handbook freshness and stale-area detection. Read `.specify/project-map/root/WORKFLOWS.md` and `OPERATIONS.md`.
- **Delegated execution and Codex runtime**: `src/specify_cli/execution/`, `src/specify_cli/hooks/`, and `src/specify_cli/codex_team/` encode packet contracts, hook validation, result handoff, and the `sp-teams` runtime. Read `.specify/project-map/root/ARCHITECTURE.md`, `WORKFLOWS.md`, and `OPERATIONS.md`.
- **Self-learning enforcement**: `src/specify_cli/hooks/learning.py` plus `src/specify_cli/learnings.py` turn passive project memory into `signal/review/capture/inject` learning hooks for every `sp-*` workflow. Read `.specify/project-map/root/WORKFLOWS.md`.

## How To Read This Project

- Start here for orientation.
- The handbook is the index-first entrypoint.
- Read `.specify/project-map/index/atlas-index.json` and `.specify/project-map/index/status.json` before broad brownfield work when you need the machine-readable routing and freshness layer.
- Treat the combined handbook/project-map set as the repository's atlas-style technical encyclopedia.
- The root topical project-map documents hold shared cross-module detail.
- The module project-map documents hold module-local technical truth and deeper drill-down paths.
- Use `Topic Map` to choose the next root or module document.
- Use `Where To Read Next` for task-oriented routing.
- Fall back to live code reads only when the topical coverage is missing, stale, or too broad.
- Point to the topic docs instead of duplicating deep detail when the explanation belongs in a topical file.

## Shared Surfaces

- `src/specify_cli/__init__.py`: the top-level CLI surface, subcommand registration, init flow, status renderers, and help text.
- `src/specify_cli/integrations/base.py` and `src/specify_cli/integrations/__init__.py`: shared integration contract and built-in integration registry.
- `templates/`: canonical shared workflow, project-map, passive-skill, testing, and worker-prompt assets copied into generated repos and wheels.
- `scripts/bash/` and `scripts/powershell/`: shared runtime helper layer installed into downstream repos.
- `extensions/agent-teams/engine/`: bundled Node/TypeScript plus Rust runtime for the agent-teams extension and native hook support.

## Risky Coordination Points

- `src/specify_cli/__init__.py`: large command surface; edits here can silently affect CLI help, route selection, project-map guidance, and multiple integration tests.
- `templates/commands/` and `templates/command-partials/`: one wording change propagates into all generated agent integrations and many template assertion tests.
- `src/specify_cli/integrations/base.py`: shared install logic, manifest recording, and context bootstrapping for almost every integration.
- `src/specify_cli/project_map_status.py`: determines stale vs fresh atlas state and therefore brownfield workflow gating.
- `src/specify_cli/codex_team/installer.py` plus `extensions/agent-teams/engine/`: change both the generated asset set and runtime startup assumptions.

## Change-Propagation Hotspots

- Agent registration metadata (`AGENT_CONFIG`, `INTEGRATION_REGISTRY`, per-integration config) propagates into CLI help text, inventory tests, and generated folder structures.
- Shared templates and scripts propagate into every integration install path, wheel packaging assets, and template-guidance tests.
- Result handoff, hook, and packet schema changes propagate into `execution/`, `hooks/`, `codex_team/`, generated workflow prompts, and contract tests.
- Learning hook changes propagate into `learnings.py`, `hooks/events.py`, `hooks/engine.py`, generated `sp-*` templates, README/quickstart guidance, and learning/hook tests.
- Codex team asset installation changes propagate into `.codex/config.toml`, `.specify/teams/*`, docs, and upgrade-path tests.

## Change Impact Guide

- If you are changing CLI routing, subcommands, or user-facing initialization text, read `.specify/project-map/root/ARCHITECTURE.md`, `WORKFLOWS.md`, and `README.md` first.
- If you are changing generated workflow wording or atlas contracts, read `.specify/project-map/root/WORKFLOWS.md`, `CONVENTIONS.md`, and the template tests under `tests/test_*template*`.
- If you are changing integration installers, read `.specify/project-map/root/INTEGRATIONS.md` and the relevant `tests/integrations/test_integration_*.py`.
- If you are changing Codex runtime, result handoff, or hook behavior, read `.specify/project-map/root/ARCHITECTURE.md`, `WORKFLOWS.md`, and `OPERATIONS.md`.

## Verification Entry Points

- Full repo regression: `pytest -q`
- Atlas/template contract regression: `pytest tests/test_project_handbook_templates.py tests/test_alignment_templates.py tests/test_specify_guidance_docs.py -q`
- Integration generation surface: `pytest tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q`
- Packaging sanity: `uv build`
- Agent-teams engine sanity: `npm --prefix extensions/agent-teams/engine run build`

## Known Unknowns

- The repo tracks many supported agent integrations, but their real external CLIs evolve outside this repo; generated surfaces are only as accurate as the maintained adapter assumptions.
- The `extensions/agent-teams/engine/` Rust crates and Node runtime are partially mapped here from package manifests, tests, and docs, not from a full engine-level source audit.
- The working tree is currently dirty, so this atlas describes the present working state rather than a clean tagged release.

## Low-Confidence Areas

- The deep internals of the Rust crates in `extensions/agent-teams/engine/crates/` are `Inferred` from manifests, tests, and surrounding runtime glue rather than fully traced line-by-line.
- The exact release packaging sequence in `.github/workflows/` is only lightly sampled here; operational details are strongest for local build flows and integration asset generation.
- Some `.planning/` research files are actively changing, so any architectural claims copied from them should be rechecked against current source before using them as long-lived truth.

## Atlas Views

- `index/atlas-index.json`: entry summary, module count, and next machine-readable lookup pointers.
- `index/modules.json`: module registry, owned roots, tags, and module doc paths.
- `index/relations.json`: cross-module dependencies, shared surfaces, and expansion routes.
- `index/status.json`: global freshness plus per-module freshness and `deep_stale` state.
- `root/ARCHITECTURE.md`: ownership, abstractions, dependency graph, Codex runtime, packet/hook layers.
- `root/STRUCTURE.md`: where code, templates, docs, scripts, tests, and extension assets live.
- `root/CONVENTIONS.md`: naming, compatibility, workflow, and testing conventions.
- `root/INTEGRATIONS.md`: external tools, config surfaces, packaging paths, security boundaries, and compatibility rules.
- `root/WORKFLOWS.md`: init flow, atlas refresh, delegated execution, Codex runtime lifecycle, and state transitions.
- `root/TESTING.md`: test layers, quality gates, and change-impact verification.
- `root/OPERATIONS.md`: build/run flows, state locations, troubleshooting, and recovery.
- `modules/specify-cli-core/*`: module-local truth for the primary Python CLI surface.

## Where To Read Next

- Add or modify a workflow template: `.specify/project-map/root/WORKFLOWS.md`, then `modules/specify-cli-core/WORKFLOWS.md`
- Add or change an integration: `.specify/project-map/root/INTEGRATIONS.md`, `root/STRUCTURE.md`, and `modules/specify-cli-core/STRUCTURE.md`
- Change CLI command wiring or init behavior: `.specify/project-map/root/ARCHITECTURE.md`, then `modules/specify-cli-core/OVERVIEW.md`
- Diagnose a failing test or stale runtime asset: `.specify/project-map/root/TESTING.md`, `root/OPERATIONS.md`, and `modules/specify-cli-core/TESTING.md`
- Work on Codex team runtime or hook flows: `.specify/project-map/root/WORKFLOWS.md`, `root/OPERATIONS.md`, and the runtime sections in `modules/specify-cli-core/ARCHITECTURE.md`

## Topic Map

- `.specify/project-map/index/atlas-index.json` - atlas entry summary and next lookup pointers
- `.specify/project-map/index/modules.json` - module registry, owned roots, and module doc paths
- `.specify/project-map/index/relations.json` - cross-module dependencies and shared-surface expansion routes
- `.specify/project-map/index/status.json` - freshness state for the root atlas and per-module deep coverage
- `.specify/project-map/root/ARCHITECTURE.md` - layers, abstractions, truth ownership
- `.specify/project-map/root/STRUCTURE.md` - where code lives and where to add new code
- `.specify/project-map/root/CONVENTIONS.md` - naming, imports, error handling, style
- `.specify/project-map/root/INTEGRATIONS.md` - external tools, env, runtime dependencies
- `.specify/project-map/root/WORKFLOWS.md` - user flows, maintainer flows, workflow risks
- `.specify/project-map/root/TESTING.md` - test layers and smallest meaningful checks
- `.specify/project-map/root/OPERATIONS.md` - startup, recovery, troubleshooting, operator notes
- `.specify/project-map/modules/specify-cli-core/OVERVIEW.md` - module-local routing and ownership for the main Python CLI surface
- `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md` - internal Python CLI boundaries and change propagation
- `.specify/project-map/modules/specify-cli-core/WORKFLOWS.md` - module-local CLI, workflow, and atlas flows

## Update Triggers

- Any change to CLI command registration, generated workflow names, integration directories, result packet schemas, hook events, atlas freshness rules, or Codex runtime asset installation.

## Recent Structural Changes

- The handbook/project-map system itself was upgraded from a navigation-oriented map to an atlas-style technical encyclopedia with explicit dependency, lifecycle, change-impact, observability, and failure-model coverage.
