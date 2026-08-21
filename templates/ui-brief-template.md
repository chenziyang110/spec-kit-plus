# UI Brief

This is a feature adoption binding, not a copy of the design system. Keep only
the selected design-change identity, feature-relevant rows, and feature delta.

## Source Design Change

- Design change ID: UD-____
- Registered design ref: .specify/design/changes/<UD-ID>/DESIGN.md
- Machine contract ref: .specify/design/changes/<UD-ID>/design-contract.json
- Registered design-change SHA-256:
- Design readiness: approved | narrow-existing-pattern-exception | blocked
- Approved visual ref: .specify/design/changes/<UD-ID>/previews/round-NN.<html|png|jpg|jpeg|webp>#direction-id
- Approved direction ID and review round:
- Preview / manifest / handoff SHA-256:
- Immutable handoff ref:
- Selected design decision IDs: []
- Selected handoff contract IDs and exact rows: []

## Feature Adoption

- UI work type: existing-pattern | feature-extension | reference-implementation
- Surface type: landing | product-workspace | hybrid | existing-pattern-maintenance
- Platforms and capability profiles:
- Applicable specimen IDs:
- Real entry points:
- Required states and viewports:
- Subject / audience / single user job:
- Design DNA / personality inherited by this feature:
- Dials (variance / motion / density) and inference reason when relevant:
- Anti-slop locks selected for this surface:
- `style_authority`:
  - mode: greenfield | inherit-existing | page-overhaul-authorized
  - scope_level: feature-partial | page
  - source_refs: []
  - protected_surfaces: [global-shell, shared-components]
  - allowed_style_delta_surfaces: []
  - authorization_source: null

For existing-product feature or partial-page work, preserve
`inherit-existing` exactly; the feature delta cannot override it. Only an
explicitly authorized exact complete-page overhaul may name a bounded allowed
style delta.

## Feature Delta

Record only what this feature narrows, extends, or overrides. Empty means exact
adoption; it does not authorize reinterpretation.

- Layout and information hierarchy:
- Tokens and components:
- Component anatomy and required states:
- Component governance:
  Preserve selected `component_contracts` rows including `variants`,
  `content_constraints`, `semantic_token_refs`, `governance` (`reuse` |
  `extend` | `new`), exact nested `adoption` action/package/version/license/
  source/permission fields, and `iconography` source/style/optical rules.
- Surface and scenario graph:
  Select exact `surface_catalog` rows for the feature surfaces, including each
  row's immutable `entrypoint_id`, and exact
  `scenario_matrix` rows for bounded risk-based or pairwise coverage. Each
  scenario references one stable surface plus every interaction, editing, data,
  accessibility, navigation, content, responsive, and motion row it exercises;
  it also preserves the exact `interaction_script` with preconditions, a start
  state selected by `data_state_ids`, ordered input/action/expected-feedback
  steps, and bounded branches. Bind every branch `expected_state_id` to the
  same scenario and keep setup, feedback, focus, announcement, continuation,
  scenario-level completion, and recovery explicit. Do not expand these into an unbounded
  Cartesian product.
- Interaction and feedback timing:
  Include `interaction_matrix` rows for mouse/pointer, keyboard, focus, touch,
  shortcuts, and async feedback that must survive implementation. Each row uses
  exact `id`, `surface`, `input`, `trigger`, `event_sequence`,
  `immediate_feedback`, `focus_behavior`, `repeat_behavior`,
  `cancellation_behavior`, `pending_behavior`, and `decision_ids`; keep input
  mechanics here and journey outcome branches in the scenario script.
- Editing lifecycle:
  Include exact `editing_matrix` rows and scenario `editing_ids` for applicable
  input methods, IME `composition_behavior`, `paste_autofill_behavior`,
  `selection_caret_behavior`, `formatting_behavior`, `validation_timing`,
  `validation_feedback`, `dirty_state_behavior`, `persistence_behavior`,
  `undo_redo_behavior`, `conflict_behavior`, `read_only_disabled_behavior`, and
  `submission_behavior`. Preserve values and focus through retry, resize,
  reauthentication, conflict resolution, and duplicate submission.
- Responsive adaptation:
  Include `responsive_matrix` rows for resize/stretch boundaries, overflow
  handling, and min/max density shifts.
- Motion and reduced-motion behavior:
  Select the exact `motion_contract`, including trigger/response,
  `duration_ms`, easing, interruption, reduced motion, and
  immediate/progress/timeout feedback timing.
- Accessibility and keyboard requirements:
  Select `accessibility_matrix` rows for WCAG 2.2 AA/platform-equivalent
  semantics, reading/focus order, keyboard/drag alternatives, announcements,
  targets, contrast, zoom/reflow, forced colors, and alternatives.
- Navigation and recovery:
  Select `navigation_matrix` rows for hierarchy, entry/destination, primary
  task, back/close, deep-link behavior, interruption recovery, consistency,
  and landmarks.
- Interface content:
  Select `content_matrix` rows for CTA, empty/loading/error/permission,
  destructive/confirmation/undo, privacy/trust, localization, RTL, truncation,
  dates, numbers, and time zones.
- Usability validation:
  Bind `usability_validation` risk, methods, critical tasks, success criteria,
  whether human review is required, and the exact routed
  `smoothness_acceptance_ids` and performance budgets for Web UI. Passing
  acceptance binds the CLI-owned Smoothness Lab report ref and SHA-256.
- Real content and imagery plan:
- Data scenarios:
  Include `data_state_matrix` rows for empty, populated, partial, loading,
  error, unavailable, and permission-limited states as applicable.
- Must preserve:
- May adapt:
- Must not:

## Reference And Fidelity

- UI reference notes: ui-reference-notes.md | none
- Visual target: ui-target.html | none
- Original inspectable assets:
- Reference intents: [{ref, intent: exact | preserve-structure | inspiration | extract-tokens | do-not-copy}]
- Fidelity mode: approximate | high | inspiration
- Fidelity criteria and human review condition:
- Ownership and forbidden copying:

## Required Evidence

- Required kinds: `structure_snapshot`, `visual_capture`,
  `runtime_diagnostics`, `visual_comparison_or_human_review`
- Surface catalog:
  Copy exact `surface_catalog` rows for the feature; do not rename a surface
  between states, viewports, tasks, or captures.
- Scenario matrix:
  Copy exact `scenario_matrix` rows and every referenced contract row. Keep the
  approved risk/required values, `interaction_script`, and decision union; do
  not recompose scenarios downstream. Evidence must execute the ordered steps
  plus applicable success/failure/timeout/cancel/retry/duplicate/out-of-order
  branches and observe every focus, announcement, completion, and recovery
  checkpoint.
- Interaction matrix:
  `[id | surface | input | trigger | expectation | decision_ids]` rows for
  mouse/pointer, keyboard, focus, touch, wheel, drag, shortcuts, or
  programmatic transitions that matter.
- Data/state matrix:
  `[id | surface | state | data_condition | expectation | decision_ids]` rows
  for no data, representative data, edge density, partial data, and failure or
  unavailable states.
- Accessibility matrix:
  Copy exact `accessibility_matrix` rows and decision bindings.
- Navigation matrix:
  Copy exact `navigation_matrix` rows and decision bindings.
- Content matrix:
  Copy exact `content_matrix` rows and decision bindings.
- Motion contract:
  Copy the exact `motion_contract`; do not reduce it to “add animation”.
- Usability validation:
  Copy `usability_validation`; medium/high-risk work remains pending until its
  required human review is complete. Automated tests and screenshots cannot
  substitute for target-user validation. Preserve smoothness IDs and prove them
  with the existing UI evidence kinds.
- Component contracts:
  Exact selected rows should retain `required_states`, `interaction_modes`,
  `data_scenarios`, `variants`, `content_constraints`, `semantic_token_refs`,
  `governance`, `iconography`, and decision bindings for each component.
- Responsive matrix:
  Exact selected rows should retain `state`, `adaptation`,
  `stretch_behavior`, `overflow_behavior`, and decision bindings for each
  viewport or immutable target.
- Visual acceptance matrix: [entry point | viewport | state | expected result | evidence path]
- Decision coverage: [DS/DH ID | task IDs | viewport/state | comparison evidence]
- Comparison report: [design ref + contract/preview/manifest/handoff SHA | implementation capture | difference | tolerance | deviation]
- Comparison tolerance: copy the selected immutable structured object; prose is invalid
- Accepted deviations and approver:
- Pending human review condition:

## Worker Contract

- Required design sources: exact change ref, machine contract, visual ref,
  handoff ref, this brief, and original references
- Required packet fields: `design_change_id`, `design_change_ref`,
  `design_change_sha256`, `design_contract_ref`, selected `DS-*`/`DH-*` rows,
  `surface_catalog`, `scenario_matrix`, `interaction_matrix`, `editing_matrix`,
  `data_state_matrix`, `accessibility_matrix`, `navigation_matrix`,
  `content_matrix`, `motion_contract`, `usability_validation`,
  component/responsive contracts,
  entry points, states, Must Preserve / May Adapt / Must Not, evidence
- Coverage rule: choose risk-based or pairwise combinations; do not create or
  silently demand an unbounded Cartesian product.
- Convergence loop: run real entry point -> capture -> query the exact pinned
  change and this brief -> compare -> repair -> recapture
- Done condition: behavior checks and visual/interaction acceptance both pass
- Stop condition: source/digest drift, missing state evidence, unresolved
  overlap, or a requested design change outside the pinned contract
