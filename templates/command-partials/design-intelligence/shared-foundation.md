## Design Intelligence Engine (three capabilities)

- **Taste Intelligence**: personality/DNA, dials, anti-slop, signature
- **Design System Reverse Engineering**: Evidence → UI System Model before
  implementation
- **Visual Validation**: real-entrypoint capture, comparison,
  pending-human-review

`sp-design` / `spx-design` is the studio that materializes one approved,
registered change-scoped truth; other stages **consume an exact pinned change**
through Design Intelligence hooks.

## Owners (do not invent parallel systems)

- Design DNA / theses / signature → exact registered change-local `DESIGN.md` + design brief
- Change dials → `design_brief.dials` variance · motion · density (1-10)
- Taste intake → `design_read`, aesthetic family, foundation strategy, redesign
  mode
- Anti-slop locks → `design_brief.anti_slop_locks` +
  `design-library/anti-slop-policy.md`
- UI System Model → `.specify/design/changes/<UD-ID>/DESIGN.md` + its
  change-local `design-contract.json`
- Evidence confidence →
  `templates/design-intelligence/schema/design-evidence.schema.json` +
  `validate_design_evidence`
- DesignContext schema →
  `templates/design-intelligence/schema/design-context.schema.json` (v1)
- Artifact lifecycle → `templates/design-intelligence/ARTIFACT-LIFECYCLE.md`
- Approval authority → `specify-runtime design approve` / export digests only
- Feature composition → `ui-brief.md` → plan `ui_design_contract` → task
  `ui_contract`
- Durable discussion carry → Design Carry-Forward + handoff `design_context`

## Interaction And Scenario Contract

UI truth includes behavior under input, data, and size—not only a static visual
state. Carry the same structured rows from the approved change through
`ui-brief.md`, `ui_design_contract`, every applicable task `ui_contract`, worker
packets, and Review evidence:

- `surface_catalog`: stable `DH-SURFACE-*` rows with `profile_id`, `name`,
  `kind`, the exact `entrypoint_id` from the consumer's official entrypoint
  inventory, source/specimen/component references, and exact `decision_ids`.
  Keep one identity and one real-entrypoint binding for each implemented
  surface across states and viewports.
- `scenario_matrix`: bounded `DH-SCENARIO-*` rows that name one
  `surface_id`, risk, required status, and the exact interaction, editing, data,
  accessibility, navigation, content, responsive, and motion row IDs exercised
  together. Each row also carries an exact `interaction_script`: non-empty
  `preconditions`, a `start_state_id` selected by `data_state_ids`, ordered
  `steps` (`input`, `action`, `expected_feedback`), and bounded `branches`.
  Branches use unique applicable `conditions` from success, failure, timeout,
  cancel, retry, duplicate, and out-of-order completion; each binds an
  `expected_state_id` from the same scenario, setup, feedback, focus behavior,
  announcement, and continuation. Also preserve non-empty `focus_checkpoint`, `announcement_checkpoint`,
  `completion_checkpoint`, and `recovery_checkpoint`. Every referenced row must
  appear in at least one scenario, and each
  scenario's `decision_ids` must equal the union of its referenced rows. Use
  risk-based or pairwise coverage; never generate an unbounded Cartesian
  product.
- `interaction_matrix`: exactly `id`, `surface`, `input`, `trigger`,
  `event_sequence`, `immediate_feedback`, `focus_behavior`, `repeat_behavior`,
  `cancellation_behavior`, `pending_behavior`, `decision_ids`. Cover applicable
  pointer/mouse, keyboard/focus, touch/stylus, shortcut, command, and system
  events. The row owns input mechanics: platform event ordering, feedback before
  completion, focus/selection/scroll continuity, repeat policy, cancellation,
  and allowed or blocked actions while pending. The scenario script owns journey
  outcome branches; do not replace these fields with one aggregate expectation.
  Add explicit rows for rapid/repeated activation, duplicate submission, drag
  cancellation, async completion order, timeouts, navigation/reload/close,
  session expiry, and external updates when they can lose work or duplicate
  effects.
- `editing_matrix`: `id`, `surface`, `input_methods`,
  `composition_behavior`, `paste_autofill_behavior`,
  `selection_caret_behavior`, `formatting_behavior`, `validation_timing`,
  `validation_feedback`, `dirty_state_behavior`, `persistence_behavior`,
  `undo_redo_behavior`, `conflict_behavior`, `read_only_disabled_behavior`,
  `submission_behavior`, and `decision_ids`. Each scenario selects these rows
  through exact `editing_ids`. Cover keyboard and platform input, IME
  composition without premature validation, paste/autofill normalization,
  selection/caret preservation, formatting boundaries, inline and announced
  validation, visible dirty state, draft/autosave/reload behavior, native or
  application undo/redo history, edit conflict resolution, readable/selectable
  read-only values, explained disabled controls, and submission under Enter,
  shortcuts, pending work, failure, retry, and duplicate activation.
- `data_state_matrix`: `id`, `surface`, `state`, `data_condition`,
  `expectation`, `decision_ids`. Every
  data-bearing surface covers empty/first-use and populated representative plus
  maximum-density data. Add loading, partial/stale/refreshing,
  validation/error, permission/read-only, offline/unavailable,
  optimistic/pending, and success states when applicable.
- `component_contracts`: retain exact `required_states`, `interaction_modes`,
  `data_scenarios`, `variants`, `content_constraints`, `semantic_token_refs`,
  `governance` (`reuse` | `extend` | `new`), exact nested component adoption
  action/package/version/license/source/permission, `iconography`, and decision
  bindings. Treat `semantic_token_refs` as semantic token references, not raw
  one-off values. Assign design-system gaps and deprecation; bind icon source,
  family, sizing, stroke/fill, optical alignment, meaning, and fallback. For
  Web UI, bind each row to the inspected live component or a shortlisted mature
  resource; `new` requires an explicit uncovered capability rather than an
  Agent inventing a base primitive.
- `responsive_matrix`: retain target/state, adaptation, `stretch_behavior`,
  `overflow_behavior`, and decision bindings. Verify continuous stretch,
  compression, and reflow between named sizes, including resize while focus,
  selection, scrolling, dragging, an overlay, or unsaved input is active.
  Stress long/localized content, text zoom or scaling, software keyboards, safe
  areas, high contrast, and reduced motion when applicable.

Use risk-based or pairwise combinations across input × data × size instead of
an unbounded Cartesian product. Cover every declared row and every high-risk
combination; a populated mouse happy path never substitutes for keyboard,
empty/error recovery, or resize evidence.

## Professional UI Contract

The owning design change stores these fields under
`design_change.verification`; the immutable handoff and every downstream
consumer preserve the exact applicable rows. A top-level accessibility summary
does not replace `accessibility_matrix`.

- `accessibility_matrix` rows use `id`, `surface`, `semantics`,
  `reading_order`, `focus_order`, `keyboard`, `announcements`, `target_size`,
  `contrast`, `zoom_reflow`, `alternatives`, and `decision_ids`. Target WCAG
  2.2 AA or the platform equivalent: Name/Role/Value and semantic structure;
  logical reading order and focus order; visible focus; a keyboard alternative
  and drag alternative; dynamic status announcement; applicable 24x24
  (24×24 CSS px)
  Web and 44pt native targets; 4.5:1 ordinary-text and 3:1 large-text/UI
  contrast; 400% reflow/zoom; forced colors/high contrast; and text or
  non-visual alternatives for images and icons.
- `navigation_matrix` rows use `id`, `surface`, `entry`, `destination`,
  `trigger`, `back_behavior`, `deep_link_behavior`,
  `interruption_recovery`, and `decision_ids`. They cover page/surface
  hierarchy, entry points, the primary task, back/close, deep link behavior,
  interruption recovery, consistent navigation, landmarks, and preservation
  of focus, task state, and unsaved work.
- `content_matrix` rows use `id`, `surface`, `state`, `purpose`, `copy`,
  `primary_action`, `trust_requirement`, `localization`, `content_limits`, and
  `decision_ids`. Cover CTA, empty/loading/error/permission, destructive
  action, confirmation, undo/recovery, privacy and trust copy; long text,
  wrapping/truncation, right-to-left (RTL)/bidirectional layout, localization
  expansion, and locale-aware date, number, currency, and time zone output.
- `motion_contract` uses `purpose`, `transitions`, `reduced_motion`, and
  `feedback_timing`. Each transition carries `id`, `surface`, `trigger`,
  `response`, `duration_ms`, `easing`, `interrupt_behavior`, and
  `decision_ids`; provide a reduced-motion alternative and explicit
  perceived-performance threshold values for immediate feedback, progress,
  and timeout.
- `usability_validation` uses `risk_level`, `methods`, `critical_tasks`,
  `success_criteria`, `human_review_required`, and the exact routed
  `smoothness_acceptance_ids` plus performance budgets. Passing integrated
  evidence binds the runtime-owned Smoothness Lab report ref/digest without a
  new evidence kind. Low-risk existing-pattern
  changes may use a documented cognitive walkthrough or heuristic review.
  Medium- and high-risk journeys name representative target users, critical
  task success criteria, and human review. Automated tests and screenshots
  cannot substitute for target-user usability validation.

Select risk-based or pairwise combinations across these contracts; never
expand them into an unbounded Cartesian product. Preserve all high-severity
failure, recovery, accessibility, trust, and usability obligations.

Do **not** create a parallel root `.design/` tree or mutable global design
authority. Use `.specify/design/changes/<UD-ID>/**`; a pre-existing root
`DESIGN.md` is read-only legacy baseline input only.

## DesignContext v1 (schema contract)

Durable design-context payloads **MUST** conform to DesignContext v1 when
serialized as structured JSON (discussion handoff fields, brief-adjacent
machine records, or runtime owners under `.specify/design/context/`):

- Schema: `templates/design-intelligence/schema/design-context.schema.json`
- Required: `version: "1.0"`, `intent.user_goal`
- Optional: `design_language` (tone + dials), `system`, `references`,
  `decisions`, `evidence` (objects validated by design-evidence schema)
- Validate via `specify_cli.design_intelligence.validate_design_context`
  (structure + evidence semantics; no taste scoring, no screenshot parsing)

Prompt-stage prose may remain human-readable; machine-readable carry-forward
must not invent a second parallel vocabulary.
