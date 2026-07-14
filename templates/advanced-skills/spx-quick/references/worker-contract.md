# Quick worker contract

Use only for an independent bounded lane. The leader owns `STATUS.md`, scope,
join decisions, final verification, and cognition closeout.

Give the worker the complete objective, allowed read/write paths, forbidden
paths, authoritative inputs, acceptance checks, and expected handoff. Do not
make the worker rediscover the task from broad planning files.

The worker returns:

- status: done, done-with-concerns, blocked, or needs-context;
- paths read and changed;
- evidence and commands actually run;
- failed assumptions, blockers, and recovery recommendation;
- any scope or contract conflict requiring leader judgment.

The leader must not edit the worker's active write scope. Consume the handoff
before closing the lane; idle or stopped execution is not a result. Re-run the
meaningful integrated verification on the leader path.
