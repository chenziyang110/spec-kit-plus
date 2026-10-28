# Investigation contract

Create an absent session with `specify-runtime artifact scaffold --kind
debug-session --path .planning/debug/<slug>.md`, or resume it through targeted
`artifact show`, on every invocation. Aggregate same-checkpoint debug-session
frontmatter/section updates in memory and, when `api list` exposes
`artifact.patch-batch`, prefer one fresh lease plus one `artifact patch-batch`;
older runtimes fall back to one leased `artifact patch` per target update.
Never emit or submit the whole session. It is the durable source of truth for intake, evidence, transitions, human
verification, interruption, and recovery. Keep the visible symptom, failure
mechanism, and fix claim separate.

## Intake, evidence, and repair confirmation

New or materially changed intake starts with `understanding_confirmed: false`.
This flag records approval of a concrete repair, not permission to investigate.
Understand the report, expected behavior, environment, and boundary; clarify a
missing fact only when it blocks the next safe evidence step. Establish the
causal map, investigation contract, log plan, and observer framing and persist
`causal_map_completed: true`, `investigation_contract_completed: true`,
`log_investigation_plan_completed: true`, and `observer_framing_completed: true`
through a leased `specify-runtime artifact patch` before evidence work. With those flags complete,
unconfirmed diagnosis may inspect existing logs, source, configuration, tests,
and runtime output, run safe existing checks or a low-risk reproduction, and
delegate bounded read-only evidence questions. Use a provisional
existing/source-backed UI target when applicable; do not invent or approve a
redesign. External-side-effect and destructive-action gates still apply.

Before user approval, no product or test changes, harness repair, persistent
instrumentation, or fix-worker dispatch is allowed. Session updates use the
runtime-owned leased artifact routes. Investigate first, then present one
Debug Understanding Checkpoint from `references/human-confirmation.md` that
explains the discovered problem, proven root cause and decisive evidence,
concrete repair and affected boundaries, expected result, risks, and
verification. The user confirms the bounded repair; causal proof remains the
agent's responsibility. A diagnose-only response never authorizes a fix.

Persist the exact approved decision payload in `checkpoint`, with
`confirmation_purpose: evidence-backed-repair`, `discovered_problem`,
`root_cause`, decisive `evidence_refs`, `proposed_fix`, `change_scope`,
`expected_outcome`, `risks`, and `validation_plan`, plus reporter facts and
boundaries and the applicable UI decision. Compute `confirmation_digest` as
SHA-256 of that canonical JSON payload: sorted object keys, stable array order,
UTF-8; exclude both `checkpoint.confirmation_digest` and applicable
`ui_confirmation.confirmation_digest` self-fields, plus mutable
`agent_investigation_plan` or full evidence log. Persist
`understanding_confirmed: true` only after the user's
approval. Keep `ui_confirmation` separate in machine state but fold its formal
repair target baseline into the same card as `界面方向` and use one reply.
This is an agent-owned approval binding, not a claim of a runtime-enforced
confirmation gate or authenticated consent.

On resume, compare the exact saved approved payload and digest against the
current repair decision. Reuse a matching current approval without another
confirmation. A legacy/generic `understanding_confirmed: true`
without the concrete payload, `evidence-backed-repair` purpose, and matching
digest is not repair authority. Keep safe diagnosis available, reconstruct the
concrete checkpoint from evidence, and obtain repair approval before writes.
New raw evidence outside the approved payload alone does not require another
confirmation.

If diagnosis cannot proceed without a test/harness change or persistent
instrumentation, first explain the evidence gap, why existing observations are
insufficient, exact bounded diagnostic changes and risks, and their validation
and cleanup. Present the same checkpoint with
`confirmation_purpose: diagnostic-enablement`; mark the root cause unknown and
do not invent a product repair. Bind and persist that approved diagnostic
payload and digest, then perform only its authorized diagnostic changes through
the execution guard. After diagnostic work, return to investigation, set
`understanding_confirmed: false`, and obtain a separate
`evidence-backed-repair` confirmation before product repair. Diagnostic
approval never serves as product repair authority.

Do not reopen confirmation merely because an agent hypothesis changes or new
reproduction, log, source, or test observations support the same approved root
cause and repair. Update the session and continue within the exact approved
boundary. A material change to the confirmed problem, root cause, proposed
fix, change scope, expected outcome, risks, authority, or UI target invalidates
repair approval. This includes a separate or derived defect, migration,
compatibility, public-interface, external-side-effect semantics, or an explicit
stop condition. First set `understanding_confirmed: false` and pause repair
mutations and fix-worker dispatch; safe bounded diagnosis may continue.

Before presenting the amendment, explain in user-facing prose the decisive
evidence, why the previous confirmation no longer covers the investigation or
fix, the consequence of omitting it, the current mutation state and safe pause
point, and the exact incremental decision the user owns. Only after that
explanation, present `## Debug Checkpoint Amendment` with only the changed rows
or decisions and an `Unchanged` statement; do not repeat the full initial Debug
Checkpoint. Persist the new complete decision payload and digest after the
confirmed delta before resuming repair, and do not request
duplicate confirmation when the user already approved that exact delta.

For a UI-only material delta, keep the Debug amendment heading, include only
the changed UI Confirmation fields. State that the main checkpoint is unchanged.
The reason-first explanation remains mandatory; do not replay either complete initial table.

1. Capture an executable reproduction or the strongest available failure
   signal, including environment and inputs that materially affect it.
2. Rank a small set of competing hypotheses. For each, choose the cheapest
   observation that would distinguish it from the others.
3. Follow evidence across entry point, owner, state/data transformation,
   boundary, and consumer only as far as the symptom requires.
4. Claim root cause only when evidence explains both the failure and why the
   proposed change prevents it. Correlation, a suspicious line, or a passing
   test alone is insufficient.
5. After evidence-backed repair approval and before production edits, write and
   run a failing automated reproduction. Existing safe reproductions may run
   during diagnosis without approval. If no reliable test surface exists,
   build the smallest viable test harness when its bounded work is already
   included in the approved `change_scope` and `validation_plan`; that needs
   no additional approval. A
   harness gap that prevents diagnosis before repair approval instead uses the
   diagnostic-enablement route above. If
   that expands beyond the first debug fix lane, preserve the session, expand
   the registered causal scope, and run a tracked internal Debug recovery lane
   to repair the harness within the approved boundary, with an amendment before
   any material expansion. Do not invoke another user-invoked workflow
   automatically; after the harness is verified, return to this reproduction
   rather than weakening RED or ending at the route, and obtain evidence-backed
   repair approval if only diagnostic work was authorized. Use `$spx-specify` only
   when the user explicitly chooses a formal spec-first path.
6. Apply the minimum coherent approved fix. Re-run the original reproduction and verify
   the regression plus adjacent and related-risk surfaces.

If the reproduction is unavailable, state the substitute evidence and reduce
confidence. If new evidence changes the problem definition, update the session
instead of defending the original hypothesis.

After two failed verification cycles, return to `investigating`, strengthen
instrumentation or competing hypotheses, and re-prove root cause before another
fix. Persistent instrumentation and a materially changed repair still require
their bounded approval or amendment. Agent-side GREEN plus a completed related-risk review moves the session to
`awaiting_human_verify`, not `resolved`.

User feedback during human verification is classified as `same_issue`,
`derived_issue`, or `unrelated_issue`. `same_issue` reopens the parent;
`derived_issue` creates a linked child and returns to the parent after the child
closes; `unrelated_issue` creates a separate session without closing the parent.
Archive only after explicit human confirmation. A blocked or interrupted run
keeps its evidence, current hypothesis, blocker, and exact recovery action.


## Diagnosis-Only Delivery

When the confirmed checkpoint says `fix_authority: diagnose only`, complete
the requested diagnosis, not defect resolution. Keep confirmation and framing
gates, gather permitted evidence, and report the supported causal conclusion,
alternatives, confidence, remaining uncertainty, and the exact evidence basis.
Do not add or modify source, tests, harnesses, dependencies, configuration, or
instrumentation merely to make a diagnosis-only request follow the repair path.
Choose read-only or already-authorized isolated diagnostic probes instead.

Persist the findings in existing `Current Focus`, `Evidence`, and `Resolution`
sections. Retain the actual investigation state: no new status such as
`diagnosed`, no `resolved` claim, no fabricated GREEN or closeout receipt, and no
human-verification request for a nonexistent fix. Completion of the requested
diagnosis does not mean the defect was repaired. Keep unanswered diagnosis
obligations explicit; unavailable required evidence is not completed analysis.

An unrequested repair is not a user-owned blocker. Deliver the agreed findings
without requiring the user to authorize extra work. A later request for repair
uses the checkpoint amendment and fresh technical/write gates; it does
not inherit source-write permission from diagnosis alone.

## Continuous execution and resume

Navigation hints are not read authorization. Queue `minimal_live_reads` and
other source/log/test routes during intake; execute them only after accepted
framing. Safe bounded diagnosis does not require repair confirmation.
Repair writes proceed only after confirmation and accepted framing, with exact
approved authority and fresh execution guards. A ready map waives neither gate.

Optional feature artifacts require a valid feature binding and an existing,
relevant artifact. Query only their needed sections through the artifact owner
after the evidence-read gates pass. Standalone Debug does not require a formal
feature package: do not create missing spec, plan, tasks, or context artifacts
or launch a specification workflow merely to satisfy a context checklist.
Missing optional inputs are recorded as not applicable, not fabricated.
A required artifact of an actually bound feature remains a real input gate.

Resolve the session from an explicit slug, validated active binding, or one
unambiguous matching active record via `artifact list`; never choose by recency
alone. Classify continuing feedback before creating a new session. Resume the
earliest unsatisfied gate, retaining valid confirmation and accepted framing.
Do not reset a confirmed session to unconfirmed merely because it resumed.

Use accepted map-backed minimum intake when sufficient:
primary and contrarian candidates, first probe, log plan, transition memo and
related-risk target. Otherwise the leader schedules Stage 1A causal map before
Stage 1B investigation/log contract; Stage 1B consumes the accepted Stage 1A
output. Preserve deep intake's three families/candidates and falsifiers; do not
impose deep-only fields on valid map-backed minimum intake. Use
native subagents or a recorded authorized fallback with the same intake-only
restrictions. Do not wait for an assumed graph-engine callback or invoke a
Python workflow. Before evidence work, verify actual artifacts and
`causal_map_completed`,
`investigation_contract_completed`, `log_investigation_plan_completed`, and
`observer_framing_completed`; booleans alone are insufficient.

When advisory cognition is absent or unusable, use report-grounded deep intake
under the existing Stage 1A -> Stage 1B restrictions. Mark unknown owners,
paths and state explicitly; candidate loops are hypotheses, not live facts.
Use the confirmed report and available permitted system context to supply
discriminating probes and falsifiers, then verify the complete deep framing
before opening evidence reads. Do not invent a map, claim graph freshness, or
mark an empty framing package accepted. If a user-owned fact is essential,
ask only for that missing fact. Do not invoke map maintenance automatically.
An absent map is different from an unavailable canonical artifact runtime:
recover that runtime through its owning bootstrap, never by direct state writes.

Bind experiments to input revision or relevant digests, worktree, environment,
inputs/seed, exact command/manual sequence, expected failure signature,
observed output/exit code, and evidence refs. RED must match the target defect;
a harness/import/permission/timeout failure is not target RED for a different
defect. If that mechanism is itself the confirmed target, require its exact
failing signature. Otherwise recover the supporting cause, then rerun the
original target check. For intermittent bugs,
preserve attempts and outcomes under controlled inputs before and after repair;
one non-reproduction does not establish resolution. Use bounded discriminating
experiments, not blind retries or indefinite polling.

Use one active causal decision and a complete ranked candidate queue. Parallel
falsifiers are evidence lanes, not competing production fixes. Persist both
supporting and contradicting signals, eliminated/deprioritized candidates,
truth owner, control/observation boundary and loop-break proof in existing
session sections. Two failed verification cycles require renewed investigation,
not an automatic user handoff. Local recovery must resume the interrupted gate
in the same invocation and continue independent dependency-ready work.

For each delegated packet, bind session/lane identity, accepted prerequisites,
input revision/digests, evidence question, allowed commands/paths, forbidden
writes, expected/falsifying observations, resource/timeout budget, result
channel and join criterion. Different files do not establish independence:
ports, databases, browser profiles, fixtures, caches and external environments
must be isolated or serialized. Never parallelize a producer with its dependent
consumer. An evidence worker is not a production-fix worker.

Treat capability snapshots as installation metadata, not proof of availability.
Check the live tool surface and actual response before dispatch; never invoke an
invented tool or Python policy helper. After authorized inline fallback, record
`execution_model: leader-inline`, `execution_surface: leader-inline` and the
matching dispatch shape. Preserve historical dispatch failure in `Evidence`,
not stale current `blocked_reason` or `execution_surface: none`. A required
independent review remains pending even when leader execution continues.

At joins, inspect packet identity, input basis, commands/exit codes,
expected/observed outcomes, evidence refs and missing rows. Withhold acceptance
of stale, incomplete, wrong-session or unverifiable submissions; preserve the raw
evidence and request only missing or invalid rows. Contradictory observations
are valid evidence when provenance and inputs match. Do not ask a worker to
change an observation to fit the current hypothesis. Keep observations separate
from interpretations and use a discriminating probe, not a majority vote.
Invalidate affected consumer acceptance when its basis changes, preserving
unaffected evidence.

A crashed, timed-out, or unsafe worker may be cancelled through its native owner
without waiting for a missing handoff. Cancellation is not task acceptance:
preserve partial evidence, the missing result, and owned resource identities.
No broad process kill or cleanup of other lanes' resources. Confirm quiescence
before redispatch, then resume the failed gate. A required independent validator
must not author or edit the fix; keep acceptance pending when unavailable and
never label self-verification an independent review.

## Write Authorization and Guard Scope

Before any source, test, harness, configuration, or instrumentation write,
recheck confirmed authority, current anchors, and declared scope through
`specify-runtime execution guard`. Register supporting scope through its owner;
after scope expansion or source drift affecting the binding, renew the guard
before affected writes. A permitted supporting repair or diagnostic probe may
precede original target RED only in its own guarded scope, with separate causal
evidence, before-state, result, and cleanup. This does not bypass target RED for
changes to the original target's production behavior. Supporting recovery does
not prove that defect resolved.

Before production writes, also recheck accepted causal/RED evidence.
Diagnosis-only authority does not permit
instrumentation writes. Keep instrumentation behavior-neutral, record observer
or timing effects, redact secrets and track cleanup. Before final validation,
remove only session-owned temporary probes/resources or explain retained
instrumentation, then rerun affected checks on the final integrated revision.
Never reset a worktree or restore a whole file to undo only the agent's patch.

Use existing `Current Focus`, `Suggested Evidence Lanes`, `Evidence`,
`Candidate Resolutions`, `Execution Intent` and `Resolution` for progress and
resume, not new top-level fields or a parallel state file. At joins, pauses and
human waits preserve accepted/pending lanes, active probe, failed gate, owned
paths/resources, attempts/results and exact next action. Batch same-checkpoint
patches where supported. On lease conflict reread and merge the intended delta
without erasing newer evidence. Inspect a possibly completed action's result
before replaying a mutation or redispatching.

## Final evidence and human verification

These repair-completion gates apply to an authorized fix. For confirmed
`diagnose only` authority, follow Diagnosis-Only Delivery instead; findings are
not a claim that the defect was fixed or that a nonexistent patch passed.

Keep the complete required verification rows: original reproduction, target
regression, control-loop restoration, related risks, affected consumers, and
UI real-entrypoint recapture when applicable. Bind each row to the final source
revision or relevant digests, environment, command/sequence, expected/observed
outcomes and evidence. Failed, skipped, unavailable and stale rows stay open;
aggregate PASS or an accepted failure report is not a passing prerequisite.
Source changes, cleanup, or changed accepted inputs invalidate affected rows.

Agent GREEN and related-risk review lead to `awaiting_human_verify`, not
`resolved`. Give exact user verification steps, expected behavior and validated
revision. Default feedback to `same_issue` unless evidence establishes a
linked derived or unrelated issue. Classification is not confirmation; neither
it nor a resolved child closes the parent. Explicit human confirmation must
match the current verified fix, not a superseded patch.

Preserve the existing cognition/Learning and guarded execution closeout gates.
Recover their failures without repeating human verification when the fix and
evidence are unchanged. A clean completion claim needs current verification,
explicit human confirmation and the required successful closeout receipt;
`status=ok` alone does not suffice. Archive only when requested after these
gates pass, through the artifact owner. Commit only authorized scoped changes;
this grants no push, merge, release or deployment authority. A true remaining
boundary uses the shared blocked-exit contract with attempted recovery, open
rows, withheld claims and exact resume action, never a claim of resolution.
