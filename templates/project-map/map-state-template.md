---
active_command: sp-map-scan
status: scanning
scan_status: pending
build_status: pending
updated: [ISO timestamp]
---

# Project Map Workflow State

## Current Focus

- next_action:
- next_command:
- handoff_reason:
- focus:
- selected_modules:
- selected_topics:
- current_packet:
- current_join_point:

## Scan Artifacts

- map_scan: .specify/project-map/map-scan.md
- coverage_ledger: .specify/project-map/coverage-ledger.md
- coverage_ledger_json: .specify/project-map/coverage-ledger.json
- scan_packets: .specify/project-map/scan-packets/

## Build Evidence

- worker_results: .specify/project-map/worker-results/
- accepted_packet_results:
- rejected_packet_results:
- failed_readiness_checks:
- failed_reverse_coverage_checks:

## Packet Inventory

- packet:
  - lane_id:
  - ledger_rows:
  - scope:
  - required_reads:
  - atlas_targets:
  - result_handoff_path:
  - status: pending | executing | accepted | rejected | blocked

## Coverage Summary

- critical_rows:
- important_rows:
- low_risk_rows:
- unknown_rows:
- excluded_buckets:

## Atlas Outputs

- handbook: PROJECT-HANDBOOK.md
- index:
  - .specify/project-map/index/atlas-index.json
  - .specify/project-map/index/modules.json
  - .specify/project-map/index/relations.json
  - .specify/project-map/index/status.json
- root_docs:
- module_docs:
- deep_docs:

## Validation Evidence

- readiness_validation:
- reverse_coverage_validation:
- complete_refresh:
- commands_run:

## Open Gaps

- gap:
  - affected_packet:
  - affected_ledger_rows:
  - summary:
  - next_action:
