# Quick worker contract

Use for each substantive Q-item lane under Quick's mandatory native-subagent model.
The leader owns `STATUS.md`, scope, join decisions, final verification, and
cognition closeout—not the default first implementation edit.

Give the worker the complete objective, allowed read/write paths, forbidden
paths, authoritative inputs, acceptance checks, and expected handoff. Do not
make the worker rediscover the task from broad planning files.
Every packet also carries one `work_item_id`, its `depends_on` ids, prerequisite
acceptance evidence, and the exact work-item acceptance it advances. Do not
dispatch a dependent item before those prerequisites pass. For serial same-file
Q items, reuse or resume one subagent across `Q1`→`Q2`→`Qn` with a fresh packet
per `item-start`; do not collapse that into unrecorded leader-inline work.
For UI work, include original visual references and their intents, real
content/image sources, the confirmed UI Confirmation, the compact UI contract,
`references/ui-quality-gate.md`, and required structure/visual/runtime evidence; do not
delegate from prose-only screenshot interpretation. The worker must not redesign
the confirmed direction; contract drift returns to the leader as a blocker.

The worker returns:

- status: done, done-with-concerns, blocked, or needs-context;
- `work_item_id`, `depends_on`, prerequisite evidence consumed, and work-item
  acceptance evidence produced or still missing;
- paths read and changed;
- evidence and commands actually run;
- failed assumptions, blockers, and recovery recommendation;
- any scope or contract conflict requiring leader judgment.

The leader must not edit the worker's active write scope. Consume the handoff
before closing the lane; idle or stopped execution is not a result. Re-run the
meaningful integrated verification on the leader path.
