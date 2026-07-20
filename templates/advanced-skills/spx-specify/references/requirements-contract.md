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
