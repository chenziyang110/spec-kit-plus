---
phase: 10-leader-contract-and-milestone-scheduler
plan: 01
subsystem: orchestration
tags: [implement, scheduler, orchestration, codex, testing]
requires: []
provides:
  - explicit milestone scheduler primitives in the orchestration core
  - leader-only implement contract in the shared template
  - regression coverage for leader-only runtime wording
affects: [10-02, implement-runtime, codex-skill-generation]
tech-stack:
  added: []
  patterns: [leader-only runtime contract, roadmap-aware scheduler primitives, phrase-level regression assertions]
key-files:
  created:
    - .planning/phases/10-leader-contract-and-milestone-scheduler/10-01-SUMMARY.md
  modified:
    - templates/commands/implement.md
    - src/specify_cli/orchestration/models.py
    - src/specify_cli/orchestration/state_store.py
    - src/specify_cli/orchestration/__init__.py
    - src/specify_cli/orchestration/scheduler.py
    - tests/test_alignment_templates.py
    - tests/codex_team/test_implement_runtime_routing.py
key-decisions:
  - "Treat the shared implement template as the canonical leader-only contract and keep Codex-specific wording downstream from it."
patterns-established:
  - "Leader-oriented workflow wording must stay in the shared template and be protected with focused phrase assertions."
  - "Milestone scheduler helpers should express roadmap-order continuation explicitly in orchestration models, state paths, and decision helpers."
requirements-completed: [ORCH-02, LEAD-01]
duration: 1 session
completed: 2026-04-14
---

# Phase 10 Plan 01: Leader Contract and Milestone Scheduler Summary

**Shipped milestone scheduler primitives now line up with a leader-only shared implement contract**

## Performance

- **Duration:** 1 session
- **Completed:** 2026-04-14T12:40:00+08:00
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Confirmed the orchestration baseline already exposed `PhaseExecutionState`, `MilestoneExecutionDecision`, milestone decision paths, and roadmap-aware scheduler helpers required by the plan.
- Updated the shared `implement` template so it explicitly describes the invoking runtime as a leader that selects the next executable phase and ready batch instead of executing implementation directly.
- Verified the leader-only contract against the template and Codex runtime routing regression suites.

## Task Commits

1. **Task 1: Add milestone scheduler models and persistence helpers** - `31551d6` (`feat(10-01): add milestone scheduler state primitives`)
2. **Task 2: Create a roadmap-aware scheduler helper for next-ready work selection** - `74296d6` (`feat(10-01): add roadmap-aware milestone scheduler`)
3. **Task 3: Rewrite the shared implement contract around leader-only scheduling** - `67fb921` (`test(10-01): add failing leader-only implement contract coverage`), `75df7eb` (`docs(implement): define leader-only milestone scheduler contract`)

## Files Created/Modified

- `templates/commands/implement.md` - establishes the leader-only scheduler contract, delegated worker-lane wording, and milestone continuation loop
- `src/specify_cli/orchestration/models.py` - adds explicit scheduler-facing milestone dataclasses
- `src/specify_cli/orchestration/state_store.py` - adds canonical milestone and decision path helpers
- `src/specify_cli/orchestration/__init__.py` - re-exports the scheduler-facing orchestration symbols
- `src/specify_cli/orchestration/scheduler.py` - adds roadmap-order selection and continuation decisions
- `tests/test_alignment_templates.py` - locks the shared contract wording to the leader-only scheduler model
- `tests/codex_team/test_implement_runtime_routing.py` - proves the runtime-facing surface preserves the same contract

## Decisions Made

- Make the shared template, not the Codex addendum, the first place the leader-only contract is stated.

## Deviations from Plan

### Auto-fixed Issues

**1. Shared contract wording lagged behind the new scheduler primitives**
- **Found during:** Task 3 red test run
- **Issue:** The scheduler code and state helpers existed, but the shared template still failed the leader-only wording assertions.
- **Fix:** Added failing coverage first in `tests/test_alignment_templates.py` and `tests/codex_team/test_implement_runtime_routing.py`, then updated `templates/commands/implement.md` to state the leader-only next-phase contract explicitly.
- **Files modified:** `tests/test_alignment_templates.py`, `tests/codex_team/test_implement_runtime_routing.py`, `templates/commands/implement.md`
- **Verification:** `pytest tests/test_alignment_templates.py tests/codex_team/test_implement_runtime_routing.py -q`
- **Committed in:** `67fb921`, `75df7eb`

## Issues Encountered

- A background executor agent stalled without returning artifacts, so execution resumed inline on the main workspace with direct verification.

## User Setup Required

None.

## Next Phase Readiness

- The shared implement surface now states the leader-only scheduler contract clearly enough for Codex-specific surfaces to mirror it in Plan 02.
- The scheduler primitives are available for milestone continuation and delegated worker-lane routing.

---
*Phase: 10-leader-contract-and-milestone-scheduler*
*Completed: 2026-04-14*
