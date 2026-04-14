---
phase: 09-surface-alignment-and-regression-hardening
plan: 01
subsystem: docs
tags: [specify, skills, alignment, testing]
requires:
  - phase: 08-guided-follow-up-experience
    provides: guided interaction, confirmation gate, and no-redirect `sp-specify` contract
provides:
  - synced local `sp-specify` skill mirror
  - regression assertions for the stronger skill surface
  - compatibility-only clarify guidance in the mirrored skill
affects: [09-02]
tech-stack:
  added: []
  patterns: [template-to-skill mirror sync, focused regression assertions]
key-files:
  created: [.planning/phases/09-surface-alignment-and-regression-hardening/09-01-SUMMARY.md]
  modified: [.agents/skills/sp-specify/SKILL.md, tests/test_extension_skills.py]
key-decisions:
  - "Treat `templates/commands/specify.md` as the source of truth and mirror its body into the local skill surface."
  - "Protect the stronger skill contract with phrase-level assertions instead of brittle snapshots."
patterns-established:
  - "When the shared `specify` contract changes, the local skill mirror and extension-skill regression coverage must advance together."
requirements-completed: [SYNC-01, SYNC-02]
duration: 1 session
completed: 2026-04-14
---

# Phase 9 Plan 01: Surface Alignment and Regression Hardening Summary

**Synced the local `sp-specify` skill mirror and hardened skill-surface regression coverage**

## Performance

- **Duration:** 1 session
- **Completed:** 2026-04-14T09:48:30+08:00
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Re-synced `.agents/skills/sp-specify/SKILL.md` to the stronger shared `templates/commands/specify.md` contract.
- Extended `tests/test_extension_skills.py` so the repo skill mirror must keep the guided-discovery, scaffolding, confirmation-gate, and no-redirect wording.
- Verified the focused extension-skill regression suite passes against the updated mirror.

## Task Commits

No new commits were created in this session.

## Files Created/Modified

- `.agents/skills/sp-specify/SKILL.md` - mirrored the current shared `sp-specify` contract into the local Codex skill surface
- `tests/test_extension_skills.py` - added and verified stronger repo-mirror assertions

## Decisions Made

- Keep the skill frontmatter stable while replacing the mirrored body from the shared template source.
- Preserve compatibility-only `/sp.clarify` guidance and optional `/sp.spec-extend` wording in the mirrored surface.

## Deviations from Plan

### Auto-fixed Issues

**1. Rewrite the mirrored skill file as UTF-8**
- **Found during:** Focused regression run
- **Issue:** The first mirror rewrite used a non-UTF-8 encoding and caused the repo-skill regression test to fail during file read.
- **Fix:** Rewrote `.agents/skills/sp-specify/SKILL.md` explicitly as UTF-8 without changing content.
- **Verification:** `pytest tests/test_extension_skills.py -q`

## Issues Encountered

None after the UTF-8 rewrite.

## User Setup Required

None.

## Next Phase Readiness

- Plan 09-02 can align release-facing docs to the same `specify -> plan` guidance.
- Phase 9 verification can now use the updated mirror as evidence for SYNC-01.

---
*Phase: 09-surface-alignment-and-regression-hardening*
*Completed: 2026-04-14*
