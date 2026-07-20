# System Review worker contract

Delegate only when a bounded lane improves independence, coverage, or repair
throughput. The leader retains global state, shared runtime resources, finding
acceptance, integrated revalidation, and the final verdict.

Compile each just-in-time `SystemReviewPacket` from the current handoff and
Review state. It is a delegation view, not a second source of truth. Include:

- one scenario/lane outcome and authoritative acceptance references;
- official real entrypoint, ready signal, preconditions, and safe test data;
- exact actions and observable expected results;
- allowed reads, isolated writes if any, and forbidden paths/actions;
- required evidence and runtime/UI capture conditions;
- finding/result destination or exact structured return shape;
- failed-assumption, blocker, and recovery requirements.

Prefer independent read-only lanes for startup/runtime diagnosis, wiring and
consumer reachability, distinct user journeys, and UI/accessibility inspection.
Run shared browser sessions, database mutations, common accounts, and one
runtime instance serially. Separate audit and repair waves; dispatch concurrent
writes only when their scopes are disjoint and no generated or shared consumer
overlaps.

Require a structured result containing scenario status, actions actually run,
observed results, evidence refs, findings, changed paths, checks, failed
assumptions, blockers, and recovery guidance. A worker must not change the
scenario matrix, global Review state, shared runtime ownership, or final source
fingerprint. It cannot declare the whole product passed or bypass an observed
failure with synthetic evidence.

At every join, validate the result against the packet, inspect all Review-owned
writes, reconcile duplicate or conflicting findings, and reject evidence from
the wrong entrypoint or snapshot. After repairs, the leader restarts the real
product and reruns the affected integrated journeys before any final verdict.
