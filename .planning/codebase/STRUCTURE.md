# Codebase Structure

**Analysis Date:** 2026-04-11

## Directory Layout

```text
spec-kit-plus/
├── src/specify_cli/             # Python package for the CLI and runtime logic
├── tests/                       # Pytest suites for CLI, integrations, presets, extensions, and codex_team
├── templates/                   # Bundled workflow page templates and core command templates
├── scripts/                     # Bundled bash and PowerShell helper scripts copied into generated projects
├── presets/                     # Example/bundled preset packages used by the CLI
├── extensions/                  # Example/bundled extension packages used by the CLI
├── .agents/skills/              # Repo-local Codex skills for working on this repository itself
├── .github/workflows/           # CI and release automation
├── docs/                        # Supporting product and superpowers docs
├── specs/                       # Feature-spec artifacts for this repository
├── .planning/codebase/          # Generated codebase mapping output
├── pyproject.toml               # Package metadata, entry point, and pytest config
└── README.md                    # Top-level product and usage documentation
```

## Directory Purposes

**`src/specify_cli/`:**
- Purpose: Main application package.
- Contains: CLI command handlers, extension/preset managers, agent command registrar, runtime vendor helpers, and the Codex team runtime.
- Key files: `src/specify_cli/__init__.py`, `src/specify_cli/agents.py`, `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`.

**`src/specify_cli/integrations/`:**
- Purpose: Agent-specific install/uninstall adapters behind a shared abstraction.
- Contains: Base classes in `src/specify_cli/integrations/base.py`, registry wiring in `src/specify_cli/integrations/__init__.py`, manifest tracking in `src/specify_cli/integrations/manifest.py`, and one package per integration such as `src/specify_cli/integrations/copilot/` or `src/specify_cli/integrations/claude/`.
- Key files: `src/specify_cli/integrations/base.py`, `src/specify_cli/integrations/manifest.py`, `src/specify_cli/integrations/copilot/__init__.py`.

**`src/specify_cli/codex_team/`:**
- Purpose: Codex-only team/runtime subsystem.
- Contains: Session, task, worker, and tmux orchestration modules.
- Key files: `src/specify_cli/codex_team/runtime_bridge.py`, `src/specify_cli/codex_team/session_ops.py`, `src/specify_cli/codex_team/task_ops.py`, `src/specify_cli/codex_team/tmux_backend.py`.

**`templates/`:**
- Purpose: Source templates bundled into generated projects and packaged wheels.
- Contains: Core markdown templates plus `templates/commands/*.md`.
- Key files: `templates/spec-template.md`, `templates/plan-template.md`, `templates/commands/specify.md`, `templates/commands/team.md`.

**`scripts/`:**
- Purpose: Source shell helpers copied into `.specify/scripts/` during init.
- Contains: Platform-specific script implementations grouped by shell.
- Key files: `scripts/bash/update-agent-context.sh`, `scripts/powershell/update-agent-context.ps1`.

**`extensions/`:**
- Purpose: Repository-hosted extension packages for development, tests, and release packaging.
- Contains: Example extension manifests and command files.
- Key files: `extensions/selftest/extension.yml`, `extensions/template/`.

**`presets/`:**
- Purpose: Repository-hosted preset packs for development and packaging.
- Contains: Preset manifests and override templates.
- Key files: `presets/scaffold/preset.yml`, `presets/self-test/preset.yml`.

**`tests/`:**
- Purpose: Automated regression coverage.
- Contains: Root CLI tests, integration-specific tests, contract tests, and Codex runtime tests.
- Key files: `tests/test_extensions.py`, `tests/test_presets.py`, `tests/integrations/test_cli.py`, `tests/codex_team/test_runtime_bridge.py`.

**`.github/workflows/`:**
- Purpose: CI, packaging, and release automation.
- Contains: Workflow definitions and release helper scripts.
- Key files: `.github/workflows/scripts/create-release-packages.sh`, `.github/workflows/scripts/create-github-release.sh`.

## Key File Locations

**Entry Points:**
- `pyproject.toml`: Declares the `specify` console entry point and package metadata.
- `src/specify_cli/__init__.py`: Root Typer app and almost all public CLI command handlers.

**Configuration:**
- `pyproject.toml`: Packaging, optional test dependencies, and pytest/coverage defaults.
- `AGENTS.md`: Repository-specific contribution and agent-integration guidance.
- `.github/dependabot.yml`: Dependency automation policy.

**Core Logic:**
- `src/specify_cli/integrations/base.py`: Shared install behavior for agent adapters.
- `src/specify_cli/agents.py`: Shared command-rendering and agent registration logic.
- `src/specify_cli/extensions.py`: Extension installation, catalogs, and hooks.
- `src/specify_cli/presets.py`: Preset installation, catalogs, and template resolution.
- `src/specify_cli/codex_team/`: Codex runtime implementation.

**Testing:**
- `tests/integrations/`: Integration abstraction and CLI integration tests.
- `tests/codex_team/`: Codex runtime behavior tests.
- `tests/contract/`: CLI surface and generated-asset contract tests.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`, for example `src/specify_cli/extensions.py` and `src/specify_cli/codex_team/runtime_bridge.py`.
- Integration packages use Python-safe directory names when the public key contains punctuation, for example `src/specify_cli/integrations/cursor_agent/` for the `cursor-agent` key and `src/specify_cli/integrations/kiro_cli/` for `kiro-cli`.
- Tests mirror behavior domains with `test_*.py`, for example `tests/integrations/test_integration_codex.py`.

**Directories:**
- Feature subsystems live directly under `src/specify_cli/` as flat domains rather than deep nested packages.
- Per-agent integrations live under `src/specify_cli/integrations/<agent_package>/`.
- Generated project assets consistently live under `.specify/...`, for example `.specify/templates/`, `.specify/extensions/`, `.specify/presets/`, and `.specify/codex-team/`.

## Where to Add New Code

**New CLI command group:**
- Primary code: `src/specify_cli/__init__.py` if it is a small addition that matches the current command-registration style.
- Preferred extraction point for non-trivial logic: create a dedicated module under `src/specify_cli/` and keep `src/specify_cli/__init__.py` as the wiring layer.
- Tests: `tests/` at the matching domain boundary, for example `tests/test_<area>.py` or `tests/<area>/test_<behavior>.py`.

**New AI integration:**
- Implementation: `src/specify_cli/integrations/<python_safe_name>/__init__.py`.
- Shared registry wiring: `src/specify_cli/integrations/__init__.py`.
- CLI/help behavior: `src/specify_cli/__init__.py`.
- Tests: `tests/integrations/test_integration_<python_safe_name>.py`.

**New extension-management behavior:**
- Implementation: `src/specify_cli/extensions.py`.
- Sample extension fixtures: `extensions/`.
- Tests: `tests/test_extensions.py` or `tests/contract/` when the user-facing output is part of the public contract.

**New preset or template-resolution behavior:**
- Implementation: `src/specify_cli/presets.py`.
- Template assets: `templates/` for bundled defaults, `presets/` for packaged examples.
- Tests: `tests/test_presets.py`.

**New Codex runtime behavior:**
- Implementation: `src/specify_cli/codex_team/` in the narrowest existing module, or a new module there if it introduces a new runtime concern.
- CLI wiring: `src/specify_cli/__init__.py` under `team_app`.
- Tests: `tests/codex_team/` and `tests/contract/` if the CLI/API surface changes.

**Utilities shared across subsystems:**
- Shared helpers: `src/specify_cli/agents.py` for command/agent rendering concerns, or a new top-level module under `src/specify_cli/` if the concern is not agent-specific.

## Special Directories

**`.specify/`:**
- Purpose: Generated project workspace used by initialized projects and also present in this repository for self-hosting assets/config.
- Generated: Yes, in downstream projects; partially committed in this repository.
- Committed: Yes, in this repository.

**`.planning/codebase/`:**
- Purpose: Generated mapping documents consumed by GSD planning flows.
- Generated: Yes.
- Committed: Intended to be committed when refreshed.

**`.agents/skills/`:**
- Purpose: Codex skill definitions for working inside this repository.
- Generated: No.
- Committed: Yes.

**`runtime_vendor/`:**
- Purpose: Supporting runtime-related code packaged with the CLI.
- Generated: No.
- Committed: Yes.

**`specs/`:**
- Purpose: Spec-driven development artifacts for repository changes.
- Generated: Yes.
- Committed: Yes.

## Placement Guidance

- Put new reusable scaffold files in `templates/` or `scripts/`, then rely on `_install_shared_infra()` in `src/specify_cli/__init__.py` to copy them into downstream projects.
- Keep new agent-specific behavior inside the matching integration package unless it truly belongs in the shared abstraction in `src/specify_cli/integrations/base.py`.
- Route anything that persists generated-project state into `.specify/`; avoid inventing new top-level state directories when `.specify/` already models the project boundary.
- When adding alternative resolution layers or override behavior, extend `PresetResolver` in `src/specify_cli/presets.py` instead of scattering template lookup logic across command handlers.

---

*Structure analysis: 2026-04-11*
