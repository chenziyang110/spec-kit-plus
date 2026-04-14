# Phase 10 Research: Leader Contract and Milestone Scheduler

## Objective

Research how to plan Phase 10 so `sp-implement` becomes a leader-only milestone scheduler without changing the current strategy vocabulary or overreaching into later-phase failure handling and state-surface work.

## Current Baseline

- `templates/commands/implement.md` already defines strategy selection using `single-agent`, `native-multi-agent`, and `sidecar-runtime`, but the outline still frames the invoking agent as the direct executor.
- `.agents/skills/sp-implement/SKILL.md` mirrors that shared contract and adds Codex-only escalation guidance for `specify team`.
- `src/specify_cli/orchestration/policy.py` chooses a strategy from a workload shape and `CapabilitySnapshot`, but it does not decide milestone-wide next steps.
- `src/specify_cli/orchestration/models.py` and `src/specify_cli/orchestration/state_store.py` already define session, batch, lane, and event primitives that can anchor a scheduler design.
- Current tests cover strategy selection and template wording, but there is no explicit regression that `single-agent` still means a delegated worker lane rather than leader self-execution.

## Planning Implications

### Contract Surface

- Phase 10 should update the shared implement contract first, because non-Codex integrations inherit it.
- The contract needs explicit language that the leader schedules and dispatches work, while all concrete execution routes through delegated worker lanes.
- `single-agent` should be renamed in behavior, not vocabulary: one worker lane, still delegated.

### Runtime Shape

- The shared orchestration core is the correct home for milestone scheduler models and helpers.
- Phase 10 only needs milestone scheduling and delegated sequential execution; parallel batch convergence and richer failure policy can remain for Phase 11.
- The scheduler should determine:
  - next executable phase
  - next ready batch within that phase
  - which strategy applies to that batch
  - whether milestone execution continues automatically

### Likely File Targets

- `templates/commands/implement.md`
- `.agents/skills/sp-implement/SKILL.md` indirectly through generation/alignment tests
- `src/specify_cli/orchestration/models.py`
- `src/specify_cli/orchestration/policy.py` only if scheduler inputs or decision metadata need extension
- `src/specify_cli/orchestration/state_store.py`
- possible new scheduler helper under `src/specify_cli/orchestration/`
- `tests/orchestration/test_policy.py`
- `tests/codex_team/test_implement_runtime_routing.py`
- `tests/test_alignment_templates.py`

## Phase 10 Risks

- Accidentally implementing Phase 11 concerns such as mixed failure recovery or safe cross-phase warm-up logic too early.
- Letting Codex-only wording define the leader contract instead of the shared template.
- Leaving the scheduler too implicit, so the contract claims milestone continuity without a concrete decision surface in the orchestration core.

## Recommendations For Planning

1. Split Phase 10 into two plans:
   - shared contract and scheduler/runtime primitives
   - roadmap-aware implement flow plus delegated sequential worker semantics
2. Keep acceptance criteria concrete:
   - template wording proving leader-only execution
   - orchestration code proving milestone next-step selection exists
   - tests proving delegated sequential semantics and no regression in strategy vocabulary
3. Leave parallel join-point convergence, retry classification, and rich persisted blocker reporting to Phases 11-12.

## Output Boundary

Phase 10 should ship enough structure that later phases can attach worker dispatch and state surfaces without rewriting the leader contract.
