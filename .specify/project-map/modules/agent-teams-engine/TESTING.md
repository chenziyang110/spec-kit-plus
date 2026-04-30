# Agent Teams Engine Testing

**Last Updated:** 2026-04-30
**Coverage Scope:** engine build checks, TypeScript tests, bridge tests, Rust test surfaces, and Python control-plane compatibility.
**Primary Evidence:** `worker-results/testing-verification.json`, `codex-team-runtime.json`
**Update When:** engine runtime code, package scripts, Rust crates, prompts, skills, or Python team contracts change.

## Smallest Trustworthy Checks

| Changed Surface | Check |
| --- | --- |
| TypeScript engine build | `npm --prefix extensions/agent-teams/engine run build` |
| Bridge behavior | `npm --prefix extensions/agent-teams/engine run test:bridge` |
| Native hook behavior | `npm --prefix extensions/agent-teams/engine run test:native-hooks` |
| Python control-plane contract | `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q` |
| Packaging inclusion | `pytest tests/test_packaging_assets.py -q` |

## Regression-Sensitive Areas

- Runtime state file schema under `.specify/teams/state/**`.
- Multiplexer backend selection and toolchain detection.
- Notify-hook dispatch behavior.
- Worker prompt/result handoff expectations.
- Packaged path resolution from source checkout versus installed wheel.
- Rust runtime semantics.

## Shared Test Dependencies

- Node >=20 is required for engine build/tests.
- Cargo is required for Rust checks.
- Python tests validate the control plane but do not exhaustively verify TypeScript/Rust runtime behavior.
- Packaged asset tests protect whether engine files ship in the wheel.

## Minimum Verification

- Engine sanity: `npm --prefix extensions/agent-teams/engine run build`
- Cross-module sanity: `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q`
- Before Rust behavior changes: run targeted Cargo tests for the affected crate in addition to engine build.
