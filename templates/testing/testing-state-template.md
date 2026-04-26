---
status: inventory
mode: bootstrap
updated: [ISO timestamp]
---

# Testing State

## Current Focus

- next_action:
- next_command:
- handoff_reason:
- selected_modules:
- selected_language_skills:
- inventory_source: specify testing inventory --format json

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
  - coverage_command:
  - state: missing | partial | healthy | gap
  - classification_reason:
  - selection_override_reason:
  - planned_action: bootstrap-framework | add-core-tests | raise-coverage | adopt-existing | audit-only

## Testing Assets

- testing_contract:
- testing_playbook:
- coverage_baseline:

## Coverage Notes

- module:
  - baseline:
  - threshold:
  - exceptions:

## Open Gaps

- module:
  - summary:
  - next_action:
