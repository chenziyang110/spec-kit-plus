---
phase: 07-questioning-contract-and-coverage
plan: 01
subsystem: docs
tags: [specify, alignment, questioning, testing]
requires:
  - phase: 06-analysis-and-planning-workflows
    provides: shared alignment-first workflow contract
provides:
  - docs/config/process-change questioning contract for `sp-specify`
  - classification-aware release gating for planning-critical ambiguity
  - regression coverage for QCOV-01, QCOV-02, and QCOV-03
affects: [07-02, phase-08, phase-09]
tech-stack:
  added: []
  patterns: [contract-driven template assertions]
key-files:
  created: [.planning/phases/07-questioning-contract-and-coverage/07-01-SUMMARY.md]
  modified: [templates/commands/specify.md, tests/test_alignment_templates.py]
key-decisions:
  - "Treat docs/config/process changes as planning-critical discovery, not passive cleanup."
  - "Keep `Aligned: ready for plan` blocked while planning-critical ambiguity remains."
patterns-established:
  - "Task classification determines which requirement dimensions `sp-specify` must probe."
  - "Template contract changes require phrase-level regression assertions in `tests/test_alignment_templates.py`."
requirements-completed: [QCOV-01, QCOV-02, QCOV-03]
duration: 4 min
completed: 2026-04-14
---

# Phase 7 Plan 01: Questioning Contract and Coverage Summary

**Docs/config questioning gates and planning-critical release rules for `sp-specify`**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-14T01:35:02+08:00
- **Completed:** 2026-04-14T01:39:33+08:00
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Made the docs/config/process-change path explicitly collect the planning-critical requirement dimensions before normal alignment release.
- Added classification-aware wording that ties question selection and release eligibility to planning-critical ambiguity.
- Added regression assertions that lock QCOV coverage and release-gate behavior into the shared template test suite.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tighten docs/config/process-change requirement coverage in `specify`** - `cd7a0c3` (docs)
2. **Task 2: Strengthen task-classification branching and ambiguity release rules** - `3c28bce` (docs)
3. **Task 3: Add regression assertions for task-type coverage and release-gate behavior** - `5cc0ad1` (test)

## Files Created/Modified

- `templates/commands/specify.md` - strengthened the planning-facing docs/config gate and the alignment release conditions
- `tests/test_alignment_templates.py` - added regression assertions for QCOV coverage and release-gate behavior

## Decisions Made

- Keep the docs/config/process-change gate phrased as required questioning, not a passive checklist.
- Express the release gate in terms of planning-critical ambiguity so later phases can build on the same contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Split Wave 1 and Wave 2 regression expectations**
- **Found during:** Task 3 (Add regression assertions for task-type coverage and release-gate behavior)
- **Issue:** The first draft of the test update bundled follow-up-depth assertions that belong to Plan 07-02, which prevented Plan 07-01 from verifying independently.
- **Fix:** Narrowed the Wave 1 test commit to QCOV-focused assertions only so 07-01 can pass cleanly before 07-02 adds the follow-up contract assertions.
- **Files modified:** tests/test_alignment_templates.py
- **Verification:** `pytest tests/test_alignment_templates.py -q`
- **Committed in:** `5cc0ad1`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Kept the plan boundaries clean without changing scope. Wave 2 still owns the follow-up-depth regression work.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 07-02 can now build on the stronger questioning and release-gate contract.
- Remaining work is limited to answer-aware follow-up and contradiction handling.

---
*Phase: 07-questioning-contract-and-coverage*
*Completed: 2026-04-14*
