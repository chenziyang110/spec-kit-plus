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

## Intake gate

New or materially changed intake starts with `understanding_confirmed: false`.
Present the Debug checkpoint from `references/human-confirmation.md`; when UI
applies, fold its independent target-baseline state into the same human card as
`界面方向` and use one reply for both. Persist user-owned
facts, fix authority, and `ui_confirmation` separately from the
`agent_investigation_plan`. Present the first evidence step only as agent-owned
context, then wait for user confirmation. Before reproduction, log
review, source or test reads, evidence collection, delegation,
instrumentation, edits, or validation, only the minimal context needed to frame
that checkpoint may be read. Persist confirmation before continuing.

Do not reopen confirmation merely because evidence changes a hypothesis, adds
reproduction, log, source, or test routes, or extends the minimum coherent fix
through tightly coupled files in the same causal chain while the confirmed
symptom, boundary, risk, and authority remain intact. Update the session and
continue. Reopen only when evidence materially changes the problem or expected
outcome or confirmed UI target baseline, introduces a separate or derived
defect, crosses the investigation boundary, requires new fix authority, changes
migration, compatibility, public-interface, external-side-effect, or material
risk semantics, or hits an
explicit stop condition; first set `understanding_confirmed: false` and pause
substantive work.

Before presenting the amendment, explain in user-facing prose the decisive
evidence, why the previous confirmation no longer covers the investigation or
fix, the consequence of omitting it, the current mutation state and safe pause
point, and the exact incremental decision the user owns. Only after that
explanation, present `## Debug Checkpoint Amendment` with only the changed rows
or decisions and an `Unchanged` statement; do not repeat the full initial Debug
Checkpoint. Persist the confirmed delta before resuming, and do not request
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
5. Before production edits, write and run a failing automated reproduction. If
   no reliable test surface exists, build the smallest viable test harness. If
   that expands beyond the first debug fix lane, preserve the session, expand
   the registered causal scope, and run a tracked internal Debug recovery lane
   to repair the harness. Do not invoke another user-invoked workflow
   automatically; after the harness is verified, return to this reproduction
   rather than weakening RED or ending at the route. Use `$spx-specify` only
   when the user explicitly chooses a formal spec-first path.
6. Apply the minimum coherent fix. Re-run the original reproduction and verify
   the regression plus adjacent and related-risk surfaces.

If the reproduction is unavailable, state the substitute evidence and reduce
confidence. If new evidence changes the problem definition, update the session
instead of defending the original hypothesis.

After two failed verification cycles, return to `investigating`, strengthen
instrumentation or competing hypotheses, and re-prove root cause before another
fix. Agent-side GREEN plus a completed related-risk review moves the session to
`awaiting_human_verify`, not `resolved`.

User feedback during human verification is classified as `same_issue`,
`derived_issue`, or `unrelated_issue`. `same_issue` reopens the parent;
`derived_issue` creates a linked child and returns to the parent after the child
closes; `unrelated_issue` creates a separate session without closing the parent.
Archive only after explicit human confirmation. A blocked or interrupted run
keeps its evidence, current hypothesis, blocker, and exact recovery action.


## Continuous execution and resume

Resolve the session from an explicit slug, validated active binding, or one
unambiguous matching active record via `artifact list`; never choose by recency
alone. Classify continuing feedback before creating a new session. Resume the
earliest unsatisfied gate, retaining valid confirmation and accepted framing.
Do not reset a confirmed session to unconfirmed merely because it resumed.

After confirmation, use accepted map-backed minimum intake when sufficient:
primary and contrarian candidates, first probe, log plan, transition memo and
related-risk target. Otherwise the leader schedules Stage 1A causal map before
Stage 1B investigation/log contract; Stage 1B consumes the accepted Stage 1A
output. Preserve deep intake's three families/candidates and falsifiers; do not
impose deep-only fields on valid map-backed minimum intake. Use
native subagents or a recorded authorized fallback with the same intake-only
restrictions. Do not wait for an assumed graph-engine callback or invoke a
Python workflow. Before evidence work, verify actual artifacts and
`understanding_confirmed`, `causal_map_completed`,
`investigation_contract_completed`, `log_investigation_plan_completed`, and
`observer_framing_completed`; booleans alone are insufficient.

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

At joins, inspect packet identity, current input basis, commands/exit codes,
expected/observed outcomes, evidence refs and missing rows. Reject stale,
incomplete, wrong-session or contradictory returns for bounded repair; resolve
contradictions with a discriminating probe rather than a vote. Invalidate
affected consumer acceptance when its basis changes, preserving unaffected
accepted evidence. A silent/blocked worker stays leader-owned: inspect state,
repair or fall back; quiesce its owned mutable resources before redispatch so
two attempts do not race. A required independent validator must not author or
edit the fix; keep required independent acceptance pending when unavailable,
and never label self-verification an independent review.

Before source writes, recheck fix authority, current patch anchors, causal/RED
evidence and the execution guard. Diagnosis-only authority does not permit
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
