# Milestones: spec-kit-plus

## v1.2 Stronger Specify Questioning (Shipped: 2026-04-14)

**Phases completed:** 3 phases, 6 plans, 18 tasks

**Key accomplishments:**

- Docs/config questioning gates and planning-critical release rules for `sp-specify`
- Answer-aware follow-up and contradiction handling for `sp-specify` clarification
- Guided interaction wording and confirmation gate for `sp-specify`
- Common-flow and pre-release confirmation wording for `sp-specify`
- Synced the local `sp-specify` skill mirror and hardened skill-surface regression coverage
- Aligned the quickstart workflow guidance and added doc regression coverage

### Evidence

- [Roadmap Archive](milestones/v1.2-ROADMAP.md)
- [Requirements Archive](milestones/v1.2-REQUIREMENTS.md)
- [Milestone Audit](milestones/v1.2-MILESTONE-AUDIT.md)

### Known Gaps

- Git tag and a clean milestone-only archival commit remain constrained by unrelated in-progress changes already present in the worktree.

---

## v1.0 Debug Workflow

**Shipped:** 2026-04-13
**Phases:** 1-3
**Plans:** 9
**Requirements:** 13 / 13 complete

### What Shipped

1. Added a persistent, resumable `sp-debug` workflow powered by a graph-based investigation lifecycle.
2. Introduced Markdown-backed debug session storage under `.planning/debug/` with safe resume behavior.
3. Loaded Spec Kit artifacts and git history into the debug workflow to narrow investigation scope with repository context.
4. Enforced reproduction-first and verification-led debugging behavior before fixes proceed.
5. Added a Human-in-the-Loop safety gate with persisted handoff reporting after repeated verification failures.

### Evidence

- [Roadmap Archive](milestones/v1.0-ROADMAP.md)
- [Requirements Archive](milestones/v1.0-REQUIREMENTS.md)
- [Milestone Audit](milestones/v1.0-MILESTONE-AUDIT.md)

### Known Gaps

- Git tag and archival commit were intentionally skipped in this workspace because unrelated in-progress changes are already present in the worktree.

## v1.1 Analysis and Planning Workflows

**Shipped:** 2026-04-13
**Phases:** 4-6
**Plans:** 3
**Requirements:** 10 / 10 complete

### What Shipped

1. Extended shared strategy-selection language from `implement` into `specify` and `plan`.
2. Extended the same shared routing contract into `tasks` and `explain`, including conservative explain fan-out guidance.
3. Added workflow-specific lane and join-point language for all Milestone 2 workflows while keeping shared templates integration-neutral.
4. Updated README, built-in workflow descriptions, generated skills, and integration tests so the shipped routing surface is described consistently.

### Evidence

- [Roadmap Archive](milestones/v1.1-ROADMAP.md)
- [Requirements Archive](milestones/v1.1-REQUIREMENTS.md)
- [Milestone Audit](milestones/v1.1-MILESTONE-AUDIT.md)

### Known Gaps

- Git tag, archival commit, and cleanup of `.planning/phases/` were intentionally skipped in this workspace because unrelated in-progress changes are already present in the worktree.
