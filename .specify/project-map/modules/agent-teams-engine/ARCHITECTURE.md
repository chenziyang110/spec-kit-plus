# Agent Teams Engine Architecture

**Last Updated:** 2026-04-30
**Coverage Scope:** bundled engine architecture, runtime boundaries, and Python control-plane relations.
**Primary Evidence:** `worker-results/codex-team-runtime.json`, `testing-verification.json`
**Update When:** TypeScript runtime, Rust crates, notify hooks, runtime state, prompts, or engine packaging changes.

## Pattern Overview

The engine is a private Node >=20 TypeScript package with a Rust workspace. It is packaged with the Python CLI but remains a separate runtime layer. Python commands install/configure/dispatch and read state; the engine executes or supports team runtime behavior through TypeScript, scripts, prompts, and native components.

## Internal Boundaries

- TypeScript runtime: `src/team/**`
- CLI/runtime scripts: `src/cli/**`, `src/scripts/**`
- Notify hooks: `src/scripts/notify-hook/**`
- Config generation: `src/config/**`
- Rust runtime/mux crates: `crates/**`
- Prompt/skill assets: `prompts/**`, `skills/**`

## Key Components and Responsibilities

| Component | Responsibility |
| --- | --- |
| `package.json` | Node engine requirement and build/test/runtime scripts |
| `src/team/runtime.ts` | team runtime composition and execution entry behavior |
| `src/team/team-ops.ts` | team operations exposed to runtime flows |
| `src/scripts/notify-hook/team-dispatch.ts` | hook-driven dispatch support |
| `src/config/generator.ts` | runtime config generation |
| `crates/omx-mux` | Rust multiplexing support |
| `crates/omx-runtime-core` | core runtime primitives |
| `crates/omx-runtime` | Rust runtime executable/test surface |
| `prompts/executor.md` | bundled executor prompt |
| `skills/worker/SKILL.md` | bundled worker skill guidance |

## Change Propagation Paths

- Engine build script change -> packaging tests -> devcontainer/toolchain assumptions -> operations docs.
- Runtime state contract change -> Python `codex_team` state readers/writers -> MCP facade -> Codex team tests.
- Notify-hook change -> `.codex/config.toml` generation -> team dispatch behavior -> runtime tests.
- Prompt/skill change -> generated worker behavior -> packet/result expectations.
- Rust crate change -> engine build/cargo tests -> runtime bridge assumptions.

## Truth Ownership and Boundaries

- Engine runtime internals live here.
- Python installation, dispatch, and state reconciliation live in `specify-cli-core`.
- `.specify/teams/state/**` record shapes are shared with Python and should be changed with cross-module tests.
- External tmux/psmux/codex/node/npm/cargo availability is an operational dependency, not a repository guarantee.

## Known Module Unknowns

- Rust crate behavior is sampled, not exhaustively mapped.
- Runtime behavior can vary by platform and available multiplexer backend.
- Full native-hook behavior should be verified in the target runtime environment before release-sensitive changes.
