# spec-kit-plus

## What This Is

`spec-kit-plus` is a maintained fork of Spec Kit focused on practical Spec-Driven Development workflow support for local AI coding agents. It bundles the `specify` CLI, generated workflow templates, and integration-specific command or skill surfaces so teams can use different agents without losing a consistent delivery model.

## Core Value

Keep Spec-Driven Development practical across local AI integrations by making the workflow consistent, truthful, and usable in the tools developers actually run.

## Latest Shipped Milestone: v1.2 Stronger Specify Questioning

**Goal:** Make `/sp.specify` noticeably stronger at structured requirement questioning so real runs surface more of the information planning needs before `plan`.

**Target features:**
- Strengthen `sp-specify` question coverage so it proactively surfaces missing requirement dimensions.
- Strengthen follow-up depth and pacing so the workflow asks more useful questions without feeling chaotic.
- Preserve the existing question-card interaction model while making the experience feel more like a guided product discussion.
- Keep shipped command templates, generated skill mirrors, and tests aligned with the improved questioning behavior.
- Borrow the strongest questioning qualities observed in `E:\work\github\superpowers` without replacing the current `specify -> plan` mainline.

## Current State

- Shipped through **v1.2 Stronger Specify Questioning**.
- Shared collaboration routing now covers `implement`, `specify`, `plan`, `tasks`, and `explain`.
- `specify team` remains the Codex-only compatibility runtime surface.
- `sp-specify` now ships stronger planning-critical questioning, answer-aware follow-up, guided interaction scaffolding, and a confirmation gate before normal release.
- The local `sp-specify` skill mirror and quickstart guidance now match the stronger shared template contract.
- No next milestone is defined yet; the next planning step is to set new requirements and roadmap scope.

## Requirements

### Validated

- `sp-debug` shipped with resumable Markdown session persistence and graph-based investigation flow in v1.0
- Debug investigations can load Spec Kit artifacts and git history to narrow search space in v1.0
- Verification-led fixing with Human-in-the-Loop escalation shipped in v1.0
- Shared collaboration routing now covers `specify`, `plan`, `tasks`, and `explain` using the canonical strategy vocabulary in v1.1
- README, built-in workflow descriptions, generated skills, and integration tests now describe the same Milestone 2 routing surface in v1.1
- `sp-specify` now treats docs/config/process changes as planning-critical discovery work and asks for objective, affected users or teams, constraints, validation, and completion criteria before normal release in Phase 7
- `sp-specify` now keeps clarification active while planning-critical ambiguity remains and only exits normally when the ambiguity is resolved or the user explicitly force proceeds in Phase 7
- `sp-specify` follow-up questions now build on the previous answer and explicitly challenge vague, shallow, or contradictory responses in Phase 7
- `sp-specify` now feels more like guided requirement discovery while preserving one-question-at-a-time interaction in v1.2
- The stronger `sp-specify` contract is now aligned across shared templates, the local Codex skill mirror, quickstart guidance, and focused regression suites in v1.2

### Active

- [ ] Extend the stronger questioning model into `spec-extend` and `clarify` where it still fits.
- [ ] Add broader behavior-level evaluation for questioning quality across more task types.

### Out of Scope

- Durable execution/runtime maturity for `implement` beyond the current release slice - deferred to the next orchestration milestone
- Parallel evidence fan-out and single-writer convergence for `debug` - deferred until the runtime maturity milestone
- Additional integration rollout beyond the current Codex, Claude, Gemini, and Copilot slice - deferred until the expansion milestone
- Reworking `spec-extend` or `clarify` in this milestone - the scope is limited to the `sp-specify` mainline experience
- Replacing structured question cards with a fully freeform brainstorming flow - the workflow should stay structured while questioning quality improves

## Context

- The repository now contains a generic orchestration core under `src/specify_cli/orchestration/` plus shared routing language across the major analysis/planning workflows.
- Codex runtime guidance remains intentionally isolated to Codex-specific surfaces and generated assets.
- Legacy phase directories from v1.0 and v1.1 were cleared when milestone v1.2 started, so the next roadmap can regenerate the active `.planning/phases/` tree cleanly.
- Milestone v1.2 is archived under `.planning/milestones/` and tagged locally as `v1.2`.
- Real `/sp.specify` usage feedback says the current questioning still feels too thin in both count and coverage, especially during requirement discovery.
- `E:\work\github\superpowers` shows stronger questioning qualities worth studying, especially following user intent closely and making the final confirmation gate more substantive.
- The repo already shipped analysis-first `specify` behavior and structured question cards, so this milestone should deepen that system rather than replace it.

## Constraints

- **Compatibility**: Preserve existing generated command and skill entrypoints for each integration; new collaboration behavior must fit under agent-native surfaces.
- **Truthfulness**: Do not claim identical multi-agent depth where the underlying runtime cannot deliver it.
- **Backward Compatibility**: Keep `specify team` working for Codex projects while generic orchestration expands elsewhere.
- **Documentation**: README, generated templates, CLI help, and tests must describe the same shared routing contract.
- **Workflow Mainline**: Keep teaching `specify -> plan`; do not make `clarify` mandatory again.
- **UX Shape**: Preserve the structured question-card interaction instead of switching `sp-specify` to a fully conversational brainstorming flow.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Extract collaboration state and policy into a generic orchestration core | Reuses the existing Codex runtime investment without locking future work to Codex-only naming | Good |
| Prefer `native-multi-agent` before `sidecar-runtime`, then downgrade to `single-agent` when needed | Keeps native agent UX primary while still allowing durable fallback | Good |
| Expand collaboration workflow-by-workflow instead of claiming parity everywhere at once | Prevents documentation and product surfaces from overpromising runtime capability | Good |
| Use Milestone 2 to migrate `specify`, `plan`, `tasks`, and `explain` before deepening `implement` and `debug` runtime behavior | Matches the approved sequence in the orchestration design and the current repository state | Good |
| Keep the milestone focused on `sp-specify` instead of redesigning `spec-extend` or `clarify` at the same time | Keeps the milestone bounded enough to improve the mainline experience without diffusing the work | Good |
| Preserve question cards and strengthen the questioning strategy inside that structure | Matches the user's preferred interaction model while still targeting a real experience upgrade | Good |

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
*Last updated: 2026-04-14 after v1.2 milestone completion*
