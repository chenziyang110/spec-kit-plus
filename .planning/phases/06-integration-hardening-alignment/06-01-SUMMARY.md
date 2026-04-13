---
phase: 06-integration-hardening-alignment
plan: 01
subsystem: docs-and-integration-surfaces
tags: [readme, cli, integration-tests, codex-isolation]
requirements: [MSG-01, QLT-01, QLT-02]
tech-stack: [markdown, pytest, typer]
key-files:
  - README.md
  - src/specify_cli/__init__.py
  - tests/integrations/test_cli.py
  - tests/integrations/test_integration_codex.py
  - tests/test_extension_skills.py
  - tests/codex_team/test_release_scope_docs.py
decisions:
  - "Describe the repository as Milestones 1-2 implemented rather than leaving README frozen at a Milestone 1-only state."
  - "Keep Codex runtime guidance isolated to Codex-specific runtime surfaces while shared workflow skills expose the canonical strategy vocabulary."
  - "Extend generated-skill integration tests so shared analysis/planning surfaces are covered, not just `implement`."
metrics:
  completed_date: "2026-04-13"
---

# Phase 06 Plan 01: Integration Hardening & Alignment Summary

## One-liner
Aligned README, built-in workflow descriptions, and generated integration surfaces with the Milestone 2 collaboration state while preserving Codex-only runtime isolation.

## Key Changes

### Documentation and CLI Copy
- Updated `README.md` to describe the repository as having Milestones 1-2 orchestration work in place.
- Updated built-in `SKILL_DESCRIPTIONS` in `src/specify_cli/__init__.py` so `specify`, `plan`, `tasks`, and `explain` now advertise their shared collaboration-routing behavior.

### Generated Skill Surface Coverage
- Added a non-Codex integration test that verifies `sp-specify`, `sp-plan`, `sp-tasks`, and `sp-explain` all contain the canonical strategy vocabulary without leaking Codex runtime wording.
- Added a Codex integration test that proves shared workflow skills stay runtime-neutral while `sp-implement` still carries Codex runtime escalation guidance where intended.

### README Regression Hardening
- Extended README regression coverage so the release-scope docs keep mentioning the canonical strategy names alongside Codex-only runtime isolation guidance.

## Deviations from Plan
- No material deviation.

## Known Stubs
- Milestone lifecycle archival and cleanup are still pending and handled separately from the phase implementation work.
- Runtime maturity for `implement` and `debug` remains future work.

## Self-Check: PASSED
- [x] README reflects Milestone 2 routing state
- [x] Built-in workflow descriptions reflect the expanded routing surface
- [x] Generated shared workflow skill surfaces are covered by integration tests
