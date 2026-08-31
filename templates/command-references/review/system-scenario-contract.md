Trigger: before starting or resuming an official entrypoint or required scenario.

Purpose: prove integrated, user-observable behavior rather than implementation-shaped proxies.

## Coverage Boundary

Before scenario execution, the Leader compiles the Review Universe from the handoff plus independent coverage discovery of authoritative requirements, design/architecture obligations, changed consumer surfaces, runtime controls and registrations, and affected shared paths. The handoff matrix is a minimum, never the complete universe by assertion. Reconcile each obligation and discovered surface to a required scenario or a specific evidence-backed out-of-scope disposition.

When Test Design is selected/required or bound upstream, first run
`specify-runtime test-design projection-verify --feature-dir <feature-dir>
--projection-ref <project-relative-ref> --expected-sha256 <sha256>`. Consume the
canonical typed pointer-only Review projection read-only as an oracle and
minimum coverage input. Never mutate or copy its publication, projection,
cases, data, coverage, gaps, or audit. Test Design is not PASS evidence and does
not prove the implementation passes; fresh integrated real-entrypoint proof is
still required. Missing or stale selected input routes back to the independent
Test Design producer.

Review always covers:

- installation/build/startup and the ready signal for each applicable official real entrypoint;
- every required user journey introduced or changed by this feature;
- directly affected shared surfaces and the regression paths needed to protect them.

Do not expand into an unbounded audit of unrelated legacy behavior. Do not narrow the active feature to only its easiest happy path.

The coverage gate is zero uncovered: no required obligation, official entrypoint, changed consumer surface, or applicable runtime-discovered control may remain unmapped or unexecuted. All packets joined is a separate gate. A worker cannot declare coverage complete; only the Leader may reconcile the universe after independent audit results have joined.

When prior screenshots/recordings, HTML/design exports, live source UI, source
code/resources/tests, a runnable source product, requirements, or business
rules govern reconstruction or migration, include the exact
`source_continuity` contract in the Review Universe. Reconcile every source
surface to one target binding with its confirmed `preserve`, `adapt`, `replace`,
`merge`, `split`, or `retire` disposition. Reconcile every action binding to its
exact `interaction_id`, `source_refs`, `user_promise`, `business_outcome`,
`side_effects`, `final_state`, and `verification`; exercise feedback and
recovery through the linked interaction/scenario rows. First require exact
equality between coverage surface/interaction/component ID sets, the selected
UI matrices, and binding targets; a missing ID is uncovered behavior, not a
sampling choice. Neither visual
resemblance nor a present handler is proof. Reconcile all `asset_bindings` by
exact `component_id`, `semantic_role`, `source_refs`, `target_strategy`,
`target_ref`, `provenance`, and `fallback`, and enforce
`placeholder_policy: forbid-character-substitution` so Unicode, emoji, ASCII,
or arbitrary glyphs cannot pass as replacement icons or images. Any applicable
`unresolved_gaps` entry, newly discovered hidden surface, unexplained retirement,
or source/target evidence conflict remains uncovered and blocks the affected
continuity claim.

## Scenario Requirements

Every mandatory scenario has a stable id, source acceptance refs, entrypoint, preconditions, safe test data, actions, observable expected results, required evidence, result, and exact resume point. Cover startup, reachability, interaction, state change/persistence, error or permission behavior, and cross-component integration when applicable.

For each source-continuity action, run a matched scenario through the source and
target official real entrypoints with equivalent safe data when the source is
runnable. Compare reachability, event order, immediate/pending feedback,
cancellation/retry/repeat behavior, side effects, `business_outcome`, and
`final_state`; report visual fidelity and behavioral continuity as separate
verdicts. If the source cannot run, use the strongest remaining inspectable
  authority, record attempted alternatives, and withhold runtime-parity claims.

For every task whose `source_continuity.applicability` is `required`, generate
the task-bound denominator with `specify-runtime evidence
source-continuity-manifest --feature-dir <feature-dir> --task-id <Txxx>`, inspect
the live inventory, and call `specify-runtime evidence
source-continuity-adapter-bridge --feature-dir <feature-dir> --task-id <Txxx>
--manifest <manifest-ref> --input-json '<live-tool-inventory>'`. It maps signals
through `source-continuity-adapter-catalog` and owns inventory, Probe, and Plan.
`source-continuity-adapter-probe` and then `source-continuity-adapter-plan` are
only progressively lower-level fallbacks. Compile
`source-continuity-adapter-execution` from the exact plan ref/SHA and execute
only its bounded packets, evidence requirements, permissions, and stop
conditions. Evidence records use provenance
`adapter:<adapter_id>` and observation rows name that adapter. Submit matched
source/target observations with `specify-runtime evidence
source-continuity-validate --feature-dir <feature-dir> --task-id <Txxx>
--manifest <manifest-ref> --adapter-plan <adapter-plan-ref>
--adapter-execution <adapter-execution-ref> --input-json
'<observed-result-json>'`. Review may claim behavioral continuity only when
`ui_verification` binds the returned exact coverage,
`source_continuity_adapter_plan_ref`/SHA-256 and
`source_continuity_adapter_execution_ref`/SHA-256 and
`source_continuity_lab_report_ref`/SHA-256. A newly discovered
unbound candidate, dead target action, side-effect/final-state mismatch, asset
fidelity failure, stale manifest, or character substitution blocks PASS.

The only non-executed terminal result is `waived` for a current,
hash-bound, human-confirmed `hardware_unavailable` exception. Its absent
hardware, attempted alternatives, withheld claims, and residual risk remain
explicit; it is never treated as PASS or used to waive a non-hardware failure.

Operate the software. A passing test suite, present component, compiled route, implemented handler, or registered-looking provider does not prove that a user can reach and use it. Exercise buttons, links, menus, forms, shortcuts, and commands, then trace their real route-handler-provider/factory-service-persistence/feedback chain when an observation fails or consumer wiring is at risk. Flag dead controls, unreachable pages, orphan implementations, unregistered consumers, swallowed errors, missing feedback, and state that disappears unexpectedly.

For UI scenarios, capture the current real entrypoint and representative viewport/state matrix. Required lifecycle evidence kinds are `structure_snapshot`, `visual_capture`, and `runtime_diagnostics`, each with `evidence_scope: integrated`. Treat blocking browser console errors, failed network calls, application exceptions, inaccessible interactions, and material visual drift as findings rather than residual notes.

Bound migration details are separate acceptance obligations: compare each
`component_states` behavior and every visual part (including disabled labels
and indicators), each `state_variants` source/target resource and dimensions,
and each `native_operation` API, permission declaration, and actual effect.
Return those exact nested details in surface/action/asset results. Missing
states, wrong sizes, character substitution, or a native operation with absent
permission evidence or unchanged declared `effect_fields` for a state-change
action blocks PASS. Reject metadata-only changes and state-denominator
shrinkage; read-only observation mode cannot waive promised side effects. Use the real
native window/system entrypoint; a browser preview or UI marker is insufficient.
