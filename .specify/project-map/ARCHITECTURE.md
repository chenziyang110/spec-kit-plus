# Architecture

**Last Updated:** 2026-04-27
**Coverage Scope:** repository-wide conceptual architecture
**Primary Evidence:** src/specify_cli/__init__.py, src/specify_cli/integrations/, src/specify_cli/orchestration/, src/specify_cli/codex_team/, src/specify_cli/execution/, src/specify_cli/hooks/, README.md
**Update When:** layers, abstractions, boundaries, truth ownership, or runtime surfaces change

## Pattern Overview

The repo is a Python CLI monolith with embedded asset packs and optional sidecar runtimes. `src/specify_cli/__init__.py` hosts the top-level Typer app, command registration, init flow, and many operator-facing subcommands. Surrounding packages provide narrower responsibilities: integrations install agent-specific scaffolds, orchestration chooses execution strategy, execution compiles worker packets, hooks validate workflow state, and `codex_team/` manages the Codex-only runtime path.

The extension runtime under `extensions/agent-teams/engine/` is a separate Node/TypeScript plus Rust workspace that is bundled alongside the Python package. That engine is a downstream execution surface, not the primary CLI entrypoint.

## High-Value Capabilities

- Initialize repositories and copy canonical templates/scripts into agent-specific layouts.
- Maintain a registry of supported AI agent integrations and their output conventions.
- Encode brownfield atlas freshness and workflow quality guardrails.
- Compile worker task packets, validate delegated results, and manage hook-driven workflow checkpoints.
- Install and operate the Codex-only `specify team` runtime surface.

## Layers

- **CLI surface**: `src/specify_cli/__init__.py`, `__main__.py`
- **Integration adaptation**: `src/specify_cli/integrations/`
- **Orchestration policy**: `src/specify_cli/orchestration/`
- **Delegated execution contracts**: `src/specify_cli/execution/`
- **Workflow quality hooks**: `src/specify_cli/hooks/`
- **Project memory / atlas freshness / testing inventory**: `learnings.py`, `learning_aggregate.py`, `project_map_status.py`, `testing_inventory.py`, `verification.py`
- **Codex runtime**: `src/specify_cli/codex_team/` plus `extensions/agent-teams/engine/`

## Core Abstractions

- `IntegrationBase`, `MarkdownIntegration`, `TomlIntegration`, `SkillsIntegration` in `src/specify_cli/integrations/base.py`
- `IntegrationManifest` in `src/specify_cli/integrations/manifest.py`
- `CapabilitySnapshot`, `ExecutionDecision`, and review/batch policy models in `src/specify_cli/orchestration/models.py`
- `WorkerTaskPacket` and related packet/result schemas in `src/specify_cli/execution/packet_schema.py`
- `ProjectMapStatus` in `src/specify_cli/project_map_status.py`

## Key Components and Responsibilities

- `src/specify_cli/__init__.py`: main CLI composition, init flow, quick/debug/testing/project-map/result/hook/learning command surfaces.
- `src/specify_cli/integrations/__init__.py`: registry and built-in integration registration.
- `src/specify_cli/integrations/base.py`: shared install/copy/manifest/context-bootstrapping behavior.
- `src/specify_cli/orchestration/policy.py`: strategy selection (`single-lane`, `native-multi-agent`, `sidecar-runtime`) and review-gate policy.
- `src/specify_cli/execution/packet_compiler.py`: compiles task-level context into rule-carrying worker packets.
- `src/specify_cli/hooks/engine.py`: canonical event dispatcher for workflow quality hooks.
- `src/specify_cli/hooks/learning.py`: product-level learning signal, review, capture, and injection hooks for cross-`sp-*` self-learning.
- `src/specify_cli/project_map_status.py`: project-map status contract, path classification, and stale-area reasoning.
- `src/specify_cli/codex_team/installer.py`: installs Codex runtime assets and `.codex/config.toml` notify hooks.

### Capability: Project Initialization and Shared Asset Installation

- Purpose: Materialize a Spec Kit Plus project with shared templates, scripts, memory files, integration-specific command surfaces, and init metadata.
- Owner: `src/specify_cli/__init__.py`, `src/specify_cli/integrations/base.py`
- Truth lives: `src/specify_cli/__init__.py`, `templates/`, `scripts/`, `src/specify_cli/integrations/*`
- Entry points: `specify init`, `specify integrate`, per-integration `setup()`
- Upstream inputs: CLI flags, `AGENT_CONFIG`, integration registry, bundled templates, script type selection
- Downstream consumers: initialized project worktrees, generated agent commands/skills, manifest tests, documentation
- Extend here: add integration-specific behavior in `src/specify_cli/integrations/<name>/__init__.py`; add shared assets in `templates/` and `scripts/`
- Do not extend here: do not hardcode agent-specific folder logic in unrelated CLI branches when the integration base class can own it
- Key contracts: manifest file recording, deterministic output directories, context-file bootstrapping, UTF-8 file writes
- Change propagation: changing shared templates/scripts affects every integration and many inventory/guidance tests
- Minimum verification: integration inventory tests plus `pytest tests/integrations/test_cli.py -q`
- Failure modes: missing bundled assets, manifest drift, wrong commands subdir, stale help text
- Confidence: Verified

### Capability: Integration Registry and Format Adaptation

- Purpose: Translate the shared workflow contract into multiple agent-specific file layouts, frontmatter formats, and context-file conventions.
- Owner: `src/specify_cli/integrations/`
- Truth lives: `src/specify_cli/integrations/__init__.py`, `src/specify_cli/integrations/base.py`, per-integration modules
- Entry points: `get_integration()`, `_register_builtins()`, `specify init --ai ...`, `specify init --integration ...`
- Upstream inputs: shared command templates, integration config, optional parsed options like `--commands-dir` and `--skills`
- Downstream consumers: `.claude/skills`, `.codex/skills`, `.gemini/commands`, `.github/agents`, `.myagent/commands`, etc.
- Extend here: add a new integration module and register it; override augmentation hooks when a target needs custom frontmatter or extra assets
- Do not extend here: avoid scattering agent-specific filename rules outside the integration layer
- Key contracts: actual CLI tool names as registry keys, registrar config shape, context file path, inventory parity
- Change propagation: one change can invalidate multiple integration tests and CLI help output
- Minimum verification: targeted `tests/integrations/test_integration_<name>.py`
- Failure modes: duplicate keys, wrong folder names, unprocessed placeholders, inventory drift
- Confidence: Verified

### Capability: Workflow Guardrails, Atlas Freshness, and Delegated Execution Contracts

- Purpose: Keep brownfield workflow context honest through project-map freshness, packet compilation, result validation, and hook-driven gates.
- Owner: `src/specify_cli/project_map_status.py`, `src/specify_cli/execution/`, `src/specify_cli/hooks/`
- Truth lives: `src/specify_cli/project_map_status.py`, `src/specify_cli/execution/packet_compiler.py`, `src/specify_cli/hooks/engine.py`
- Entry points: `specify project-map ...`, `specify hook ...`, `specify result ...`, packet compile/validate helpers
- Upstream inputs: project files under `.specify/`, `plan.md`, `tasks.md`, status JSON, hook payloads
- Downstream consumers: generated workflows, runtime hook adapters, delegated workers, tests
- Extend here: add new hook events and validators in `src/specify_cli/hooks/`; add packet schema evolution in `src/specify_cli/execution/`
- Do not extend here: do not bypass the canonical hook event registry or invent parallel freshness semantics in templates
- Key contracts: `ProjectMapStatus`, `WorkerTaskPacket`, hook event names, result envelope schema
- Change propagation: affects `sp-*` prompt contracts, hook adapters, result submission, and project-map checks
- Minimum verification: `pytest tests/hooks tests/execution tests/test_project_map_status.py -q`
- Failure modes: stale atlas gating false positives/negatives, packet drift, hook event mismatch, invalid result normalization
- Confidence: Verified

### Capability: Cross-Workflow Self-Learning Enforcement

- Purpose: Convert workflow friction into reusable project learning instead of relying on agent memory or end-of-chat discipline.
- Owner: `src/specify_cli/learnings.py`, `src/specify_cli/hooks/learning.py`, generated `sp-*` templates
- Truth lives: `src/specify_cli/learnings.py` for memory schema and capture, `src/specify_cli/hooks/events.py` and `hooks/learning.py` for enforcement events
- Entry points: `specify learning ...`, `specify hook signal-learning`, `review-learning`, `capture-learning`, `inject-learning`
- Upstream inputs: workflow state files, retry/validation/route-change counts, false starts, rejected paths, decisive signals, injection targets
- Downstream consumers: `.planning/learnings/candidates.md`, `.specify/memory/project-learnings.md`, generated workflow closeout gates, README/quickstart guidance
- Extend here: add learning taxonomy or structured fields in `learnings.py`; add hook event behavior in `hooks/learning.py`; update all generated workflow templates together
- Do not extend here: do not add one-off learning prompts to a single `sp-*` command when the pattern should be enforced through shared hooks
- Key contracts: learning type taxonomy, `LearningEntry` payload, `workflow.learning.signal/review/capture/inject`, terminal review gate semantics
- Change propagation: affects `sp-*` prompts, learning aggregate behavior, hook CLI contract tests, and passive skill guidance
- Minimum verification: `pytest tests/hooks/test_learning_hooks.py tests/test_learning_cli.py tests/test_alignment_templates.py -q`
- Failure modes: noisy pain-score warnings, skipped review gates, malformed candidate payloads, injection targets that never reach the future workflow that should prevent recurrence
- Confidence: Verified

### Capability: Codex Team Runtime Packaging and Runtime Surface

- Purpose: Install, describe, and operate the Codex-only `specify team` runtime including optional MCP facade wiring.
- Owner: `src/specify_cli/codex_team/`, `extensions/agent-teams/engine/`
- Truth lives: `src/specify_cli/codex_team/installer.py`, `src/specify_cli/codex_team/runtime_bridge.py`, `extensions/agent-teams/engine/package.json`
- Entry points: `specify team ...`, `upgrade_existing_codex_project()`, generated `sp-team`, optional `specify-teams-mcp`
- Upstream inputs: integration key, tmux/node/npm/cargo availability, `.codex/config.toml`, runtime state paths
- Downstream consumers: Codex-generated projects, runtime state under `.specify/codex-team/`, tests, docs
- Extend here: `src/specify_cli/codex_team/` for Python-side runtime logic; `extensions/agent-teams/engine/` for engine behavior
- Do not extend here: do not model Codex runtime assumptions in generic integration codepaths
- Key contracts: `.specify/codex-team/runtime.json`, `.specify/config.json`, `.codex/config.toml` notify wiring, result templates, CLI API surface
- Change propagation: touches install inventories, upgrade tests, docs, runtime behavior, and MCP compatibility
- Minimum verification: `pytest tests/codex_team tests/contract/test_codex_team_* -q`
- Failure modes: runtime backend detection failures, config merge drift, stale worktree sync assumptions, missing MCP extra
- Confidence: Verified

## Dependency Graph and Coupling Hotspots

- `__init__.py` depends on nearly every subsystem for CLI composition; it is the highest blast-radius file.
- Integration modules depend on shared templates and scripts; inventory tests and generated assets form a strong consumer graph from `templates/` and `scripts/` outward.
- `project_map_status.py` feeds `project-map` commands, hooks, docs, and brownfield workflow gating.
- `execution/` and `hooks/` are mutually coupled by worker packet and validation semantics even when they do not import each other directly.
- `learnings.py` and `hooks/learning.py` are intentionally coupled through lazy imports so self-learning hooks can write candidates without creating hook package import cycles.
- `codex_team/` depends on orchestration models, manifests, runtime state, and external tool availability; changes here propagate into docs and CLI expectations quickly.

## Main Flows

- **Init flow**: CLI args -> integration resolution -> shared infra install -> context file bootstrap -> manifest write -> next-step help.
- **Brownfield atlas flow**: repo evidence -> handbook/project-map docs -> status.json baseline -> later workflow preflight / check decisions.
- **Delegated execution flow**: plan/tasks/context -> `compile_worker_task_packet()` -> validate packet -> dispatch runtime/native lane -> submit normalized result -> validate result -> leader join point.
- **Codex team flow**: install runtime assets -> `specify team` runtime status/doctor/watch -> runtime bridge dispatch -> state JSON updates -> result handoff / sync-back.

## Change Propagation Paths

- Editing `templates/commands/*.md` propagates into generated surfaces across Markdown, TOML, and skills integrations, plus many template assertion tests.
- Editing `src/specify_cli/integrations/base.py` propagates into almost every integration inventory and setup test.
- Editing `src/specify_cli/project_map_status.py` propagates into project-map CLI, hooks, atlas docs, and stale/fresh expectations in tests.
- Editing `extensions/agent-teams/engine/` propagates into Codex runtime docs, packaging assets, and engine-specific build/test commands.

## Internal Boundaries and Critical Seams

- Integration-specific formatting belongs in per-integration modules; shared path resolution and copy logic belong in the base classes.
- Hook events are centralized in `src/specify_cli/hooks/events.py`; adapters should translate into those names rather than inventing parallel semantics.
- Learning capture belongs in `src/specify_cli/learnings.py` and `src/specify_cli/hooks/learning.py`; generated templates should call the shared hook surface rather than inventing local closeout prompts.
- The extension engine is a bundled sidecar, not a replacement CLI surface; human/operator entry remains `specify team`.
- `templates/` is product behavior. Treat changes there with the same care as Python runtime code.

## Ownership and Truth Map

- CLI truth: `src/specify_cli/__init__.py`
- Integration registry truth: `src/specify_cli/integrations/__init__.py`
- Shared installation contract truth: `src/specify_cli/integrations/base.py`
- Atlas freshness truth: `src/specify_cli/project_map_status.py`
- Hook event truth: `src/specify_cli/hooks/events.py` + `hooks/engine.py`
- Learning memory truth: `src/specify_cli/learnings.py` + `src/specify_cli/hooks/learning.py`
- Worker packet truth: `src/specify_cli/execution/packet_schema.py` and `packet_compiler.py`
- Codex runtime asset truth: `src/specify_cli/codex_team/installer.py`

## Truth Ownership and Boundaries

- Do not infer project-map topic names from ad hoc strings; use `TOPIC_FILES`.
- Do not create integration metadata outside the integration registry and config contracts.
- Do not bypass manifest recording when writing generated files.
- Do not treat documentation-only files in `templates/` as safe to change without regeneration tests; they are consumed as install-time product assets.

## Decision and Evolution Links

- `docs/superpowers/specs/2026-04-18-project-handbook-navigation-system-design.md`: handbook/project-map split.
- `docs/superpowers/specs/2026-04-23-project-learning-layer-design.md`: passive learning layer.
- `docs/superpowers/specs/2026-04-23-rule-carrying-task-execution-design.md`: worker packet / delegated execution contract.
- `docs/superpowers/specs/2026-04-11-codex-team-runtime-state-design.md` and later Codex team plans/specs: runtime surface evolution.

## Cross-Cutting Concerns

- Deterministic file generation and manifest tracking
- Cross-agent contract parity from one shared template base
- Brownfield safety via atlas freshness and hook gates
- Delegated execution honesty via packet/result validation
- Local/offline packaging by force-including core assets into the wheel

## Known Architectural Unknowns

- The future boundary between Python-side orchestration and Node/Rust engine runtime is still evolving.
- Some large entrypoint modules remain intentionally centralized for product ergonomics, so exact decomposition plans are still a moving target.
