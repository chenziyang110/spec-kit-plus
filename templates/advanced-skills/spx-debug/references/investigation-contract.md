# Investigation contract

Persist a session from `assets/debug-session.md` only when recovery across turns
is useful. Keep the visible symptom, failure mechanism, and fix claim separate.

1. Capture an executable reproduction or the strongest available failure
   signal, including environment and inputs that materially affect it.
2. Rank a small set of competing hypotheses. For each, choose the cheapest
   observation that would distinguish it from the others.
3. Follow evidence across entry point, owner, state/data transformation,
   boundary, and consumer only as far as the symptom requires.
4. Claim root cause only when evidence explains both the failure and why the
   proposed change prevents it. Correlation, a suspicious line, or a passing
   test alone is insufficient.
5. Apply the minimum coherent fix. Re-run the original reproduction, add a
   regression check when practical, and verify adjacent risk surfaces.

If the reproduction is unavailable, state the substitute evidence and reduce
confidence. If new evidence changes the problem definition, update the session
instead of defending the original hypothesis.
