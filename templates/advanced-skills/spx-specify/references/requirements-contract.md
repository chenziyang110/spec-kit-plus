# Requirements contract

The specification is planning truth, not implementation design. Preserve the
user's complete confirmed capability unless they explicitly defer part of it.

Capture:

- target need and observable user/system outcomes;
- in-scope, out-of-scope, and explicitly deferred behavior;
- constraints and decisions that restrict valid solutions;
- acceptance criteria with actor/input, observable result, and important error
  or recovery behavior;
- required operations and existing behavior that must survive;
- unresolved items that materially block planning.

Ask only when repository evidence cannot resolve a decision and different
answers would change behavior, public interfaces, data/state lifecycle,
security, compatibility, or acceptance. Record safe assumptions explicitly.

Keep implementation choices out unless they are already a confirmed constraint.
Do not convert uncertainty into vague requirements such as "works correctly".
Every material requirement must be testable or otherwise observable.

Record machine-readable closure in `acceptance_coverage`, one
`requirement_ref`/`acceptance_ref` pair per row. Requirement refs are canonical
JSON Pointers to every item in `scope.in` and `capability_operations` (escaping
mapping keys per RFC 6901); acceptance refs point to
`spec-contract.json#/acceptance_criteria/N`. A requirement may need multiple
criteria, but every requirement must appear and every acceptance criterion must
appear exactly once, so one generic criterion cannot stand in for multiple
independent requirements.

Before declaring planning-ready, reconcile contradictions between the contract,
spec, discussion/UI handoffs, live behavior, and project rules. A non-empty
semantic change to previously confirmed user intent requires explicit review.

## Entrypoint outcome inheritance

For a new or changed entry point over an existing operation, a
direct/background/headless/system entry point, or a changed consumer or
interaction owner, build `entrypoint_outcome_contract` from current live
evidence: result/error definitions, existing consumers, state transitions,
tests, and UI/window/request/retry owners. Archived specifications are excluded
from default discovery; use one only for explicit lineage or provenance and
verify the traced claim against current live evidence.

Persist live facet values in `learning_context`, the contextual read in
`learning_search_refs`, every returned ref in `learning_candidate_refs`, and
exactly one `applied`, `not_applicable`, or `deferred` item in
`learning_dispositions` for each candidate. Do not silently ignore or
auto-apply a candidate: applied Learning traces to requirement or `CA-###`
refs, not-applicable needs current evidence, and deferral needs an explicit
deferral ref.

Keep `result_inventory` separate from `outcome_dispositions` and require exact
closure. Classify outcomes as terminal success/failure, cancelled,
`recoverable-user-input`, recoverable automatic, or partial success. Every
preserved/adapted outcome has observable behavior, canonical
`spec-contract.json#/acceptance_criteria/N` refs, and `CA-###` refs.
Not-applicable needs current evidence; deferral needs explicit
user confirmation, residual risk, and a reopen condition. Direct/background or
no-home constraints do not prohibit interaction required for recovery. Do not
declare planning-ready with an incomplete inventory or any uncovered outcome.
