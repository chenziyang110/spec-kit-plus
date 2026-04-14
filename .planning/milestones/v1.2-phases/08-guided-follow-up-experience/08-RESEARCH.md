# Phase 8 Research: Guided Follow-up Experience

**Phase:** 8
**Name:** Guided Follow-up Experience
**Researched:** 2026-04-14
**Mode:** Local fallback research

## Objective

Define what Phase 8 must add on top of the Phase 7 questioning contract so `/sp.specify` feels like guided requirement discovery rather than a better checklist.

## Scope Boundary

Phase 8 should solve the interaction-quality contract inside the shared `specify` template.

This phase should establish:
- how recommendation and example scaffolding help users answer more clearly
- how a stronger current-understanding or confirmation gate works before release
- how common docs/config/process-change runs can stay inside `sp-specify`
- how the shared-template regression suite proves the guided flow is still present

This phase should not yet finish:
- syncing `.agents/skills/sp-specify/SKILL.md` with the template
- broader release-surface or documentation alignment work
- generalized evaluation infrastructure beyond this milestone slice

## Current Sources Of Truth

1. `templates/commands/specify.md`
   This remains the authoritative shared interaction contract.
2. `tests/test_alignment_templates.py`
   This already protects the alignment-first contract and Phase 7 follow-up rules.
3. `.planning/phases/08-guided-follow-up-experience/08-CONTEXT.md`
   The smart-discuss artifact fixing the intended interaction direction for this phase.
4. `.planning/REQUIREMENTS.md`
   Phase 8 must cover `FDEP-03`, `EXPQ-01`, `EXPQ-02`, and `EXPQ-03`.
5. `docs/superpowers/specs/2026-04-12-tui-visual-system-design.md`
   This provides the strongest local guidance on making the interaction feel deliberate and open without reintroducing boxed cards.

## Key Findings

### 1. Phase 7 solved contract depth, not interaction confidence

The current template now knows what to ask and when to keep clarifying, but it still does not strongly describe how the interaction should feel guided in live use.

### 2. Recommendation and example scaffolding need to become a flow-level rule

The open question block already supports recommendation and example rows, but the template does not yet require the workflow to use them strategically to help users answer clearly. Phase 8 needs to turn those rows into active guidance rather than decorative structure.

### 3. The confirmation gate is the biggest remaining trust gap

The template currently has grouped recaps and release decisions, but Phase 8 needs a dedicated current-understanding or confirmation step before `Aligned: ready for plan` so users can verify the collected framing before the workflow exits normally.

### 4. Real experience validation should stay template-driven

Phase 8 should validate the guided flow by extending shared-template regression coverage and by encoding scenario-oriented contract language in `templates/commands/specify.md`. Skill-mirror sync belongs to Phase 9.

## Planning Implications

Phase 8 should split into two plans:

### Plan 08-01: Guided interaction contract and confirmation gate

Focus:
- require recommendation/example scaffolding when the user needs help answering
- add a stronger current-understanding or confirmation gate before normal release
- keep the one-question-at-a-time flow and `specify -> plan` mainline intact

Likely files:
- `templates/commands/specify.md`
- `tests/test_alignment_templates.py`

### Plan 08-02: Experience validation for common flows

Focus:
- validate that common docs/config/process-change runs can complete inside `sp-specify`
- add regression assertions for guided-discovery wording, confirmation behavior, and no-redirect expectations
- avoid touching the skill mirror or broader docs in this phase

Likely files:
- `templates/commands/specify.md`
- `tests/test_alignment_templates.py`

## Risks

| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Overwriting Phase 7 ambiguity rules | The guided experience could accidentally weaken the new release gate | Make confirmation-gate wording explicitly build on Phase 7, not replace it |
| Drifting into Phase 9 sync work | Skill-mirror updates would widen scope and slow validation | Keep this phase centered on the shared template and its direct regression coverage |
| Making the flow verbose instead of guided | Extra summaries or examples can turn into prompt bloat | Require concise scaffolding and use confirmation as a focused gate, not a repeated recap |
| Treating "guided" as subjective only | Phase verification becomes fuzzy | Encode concrete contract phrases and test assertions for recommendation/example scaffolding and confirmation behavior |

## Recommendations For Planner

1. Keep both plans sequential because they touch the same shared template and regression file.
2. Make Plan 08-01 own the confirmation gate and flow-shaping language.
3. Make Plan 08-02 own the experience-validation assertions and common-flow guarantees.
4. Keep `.agents/skills/sp-specify/SKILL.md` out of scope until Phase 9 unless a blocker appears.

## Success Criteria Lens

Phase 8 is well planned only if the resulting plans clearly answer:
- how the interaction helps the user answer
- where the current-understanding gate appears
- how the release decision depends on that gate
- how common target flows stay inside `sp-specify`

If the plans cannot answer those questions concretely, they are still too shallow.
