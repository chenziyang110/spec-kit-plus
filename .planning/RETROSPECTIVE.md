# Retrospective: spec-kit-plus

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
