# Technology Stack

**Analysis Date:** 2026-04-11

## Languages

**Primary:**
- Python 3.11+ - core CLI implementation, integration framework, extension/preset management, and Codex team runtime in `src/specify_cli/__init__.py`, `src/specify_cli/integrations/`, `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`, and `src/specify_cli/codex_team/`.

**Secondary:**
- Shell (`.sh`) - generated project helper scripts and agent-context update tooling in `scripts/bash/` and bundled via `pyproject.toml`.
- PowerShell (`.ps1`) - Windows-first helper scripts and context update tooling in `scripts/powershell/` and bundled via `pyproject.toml`.
- Markdown - command templates, docs, presets, extension guides, and generated agent assets in `templates/`, `docs/`, `extensions/`, `presets/`, and `specs/`.
- YAML/TOML/JSON - package/config/test metadata in `pyproject.toml`, `.github/workflows/*.yml`, `docs/toc.yml`, `extensions/*/extension.yml`, `presets/*/preset.yml`, and manifest/cache files written under `.specify/`.

## Runtime

**Environment:**
- CPython 3.11 or newer is required by `pyproject.toml`.
- The CLI entrypoint is `specify = "specify_cli:main"` in `pyproject.toml`.
- The Codex team runtime adds a tmux-capable backend requirement through `src/specify_cli/codex_team/runtime_bridge.py`.

**Package Manager:**
- `uv` is the expected developer and install workflow in `README.md`, `TESTING.md`, `docs/installation.md`, and `.github/workflows/test.yml`.
- Build backend: `hatchling` in `pyproject.toml`.
- Lockfile: `uv.lock` present.

## Frameworks

**Core:**
- Typer - CLI command surface and subcommands in `src/specify_cli/__init__.py`.
- Rich - terminal UI, tables, panels, and live status rendering in `src/specify_cli/__init__.py`.
- PyYAML - frontmatter parsing, manifest parsing, extension/preset config parsing, and generated-file transformations in `src/specify_cli/agents.py`, `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`, and `src/specify_cli/integrations/base.py`.

**Testing:**
- Pytest - primary runner configured in `pyproject.toml` and used across `tests/`.
- pytest-cov - optional coverage dependency declared in `pyproject.toml`.

**Build/Dev:**
- Hatchling - wheel build backend in `pyproject.toml`.
- Ruff - linting in `.github/workflows/test.yml`.
- markdownlint-cli2 - Markdown linting in `.github/workflows/lint.yml` with config in `.markdownlint-cli2.jsonc`.
- DocFX - documentation site generation in `docs/docfx.json` and `.github/workflows/docs.yml`.
- GitHub Actions - CI, release, docs deploy, stale triage, and CodeQL defined in `.github/workflows/`.

## Key Dependencies

**Critical:**
- `typer` - defines the CLI surface in `src/specify_cli/__init__.py`.
- `click>=8.1` - Typer runtime dependency declared in `pyproject.toml`.
- `rich` - required for the interactive terminal UX in `src/specify_cli/__init__.py`.
- `pyyaml>=6.0` - required for YAML manifests, frontmatter, presets, and extensions in `src/specify_cli/agents.py`, `src/specify_cli/extensions.py`, and `src/specify_cli/presets.py`.
- `pathspec>=0.12.0` - used for extension packaging/ignore behavior in `src/specify_cli/extensions.py`.
- `packaging>=23.0` - semantic version and specifier handling in `src/specify_cli/extensions.py` and `src/specify_cli/presets.py`.
- `json5>=0.13.0` - tolerant config parsing in `src/specify_cli/__init__.py`.
- `readchar` - cross-platform single-key terminal input in `src/specify_cli/__init__.py`.

**Infrastructure:**
- `platformdirs` - declared in `pyproject.toml`; used for local CLI/runtime path management in the main package surface.
- Standard library `urllib`, `zipfile`, `tempfile`, `subprocess`, and `shutil` - used heavily for downloads, archive extraction, process invocation, and packaging in `src/specify_cli/__init__.py`, `src/specify_cli/extensions.py`, and `src/specify_cli/presets.py`.

## Configuration

**Environment:**
- Python package metadata and tool config live in `pyproject.toml`.
- Agent/integration metadata is generated from `src/specify_cli/integrations/__init__.py` into `AGENT_CONFIG` in `src/specify_cli/__init__.py`.
- Extension and preset catalogs can be overridden with `SPECKIT_CATALOG_URL` and `SPECKIT_PRESET_CATALOG_URL` in `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`, and surfaced by `src/specify_cli/__init__.py`.
- Extension-specific config can be layered through `.specify/extensions/<ext-id>/<ext-id>-config.yml`, `.specify/extensions/<ext-id>/local-config.yml`, and `SPECKIT_<EXT_ID>_*` environment variables in `src/specify_cli/extensions.py`.
- Codex team backend detection reads `WSL_INTEROP`, `WSL_DISTRO_NAME`, and `MSYSTEM` in `src/specify_cli/codex_team/runtime_bridge.py`.

**Build:**
- Packaging and asset bundling are configured in `pyproject.toml`, including forced inclusion of `templates/commands`, `templates/*.md`, `scripts/bash`, and `scripts/powershell`.
- CI/CD is defined in `.github/workflows/test.yml`, `.github/workflows/lint.yml`, `.github/workflows/docs.yml`, `.github/workflows/codeql.yml`, `.github/workflows/release-trigger.yml`, and `.github/workflows/release.yml`.
- Doc site configuration lives in `docs/docfx.json`.

## Platform Requirements

**Development:**
- Python 3.11+ and `uv` are the expected baseline from `README.md` and `TESTING.md`.
- `git` is assumed by init/release/dev flows in `README.md`, `docs/local-development.md`, and `src/specify_cli/__init__.py`.
- Agent-specific CLIs or IDEs are required depending on `AGENT_CONFIG` in `src/specify_cli/__init__.py` and `src/specify_cli/integrations/`.
- Codex team runtime work requires `tmux` on Unix/WSL or `psmux` on native Windows in `src/specify_cli/codex_team/runtime_bridge.py`.

**Production:**
- Distribution target is a Python CLI package installed through `uv tool install` or `uvx`, as documented in `README.md` and `docs/installation.md`.
- Documentation publishing targets GitHub Pages via `.github/workflows/docs.yml`.
- Release automation targets GitHub Releases via `.github/workflows/release.yml` and `.github/workflows/release-trigger.yml`.

## Practical Notes

- Treat `src/specify_cli/integrations/` as the source of truth for supported AI agents. `AGENT_CONFIG` in `src/specify_cli/__init__.py` is derived from that registry, not maintained independently.
- Treat `templates/` plus the force-include rules in `pyproject.toml` as a packaged runtime asset set. Changes there affect generated projects even when the CLI runs offline.
- Use `tests/integrations/`, `tests/test_agent_config_consistency.py`, and `tests/test_presets.py` when changing agent metadata, packaging rules, or generated asset behavior.

---

*Stack analysis: 2026-04-11*
