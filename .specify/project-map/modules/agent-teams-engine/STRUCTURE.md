# Agent Teams Engine Structure

**Last Updated:** 2026-04-30
**Coverage Scope:** bundled engine file placement, owned directories, and extension points.
**Primary Evidence:** `worker-results/codex-team-runtime.json`, `packaging-release-config.json`
**Update When:** engine directories, package scripts, Rust crates, prompts, skills, or packaged asset locations change.

## Owned Roots

- `extensions/agent-teams/engine/`

## Directory Responsibilities

| Path | Responsibility |
| --- | --- |
| `package.json` | Node package metadata, required Node version, scripts, dependencies |
| `tsconfig.json` | TypeScript compiler configuration |
| `src/team/` | team runtime, state, operations, worker bootstrap, model/runtime contracts |
| `src/cli/` | engine CLI entry tests and runtime entry surfaces |
| `src/scripts/notify-hook/` | notification hook and dispatch support |
| `src/config/` | runtime configuration generation |
| `tests/` | engine bridge tests |
| `crates/` | Rust workspace crates and tests |
| `prompts/` | bundled runtime prompts |
| `skills/` | bundled worker skills |

## Key File Families

- `src/team/*.ts`
- `src/team/**/__tests__/**`
- `src/scripts/notify-hook/*.ts`
- `src/config/*.ts`
- `crates/*/Cargo.toml`
- `crates/*/src/**`
- `prompts/*.md`
- `skills/*/SKILL.md`

## Shared Write Surfaces

- `.specify/teams/runtime.json`
- `.specify/teams/state/**`
- `.specify/config.json`
- `.codex/config.toml` notify/MCP config when installed by the Python control plane
- Packaged wheel assets via `pyproject.toml`

## Where To Extend This Module

- Runtime behavior: update `src/team/**` and matching tests.
- Notify hooks: update `src/scripts/notify-hook/**` and Python installer expectations.
- Rust behavior: update `crates/**`, then run targeted Rust/engine verification.
- Worker prompts/skills: update `prompts/**` or `skills/**`, then verify packaging and generated team behavior.
