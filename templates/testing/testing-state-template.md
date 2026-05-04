---
active_command: sp-test-scan
status: routing
mode: bootstrap
scan_status: pending
build_status: pending
updated: [ISO timestamp]
---

# Testing State

control_plane_role: lifecycle and routing tracker for `.specify/testing/*`; do not duplicate scan evidence, build-plan lane packets, contract rules, or playbook instructions here.

## Current Focus

- next_action:
- next_command:
- handoff_reason:
- selected_modules:
- selected_language_skills: bundled Spec Kit testing language skills used by `sp-test-scan` / `sp-test-build` (for example `python-testing`, `js-testing`, `rust-testing`)
- inventory_source: specify testing inventory --format json
- current_wave:
- current_lane:

## Scan Artifacts

- test_scan: .specify/testing/TEST_SCAN.md
- test_build_plan: .specify/testing/TEST_BUILD_PLAN.md
- test_build_plan_json: .specify/testing/TEST_BUILD_PLAN.json
- unit_test_system_request: .specify/testing/UNIT_TEST_SYSTEM_REQUEST.md

## Build Execution

- accepted_results:
- rejected_results:
- failed_validation:
- retry_policy:

## Module Inventory

- module:
  - module_name:
  - module_root:
  - module_kind: root-module | workspace-root | nested-module
  - language:
  - manifest_path:
  - selected_skill:
  - framework:
  - framework_confidence: high | medium | low
  - canonical_test_path:
  - canonical_test_command:
  - command_tiers:
    - fast smoke:
    - focused:
    - full:
  - coverage_command:
  - state: missing | partial | healthy | gap
  - classification_reason:
  - selection_override_reason:
  - planned_action: bootstrap-framework | add-core-tests | raise-coverage | adopt-existing | audit-only

## Testing Assets

- testing_contract:
- testing_playbook:
- coverage_baseline:
- unit_test_system_request:

## Coverage Notes

- module:
  - baseline:
  - threshold:
  - exceptions:
  - uncovered_hotspots:
  - hotspot_context:
  - command_tier_context:
    - fast smoke:
    - focused:
    - full:

## Validation Evidence

- last_manual_validation:
  - commands:
  - run_at:
  - exit_status:
  - summary:

## Open Gaps

- module:
  - summary:
  - next_action:
