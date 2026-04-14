---
phase: 08-guided-follow-up-experience
plan: 02
subsystem: docs
tags: [specify, confirmation, experience, testing]
requires:
  - phase: 08-guided-follow-up-experience
    provides: guided interaction wording and confirmation-gate contract from plan 01
provides:
  - no-redirect common-flow wording for `sp-specify`
  - explicit pre-release confirmation-step language
  - regression assertions for common-flow experience expectations
affects: [phase-09]
tech-stack:
  added: []
  patterns: [experience-contract assertions for shared template flows]
key-files:
  created: [.planning/phases/08-guided-follow-up-experience/08-02-SUMMARY.md]
  modified: [templates/commands/specify.md, tests/test_alignment_templates.py]
key-decisions:
  - "Target docs/config flows should finish inside `sp-specify` once ambiguity is resolved."
  - "The confirmation gate should read as an explicit pre-release check, not just a final recap."
patterns-established:
  - "Experience expectations for `sp-specify` stay protected through phrase-level checks in `tests/test_alignment_templates.py`."
requirements-completed: [EXPQ-03]
duration: 1 min
completed: 2026-04-14
---

# Phase 8 Plan 02: Guided Follow-up Experience Summary

**Common-flow and pre-release confirmation wording for `sp-specify`**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-14T02:22:48+08:00
- **Completed:** 2026-04-14T02:23:14+08:00
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Made the confirmation gate read as an explicit pre-release check.
- Clarified that common target docs/config/process-change flows can finish inside `sp-specify` once ambiguity is resolved.
- Added regression assertions that protect the no-redirect common-flow contract.

## Task Commits

Each task was committed atomically where it produced file changes:

1. **Task 1: Add failing assertions for common-flow completion inside `sp-specify`** - `44f2ce8` (test)
2. **Task 2: Refine the confirmation and no-redirect wording in `specify`** - `96f2a4d` (docs)
3. **Task 3: Re-run the common-flow experience regression suite** - verification only, no file changes

## Files Created/Modified

- `templates/commands/specify.md` - clarified the explicit pre-release check and no-redirect target-flow behavior
- `tests/test_alignment_templates.py` - added common-flow experience assertions

## Decisions Made

- Keep common-flow guarantees in the shared template so later surface sync can mirror them without redefining behavior.
- Preserve compatibility-only language for `/sp.clarify` while making the normal target path stay inside `sp-specify`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Normalize assertion wording for stable phrase matching**
- **Found during:** Task 3 (Re-run the common-flow experience regression suite)
- **Issue:** The initial template wording capitalized the common-flow sentence, causing the new exact-match assertion to fail even though the behavior was present.
- **Fix:** Normalized the sentence to the exact asserted phrase so the regression check is stable and unambiguous.
- **Files modified:** templates/commands/specify.md
- **Verification:** `pytest tests/test_alignment_templates.py -q`
- **Committed in:** `96f2a4d`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** No scope change. The deviation only stabilized the contract wording for the new regression check.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 8 now establishes the guided interaction and common-flow contract needed by the milestone.
- Phase 9 can focus on surface alignment, generated skill mirror sync, and regression hardening across shipped surfaces.

---
*Phase: 08-guided-follow-up-experience*
*Completed: 2026-04-14*
