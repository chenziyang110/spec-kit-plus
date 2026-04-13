---
phase: 04-specify-plan-collaboration-routing
plan: 01
subsystem: orchestration-templates
tags: [specify, plan, orchestration, templates, tests]
requirements: [WF-01, WF-02, LANE-01]
tech-stack: [markdown templates, pytest]
key-files:
  - templates/commands/specify.md
  - templates/commands/plan.md
  - tests/test_alignment_templates.py
  - tests/orchestration/test_policy.py
decisions:
  - "Mirror the canonical strategy order from `implement` into `specify` and `plan` rather than inventing workflow-specific names."
  - "Record shared routing decisions inside workflow artifacts instead of adding a separate runtime-only surface."
  - "Keep Codex-only runtime wording out of shared templates."
metrics:
  completed_date: "2026-04-13"
---

# Phase 04 Plan 01: Specify & Plan Collaboration Routing Summary

## One-liner
Extended the shared orchestration contract into `specify` and `plan` so both workflows now describe canonical strategy selection, workflow-specific lanes, join points, and integration-neutral routing language.

## Key Changes

### Shared Template Contract
- Updated `templates/commands/specify.md` so it selects a collaboration strategy before decomposition begins.
- Updated `templates/commands/plan.md` so it selects a collaboration strategy before research and design fan-out begins.
- Both templates now use the canonical strategy names `single-agent`, `native-multi-agent`, and `sidecar-runtime` with the same fallback order already established for `implement`.

### Workflow-Specific Lane Design
- `specify` now documents its candidate lanes as repository/local context analysis, reference analysis, and ambiguity/risk/gap analysis.
- `plan` now documents its candidate lanes as research, data model, contracts, and quickstart/validation scenarios.
- Both workflows explicitly call out the required join points before final artifact writing.

### Regression Coverage
- Added shared template assertions in `tests/test_alignment_templates.py`.
- Added generic policy tests in `tests/orchestration/test_policy.py` to prove the chooser remains command-agnostic for `specify` and `plan`.

## Deviations from Plan
- No material deviation. Verification initially failed because the shared templates still contained the literal Codex runtime surface name in negative guidance text; the wording was normalized to keep shared templates runtime-neutral and satisfy the existing contract tests.

## Known Stubs
- `tasks` and `explain` routing are still pending and belong to Phase 5.
- CLI/init messaging and generated-skill integration coverage are still pending and belong to Phase 6.

## Self-Check: PASSED
- [x] Shared strategy language added to `specify`
- [x] Shared strategy language added to `plan`
- [x] Template and policy regressions pass
