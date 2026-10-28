Trigger: when creating, updating, resuming, or archiving the debug session file.

Purpose: preserve debug file protocol, session lifecycle fields, active hypothesis, evidence, state transitions, and archive behavior.

Preserved Contract: the debug file remains the durable source of truth for evidence, hypothesis, verification, and terminal status.

## Debug File Protocol

- **Location**: `.planning/debug/[slug].md`
- **understanding_confirmed**: a repair-approval flag, not a diagnosis
  prerequisite. Set true only after explicit user approval of the exact current
  decision payload; retain the fixed `## Debug Understanding Checkpoint`
  section for compatibility.
- **checkpoint**: keep reporter facts and bounds plus `confirmation_purpose`,
  `discovered_problem`, `root_cause`, `evidence_refs`, `proposed_fix`,
  `change_scope`, `expected_outcome`, `risks`, and `validation_plan`. Use
  `evidence-backed-repair` for concrete repair approval, or
  `diagnostic-enablement` for a narrowly approved missing diagnostic harness or
  persistent instrumentation only. Diagnostic authority permits no production
  fix and returns to diagnosis before repair approval.
- **confirmation_digest**: SHA-256 of canonical approved decision JSON
  (sorted keys, stable arrays, UTF-8), computed by the leader in memory. Include
  reporter facts/bounds, purpose, discovered problem/root cause, decisive
  evidence references, proposed fix/scope/outcome/risks/validation, and the
  applicable UI decision. Exclude checkpoint/UI confirmation digests, mutable agent investigation
  plan, and full evidence log. Persist the exact approved payload and digest
  through fresh artifact leases; compare them before mutation and on resume.
  Legacy true or generic diagnose-and-fix without this purpose and matching
  concrete approved contents cannot authorize repair. These checks do not imply
  runtime enforcement.
- **causal_map_completed**: `false` until the Stage 1A causal map, dimension scan, and candidate board are persisted through leased `specify-runtime artifact patch` calls.
- **investigation_contract_completed**: `false` until the Stage 1B investigation contract is persisted through a leased `specify-runtime artifact patch` call.
- **log_investigation_plan_completed**: `false` until the Stage 1B log investigation plan is persisted as its own section through a leased `specify-runtime artifact patch` call.
- **observer_framing_completed**: `false` until the canonical intake package is complete.
- **legacy_session_needs_reintake**: `true` only when a resumed legacy session cannot safely satisfy the canonical intake gate.
- **Current Focus**: replace this section on every durable update through a fresh `specify-runtime artifact patch --section` lease. Reflect exactly what the leader is doing now.
- **Evidence**: query the section through `specify-runtime artifact show --section`, add confirmed findings in memory, then replace it through a fresh `artifact patch --section` lease.
- **Eliminated**: query the section through `specify-runtime artifact show --section`, add disproven theories in memory, then replace it through a fresh `artifact patch --section` lease.
- **Update Rule**: mutate the session only through `specify-runtime artifact`; never edit, append, rename, move, or delete the file directly.
- No source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`.
- After the intake/observer gates, `understanding_confirmed: false` permits safe
  bounded reproduction, existing log/source/test reads, and read-only evidence
  subagents. It blocks fix/source/test/harness/persistent instrumentation writes
  and fix-worker dispatch. Preserve external/destructive action gates and use
  provisional source-backed UI observations during diagnosis; confirm the UI
  target together with repair before mutation.

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
   - If a session exists and no new issue is described, resume it.
   - If a new issue is described, start a new session.
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
   - The scaffold initializes `understanding_confirmed: false`; understand the report, complete the existing intake/observer gates, and gather bounded evidence before presenting the concrete repair checkpoint.
   - On resume, compare the exact approved payload and digest. Missing, legacy, or stale approval blocks mutation and fix-worker dispatch while safe bounded diagnosis may continue in scope. Do not request another confirmation for the same approved repair merely because more evidence was recorded.

3. **Run the Investigation Protocol**
   - Move through the investigation stages below, starting with the map-backed intake contract before evidence collection begins.
   - **Intake gate**: Do not enter reproduction, log review, test inspection, source-code reads, or evidence collection until the debug session records `causal_map_completed: true`, `investigation_contract_completed: true`, `log_investigation_plan_completed: true`, and `observer_framing_completed: true`. `understanding_confirmed` is not a diagnosis prerequisite.
   - Patch the debug session through a fresh `specify-runtime artifact patch` lease before each action that changes durable state.
   - Query `Evidence` through `artifact show --section`, add each confirmed finding in memory, and replace the section through `artifact patch --section`.
   - Query `Eliminated` through `artifact show --section`, add each disproven theory in memory, and replace the section through `artifact patch --section`.

4. **Fix and Verify**
   - Present the discovered problem and decisive evidence, concrete repair and scope, expected outcome, risks, and validation. Wait for explicit user approval and persist the exact payload plus digest before repair writes or fix-worker dispatch. Material changes to cause, repair, scope, risk, UI target, or authority invalidate this approval: pause mutation, explain why, and obtain only the changed decision through the Debug Checkpoint Amendment before resuming; bounded diagnosis within scope may continue.
   - Apply the minimum code change needed to address the confirmed root cause when `execution_model: leader-inline`.
   - When `execution_model: subagent-assisted`, delegate it through a validated subagent lane and integrate the returned handoff on the leader path.
   - When the fix cannot proceed safely, cannot be packetized, or cannot be verified, record `subagent-blocked` with `execution_surface: none` and a concrete blocked reason instead of layering a speculative fix.
   - Verify with the reproduction steps and relevant tests.

5. **Human Verification**
   - Once the fix is verified by the agent, move into a formal human verification stage instead of resolving immediately.
   - The session closes only after explicit human confirmation or an evidence-backed classification into `same_issue`, `derived_issue`, or `unrelated_issue`.

6. **Archive and Commit**
   - After human confirmation, mark the session resolved through a leased `specify-runtime artifact patch`. If archival is requested, prepare a fresh lease and run recoverable `specify-runtime artifact delete`; never move or rename the file directly.
   - Commit the fix and the debug documentation.
