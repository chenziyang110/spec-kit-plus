# Integrations

**Last Updated:** 2026-04-30
**Coverage Scope:** Agent adapters, external tools, MCP/runtime seams, extension/preset catalogs, packaging boundaries, and trust boundaries.
**Primary Evidence:** `worker-results/integrations-generated-surfaces.json`, `codex-team-runtime.json`, `packaging-release-config.json`.
**Update When:** Supported agents, adapter transforms, MCP surfaces, external runtime assumptions, extension/preset catalogs, or packaging assets change.

## API and Exported Surfaces

- Python console scripts: `specify` and `specify-teams-mcp`.
- Main CLI app: `src/specify_cli/__init__.py`.
- Agent integration registry: `src/specify_cli/integrations/INTEGRATION_REGISTRY`.
- Teams MCP facade: `src/specify_cli/mcp/teams_server.py`.
- Extension/preset managers: `src/specify_cli/extensions.py` and `src/specify_cli/presets.py`.

## Supported Agent Integration Families

- Markdown command integrations: Amp, Auggie, Bob, CodeBuddy, Cursor Agent, Forge, Generic, iFlow, Junie, Kilo Code, Kiro CLI, opencode, Pi, Qoder CLI, Qwen, Roo, SHAI, Trae, Vibe, Windsurf, and similar standard adapters.
- TOML integrations: Gemini and Tabnine.
- Skills integrations: Codex, Claude, Kimi, Antigravity.
- Custom integration: Copilot writes `.agent.md` files, companion `.prompt.md` files, and VS Code settings.
- Custom integration: Forge replaces `$ARGUMENTS`, strips incompatible `handoffs`, and injects `name` frontmatter.

## Protocol and Bridge Seams

- Shared templates are transformed through `IntegrationBase.process_template` and concrete setup methods.
- Generated update-context scripts maintain agent context/instructions blocks.
- Codex team notify hooks use `.codex/config.toml` `notify` configuration and optional `specify-teams-mcp` registration.
- `specify-teams-mcp` exposes agent-facing MCP tools for teams status, doctor, live probe, task listing, auto dispatch, batch completion, result submission, and result templates.
- Codex team runtime bridges Python dispatch/result records and the bundled engine's runtime CLI/state model.

## Toolchain, Packaging, and Runtime Invariants

- Python requires 3.11+.
- Python packaging uses Hatchling and force-includes templates, scripts, project-map/testing assets, passive skills, worker prompts, and engine source/assets.
- The bundled engine requires Node >=20 for TypeScript build/runtime paths.
- The Rust workspace is under `extensions/agent-teams/engine` and includes `omx-mux`, `omx-runtime-core`, and `omx-runtime`.
- Native Windows Codex team runtime expects psmux plus codex/node/npm/cargo/git; non-Windows first-release runtime expects tmux.

## Configuration and Feature-Control Surfaces

- `pyproject.toml`: package dependencies, scripts, bundled assets, pytest config.
- `.codex/config.toml`: generated notify/MCP config for Codex team projects.
- `.specify/config.json`: generated project config and Codex team runtime metadata.
- `.specify/teams/runtime.json`: Codex team runtime metadata.
- `.github/workflows/*.yml`: CI, docs, release, CodeQL, stale automation.
- `.devcontainer/post-create.sh`: convenience install surface for many agent CLIs plus uv/docfx.
- Extension/preset catalog JSON files: source of available add-on metadata.

## Compatibility and Versioning Strategy

- Agent keys should match actual installed CLI executable names when applicable.
- IDE-based integrations set `requires_cli: False`.
- Skills-based integrations keep `sp-*` workflow skill names and passive skill directory names.
- `map-scan` and `map-build` are breaking replacements for the former one-step map-codebase guidance.
- Generated surfaces should not overpromise runtime-native subagents where the integration cannot support them.
- Execution-oriented generated guidance uses `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents | subagent-blocked`, and `execution_surface: native-subagents`.
- Adapter-specific addenda may name concrete native subagent tools, but durable `sp-teams` orchestration remains reserved for durable team state or lifecycle needs and `subagent-blocked` must record its reason.

## Security and Trust Boundaries

- Generated destinations are validated to stay under the project root.
- Extension/preset manifest file paths must be relative and non-traversing.
- External agent CLIs, GitHub Actions marketplace actions, Node/npm packages, Cargo crates, tmux/psmux, and MCP dependencies sit outside repo ownership.
- MCP facade availability depends on installing optional `specify-cli[mcp]`.

## Change Impact

| Surface | Consumers | Verification |
| --- | --- | --- |
| `integrations/base.py` | nearly all generated integrations | `pytest tests/integrations -q` |
| specific adapter package | that agent's generated files | matching `tests/integrations/test_integration_*.py` |
| Codex team installer/runtime | Codex projects, MCP, engine packaging | `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py -q` |
| extension/preset managers | catalogs, user add-ons | `pytest tests/test_extensions.py tests/test_presets.py -q` |
| packaging force-includes | wheel contents | `pytest tests/test_packaging_assets.py -q`; `uv build` |

## Known Integration Unknowns

- Upstream agent CLIs can change command formats and capabilities without this repo changing.
- Release publishing beyond GitHub release creation should be rechecked before changing distribution automation.
