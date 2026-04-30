# Specify CLI Core Testing

**Last Updated:** 2026-04-30
**Coverage Scope:** Python CLI, integration generation, hooks, execution contracts, orchestration, project-map state, and Codex team control-plane verification.
**Primary Evidence:** `worker-results/testing-verification.json`, `core-cli-architecture.json`, `hooks-execution-orchestration.json`
**Update When:** tests, command surfaces, validation helpers, or core Python behavior changes.

## Smallest Trustworthy Checks

| Changed Surface | Check |
| --- | --- |
| Project-map status/freshness | `pytest tests/test_project_map_status.py tests/test_project_map_freshness_scripts.py -q` |
| CLI/init routing | `pytest tests/integrations/test_cli.py -q` |
| Integration generation | `pytest tests/integrations -q` |
| Execution contracts | `pytest tests/execution -q` |
| Hooks | `pytest tests/hooks -q` |
| Orchestration | `pytest tests/orchestration -q` |
| Codex team Python control plane | `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q` |
| Packaging asset inclusion | `pytest tests/test_packaging_assets.py -q` |

## Regression-Sensitive Areas

- CLI command registration and aliases.
- Generated file paths and placeholder transforms.
- Project-map dirty reason normalization and topic mapping.
- Worker packet/result schemas and validators.
- Strategy selection claims for multi-agent/sidecar execution.
- Codex team state paths, dispatch/result records, and MCP tool names.

## Shared Test Dependencies

- `pyproject.toml` pytest config controls discovery and strict markers.
- Template tests may fail from Python source changes when generated wording changes.
- Codex team tests depend on packaged runtime metadata and state file assumptions.
- Source-aware CLI checks should set `PYTHONPATH=src` when global `specify` may lag the checkout.

## Minimum Verification

- Focused atlas/core check: `pytest tests/test_map_scan_build_template_guidance.py tests/test_project_map_layered_contract.py tests/test_project_map_status.py -q`
- Core workflow contracts: `pytest tests/hooks tests/execution tests/orchestration -q`
- Broad Python regression: `pytest -q`
