Trigger: when creating, updating, resuming, or archiving the debug session file.

Purpose: preserve debug file protocol, session lifecycle fields, active hypothesis, evidence, state transitions, and archive behavior.

Preserved Contract: the debug file remains the durable source of truth for evidence, hypothesis, verification, and terminal status.

## Debug File Protocol

- **Location**: `.planning/debug/[slug].md`
- **causal_map_completed**: `false` until the selected map-backed minimum causal map, or deep Stage 1A map with dimension scan and candidate board, is accepted and persisted through leased `specify-runtime artifact patch` calls. Do not impose deep-only fields on valid minimum intake.
- **investigation_contract_completed**: `false` until the selected minimum-intake or deep Stage 1B investigation contract is accepted and persisted through a leased `specify-runtime artifact patch` call.
- **log_investigation_plan_completed**: `false` until the selected minimum-intake or deep Stage 1B log plan is accepted and persisted as its own section through a leased `specify-runtime artifact patch` call.
- **observer_framing_completed**: `false` until the canonical intake package is complete.
- **legacy_session_needs_reintake**: `true` only when a resumed legacy session cannot safely satisfy the canonical intake gate.
- **Current Focus**: replace this section on every durable update through a fresh `specify-runtime artifact patch --section` lease. Reflect exactly what the leader is doing now.
- **Evidence**: query the section through `specify-runtime artifact show --section`, add confirmed findings in memory, then replace it through a fresh `artifact patch --section` lease.
- **Eliminated**: query the section through `specify-runtime artifact show --section`, add disproven theories in memory, then replace it through a fresh `artifact patch --section` lease.
- **Update Rule**: mutate the session only through `specify-runtime artifact`; never edit, append, rename, move, or delete the file directly.
- No source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`.

The session file must always make it clear:
- what the observer framing concluded,
- what the active hypothesis is,
- what experiment is being run,
- why the current logs are sufficient or insufficient,
- which layer owns the relevant truth,
- which state is control state versus observation state,
- where the closed loop is currently believed to break,
- and what the next action is if the session resumes later.

## Session Lifecycle

1. **Check for Active Session**
   - List active records with `specify-runtime artifact list --path-prefix .planning/debug`; do not enumerate `.planning/debug/*.md` directly.
   - Prefer an explicit session slug or a validated active binding; otherwise resume only one unambiguous matching active session. If multiple sessions match, ask only for session selection; never choose by recency alone.
   - Classify feedback against the active symptom before creating a new session. A continuing report is not automatically a new issue; preserve the parent until its own verification completes.
   - If the active session is `awaiting_human_verify` and the user reports another problem, classify it as `same_issue`, `derived_issue`, or `unrelated_issue`.
   - Default to `same_issue` unless repository evidence proves the other two classes.
   - `same_issue` reopens the parent session.
   - `derived_issue` starts a linked follow-up session instead of replacing the parent session.
   - In other words, when repository evidence supports `derived_issue`, start a linked follow-up session rather than reopening the parent directly.
   - `unrelated_issue` starts a separate session and does not auto-close the parent.
   - Patch the parent/child relationship into both sessions through fresh `specify-runtime artifact patch` leases. After a `derived_issue` follow-up session is resolved, return to the parent session to finish the original human verification before archiving it through `specify-runtime artifact delete`.

2. **Initialize or Resume**
- [AGENT] Create `.planning/debug/[slug].md` with `specify-runtime artifact scaffold --kind debug-session --path .planning/debug/[slug].md`; resume it only through targeted `specify-runtime artifact show` calls.
   - Announce the current status, current hypothesis, and immediate next action.
   - The scaffold initializes `understanding_confirmed: false`; present the Debug Understanding Checkpoint, then persist confirmation through a fresh `specify-runtime artifact patch --frontmatter-json` lease before substantive investigation.
   - For a resumed session with `understanding_confirmed: false`, repair or confirm the checkpoint before reproduction, log review, source/test reads, evidence collection, subagent dispatch, instrumentation, code edits, or validation.

3. **Run the Investigation Protocol**
   - Move through the investigation stages below, starting with the map-backed intake contract before evidence collection begins.
   - **Hard gate**: Do not enter reproduction, log review, test inspection, source-code reads, evidence collection, or fixing until the debug session records `understanding_confirmed: true`, `causal_map_completed: true`, `investigation_contract_completed: true`, `log_investigation_plan_completed: true`, and `observer_framing_completed: true`.
   - Patch the debug session through a fresh `specify-runtime artifact patch` lease before each action that changes durable state.
   - Query `Evidence` through `artifact show --section`, add each confirmed finding in memory, and replace the section through `artifact patch --section`.
   - Query `Eliminated` through `artifact show --section`, add each disproven theory in memory, and replace the section through `artifact patch --section`.

4. **Fix and Verify**
   - Apply the minimum code change needed to address the confirmed root cause when `execution_model: leader-inline`.
   - When `execution_model: subagent-assisted`, delegate it through a validated subagent lane and integrate the returned handoff on the leader path.
   - Record `subagent-blocked` as dispatch evidence when a lane is unsafe or unavailable; repair its packet/tool path, serialize it, or use an authorized leader fallback. Do not close Debug merely because delegation failed. Preserve the exact interrupted gate and resume it after recovery.
   - Verify with the reproduction steps and relevant tests.

5. **Human Verification**
   - Once the fix is verified by the agent, move into a formal human verification stage instead of resolving immediately.
   - The session closes only after explicit human confirmation of the verified fix. Classification as `same_issue`, `derived_issue`, or `unrelated_issue` routes feedback; classification is not confirmation and never closes the parent.

6. **Archive and Commit**
   - After human confirmation, mark the session resolved through a leased `specify-runtime artifact patch`. If archival is requested, prepare a fresh lease and run recoverable `specify-runtime artifact delete`; never move or rename the file directly.
   - Commit only the scoped fix and debug documentation when authorized; preserve unrelated changes. This does not authorize push, merge, release, or deployment.

## Earliest-Unsatisfied-Gate Resume

On entry/resume, read only the session identity, `Current Focus`, confirmation,
framing flags, `Execution Intent`, and relevant `Resolution`/evidence sections.
Use a current runtime lease/revision and the recorded input/output evidence
basis. Do not reopen a valid confirmation or recreate accepted intake merely
because a new invocation started. Load a detailed reference only at its trigger;
reuse unchanged evidence instead of repeatedly rereading the whole repository.

Resume the earliest unsatisfied gate: confirmation -> framing -> reproduction
and causal proof -> guarded fix -> final-revision validation -> human verify ->
closeout. Check substantive outputs, not booleans alone. A changed input or
source revision/digest reopens only affected technical gates and consumers;
material boundary/authority changes still require the checkpoint amendment.
Human feedback must bind to the currently verified fix, not a superseded patch.

Persist the active candidate/probe, accepted and pending lanes, failed gate,
owned changed paths, evidence basis, attempted recovery, live resource owners,
and exact next action in the existing sections before a join, interruption or
human wait. Do not add new top-level fields or a parallel state file. Use one
same-checkpoint `artifact patch-batch` when supported; otherwise patch through
fresh leases. On a lease conflict, reread and merge the intended semantic delta
against current state, preserving history; never replay a stale whole-section
replacement that erases newer evidence. Inspect a prior action's recorded
result before retrying a possibly completed mutation or redispatching a lane.
