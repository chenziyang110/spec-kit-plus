{{spec-kit-include: ../common/user-input.md}}

## Objective

Advance the current feature through tracked implementation batches while keeping execution state, subagent work, verification evidence, and recovery paths explicit.

## Context

- Primary inputs: canonical `task-index.json` or the light leader-direct task list, current execution state, the current task's required refs, and live repository evidence for the touched area. The full plan/spec package is fallback evidence, not default intake.
- The leader owns tracker truth, execution strategy, join points, blocker handling, and final validation.
- Delegated workers own bounded implementation lanes only; they do not own the overall implementation state.

## Process

- Recover compact execution state, validate the task-graph revision, and identify the current ready batch.
- If the feature lane is not explicit, run `{{specify-subcmd:lane resolve --command implement --ensure-worktree}}`; use the returned execution context/materialized worktree and stop on `uncertain`.
- Read `FEATURE_DIR/workflow-state.md` when present. If its canonical `next_command` still points to `/sp.analyze`, stop and honor that pending diagnostic gate rather than self-authorizing implementation from chat memory.
- On resume, audit terminal-looking tracker/task state before trusting completion; checked tasks are claims until validation, handoff, join point, and consumer evidence prove them. When `real_entrypoint_evidence` is required, synthetic-only consumer proof is not sufficient.
- Carry every `CA-###` consequence obligation from packets into dispatch, implementation evidence, result acceptance, tracker open gaps, and stop-and-reopen routing.
- Choose leader-direct or delegated execution. Compile and validate a WorkerTaskPacket just in time only for delegated work; do not require packets for leader-direct tasks.
- Integrate worker results into one task lifecycle record with validation, review verdict, blockers, and recovery; keep execution truth current without duplicating task briefs, review packages, and ledgers.
- Continue automatically until the feature is complete or blocked by a real blocker.

## Output Contract

- Produce verified implementation changes plus updated compact execution state for the active feature.
- Keep one task lifecycle record per executed task aligned with what actually happened. Additional review or repair records are event-triggered rather than mandatory for every batch.
- Report blockers, retries, and completion honestly rather than inferring success from partial progress.
- On successful technical closeout, keep `active_command: sp-implement`, mark implementation `status: completed` with `phase_mode: execution-only`, set canonical `next_command: /sp.accept`, report `human-acceptance.json`, and hand off to `{{invoke:accept}}`. This is the default post-implement stage; do not pre-fill a human PASS, set `active_command: sp-accept` early, or continue into acceptance within the same invocation.
- For any blocked, approval-gated, timeout-gated, or nonzero-verification exit, include an **Actionable Blocker Resolution** section instead of a bare blocked summary. It must name each blocker, `owner: agent | user | maintainer | external-system`, `exact_next_action`, `approval_question` when human approval is the next step, artifact or log evidence, `unblock_criteria`, and whether the rest of implementation can continue.
- Do not leave the user to infer whether to handle the blocker. Say whether the blocker is mandatory for completion, optional cleanup, external baseline maintenance, or a follow-up risk, and name the next command or approval decision when one is known.
- Preserve any `MP-*` obligations carried in task packets, implementation state, or result handoff expectations.
- Worker result handoffs must include must-preserve evidence when packet obligations require it.
- If implementation discovers a conflict with an `MP-*` obligation, return a blocked result instead of silently changing the protected discussion decision.

## Guardrails

- Do not dispatch from raw task text alone; compile and validate the packet first.
- Do not bypass tracker truth, result handoffs, or verification gates.
- Do not declare completion because tasks look checked off if the implementation contract is not actually satisfied.
