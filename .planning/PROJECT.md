# Context

**What this is:** A dedicated, intelligent, and context-aware bug-fixing workflow/command (e.g., `sp-debug`) for `spec-kit-plus`.
**Core Value:** Rapid, systematic bug resolution that perfectly resumes after interruptions by persistently tracking investigation state. It supercharges the process by automatically leveraging existing Spec Kit artifacts (`constitution`, `spec`, `plan`, `tasks`) to instantly understand the codebase context, avoiding the need to manually re-read the entire repository.

## Requirements

### Validated

- ✔️ Existing `spec-kit-plus` CLI and agent skill infrastructure (foundation)
- ✔️ Existing project context generation (`spec.md`, `plan.md`, `tasks.md`)

### Active

- [ ] Implement a command (e.g., `specify debug` / `sp-debug`) that initiates the bug-fixing workflow.
- [ ] Adopt the "Scientific Method" investigation loop (Gather -> Investigate -> Fix -> Verify) inspired by `get-shit-done` (`gsd-debug`).
- [ ] Implement state persistence: Automatically log hypotheses, symptoms, eliminated theories, and evidence to a structured markdown file (e.g., `.planning/debug/[slug].md`).
- [ ] Implement resumability: The agent must be able to read the debug state file and perfectly resume the investigation if the session is interrupted (e.g., computer shuts down, network drops).
- [ ] Integrate Spec Kit context: The debug agent MUST automatically read and utilize project artifacts (`constitution.md`, `spec.md`, `plan.md`, `tasks.md`, `ROADMAP.md`) to rapidly understand what features were recently built and how they were implemented, significantly narrowing the search space for root causes.

### Out of Scope

- General-purpose codebase refactoring during a debug session (fixes should be targeted and minimal based on verified root causes).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Borrow architecture from `get-shit-done`'s `gsd-debug` | It provides a proven, professional standard for systematic debugging and state persistence. | ➡️ Pending |
| Leverage existing Spec Kit artifacts for context | Spec-Driven Development produces rich documentation; using it eliminates the "cold start" problem when debugging recently implemented features. | ➡️ Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check → still the right priority?
3. Audit Out of Scope → reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 after initialization*