{{spec-kit-include: ../common/user-input.md}}

## Objective

Advance the current feature through tracked implementation batches while keeping execution state, subagent work, verification evidence, and recovery paths explicit.

## Context

- Primary inputs: canonical `task-index.json` or the light leader-direct task list, current execution state, the current task's required refs, and live repository evidence for the touched area. The full plan/spec package is fallback evidence, not default intake.
- The leader owns tracker truth, execution strategy, join points, blocker handling, and final validation.
- Delegated workers own bounded implementation lanes only; they do not own the overall implementation state.
- One validation-epoch ledger is shared across Implement and Review and bound to
  source fingerprints. The combined workflow may consume at most three
  heavyweight epochs; do not reset the count at phase handoff or resume.

## Process

- Recover compact execution state, validate the task-graph revision, and identify the current ready batch.
- If the feature lane is not explicit, run `{{specify-subcmd:lane resolve --command implement --ensure-worktree}}`; use the returned execution context/materialized worktree and stop on `uncertain`.
- Read `FEATURE_DIR/workflow-state.md` when present. If its canonical `next_command` still points to `/sp.analyze`, stop and honor that pending diagnostic gate rather than self-authorizing implementation from chat memory.
- On resume, audit terminal-looking tracker/task state before trusting completion; checked tasks are claims until validation, handoff, join point, and consumer evidence prove them. When `real_entrypoint_evidence` is required, synthetic-only consumer proof is not sufficient.
- Carry every `CA-###` consequence obligation from packets into dispatch, implementation evidence, result acceptance, tracker open gaps, and stop-and-reopen routing.
- Choose leader-direct or delegated execution. Compile and validate a WorkerTaskPacket just in time only for delegated work; do not require packets for leader-direct tasks.
- Integrate worker results into one task lifecycle record with cheap task checks,
  test impact, shared validation-epoch refs, review verdict, blockers, and
  recovery; keep execution truth current without duplicating task briefs,
  review packages, and ledgers. A worker must not run a heavyweight test, full
  build, server startup, E2E journey, or browser capture per Txx. The Leader
  groups those gates into a validation epoch for the current change-set.
- Continue automatically until the feature is complete or blocked by a real blocker.

## Output Contract

- Produce verified implementation changes plus updated compact execution state for the active feature.
- Keep one task lifecycle record per executed task aligned with what actually happened. Additional review or repair records are event-triggered rather than mandatory for every batch.
- Report blockers, retries, and completion honestly rather than inferring success from partial progress.
- On successful technical closeout, create the deterministic `implementation-handoff.json` from accepted task lifecycle evidence, actual changed paths, official real entrypoints, required system-review scenarios, and the validation-epoch ledger with its consumed count and remaining budget. Revalidate it against the live Spec, Plan, and Tasks, then carry their exact complete `acceptance_refs` denominator, `acceptance_denominator_sha256`, and frozen Human Acceptance Universe (`human_acceptance_obligations`, `human_acceptance_scenarios`, and `human_acceptance_contract_sha256`) forward unchanged; never omit an item, downgrade `required`, reconstruct the contract from prose, or reset the epoch count. Implement must not create, infer, or prefill `reviewed_runtime_targets`; only Review creates those targets from final integrated evidence. Update owned rich `workflow-state.md` evidence/resume fields truthfully, then run the workflow runtime `complete-stage` command with the current revision. It records `implement/completed` only in CLI-owned `workflow-runtime.json`; it does not update rich state fields. Hand off to `{{invoke:review}}`. This is the mandatory post-implement stage; do not set rich state to `active_command: sp-review` early, execute the returned transition, or continue into Review in the same invocation.
- For any blocked, approval-gated, timeout-gated, or nonzero-verification exit, include an **Actionable Blocker Resolution** section instead of a bare blocked summary. It must name each blocker, `owner: agent | user | maintainer | external-system`, `exact_next_action`, `approval_question` when human approval is the next step, artifact or log evidence, `unblock_criteria`, and whether the rest of implementation can continue.
- Do not leave the user to infer whether to handle the blocker. Say whether the blocker is mandatory for completion, optional cleanup, external baseline maintenance, or a follow-up risk, and name the next command or approval decision when one is known.
- Preserve any `MP-*` obligations carried in task packets, implementation state, or result handoff expectations.
- Worker result handoffs must include must-preserve evidence when packet obligations require it.
- If implementation discovers a conflict with an `MP-*` obligation, return a blocked result instead of silently changing the protected discussion decision.

## Guardrails

- Do not dispatch from raw task text alone; compile and validate the packet first.
- Do not bypass tracker truth, result handoffs, or verification gates.
- Do not let a passive testing skill, worker, join, resume, task transition, or
  completion claim start an extra validation epoch. A third failed epoch blocks
  with exact evidence and resume criteria; never start a fourth.
- Do not declare completion because tasks look checked off if the implementation contract is not actually satisfied.
- Do not treat the later system Review as a dumping ground. Complete known entrypoint and consumer wiring during implementation; Review is an independent integrated proof-and-repair gate.
