Trigger: before quick-task implementation, subagent dispatch, join points, or recovery work.

Purpose: preserve mandatory subagent execution, leader role, execution modes, coordinator model, autonomous execution, recovery, surface sweep, and process flow.

Preserved Contract: substantive quick-task work remains packetized and leader-owned with structured worker results.

## Mandatory Subagent Execution

{{spec-kit-include: ../../command-partials/common/dispatch-mode-gradient.md}}

**This command tier: light. Dispatch mode: subagent-preferred.**

Dispatch one safe validated lane as `one-subagent` or multiple safe isolated lanes as `parallel-subagents`; otherwise record `subagent-blocked` with the concrete reason and stop for escalation or recovery.

## Leader Role

- You are the workflow leader and orchestrator.
- You own routing, task splitting, task contracts, dispatch, join points, integration, verification, and state updates.
- Subagents own the substantive task lanes assigned through task contracts.
- You are the quick-task leader. You own scope control, `STATUS.md`, lane selection, validation, and the final summary artifact.
- You are not the default implementer for the quick task; substantive task work belongs on subagent lanes once scope and contracts are locked.
- Use `execution_model: subagent-mandatory` once the quick task has a bounded execution lane.
- Dispatch `one-subagent` for one safe delegated lane and `parallel-subagents` for isolated lanes that can run concurrently.
- Compile a validated `WorkerTaskPacket` or equivalent execution contract before dispatch.
- Keep quick status fields compatible with `templates/artifacts/quick-status.md`: record `done_or_progress_signal` for every join-point update and `blocked_dispatch` when dispatch is unavailable, unsafe, or unpacketizable.

## Execution Modes

The following flags are available and composable:
- `--discuss`: Do a lightweight clarification pass before planning.
- `--research`: Investigate implementation approaches before planning.
- `--validate`: Add plan checking and post-execution verification.
- `--full`: Equivalent to `--discuss --research --validate`.

## Coordinator Model

- The invoking runtime is the leader for the quick task. It owns scope decisions, the lightweight plan, execution strategy selection, join-point handling, validation, and the final summary artifact.
- The leader should not blur planning, execution, and validation into a long conversational loop when the task can be dispatched through a bounded subagent.
- Constitution first: read `.specify/memory/constitution.md` before workspace setup, clarification, lane selection, subagent dispatch, or local analysis.
- If project cognition readiness requires `{{invoke:map-update}}`, `{{invoke:map-scan}}`, or `{{invoke:map-build}}`, record that requirement in `STATUS.md` while `understanding_confirmed: false`, present the Understanding Checkpoint, and only hand off to map maintenance after confirmation.
- Before the first subagent is dispatched, the leader may gather only the minimum context needed to choose scope, lane shape, and execution strategy. Do not perform broad repository analysis or implementation design locally before creating `STATUS.md` and selecting the first subagent path.
- Before implementation work starts, confirm the Understanding Checkpoint and persist `understanding_confirmed: true` in `STATUS.md`; only then identify whether the quick task is best handled by one bounded subagent or by two or more independent subagents that can safely proceed in parallel.
- [AGENT] Use the shared policy function before execution begins and again at each join point: `choose_subagent_dispatch(command_name="quick", snapshot, workload_shape)`.
- Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
- Treat `snapshot.delegation_confidence` as a runtime/model reliability signal for the current subagent path. If confidence is `low`, prefer the native subagent workflow or record `subagent-blocked` over fragile dispatch.
- Decision order:
  - One safe validated lane -> `one-subagent` on `native-subagents` when available.
  - Two or more safe isolated lanes -> `parallel-subagents` on `native-subagents` when available.  - No safe lane, overlapping writes, missing contract, low confidence, or unavailable delegation -> `subagent-blocked` with a recorded reason.
- Substantive quick-task lanes must use subagent execution once a validated `WorkerTaskPacket` or equivalent execution contract preserves quality. If that readiness bar is not met, compile the missing contract before dispatch; if the contract cannot be made safe, record `subagent-blocked` and stop for escalation or recovery.
- If two or more independent subagent lanes can safely run in parallel and that fan-out materially improves throughput, dispatch multiple subagents instead of serial execution.
- `subagent-blocked` is an exception path, not a strategy choice. Use it only when the current quick-task batch cannot proceed through subagents or the native subagent workflow.
- If subagent-blocked status is used, record the concrete reason in `STATUS.md`, including which subagent path was unavailable or blocked for the current batch.
- The first actionable execution step after scope lock and understanding confirmation is to dispatch the first subagent batch, not to continue local deep-dive analysis.
- Use `.specify/templates/worker-prompts/quick-worker.md` as the default contract for quick-task subagents so the subagent returns enough state for the leader to keep `STATUS.md` accurate.
- Prefer structured subagent results compatible with the shared `WorkerTaskResult` contract when the current runtime supports them.
- If the current integration exposes a runtime-managed result channel, use that channel. For Codex runtime-managed handoffs, the canonical path requires the runtime dispatch request id and is computed with `{{specify-subcmd:result path --command quick --request-id <request-id>}}`; final completion must be reported through the active runtime-managed result channel for that request id.
- Without a runtime-managed result channel, write the normalized subagent result envelope to `.planning/quick/<id>-<slug>/worker-results/<lane-id>.json`
- When the local CLI is available and no runtime-managed result channel exists, prefer `{{specify-subcmd:result path --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id>}}` to compute the canonical handoff target and `{{specify-subcmd:result submit --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id> --result-file <path>}}` to normalize and write the subagent result envelope. `result path` emits JSON and does not accept `--format`; do not append `--format`.
- Preserve `reported_status` when normalizing subagent language such as `DONE_WITH_CONCERNS` or `NEEDS_CONTEXT` into canonical orchestration state.
- Idle subagent is not an accepted result.
- The leader must wait for and consume the structured handoff before closing the join point, declaring completion, requesting shutdown, or interrupting subagent execution.

## Image and UI Reference Handoff

- UI handling applies even without an image. For every bounded user-visible UI
  change, record the approved `DESIGN.md`/live pattern, affected entry point,
  work/surface/platform type, subject/audience/job, approved direction/signature,
  states and viewports, must-preserve decisions, and real-entrypoint
  structure/visual/runtime evidence. Route a missing/bootstrap design or new visual direction to
  `sp-design`, and acceptance-heavy multi-surface work to `sp-specify`.
- Carry the confirmed UI Confirmation unchanged into `STATUS.md` and every UI
  worker packet. A worker may implement within its `must preserve`/`may adapt`
  boundaries but must not redesign the confirmed proposal; any conflict returns
  to the leader as a checkpoint amendment or workflow escalation.
- Treat a user-provided PNG, screenshot, mockup, design export, reference image, or "make it like this" UI request as a first-class worker input when it shapes the quick task.
- Before dispatch, record the image inputs in the quick-task context and include them in the `WorkerTaskPacket` or equivalent lane contract as `image_inputs` or UI reference inputs with stable project-relative paths when available.
- If the image exists only as a chat attachment, materialize it to a stable project-local artifact path or pass it to the subagent as a runtime image item/local_image when the integration supports that. Do not rely on inherited chat context, `fork_context`, or a prose summary as the only handoff.
- Dispatch image-backed UI lanes to a vision-capable or design-capable worker when the runtime exposes worker roles or capabilities.
- The lane contract must state the fidelity mode (`approximate` by default unless the user says `high` or `inspiration`), the original image input refs, visual constraints to preserve, allowed adaptations, required UI states, and screenshot or visual-review evidence.
- Do not dispatch a UI implementation worker when the worker would receive only the leader's textual description of the image. If the original image cannot be handed off or materialized and the lane depends on seeing it, record `subagent-blocked` with that reason instead of guessing.
- The accepted worker result must state which image inputs were inspected. If visual comparison is unavailable, record the fidelity status truthfully as pending human review or blocked instead of claiming visual match.
- Assign every reference its use intent and carry real content/image sources.
  Require `structure_snapshot`, `visual_capture`, `runtime_diagnostics`, and
  visual comparison or human review; use the platform-specific aliases from the
  shared UI contract.
- Before quick closeout, run the real surface, capture the representative
  viewport/state, inspect it, repair observable drift, and recapture. Passing
  behavior tests is separate from visual/interaction acceptance.

## Autonomous Execution Contract

- The leader must continue automatically until the quick task is complete or a concrete blocker prevents further safe progress.
- Do not stop after a single edit, single command, or single failed attempt when the next recovery step is obvious and low-risk.
- Do not start execution routing while `understanding_confirmed: false`; repair or confirm the Understanding Checkpoint first.
- Dispatch subagents when `snapshot.native_subagents` is true and the workload has one or more safe validated lanes.
- Substantive quick-task lanes must use subagent execution once a validated `WorkerTaskPacket` or equivalent execution contract preserves quality. If that readiness bar is not met, finish compiling the missing contract first; if the contract cannot be made safe, record `subagent-blocked` and stop for escalation or recovery.
- After `STATUS.md` is initialized, `understanding_confirmed: true` is recorded, and the first lane is defined, dispatch that subagent path before doing any further local repository deep dive.
- If multiple safe subagent lanes exist and they can improve throughput without creating write conflicts, dispatch them in parallel instead of artificially serializing the work.
- Use `subagent-blocked` only after subagent execution is concretely unavailable for the current batch and the native subagent workflow is also unavailable or unsuitable.
- Re-evaluate after every join point, recovery step, and validation result instead of assuming the first plan still holds.
- A quick task reaches a terminal state only when `STATUS.md` shows either `resolved` or `blocked`.

## Recovery Before Blocking

- When execution hits friction, attempt the smallest safe recovery step before declaring the task blocked.
- Default recovery order:
  - read additional local context that directly touches the failing area
  - run the smallest meaningful verification or repro command
  - inspect the immediate error output, logs, or failing test result
  - make one focused repair attempt that matches the evidence
  - if uncertainty remains high, use `--research`-style focused investigation for the narrow blocker rather than abandoning the task immediately
- Record each recovery step in `STATUS.md` under `recovery_action` and increment `retry_attempts`.
- If subagent execution is failing, attempt the next safe path before switching to subagent-blocked status:
  - retry the bounded subagent lane when the failure looks transient
  - retry or recompile the same native-subagent path when contract or context was insufficient
  - only then consider subagent-blocked status if no safe subagent path is currently available
- Escalate to `blocked` only when:
  - required credentials, services, permissions, or external systems are unavailable
  - the requirement remains high-impact ambiguous after the minimum safe clarification pass
  - repeated focused recovery attempts still leave no safe next step
  - the next action would be high-risk or destructive without user confirmation
- When blocked, write the concrete blocker reason to `blocker_reason`, preserve the best known next action, and stop only after the blocker is explicit.

## Surface Sweep Rule

- Treat every quick task as a small-scope complete sweep, not as an opportunistic one-file patch.
- Before editing, name the affected surfaces for this pass. Start from the smallest relevant set and expand until the task has a defendable boundary.
- Include propagation hotspots, consumer surfaces, verification entry points, and known unknowns from project cognition slices whenever they materially affect the quick task.
- For interface or contract changes, default sweep surfaces are:
  - implementation
  - export or declaration layer
  - docs
  - examples
  - tests
  - key callsites or consuming paths
- For other quick tasks, still name the concrete surfaces in play rather than implying coverage from a partial read.
- The leader must be able to say which surfaces were intentionally checked before claiming completion.
- For each named surface, record one explicit status conclusion:
  - `confirmed correct`
  - `fixed in this quick task`
  - `not checked in this pass (with reason)`
- Do not collapse `not checked` into silence. If a surface was not verified, say so explicitly and explain why it stayed outside the current pass.

## Process

1. **Scope gate**
   - Read `.specify/memory/constitution.md` first if present. Do not continue until this gate is satisfied.
   - Confirm the task is small but non-trivial.
   - Redirect to `{{invoke:fast}}` or `{{invoke:specify}}` if the task is outside the quick-task band.

2. **Create lightweight quick-task context**
   - Create or resume an id-based workspace under `.planning/quick/<id>-<slug>/`.
   - Keep quick-task artifacts separate from the main phase/spec workflow.
   - Initialize `STATUS.md` as the recoverable source of truth for the quick task.
   - Rebuild or refresh `.planning/quick/index.json` as a derived management projection when needed.
   - Do not continue into broad repository analysis or implementation planning until this workspace exists and the initial lane or batch is recorded.

3. **Optional pre-execution phases**
   - If `--discuss` is present, clarify assumptions and lock the minimum decisions needed.
   - If `--research` is present, gather focused implementation guidance.

4. **Lightweight planning**
   - Produce only the plan needed to execute this ad-hoc task safely.
   - Keep the work atomic and self-contained.
   - Keep local planning shallow until the Understanding Checkpoint is confirmed and the first subagent batch has been launched.
   - Identify the smallest safe execution lanes and choose the current execution strategy before implementation starts, but do not dispatch until `understanding_confirmed: true` is recorded.
   - For behavior-changing work, bug fixes, and refactors, the first executable lane must produce a failing automated test or failing repro check before production edits begin.
   - Do not write production code until the RED state is captured and recorded in `STATUS.md`.
   - If no reliable automated test surface exists for the touched behavior, bootstrap the smallest viable test surface first. If that bootstrap is no longer a bounded quick-task step, stop and escalate to `{{invoke:specify}}`.
   - For bug fixes and regressions, record the current root-cause explanation before implementation starts. If the root cause is not yet known, or if multiple plausible causes are still in play, stop and route to `{{invoke:debug}}` instead of applying a quick symptom patch.
   - A `surface-only` or symptom-only change cannot satisfy the quick-task contract for a bug fix unless the user explicitly scoped the work to temporary mitigation.
   - Name the affected surfaces for this quick-task pass and decide how each one will be checked.
   - If multiple safe lanes would materially improve throughput, plan the first fan-out as parallel subagents instead of defaulting to serial execution.
   - If the task includes a propagating change, write the minimal sweep plan first and list the affected surfaces that must be checked before completion.

5. **Execution**
   - Start execution only after `understanding_confirmed: true` is recorded in `STATUS.md`.
   - Execute the current quick-task lane or ready batch through the selected dispatch shape and execution surface.
   - For `one-subagent`, dispatch one subagent once the subagent-readiness bar is satisfied; otherwise finish compiling the missing contract before dispatch. If the contract cannot be made safe, record `subagent-blocked` and stop for escalation or recovery.
   - The first concrete execution action after understanding confirmation should normally be dispatching that subagent batch, not continuing local repository analysis.
   - If multiple subagent lanes are safe and useful, dispatch them in parallel as the current ready batch instead of holding back fan-out without a concrete coordination reason.
   - Keep changes tightly scoped to the quick-task goal.
   - Re-evaluate dispatch at each join point instead of assuming the first choice remains correct.
   - Only use `subagent-blocked` after subagent execution and the native subagent workflow are unavailable or blocked for the current batch, and record the blocked dispatch reason explicitly in `STATUS.md`.
   - When blocked, update `blocked_dispatch` in `STATUS.md` with the concrete unavailable or unsafe dispatch surface.
   - At each join point, update `done_or_progress_signal` with the latest completion proof or next safe progress signal.
   - Continue automatically until the quick task is complete or a concrete blocker prevents further safe progress.
   - If execution hits friction, attempt the smallest safe recovery step before declaring the task blocked.

6. **Validation**
   - If `--validate` or `--full` is present, perform plan checking and post-execution verification.
   - Otherwise still verify the change with the smallest meaningful executable check.
   - Do not skip verification just because the quick-task scope is small.

7. **Summary**
   - Write a concise summary artifact for what changed, how it was verified, and which surfaces were left unverified.
   - Prefer `SUMMARY.md` in `.planning/quick/<id>-<slug>/`.
   - Separate `verified` coverage from `not checked` coverage so readers can tell what was actually proven versus what is only expected to be safe.
   - For each declared surface, give the terminal status conclusion: `confirmed correct`, `fixed in this quick task`, or `not checked in this pass (with reason)`.
   - Make sure the final `STATUS.md` points to the summary, records the terminal state, and makes a future resume decision obvious.
