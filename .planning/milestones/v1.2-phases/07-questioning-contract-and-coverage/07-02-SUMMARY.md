---
phase: 07-questioning-contract-and-coverage
plan: 02
subsystem: docs
tags: [specify, clarification, ambiguity, testing]
requires:
  - phase: 07-questioning-contract-and-coverage
    provides: docs/config questioning gate and release-gate contract from plan 01
provides:
  - answer-aware clarification-loop rules for `sp-specify`
  - targeted handling for vague, shallow, and contradictory answers
  - regression coverage for FDEP-01 and FDEP-02
affects: [phase-08, phase-09]
tech-stack:
  added: []
  patterns: [answer-aware clarification prompts]
key-files:
  created: [.planning/phases/07-questioning-contract-and-coverage/07-02-SUMMARY.md]
  modified: [templates/commands/specify.md, tests/test_alignment_templates.py]
key-decisions:
  - "Clarification follow-up must build from the user's most recent answer instead of generic resets."
  - "Weak or contradictory answers require targeted narrowing tied to planning-critical ambiguity."
patterns-established:
  - "Follow-up rules stay one-question-at-a-time while remaining answer-aware."
  - "Template tests guard both the questioning surface and the clarification-loop contract."
requirements-completed: [FDEP-01, FDEP-02]
duration: 2 min
completed: 2026-04-14
---

# Phase 7 Plan 02: Questioning Contract and Coverage Summary

**Answer-aware follow-up and contradiction handling for `sp-specify` clarification**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-14T01:43:14+08:00
- **Completed:** 2026-04-14T01:44:51+08:00
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Required each clarification turn to build on the user's most recent answer instead of dropping back to generic prompts.
- Defined targeted handling for vague, shallow, and contradictory answers while keeping the workflow tied to planning-relevant ambiguity.
- Added regression assertions that lock in the new follow-up and contradiction-handling contract.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite the clarification loop for answer-aware follow-up** - `0f28fcd` (docs)
2. **Task 2: Strengthen contradiction and shallow-answer handling** - `7a7387d` (docs)
3. **Task 3: Add regression coverage for answer-aware follow-up and contradiction handling** - `a45fcad` (test)

## Files Created/Modified

- `templates/commands/specify.md` - expanded the clarification-loop contract with answer-aware and ambiguity-targeted follow-up rules
- `tests/test_alignment_templates.py` - added regression assertions for FDEP-01 and FDEP-02

## Decisions Made

- Keep the clarification loop structured and one-question-at-a-time even while making follow-up more adaptive.
- Tie stronger follow-up behavior to planning-relevant ambiguity rather than generic conversational depth.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 7 now has both the coverage contract and the follow-up-depth contract required by the milestone.
- Phase 8 can focus on guided interaction quality instead of repairing the base questioning logic.

---
*Phase: 07-questioning-contract-and-coverage*
*Completed: 2026-04-14*
