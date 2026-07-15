# Investigation contract

Create or resume a session from `assets/debug-session.md` on every invocation.
It is the durable source of truth for intake, evidence, transitions, human
verification, interruption, and recovery. Keep the visible symptom, failure
mechanism, and fix claim separate.

## Intake gate

New or materially changed intake starts with `understanding_confirmed: false`.
Present the Debug card from `references/human-confirmation.md`; when UI applies,
append its target-baseline card and use one reply for both. Persist user-owned
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
the changed UI Confirmation rows. State that the main checkpoint is unchanged.
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
   that harness cannot remain bounded, hand off to `$spx-quick` or
   `$spx-specify` and stop rather than weakening RED.
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
