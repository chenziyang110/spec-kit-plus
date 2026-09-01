# Planning contract

Plan from the specification contract and current repository. Preserve confirmed
scope; delivery phases do not silently defer requirements.

Record only decisions that constrain implementation:

- affected owners, consumers, files, and generated or mirrored surfaces;
- interfaces, data/state transitions, error and recovery behavior;
- compatibility, migration, security, rollout, and rollback when triggered;
- verification at real entry points and important boundaries;
- alternatives, assumptions, and risks that materially affect the design.

Record `test_design_gate.decision` as exactly `not_selected`, `selected`, or
`required`. A selected/required gate carries either an all-null pending binding
or the full runtime-produced `projection_binding`; partial binding is invalid.
When Plan consumes it, verify with `specify-runtime test-design
projection-verify --feature-dir <feature-dir> --projection-ref
<project-relative-ref> --expected-sha256 <sha256>` before reading the typed
pointer-only selection; omit `--feature-dir` for project scope. Plan consumes
that canonical projection read-only and must not mutate or copy its publication,
cases, data, coverage, gaps, or audit. Missing input needed by Plan routes to the
independent `$spx-test-design` producer; otherwise all-null pending selection
may route there afterward. It does not require a completed Plan. `not_selected`
has no invented binding. This binding proves only Plan consumption, never Tasks
authorization; Tasks requires a fresh feature handoff, its own projection, and
runtime task-index binding. Avoid a Plan-contract basis/hash cycle.

When UI applies, preserve the feature `ui-brief.md` adoption binding rather
than reinterpreting it. For a late design overlay, first verify the current
`formal-post-specify` overlay with `specify-runtime design adoption` against the
exact unchanged source spec ref and SHA-256. This is the
specify -> design -> plan route; it does not rerun Specify. A missing/mismatched
receipt blocks Plan, while a real requirements change returns to Specify. Query its exact
`.specify/design/changes/<UD-ID>/design-contract.json` and matching `design-change.md`
through targeted `specify-runtime artifact show` calls; use the former as the
machine-readable source of truth and the latter only as the corresponding
human-readable projection for review and explanation. Never resolve “latest”
from the index. Explicitly set `ui_applicable: true`,
record `design_adoption_binding` with the exact current receipt mode, consumer,
scope, revision/change ID, project-relative source-Spec ref/SHA, and impact SHA,
and revalidate it against the runtime index and current source bytes. A model's
own `verified` claim is not evidence. For a pending source `design_gate`,
preserve Spec-owned requirement fields exactly while allowing only verified
Design-owned identity and matrices to come from the registered overlay.
preserve `ui_brief_ref`, and record `design_readiness: approved` or a bounded
`narrow-existing-pattern-exception`. Map its work/surface/platform types,
subject/audience/job, three theses, signature, exact `style_authority`, approved visual ref, reference
intents, real content/image plans, preview/manifest/handoff SHA-256 values,
immutable handoff ref, approved `DS-*` decision IDs, selected `DH-*` handoff
contract IDs, entry points, approved design tokens/components, color modes,
component anatomy/state contracts, exact `interaction_matrix`, `editing_matrix`,
and `data_state_matrix` rows, component `interaction_modes` / `data_scenarios`,
responsive/motion contracts including `stretch_behavior` and
`overflow_behavior`, required states, responsive/accessibility rules, fidelity constraints, and
must-preserve/may-adapt/must-not decisions into
`plan-contract.json#/ui_design_contract`. The verification plan names the
representative risk-based input × data × size matrix, including pointer/mouse,
keyboard/focus, applicable touch/shortcut/command paths, empty and populated
data, degraded/recovery states, and continuous resize while interaction context
is active; screenshot or platform capture routes,
the structure/visual/runtime evidence triad, visual comparison, comparison
tolerance, accepted deviations, decision coverage, and accepted
deviation or pending-human-review boundary. Carry verified cognition routes for
entry points, owners, reusable patterns, and visual tests in the context capsule.
Preserve selected handoff rows by ID; planning may choose a feature-relevant
subset but must not paraphrase or weaken an approved row.

Trace every requirement and must-preserve obligation to a design decision or an
explicit unresolved blocker. Use precise paths when reasonably knowable, but do
not turn the plan into task-level edit instructions. A planning-ready result has
no hidden feasibility question capable of changing the chosen architecture.

Treat `acceptance_refs` as the complete fail-closed denominator. For a ready
version-2 plan it is the unique ordered list
`spec-contract.json#/acceptance_criteria/0..N-1` covering every specification
acceptance criterion exactly once; it is never a selected subset or prose
reconstruction.

When the specification `entrypoint_outcome_contract` is triggered, reuse its
`CA-###` refs rather than copying the inventory. For each active outcome, add an
`operational_consequence_decisions` entry with `producer_result_ref`,
`consumer_owner`, state transition, interaction owner/policy,
`request_retention`, `retry_identity`, cancel behavior, and validation refs.
Recoverable user-input decisions also carry security constraints and distinguish
prohibited unrelated shell UI from interaction required to continue. Missing
outcome CA design blocks planning completion.

When deep research exists, preserve its planning handoff rather than
reconstructing feasibility. Consume each `PH-###` in a level-2 `## Deep Research
Traceability Matrix` with the runtime-required columns: `Plan Decision`,
`Handoff ID`, `Evidence / Spike ID`, `Evidence Quality`, and `Plan Action`.
Mandatory items must be consumed; optional deferral and user-decision items stay
explicit.

The runtime-published structured research package is canonical. Its handoff,
accepted evidence IDs, claim status, source hash or digest, and revision-bound
publish state are the source of truth; `deep-research.md` is the derived
human-readable projection. Before Plan consumes deep research, verify the
selected handoff with `specify-runtime deep-research verify-handoff`, then use
a fresh `specify-runtime artifact patch` lease for
`plan-contract.json#/deep_research_binding`. Preserve exactly:

- `decision`;
- `handoff_ref` and `handoff_sha256`;
- `source_spec_sha256`;
- `state_revision`;
- verified `claim_status`;
- `handoff_ids`.

Bind a validated `**Status**: Not needed` result to its runtime-verified
handoff with an empty `handoff_ids` array. Any stale,
tampered, foreign, partial, or claim-mismatched research handoff blocks
planning until the owning deep-research workflow republishes and verifies it.

## Professional UI contract continuity

For UI-bearing scope, `ui_design_contract` selects the exact immutable
`source_continuity`, `surface_catalog`, `scenario_matrix`, `interaction_matrix`,
`editing_matrix`, `data_state_matrix`, `accessibility_matrix`, `navigation_matrix`,
`content_matrix`, `motion_contract`, and `usability_validation` values,
including exact component adoption rows, `smoothness_acceptance_ids`, and performance budgets, and
assigns implementation/verification routes.
Retain component governance and iconography. Plan risk-based or pairwise
combinations without an unbounded Cartesian product.
