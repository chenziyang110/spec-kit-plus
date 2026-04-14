# Phase 9 Research: Surface Alignment and Regression Hardening

**Phase:** 9
**Name:** Surface Alignment and Regression Hardening
**Researched:** 2026-04-14
**Mode:** Local fallback research

## Objective

Define the minimum work required to make the stronger `sp-specify` behavior truthful across shipped surfaces and resistant to regression.

## Scope Boundary

Phase 9 should finish the milestone by synchronizing shipped surfaces and hardening regression coverage.

This phase should establish:
- that `.agents/skills/sp-specify/SKILL.md` describes the same contract as `templates/commands/specify.md`
- that release-facing guidance teaches `specify -> plan` while keeping `clarify` compatibility-only
- that tests fail when the mirror or guidance drift back toward the old flow

This phase should not expand into:
- new runtime orchestration behavior
- broader evaluation infrastructure beyond this milestone
- redesigning `clarify` or `spec-extend` beyond keeping their current positioning truthful

## Key Findings

### 1. The local skill mirror is materially behind the shared template

The current diff between `templates/commands/specify.md` and `.agents/skills/sp-specify/SKILL.md` is not just frontmatter noise. The skill mirror is missing:
- whole-feature analysis and capability decomposition language
- the Phase 7 planning-critical docs/config gates
- the Phase 8 guided interaction and confirmation-gate wording
- the no-redirect target-flow contract

### 2. Generated-surface tests already exist, but the local mirror is under-protected

`tests/test_extension_skills.py` already inspects generated skill content, making it the right place to add more explicit checks for the stronger `specify` contract. This phase should also protect the local mirror and the user-facing guidance surface.

### 3. `docs/quickstart.md` still teaches the old clarify-first refinement pattern

The README and AGENTS guidance are already aligned with `specify -> plan`, but `docs/quickstart.md` still presents `/speckit.clarify` as the normal Step 4. That is direct release-facing drift.

## Planning Implications

Phase 9 should split into two plans:

### Plan 09-01: Synchronize shipped template and local skill mirror

Focus:
- update `.agents/skills/sp-specify/SKILL.md` to match the current template contract
- add regression coverage that fails if the skill mirror or generated skill surfaces drift

Likely files:
- `.agents/skills/sp-specify/SKILL.md`
- `tests/test_extension_skills.py`

### Plan 09-02: Harden guidance and final regression coverage

Focus:
- update `docs/quickstart.md` and any other release-facing guidance still teaching the old flow
- add a focused regression test for user-facing workflow guidance

Likely files:
- `docs/quickstart.md`
- `README.md` or `AGENTS.md` only if alignment gaps remain after validation
- a focused doc regression test file under `tests/`

## Risks

| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Surface sync by copy-paste only | The mirror may still diverge on the next update | Add explicit regression checks for both the local mirror and generated skills |
| Doc cleanup without tests | User-facing guidance could regress again silently | Add a focused doc guidance regression test |
| Over-scoping into every document in the repo | The final phase becomes documentation sprawl | Limit updates to shipped onboarding and clearly user-facing workflow guidance |

## Recommendations For Planner

1. Keep the phase to two sequential plans.
2. Make Plan 09-01 own the skill-mirror sync and mirror-focused regression coverage.
3. Make Plan 09-02 own the user-facing guidance update and its regression checks.
4. Treat README and AGENTS as validation anchors first; edit them only if they still drift after review.

## Success Criteria Lens

Phase 9 is well planned only if the resulting work can prove:
- the local skill mirror matches the shared template in the important behavior sections
- the generated-surface tests know about the stronger questioning contract
- release-facing docs teach the same mainline as the repo instructions

If any of those remain unverifiable, the milestone is not truly complete.
