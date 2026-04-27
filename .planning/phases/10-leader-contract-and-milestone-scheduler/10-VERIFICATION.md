---
phase: 10-leader-contract-and-milestone-scheduler
status: passed
verified: 2026-04-14
requirements:
  - ORCH-01
  - ORCH-02
  - LEAD-01
  - LEAD-02
score: 4/4
human_verification: []
---

# Phase 10 Verification

## Goal

Redefine `sp-implement` so the invoking runtime acts only as the leader while it schedules the next executable work across the full milestone.

## Automated Checks

- `pytest tests/test_alignment_templates.py tests/codex_team/test_implement_runtime_routing.py tests/orchestration/test_policy.py tests/integrations/test_integration_codex.py -q`

## Must-Have Verification

### 1. `/sp.implement` describes and enforces a leader-only role instead of leader self-execution

Status: PASS

Evidence:
- `templates/commands/implement.md:156-165` states that the invoking runtime acts as the leader, treats `single-lane` as a delegated worker lane, and keeps the shared template as the primary source of truth.
- `tests/codex_team/test_implement_runtime_routing.py:57-66` and `tests/test_alignment_templates.py:257-260` fail if that leader-only wording drifts.

### 2. The runtime can determine the next executable phase and ready batch from roadmap order, task dependencies, and current state

Status: PASS

Evidence:
- `src/specify_cli/orchestration/models.py:43-68` defines `PhaseExecutionState` and `MilestoneExecutionDecision` with milestone continuation fields.
- `src/specify_cli/orchestration/state_store.py:35-40` provides canonical `milestone_state_path` and `decision_path` helpers for persisted scheduler state.
- `src/specify_cli/orchestration/scheduler.py:54-108` implements `select_next_phase` and `build_milestone_execution_decision` with roadmap-order continuation behavior.

### 3. Sequential execution still routes through delegated worker lanes rather than leader self-execution

Status: PASS

Evidence:
- `templates/commands/implement.md:165-174` explicitly says `single-lane` means one delegated worker lane and that the leader re-evaluates milestone state after each completed batch.
- `.agents/skills/sp-implement/SKILL.md:226-237` and `src/specify_cli/integrations/codex/__init__.py:82-93` mirror the same delegated sequential semantics in the shipped Codex surface.
- `tests/integrations/test_integration_codex.py:82-85` verifies the generated Codex skill inherits those phrases.

### 4. The active milestone can continue past the first completed phase without requiring a manual restart for each later phase

Status: PASS

Evidence:
- `templates/commands/implement.md:174` states that after each completed batch the leader selects the next executable phase and ready batch in roadmap order and continues automatically until the milestone is complete or blocked.
- `.agents/skills/sp-implement/SKILL.md:237` and `src/specify_cli/integrations/codex/__init__.py:93` preserve the same continuation wording for shipped/generated Codex guidance.
- `pytest tests/test_alignment_templates.py tests/codex_team/test_implement_runtime_routing.py tests/orchestration/test_policy.py tests/integrations/test_integration_codex.py -q` passed on 2026-04-14.

## Review Inputs

- `10-01-SUMMARY.md`
- `10-02-SUMMARY.md`
- `10-REVIEW.md`

## Result

Phase 10 passed verification. The shared implement contract, orchestration scheduler primitives, and shipped Codex surface now agree on a leader-only milestone scheduler that continues through roadmap-ordered ready work using delegated worker semantics.
