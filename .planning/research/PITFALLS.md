# Pitfalls Research: Stronger `sp-specify` Questioning

**Domain:** Improving requirement questioning in `specify`
**Researched:** 2026-04-13

## Main Risks

| Pitfall | Why It Matters | Prevention |
|---------|----------------|------------|
| **Confusing “more questions” with “better questions”** | The experience gets slower and more annoying without actually improving alignment | Require each new questioning rule to justify what ambiguity it resolves |
| **Overfitting to `superpowers` literally** | `superpowers` uses a different workflow philosophy; copying it wholesale would fight the current Spec Kit mainline | Borrow questioning strengths, not the entire brainstorming workflow |
| **Improving the template but not the shipped skill mirror** | Users keep seeing stale behavior depending on the surface they run | Treat template and skill changes as inseparable deliverables |
| **Focusing on TUI cosmetics instead of requirement depth** | The milestone ships visible motion without solving the actual user complaint | Keep requirements centered on questioning quality and confirmation strength |
| **Letting `clarify` absorb the missing depth again** | Reintroduces the old split-responsibility problem that the repo just removed | Keep the improved questioning burden inside `sp-specify` |
| **Breaking the structured interaction model** | The user explicitly wants to keep structured cards/blocks | Improve sequencing and content quality without removing the structure |

## Specific Warning Signs

- A PR mostly changes card copy, borders, or banners but not the actual clarification strategy.
- New questions are added as a fixed checklist regardless of task type or user emphasis.
- Template assertions pass, but generated skill mirrors are still stale.
- The workflow recaps more often, but still does not challenge vague user answers.
- The system claims richer questioning while docs and tests still only verify formatting.

## Recommended Safeguards

1. Add requirements that explicitly mention both **coverage** and **follow-up depth**.
2. Add at least one requirement around **template/skill/test alignment**.
3. Ensure roadmap phases leave room for both behavior design and regression hardening.
4. Evaluate success through realistic `/sp.specify` interaction quality, not only file diffs.

## Where These Risks Should Be Addressed

| Risk Area | Best Phase to Address |
|-----------|-----------------------|
| Question quality still too shallow | Early design/contract phase |
| Surface drift between template and skill | Mid implementation/test phase |
| Misleading docs or release messaging | Final alignment phase |
