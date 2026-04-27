---
phase: 10-leader-contract-and-milestone-scheduler
plan: 02
subsystem: codex
tags: [codex, implement, skills, integration, testing]
requires:
  - phase: 10-leader-contract-and-milestone-scheduler
    provides: leader-only implement contract and milestone scheduler primitives
provides:
  - Codex skill addendum aligned with the shared leader-only contract
  - generated-skill regression coverage for milestone continuation wording
  - integration post-processing that preserves delegated single-lane semantics
affects: [codex-init, skill-generation, implement-runtime]
tech-stack:
  added: []
  patterns: [shared-template-first Codex alignment, generated-skill contract assertions]
key-files:
  created:
    - .planning/phases/10-leader-contract-and-milestone-scheduler/10-02-SUMMARY.md
  modified:
    - .agents/skills/sp-implement/SKILL.md
    - src/specify_cli/integrations/codex/__init__.py
    - tests/integrations/test_integration_codex.py
    - templates/commands/implement.md
    - src/specify_cli/orchestration/scheduler.py
key-decisions:
  - "Keep `specify team` as the Codex interpretation of `sidecar-runtime` without changing the shared strategy vocabulary."
  - "Assert generated skill wording directly so Codex packaging cannot drift from the shared template."
patterns-established:
  - "Codex addenda may specialize runtime behavior, but they must repeat the shared leader-only contract instead of replacing it."
  - "Generated skill tests should assert the same core contract phrases that the shared template exposes."
requirements-completed: [ORCH-01, LEAD-02]
duration: 1 session
completed: 2026-04-14
---

# Phase 10 Plan 02: Leader Contract and Milestone Scheduler Summary

**Codex-generated `sp-implement` guidance now mirrors the shared leader-only milestone scheduler contract**

## Performance

- **Duration:** 1 session
- **Completed:** 2026-04-14T12:40:00+08:00
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Updated the checked-in Codex skill mirror so it states the leader-only contract, delegated `single-lane` semantics, and milestone continuation loop explicitly.
- Updated Codex integration post-processing to inject the same contract phrases into generated `sp-implement` skills.
- Added generated-skill regression assertions that fail if the Codex surface stops mirroring the shared template contract.

## Task Commits

1. **Task 1: Update the implement flow for milestone continuation and delegated sequential execution** - `75df7eb` (`docs(implement): define leader-only milestone scheduler contract`)
2. **Task 2: Align the shipped Codex skill and integration post-processing with the shared contract** - `347bed9` (`feat(codex): align implement skill with leader-only scheduler`)
3. **Task 3: Add regression coverage for delegated sequential semantics and generated-skill alignment** - `347bed9` (`feat(codex): align implement skill with leader-only scheduler`)

## Files Created/Modified

- `.agents/skills/sp-implement/SKILL.md` - mirrors the leader-only contract and Codex-specific `sidecar-runtime` escalation path
- `src/specify_cli/integrations/codex/__init__.py` - injects the same leader-only wording into generated skills during setup
- `tests/integrations/test_integration_codex.py` - asserts the generated `sp-implement` skill contains the core leader-only contract phrases
- `templates/commands/implement.md` - supplies the shared contract wording the Codex surface now inherits
- `src/specify_cli/orchestration/scheduler.py` - continues to serve as the concrete scheduler API named by the contract

## Decisions Made

- Keep the Codex addendum subordinate to the shared template by explicitly saying the shared implement template remains the primary source of truth.
- Use phrase-level assertions in integration tests instead of snapshots so wording drift is obvious without overfitting formatting.

## Deviations from Plan

None.

## Issues Encountered

- The initial generated-skill regression extension failed because the new leader-only phrases were not yet present in either the shared template or the Codex addendum; both surfaces were updated together to restore alignment.

## User Setup Required

None.

## Next Phase Readiness

- Codex skill generation now preserves the shared leader-only contract and milestone continuation semantics during `init`.
- Phase-level verification can treat the shared template, Codex generator, and generated skill regression as aligned evidence for milestone runtime behavior.

---
*Phase: 10-leader-contract-and-milestone-scheduler*
*Completed: 2026-04-14*
