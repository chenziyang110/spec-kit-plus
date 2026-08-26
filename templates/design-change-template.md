---
design_change:
  schema: spec-kit-ui-design-change-v1
  id: __DESIGN_CHANGE_ID__
  title: __DESIGN_CHANGE_TITLE__
  name: __DESIGN_CHANGE_ID__
  version: 1
  status: draft
  change_type: __DESIGN_CHANGE_TYPE__
  scope:
    surfaces: __DESIGN_CHANGE_SCOPES__
    entrypoints: []
    states: []
    platforms: __DESIGN_CHANGE_PROFILES__
  baseline_refs: __DESIGN_CHANGE_BASELINE_REFS__
  relationships:
    iteration_of: __DESIGN_CHANGE_ITERATION_OF__
    supersedes: __DESIGN_CHANGE_SUPERSEDES__
    depends_on: []
    conflicts_with: []
  constraints:
    must_preserve: []
    may_adapt: []
    must_not: []
  approval:
    status: unapproved
    direction: null
    review_round: null
    source_refs: []
    visual_refs: []
    preview_sha256: null
    manifest_sha256: null
    visual_medium: null
    prompt_ref: null
    prompt_sha256: null
    inspection_owner: null
    handoff_ref: null
    handoff_sha256: null
    decision_ids: []
    handoff_contract_ids: []
    capability_profile_ids: []
    specimen_ids: []
  product_context:
    subject: null
    audience: null
    single_job: null
  professional_skill_route:
    catalog_version: spec-kit-ui-professional-v1
    status: unresolved
    domain_skill_id: null
    style_skill_id: null
    specialist_skill_ids: []
    matched_signals: {}
    loaded_refs: []
    unresolved_candidates: []
    mature_web_ui_resource_ids: []
    web_ui_asset_inventory:
      status: not-scanned
      manifest_refs: []
      lockfile_refs: []
      framework_ids: []
      installed_resources: []
      component_roots: []
      token_refs: []
      theme_refs: []
      surface_refs: []
    mature_web_ui_selection:
      status: not-applicable
      primary_resource_id: null
      supporting_resource_ids: []
      agent_resource_ids: []
      candidates: []
      confirmation_codes: []
      component_adoption_plan: []
      official_resource_refresh:
        status: not-run
        helper_ref: ui-professional-skills/refresh.py
        selected_resource_ids: []
        selected_agent_resource_ids: []
        network_policy: blocked_by_default
        install_or_upgrade: unauthorized
        items: []
    smoothness_acceptance_ids: []
    smoothness_performance_budgets: {}
  style_authority:
    mode: unresolved
    scope_level: null
    source_refs: []
    protected_surfaces: []
    allowed_style_delta_surfaces: []
    authorization_source: null
  direction_contract:
    visual_thesis: null
    content_thesis: null
    interaction_thesis: null
    signature_element: null
    safe_system_choices: []
    creative_risks: []
  platforms: __DESIGN_CHANGE_PROFILES__
  capability_profiles: __DESIGN_CHANGE_PROFILES__
  specimens: []
  tokens:
    color: {}
    spacing: {}
    radius: {}
    typography: {}
    motion: {}
    elevation: {}
    sizing: {}
    layout: {}
  color_modes: {}
  components: {}
  responsive:
    breakpoints: {}
    adaptations: []
  content:
    voice_rules: []
    real_content_sources: []
    imagery_rules: []
  decisions: []
  verification:
    source_continuity:
      schema: spec-kit-ui-source-continuity-v1
      applicability: not-assessed
      mode: none
      reason: null
      coverage:
        surface_ids: []
        interaction_ids: []
        component_ids: []
      authority_refs: []
      surface_bindings: []
      action_bindings: []
      asset_bindings: []
      unresolved_gaps: []
    required_viewports: []
    required_states: []
    surface_catalog: []
    scenario_matrix: []
    interaction_matrix: []
    editing_matrix: []
    data_state_matrix: []
    accessibility_matrix: []
    navigation_matrix: []
    content_matrix: []
    motion_contract: {}
    usability_validation: {}
    visual_tolerance: null
    accepted_deviations: []
  accessibility:
    contrast_intent: WCAG AA for ordinary text where platform rendering allows
    focus_visible: required
    keyboard_navigation: required
    reduced_motion: required
    touch_target: platform appropriate
    forced_colors: supported where the platform exposes it
---

# UI Design Change

This document is the draft contract for one bounded UI change. It does not
replace the project globally. Audit the live product and the baseline refs,
discuss one consequential decision at a time, iterate one professionally
authored concept in immutable review rounds, then explicitly approve that
direction before setting `status: approved`.

## Product Feel

Describe the intended feeling for this change and why it fits the affected
audience, job, surfaces, and existing product.

## Style Authority

Existing-product feature/page work defaults to `inherit-existing`: cite the
live UI/token/component sources, keep `global-shell` and `shared-components`
protected, and do not load a professional style skill. Only an explicitly
authorized full-page overhaul may use `page-overhaul-authorized`; its allowed
style delta must name the exact page surface and may not silently restyle the
product shell or shared components.

## Design Direction

Record the selected direction only after approval. Keep the unselected rounds
as immutable review history under this change workspace.

## Visual And Interaction Signature

Describe the recognizable element introduced or refined by this change and
map implementable statements to stable `DS-*` decision IDs.

## Foundations

Record only foundations used or changed by this scope. Inherited tokens and
components should be referenced through `baseline_refs`, not copied as a new
project-wide system.

## Platforms

Describe platform-specific behavior for the declared scope and capability
profiles. Do not promote surface-specific aesthetic rules into global policy.

## Component Rules

Record affected component anatomy, variants, states, and decision references.
Prefer live components unless the approved change explicitly replaces them.
For Web UI, use the routed mature-resource shortlist and one-primary-system
rule; add a headless or specialist library only for an exact uncovered
capability. Official Agent material is retrieval input, not install authority.
The final component choice must cite a scanned `web_ui_asset_inventory` and its
explainable `mature_web_ui_selection`; provisional candidates cannot authorize
dependency changes.
Copy the exact `component_adoption_plan` row into each affected component
contract. `add` stays `permission_status: not-authorized` until the user
confirms that exact dependency action. Persist the read-only official-resource
refresh hashes/drift codes; drift reopens selection but never authorizes change.
Call out the concrete mouse/pointer, keyboard/focus, touch, and command
interactions that must continue to work for each affected component.
Include empty, representative-data, dense-data, and failure expectations when
data shape changes the component's meaning or available actions.
Every exported `component_contracts` row also records `variants`,
`content_constraints`, `semantic_token_refs`, `governance`, nested `adoption`,
and `iconography`.
Governance chooses reuse, extension, or a justified new component; names the
owner of any design-system gap; and records replacement or deprecation rules.
Iconography names its approved source, visual family, sizing, stroke/fill
rules, optical alignment, semantic meaning, and text or non-visual fallback.

## Interaction And State Scenarios

When the change reconstructs or adapts an existing/reference-grounded UI,
freeze `verification.source_continuity` before these scenarios. It binds the
complete coverage surface, interaction, and component ID sets below to
inspectable source authority and requires exact binding-target equality,
business outcomes, final states, side effects, asset provenance, target
strategies, and source-target verification. A screenshot or HTML reference is
not behavioral evidence. Raw characters, emoji, or Unicode glyphs cannot stand
in for a required icon unless the approved contract explicitly records an
`approved-text-symbol` exception.

Keep these in `verification.interaction_matrix`, `verification.editing_matrix`,
and `verification.data_state_matrix`, not only in prose.

- Each `interaction_matrix` row names exactly `id`, `surface`, `input`,
  `trigger`, `event_sequence`, `immediate_feedback`, `focus_behavior`,
  `repeat_behavior`, `cancellation_behavior`, `pending_behavior`, and
  `decision_ids`. Cover pointer/mouse, keyboard/focus, touch, shortcuts, and
  command or system events when applicable. Define platform event ordering,
  feedback before completion, focus/selection/scroll continuity, single versus
  double/held/repeated activation, cancellation, and allowed or blocked actions
  while pending. Scenario scripts own journey outcomes; interaction rows own
  input mechanics and must not collapse back into one aggregate expectation.
- Add explicit rows for rapid/repeated activation, duplicate submission, drag
  cancellation, async completion order, timeouts, navigation/reload/close,
  session expiry, and external updates whenever they can lose work, duplicate
  effects, or leave feedback attached to stale state.
- Each `editing_matrix` row names `id`, `surface`, `input_methods`,
  `composition_behavior`, `paste_autofill_behavior`,
  `selection_caret_behavior`, `formatting_behavior`, `validation_timing`,
  `validation_feedback`, `dirty_state_behavior`, `persistence_behavior`,
  `undo_redo_behavior`, `conflict_behavior`, `read_only_disabled_behavior`,
  `submission_behavior`, and `decision_ids`; selected scenarios bind it with
  exact `editing_ids`. Cover IME composition without premature validation,
  paste/autofill, caret and selection preservation, formatting, inline and
  announced validation, visible dirty state, draft/autosave/reload, undo/redo,
  edit conflict resolution, read-only and disabled behavior, and duplicate
  submission while pending, retrying, or recovering.
- Each `data_state_matrix` row names `id`, `surface`, `state`,
  `data_condition`, `expectation`, and `decision_ids`. Every data-bearing
  surface covers empty/first-use and
  populated representative/maximum-density data; add loading, partial/stale,
  validation/error, permission/read-only, offline/unavailable, optimistic,
  pending, and success scenarios when applicable.
- Select risk-based combinations across input, data state, and size. Do not
  create a Cartesian-product checklist, but do cover interactions during
  loading/error recovery and resizing during active focus, selection, drag,
  scrolling, or unsaved input.
- Every selected `scenario_matrix` row carries an executable
  `interaction_script`: non-empty preconditions, a selected start state,
  ordered input/action/expected-feedback steps, and bounded branches. Cover
  applicable success, failure, timeout, cancel, retry, duplicate, and
  out-of-order outcomes; bind every expected state to the scenario's selected
  data states and preserve setup, feedback, focus, announcement, continuation,
  completion, and recovery. These are immutable scenario truth, not downstream test prose.

## Accessibility Contract

Keep normative, surface-specific requirements in
`verification.accessibility_matrix`. Rows carry `id`, `surface`, `semantics`,
`reading_order`, `focus_order`, `keyboard`, `announcements`, `target_size`,
`contrast`, `zoom_reflow`, `alternatives`, and `decision_ids`. The top-level
`accessibility` block is a summary and cannot replace the matrix. Target WCAG 2.2 AA or the platform
equivalent and cover Name/Role/Value, semantics, reading order, focus order,
visible focus, keyboard and drag alternatives, dynamic status announcement,
and image/icon alternatives. Record applicable 24x24 (24×24 CSS px) Web and
44pt native
target expectations, 4.5:1 ordinary-text and 3:1 large-text/UI contrast,
400% zoom/reflow, forced colors/high contrast, text scaling, and non-color
cues. Each row names the affected surface or component, requirement, expected
behavior, and verification route.

## Navigation Contract

Use `verification.navigation_matrix` rows with `id`, `surface`, `entry`,
`destination`, `trigger`, `back_behavior`, `deep_link_behavior`,
`interruption_recovery`, and `decision_ids` to record pages/surfaces,
hierarchy, entry points, the primary task, back/close behavior, deep links,
interruption recovery, cross-surface consistency, and orientation landmarks.
Preserve focus, task state, and unsaved work through refresh, relaunch,
authentication, permission changes, and external navigation when applicable.

## Content Contract

Use `verification.content_matrix` rows with `id`, `surface`, `state`, `purpose`,
`copy`, `primary_action`, `trust_requirement`, `localization`,
`content_limits`, and `decision_ids` for CTA, empty, loading, error, permission,
destructive action, confirmation, undo/recovery, privacy, and trust copy.
Specify long-text capacity, wrapping and truncation, right-to-left
(RTL)/bidirectional behavior,
localization expansion, terminology, and locale-aware date, number, currency,
and time zone presentation. Content must explain the next safe action without
depending on color, iconography, or an unspecified toast.

## Motion Rules

Define `verification.motion_contract` with `purpose`, `transitions`,
`reduced_motion`, and `feedback_timing`. Each transition carries `id`,
`surface`, `trigger`, `response`, `duration_ms`, `easing`,
`interrupt_behavior`, and `decision_ids`. Record spatial continuity,
interruption/cancel behavior, reduced-motion alternative, and
perceived-performance threshold for immediate feedback, waiting indicators,
and determinate progress. Unaffected motion remains inherited from the live
baseline; motion never blocks input or hides completion and error states.

## Responsive Behavior

Define the viewport, density, hierarchy, overflow, and input adaptations that
must be verified for this change, including what happens when the surface is
stretched, compressed, or reflowed around long content and dense data. Every
responsive contract records `stretch_behavior` and `overflow_behavior` and
states what happens to focus, selection, scroll position, open overlays, and
unsaved input while resizing—not only at named breakpoint screenshots.
Stress long/localized content, text zoom or scaling, software keyboards, safe
areas, high contrast, and reduced motion when the platform supports them.

## Content And Imagery

Name representative content, localization stress cases, data volume, and image
sources needed to judge this change honestly. Include empty, populated, partial,
error, permission-limited, offline, and recovery states whenever they matter to
the affected job.

## Usability Validation

Record `verification.usability_validation` with `risk_level`, `methods`,
`critical_tasks`, `success_criteria`, `human_review_required`, and applicable
`smoothness_acceptance_ids` plus performance budgets. Name target
users, reviewer/status, and evidence where the selected method requires it. A
passing integrated implementation must bind the runtime-owned Smoothness Lab
report ref and SHA-256 produced from the real entrypoint.
A low-risk existing-pattern change may use a documented cognitive walkthrough or
heuristic review. Medium- and high-risk journeys require representative target
users, task-based success criteria, and human review before acceptance.
Automated tests and screenshots verify implementation properties; they cannot
stand in for target-user usability or authorize an unreviewed high-risk flow.
Select risk-based or pairwise scenarios and avoid an unbounded Cartesian
product while preserving every high-severity failure and recovery path.

## Anti-Patterns

List contextual failures for the affected surfaces. Do not turn landing-page,
dashboard, mobile, CLI, or TUI guidance into universal bans.

## UI QA Checklist

- The implementation binds this exact change ID and approval digest.
- Required states and viewports have real-entrypoint evidence.
- Structure, visual output, runtime diagnostics, and visual comparison are distinct.
- Deviations are explicit and tied to affected `DS-*` and `DH-*` IDs.

## Reference Fidelity

Record each baseline/reference, its use intent, what must be preserved, what
may adapt, and what must not be copied.

## Planned Gaps and Exceptions

Record only explicit, owned gaps with affected decisions and revisit criteria.

## Design Change Policy

Before approval this workspace may be refined through new inspected rounds.
After approval, do not mutate this contract or its approval provenance. Create
a new design change and declare `supersedes`, `depends_on`, or `conflicts_with`
when later work intentionally changes this result.
