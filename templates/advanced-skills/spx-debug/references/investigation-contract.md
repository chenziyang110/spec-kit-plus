# Investigation contract

Create or resume a session from `assets/debug-session.md` on every invocation.
It is the durable source of truth for intake, evidence, transitions, human
verification, interruption, and recovery. Keep the visible symptom, failure
mechanism, and fix claim separate.

## Intake gate

New or materially changed intake starts with `understanding_confirmed: false`.
Present the symptom, environment, intended outcome, boundaries, and proposed
first evidence step, then wait for user confirmation. Before reproduction, log
review, source or test reads, evidence collection, delegation,
instrumentation, edits, or validation, only the minimal context needed to frame
that checkpoint may be read. Persist confirmation before continuing.

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
