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
