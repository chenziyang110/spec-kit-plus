# Phase 11: Worker Dispatch and Failure Convergence - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes delegated execution safe once `sp-implement` is already acting as the milestone-level leader. It adds worker dispatch, explicit join-point convergence, limited safe cross-phase preparation, and mixed failure handling without redefining the Phase 10 leader-only contract or Phase 12 state-surface alignment work.

</domain>

<decisions>
## Implementation Decisions

### Failure Classification
- **D-01:** Use a mixed failure policy rather than a single global rule. Phase 11 should classify worker failures into recoverable/non-critical vs critical/blocking outcomes.
- **D-02:** Non-critical failures may leave unrelated ready work in the same milestone executable, but any work gated by the failed batch's join point must stay blocked until the failure is resolved or explicitly deferred.
- **D-03:** Critical-path failures and repeated failures must stop phase advancement and surface a blocker state that the leader can report truthfully.

### Safe Cross-Phase Preparation
- **D-04:** Allow only limited cross-phase preparation work before an earlier phase is fully complete.
- **D-05:** "Safe preparation" means low-risk work such as read-only analysis, scaffolding, documentation preparation, or similarly reversible setup. It does not include broad implementation of later-phase deliverables even when write sets appear disjoint.
- **D-06:** Roadmap order remains the default execution contract. Any allowed preparation work must not mark later phases complete early or blur milestone truthfulness.

### Join-Point Convergence
- **D-07:** Join-point completion uses a mixed rule tied to batch classification rather than one universal success condition.
- **D-08:** For strict batches, a join point completes only when every dispatched task succeeds.
- **D-09:** For mixed-tolerance batches, the join point may converge after all tasks reach terminal states, but only if the resulting classification still allows downstream unrelated work to proceed safely.

### Retry and Escalation
- **D-10:** Automatic retry is allowed only for explicitly transient failures.
- **D-11:** Logic bugs, write-set conflicts, invalid plans, or other deterministic failures should escalate immediately instead of being retried.
- **D-12:** Transient failures should use a bounded retry budget and then escalate to a blocked or deferred state if retries are exhausted.

### the agent's Discretion
- Planners and implementers may decide the exact classification vocabulary, retry counters, and batch-type naming as long as they preserve the mixed-policy behavior above.
- The concrete storage shape for join-point and blocker metadata may evolve within existing orchestration and Codex-team state patterns.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirement contract
- `.planning/ROADMAP.md` - Phase 11 goal, success criteria, and plan split (`11-01`, `11-02`)
- `.planning/REQUIREMENTS.md` - `ORCH-03`, `LEAD-03`, `FAIL-01`, `FAIL-02`, and `FAIL-03`
- `.planning/PROJECT.md` - milestone-level constraints, truthfulness rules, and current v1.3 scope
- `.planning/STATE.md` - current milestone position and carry-forward decisions from Phase 10

### Prior phase decisions that remain locked
- `.planning/phases/10-leader-contract-and-milestone-scheduler/10-01-SUMMARY.md` - shared leader-only contract and scheduler primitives that Phase 11 must build on
- `.planning/phases/10-leader-contract-and-milestone-scheduler/10-02-SUMMARY.md` - Codex alignment and generated-skill contract expectations
- `.planning/phases/10-leader-contract-and-milestone-scheduler/10-VERIFICATION.md` - verified Phase 10 truths that must not regress

### Existing runtime and dispatch implementation
- `src/specify_cli/orchestration/policy.py` - current strategy routing and parallel-batch gating rules
- `src/specify_cli/orchestration/scheduler.py` - roadmap-aware next-phase and next-batch selection
- `src/specify_cli/codex_team/auto_dispatch.py` - current explicit batch dispatch, inferred batches, and join-point hooks
- `src/specify_cli/codex_team/runtime_bridge.py` - runtime environment checks, dispatch persistence, and visible failure state
- `src/specify_cli/codex_team/task_ops.py` - terminal task transitions, join-point markers, and task claim lifecycle
- `src/specify_cli/codex_team/runtime_state.py` - persisted task, worker, monitor, and batch record payloads
- `src/specify_cli/codex_team/session_ops.py` - session bootstrap, monitor summary, and cleanup lifecycle
- `src/specify_cli/codex_team/state_paths.py` - persisted state locations for dispatch, batch, task, worker, and monitor records

### Regression and contract tests
- `tests/codex_team/test_auto_dispatch.py` - current expectations for batch dispatch, join-point updates, and failure effects
- `tests/codex_team/test_passive_parallelism.py` - current conservative policy for passive parallel work and overlap handling
- `tests/contract/test_codex_team_auto_dispatch_cli.py` - CLI/API expectations for auto-dispatch and batch completion
- `tests/orchestration/test_policy.py` - shared routing policy expectations that Phase 11 must extend without breaking

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/specify_cli/codex_team/auto_dispatch.py`: already parses explicit parallel batches, derives inferred batches, dispatches workers, and writes batch records.
- `src/specify_cli/codex_team/task_ops.py`: already owns task claiming, status transitions, join-point metadata, and sync hooks when tasks hit terminal states.
- `src/specify_cli/codex_team/runtime_bridge.py`: already persists runtime session state and explicit dispatch failure records.
- `src/specify_cli/codex_team/runtime_state.py` and `src/specify_cli/codex_team/state_paths.py`: already define a file-backed model for runtime, worker, task, batch, and monitor state.
- `src/specify_cli/orchestration/policy.py`: already models conservative strategy choice from parallel-batch count and write-set overlap.

### Established Patterns
- The repo prefers conservative orchestration defaults: no safe batch means downgrade to `single-agent`, overlapping write sets block passive parallelism, and sidecar escalation is explicit.
- Codex-specific runtime behavior lives under `src/specify_cli/codex_team/` and integration glue under `src/specify_cli/integrations/codex/`, while shared orchestration policy stays runtime-neutral.
- Phrase-level regression tests are preferred over snapshots for workflow-contract behavior.
- File-backed JSON state with explicit schema/version fields is the current persistence model; Phase 11 should extend it rather than inventing a separate coordination substrate.

### Integration Points
- Phase 11 should connect shared orchestration policy decisions to the Codex team dispatch layer rather than replacing the existing `specify team auto-dispatch` surface.
- Batch classification, retry behavior, and blocker semantics will likely land across `auto_dispatch.py`, `task_ops.py`, `session_ops.py`, and shared orchestration models or policy helpers.
- The generated/shared `implement` contract from Phase 10 is the user-facing boundary that must remain truthful while Phase 11 deepens runtime behavior behind it.

</code_context>

<specifics>
## Specific Ideas

- Keep the default roadmap-order contract visible even when low-risk later-phase preparation work is allowed.
- Treat "safe preparation" narrowly; Phase 11 should not open the door to broad out-of-order implementation just because write scopes look independent.
- Prefer a mixed join-point and failure model that matches the real structure already present in the Codex runtime instead of forcing all batches through one rigid success rule.

</specifics>

<deferred>
## Deferred Ideas

- Full state-surface visibility, richer planning-artifact reporting, and release-facing guidance remain Phase 12 work.
- Any redesign of the orchestration vocabulary or move to a more durable coordination substrate remains out of scope for this phase.
- Applying the same runtime model to `debug` remains a future milestone item.

</deferred>

---

*Phase: 11-worker-dispatch-and-failure-convergence*
*Context gathered: 2026-04-14*
