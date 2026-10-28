# Quick worker contract

Use for each substantive Q-item lane under Quick's mandatory native-subagent model.
The leader owns `STATUS.md`, scope, join decisions, final verification, and
cognition closeout—not the default first implementation edit.

Read-only intake workers are a separate bounded discovery use of native
subagents before confirmation: name read paths, safe-check permissions and
stop conditions, grant no product write scope, and return inspectable findings
with source/check refs. They do not call `quick item-start`, consume an
implementation packet, change product/test/harness files, add persistent
instrumentation or produce Q acceptance. The implementation contract below
requires the exact confirmed or validated inherited proposal and its normal
runtime packet/Work gates. Carry its current-state evidence, concrete approach
and risk boundaries so the worker does not lose the approved context.

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
delegate from prose-only screenshot interpretation. Include exact
`interaction_matrix`, `editing_matrix`, `data_state_matrix`, component `interaction_modes` /
`data_scenarios`, and responsive `stretch_behavior` / `overflow_behavior` rows;
exercise exact event sequence, immediate feedback, focus, repeat, cancellation,
and pending behavior for pointer/mouse and keyboard/focus plus applicable touch/command,
empty/populated and degraded/recovery data, and active resize. The worker must not redesign
the confirmed direction; contract drift returns to the leader as a blocker.

The worker returns:

- status: done, done-with-concerns, blocked, or needs-context;
- `work_item_id`, `depends_on`, prerequisite evidence consumed, and work-item
  acceptance evidence produced or still missing;
- paths read and changed;
- evidence and commands actually run;
- failed assumptions, blockers, and recovery recommendation;
- any scope or contract conflict requiring leader judgment.

The leader must not edit the worker's active write scope between `item-start`
and `item-accept`. Consume the handoff (`result submit` with lane-id matching
the Q item) before closing the lane; idle or stopped execution is not a result,
and runtime refuses `item-accept` without that worker result (or prior
`quick allow-inline`). Re-run the meaningful integrated verification on the
leader path.

Return `cognition_delta` with `schema: "spec-kit-cognition-delta-v1"`,
`version: 1`, and the packet's reported identity. Its `changed_paths` includes
all retained edits even on blocked/failed attempts; `path_changes` preserves
both endpoints of each rename. Keep behavior, owner/consumer/interface,
generated chain, state contract, verification/evidence, invalidated claim,
unknown, confidence and recovery facets as nested JSON candidates. The native
result channel retains submissions and the item owner binds exact acceptance;
workers cannot supply `submission_history` or `cognition_result_binding`.
Conflicting aliases are refused. The leader's closeout planner consumes stored
results/history, retaining unaccepted semantics as candidates and every
retained edit in invalidation accounting; resolve overlapping path or claim
conflicts explicitly.
Before dispatch, require
`{{specify-subcmd:specify-runtime api ensure --capabilities cognition.worker-delta.v1 --format json}}`;
repair or upgrade a missing capability before source-changing work.

## Professional UI contract continuity

Quick preserves the confirmed affected subset of `surface_catalog`,
`scenario_matrix`, `interaction_matrix`, `editing_matrix`, `data_state_matrix`,
`accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, and `usability_validation`, including
component governance/iconography. It may not downgrade approved truth. Verify
risk-based or pairwise scenarios, never an unbounded Cartesian product, and
leave target-user human review explicit.

## Exact Task Scope Availability

After the owning runtime compiles the canonical current task packet, and before
dependent graph consumption, require `specify-runtime api ensure --capabilities
cognition.scope-availability.v2 --format json`, then run `specify-runtime cognition
check --task-packet <exact-project-relative-packet-path> --format json`. Use the
compiler's returned packet path; do not assemble a substitute packet or infer
complete read dependencies from prose. Quick confirmation items declare optional
`read_scope` as an explicit array of exact paths, including required UI contract
and original reference inputs when applicable. Missing legacy `read_scope` is
unknown; explicit `[]` is a complete empty declaration. Null, non-arrays and
non-string paths refuse. Read metadata follows execution `write_scope` digest
exclusion; it never changes registered UI approval or grants worker write scope.

Carry native `availability`, `scope_ready`, `global_status`, `debt_assessments`,
`reasons`, `minimal_live_reads` and `binding` separately. Only an actual version 2
ready result permits scoped advisory graph navigation; proven unrelated debt
remains visible globally. Blocked/degraded/unavailable or unknown proof suspends
dependent graph consumption and uses bounded current live reads, with gaps
explicit. Do not erase blocked results or treat advisory warnings as uniform
protection. Commands without a canonical packet keep the global check and cannot
assert unrelated debt. This route applies with hooks and without hooks on every
CLI and both profiles.

At handoff/resume and before reusing graph context, rerun the same native check
with `--availability-json <previous-native-binding-json>` against the current
canonical packet. Changed source/packet/status/dependency/claim bytes or an old
contract invalidate reuse; repair the owning proof and obtain a new result. Scope
readiness never declares the project globally fresh, grants source write
authority, sets workflow `claim_ready`, or replaces independent Review and human
Accept. Preserve normal packet/Work/UI prerequisite and approval gates.
