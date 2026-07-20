Trigger: before starting or resuming an official entrypoint or required scenario.

Purpose: prove integrated, user-observable behavior rather than implementation-shaped proxies.

## Coverage Boundary

Before scenario execution, the Leader compiles the Review Universe from the handoff plus independent coverage discovery of authoritative requirements, design/architecture obligations, changed consumer surfaces, runtime controls and registrations, and affected shared paths. The handoff matrix is a minimum, never the complete universe by assertion. Reconcile each obligation and discovered surface to a required scenario or a specific evidence-backed out-of-scope disposition.

Review always covers:

- installation/build/startup and the ready signal for each applicable official real entrypoint;
- every required user journey introduced or changed by this feature;
- directly affected shared surfaces and the regression paths needed to protect them.

Do not expand into an unbounded audit of unrelated legacy behavior. Do not narrow the active feature to only its easiest happy path.

The coverage gate is zero uncovered: no required obligation, official entrypoint, changed consumer surface, or applicable runtime-discovered control may remain unmapped or unexecuted. All packets joined is a separate gate. A worker cannot declare coverage complete; only the Leader may reconcile the universe after independent audit results have joined.

## Scenario Requirements

Every mandatory scenario has a stable id, source acceptance refs, entrypoint, preconditions, safe test data, actions, observable expected results, required evidence, result, and exact resume point. Cover startup, reachability, interaction, state change/persistence, error or permission behavior, and cross-component integration when applicable.

Operate the software. A passing test suite, present component, compiled route, implemented handler, or registered-looking provider does not prove that a user can reach and use it. Exercise buttons, links, menus, forms, shortcuts, and commands, then trace their real route-handler-provider/factory-service-persistence/feedback chain when an observation fails or consumer wiring is at risk. Flag dead controls, unreachable pages, orphan implementations, unregistered consumers, swallowed errors, missing feedback, and state that disappears unexpectedly.

For UI scenarios, capture the current real entrypoint and representative viewport/state matrix. Required lifecycle evidence kinds are `structure_snapshot`, `visual_capture`, and `runtime_diagnostics`, each with `evidence_scope: integrated`. Treat blocking browser console errors, failed network calls, application exceptions, inaccessible interactions, and material visual drift as findings rather than residual notes.
