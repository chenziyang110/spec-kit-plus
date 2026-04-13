# Research Summary: Stronger `sp-specify` Questioning

**Domain:** Requirement-questioning quality for `spec-kit-plus`
**Researched:** 2026-04-13
**Overall Confidence:** HIGH

## Executive Summary

The research says this milestone should not be treated as a cosmetic prompt polish. The real gap is that `/sp.specify` still feels shallow during live requirement discovery even after the analysis-first redesign. The strongest local comparison point, `E:\work\github\superpowers`, succeeds because its questioning follows user intent more closely, probes purpose and success criteria more naturally, and uses a stronger confirmation gate before it moves on.

For `spec-kit-plus`, the right move is not to replace structured question cards with a freeform brainstorming workflow. It is to keep the current structured interaction shape while upgrading four things together: question coverage, follow-up depth, confirmation quality, and contract alignment across templates, generated skills, and tests.

## Key Findings

**Current stack:** This milestone lives mainly in Markdown command templates, generated skill mirrors, and pytest contract tests.

**Biggest gap:** `templates/commands/specify.md` and `.agents/skills/sp-specify/SKILL.md` have materially drifted, so the repo already ships inconsistent questioning behavior depending on surface.

**Best borrowing target:** From `superpowers`, borrow intent-following probing, one-question-at-a-time depth, and a more substantive pre-exit validation gate.

**Main anti-pattern:** Adding more questions without improving question quality will make the workflow slower but not better.

## What This Means For Requirements

The milestone requirements should cover exactly four capability areas:

1. **Question Coverage**  
   `sp-specify` reliably surfaces missing requirement dimensions that planning depends on.
2. **Follow-up Depth**  
   `sp-specify` reacts better to vague answers and asks stronger next questions.
3. **Experience Quality**  
   The interaction stays structured but feels more like guided requirement discovery than a static questionnaire.
4. **Artifact Alignment**  
   Templates, generated skill mirrors, and regression tests all ship the same stronger contract.

## Recommended Roadmap Shape

1. **Phase 7: Questioning Contract Redesign**  
   Redefine the target `sp-specify` questioning behavior and the specific dimensions/follow-up rules it must cover.
2. **Phase 8: Surface Sync and Regression Hardening**  
   Apply the contract to the command template and generated skill mirror, then harden tests so drift and shallow regressions are caught.
3. **Phase 9: Experience Alignment and Release Surface**  
   Tighten docs, examples, and any remaining messaging so the shipped product truthfully describes the stronger questioning experience.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Scope focus on `sp-specify` only | HIGH | User explicitly constrained the milestone |
| Need for stronger question coverage and follow-up depth | HIGH | Direct user feedback plus repo state support it |
| Need for template/skill/test alignment work | HIGH | Direct diff confirms current drift |
| Value of borrowing from `superpowers` selectively | HIGH | Strong local reference, but only certain qualities should transfer |

## Gaps To Watch

- The repo still needs a clear way to test “question quality” behaviorally rather than only structurally.
- `clarify` and `spec-extend` drift remains a follow-on concern, but it should stay outside this milestone unless it blocks `sp-specify` shipping cleanly.
