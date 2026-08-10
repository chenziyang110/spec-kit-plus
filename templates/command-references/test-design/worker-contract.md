Trigger: when preparing, leasing, checkpointing, yielding, accepting, or independently auditing a test-design lane.

Purpose: Preserve the runtime-owned packet boundary, read-only worker role, and Leader-only join authority for discovery and independent audit lanes.

Preserved Contract: A worker consumes one leased self-contained brief, reads only packet paths, returns the canonical lane-result shape, checkpoints or yields before capacity exhaustion, and never writes or accepts canonical workflow state.

Discovery lanes propose evidence-backed `candidate_cases`, `data_requirements`,
`contradictions`, `unknowns`, and `gaps`. Every inspected path must be inside the
frozen packet. A partial lane checkpoints useful completed work and yields the
remainder; it never marks unread scope complete. Workers never write canonical
artifacts, invoke `artifact patch` or `gap-reconcile`, or merge a whole runtime
file; their checkpoint is only a candidate for Leader review.

The independent `AUDIT-*` lane must be assigned to a worker that did not author
the synthesis. It checks reverse traceability, omitted risks and consumers,
weak or circular oracles, duplicate cases, infeasible harnesses, missing or
unsafe materials, contradictions, exclusions, and stale evidence. It reports
findings to the Leader and cannot self-accept or declare global completeness.

Only the Leader may call lane acceptance after comparing the result with the
leased packet. The Leader selects the accepted truth, registers accepted
evidence, and submits approved case, data, and coverage changes only through a
fresh lease plus targeted `artifact patch`; approved gaps go only through
runtime `gap-reconcile`. `synthesize` validates the resulting canonical bundle
and advances its runtime state; it does not automatically materialize worker
proposals. Only the runtime applies those mediated mutations, calculates claim
status, and creates the Tasks handoff.
