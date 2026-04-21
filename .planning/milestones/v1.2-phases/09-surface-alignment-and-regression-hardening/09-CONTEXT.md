# Phase 9: Surface Alignment and Regression Hardening - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase aligns the stronger `sp-specify` behavior across shipped surfaces and adds regression coverage so the milestone contract stays truthful after release. It should synchronize the local Codex skill mirror, tighten tests around that mirror, and update user-facing guidance that still teaches the old clarify-heavy flow.

</domain>

<decisions>
## Implementation Decisions

### Surface Alignment
- Treat `templates/commands/specify.md` as the source of truth for `sp-specify`.
- Sync `.agents/skills/sp-specify/SKILL.md` to the current shared template contract rather than redefining behavior in the skill mirror.
- Keep compatibility-only `/sp.clarify` guidance and optional `spec-extend` wording intact during sync.

### Regression Hardening
- Add or update tests so the local skill mirror and generated skill surfaces fail when they drift from the stronger questioning contract.
- Add guidance-focused regression checks for the user-facing docs that teach the mainline workflow.
- Prefer lightweight structural assertions over brittle full-document snapshots.

### User-Facing Guidance
- Keep `specify -> plan` as the recommended mainline.
- Update outdated quickstart or walkthrough surfaces that still treat `clarify` as the normal next step.
- Preserve compatibility guidance for older workflows without re-promoting `clarify` into the mainline.

### the agent's Discretion
- The exact test file split is at the agent's discretion as long as it protects both the skill mirror and the user-facing guidance contract.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `templates/commands/specify.md` now contains the Phase 7 and Phase 8 contract language and should be mirrored downstream.
- `.agents/skills/sp-specify/SKILL.md` still reflects an older, simplified version of the `specify` contract.
- `tests/test_extension_skills.py` already inspects generated skill content and is the natural place to extend mirror-surface checks.
- `README.md` and `AGENTS.md` already teach `specify -> plan`, but `docs/quickstart.md` still advertises `/speckit.clarify` as a normal refinement step.

### Established Patterns
- Shared contract changes are usually protected in `tests/test_alignment_templates.py`.
- Generated-surface and extension-skill expectations live in `tests/test_extension_skills.py` and integration tests.
- Docs guidance should stay consistent with the mainline taught in `README.md` and `AGENTS.md`.

### Integration Points
- Local skill mirror: `.agents/skills/sp-specify/SKILL.md`
- Shared source template: `templates/commands/specify.md`
- User-facing guidance: `docs/quickstart.md` and any other release-facing docs that still drift
- Regression surfaces: `tests/test_extension_skills.py` plus a focused doc-guidance test if needed

</code_context>

<specifics>
## Specific Ideas

- Mirror the stronger clarification loop, confirmation gate, and no-redirect target flow into `.agents/skills/sp-specify/SKILL.md`.
- Update `docs/quickstart.md` so the example workflow teaches `specify -> plan` with `clarify` as compatibility-only.
- Add regression checks that fail if the skill mirror or guidance docs slip back toward `specify -> clarify -> plan`.

</specifics>

<deferred>
## Deferred Ideas

- Broader behavior-evaluation harnesses beyond milestone-specific regression tests.
- Runtime or execution-surface changes unrelated to `sp-specify` guidance truthfulness.
- Additional documentation rewrites outside the shipped user-facing onboarding surfaces.

</deferred>
