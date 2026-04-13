---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Stronger Specify Questioning
status: Ready to plan
last_updated: "2026-04-14T01:52:06.6055892+08:00"
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 6
  completed_plans: 2
  percent: 33
---

# State: spec-kit-plus

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Keep Spec-Driven Development practical across local AI integrations by making the workflow consistent, truthful, and usable in the tools developers actually run.
**Current focus:** Phase 8 planning after Phase 7 verification.

## Current Position

**Phase**: Phase 8 next
**Plan**: Not started
**Status**: Phase 7 is complete, reviewed, and verified. The next step is to discuss or plan Phase 8 Guided Follow-up Experience.

```text
[###-------] 33%
```

## Progress Snapshot

| Metric | Current | Status |
|--------|---------|--------|
| Archived milestones | v1.0, v1.1 | Complete |
| Active milestone | v1.2 Stronger Specify Questioning | Phase 7 complete |
| Next recommended command | `/gsd-discuss-phase 8` | Ready |

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

### Technical Notes

- `src/specify_cli/orchestration/` exists and shared routing language now covers `implement`, `specify`, `plan`, `tasks`, and `explain`.
- `specify team` remains the Codex-only compatibility surface.
- Milestone v1.1 is archived under `.planning/milestones/`.
- Legacy phase directories were cleared at v1.2 start so the next roadmap can recreate active phase directories from a clean slate.
- Actual `/sp.specify` usage feedback indicates the current requirement questioning still feels too thin in both count and dimension coverage.
- `E:\work\github\superpowers` is the current comparison repo for stronger questioning patterns worth adapting into `sp-specify`.
- Milestone v1.2 roadmap now spans Phases 7-9 with a sequence of questioning contract redesign, guided interaction quality, and surface/test alignment.
- Phase 7 now updates `templates/commands/specify.md` and `tests/test_alignment_templates.py` to enforce planning-critical docs/config coverage, ambiguity gating, and answer-aware follow-up.
- Phase 7 review and verification artifacts are present under `.planning/phases/07-questioning-contract-and-coverage/`.

### Blockers

- Git tagging and archival commits remain pending because the worktree is dirty and those lifecycle steps are confirmation-sensitive.

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
