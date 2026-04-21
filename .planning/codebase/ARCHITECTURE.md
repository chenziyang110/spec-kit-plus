# Architecture

**Analysis Date:** 2026-04-11

## Pattern Overview

**Overall:** Typer-based CLI application with a registry-driven integration layer, asset-bundling scaffold pipeline, and optional plugin-style extension, preset, and Codex runtime subsystems.

**Key Characteristics:**
- The primary CLI surface is centralized in `src/specify_cli/__init__.py`, which owns command registration, interactive setup flow, and shared project helpers.
- AI-agent support is modularized behind `IntegrationBase` subclasses in `src/specify_cli/integrations/`, with a single runtime registry in `src/specify_cli/integrations/__init__.py`.
- Project customization is layered rather than hard-coded: presets override templates through `src/specify_cli/presets.py`, extensions register commands/hooks through `src/specify_cli/extensions.py`, and generated project state lives under `.specify/`.

## Layers

**CLI Surface Layer:**
- Purpose: Expose the public `specify` command tree and orchestrate user-facing workflows.
- Location: `src/specify_cli/__init__.py`
- Contains: The root `app = typer.Typer(...)`, `team_app`, `extension_app`, `preset_app`, `integration_app`, `init`, `check`, and all subcommand handlers.
- Depends on: `src/specify_cli/integrations/`, `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`, `src/specify_cli/codex_team/`, `src/specify_cli/agents.py`.
- Used by: The console script entry point in `pyproject.toml` (`specify = "specify_cli:main"`).

**Integration Layer:**
- Purpose: Install and remove agent-specific command/skill files and helper scripts.
- Location: `src/specify_cli/integrations/base.py`, `src/specify_cli/integrations/manifest.py`, `src/specify_cli/integrations/__init__.py`, and one subpackage per agent such as `src/specify_cli/integrations/claude/__init__.py` and `src/specify_cli/integrations/copilot/__init__.py`.
- Contains: Abstract install/uninstall primitives, manifest tracking, template processing, and concrete integrations with per-agent folder/format metadata.
- Depends on: Bundled assets from `templates/` and `scripts/`, plus shared path rewriting from `src/specify_cli/agents.py`.
- Used by: `init`, `specify integration install`, `specify integration uninstall`, and `specify integration switch` in `src/specify_cli/__init__.py`.

**Shared Asset Layer:**
- Purpose: Provide scaffold templates and scripts that are copied into generated projects.
- Location: `templates/`, `scripts/bash/`, `scripts/powershell/`, wheel bundle definitions in `pyproject.toml`, and installer helpers such as `_install_shared_infra()` in `src/specify_cli/__init__.py`.
- Contains: Core workflow templates, command templates, VS Code settings, and shell/PowerShell helper scripts.
- Depends on: Packaging configuration in `pyproject.toml`.
- Used by: Integration setup, preset resolution, and generated `.specify/` project trees.

**Extension Layer:**
- Purpose: Install extension packages that add namespaced commands, hooks, and optional skill mirrors.
- Location: `src/specify_cli/extensions.py`
- Contains: `ExtensionManifest`, `ExtensionRegistry`, `ExtensionManager`, `ExtensionCatalog`, `HookExecutor`, and compatibility/conflict validation.
- Depends on: `src/specify_cli/agents.py` for command registration and `.specify/extensions.yml` for hook state.
- Used by: `specify extension *` and extension-aware preset resolution in `src/specify_cli/presets.py`.

**Preset Layer:**
- Purpose: Install versioned template packs and resolve the active template source by priority.
- Location: `src/specify_cli/presets.py`
- Contains: `PresetManifest`, `PresetRegistry`, `PresetManager`, `PresetCatalog`, and `PresetResolver`.
- Depends on: `.specify/presets/`, `.specify/templates/`, `.specify/extensions/`, and `src/specify_cli/agents.py`.
- Used by: `specify preset *`, `specify init --preset`, and any future template lookup that needs `PresetResolver`.

**Codex Team Runtime Layer:**
- Purpose: Support the Codex-only runtime and `specify team` operational surface.
- Location: `src/specify_cli/codex_team/`
- Contains: Runtime state schemas, session/task/worker operations, tmux bridging, runtime bootstrapping, and helper asset installation.
- Depends on: `.specify/codex-team/` project state, `tmux`, and the CLI surface in `src/specify_cli/__init__.py`.
- Used by: `specify team *` commands and Codex integration install hooks via `_install_codex_team_assets_if_needed()` in `src/specify_cli/__init__.py`.

## Data Flow

**Project Initialization Flow:**

1. `pyproject.toml` routes `specify` to `specify_cli:main`, which invokes the Typer app in `src/specify_cli/__init__.py`.
2. `init()` in `src/specify_cli/__init__.py` resolves the selected integration through `get_integration()` from `src/specify_cli/integrations/__init__.py`.
3. The integration writes agent-specific commands/skills and helper scripts, tracked by `IntegrationManifest` in `src/specify_cli/integrations/manifest.py`.
4. `_install_shared_infra()` in `src/specify_cli/__init__.py` copies bundled templates and scripts into `.specify/`, then `save_init_options()` and `_write_integration_json()` persist the selected mode.
5. Optional preset installation flows through `PresetManager.install_from_directory()` or `PresetManager.install_from_zip()` in `src/specify_cli/presets.py`.

**Extension and Preset Resolution Flow:**

1. Extension installation runs through `ExtensionManager.install_from_directory()` or `ExtensionManager.install_from_zip()` in `src/specify_cli/extensions.py`.
2. Command overrides are registered into detected agent directories through `CommandRegistrar` in `src/specify_cli/agents.py`; hooks are written into `.specify/extensions.yml` by `HookExecutor`.
3. Preset installation runs through `PresetManager` in `src/specify_cli/presets.py`, which can also register command overrides and skill overrides.
4. `PresetResolver.resolve()` in `src/specify_cli/presets.py` applies a stable lookup stack: `.specify/templates/overrides/` -> `.specify/presets/<id>/` -> `.specify/extensions/<id>/templates/` -> `.specify/templates/`.

**Codex Team Runtime Flow:**

1. `team_app` in `src/specify_cli/__init__.py` gates all runtime commands through `_require_codex_team_project()`.
2. Session lifecycle operations fan into `src/specify_cli/codex_team/session_ops.py`, `task_ops.py`, `worker_ops.py`, and `runtime_bridge.py`.
3. Runtime state is serialized under `.specify/codex-team/` using helpers from `src/specify_cli/codex_team/state_paths.py`, `runtime_state.py`, and `manifests.py`.
4. Runtime execution and worker orchestration bridge out to tmux via `src/specify_cli/codex_team/tmux_backend.py` and `worker_bootstrap.py`.

**State Management:**
- CLI configuration state is persisted in `.specify/init-options.json` by `save_init_options()` in `src/specify_cli/__init__.py`.
- Active integration metadata is stored in `.specify/integration.json` by `_write_integration_json()` in `src/specify_cli/__init__.py`.
- Integration install state is hash-tracked per integration manifest via `src/specify_cli/integrations/manifest.py`.
- Extension and preset registries live in `.specify/extensions/.registry` and `.specify/presets/.registry`, managed by `ExtensionRegistry` in `src/specify_cli/extensions.py` and `PresetRegistry` in `src/specify_cli/presets.py`.

## Key Abstractions

**Integration Registry:**
- Purpose: Make the supported AI-agent surface discoverable from a single source of truth.
- Examples: `INTEGRATION_REGISTRY` and `_register_builtins()` in `src/specify_cli/integrations/__init__.py`; `AGENT_CONFIG = _build_agent_config()` in `src/specify_cli/__init__.py`.
- Pattern: Registry + subclass metadata.

**Manifest-Tracked Installation:**
- Purpose: Allow safe uninstall and switch operations without blindly deleting user-modified files.
- Examples: `IntegrationManifest` in `src/specify_cli/integrations/manifest.py`; extension/preset registries in `src/specify_cli/extensions.py` and `src/specify_cli/presets.py`.
- Pattern: Write-time hashing plus later reconciliation.

**Command Registration Boundary:**
- Purpose: Convert shared command templates or extension/preset overrides into agent-specific filesystem outputs.
- Examples: `CommandRegistrar` in `src/specify_cli/agents.py`; `process_template()` in `src/specify_cli/integrations/base.py`.
- Pattern: Format adapter with path-rewrite normalization.

**Template Resolution Stack:**
- Purpose: Let local overrides, presets, extensions, and bundled defaults coexist predictably.
- Examples: `PresetResolver.resolve()` and `PresetResolver.resolve_with_source()` in `src/specify_cli/presets.py`.
- Pattern: Ordered lookup chain by priority, then stable source attribution.

**Hook Execution Contract:**
- Purpose: Let extensions attach follow-up actions to workflow events without embedding those decisions into core commands.
- Examples: `HookExecutor.register_hooks()`, `HookExecutor.check_hooks_for_event()`, and `HookExecutor.format_hook_message()` in `src/specify_cli/extensions.py`.
- Pattern: Declarative config + deferred execution by the AI agent.

## Entry Points

**Console Script:**
- Location: `pyproject.toml`
- Triggers: User runs `specify`.
- Responsibilities: Invoke `specify_cli:main`.

**Root CLI App:**
- Location: `src/specify_cli/__init__.py`
- Triggers: `main()` calling `app()`.
- Responsibilities: Register top-level commands, create subcommand groups, and route all public CLI traffic.

**Initialization Command:**
- Location: `src/specify_cli/__init__.py`
- Triggers: `specify init ...`
- Responsibilities: Validate inputs, resolve integration, scaffold `.specify/`, initialize git, persist init state, and optionally install a preset.

**Integration Commands:**
- Location: `src/specify_cli/__init__.py`
- Triggers: `specify integration list|install|uninstall|switch`
- Responsibilities: Operate on `IntegrationBase` implementations and their manifests.

**Extension Commands:**
- Location: `src/specify_cli/__init__.py`
- Triggers: `specify extension ...` and `specify extension catalog ...`
- Responsibilities: Manage install/remove/update lifecycles and catalog configuration through `src/specify_cli/extensions.py`.

**Preset Commands:**
- Location: `src/specify_cli/__init__.py`
- Triggers: `specify preset ...` and `specify preset catalog ...`
- Responsibilities: Manage preset catalogs, install/remove preset packs, and inspect template resolution behavior through `src/specify_cli/presets.py`.

**Codex Team Commands:**
- Location: `src/specify_cli/__init__.py`
- Triggers: `specify team ...`
- Responsibilities: Operate the Codex-only runtime through `src/specify_cli/codex_team/`.

## Error Handling

**Strategy:** Validate early, raise domain exceptions inside subsystems, and convert user-facing failures to `typer.Exit` at the CLI edge.

**Patterns:**
- Input and environment validation happen before mutations, for example CLI option checks in `init()` within `src/specify_cli/__init__.py`, ZIP path validation in `ExtensionManager.install_from_zip()` in `src/specify_cli/extensions.py`, and preset ZIP validation in `PresetManager.install_from_zip()` in `src/specify_cli/presets.py`.
- Install/switch operations attempt rollback on partial failure, for example `integration_install()` and `integration_switch()` in `src/specify_cli/__init__.py`.
- Uninstall paths preserve modified files instead of deleting them when hashes drift, via `IntegrationManifest.uninstall()` in `src/specify_cli/integrations/manifest.py`.

## Cross-Cutting Concerns

**Logging:** Rich console output is centralized in `src/specify_cli/__init__.py`; warning-style operational logging appears in helpers such as `_install_shared_infra()` in `src/specify_cli/__init__.py` and `_merge_vscode_settings()` in `src/specify_cli/integrations/copilot/__init__.py`.

**Validation:** Manifest schema checks are explicit in `ExtensionManifest` in `src/specify_cli/extensions.py` and `PresetManifest` in `src/specify_cli/presets.py`; integration destination paths are bounded to the project root in `src/specify_cli/integrations/base.py`.

**Authentication:** No first-party auth service exists in the application. External access is constrained instead by CLI-tool presence checks in `check_tool()` and `init()` in `src/specify_cli/__init__.py`, plus HTTPS-only catalog/install policies in `src/specify_cli/extensions.py` and `src/specify_cli/presets.py`.

---

*Architecture analysis: 2026-04-11*
