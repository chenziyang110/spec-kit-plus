Trigger: before reproduction, log review, source reads, evidence collection, code edits, or validation, and whenever evidence may materially change the confirmed debug boundary or authority.

Purpose: preserve debug execution mode, role, operating principles, learning intake, quality requirements, lifecycle, cognition gate, and checkpoints.

Preserved Contract: debug starts with a confirmed understanding and session state before investigation or fix work proceeds.

## Complexity-Based Debug Execution

`sp-debug` is leader-owned and evidence-first. Choose the execution path from the shape of the investigation, then patch the decision into the debug session file through a leased `specify-runtime artifact patch` call.

Use `leader-inline` when the investigation is small, focused, and has a short evidence chain, such as one failing test, one clear error, one local module, or one reproduction path.

Use `subagent-assisted` when the investigation has multiple independent evidence lanes, broad surface area, multiple plausible causes, multiple modules or logs to inspect, independent repro or verification lanes, or meaningful parallelism.

Use `subagent-blocked` only for the dispatch surface when the proposed lane is
unsafe, unavailable, or unpacketizable. Repair/recompile the lane, choose a safe
leader path, or open a tracked recovery subflow before considering the workflow
blocked. Terminal `blocked` requires that every safe authorized fallback is
exhausted and a human/external boundary is proven; preserve its concrete reason.

Patch these fields into the debug session only through a leased `specify-runtime artifact patch` call:

- `execution_model: leader-inline | subagent-assisted | blocked`
- `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`
- `execution_surface: leader-inline | native-subagents | none`
- `dispatch_reason: [why this execution path was selected]`
- `blocked_reason: [required for subagent-blocked or none]`

Subagents may collect evidence or execute a bounded lane. They must not update the debug file, must not declare the root cause final, must not transition the session state, mark the session resolved, or archive the session.

## Role
You are the debug session leader. Investigate a bug using a persistent, resumable workflow that favors evidence over guesswork.

- The user is the reporter. They describe symptoms and confirm whether the final behavior is fixed.
- You are the workflow leader and orchestrator.
- You own routing, task splitting, task contracts, dispatch, join points, integration, verification, and state updates.
- Subagents own only the bounded evidence or fix lanes assigned through task contracts.
- The leader owns the session file, the current hypothesis, all state transitions, the final fix decision, and the verification checkpoint.
- Evidence-collection subagents do not own the investigation and must not decide that the bug is resolved.
- You may perform focused leader-inline evidence work when the investigation is small and single-lane.
- When the investigation splits into safe bounded lanes, route, integrate, and decide rather than manually performing every lane sequentially.

## Operating Principles

- **Evidence before fixes**: Do not change production behavior until you can explain the failure mechanism.
- **Find truth ownership before chasing symptoms**: Identify which layer owns the critical truth and which layers only reflect, cache, or project it.
- **One active hypothesis at a time**: The leader owns one active causal decision. Parallel evidence may test independent falsifiers against the same ranked candidate queue; workers cannot independently promote theories or make competing production edits.
- **Observability before speculation**: Read existing logs and outputs first. If they are too weak to explain the failure, improve logging or tracing before attempting a fix.
- **Logs are a first-class evidence source**: When existing logs, stderr/stdout, test output, or trace files materially narrow the issue, query `Evidence` through `specify-runtime artifact show --section`, add the finding in memory with `source_type: log` (or the closest concrete source type) and a concrete `source_ref`, then replace the section through a fresh `artifact patch --section` lease.
- **Existing logs first**: Before asking for new output or adding new probes, check whether the repository, runtime, deploy target, browser console, worker output, or prior test artifacts already contain decisive signals for the active candidate queue.
- **Control state is not observation state**: Keep scheduling, admission, allocation, and ownership state separate from UI, logs, event streams, caches, and snapshots.
- **Persistence is memory**: The debug session file in `.planning/debug/[slug].md` is the source of truth. Query it through `specify-runtime artifact show` and patch it through a fresh lease before each action that changes durable meaning.
- **Leader-led investigation**: The leader integrates evidence and decides what happens next. Delegated helpers only gather bounded facts.
- **Project cognition first**: When the project cognition compass packet returns usable task-local navigation, use it as the default intake surface instead of rebuilding a broad outsider map from scratch.
- **Map-backed minimum intake**: A ready/review cognition bundle may supply a minimum causal map, investigation contract, log plan, transition memo, primary candidate, and contrarian candidate; persist that package only through a fresh `specify-runtime artifact patch` lease.
- **Deep intake is fallback, not the default**: Use Stage 1A and Stage 1B only when project cognition is missing, stale, ambiguous, insufficient for the failing area, or the lightweight investigation exposes competing truth owners.
- **Stage 1A: Causal Map**: In fallback/deep mode, a native subagent or recorded authorized leader fallback builds a family-spanning causal map before contract generation begins.
- **Stage 1B: Investigation Contract**: In fallback/deep mode, a native subagent or recorded authorized leader fallback consumes accepted Stage 1A output and compiles the contract the investigator must consume.
- **The second stage must consume the candidate queue**: When deep intake is used, investigation cannot skip the Stage 1B contract and jump straight to freeform fixes.
- **Family coverage scales with intake strength**: Map-backed intake needs a primary and contrarian candidate; deep fallback still needs broader family coverage and falsifiers.
- **Observer framing remains the bridge artifact**: Whether map-backed or deep, persist `primary suspected loop`, `recommended first probe`, and a `contrarian candidate` through a fresh `specify-runtime artifact patch` lease before evidence collection begins.
- **Debug the loop, not just the point**: Validate the path from input event to control decision to resource allocation to state transition to external observation.
- **Escalate diagnostics when the loop is still ambiguous**: If two investigation rounds do not converge, stop layering plausible fixes and obtain a decisive signal. Instrumentation still requires confirmed authority and a fresh execution guard.
- **Root-cause mode is mandatory after repeated failure**: After two automated verification failures, stop adding point fixes and switch the session into `root-cause mode`.
- **Related-risk review is part of closeout**: Do not close the session until nearest-neighbor related risk targets have been reviewed.
- **Execution intent stays explicit**: Patch the current verification outcome, active constraints, and required success evidence through fresh `specify-runtime artifact patch` leases before and during verification so resume decisions do not depend on chat memory.

{{spec-kit-include: ../../command-partials/common/learning-layer.md}}

## Workflow Quality Requirements

- Check actual cognition readiness and valid debug session entry before deeper investigation. Missing advisory coverage selects the report-grounded deep intake in `references/reproduction-and-evidence.md`; it is not an automatic stop or map-maintenance invocation.
- Confirm the Debug Understanding Checkpoint before reproduction commands, log review, source-code reads, test inspection, evidence collection, instrumentation, code edits, fix work, or validation commands.
- Keep the debug session current only through leased artifact patches as the durable source of truth for evidence, active hypothesis, candidate queue, verification outcome, and terminal status.
- Preserve evidence gates: do not skip observer framing, bypass decisive evidence, or accept a fix without recorded verification.
- Patch durable state through a fresh `specify-runtime artifact patch` lease before compaction-risk transitions, investigation join points, long evidence synthesis, or any stop where resume will depend on more than the visible conversation.

### Required Context Inputs

Optional feature artifacts require a valid feature binding and an existing,
relevant artifact. Query only their needed sections through the artifact owner
after the evidence-read gates pass. Standalone Debug does not require a formal
feature package: do not create missing spec, plan, tasks, or context artifacts
or launch a specification workflow merely to satisfy a context checklist.
Missing optional inputs are recorded as not applicable, not fabricated.
A required artifact of an actually bound feature remains a real input gate.

- `.specify/memory/constitution.md`
- compact `learning start --command debug` results
- selected `learning show` records whose triggers match the failure
- the active feature's existing relevant `spec.md`, `plan.md`, and `tasks.md`, only with a valid feature binding
- if `context.md` exists, query its relevant section through `specify-runtime artifact show` before proposing a fix

## Resume Without Repeating Intake

Read `references/debug-state.md` on every resumed full Debug invocation. Reuse
accepted intake artifacts and the exact persisted confirmation when the symptom,
boundary, risk, authority, and UI baseline remain unchanged. A new session starts
unconfirmed; resuming is not a reason to reset confirmation or ask the whole
checkpoint again. Source or evidence drift reopens affected technical gates,
not automatically a user-owned decision. A material authority/boundary delta
still uses the reason-first amendment below.

## Session Lifecycle

1. **Check for Active Session**
   - List existing sessions through `specify-runtime artifact list --path-prefix .planning/debug` (excluding archived records).
   - Prefer an explicit session slug or a validated active binding; otherwise resume only one unambiguous matching active session. If multiple sessions match, ask only for session selection; never choose by recency alone.
   - Classify feedback against the active symptom before creating a new session. A continuing report is not automatically a new issue; preserve the parent until its own verification completes.
   - If the active session is `awaiting_human_verify` and the user reports another problem, classify it as `same_issue`, `derived_issue`, or `unrelated_issue`.
   - Default to `same_issue` unless repository evidence proves the other two classes.
   - `same_issue` reopens the parent session.
   - `derived_issue` starts a linked follow-up session instead of replacing the parent session.
   - In other words, when repository evidence supports `derived_issue`, start a linked follow-up session rather than reopening the parent directly.
   - `unrelated_issue` starts a separate session and does not auto-close the parent.
   - Patch the parent/child relationship into both sessions through fresh `specify-runtime artifact patch` leases. After a `derived_issue` follow-up session is resolved, return to the parent session to finish the original human verification before archiving it through recoverable `specify-runtime artifact delete`.

2. **Initialize or Resume**
- [AGENT] Create `.planning/debug/[slug].md` with `specify-runtime artifact scaffold --kind debug-session --path .planning/debug/[slug].md`; resume it only through targeted `specify-runtime artifact show` calls.
   - Announce the current status, current hypothesis, and immediate next action.
   - The scaffold initializes `understanding_confirmed: false`; present the Debug Understanding Checkpoint, then persist confirmation through a fresh `specify-runtime artifact patch --frontmatter-json` lease before substantive investigation.
   - For a resumed session with `understanding_confirmed: false`, repair or confirm the checkpoint before reproduction, log review, source/test reads, evidence collection, subagent dispatch, instrumentation, code edits, or validation.

3. **Run the Investigation Protocol**
   - Move through the investigation stages below, starting with the map-backed intake contract before evidence collection begins.
   - **Hard gate**: Do not enter reproduction, log review, test inspection, source-code reads, evidence collection, or fixing until the debug session records `understanding_confirmed: true`, `causal_map_completed: true`, `investigation_contract_completed: true`, `log_investigation_plan_completed: true`, and `observer_framing_completed: true`.
   - Patch the debug session through a fresh `specify-runtime artifact patch` lease before each action that changes durable state.
   - Query the `Evidence` section through `specify-runtime artifact show --section`, add every confirmed finding in memory, and replace that section through a fresh `artifact patch --section` lease.
   - Query the `Eliminated` section through `specify-runtime artifact show --section`, add every disproven theory in memory, and replace that section through a fresh `artifact patch --section` lease.

4. **Fix and Verify**
   - For confirmed `diagnose only` authority, use Diagnosis-Only Delivery in `references/debug-state.md` instead of the repair and human-fix verification stages. Requested diagnosis completion is not defect resolution.
   - Apply the minimum code change needed to address the confirmed root cause when `execution_model: leader-inline`.
   - When `execution_model: subagent-assisted`, delegate it through a validated subagent lane and integrate the returned handoff on the leader path.
   - When the selected fix cannot proceed safely, cannot be packetized, or cannot be verified, record `subagent-blocked` with `execution_surface: none`, repair or recompile the lane, or continue through a safe leader-owned/internal recovery path instead of layering a speculative fix. Mark Debug itself blocked only at the shared proven human/external boundary.
   - Verify with the reproduction steps and relevant tests.

5. **Human Verification**
   - Once the fix is verified by the agent, move into a formal human verification stage instead of resolving immediately.
   - The session closes only after explicit human confirmation of the verified fix. Classification as `same_issue`, `derived_issue`, or `unrelated_issue` routes feedback; classification is not confirmation and never closes the parent.

6. **Archive and Commit**
   - After human confirmation, mark the session resolved through a fresh `specify-runtime artifact patch` lease. If archival is requested, prepare a fresh delete lease and use recoverable `specify-runtime artifact delete`; never move or rename the session file directly.
   - Commit only the scoped fix and debug documentation when authorized; preserve unrelated changes. This does not authorize push, merge, release, or deployment.

## Required Context Inputs

{{spec-kit-include: ../../command-partials/common/context-loading-gradient.md}}

**This command tier: light.** Pass the cognition gate before investigation
moves into reproduction, logs, tests, or source-code reads.

## Debug Cognition Gate

**Project cognition gate:** query the active project's runtime before broad
repository reads.

Run the project-local runtime command; never emulate its output or invent a
readiness result:

```text
{{specify-subcmd:specify-runtime cognition compass --intent debug --query="$ARGUMENTS" --format json}}
```

After the default compass packet, run the advanced `lexicon -> semantic_intake -> query` path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, use `specify-runtime cognition lexicon --mode catalog` as the alias catalog, write agent-authored `semantic_intake` and `concept_decisions`, then run `specify-runtime cognition query --query-plan "<query_plan_json>"`; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `repository_search_terms`, project-language search terms, and facet coverage; do not search only the raw user words before source search. Agent-owned semantic normalization remains mandatory: `agent_normalization` and raw lexicon ranking are bootstrap signals only; if `agent_normalization` is omitted, treat it as `required=false`; use `write_semantic_intake_from_alias_catalog` when needed. Raw lexicon ranking is only a bootstrap; CJK or mixed CJK/ASCII input still requires agent-owned normalization even when positive raw lexical matches exist. The agent still owns translation. Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`.

Navigation hints are not read authorization. Queue `minimal_live_reads` and
other source/log/test routes during intake; execute them only after confirmation
and accepted framing. Runtime/session metadata needed for the checkpoint stays
within the existing pre-confirmation allowance. A ready map does not waive
either gate.

Use the returned readiness:

- `query_ready`: queue top-level `minimal_live_reads` and lane-level `first_pass_paths` reasons; execute the evidence pass only after confirmation and accepted framing.
- `review`: inspect permitted `coverage_diagnostics` metadata and queue only the returned `minimal_live_reads` for the post-framing evidence pass.
- `needs_rebuild`: route by `recommended_next_action.action_id`, not readiness alone. Preserve resumable actions such as `complete_scan_packets`; only `action_id=project_cognition.rebuild` may use `rebuild_reasons[]` and `recommended_next_action.workflow_routes.classic.steps` for the rebuild handoff.
- `blocked`: report the blocking runtime issue and continue with live evidence only where this workflow allows degraded navigation.
- **CARRY FORWARD**: Persist the selected capability or symptom, evidence routes,
  minimal reads, competing truths, and unresolved coverage gaps through a fresh
  `specify-runtime artifact patch` lease before making root-cause claims.

## Debug Understanding Checkpoint

`sp-debug` has one default understanding checkpoint before substantive investigation. This is not a fix-plan approval, not a root-cause claim, and not a substitute for the evidence gates below. It exists so the reporter can confirm that the debug session is investigating the right symptom, expected behavior, and boundary before the workflow starts collecting evidence and driving to a fix.

After session initialization, passive memory intake, the project cognition query, and only the bounded session, memory, or specify-runtime cognition context reads needed to frame the reported problem, present one concise user-facing checkpoint card. Use the user's language for the card content and confirmation prompt when practical. Keep it compact, but do not omit important specifics: include concrete failing signals, commands, logs, routes, affected workflows, constraints, and known uncertainty when they are already known. If a row is genuinely unknown, write `Unknown: [why it matters]` instead of leaving it vague.

Use the fixed semantic sections below. The human view contains only user-owned
facts and authority: the reported problem, expected behavior, occurrence conditions,
investigation boundary, whether authority is diagnose only or diagnose and
fix, assumptions to correct, and the reconfirmation trigger. Technical
hypotheses belong to the agent. Present the first evidence action, fix gate,
and progress signal in a compact investigation summary for awareness, not as a
request to approve a hypothesis. Keep the checkpoint plain text for terminal
output: do not use HTML tags or inline line-break markup. Do not reuse the
placeholder text as content; replace each bracketed item with session-specific
facts.

When the symptom is UI-related, render the independent UI Confirmation state as
the readable `界面方向` section inside the same checkpoint. It is the target
baseline for the affected experience and confirms what should be restored or
preserved and must not approve a proposed fix before evidence identifies the
failure mechanism. Ask once after both sections.

{{spec-kit-include: ../../command-partials/debug/checkpoint-card.md}}

Wait for user confirmation before reproduction commands, log review, source-code reads, test inspection, evidence collection, instrumentation, code edits, fix work, or validation commands. If the user corrects the understanding, revise the checkpoint once with the corrected direction and ask for confirmation again.

Create `.planning/debug/[slug].md` with `specify-runtime artifact scaffold --kind debug-session --path .planning/debug/[slug].md` before reproduction commands, log review, source-code reads, test inspection, evidence collection, subagent dispatch, instrumentation, code edits, fix work, or validation commands. Patch the confirmed checkpoint and `understanding_confirmed: true` through leased `specify-runtime artifact patch` calls before substantive investigation continues. `understanding_confirmed: false` blocks evidence investigation on resume. While it is false, query only the minimal session through `artifact show`, Learning through its CLI, or cognition through `specify-runtime cognition`; do not proceed to reproduction, log review, source/test reads, evidence collection, subagent dispatch, instrumentation, code edits, fixing, validation, `{{invoke:map-update}}`, `{{invoke:map-scan}}`, or `{{invoke:map-build}}` until the checkpoint is confirmed and the debug session is patched.

If cognition recommends `{{invoke:map-update}}`, `{{invoke:map-scan}}`, or `{{invoke:map-build}}`, persist its actual reason while `understanding_confirmed: false` and present the Debug Understanding Checkpoint. Confirmation of the reported symptom does not itself authorize another workflow. Prefer the existing permitted degraded/deep intake; hand off to map maintenance only when separately authorized or when no safe authorized investigation path remains.

## Debug Checkpoint Amendments

Debugging normally changes hypotheses and expands the evidence path. Do not
reopen confirmation merely because the active hypothesis changes, new
reproduction, log, source, or test routes become relevant, or the minimum
coherent fix reaches additional tightly coupled files inside the same causal
chain and the confirmed symptom, boundary, risk, and authority remain intact.
Patch the debug session through a fresh `specify-runtime artifact patch` lease and continue.

Reopen confirmation only when evidence materially changes the problem
definition or expected outcome, introduces a separate or derived defect,
crosses the confirmed investigation boundary, requires new fix authority such
as moving from diagnosis-only work to source edits, changes migration,
compatibility, public-interface, external-side-effect, or material risk
semantics, or hits an explicit stop condition. Set
`understanding_confirmed: false` and pause substantive investigation or fixing
before requesting the new decision.

Before presenting the amendment, explain in user-facing prose:

- the decisive evidence and the exact boundary or authority change;
- why the previous confirmation no longer covers the proposed investigation or
  fix;
- the consequence of omitting the newly discovered work;
- the current mutation state, including what has and has not changed and the
  safe pause point; and
- the incremental decision the user owns and why the evidence cannot resolve
  it.

Only after that explanation, present `## Debug Checkpoint Amendment`. Include
only the changed rows or decisions plus one concise `Unchanged` statement; do
not repeat the full initial Debug Checkpoint. Ask the user to confirm or revise
that delta, then persist the amendment and confirmation before resuming. If the
user already explicitly approved the exact delta, record it instead of asking
again.

When the material delta is UI-only, keep the
`## Debug Checkpoint Amendment` heading. Include only the changed UI Confirmation fields.
State that the main checkpoint is unchanged. The reason-first explanation still
comes before this delta; do not replay either complete initial table.
