# Integrations

**Last Updated:** 2026-04-19
**Coverage Scope:** repository-wide external and runtime dependencies
**Primary Evidence:** src/, scripts/, CI config, docs
**Update When:** external services, env configuration, CI/CD assumptions, or runtime dependencies change

## External Services and Tools

- Git for repository state and branch-based workflow behavior.
- `uv`/Python runtime for CLI execution and packaging.
- Agent CLIs/IDEs depending on selected integration (Codex, Claude, Gemini,
  Cursor, Windsurf, Kimi, Forge, etc.).
- Optional runtime backend requirements for Codex team workflows (tmux-capable
  environment).

## Environment Configuration

- Agent/tool availability is checked via CLI checks and setup logic.
- Generated projects track integration/init state in `.specify` metadata files.
- Scripts under `scripts/bash/` and `scripts/powershell/` provide platform-aware
  helper operations.

## CI/CD and Release Surfaces

- Packaging and release scripts under `.github/workflows/scripts/` build
  integration-specific artifacts.
- Test suites enforce template inventories, integration behavior, and docs
  guidance consistency.

## Runtime Dependencies

- Core runtime dependencies are Python modules in `src/specify_cli/`.
- Integration dependencies are mostly file generation contracts rather than
  runtime network clients.
- Codex runtime features in `src/specify_cli/codex_team/` depend on local
  runtime state directories and backend process support.

## Integration Risks

- Divergence between `AGENT_CONFIG`, docs tables, and tests can break init flows.
- Template changes without mirror/test updates can create contract drift.
- Integration-specific behavior should stay isolated unless intentionally shared
  to all supported CLIs.
