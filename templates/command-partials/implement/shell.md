{{spec-kit-include: ../common/user-input.md}}

## Objective

Advance the current feature through tracked implementation batches while keeping execution state, subagent work, verification evidence, and recovery paths explicit.

## Context

- Primary inputs come from `specify-runtime implement task-next` and targeted `specify-runtime artifact show` queries, plus live repository evidence for the touched area. Follow the returned required references through those CLI queries; the full task index and full plan/spec package are fallback evidence, not default intake.
- The leader owns tracker truth, execution strategy, join points, blocker handling, and final validation.
- Delegated workers own bounded implementation lanes only; they do not own the overall implementation state.
- One validation ledger is shared across Implement and Review and bound to
  source fingerprints. It has three logical gates; physical retries are
  attempts inside a gate. Do not reset it at phase handoff or resume.

## Process

- Recover compact execution state, validate the task-graph revision, and identify the current ready batch.
- Before allocating a Leader-owned validation wave, run
  `{{specify-subcmd:specify-runtime implement validation-status --feature-dir <feature-dir> --format json}}`
  and obey `attempt_decision`. Resume `resume_running_attempt`; start the
  progress-bound attempt returned by `retry_same_gate`; for
  `repair_before_retry`, repair first and require the implementation fingerprint
  to change; use `open_logical_gate` only for a genuinely unopened logical
  gate; and create no attempt for `validation_complete`. `remaining_epochs` is
  a compatibility count of unopened logical gates, as is
  `remaining_gate_slots`; zero is not a retry-exhaustion signal. Never stop or
  blindly rerun from the raw count alone.
- If `FEATURE_DIR` is not explicit, use a validated managed Run feature subject or the installed prerequisite helper's paths-only result. Require exactly one match and stop on ambiguity; never guess from the Run's private Git ref.
- Query `FEATURE_DIR/workflow-state.md` with `specify-runtime artifact show` when present. If its canonical `next_command` still points to `/sp.analyze`, stop and honor that pending diagnostic gate; never treat self-authorizing implementation from chat memory as a substitute for the CLI-queried gate.
- On resume, audit terminal-looking tracker/task state before trusting completion; checked tasks are claims until validation, handoff, join point, and consumer evidence prove them. When `real_entrypoint_evidence` is required, synthetic-only consumer proof is not sufficient.
- Carry every `CA-###` consequence obligation from packets into dispatch, implementation evidence, result acceptance, tracker open gaps, and stop-and-reopen routing.
- Choose leader-direct or delegated execution. Compile and validate a WorkerTaskPacket just in time only for delegated work; do not require packets for leader-direct tasks.
- Integrate worker results into one task lifecycle record with cheap task checks,
  test impact, shared validation gate/attempt refs, review verdict, blockers, and
  recovery; keep execution truth current without duplicating task briefs,
  review packages, and ledgers. A worker must not run a heavyweight test, full
  build, server startup, E2E journey, or browser capture per Txx. The Leader
  groups those checks into one gate attempt for the current change-set.
- Continue automatically until the feature is complete or blocked by a real blocker.
- A task-local blocker is parked while any dependency-safe task remains runnable;
  do not persist a feature-wide workflow block until no ready work remains.
- When the human explicitly agrees to postpone a low/medium-risk item, use the
  hash-bound `implement deferral-propose -> deferral-confirm` flow, leave the
  item `deferred` rather than passed/accepted, list the claims withheld, and
  transfer it to mandatory Review revalidation.

## Output Contract

- Produce verified implementation changes plus updated compact execution state for the active feature.
- Keep one task lifecycle record per executed task aligned with what actually happened. Additional review or repair records are event-triggered rather than mandatory for every batch.
- Report blockers, retries, and completion honestly rather than inferring success from partial progress.
- On successful technical closeout, invoke `specify-runtime implement closeout`. It exclusively derives and atomically writes `implementation-summary.md` and `implementation-handoff.json` from accepted task lifecycle evidence, actual changed paths, official real entrypoints, required system-review scenarios, and the validation ledger. Never create, patch, replace, or generically submit either artifact. The runtime revalidates the live Spec, Plan, and Tasks and carries their exact complete acceptance denominator and frozen Human Acceptance Universe forward. Implement must not create, infer, or prefill `reviewed_runtime_targets`; only Review creates those targets from final integrated evidence. Hand off to `{{invoke:review}}` and stop.
- `implement closeout` does not update phase state. After it succeeds, execute the returned/shared `specify-runtime workflow complete-stage` action. Only that workflow command validates the sealed stage and updates CLI-owned `workflow.json`; it does not update rich `workflow-state.md`, whose resume/evidence sections remain behind targeted `artifact show` and fresh leased `artifact patch` calls.
- For any blocked, approval-gated, timeout-gated, or nonzero-verification exit, include an **Actionable Blocker Resolution** section instead of a bare blocked summary. It must name each blocker, `owner: agent | user | maintainer | external-system`, `exact_next_action`, `approval_question` when human approval is the next step, artifact or log evidence, `unblock_criteria`, and whether the rest of implementation can continue.
- Do not leave the user to infer whether to handle the blocker. Say whether the blocker is mandatory for completion, optional cleanup, external baseline maintenance, or a follow-up risk, and name the next command or approval decision when one is known.
- Preserve any `MP-*` obligations carried in task packets, implementation state, or result handoff expectations.
- Worker result handoffs must include must-preserve evidence when packet obligations require it.
- If implementation discovers a conflict with an `MP-*` obligation, return a blocked result instead of silently changing the protected discussion decision.

## Guardrails

- Do not dispatch from raw task text alone; compile and validate the packet first.
- Do not bypass tracker truth, result handoffs, or verification gates.
- Do not let a passive testing skill, worker, join, resume, task transition, or
  completion claim open an extra logical gate. Interruptions retry inside their
  gate; real failures require repair and a new fingerprint. Never open a fourth
  logical gate.
- Do not convert `remaining_epochs: 0` into a hard stop when
  `attempt_decision.can_start_attempt` is true. Logical-gate cost control limits
  new validation scope; it does not suppress a repaired or interrupted attempt
  needed to finish the current gate.
- Do not declare completion because tasks look checked off if the implementation contract is not actually satisfied.
- Do not treat the later system Review as a dumping ground. Complete known entrypoint and consumer wiring during implementation; Review is an independent integrated proof-and-repair gate.
