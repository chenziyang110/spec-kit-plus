# spec-kit-plus

## What This Is

`spec-kit-plus` is a maintained fork of Spec Kit focused on practical Spec-Driven Development workflow support for local AI coding agents. It bundles the `specify` CLI, generated workflow templates, and integration-specific command or skill surfaces so teams can use different agents without losing a consistent delivery model.

## Core Value

Keep Spec-Driven Development practical across local AI integrations by making the workflow consistent, truthful, and usable in the tools developers actually run.

## Current State

- Shipped through **v1.1 Analysis and Planning Workflows**.
- Shared collaboration routing now covers `implement`, `specify`, `plan`, `tasks`, and `explain`.
- `specify team` remains the Codex-only compatibility runtime surface.
- The next milestone has not been defined yet.

## Requirements

### Validated

- ✅ `sp-debug` shipped with resumable Markdown session persistence and graph-based investigation flow in v1.0
- ✅ Debug investigations can load Spec Kit artifacts and git history to narrow search space in v1.0
- ✅ Verification-led fixing with Human-in-the-Loop escalation shipped in v1.0
- ✅ Shared collaboration routing now covers `specify`, `plan`, `tasks`, and `explain` using the canonical strategy vocabulary in v1.1
- ✅ README, built-in workflow descriptions, generated skills, and integration tests now describe the same Milestone 2 routing surface in v1.1

### Active

- [ ] Define the next milestone goals before resuming roadmap planning

### Out of Scope

- Durable execution/runtime maturity for `implement` beyond the current release slice - deferred to the next orchestration milestone
- Parallel evidence fan-out and single-writer convergence for `debug` - deferred until the runtime maturity milestone
- Additional integration rollout beyond the current Codex, Claude, Gemini, and Copilot slice - deferred until the expansion milestone

## Context

- The repository now contains a generic orchestration core under `src/specify_cli/orchestration/` plus shared routing language across the major analysis/planning workflows.
- Codex runtime guidance remains intentionally isolated to Codex-specific surfaces and generated assets.
- Phase directories for v1.0 and v1.1 remain in `.planning/phases/` because cleanup/archive moves were not run in this dirty workspace.
- Git tagging and archival commits were intentionally skipped because the worktree already contains unrelated in-progress changes.

## Constraints

- **Compatibility**: Preserve existing generated command and skill entrypoints for each integration; new collaboration behavior must fit under agent-native surfaces.
- **Truthfulness**: Do not claim identical multi-agent depth where the underlying runtime cannot deliver it.
- **Backward Compatibility**: Keep `specify team` working for Codex projects while generic orchestration expands elsewhere.
- **Documentation**: README, generated templates, CLI help, and tests must describe the same shared routing contract.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Extract collaboration state and policy into a generic orchestration core | Reuses the existing Codex runtime investment without locking future work to Codex-only naming | ✅ Good |
| Prefer `native-multi-agent` before `sidecar-runtime`, then downgrade to `single-agent` when needed | Keeps native agent UX primary while still allowing durable fallback | ✅ Good |
| Expand collaboration workflow-by-workflow instead of claiming parity everywhere at once | Prevents documentation and product surfaces from overpromising runtime capability | ✅ Good |
| Use Milestone 2 to migrate `specify`, `plan`, `tasks`, and `explain` before deepening `implement` and `debug` runtime behavior | Matches the approved sequence in the orchestration design and the current repository state | ✅ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-13 after v1.1 milestone*
