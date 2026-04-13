# Stack Research: Stronger `sp-specify` Questioning

**Domain:** Requirement-questioning workflow design for `spec-kit-plus`
**Researched:** 2026-04-13

## Current Stack Reality

The improvement surface for this milestone is primarily prompt-template and regression driven, not runtime-driven.

| Area | Current Stack | Implication for v1.2 |
|------|---------------|----------------------|
| Command surface | `templates/commands/specify.md` | Primary shared workflow contract for generated integrations |
| Generated Codex mirror | `.agents/skills/sp-specify/SKILL.md` | Must stay synchronized with the template or the user sees stale behavior |
| Regression layer | `tests/test_alignment_templates.py` | Already enforces parts of the `specify` questioning contract |
| Adjacent compatibility surface | `templates/commands/clarify.md`, `.agents/skills/sp-clarify/SKILL.md` | Relevant as drift risk, but not first-class scope for this milestone |
| Design history | `docs/superpowers/specs/2026-04-11-specify-analysis-rework-design.md` | Confirms the repo already chose analysis-first `specify` as the mainline |
| External comparison source | `E:\work\github\superpowers\skills/brainstorming/SKILL.md` | Best local reference for richer requirement questioning patterns |

## Recommended Stack Additions or Changes

| Recommendation | Why | Scope Impact |
|----------------|-----|--------------|
| Treat `templates/commands/specify.md` as the authoritative questioning contract and explicitly resync the generated skill mirror | The current skill mirror is materially behind the template | Required |
| Expand regression coverage beyond structure-only checks toward question-depth and interaction-shape expectations | Current tests protect TUI structure more strongly than questioning quality | Required |
| Use docs/spec artifacts to explain the new questioning behavior and guardrails | This is a workflow-behavior milestone, so guidance drift is a real product risk | Recommended |
| Keep changes in Markdown/template/test surfaces first | This milestone is about user-facing prompting behavior, not orchestration-core code | Required |

## What Not To Add

| Avoid | Why |
|------|-----|
| New runtime coordination layer for `specify` | Out of scope and unnecessary for this questioning-focused milestone |
| Mandatory `clarify` or `spec-extend` dependency | Conflicts with the approved `specify -> plan` mainline |
| Visual/TUI redesign as the main deliverable | The real problem is questioning quality, not decorative presentation |

## Integration Notes

- The current `templates/commands/specify.md` already moved toward open question blocks and deeper analysis language.
- The current `.agents/skills/sp-specify/SKILL.md` still carries an older question-card contract with boxed-card language and a narrower analysis model.
- The milestone should therefore assume a multi-surface alignment problem, not a single-file wording tweak.

## Confidence

| Area | Confidence | Notes |
|------|------------|-------|
| Template-first implementation path | HIGH | The current repo already encodes most behavior in templates and generated mirrors |
| Need for skill resynchronization | HIGH | Direct diff shows substantial drift |
| Need for more regression coverage | HIGH | Existing tests focus on structure and compatibility, not enough on questioning depth |
