# Specify CLI Core Architecture

**Last Updated:** 2026-04-30
**Coverage Scope:** module-local architecture, internal boundaries, contracts, and truth ownership.
**Primary Evidence:** `worker-results/core-cli-architecture.json`, `hooks-execution-orchestration.json`, `integrations-generated-surfaces.json`, `codex-team-runtime.json`
**Update When:** command routing, init flow, integration generation, freshness state, hooks, execution schemas, orchestration, or Python team runtime behavior changes.

## Pattern Overview

The module is a Python Typer CLI with registry-driven integration adapters and file-backed workflow state. It favors explicit command surfaces and JSON state artifacts over implicit runtime coupling. Generated downstream behavior is treated as product code: templates and integration adapters are part of the CLI's behavioral contract, not auxiliary documentation.

## Internal Boundaries

- CLI boundary: `src/specify_cli/__init__.py` registers commands and delegates to helper modules.
- Integration boundary: `src/specify_cli/integrations/` transforms shared templates into agent-specific files.
- State boundary: `.specify/**` and `.planning/**` files are written through helper modules and validated by hooks/tests.
- Contract boundary: `execution/` and `hooks/` define reusable packet/result and workflow validation contracts.
- Team boundary: `codex_team/` controls Codex team state and dispatch; `extensions/agent-teams/engine/` supplies bundled runtime assets.

## Key Components and Responsibilities

| Component | Responsibility |
| --- | --- |
| `__init__.py` | Typer app, command help, subapp registration, `init`, aliases, status panels, project-map/hook/testing/learning/eval/team commands |
| `launcher.py`, `__main__.py` | Console entry routing for local or packaged execution |
| `integrations/__init__.py` | Built-in integration registration and registry export |
| `integrations/base.py` | Template discovery, placeholder replacement, manifest writing, passive skill/script copying, generated guidance addenda |
| `project_map_status.py` | Canonical status path, legacy fallback, dirty reasons, topic mapping, freshness inspection, complete refresh |
| `testing_inventory.py` | Source-aware detection of Python/Rust testable modules |
| `learnings.py` | Learning capture/review state and project-memory update helpers |
| `verification.py` | Command result summaries for workflow verification |
| `execution/*` | Worker packet/result schemas, validators, renderers, and handoff helpers |
| `hooks/*` | Preflight, artifact/state, delegation, project-map, learning, read/prompt, boundary, commit, and checkpoint helpers |
| `orchestration/*` | Subagents-first dispatch policy, capability snapshots, scheduler, state store, and review loop |
| `codex_team/*` | Team install, dispatch, result, sync, status, doctor, watcher, state paths, runtime bridge |
| `mcp/teams_server.py` | Optional MCP tool/resource facade over Codex team state and operations |

## Change Propagation Paths

- CLI command change -> tests for help/command routing -> README/workflow docs -> generated skill expectations.
- Integration registry/base change -> all generated agents -> packaging assets -> integration tests.
- Project-map status change -> map templates -> scripts/bash and scripts/powershell -> hook helpers -> project-map tests.
- Packet/result schema change -> hooks -> generated workflow prompts -> Codex team runtime -> contract tests.
- Codex team command/state change -> Python tests -> MCP facade -> bundled engine assumptions -> `pyproject.toml` force-includes.

## Truth Ownership and Boundaries

- Command existence and argument semantics live in `src/specify_cli/__init__.py`.
- Integration generation behavior lives in `src/specify_cli/integrations/`.
- Generated workflow wording lives in `templates/`, but how it is installed lives in the integration module.
- Project-map freshness truth lives in `project_map_status.py` plus parity scripts.
- Delegated execution truth lives in shared packet/result schemas; command-local variants should not bypass them.
- Python Codex team behavior lives in `codex_team/`; engine internals live in `agent-teams-engine`.

## Known Module Unknowns

- A developer's global `specify` command may be stale. Use source-aware invocation for checkout validation: `$env:PYTHONPATH='src'; python -m specify_cli ...`.
- External agent CLI behavior is not owned here and should be revalidated when adapter behavior changes.
- Rust engine behavior is only sampled through this module's Python control plane; deeper Rust changes need a targeted engine packet.
