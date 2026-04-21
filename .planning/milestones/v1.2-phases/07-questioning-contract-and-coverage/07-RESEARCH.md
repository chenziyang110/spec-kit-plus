# Phase 7 Research: Questioning Contract and Coverage

**Phase:** 7
**Name:** Questioning Contract and Coverage
**Researched:** 2026-04-14
**Mode:** Local fallback research

## Objective

Answer: what needs to be true for Phase 7 planning to improve `sp-specify` questioning quality in a meaningful way, before later phases handle experience polish and shipped-surface alignment.

## Scope Boundary

Phase 7 should solve the contract-level problem, not the entire milestone.

This phase should establish:
- what requirement dimensions `sp-specify` must cover for the milestone's target task type
- how task classification changes the questioning path
- when the workflow must continue clarifying instead of exiting early
- how vague or contradictory answers trigger stronger follow-up

This phase should not yet try to finish:
- final experience polish for the live interaction
- full template/skill mirror synchronization
- all docs and release-surface alignment work

## Current Sources Of Truth

The planning-critical sources for this phase are:

1. `templates/commands/specify.md`
   This is the most current shared contract for `sp-specify`.
2. `.agents/skills/sp-specify/SKILL.md`
   This is the shipped Codex mirror and currently drifts from the template.
3. `tests/test_alignment_templates.py`
   This enforces part of the template contract and shows what is already considered stable.
4. `.planning/REQUIREMENTS.md`
   Phase 7 must cover `QCOV-01`, `QCOV-02`, `QCOV-03`, `FDEP-01`, and `FDEP-02`.
5. `.planning/research/SUMMARY.md`
   This captures the milestone-level conclusion that the current problem is shallow questioning, not just TUI presentation.

## Key Findings

### 1. Phase 7 must target contract behavior, not wording churn

The real complaint is that `/sp.specify` still feels too thin in live use. If Phase 7 only edits labels, examples, or card phrasing, it will fail even if the diff is large.

### 2. The task-type gate is the first planning-critical deficiency

For this milestone, the target scenario is a docs/config/process change around `sp-specify` itself. The workflow already lists mandatory clarity gates by task type, but the repo still needs stronger coverage and follow-up logic that makes those gates feel real in use.

### 3. Drift between template and skill mirror is important, but mostly Phase 9 work

The current drift is a major milestone concern, but Phase 7 only needs enough awareness of it to avoid designing a contract that cannot later be mirrored cleanly. Full shipped-surface sync belongs later.

### 4. The strongest external behavior to borrow is intent-following probing

The useful lesson from `E:/work/github/superpowers` is not "be freeform." It is:
- ask one thing at a time
- follow the user's last answer closely
- do not accept vague language when it affects planning
- make the final confirmation gate more substantive

## Planning Implications

Phase 7 should likely split into two plans:

### Plan 07-01: Contract redesign and task-type coverage

Focus:
- identify the concrete question dimensions for the targeted task types
- encode stronger task-classification-aware questioning rules
- tighten the release gate so planning-critical ambiguity blocks completion

Likely files:
- `templates/commands/specify.md`
- possibly design/history docs that define the intended contract if the repo uses them as planning references

### Plan 07-02: Follow-up logic and ambiguity handling

Focus:
- make follow-up questions build from the user's previous answer
- define stronger behavior for vague, shallow, and contradictory responses
- add regression coverage that proves deeper clarification expectations at the contract level

Likely files:
- `templates/commands/specify.md`
- `tests/test_alignment_templates.py`
- possibly other nearby tests that validate generated skill/template behavior

## Risks

| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Solving presentation instead of coverage | The phase ships visible changes without fixing requirement discovery | Keep plan objectives tied to `QCOV-*` and `FDEP-*` behaviors |
| Mixing Phase 8 or Phase 9 work into Phase 7 | The first phase becomes too broad and hard to verify | Keep Phase 7 focused on contract behavior and ambiguity rules |
| Treating all task types the same | The milestone specifically needs better task-type-aware questioning | Make classification-aware branching part of the plan objective |
| Leaving acceptance vague | Later execution may implement generic prompt edits instead of real behavior changes | Use acceptance criteria that mention exact requirement IDs and concrete contract statements |

## Recommendations For Planner

1. Keep Phase 7 to two plans.
2. Make both plans sequential in wave order unless the file scopes are truly independent.
3. Ensure at least one plan explicitly owns the task-type coverage contract.
4. Ensure at least one plan explicitly owns the ambiguity/follow-up contract.
5. Leave mirror sync and broader release-surface cleanup for later phases, except where a small reference read is needed to avoid regressions.

## Success Criteria Lens

Phase 7 should be considered well planned only if the resulting plans would clearly answer:
- what the workflow must ask
- how the workflow adapts by task type
- what counts as unresolved ambiguity
- how stronger follow-up is supposed to work

If a plan cannot answer those four questions, it is still too shallow.
