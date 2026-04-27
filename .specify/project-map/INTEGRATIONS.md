# Integrations

**Last Updated:** 2026-04-27
**Coverage Scope:** repository-wide external and runtime dependencies
**Primary Evidence:** src/specify_cli/integrations/, src/specify_cli/codex_team/, src/specify_cli/mcp/, extensions/agent-teams/engine/, pyproject.toml, README.md, docs/installation.md
**Update When:** external services, env/config surfaces, packaging assumptions, runtime dependencies, or compatibility rules change

## External Services and Tools

- Python runtime 3.11+ and `uv`/`pip` packaging are required for the main CLI.
- Git is a hard dependency for many user flows and freshness reasoning.
- Supported external agent CLIs/IDEs include Codex, Claude, Gemini, Copilot, Cursor, Windsurf, Kimi, Forge, and others through `src/specify_cli/integrations/`.
- Optional MCP layer: `specify-teams-mcp` via `specify-cli[mcp]`.
- Optional Codex runtime backend depends on `tmux`, `node`, `npm`, `cargo`, and the bundled extension engine.

## Environment Configuration

- `--script sh|ps` chooses Bash vs PowerShell helper installation.
- `--ignore-agent-tools`, `--offline`, and `--constitution-profile` materially change init behavior.
- Runtime backend availability for Codex team is discovered from the local machine and can differ across operators.

## Configuration and Feature-Control Surfaces

- `AGENT_CONFIG` and per-integration `config`/`registrar_config` determine output folder shape, context files, and command formats.
- `CapabilitySnapshot` and orchestration policy determine whether a workflow stays local, uses native multi-agent, or escalates to a sidecar runtime.
- `.codex/config.toml` and `.specify/config.json` are generated control surfaces for Codex runtime notifications.
- Feature flags are mostly represented as CLI options, optional dependencies (`mcp` extra), and runtime capability detection rather than a central flag service.
- Hidden coupling exists between shared templates, integration augmentation code, and tested help/doc wording.

## CI/CD and Release Surfaces

- Python packaging is driven by `pyproject.toml` with wheel `force-include` for templates, scripts, and extension engine assets.
- The repo relies on GitHub Actions workflows and workflow helper scripts under `.github/workflows/` plus release-package scripts to assemble downstream artifacts.
- The extension engine has its own Node build (`npm run build`) and Rust workspace metadata (`Cargo.toml` / `Cargo.lock`).

## Runtime Dependencies

- Python package dependencies: Typer, Click, Rich, Platformdirs, Readchar, PyYAML, Packaging, Pathspec, JSON5, Pydantic AI/Graph.
- Optional `mcp` extra for MCP server support.
- `extensions/agent-teams/engine/package.json` requires Node >= 20 and depends on `@modelcontextprotocol/sdk`, `js-yaml`, `zod`, and `@iarna/toml`.

## API and Exported Surfaces

- Human CLI entrypoints: `specify`, `specify team`, `specify project-map`, `specify result`, `specify hook`, `specify learning`, `specify testing`.
- Optional MCP entrypoint: `specify-teams-mcp`.
- Generated downstream command/skill surfaces under `.claude/`, `.codex/`, `.gemini/`, `.github/`, `.myagent/`, etc.

## Protocol and Bridge Seams

- Claude native hooks are thin adapters that translate Claude hook payloads into `specify hook ...` calls.
- Worker result handoff normalizes lane-local outcomes into canonical result envelopes.
- Codex team runtime installation bridges Python CLI state and `.codex/config.toml` notify wiring to the bundled runtime engine.

## Contract Boundaries

- Integration modules own target-specific format changes; shared template content should stay integration-neutral unless a specific adapter layer augments it.
- `IntegrationManifest` is the ownership boundary for generated files. If a file is created or modified during install, it must be tracked there.
- Packet/result schemas are the boundary between leaders and delegated workers.

## Compatibility and Versioning Strategy

- The repo keeps agent names aligned with real executable names to minimize mapping shims.
- Skills-based vs Markdown/TOML-based integrations share one workflow contract but expose different filesystem layouts and invocation syntax.
- Release and upgrade behavior for Codex runtime must preserve existing projects via upgrade paths and config merges rather than destructive replacement.

## Security and Trust Boundaries

- Agent folders may contain credentials or identifying config after downstream use; docs recommend gitignore guidance for those folders.
- Hook validation is a trust boundary: prompt, read-path, and commit validation are centralized rather than duplicated in adapter scripts.
- Runtime state directories and config merge logic must not silently clobber unrelated user config.

## Toolchain, Packaging, and Runtime Invariants

- Bundled assets in `templates/`, `scripts/`, and `extensions/agent-teams/engine/` must remain wheel-includable.
- Node and Cargo are optional for core CLI use but required for the agent-teams engine build/runtime path.
- Windows offline install notes and PowerShell 7 expectations are explicit product constraints.

## Integration Risks

- Help text, templates, manifests, and tests can drift if one integration path is updated in isolation.
- External agent products may change capabilities faster than the repo updates their adapters.
- Codex runtime asset installation has higher blast radius because it touches Python, TOML config, docs, and runtime packaging at once.
