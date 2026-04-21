---
phase: 11-worker-dispatch-and-failure-convergence
plan: 02
subsystem: codex
tags: [codex-team, failures, retries, blocker-state, testing]
requires:
  - phase: 11-worker-dispatch-and-failure-convergence
    provides: classified batch and join-point policy from plan 01
provides:
  - runtime failure taxonomy
  - retry-pending status for transient failures
  - blocker escalation for critical batch convergence failures
affects: [phase-12-state-surfaces, runtime-reporting]
tech-stack:
  added: []
  patterns: [failure classification, bounded retries, blocked-session escalation]
key-files:
  created:
    - .planning/phases/11-worker-dispatch-and-failure-convergence/11-02-SUMMARY.md
  modified:
    - src/specify_cli/codex_team/manifests.py
    - src/specify_cli/codex_team/runtime_bridge.py
    - src/specify_cli/codex_team/task_ops.py
    - src/specify_cli/codex_team/batch_ops.py
    - tests/codex_team/test_manifests.py
    - tests/codex_team/test_dispatch_record.py
    - tests/codex_team/test_auto_dispatch.py
    - tests/contract/test_codex_team_auto_dispatch_cli.py
key-decisions:
  - "Use `retry_pending` for transient runtime failures that still have retry budget."
  - "Escalate critical or repeated batch failures into explicit blocked-session state rather than hiding them inside task status alone."
patterns-established:
  - "Failure classification must be persisted in dispatch/session records, not reconstructed later from plain status strings."
  - "Mixed-tolerance batches can become blocked without forcing the whole runtime session into failed state."
requirements-completed: [FAIL-01, FAIL-02, FAIL-03]
duration: 1 session
completed: 2026-04-14
---

# Phase 11 Plan 02: Worker Dispatch and Failure Convergence Summary

**Added runtime failure taxonomy, retry-pending behavior, and blocker escalation for worker batch convergence**

## Performance

- **Duration:** 1 session
- **Completed:** 2026-04-14T14:05:00+08:00
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Extended runtime session and dispatch records with `failure_class`, retry counters, and `blocker_id`.
- Added transient-failure handling that keeps runtime state at `retry_pending` while retry budget remains.
- Updated batch convergence so mixed-tolerance non-critical failures block the affected join point without immediately failing the entire session, while critical failures escalate to blocked-session state.

## Task Commits

1. **Task 1: Add failing regression coverage for failure taxonomy, retry eligibility, and blocker persistence** - `b91181c` (`feat(phase-11): add batch policy and runtime failure taxonomy`)
2. **Task 2: Implement failure classification and bounded retry metadata in runtime records** - `b91181c` (`feat(phase-11): add batch policy and runtime failure taxonomy`)
3. **Task 3: Escalate critical and repeated failures into truthful batch/session blocker state** - `960784b` (`feat(phase-11): converge worker batches and blocker handling`)

## Files Created/Modified

- `src/specify_cli/codex_team/manifests.py` - adds session and dispatch failure metadata fields
- `src/specify_cli/codex_team/runtime_bridge.py` - classifies runtime failures and exposes `retry_pending`
- `src/specify_cli/codex_team/task_ops.py` - records task-level `failure_class` on terminal transitions
- `src/specify_cli/codex_team/batch_ops.py` - converges non-critical mixed-tolerance failures as `blocked` and critical failures as blocked-session escalation
- `tests/codex_team/test_manifests.py` - verifies failure metadata round-trips
- `tests/codex_team/test_dispatch_record.py` - verifies critical vs transient runtime failure persistence
- `tests/codex_team/test_auto_dispatch.py` - verifies mixed-tolerance non-critical failures block join points without failing the session
- `tests/contract/test_codex_team_auto_dispatch_cli.py` - remains green against the updated runtime state behavior

## Decisions Made

- Non-critical failures in mixed-tolerance batches should block the affected join point but not mark the whole session failed.
- Critical convergence failures should be visible as session-level blockers using a stable `blocker_id`.

## Deviations from Plan

None.

## Issues Encountered

- Environment-level subagent handoffs stalled repeatedly, so execution proceeded inline with direct regression validation.

## User Setup Required

None.

## Next Phase Readiness

- Phase 12 can now expose blocked versus retry-pending versus failed runtime truth in planning artifacts and generated surfaces.
- The milestone runtime has enough structured state to support phase-level reporting and end-to-end verification.

---
*Phase: 11-worker-dispatch-and-failure-convergence*
*Completed: 2026-04-14*
