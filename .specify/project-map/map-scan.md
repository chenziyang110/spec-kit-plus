# Map Scan

## Run Metadata

- generated_by: sp-map-scan
- generated_at: 2026-04-30
- repository: F:\github\spec-kit-plus
- focus: full brownfield atlas refresh after map-scan/map-build workflow changes
- execution_model: subagents-first
- dispatch_shape: leader-inline-fallback
- execution_surface: leader-inline
- dispatch_reason: no-safe-delegated-lane in this historical scan session; the scan package is structured for packet execution.
- build_handoff: sp-map-build

## Repository Scope And Exclusions

Project-relevant inventory was built from `rg --files`, `git ls-files`, targeted root directory listing, existing `PROJECT-HANDBOOK.md`, `.specify/project-map/index/status.json`, workflow templates, and project memory startup.

Included surfaces:

- Python CLI source under `src/specify_cli/`
- workflow, passive-skill, project-map, testing, constitution, and worker prompt templates under `templates/`
- generated-agent integration adapters under `src/specify_cli/integrations/`
- Bash and PowerShell helper scripts under `scripts/`
- Codex team Python runtime under `src/specify_cli/codex_team/` and MCP facade under `src/specify_cli/mcp/`
- bundled Node/TypeScript/Rust team engine under `extensions/agent-teams/engine/`
- extension and preset catalogs plus docs under `extensions/` and `presets/`
- Python tests, contract tests, integration tests, hook tests, execution tests, orchestration tests, and Codex-team tests under `tests/`
- CI, devcontainer, packaging, docs, planning, and project-state files

Excluded from deep read but listed in the ledger:

- `.git/`: Git object database; revisit only for history investigation.
- `.venv/`: local environment; revisit only for dependency resolution defects.
- `.pytest_cache/`, `.ruff_cache/`: tool caches; revisit only for cache-specific debugging.
- `dist/`, `.tmp-dist/`, `.tmp-agent-teams-smoke/`, `runtime-test-output.log`: generated outputs; revisit only for packaging or smoke-test failure triage.
- `.worktrees/`: generated worktree state; revisit only when a task explicitly uses a worktree.

## Scan Dispatch And Subagent Use

Selected dispatch shape: `leader-inline-fallback`.

Reasoning:

- The scan found multiple safe read-only lanes, but this historical runtime invocation did not include explicit permission to spawn native subagents.
- The leader therefore produced scan packets and executed them on the leader-inline path during `sp-map-build`.
- The packet structure still preserves `MapScanPacket` fields so a future runtime with explicit dispatch can fan out the same lanes.

Join points:

- before finalizing `coverage-ledger.json`: complete
- before writing `scan-packets/*.md`: complete
- before atlas writing: delegated to `sp-map-build`

## Coverage Summary

- critical_rows: 10
- important_rows: 4
- low_risk_rows: 2
- unknown_rows: 0
- excluded_buckets: 5

No unresolved `unknown` rows remain. Every critical row has a scan packet, at least one final atlas target, and a verification route.

## Module And Topic Candidates

Primary modules for `sp-map-build`:

- `specify-cli-core`: Python CLI, integration registry, workflow hooks, execution packet/result contracts, project-map freshness, learning, quick/testing/eval/project-map commands, and generated installation behavior.
- `agent-teams-engine`: bundled optional Node/TypeScript/Rust Codex team runtime and native hook/runtime assets.
- `templates-generated-surfaces`: shared command templates, command partials, passive skills, project-map/testing templates, worker prompts, scripts, and generated downstream surfaces.

Root atlas topics:

- `ARCHITECTURE.md`: Python CLI monolith, shared subsystems, module graph, trust ownership, delegated execution boundaries.
- `STRUCTURE.md`: directory ownership, critical file families, placement rules, generated/bundled assets.
- `CONVENTIONS.md`: registry conventions, command naming, agent key conventions, generated-surface compatibility, state/documentation conventions.
- `INTEGRATIONS.md`: supported agent integrations, MCP/Context surfaces, external CLIs, optional runtimes, release/package boundaries, trust boundaries.
- `WORKFLOWS.md`: `specify -> plan`, brownfield `map-scan -> map-build`, testing workflows, implement/debug/quick behavior, state transitions.
- `TESTING.md`: Python pytest layers, template contract tests, integration generation tests, Codex runtime tests, engine build/test checks.
- `OPERATIONS.md`: install, local dev, build, release, project-map freshness, recovery, runtime state locations.

## Critical Surfaces

- CLI app and command wiring in `src/specify_cli/__init__.py`
- project-map freshness model in `src/specify_cli/project_map_status.py` and scripts under `scripts/*/project-map-freshness.*`
- integration registry and installer framework in `src/specify_cli/integrations/`
- generated workflow templates under `templates/commands/` and `templates/command-partials/`
- passive workflow skills under `templates/passive-skills/`
- execution packet/result and hook contracts under `src/specify_cli/execution/` and `src/specify_cli/hooks/`
- orchestration policy/state under `src/specify_cli/orchestration/`
- Codex team Python runtime and bundled engine assets
- Python test suites and engine build/test entry points
- packaging and force-included assets in `pyproject.toml`

## Scan Packet Index

| Packet | Ledger Rows | Scope | Result |
| --- | --- | --- | --- |
| `core-cli-architecture` | L001, L002, L003, L014 | Python CLI core, project-map status, learning/testing helpers, root config | `.specify/project-map/worker-results/core-cli-architecture.json` |
| `integrations-generated-surfaces` | L004, L005, L006 | integration registry, adapter classes, command/passive-skill templates, helper scripts | `.specify/project-map/worker-results/integrations-generated-surfaces.json` |
| `hooks-execution-orchestration` | L003, L007, L008 | packet/result contracts, hooks, orchestration policy and state | `.specify/project-map/worker-results/hooks-execution-orchestration.json` |
| `codex-team-runtime` | L009, L010 | Codex team Python runtime, MCP facade, bundled engine | `.specify/project-map/worker-results/codex-team-runtime.json` |
| `testing-verification` | L011, L012, L016 | Python test matrix, engine tests, verification commands | `.specify/project-map/worker-results/testing-verification.json` |
| `docs-planning-operations` | L013, L014, L015 | README/docs/planning/state, release docs, operator guidance | `.specify/project-map/worker-results/docs-planning-operations.json` |
| `packaging-release-config` | L001, L006, L015 | packaging metadata, CI/devcontainer, extension/preset catalogs | `.specify/project-map/worker-results/packaging-release-config.json` |
| `project-map-atlas-state` | L003, L005, L013, L014 | existing handbook, project-map templates/status, AGENTS instructions | `.specify/project-map/worker-results/project-map-atlas-state.json` |

## Build Readiness Checklist

- [x] Every project-relevant row is categorized.
- [x] No unresolved `unknown` rows remain.
- [x] Every critical row has at least one scan packet.
- [x] Every critical or important row has at least one atlas target or an explicit grouped target.
- [x] Every excluded bucket has a reason and revisit condition.
- [x] Every scan packet declares required reads, expected outputs, atlas targets, forbidden actions, result handoff path, join points, and minimum verification.
- [x] `sp-map-build` can execute packets against live repository paths without relying on chat memory.

## Known Scan Gaps

- The bundled Rust crates in `extensions/agent-teams/engine/crates/` are mapped from manifests, representative source, and tests; if future work changes Rust runtime behavior, run a deeper Rust-specific packet.
- External behavior of supported third-party agent CLIs is outside this repo and must be verified from upstream docs when adapter assumptions change.
- The repository has many historical planning files; atlas output should summarize durable product direction and avoid treating all old planning notes as current truth.

## Handoff To sp-map-build

`sp-map-build` must validate `coverage-ledger.json`, read every scan packet, execute the required live reads, write worker-result evidence with `paths_read`, synthesize the root/module atlas, prove reverse coverage closure, and then run the project-map complete-refresh hook.
