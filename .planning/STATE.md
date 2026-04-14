---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Implement Orchestrator Runtime
status: Ready to plan
last_updated: "2026-04-14T06:04:18.265Z"
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 100
---

# State: spec-kit-plus

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Keep Spec-Driven Development practical across local AI integrations by making the workflow consistent, truthful, and usable in the tools developers actually run.
**Current focus:** Phase 12 discussion and planning for state-surfaces-and-end-to-end-verification.

## Current Position

**Phase**: Phase 12 ready to discuss
**Plan**: Not started
**Status**: Phase 11 completed with summaries, review, and verification artifacts. Next step is to discuss or plan Phase 12.

```text
[#######---] 67%
```

## Progress Snapshot

| Metric | Current | Status |
|--------|---------|--------|
| Archived milestones | v1.0, v1.1, v1.2 | Complete |
| Active milestone | v1.3 Implement Orchestrator Runtime | In progress |
| Next recommended command | `/gsd-discuss-phase 12` | Ready |

## Accumulated Context

### Decisions

- Adopt `pydantic-graph` for the debug investigation lifecycle.
- Use Markdown persistence for resumable debug sessions.
- Enforce a "No Fix Without Proof" gate for debug work.
- Extract collaboration state and policy into a generic orchestration core rather than keeping it Codex-only.
- Expand collaboration workflow-by-workflow and keep native agent surfaces primary.
- Keep shared analysis/planning templates integration-neutral while isolating Codex runtime wording to Codex-only surfaces.
- Keep milestone v1.2 focused on `sp-specify` rather than redesigning `spec-extend` or `clarify`.
- Preserve the question-card interaction shape while strengthening question coverage and follow-up depth.
- Keep docs/config/process changes behind a planning-critical gate before normal alignment release.
- Keep clarification answer-aware and escalation-oriented when user input stays vague or contradictory.
- Make `sp-implement` a leader that delegates all concrete execution work to worker agents.
- Let `sp-implement` drive the full roadmap across all phases instead of stopping at a single phase by default.
- Keep roadmap order as the default contract while allowing safe preparation work for later phases.
- Use mixed failure handling so non-critical worker failures do not freeze all progress.

### Technical Notes

- `src/specify_cli/orchestration/` exists and shared routing language now covers `implement`, `specify`, `plan`, `tasks`, and `explain`.
- `specify team` remains the Codex-only compatibility surface.
- Milestone v1.1 is archived under `.planning/milestones/`.
- Legacy phase directories were cleared at v1.2 start so the next roadmap can recreate active phase directories from a clean slate.
- The shared implement template now positions the invoking runtime as a leader that selects the next executable phase and delegated worker lane.
- The orchestration core now exposes milestone state, decision, and scheduler helpers for roadmap-aware continuation.
- v1.2 phase execution artifacts are archived under `.planning/milestones/v1.2-phases/`.
- This milestone is expected to continue numbering from Phase 10 unless the roadmap later proves a different split is cleaner.

### Blockers

- None for Phase 11. Unrelated in-progress changes remain in the worktree for separate workstreams.

## Session Continuity

| Date | Focus | Result | Next Steps |
|------|-------|--------|------------|
| 2026-04-12 | Project initialization | v1.0 roadmap and state initialized. | Execute Phase 1 |
| 2026-04-13 | Complete v1.0 | Audit passed; debug workflow milestone shipped. | Archive v1.0 and start v1.1 |
| 2026-04-13 | Complete v1.1 | Shared collaboration routing now covers the analysis and planning workflow surface. | Define the next milestone |
| 2026-04-13 | Start v1.2 | Milestone scope confirmed around stronger `sp-specify` questioning. | Define requirements and roadmap |
| 2026-04-13 | Roadmap v1.2 | Phases 7-9 drafted around questioning contract, guided interaction, and alignment hardening. | Plan Phase 7 |
| 2026-04-14 | Plan Phase 7 | Phase 7 research and 2 executable plans created for questioning contract and follow-up depth work. | Execute Phase 7 |
| 2026-04-14 | Execute Phase 7 | Phase 7 completed with summaries, review, and verification artifacts. | Discuss or plan Phase 8 |
| 2026-04-14 | Reconcile Phases 8-9 | Phase 8 state drift fixed and Phase 9 completed with mirror sync, quickstart alignment, review, and verification. | Finish v1.2 lifecycle |
| 2026-04-14 | Complete v1.2 lifecycle | Milestone audit and archives created for v1.2. | Define the next milestone |
| 2026-04-14 | Start v1.3 | Milestone scope confirmed around leader-only `sp-implement` orchestration across the full roadmap. | Research, requirements, and roadmap |
| 2026-04-14 | Execute Phase 10 | Leader-only implement contract, milestone scheduler helpers, Codex alignment, review, and verification shipped. | Discuss or plan Phase 11 |
| 2026-04-14 | Discuss Phase 11 | Captured Phase 11 decisions for join points, safe cross-phase preparation, mixed failure handling, and retry escalation. | Plan Phase 11 |
| 2026-04-14 | Plan Phase 11 | Research and 2 executable plans created for classified dispatch, join-point convergence, retry, and blocker handling. | Execute Phase 11 |
| 2026-04-14 | Execute Phase 11 | Worker batch policy, retry taxonomy, blocker handling, review, and verification shipped. | Discuss or plan Phase 12 |
