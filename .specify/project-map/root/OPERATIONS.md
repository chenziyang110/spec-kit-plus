# Operations

**Last Updated:** 2026-04-30
**Coverage Scope:** Build/run flows, install paths, freshness operations, runtime state, troubleshooting, and recovery.
**Primary Evidence:** `worker-results/core-cli-architecture.json`, `testing-verification.json`, `codex-team-runtime.json`, `project-map-atlas-state.json`, `packaging-release-config.json`.
**Update When:** Build tooling, install guidance, runtime prerequisites, state locations, freshness scripts, CI/release, or recovery playbooks change.

## Build and Packaging Playbooks

- Install for development with an editable/source-aware environment; if a global `specify` is stale, prefer `PYTHONPATH=src; python -m specify_cli ...`.
- Run Python tests with `pytest -q`.
- Build package with `uv build`.
- Build bundled engine with `npm --prefix extensions/agent-teams/engine run build`.
- CI uses `uv sync --extra test` and `uv run pytest` on Python 3.11, 3.12, and 3.13.

## Deployment and Runtime Topology

This is a CLI/package repo, not a deployed service. Runtime surfaces are local:

- `specify`: Python CLI.
- Generated agent files under downstream project-specific directories.
- `.specify/`: generated project state, memory, testing, atlas, team runtime metadata.
- `sp-teams`: Codex-only local team runtime surface.
- `specify-teams-mcp`: optional stdio MCP facade when `specify-cli[mcp]` is installed.
- `extensions/agent-teams/engine`: bundled optional runtime source/assets.

## Runtime and Toolchain Invariants

- Python 3.11+ is required.
- `uv`, Git, and the target agent CLI/IDE are normal local prerequisites.
- Node >=20 is required to build the bundled engine.
- Cargo is required for Rust workspace checks.
- Codex team runtime needs tmux or psmux depending on platform and checks native Windows psmux/codex/node/npm/cargo/git availability.

## Runtime State Locations

| State | Location |
| --- | --- |
| Project map status | `.specify/project-map/index/status.json` and legacy mirror `.specify/project-map/status.json` |
| Map scan/build state | `.specify/project-map/map-state.md` |
| Map packet evidence | `.specify/project-map/worker-results/*.json` |
| Project memory | `.specify/memory/project-rules.md`, `.specify/memory/project-learnings.md` |
| Learning runtime | `.planning/learnings/candidates.md`, `.planning/learnings/review.md` |
| Quick tasks | `.planning/quick/` |
| Orchestration state | `.specify/orchestration/` |
| Codex teams state | `.specify/teams/state/` |
| Codex teams install metadata | `.specify/teams/runtime.json`, `.specify/teams/install-state.json` |

## Project-Map Freshness Operations

- Check: `specify project-map check --format json` or source-aware equivalent.
- Mark dirty: `specify project-map mark-dirty <reason>`.
- Complete full refresh: `specify project-map complete-refresh --format json` after canonical files exist.
- Hook equivalent: `specify hook complete-refresh`.
- If uncommitted canonical atlas files exist, freshness inspection can still report changed files relative to HEAD until the atlas update is committed.

## Observability Design

- Python CLI surfaces return JSON with `--format json` for many helper commands.
- Hook commands print structured JSON payloads.
- Codex team runtime writes dispatch, result, batch, worker, mailbox, phase, event, monitor, and executor state files.
- Engine runtime has tests and generated state but should not be treated as a black box when runtime behavior changes.

## Failure Modes and Recovery Playbooks

- **Stale global CLI**: use source-aware command invocation or reinstall/editable install.
- **Missing atlas docs**: run `sp-map-scan -> sp-map-build`.
- **Incomplete scan package**: repair `coverage-ledger.json` or scan packets before building atlas.
- **Structural-only map build**: reject; require worker-results with `paths_read`.
- **Missing Codex team backend**: install tmux/psmux and required toolchain.
- **Packaging asset mismatch**: run `pytest tests/test_packaging_assets.py -q` and `uv build`.
- **Generated integration drift**: run focused integration tests, then broad `tests/integrations`.

## Known Runtime Unknowns

- Rust crate internals are sampled in this atlas.
- Release publication after GitHub release creation is lightly sampled.
- External CLIs and MCP clients may change behavior outside this repo.
