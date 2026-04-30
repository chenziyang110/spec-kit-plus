# Testing

**Last Updated:** 2026-04-30
**Coverage Scope:** Python pytest layers, integration/template contracts, engine build checks, and verification matrix.
**Primary Evidence:** `worker-results/testing-verification.json`, `packaging-release-config.json`.
**Update When:** Test layout, verification commands, CI, templates, integration surfaces, or engine build/test scripts change.

## Test Pyramid and Quality Gates

- Python unit/contract/integration tests under `tests/` are the primary regression suite.
- Template contract tests lock generated workflow wording and atlas/testing guidance.
- Integration tests lock generated output paths and adapter-specific transforms.
- Hook/execution/orchestration tests lock workflow quality helper contracts.
- Codex-team tests lock Python control-plane behavior and CLI/API surfaces.
- Engine build checks validate bundled TypeScript runtime packaging.

## Capability Verification Map

| Capability | Minimum Verification |
| --- | --- |
| Map scan/build templates and atlas status | `pytest tests/test_map_scan_build_template_guidance.py tests/test_project_map_layered_contract.py tests/test_project_map_status.py -q` |
| CLI/init/integration generation | `pytest tests/integrations -q` |
| Passive skills and generated guidance | `pytest tests/test_passive_skill_guidance.py tests/test_quick_skill_mirror.py tests/test_specify_guidance_docs.py -q` |
| Hooks/execution/orchestration | `pytest tests/hooks tests/execution tests/orchestration -q` |
| Codex team runtime | `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q` |
| Packaging assets | `pytest tests/test_packaging_assets.py -q`; `uv build` |
| Bundled engine | `npm --prefix extensions/agent-teams/engine run build` |

## Contract Verification Surfaces

- `tests/test_map_scan_build_template_guidance.py`: scan/build prompt contract, packet evidence, reverse coverage, structural-only refresh refusal.
- `tests/test_project_map_status.py`: Python freshness model, dirty reasons, topic mapping, complete-refresh reason.
- `tests/test_project_map_freshness_scripts.py`: Bash/PowerShell helper parity and legacy status fallback.
- `tests/integrations/`: per-agent generated output behavior.
- `tests/execution/`: worker packet/result schemas, validators, handoffs.
- `tests/hooks/`: hook event behavior and guardrails.
- `tests/orchestration/`: subagents-first dispatch policy, scheduling, state store, review loop.
- `tests/codex_team/`: team runtime state, dispatch, sync-back, watch, doctor, API surface.
- Generated-surface tests should assert `subagent-mandatory`, `one-subagent`, `parallel-subagents`, `subagent-blocked`, and `native-subagents` where active workflow guidance describes execution dispatch.

## Build, Runtime, and Recovery Verification

- Local source CLI command checks should use `PYTHONPATH=src; python -m specify_cli ...` when the installed `specify` may be stale.
- CI runs Ruff on `src/` and pytest on Python 3.11, 3.12, and 3.13.
- Engine build uses Node/npm independently of Python pytest.
- Rust testability is detected by `testing_inventory.py`, but full Rust runtime verification is separate from the Python test suite.

## Change-Impact Verification Matrix

| Changed Surface | Focused Check | Broader Check |
| --- | --- | --- |
| `src/specify_cli/project_map_status.py` | `pytest tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py -q` | `pytest tests/hooks/test_project_map_hooks.py -q` |
| `templates/commands/*` | matching `tests/test_*template*` | `pytest tests/integrations -q` |
| `integrations/base.py` | `pytest tests/integrations/test_integration_base_* -q` | `pytest tests/integrations -q` |
| `execution/` | `pytest tests/execution -q` | `pytest tests/hooks tests/codex_team -q` |
| `codex_team/` | `pytest tests/codex_team -q` | `pytest tests/contract/test_codex_team*.py -q` |
| `extensions/agent-teams/engine/` | `npm --prefix extensions/agent-teams/engine run build` | engine-specific node/cargo tests as needed |
| `pyproject.toml` | `pytest tests/test_packaging_assets.py -q` | `uv build` |

## Verification Entry Points

- Full repo Python: `pytest -q`
- Source command smoke: `$env:PYTHONPATH='src'; python -m specify_cli --help`
- Testing inventory: `$env:PYTHONPATH='src'; python -m specify_cli testing inventory --format json`
- Project-map focused: `pytest tests/test_map_scan_build_template_guidance.py tests/test_project_map_layered_contract.py tests/test_project_map_status.py -q`

## Known Test Unknowns

- Engine Rust crates were not exhaustively mapped; run Cargo tests before Rust behavior changes.
- CI release workflow details beyond sampled YAML should be verified before release automation changes.
