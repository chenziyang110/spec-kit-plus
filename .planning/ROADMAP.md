# Roadmap: spec-kit-plus

## Overview

The roadmap now moves from stronger planning-time questioning into deeper execution-time orchestration. Milestone v1.3 focuses on one specific product gap: `sp-implement` still cannot reliably drive a whole milestone to completion because the invoking agent remains the executor, phase progression stops too early, and worker results do not converge into a durable milestone-level loop. The execution path for this milestone is to first establish a leader-only scheduler contract, then ship worker dispatch and mixed failure handling, and finally align state artifacts, shipped surfaces, and regression coverage around the new runtime.

## Milestones

- Good **v1.0 Debug Workflow** - Phases 1-3 (shipped 2026-04-13)
- Good **v1.1 Analysis and Planning Workflows** - Phases 4-6 (shipped 2026-04-13)
- Good **v1.2 Stronger Specify Questioning** - Phases 7-9 (shipped 2026-04-14, see `milestones/v1.2-ROADMAP.md`)
- Planned **v1.3 Implement Orchestrator Runtime** - Phases 10-12

## v1.3 Implement Orchestrator Runtime

**Milestone Goal:** Make `/sp.implement` a milestone-level orchestration leader that delegates all concrete execution work to workers and can continue through the full active roadmap until completion or a clear blocker.

## Phases

- [ ] **Phase 10: Leader Contract and Milestone Scheduler** - Define the leader-only execution contract and the milestone-wide scheduling loop.
- [ ] **Phase 11: Worker Dispatch and Failure Convergence** - Dispatch sequential and parallel work through workers while classifying failures and enforcing join points.
- [ ] **Phase 12: State Surfaces and End-to-End Verification** - Reflect the new runtime truth across planning artifacts, generated surfaces, docs, and regression coverage.

## Phase Details

### Phase 10: Leader Contract and Milestone Scheduler
**Goal**: Redefine `sp-implement` so the invoking runtime acts only as the leader while it schedules the next executable work across the full milestone.
**Depends on**: Phase 9
**Requirements**: ORCH-01, ORCH-02, LEAD-01, LEAD-02
**Success Criteria** (what must be TRUE):
  1. `/sp.implement` describes and enforces a leader-only role instead of allowing the invoking agent to perform concrete implementation tasks itself.
  2. The runtime can determine the next executable phase and ready batch from roadmap order, task dependencies, and current state.
  3. Sequential execution still routes through delegated worker lanes rather than leader self-execution.
  4. The active milestone can continue past the first completed phase without requiring a manual restart for each later phase.
**Plans**: 2 plans

Plans:
- [ ] 10-01: Define the leader-only implement contract and milestone scheduler surfaces
- [ ] 10-02: Integrate roadmap-aware execution flow and delegated sequential worker handling

### Phase 11: Worker Dispatch and Failure Convergence
**Goal**: Make delegated execution safe for both sequential and parallel work while preserving join points and mixed failure handling.
**Depends on**: Phase 10
**Requirements**: ORCH-03, LEAD-03, FAIL-01, FAIL-02, FAIL-03
**Success Criteria** (what must be TRUE):
  1. Safe parallel batches dispatch worker lanes with explicit join-point semantics before downstream work advances.
  2. The runtime can start clearly safe preparation work for later phases without violating roadmap-order truth.
  3. Non-critical worker failures are reported while unrelated safe work can continue.
  4. Critical-path failures and repeated failures halt or defer milestone progress with an actionable blocker state.
**Plans**: 2 plans

Plans:
- [ ] 11-01: Implement worker dispatch, join-point coordination, and safe cross-phase preparation rules
- [ ] 11-02: Implement mixed failure classification, retry boundaries, and blocker reporting

### Phase 12: State Surfaces and End-to-End Verification
**Goal**: Ship the new orchestration model truthfully across persisted state, generated surfaces, documentation, and focused validation.
**Depends on**: Phase 11
**Requirements**: STAT-01, STAT-02, STAT-03
**Success Criteria** (what must be TRUE):
  1. Planning artifacts show worker outcomes, open join points, advanced tasks or phases, and remaining blockers.
  2. Regression tests fail if the shared implement template, generated Codex skill, and orchestration runtime drift on the leader-only contract.
  3. User-facing guidance explains `/sp.implement` as a milestone-level orchestration leader with delegated execution and mixed failure handling.
  4. The milestone-level execution loop is verified end-to-end against the shipped roadmap expectations.
**Plans**: 2 plans

Plans:
- [ ] 12-01: Persist runtime state and align shipped implement surfaces
- [ ] 12-02: Add end-to-end verification and release-facing guidance for the leader/worker runtime

## Archived Milestones

Completed milestone details are archived under `.planning/milestones/`:

- `v1.0-ROADMAP.md`
- `v1.1-ROADMAP.md`
- `v1.2-ROADMAP.md`

## Progress

| Milestone | Status | Phase Range | Shipped |
|-----------|--------|-------------|---------|
| v1.0 Debug Workflow | Complete | 1-3 | 2026-04-13 |
| v1.1 Analysis and Planning Workflows | Complete | 4-6 | 2026-04-13 |
| v1.2 Stronger Specify Questioning | Complete | 7-9 | 2026-04-14 |
| v1.3 Implement Orchestrator Runtime | Planned | 10-12 | - |
