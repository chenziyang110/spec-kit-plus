# Agent Teams Engine Overview

**Module ID:** `agent-teams-engine`
**Owned Roots:** `extensions/agent-teams/engine/`
**Related Root Topics:** `ARCHITECTURE.md`, `INTEGRATIONS.md`, `OPERATIONS.md`, `TESTING.md`
**Primary Evidence:** `worker-results/codex-team-runtime.json`, `testing-verification.json`, `packaging-release-config.json`
**Update When:** bundled TypeScript runtime, Rust crates, notify hooks, prompts, worker skill assets, engine build scripts, or runtime prerequisites change.

## Purpose

This module is the optional bundled engine used by Codex team workflows. It supplies TypeScript runtime code, notify-hook support, prompts, worker skill assets, and Rust workspace crates that the Python `specify-cli-core` package includes and controls through Codex team commands.

## Why This Module Exists

Codex team execution needs runtime assets beyond the Python CLI: session orchestration, worker bootstrap, native hook support, model/runtime contracts, and lower-level multiplexing/runtime pieces. Keeping this as a separate module prevents Python CLI control-plane assumptions from being confused with engine internals.

## Shared Surfaces

- `package.json`: Node version, build, runtime, and engine test scripts.
- `src/team/`: TypeScript team runtime, state, session, worker, and orchestration code.
- `src/scripts/notify-hook/`: native hook notification and team dispatch helpers.
- `src/config/`: generated runtime configuration.
- `crates/`: Rust workspace members `omx-mux`, `omx-runtime-core`, and `omx-runtime`.
- `prompts/` and `skills/`: bundled executor prompts and worker skill assets.

## Risky Coordination Points

- Engine assets are force-included by `pyproject.toml`; packaging changes can break runtime installs.
- Runtime behavior depends on external `node`, `npm`, `cargo`, `codex`, `tmux` or `psmux`.
- Rust internals are marked lower confidence in this atlas and need targeted packeting before behavior-level Rust changes.
- Notify-hook semantics must stay aligned with Python Codex team state and `.codex/config.toml` generation.

## Where To Read Next

- `ARCHITECTURE.md` for runtime/control-plane separation.
- `STRUCTURE.md` for engine directory responsibilities.
- `WORKFLOWS.md` for dispatch/runtime/build flows.
- `TESTING.md` for build and runtime verification.
- Root `OPERATIONS.md` for toolchain and recovery notes.
