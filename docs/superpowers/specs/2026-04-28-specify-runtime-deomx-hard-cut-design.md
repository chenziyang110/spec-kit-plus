# Specify Runtime De-OMX Hard-Cut Design

**Date:** 2026-04-28  
**Status:** Approved  
**Owner:** Codex

## Summary

This design removes `OMX` branding and naming from the active `spec-kit-plus`
runtime surface through a hard cut with no compatibility layer.

The new naming policy is:

- user-facing workflow/runtime surfaces use `sp-*`
- internal identifiers use `specify_*`
- internal state and runtime files live under `.specify/*`
- environment variables use `SPECIFY_*`

This pass prioritizes hard-cut naming and surface migration. MCP reduction
decisions are documented here, but functional MCP removal is deferred until the
new names and paths are stable.

## Goals

- Replace `specify team` / `sp-team` with `sp-teams` as the public runtime
  surface.
- Replace `.specify/codex-team/*` with `.specify/teams/*`.
- Replace `omx_*` MCP server names with `specify_*`.
- Replace `.omx/*` runtime storage with `.specify/runtime/*`.
- Replace `OMX_*` environment variables with `SPECIFY_*`.
- Remove `OMX` / `omx` language from public docs, config generation, and
  user-facing runtime messaging.

## Non-Goals

- Do not keep a read/write compatibility shim for old `OMX` names.
- Do not preserve `omx` CLI as an advertised or fallback user surface.
- Do not perform deep MCP feature deletion in the same pass as the hard-cut
  naming migration.

## Naming Contract

### Public Surfaces

| Old | New |
|-----|-----|
| `specify team` | `sp-teams` |
| `sp-team` | `sp-teams` |
| `specify team watch` | `sp-teams watch` |
| `specify team submit-result` | `sp-teams submit-result` |

### Internal Identifiers

| Old | New |
|-----|-----|
| `omx_state` | `specify_state` |
| `omx_memory` | `specify_memory` |
| `omx_code_intel` | `specify_code_intel` |
| `omx_trace` | `specify_trace` |
| `omx_wiki` | `specify_wiki` |

### Internal Paths

| Old | New |
|-----|-----|
| `.omx/state/` | `.specify/runtime/state/` |
| `.omx/logs/` | `.specify/runtime/logs/` |
| `.omx/wiki/` | `.specify/runtime/wiki/` |
| `.omx/notepad.md` | `.specify/runtime/notepad.md` |
| `.omx/project-memory.json` | `.specify/runtime/project-memory.json` |
| `.specify/codex-team/` | `.specify/teams/` |

### Environment Variables

All runtime and MCP environment variables move from `OMX_*` to `SPECIFY_*`.

Examples:

- `OMX_TEAM_STATE_ROOT` -> `SPECIFY_TEAM_STATE_ROOT`
- `OMX_MCP_WORKDIR_ROOTS` -> `SPECIFY_MCP_WORKDIR_ROOTS`
- `OMX_TEAM_WORKER_CLI` -> `SPECIFY_TEAM_WORKER_CLI`

## Runtime Surface Rules

- `sp-teams` is the only public team/runtime entry point.
- `omx` and `specify team` are removed from official docs, generated messages,
  and product help.
- internal Python modules may remain under `codex_team` temporarily if needed,
  but no public contract may mention `codex-team`.

## MCP Retention Decision

The current MCP set is retained under new names in this pass.

### Keep in Hard-Cut Pass

- `specify_state`
- `specify_trace`
- `specify_memory`
- `specify_wiki`
- `specify_code_intel`

### Follow-Up Rationalization

After naming stabilizes, reassess:

- whether `specify_code_intel` should remain a standalone MCP or collapse into
  local tooling/helpers
- whether `specify_memory` and `specify_wiki` should remain separate services or
  become a thinner persistence layer under the Python runtime

## Risks

- this is a large string/path/env migration touching docs, tests, Python, TS,
  and Rust-adjacent build/runtime assumptions
- stale generated references can leave the runtime split between old and new
  state roots
- command-surface hard cut can invalidate existing operator habits and fixtures

## Acceptance Criteria

- no public runtime docs or generated help reference `omx` or `specify team`
- public runtime surface is `sp-teams`
- MCP server ids use `specify_*`
- runtime storage uses `.specify/runtime/*`
- team runtime storage uses `.specify/teams/*`
- targeted contract/integration suites pass with the new naming
