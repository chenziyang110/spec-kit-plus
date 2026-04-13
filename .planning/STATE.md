---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: stronger-specify-questioning
status: defining-requirements
last_updated: "2026-04-13T00:00:00Z"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# State: spec-kit-plus

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-13)

**Core value:** Keep Spec-Driven Development practical across local AI integrations by making the workflow consistent, truthful, and usable in the tools developers actually run.
**Current focus:** Milestone v1.2 is being defined around stronger `sp-specify` questioning.

## Current Position

**Phase**: Not started (defining requirements)
**Plan**: -
**Status**: Defining requirements for milestone v1.2 Stronger Specify Questioning.

```
[----------] 0%
```

## Progress Snapshot

| Metric | Current | Status |
|--------|---------|--------|
| Archived milestones | v1.0, v1.1 | Complete |
| Active milestone | v1.2 Stronger Specify Questioning | Defining requirements |
| Next recommended command | `/gsd-plan-phase [next phase]` | Pending roadmap creation |

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

### Technical Notes

- `src/specify_cli/orchestration/` exists and shared routing language now covers `implement`, `specify`, `plan`, `tasks`, and `explain`.
- `specify team` remains the Codex-only compatibility surface.
- Milestone v1.1 is archived under `.planning/milestones/`.
- Legacy phase directories were cleared at v1.2 start so the next roadmap can recreate active phase directories from a clean slate.
- Actual `/sp.specify` usage feedback indicates the current requirement questioning still feels too thin in both count and dimension coverage.
- `E:\work\github\superpowers` is the current comparison repo for stronger questioning patterns worth adapting into `sp-specify`.

### Blockers

- Git tagging and archival commits remain pending because the worktree is dirty and those lifecycle steps are confirmation-sensitive.

## Session Continuity

| Date | Focus | Result | Next Steps |
|------|-------|--------|------------|
| 2026-04-12 | Project initialization | v1.0 roadmap and state initialized. | Execute Phase 1 |
| 2026-04-13 | Complete v1.0 | Audit passed; debug workflow milestone shipped. | Archive v1.0 and start v1.1 |
| 2026-04-13 | Complete v1.1 | Shared collaboration routing now covers the analysis and planning workflow surface. | Define the next milestone |
| 2026-04-13 | Start v1.2 | Milestone scope confirmed around stronger `sp-specify` questioning. | Define requirements and roadmap |
