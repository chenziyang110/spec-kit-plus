# System Review worker contract

The leader orchestrates subagents through three explicit waves and retains
global state, the Review Universe, shared runtime resources, joins, finding
acceptance, zero-uncovered reconciliation, and the final verdict.

These are orchestration waves inside the validation-epoch budget shared across
Implement and Review, not separate permission to rerun heavyweight gates. Do not
reset the ledger. The Leader opens at most one epoch for all audit scenarios
against a source fingerprint and one later epoch after a Fix when budget remains.
Read-only workers may observe slices within an open epoch but cannot open their
own. The combined flow permits at most three; the third failed epoch blocks and
no agent may ever start a fourth.

Compile each just-in-time `SystemReviewPacket` from the current handoff and
Review state. Mark its lane `audit`, `diagnostic`, `fix`, or `revalidation`; it
is a delegation view, not a second source of truth. `diagnostic` is a packet
lane only; persist its read-only `review-state.json` assignment with
`kind: scenario_review` and `read_only: true`, never `kind: diagnostic`. Include:

- one scenario/lane outcome and authoritative acceptance references;
- official real entrypoint, ready signal, preconditions, and safe test data;
- exact actions and observable expected results;
- allowed reads, isolated writes if any, and forbidden paths/actions;
- required evidence and runtime/UI capture conditions;
- finding/result destination or exact structured return shape;
- failed-assumption, blocker, and recovery requirements.

Start with a read-only Review/Audit wave for independent coverage discovery,
startup/runtime diagnosis, wiring and consumer reachability, distinct user
journeys, and UI/accessibility inspection. An audit worker has no product write
scope and cannot declare coverage complete. The leader joins every audit result
and freezes accepted findings before starting the independent Fix wave.

Fix workers receive accepted finding ids and bounded write scopes. They run
cheap task checks, return test impact, and must not run heavyweight validation
per Txx. Run shared
browser sessions, database mutations, common accounts, registries, and one
runtime instance serially; dispatch concurrent writes only when scopes are
disjoint and no generated or shared consumer overlaps. Unknown root cause work
uses a read-only diagnostic packet while Review remains the stage owner.

After all repair joins, open the next remaining validation epoch and run an
independent revalidation wave. A repair author
must not verify its own finding; the leader or a different read-only subagent
reruns the failed journey and affected scenarios against the repaired snapshot.
That subset scopes finding-level revalidation only. After any Fix, the leader
must rerun every required Review scenario and recapture all required evidence
against the single final reviewed snapshot before approval.

The final revalidation worker returns the complete accepted Fix id set and its
canonical digest, the exact required-scenario set, and a current-cycle
`evidence_manifest_ref` whose byte-bound JSON enumerates every required
scenario/evidence-kind path and artifact digest. Cycle 1 artifacts also require
their current cycle id, confined Review path, and byte digest.

Require a structured result containing scenario status, actions actually run,
observed results, evidence refs, findings, changed paths, checks, failed
assumptions, blockers, and recovery guidance. A worker must not change the
scenario matrix, global Review state, shared runtime ownership, or final source
fingerprint. It cannot declare the whole product passed or bypass an observed
failure with synthetic evidence.

At every join, validate the result against the packet, inspect all Review-owned
writes, reconcile duplicate or conflicting findings, and reject evidence from
the wrong entrypoint or snapshot. After repairs, the leader restarts the real
product and reruns the affected integrated journeys. Approval requires all
packets joined and the Review Universe at zero uncovered before the leader may
issue the final verdict.
