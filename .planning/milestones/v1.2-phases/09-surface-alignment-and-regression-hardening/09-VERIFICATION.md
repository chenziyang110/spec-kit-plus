---
phase: 09-surface-alignment-and-regression-hardening
status: passed
verified: 2026-04-14
requirements:
  - SYNC-01
  - SYNC-02
  - SYNC-03
score: 3/3
human_verification: []
---

# Phase 09 Verification

## Goal

Align shipped surfaces and regression coverage so the stronger `sp-specify` behavior stays truthful and stable.

## Automated Checks

- `pytest tests/test_extension_skills.py -q`
- `pytest tests/test_specify_guidance_docs.py -q`

## Must-Have Verification

### 1. The local `sp-specify` skill mirror matches the stronger shared contract

Status: PASS

Evidence:
- `.agents/skills/sp-specify/SKILL.md:224` requires the interaction to feel like guided requirement discovery.
- `.agents/skills/sp-specify/SKILL.md:235` preserves recommendation and example scaffolding in the mirrored skill surface.
- `.agents/skills/sp-specify/SKILL.md:337-341` keeps the confirmation gate and no-redirect `sp-specify` path.

### 2. Regression tests fail if the stronger skill and workflow guidance drift

Status: PASS

Evidence:
- `tests/test_extension_skills.py:380-384` asserts the mirrored skill keeps guided-discovery, scaffolding, confirmation-gate, and no-redirect wording.
- `tests/test_specify_guidance_docs.py:11-27` asserts quickstart mainline and compatibility-only workflow guidance.
- `pytest tests/test_extension_skills.py -q` and `pytest tests/test_specify_guidance_docs.py -q` both passed on 2026-04-14.

### 3. User-facing guidance teaches `specify -> plan` while keeping clarify compatibility-only

Status: PASS

Evidence:
- `docs/quickstart.md:50` tells users to move directly from `/speckit.specify` to `/speckit.plan`.
- `docs/quickstart.md:56` keeps `/speckit.spec-extend` optional and `/speckit.clarify` compatibility-only.
- `docs/quickstart.md:162-164` reinforces the same workflow guidance in the principles section.

## Review Inputs

- `09-01-SUMMARY.md`
- `09-02-SUMMARY.md`
- `09-REVIEW.md`

## Result

Phase 09 passed verification. The stronger `sp-specify` contract is now aligned across the local skill mirror, quickstart guidance, and focused regression coverage.
