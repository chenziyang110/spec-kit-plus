# Coding Conventions

**Analysis Date:** 2026-04-11

## Naming Patterns

**Files:**
- Use `snake_case.py` for Python modules and tests. Examples: `src/specify_cli/extensions.py`, `src/specify_cli/codex_team/runtime_bridge.py`, `tests/test_extensions.py`, `tests/integrations/test_integration_codex.py`.
- Reserve `__init__.py` for package exports and package-local assembly. Examples: `src/specify_cli/__init__.py`, `src/specify_cli/integrations/__init__.py`.
- Name tests `test_<subject>.py` and group them by subsystem under `tests/`. Use subdirectories when the subsystem is large enough to justify its own fixture scope, such as `tests/integrations/`, `tests/contract/`, and `tests/codex_team/`.

**Functions:**
- Use `snake_case` for functions, helpers, and CLI callbacks. Examples: `src/specify_cli/__init__.py` defines `_build_ai_assistant_help`, `check_tool`, and `init_git_repo`; `src/specify_cli/extensions.py` defines `normalize_priority`.
- Prefix internal helpers with `_` when they are not intended as public API. Examples: `_build_agent_configs` in `src/specify_cli/agents.py`, `_render_hook_invocation` in `src/specify_cli/extensions.py`.

**Variables:**
- Use `snake_case` for local variables, fixture names, and parameters. Examples: `project_root`, `script_type`, `valid_manifest_data`, `codex_team_project_root`.
- Use `UPPER_SNAKE_CASE` for module-level constants and regex patterns. Examples: `AGENT_CONFIG` in `src/specify_cli/__init__.py`, `CORE_COMMAND_NAMES` and `EXTENSION_COMMAND_NAME_PATTERN` in `src/specify_cli/extensions.py`, `_ANSI_ESCAPE_RE` in `tests/conftest.py`.

**Types:**
- Use `PascalCase` for classes, dataclasses, and exception types. Examples: `IntegrationBase` in `src/specify_cli/integrations/base.py`, `CatalogEntry` in `src/specify_cli/extensions.py`, `RuntimeEnvironmentError` in `src/specify_cli/codex_team/runtime_bridge.py`.
- Prefer typed built-ins and `X | None` syntax over legacy `typing.Optional[...]`. Examples: `dict[str, Any] | None` and `Path | None` in `src/specify_cli/integrations/base.py`.

## Code Style

**Formatting:**
- No repo-local formatter config is detected in `pyproject.toml` or root config files. Keep formatting aligned with the existing source: 4-space indentation, double-quoted docstrings, and line wrapping near PEP 8 norms.
- Preserve long help strings and CLI option declarations in a readable vertical format, as used throughout `src/specify_cli/__init__.py`.
- Keep import groups visually separated: standard library, third-party, then local package imports. See `src/specify_cli/integrations/base.py` and `src/specify_cli/extensions.py`.

**Linting:**
- Linting is enforced in CI with Ruff via `.github/workflows/test.yml`.
- The current CI command is `uvx ruff check src/`. Match that scope when adding or refactoring production code.
- Markdown linting is enforced separately by `.github/workflows/lint.yml` with `markdownlint-cli2` across `**/*.md`, excluding `extensions/**/*.md`.

## Import Organization

**Order:**
1. Standard library imports first. Examples: `json`, `os`, `tempfile`, `Path`.
2. Third-party imports next. Examples: `pytest`, `typer`, `yaml`, `pathspec`, `rich`.
3. Local package imports last. Examples: `from specify_cli import app`, `from specify_cli.integrations.base import MarkdownIntegration`.

**Path Aliases:**
- Not used. Import through real package paths such as `specify_cli.extensions` and `specify_cli.codex_team.runtime_bridge`.
- Tests import shared helpers through normal package or test-package paths, for example `from tests.conftest import strip_ansi` in `tests/test_extensions.py`.

## Error Handling

**Patterns:**
- Raise typed domain exceptions for library and subsystem failures. Examples: `ValidationError`, `CompatibilityError`, and `ExtensionError` in `src/specify_cli/extensions.py`; runtime errors such as `RuntimeEnvironmentError` in `src/specify_cli/codex_team/runtime_bridge.py`.
- CLI entrypoints convert recoverable failures into `typer.Exit(...)` after printing user-facing messages. This is the dominant pattern in `src/specify_cli/__init__.py`.
- Validate filesystem boundaries before writing or uninstalling files. `src/specify_cli/integrations/base.py` rejects destinations outside `project_root`; `tests/integrations/test_manifest.py` locks in those traversal protections.
- Default to defensive fallback behavior when reading external or potentially corrupted state. Examples: registry loading in `src/specify_cli/extensions.py` and hook config loading in `HookExecutor.get_project_config`.

## Logging

**Framework:** `rich.console.Console` for user-facing CLI output in `src/specify_cli/__init__.py`

**Patterns:**
- Use `console.print(...)` with Rich markup instead of raw `print(...)` for CLI status, warnings, and errors in production code.
- Keep low-level modules mostly side-effect free; return structured data or raise exceptions rather than logging internally. This is the normal style in `src/specify_cli/extensions.py`, `src/specify_cli/agents.py`, and `src/specify_cli/integrations/base.py`.
- Tests assert against rendered CLI output through `CliRunner` results, sometimes stripping ANSI escapes with `tests/conftest.py:strip_ansi`.

## Comments

**When to Comment:**
- Prefer concise docstrings over inline comments. Most modules start with a summary docstring, and non-trivial classes and methods are documented similarly in `src/specify_cli/integrations/base.py`, `src/specify_cli/extensions.py`, and `src/specify_cli/agents.py`.
- Use inline comments sparingly for edge cases, compatibility notes, or rollback steps. Examples appear in `src/specify_cli/__init__.py` around CLI/tool compatibility and in `src/specify_cli/extensions.py` around corrupted registry handling.

**JSDoc/TSDoc:**
- Not applicable. This codebase uses Python docstrings.
- Follow the local style: a short summary sentence, then optional `Args:`, `Returns:`, and `Raises:` sections for non-trivial APIs. Representative examples are in `src/specify_cli/integrations/base.py` and `src/specify_cli/extensions.py`.

## Function Design

**Size:**
- Utility modules prefer medium-sized focused helpers. Large orchestration flows exist in `src/specify_cli/__init__.py`, but even there behavior is split into helper functions such as `check_tool`, `is_git_repo`, `handle_vscode_settings`, and `_resolve_installed_extension`.
- For new logic, prefer adding a dedicated helper in the owning module instead of extending already-large command bodies.

**Parameters:**
- Type annotate public helpers and methods. Existing code commonly annotates both parameters and return types, for example `rewrite_project_relative_paths(text: str) -> str` in `src/specify_cli/agents.py`.
- Prefer explicit flags over overloaded positional behavior. The CLI surface in `src/specify_cli/__init__.py` uses named Typer options extensively, and subsystem helpers mirror that clarity.

**Return Values:**
- Return structured Python data for reusable logic. Examples: dictionaries from runtime/status helpers, tuples such as `(removed, skipped)` from uninstall methods in `src/specify_cli/integrations/base.py`, and config dictionaries from registry/config manager APIs in `src/specify_cli/extensions.py`.
- Keep boolean-returning predicates narrow and predictable, for example `check_tool(...) -> bool` and `is_git_repo(...) -> bool` in `src/specify_cli/__init__.py`.

## Module Design

**Exports:**
- Keep subsystem code in dedicated modules under `src/specify_cli/` and import from those modules directly.
- `src/specify_cli/__init__.py` serves as the CLI entrypoint and broad orchestrator. Place reusable business logic in subsystem modules instead of expanding that file further when possible.
- Package `__init__.py` files are lightweight. `src/specify_cli/codex_team/__init__.py` and `src/specify_cli/integrations/__init__.py` expose registries and shared entrypoints without burying implementation details.

**Barrel Files:**
- Used sparingly. `src/specify_cli/integrations/__init__.py` and `src/specify_cli/codex_team/__init__.py` are the main barrel-style modules.
- Do not introduce broad wildcard export layers. The prevailing pattern is explicit imports from concrete modules.

## Practical Rules For New Work

- Put production Python in `src/specify_cli/<subsystem>.py` or `src/specify_cli/<subsystem>/...`, not under `tests/` or ad hoc root files.
- Match the existing import ordering and type annotation style from `src/specify_cli/extensions.py` and `src/specify_cli/integrations/base.py`.
- Use typed exceptions plus `typer.Exit` at the CLI boundary, following `src/specify_cli/__init__.py`.
- Keep path handling and file writes defensive. Reuse existing manifest and boundary-check helpers rather than hand-rolling filesystem mutations.
- When touching CLI-visible behavior, keep output testable through `typer.testing.CliRunner` and Rich-rendered strings, as shown in `tests/integrations/test_cli.py` and `tests/contract/test_codex_team_cli_surface.py`.

---

*Convention analysis: 2026-04-11*
