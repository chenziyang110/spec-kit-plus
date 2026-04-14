# Requirements: spec-kit-plus

**Defined:** 2026-04-14
**Core Value:** Keep Spec-Driven Development practical across local AI integrations by making the workflow consistent, truthful, and usable in the tools developers actually run.

## v1 Requirements

### Milestone Orchestration

- [x] **ORCH-01**: User can run `/sp.implement` once against the active planning artifacts and have it continue across all remaining phases in the current milestone until work is complete or a blocker is declared.
- [x] **ORCH-02**: User can rely on `/sp.implement` to derive the next executable phase and ready task batch from roadmap order, task dependencies, and current execution state instead of requiring manual phase-by-phase restarts.
- [x] **ORCH-03**: User sees roadmap order preserved as the default execution contract, while clearly safe preparation work for later phases can be started early without marking those phases complete prematurely.

### Leader and Worker Roles

- [x] **LEAD-01**: User can rely on the `sp-implement` leader to schedule, dispatch, reconcile, and report work without directly performing the implementation or verification tasks itself.
- [x] **LEAD-02**: User running a sequential implementation batch still gets that work executed by a worker lane or delegated path rather than by the leader process.
- [x] **LEAD-03**: User running a safe parallel batch gets multiple worker executions coordinated under explicit join-point semantics before downstream work continues.

### Failure and Recovery

- [x] **FAIL-01**: User sees non-critical worker failures reported without freezing unrelated ready work that can still proceed safely in the current milestone.
- [x] **FAIL-02**: User sees critical-path worker failures stop phase advancement and surface an actionable blocker report before the runtime claims milestone progress.
- [x] **FAIL-03**: User sees repeated worker failures escalate to a blocked or deferred state instead of being retried indefinitely.

### State and Surface Alignment

- [x] **STAT-01**: User can inspect planning artifacts and see which workers ran, which join points are still open, which tasks or phases advanced, and which blockers remain.
- [x] **STAT-02**: Maintainer running focused regression coverage gets failures if the shared implement template, generated Codex skill, and orchestration runtime disagree about the leader-only execution contract.
- [x] **STAT-03**: User-facing guidance describes `/sp.implement` truthfully as a milestone-level orchestration leader with delegated execution behavior and mixed failure handling.

## v2 Requirements

### Follow-on Runtime Expansion

- **DBUG-01**: `debug` adopts the same leader/worker runtime model once `sp-implement` proves the pattern.
- **DAG-01**: The runtime can promote from ordered phase execution to a full dependency-graph scheduler when the planning system is ready for it.
- **RUNT-01**: The runtime can use a more durable coordination substrate than `.planning/` artifacts if the current file-backed approach proves insufficient.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Applying the leader/worker redesign to `debug` in this milestone | Keep the milestone narrowly focused on the current `sp-implement` execution gap |
| Replacing the current strategy vocabulary with a new orchestration taxonomy | The current problem is execution depth and delegation, not naming |
| Building an external queue, broker, or service-backed runtime | Too large for this milestone and unnecessary before the file-backed model is proven |
| Fully dependency-graph-driven cross-phase execution | Useful later, but this milestone should keep roadmap order as the default contract |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ORCH-01 | Phase 10 | Complete |
| ORCH-02 | Phase 10 | Complete |
| ORCH-03 | Phase 11 | Complete |
| LEAD-01 | Phase 10 | Complete |
| LEAD-02 | Phase 10 | Complete |
| LEAD-03 | Phase 11 | Complete |
| FAIL-01 | Phase 11 | Complete |
| FAIL-02 | Phase 11 | Complete |
| FAIL-03 | Phase 11 | Complete |
| STAT-01 | Phase 12 | Complete |
| STAT-02 | Phase 12 | Complete |
| STAT-03 | Phase 12 | Complete |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 Good

---
*Requirements defined: 2026-04-14*
*Last updated: 2026-04-14 after Phase 12 completion*
