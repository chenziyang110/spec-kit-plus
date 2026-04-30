# MapScanPacket: codex-team-runtime

- lane_id: codex-team-runtime
- mode: read_only
- scope: Codex team Python runtime, MCP facade, generated Codex runtime assets, bundled TypeScript/Rust engine.
- ledger_row_ids: L009, L010

## required_reads

- `src/specify_cli/codex_team/**`
- `src/specify_cli/mcp/teams_server.py`
- `extensions/agent-teams/engine/package.json`
- `extensions/agent-teams/engine/tsconfig.json`
- `extensions/agent-teams/engine/src/cli/index.ts`
- `extensions/agent-teams/engine/src/team/**`
- `extensions/agent-teams/engine/src/scripts/notify-hook/**`
- `extensions/agent-teams/engine/src/config/**`
- `extensions/agent-teams/engine/crates/**/Cargo.toml`
- `extensions/agent-teams/engine/crates/**/*.rs`
- `extensions/agent-teams/engine/prompts/*.md`
- `extensions/agent-teams/engine/skills/worker/SKILL.md`
- `tests/codex_team/**`
- `tests/contract/test_codex_team*.py`
- `tests/test_teams_mcp_server.py`

## excluded_paths

- `extensions/agent-teams/engine/node_modules/**`
- `extensions/agent-teams/engine/dist/**`

## required_questions

- What is owned by the Python `specify team` surface versus the bundled engine?
- What state paths, dispatch records, worker results, and runtime events exist?
- Which MCP operations mirror CLI operations?
- What is the build/test contract for the engine?

## expected_outputs

- Codex runtime lifecycle, state, and failure/recovery facts.
- Engine topology and entry points.
- Python/engine boundary and packaging asset facts.

## atlas_targets

- `.specify/project-map/root/ARCHITECTURE.md`
- `.specify/project-map/root/INTEGRATIONS.md`
- `.specify/project-map/root/OPERATIONS.md`
- `.specify/project-map/modules/specify-cli-core/WORKFLOWS.md`
- `.specify/project-map/modules/agent-teams-engine/OVERVIEW.md`
- `.specify/project-map/modules/agent-teams-engine/ARCHITECTURE.md`
- `.specify/project-map/modules/agent-teams-engine/STRUCTURE.md`
- `.specify/project-map/modules/agent-teams-engine/WORKFLOWS.md`
- `.specify/project-map/modules/agent-teams-engine/TESTING.md`

## forbidden_actions

- Do not start or mutate long-running team sessions.
- Do not build or install dependencies during evidence collection.

## result_handoff_path

`.specify/project-map/worker-results/codex-team-runtime.json`

## join_points

- before final atlas writing
- before reverse coverage validation

## minimum_verification

- `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q`
- `npm --prefix extensions/agent-teams/engine run build`

## blocked_conditions

- Python runtime or engine package manifests are unreadable.
- Runtime state locations cannot be established.
