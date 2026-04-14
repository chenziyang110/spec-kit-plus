# Retrospective: spec-kit-plus

## Milestone: v1.2 - Stronger Specify Questioning

**Shipped:** 2026-04-14
**Phases:** 3 | **Plans:** 6

### What Was Built
- Strengthened `sp-specify` so docs/config/process-change runs now gather planning-critical dimensions before normal release.
- Made follow-up behavior answer-aware, contradiction-sensitive, and more guided without abandoning the question-card structure.
- Added a confirmation gate and no-redirect `specify -> plan` path for the milestone's target work types.
- Synced shipped skill and doc surfaces with the stronger contract and added focused regression coverage for drift.

### What Worked
- Keeping the shared template as the source of truth made later surface alignment straightforward.
- Focused regression slices were enough to verify each phase quickly without needing broad end-to-end harnesses.
- Reconstructing the milestone from phase summaries and verification files worked even after roadmap/state drift.

### What Was Inefficient
- Phase/state drift meant the autonomous flow had to reconcile Phase 8 and Phase 9 artifacts before lifecycle work could proceed.
- Dirty-worktree constraints again limited how much of the final lifecycle could be expressed as clean git history.

### Patterns Established
- Questioning-quality milestones should treat templates, skill mirrors, quickstart docs, and regression suites as one aligned release surface.
- Milestone audits are a good place to normalize requirements traceability when execution artifacts got ahead of planning metadata.

### Key Lessons
- The user-facing feel of `sp-specify` can improve materially through contract language and confirmation structure without runtime changes.
- Workflow guidance drifts faster than implementation intent unless it has its own focused regression tests.

### Cost Observations
- Model mix: not tracked in this local run
- Sessions: 1
- Notable: focused template and doc tests gave enough confidence to complete the milestone without a large integration harness.

## Milestone: v1.1 - Analysis and Planning Workflows

**Shipped:** 2026-04-13
**Phases:** 3 | **Plans:** 3

### What Was Built
- Extended shared strategy-selection language from `implement` into `specify`, `plan`, `tasks`, and `explain`.
- Added workflow-specific lane and join-point language for shared analysis/planning workflows.
- Aligned README, built-in workflow descriptions, generated skills, and integration tests with the shipped routing surface.

### What Worked
- Reusing the canonical strategy vocabulary avoided inventing per-workflow variants.
- Existing template and integration test suites made it straightforward to lock routing language changes down quickly.
- Keeping Codex runtime wording isolated to Codex-only surfaces reduced release-scope ambiguity.

### What Was Inefficient
- GSD init metadata lagged behind the newly initialized milestone docs, so ROADMAP had to be treated as the authoritative source during autonomous execution.
- Dirty-worktree constraints prevented tag/commit/cleanup lifecycle steps from being completed automatically.

### Patterns Established
- Shared workflow routing changes should land as template updates plus direct regression assertions against generated skill surfaces.
- Milestone lifecycle work in a dirty workspace should prefer local archive updates over automated tag/commit flows.

### Key Lessons
- The repository’s primary collaboration contract lives in templates and generated skills, not only in Python runtime helpers.
- README and built-in descriptions need to move in lockstep with template-level behavior to avoid stale guidance.

### Cost Observations
- Model mix: not tracked in this local run
- Sessions: 1
- Notable: targeted test slices were enough to verify each phase quickly, then a combined audit suite provided milestone-level confidence.

## Cross-Milestone Trends

| Milestone | Theme | Observation |
|-----------|-------|-------------|
| v1.0 | Durable workflow behavior | Focused on shipping the resumable debug workflow end-to-end |
| v1.1 | Shared collaboration language | Shifted from runtime skeleton work into analysis/planning workflow consistency and integration truthfulness |
| v1.2 | Stronger requirement discovery | Shipped better `sp-specify` questioning by treating templates, mirrors, docs, and regression tests as one release surface |
