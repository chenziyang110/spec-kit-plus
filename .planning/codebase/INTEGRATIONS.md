# External Integrations

**Analysis Date:** 2026-04-11

## APIs & External Services

**Agent Tooling:**
- Local AI agent CLIs and IDE integrations - the core product scaffolds command/skill files for agent-specific directories defined by `src/specify_cli/integrations/__init__.py` and surfaced through `AGENT_CONFIG` in `src/specify_cli/__init__.py`.
  - SDK/Client: not a Python SDK; integrations are file-based plus local executable checks in `src/specify_cli/__init__.py`.
  - Auth: none handled by this repo; each external agent authenticates through its own toolchain.
- Codex team runtime backend - local `tmux` on Unix/WSL or `psmux` on native Windows detected in `src/specify_cli/codex_team/runtime_bridge.py`.
  - SDK/Client: `shutil.which()` plus subprocess/runtime file management in `src/specify_cli/codex_team/runtime_bridge.py` and `src/specify_cli/codex_team/`.
  - Auth: none.

**Remote Catalogs and Downloads:**
- Spec Kit extension catalog - downloaded from `https://raw.githubusercontent.com/github/spec-kit/main/extensions/catalog.json` and `catalog.community.json` by `src/specify_cli/extensions.py`.
  - SDK/Client: standard-library `urllib.request` in `src/specify_cli/extensions.py`.
  - Auth: none by default; optional override via `SPECKIT_CATALOG_URL`.
- Spec Kit preset catalog - downloaded from `https://raw.githubusercontent.com/github/spec-kit/main/presets/catalog.json` and `catalog.community.json` by `src/specify_cli/presets.py`.
  - SDK/Client: standard-library `urllib.request` in `src/specify_cli/presets.py`.
  - Auth: none by default; optional override via `SPECKIT_PRESET_CATALOG_URL`.
- Extension ZIP downloads - fetched from per-extension `download_url` values with HTTPS enforcement in `src/specify_cli/extensions.py`.
  - SDK/Client: standard-library `urllib.request` and `zipfile` in `src/specify_cli/extensions.py`.
  - Auth: none in core; URLs may point to trusted public sources.
- Preset ZIP downloads - fetched from per-preset `download_url` values with HTTPS enforcement in `src/specify_cli/presets.py`.
  - SDK/Client: standard-library `urllib.request` and `zipfile` in `src/specify_cli/presets.py`.
  - Auth: none in core; install policy can block community catalogs in `src/specify_cli/presets.py`.
- Remote bootstrap/archive source - `specify init --from <url>` uses URL fetching and archive extraction in `src/specify_cli/__init__.py`.
  - SDK/Client: standard-library `urllib.request`, `tempfile`, and `zipfile` in `src/specify_cli/__init__.py`.
  - Auth: none detected in core implementation.

**GitHub Platform:**
- GitHub repository distribution - installation and one-shot execution use Git URLs from `README.md`, `docs/quickstart.md`, and `docs/upgrade.md`.
  - SDK/Client: `uv tool install` / `uvx`; repository URLs are documented rather than called through a Python SDK.
  - Auth: inherited from local Git/uv configuration when needed.
- GitHub Releases - release creation is automated in `.github/workflows/release.yml` and `.github/workflows/release-trigger.yml`.
  - SDK/Client: `gh` CLI in GitHub Actions workflows.
  - Auth: `GITHUB_TOKEN` and `RELEASE_PAT` in `.github/workflows/release.yml` and `.github/workflows/release-trigger.yml`.
- GitHub Pages - docs deployment is configured in `.github/workflows/docs.yml`.
  - SDK/Client: official GitHub Actions.
  - Auth: workflow-scoped `GITHUB_TOKEN` permissions.
- CodeQL scanning - configured in `.github/workflows/codeql.yml`.
  - SDK/Client: `github/codeql-action`.
  - Auth: workflow permissions only.

## Data Storage

**Databases:**
- None detected.
  - Connection: not applicable.
  - Client: not applicable.

**File Storage:**
- Local filesystem is the primary persistence layer.
  - Generated project assets and manifests live under `.specify/`, as managed by `src/specify_cli/__init__.py`, `src/specify_cli/integrations/manifest.py`, `src/specify_cli/extensions.py`, and `src/specify_cli/presets.py`.
  - Codex team runtime state lives under `.specify/codex-team/` per `README.md` and `src/specify_cli/codex_team/`.
  - Cached catalogs and downloaded ZIPs live under `.specify/extensions/.cache/` and `.specify/presets/.cache/` in `src/specify_cli/extensions.py` and `src/specify_cli/presets.py`.

**Caching:**
- File-based JSON cache with 1-hour TTL for extension and preset catalogs in `src/specify_cli/extensions.py` and `src/specify_cli/presets.py`.

## Authentication & Identity

**Auth Provider:**
- No centralized application auth provider detected.
  - Implementation: this CLI delegates auth to external tools and platforms rather than managing user identity itself.

## Monitoring & Observability

**Error Tracking:**
- None detected.

**Logs:**
- Human-facing terminal output uses Rich and console printing in `src/specify_cli/__init__.py`.
- Codex team runtime writes structured JSON state plus append-only event logs under `.specify/codex-team/state/` via `src/specify_cli/codex_team/events.py` and related modules.
- GitHub Actions workflow logs serve as CI/release observability in `.github/workflows/`.

## CI/CD & Deployment

**Hosting:**
- Python package distribution is oriented around Git-based install flows documented in `README.md` and `docs/installation.md`.
- Documentation is hosted on GitHub Pages via `.github/workflows/docs.yml`.

**CI Pipeline:**
- GitHub Actions is the only CI/CD system detected.
  - Test matrix and Ruff linting: `.github/workflows/test.yml`
  - Markdown linting: `.github/workflows/lint.yml`
  - Documentation deploy: `.github/workflows/docs.yml`
  - Security scanning: `.github/workflows/codeql.yml`
  - Release orchestration: `.github/workflows/release-trigger.yml` and `.github/workflows/release.yml`

## Environment Configuration

**Required env vars:**
- `SPECKIT_CATALOG_URL` - optional override for the extension catalog source in `src/specify_cli/extensions.py`.
- `SPECKIT_PRESET_CATALOG_URL` - optional override for the preset catalog source in `src/specify_cli/presets.py`.
- `SPECKIT_<EXT_ID>_*` - extension-specific config injection in `src/specify_cli/extensions.py`.
- `WSL_INTEROP`, `WSL_DISTRO_NAME`, `MSYSTEM` - environment detection for Codex team runtime backend selection in `src/specify_cli/codex_team/runtime_bridge.py`.
- `GITHUB_TOKEN` and `RELEASE_PAT` - GitHub Actions secrets referenced in `.github/workflows/release.yml` and `.github/workflows/release-trigger.yml`.

**Secrets location:**
- CI secrets are referenced through GitHub Actions secrets in `.github/workflows/release.yml` and `.github/workflows/release-trigger.yml`.
- Local agent credentials are not stored or managed by this repository; they remain external to the codebase.

## Webhooks & Callbacks

**Incoming:**
- None detected.

**Outgoing:**
- HTTPS catalog fetches and ZIP downloads to configured extension/preset sources in `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`, and `src/specify_cli/__init__.py`.
- GitHub API operations through the `gh` CLI inside release workflows in `.github/workflows/release.yml` and `.github/workflows/release-trigger.yml`.

## Integration Constraints

- Catalog and download URLs are explicitly restricted to HTTPS, with localhost-only HTTP exceptions, in `src/specify_cli/extensions.py` and `src/specify_cli/presets.py`.
- Community catalogs are discoverable but not always installable; install policy is encoded per catalog entry in `src/specify_cli/extensions.py` and `src/specify_cli/presets.py`.
- Agent integrations are mostly local filesystem contracts plus executable availability checks. Adding a new agent usually means updating `src/specify_cli/integrations/`, generated context scripts in `scripts/bash/update-agent-context.sh` and `scripts/powershell/update-agent-context.ps1`, and release workflows under `.github/workflows/`.
- The Codex team runtime is intentionally isolated to Codex projects, with runtime files living only under `.specify/codex-team/` as described in `README.md` and implemented in `src/specify_cli/codex_team/`.

---

*Integration audit: 2026-04-11*
