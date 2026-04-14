---
phase: 07-questioning-contract-and-coverage
status: passed
verified: 2026-04-14
requirements:
  - QCOV-01
  - QCOV-02
  - QCOV-03
  - FDEP-01
  - FDEP-02
score: 4/4
human_verification: []
---

# Phase 07 Verification

## Goal

Redefine the `sp-specify` questioning contract so it covers the right requirement dimensions and reacts more intelligently to ambiguity.

## Automated Checks

- `pytest tests/test_alignment_templates.py -q`

## Must-Have Verification

### 1. Docs/config/process changes ask for planning-critical dimensions

Status: PASS

Evidence:
- `templates/commands/specify.md:186` defines the `Docs/config/process change:` gate.
- `templates/commands/specify.md:187-193` requires changed artifact, change objective, affected users or teams, compatibility/process constraints, validation method, and completion criteria before normal alignment release.
- `tests/test_alignment_templates.py:77-81` asserts the presence of the docs/config contract and planning-critical release wording.

### 2. Task classification changes the questioning path

Status: PASS

Evidence:
- `templates/commands/specify.md:101` states that task classification changes which requirement dimensions are probed.
- `templates/commands/specify.md:186-193` gives the docs/config classification its own required questioning path.
- `tests/test_alignment_templates.py:80` guards the classification-aware probing contract.

### 3. Vague or contradictory answers trigger targeted follow-up

Status: PASS

Evidence:
- `templates/commands/specify.md:234-239` requires the next question to build on the previous answer and to react to vague, shallow, or contradictory input with targeted narrowing.
- `templates/commands/specify.md:237` prevents long but still ambiguous answers from being accepted as sufficient.
- `tests/test_alignment_templates.py:82-87` locks the answer-aware and contradiction-handling phrases into regression coverage.

### 4. Planning-critical ambiguity blocks normal planning-ready release

Status: PASS

Evidence:
- `templates/commands/specify.md:227` keeps the workflow in clarification when planning-critical ambiguity remains.
- `templates/commands/specify.md:341` blocks `Aligned: ready for plan` until ambiguity is resolved or the user explicitly chooses `Force proceed with known risks`.
- `tests/test_alignment_templates.py:81` guards the planning-critical ambiguity language.

## Review Inputs

- `07-01-SUMMARY.md`
- `07-02-SUMMARY.md`
- `07-REVIEW.md`

## Result

Phase 07 passed verification. The shared `sp-specify` template now captures both the planning-critical question surface and the answer-aware clarification behavior required by the roadmap.
