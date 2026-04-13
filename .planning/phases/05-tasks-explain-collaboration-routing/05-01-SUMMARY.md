---
phase: 05-tasks-explain-collaboration-routing
plan: 01
subsystem: orchestration-templates
tags: [tasks, explain, orchestration, templates, tests]
requirements: [WF-03, WF-04, LANE-02, LANE-03]
tech-stack: [markdown templates, pytest]
key-files:
  - templates/commands/tasks.md
  - templates/commands/explain.md
  - tests/test_alignment_templates.py
  - tests/test_tui_visual_contract.py
  - tests/test_extension_skills.py
  - tests/orchestration/test_policy.py
decisions:
  - "Apply the same canonical routing contract to `tasks` as the other collaboration-aware workflows."
  - "Keep `explain` conservative by default and only justify fan-out for supporting cross-checks."
  - "Validate explain routing both at the shared template level and at generated-skill level."
metrics:
  completed_date: "2026-04-13"
---

# Phase 05 Plan 01: Tasks & Explain Collaboration Routing Summary

## One-liner
Extended the shared orchestration contract into `tasks` and `explain`, giving task generation explicit pre-decomposition strategy routing and keeping explanation fan-out conservative and join-pointed.

## Key Changes

### Tasks Workflow Contract
- Updated `templates/commands/tasks.md` so it now selects a collaboration strategy before task decomposition begins.
- Added explicit `tasks` lanes for story/phase decomposition, dependency analysis, and write-set / parallel-safety analysis.
- Added explicit join points before writing `tasks.md` and before emitting canonical parallel batches and join points.

### Explain Workflow Contract
- Updated `templates/commands/explain.md` so it now applies the shared strategy chooser before translating artifacts.
- Made the conservative default explicit: `explain` stays `single-agent` unless supporting cross-check work is justified.
- Added the required convergence point before the final explanation is rendered.

### Regression Coverage
- Added shared template assertions in `tests/test_alignment_templates.py`.
- Extended explain TUI and generated-skill contract checks in `tests/test_tui_visual_contract.py` and `tests/test_extension_skills.py`.
- Added generic policy tests proving the chooser remains command-agnostic for `tasks` and `explain`.

## Deviations from Plan
- No material deviation. One verification failure came from a case-sensitive test assertion for the explain default-routing sentence; the test was normalized to match the template's existing capitalization style.

## Known Stubs
- CLI/init messaging and broader integration hardening are still pending and belong to Phase 6.
- Runtime maturity work for `implement` and `debug` remains deferred to later milestones.

## Self-Check: PASSED
- [x] Shared strategy language added to `tasks`
- [x] Conservative routing language added to `explain`
- [x] Template, TUI, generated-skill, and policy regressions pass
