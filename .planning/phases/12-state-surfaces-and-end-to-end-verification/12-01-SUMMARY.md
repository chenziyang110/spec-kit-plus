---
phase: 12-state-surfaces-and-end-to-end-verification
plan: 01
subsystem: docs
tags: [state-surfaces, runtime-summary, implement, codex, testing]
requires:
  - phase: 11-worker-dispatch-and-failure-convergence
    provides: join-point, retry, and blocker runtime truth
provides:
  - surfaced runtime summary output
  - shared/generated implement wording aligned to runtime truth
  - regression coverage for surfaced runtime semantics
affects: [12-02, milestone-audit]
tech-stack:
  added: []
  patterns: [runtime-summary surfacing, shared/generated surface alignment]
key-files:
  created:
    - .planning/phases/12-state-surfaces-and-end-to-end-verification/12-01-SUMMARY.md
  modified:
    - src/specify_cli/codex_team/commands.py
    - src/specify_cli/codex_team/runtime_bridge.py
    - templates/commands/implement.md
    - .agents/skills/sp-implement/SKILL.md
    - src/specify_cli/integrations/codex/__init__.py
    - tests/test_alignment_templates.py
    - tests/integrations/test_integration_codex.py
    - tests/contract/test_codex_team_cli_api_surface.py
    - tests/codex_team/test_commands.py
key-decisions:
  - "Surface runtime truth through existing CLI/status channels instead of inventing a new reporting subsystem."
  - "Keep the shared implement template as the primary wording source and mirror it into Codex-specific generated surfaces."
patterns-established:
  - "Runtime wording must explicitly mention join points, retry-pending work, and blockers."
  - "Shared template, generated Codex skill, and runtime status payload should be tied by phrase-level regressions."
requirements-completed: [STAT-01, STAT-02]
duration: 1 session
completed: 2026-04-14
---

# Phase 12 Plan 01: State Surfaces and End-to-End Verification Summary

**Surfaced runtime truth across status output, shared implement wording, and generated Codex surfaces**

## Performance

- **Duration:** 1 session
- **Completed:** 2026-04-14T15:20:00+08:00
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added human-readable runtime summary output that explicitly mentions worker outcomes, join points, retry-pending work, and blockers.
- Updated the shared `implement` contract and generated Codex `sp-implement` wording so surfaced runtime truth is no longer implicit.
- Added targeted regressions tying template wording, generated skill output, and API status payloads together.

## Task Commits

1. **Task 1: Add failing regression coverage for surfaced runtime truth and generated implement alignment** - `bb10007` (`feat(phase-12): surface runtime truth across docs and generated outputs`)
2. **Task 2: Surface runtime truth into planning and project state artifacts** - `bb10007` (`feat(phase-12): surface runtime truth across docs and generated outputs`)
3. **Task 3: Align shared and generated implement surfaces with the surfaced runtime truth** - `bb10007` (`feat(phase-12): surface runtime truth across docs and generated outputs`)

## Files Created/Modified

- `src/specify_cli/codex_team/commands.py` - surfaced runtime summary string now includes join points, retry-pending work, and blockers
- `src/specify_cli/codex_team/runtime_bridge.py` - status payload now exposes `runtime_state_summary`
- `templates/commands/implement.md` - shared implement contract now mentions retry/blocker truth explicitly
- `.agents/skills/sp-implement/SKILL.md` - checked-in Codex skill mirror now carries surfaced runtime wording
- `src/specify_cli/integrations/codex/__init__.py` - generated Codex skill addendum now injects matching wording
- `tests/test_alignment_templates.py` - template regressions cover surfaced runtime semantics
- `tests/integrations/test_integration_codex.py` - generated-skill regressions cover surfaced runtime semantics
- `tests/contract/test_codex_team_cli_api_surface.py` - API status contract covers surfaced runtime summary
- `tests/codex_team/test_commands.py` - focused runtime summary wording regression

## Decisions Made

- Use the existing status and generated-template surfaces as the “state truth source” for users rather than adding a separate dashboard.
- Phrase-level alignment tests are sufficient and preferable to snapshots for this surface layer.

## Deviations from Plan

None.

## Issues Encountered

- Subagent handoffs remained unreliable in this environment, so the phase was executed inline with direct regression validation.

## User Setup Required

None.

## Next Phase Readiness

- Release-facing docs and end-to-end verification can now rely on surfaced runtime wording that already matches the shared and generated implement surfaces.

---
*Phase: 12-state-surfaces-and-end-to-end-verification*
*Completed: 2026-04-14*
