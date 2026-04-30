---
active_command: sp-map-build
status: complete
scan_status: complete
build_status: complete
updated: 2026-04-30
---

# Project Map Workflow State

## Current Focus

- next_action: commit atlas refresh, then rerun complete-refresh so the stored baseline points at the atlas commit
- next_command: git commit followed by project-map complete-refresh
- handoff_reason: full brownfield atlas refresh completed from scan packets and worker evidence
- focus: full brownfield atlas refresh
- selected_modules: specify-cli-core, agent-teams-engine, templates-generated-surfaces
- selected_topics: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, INTEGRATIONS.md, WORKFLOWS.md, TESTING.md, OPERATIONS.md
- current_packet: none
- current_join_point: atlas synthesized

## Scan Artifacts

- map_scan: .specify/project-map/map-scan.md
- coverage_ledger: .specify/project-map/coverage-ledger.md
- coverage_ledger_json: .specify/project-map/coverage-ledger.json
- scan_packets: .specify/project-map/scan-packets/

## Build Evidence

- worker_results: .specify/project-map/worker-results/
- accepted_packet_results:
  - core-cli-architecture
  - integrations-generated-surfaces
  - hooks-execution-orchestration
  - codex-team-runtime
  - testing-verification
  - docs-planning-operations
  - packaging-release-config
  - project-map-atlas-state
- rejected_packet_results: none
- failed_readiness_checks: none
- failed_reverse_coverage_checks: none

## Packet Inventory

- packet:
  - lane_id: core-cli-architecture
  - ledger_rows: L001, L002, L003, L014
  - scope: Python CLI core and project-map helper surfaces
  - result_handoff_path: .specify/project-map/worker-results/core-cli-architecture.json
  - status: accepted
- packet:
  - lane_id: integrations-generated-surfaces
  - ledger_rows: L004, L005, L006
  - scope: integrations and generated workflow/template surfaces
  - result_handoff_path: .specify/project-map/worker-results/integrations-generated-surfaces.json
  - status: accepted
- packet:
  - lane_id: hooks-execution-orchestration
  - ledger_rows: L003, L007, L008
  - scope: execution contracts, hooks, orchestration core
  - result_handoff_path: .specify/project-map/worker-results/hooks-execution-orchestration.json
  - status: accepted
- packet:
  - lane_id: codex-team-runtime
  - ledger_rows: L009, L010
  - scope: Codex team Python runtime, MCP facade, bundled engine
  - result_handoff_path: .specify/project-map/worker-results/codex-team-runtime.json
  - status: accepted_with_concerns
- packet:
  - lane_id: testing-verification
  - ledger_rows: L011, L012, L016
  - scope: Python and engine test surfaces plus excluded output buckets
  - result_handoff_path: .specify/project-map/worker-results/testing-verification.json
  - status: accepted
- packet:
  - lane_id: docs-planning-operations
  - ledger_rows: L013, L014, L015
  - scope: README, docs, planning, release docs, extension/preset guidance
  - result_handoff_path: .specify/project-map/worker-results/docs-planning-operations.json
  - status: accepted
- packet:
  - lane_id: packaging-release-config
  - ledger_rows: L001, L006, L015
  - scope: packaging, CI, devcontainer, extension/preset catalogs
  - result_handoff_path: .specify/project-map/worker-results/packaging-release-config.json
  - status: accepted
- packet:
  - lane_id: project-map-atlas-state
  - ledger_rows: L003, L005, L013, L014
  - scope: AGENTS, project-map status/templates, memory and atlas contracts
  - result_handoff_path: .specify/project-map/worker-results/project-map-atlas-state.json
  - status: accepted

## Coverage Summary

- critical_rows: 10
- important_rows: 4
- low_risk_rows: 2
- unknown_rows: 0
- excluded_buckets: 5
- critical_rows_without_packets: 0
- critical_or_important_rows_without_atlas_targets: 0
- unresolved_unknown_rows: 0

## Atlas Outputs

- handbook: PROJECT-HANDBOOK.md
- index:
  - .specify/project-map/index/atlas-index.json
  - .specify/project-map/index/modules.json
  - .specify/project-map/index/relations.json
  - .specify/project-map/index/status.json
- root_docs:
  - .specify/project-map/root/ARCHITECTURE.md
  - .specify/project-map/root/STRUCTURE.md
  - .specify/project-map/root/CONVENTIONS.md
  - .specify/project-map/root/INTEGRATIONS.md
  - .specify/project-map/root/WORKFLOWS.md
  - .specify/project-map/root/TESTING.md
  - .specify/project-map/root/OPERATIONS.md
- module_docs:
  - .specify/project-map/modules/specify-cli-core/OVERVIEW.md
  - .specify/project-map/modules/specify-cli-core/ARCHITECTURE.md
  - .specify/project-map/modules/specify-cli-core/STRUCTURE.md
  - .specify/project-map/modules/specify-cli-core/WORKFLOWS.md
  - .specify/project-map/modules/specify-cli-core/TESTING.md
  - .specify/project-map/modules/agent-teams-engine/OVERVIEW.md
  - .specify/project-map/modules/agent-teams-engine/ARCHITECTURE.md
  - .specify/project-map/modules/agent-teams-engine/STRUCTURE.md
  - .specify/project-map/modules/agent-teams-engine/WORKFLOWS.md
  - .specify/project-map/modules/agent-teams-engine/TESTING.md
  - .specify/project-map/modules/templates-generated-surfaces/OVERVIEW.md
  - .specify/project-map/modules/templates-generated-surfaces/ARCHITECTURE.md
  - .specify/project-map/modules/templates-generated-surfaces/STRUCTURE.md
  - .specify/project-map/modules/templates-generated-surfaces/WORKFLOWS.md
  - .specify/project-map/modules/templates-generated-surfaces/TESTING.md
- deep_docs: not required for this full atlas refresh; use module deep docs for future targeted packeted refreshes

## Validation Evidence

- readiness_validation: passed at scan handoff
- worker_result_json_validation: passed for all 8 worker result files
- reverse_coverage_validation: passed; every coverage-ledger row maps to packet evidence and atlas targets or is explicitly excluded
- complete_refresh: passed; status metadata written with `last_refresh_reason: map-build`, `freshness: fresh`, `dirty: false`
- commands_run:
  - `specify learning start --command map-scan --format json`
  - `rg --files`
  - `git ls-files`
  - `python -m json.tool .specify/project-map/coverage-ledger.json`
  - `python -m json.tool .specify/project-map/worker-results/*.json`
  - `$env:PYTHONPATH='src'; python -m specify_cli testing inventory --format json`
  - `$env:PYTHONPATH='src'; python -m specify_cli project-map complete-refresh --format json`
  - `pytest tests/test_map_scan_build_template_guidance.py tests/test_project_map_layered_contract.py tests/test_project_map_status.py -q`
  - `pytest -q`
  - `npm --prefix extensions/agent-teams/engine run build`

## Open Gaps

- gap:
  - affected_packet: codex-team-runtime
  - affected_ledger_rows: L010
  - summary: Rust crate internals are sampled rather than exhaustively line-read.
  - next_action: run targeted deep Rust packet before changing Rust runtime behavior.
- gap:
  - affected_packet: project-map-atlas-state
  - affected_ledger_rows: L014
  - summary: `.specify/project-map/**` and `.specify/memory/project-*.md` are now intentionally unignored as stable project knowledge, while `.specify/runtime/**` and `.specify/teams/**` remain ignored runtime state.
  - next_action: after committing the atlas refresh, rerun `$env:PYTHONPATH='src'; python -m specify_cli project-map complete-refresh --format json` and commit the updated status files so `last_mapped_commit` points at the atlas commit.
