---
phase: 09-surface-alignment-and-regression-hardening
plan: 02
subsystem: docs
tags: [quickstart, workflow-guidance, specify, testing]
requires:
  - phase: 09-surface-alignment-and-regression-hardening
    provides: synced local skill mirror and stronger skill-surface assertions from plan 01
provides:
  - truthful quickstart workflow guidance
  - focused regression checks for `specify -> plan` mainline wording
  - compatibility-only clarify positioning in release-facing docs
affects: []
tech-stack:
  added: []
  patterns: [focused doc assertions, workflow-guidance consistency]
key-files:
  created:
    - .planning/phases/09-surface-alignment-and-regression-hardening/09-02-SUMMARY.md
    - tests/test_specify_guidance_docs.py
  modified: [docs/quickstart.md]
key-decisions:
  - "Teach `specify -> plan` as the default path in quickstart instead of treating clarify as a normal required step."
  - "Keep `spec-extend` optional and `clarify` compatibility-only in release-facing docs."
patterns-established:
  - "User-facing workflow guidance should be protected by a dedicated lightweight regression test file."
requirements-completed: [SYNC-02, SYNC-03]
duration: 1 session
completed: 2026-04-14
---

# Phase 9 Plan 02: Surface Alignment and Regression Hardening Summary

**Aligned the quickstart workflow guidance and added doc regression coverage**

## Performance

- **Duration:** 1 session
- **Completed:** 2026-04-14T09:48:30+08:00
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Updated `docs/quickstart.md` so it now teaches `specify -> plan` as the mainline workflow.
- Added `tests/test_specify_guidance_docs.py` to catch drift in quickstart wording around `specify`, `plan`, `spec-extend`, and `clarify`.
- Verified the guidance regression suite passes against the updated docs.

## Task Commits

No new commits were created in this session.

## Files Created/Modified

- `docs/quickstart.md` - replaced the old clarify-heavy flow with the new mainline guidance
- `tests/test_specify_guidance_docs.py` - added focused workflow-guidance assertions

## Decisions Made

- Keep the quickstart concise and practical rather than turning it into migration-only commentary.
- Check the quickstart against `README.md` and `AGENTS.md` instead of duplicating their full guidance.

## Deviations from Plan

None.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- Phase 9 now covers both surface alignment and release-facing workflow truthfulness.
- Milestone verification can use the quickstart and new doc regression tests as evidence for SYNC-03.

---
*Phase: 09-surface-alignment-and-regression-hardening*
*Completed: 2026-04-14*
