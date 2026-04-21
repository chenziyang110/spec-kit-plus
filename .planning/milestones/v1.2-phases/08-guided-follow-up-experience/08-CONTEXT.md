# Phase 8: Guided Follow-up Experience - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase turns the stronger Phase 7 questioning contract into a guided requirement-discovery experience inside `sp-specify`. It should improve pacing, recommendation scaffolding, and the confirmation gate while preserving the one-question-at-a-time structure and the `specify -> plan` mainline.

</domain>

<decisions>
## Implementation Decisions

### Guided Follow-up Flow
- Keep one-question-at-a-time turns as the default interaction shape.
- Make each turn feel guided by adding concise recommendation framing and one concrete example when it helps the user answer.
- Avoid checklist dumping, long recaps after every answer, and generic resets.

### Confirmation Gate
- Add a stronger current-understanding or confirmation step before the release decision.
- The confirmation gate should summarize the collected requirement state in grouped sections, then explicitly ask the user to confirm or correct it.
- Normal release should happen only after the confirmation gate and the existing ambiguity checks both pass.

### Experience Constraints
- Keep the flow inside `sp-specify`; do not route ordinary docs/config/process-change runs into `sp.clarify` or `sp.spec-extend`.
- Preserve the open question block structure introduced in the shared template instead of inventing a new presentation system here.
- Improve the live interaction contract in the shared template first; skill mirror sync and release-surface alignment stay deferred to Phase 9.

### the agent's Discretion
- The exact wording of the confirmation prompt, recommendation framing, and example scaffolding is at the agent's discretion as long as it stays concise, structured, and compatible with the stronger Phase 7 ambiguity rules.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `templates/commands/specify.md` already contains the open question block structure, ambiguity gates, and answer-aware follow-up rules from Phase 7.
- `tests/test_alignment_templates.py` already enforces the core shared-template contract and is the right place for new regression checks.
- `.agents/skills/sp-specify/SKILL.md` mirrors older `specify` behavior and should be treated as a downstream sync surface, not the source of truth for this phase.

### Established Patterns
- Shared workflow behavior is authored in `templates/commands/specify.md` first, then protected with phrase-level assertions in `tests/test_alignment_templates.py`.
- Phase tracking expects plan summaries, review, and verification artifacts under `.planning/phases/<phase-slug>/`.
- The repo keeps `specify -> plan` as the mainline and treats `clarify` as compatibility-only guidance.

### Integration Points
- Changes will primarily land in `templates/commands/specify.md`.
- Regression checks should extend `tests/test_alignment_templates.py`.
- Phase 9 will need to reconcile `.agents/skills/sp-specify/SKILL.md`, generated surfaces, and user-facing guidance with whatever this phase introduces.

</code_context>

<specifics>
## Specific Ideas

- Use recommendation and example scaffolding to make answers easier without forcing rigid option picking.
- Add a confirmation gate that shows the current understanding in grouped sections before `Aligned: ready for plan`.
- Validate the guided flow against common docs/config/process-change requests rather than only abstract wording.

</specifics>

<deferred>
## Deferred Ideas

- Synchronizing `.agents/skills/sp-specify/SKILL.md` with the shared template.
- Broad release-surface and documentation alignment work outside the shared template and its focused regression tests.
- Larger evaluation harnesses or broader behavior scoring beyond milestone-specific checks.

</deferred>
