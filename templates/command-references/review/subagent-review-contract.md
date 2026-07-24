Trigger: before delegating review or repair work and before accepting a worker result.

Purpose: gain independent inspection and safe parallelism without splitting ownership of runtime truth or the final verdict.

## Leader-Orchestrated Waves

The Leader orchestrates subagents through three explicit waves and owns the joins between them:

1. A read-only Review/Audit wave performs independent coverage discovery across disjoint slices of the Review Universe. An audit worker has no product write scope and cannot declare coverage complete.
2. After joining and reconciling every audit result, an independent Fix wave assigns accepted findings to Fix workers with bounded, non-overlapping write scopes. Serialize shared registries, generated consumers, browser/database state, or overlapping writes.
3. After joining and inspecting every repair, an independent revalidation wave assigns the failed journey and affected regression paths to the Leader or a different read-only worker. A repair author must not verify its own finding.

These are orchestration waves, not permission for unlimited heavyweight runs.
Continue the validation ledger shared across Implement and Review and do not
reset it. The Leader opens attempts inside Review's delivery gate. Read-only
workers may observe slices inside the open attempt but cannot open their own.
The combined flow has three logical gates; interruptions retry inside delivery
and real failures require repair plus a new fingerprint.

Compile every `SystemReviewPacket` just in time and identify its lane as `audit`, `diagnostic`, `fix`, or `revalidation`. `diagnostic` is a packet lane, not a `review-state.json` assignment kind: persist a diagnostic packet's read-only assignment with `kind: scenario_review` and `read_only: true`, never `kind: diagnostic`. The packet contains only the assigned obligation/surface/finding ids, current fingerprint, authoritative refs, official real entrypoint, preconditions and safe test data, exact actions, observable expected results, allowed read/write scope, forbidden paths and external effects, required evidence, failure taxonomy, validation commands, done condition, and recovery/return shape. Unknown root cause work uses a read-only diagnostic packet inside Review before the Leader issues any Fix packet.

The result records status, observations, sanitized evidence refs, findings,
changed paths, cheap task checks and test impact for Fix lanes, validation and
rerun results for an already-open audit/revalidation attempt, concerns, and
recovery. A Fix worker must not run heavyweight gates per Txx. The Leader
validates live repository state and the packet boundary before accepting it.

## Authority

Workers never own `review-state.json`, the Review Universe, shared runtime instances, ports, test data, cross-lane finding status, joins, or the global claim gate. A worker cannot declare coverage complete or the system approved and must not advance workflow state. The Leader owns zero-uncovered reconciliation, confirms all packets joined, accepts every repair, and owns the final verdict after integrating results, restarting the actual product, and running the mandatory and affected regression scenarios.
