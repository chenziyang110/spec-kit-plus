---
design_change:
  schema: spec-kit-ui-design-change-v1
  id: UD-0000
  title: "{{design_change_title}}"
  name: "{{design_change_name}}"
  version: 1
  status: draft
  change_type: extension
  scope:
    surfaces: ["web:replace-me"]
    entrypoints: []
    states: []
    platforms: [web]
  baseline_refs: []
  relationships:
    iteration_of: null
    supersedes: []
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
    smoothness_acceptance_ids: []
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
  platforms: [web]
  capability_profiles: [web]
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

This is content guidance for one bounded `UD-*` workspace. Replace the example
identity and scope, then refine the scaffolded change through leased artifact
patches. It is not a root design system and it never authorizes “latest”.

## Product Feel

State the intended feeling for the affected audience, job, surfaces, and live
baseline.

## Style Authority

Existing-product feature/page work defaults to `inherit-existing`: cite the
live UI/token/component sources, keep `global-shell` and `shared-components`
protected, and do not load a professional style skill. Only an explicitly
authorized full-page overhaul may use `page-overhaul-authorized`; its allowed
style delta must name the exact page surface and may not silently restyle the
product shell or shared components.

## Design Direction

Record only the inspected and approved direction. Keep rejected directions in
immutable review rounds inside the same change workspace.

## Visual And Interaction Signature

Name the recognizable choice introduced or refined by this change and bind its
implementable consequences to stable `DS-*` IDs.

## Foundations

Record only foundations used or changed by this scope. Reference inherited
tokens and components through `baseline_refs` instead of copying a project-wide
system.

## Platforms

Describe platform-specific behavior for the declared scope and capability
profiles.

## Component Rules

Define affected component anatomy, variants, states, decision references, and
the mouse/pointer, keyboard/focus, touch, or shortcut interactions that must
remain true. Include empty and representative-data expectations when data shape
changes behavior.
For Web UI, use the routed mature-resource shortlist and one-primary-system
rule. Prefer live reuse/extension; add a headless or specialist library only
for an exact gap, and never treat Agent material as install authority.
Final selection cites the scanned `web_ui_asset_inventory` and explainable
`mature_web_ui_selection`; provisional candidates cannot authorize dependency
changes.
Every exported `component_contracts` row also records `variants`,
`content_constraints`, `semantic_token_refs`, `governance`, and `iconography`.
Governance distinguishes reuse, extension, and justified new work; assigns
design-system gaps and deprecation. Iconography binds source, family, sizing,
stroke/fill, optical alignment, meaning, and a text or non-visual fallback.

## Interaction And State Scenarios

Store the contract in `verification.interaction_matrix`,
`verification.editing_matrix`, and `verification.data_state_matrix`, not only
in prose. Interaction rows carry exactly `id`, `surface`, `input`, `trigger`,
`event_sequence`, `immediate_feedback`, `focus_behavior`, `repeat_behavior`,
`cancellation_behavior`, `pending_behavior`, and `decision_ids` for
pointer/mouse, keyboard/focus, touch, shortcuts, command, or system events as
applicable. They define platform event ordering, pre-completion feedback,
focus/selection/scroll continuity, repeat policy, cancellation, and allowed or
blocked pending actions; scenario scripts own journey outcomes. Data rows carry `id`,
`surface`, `state`, `data_condition`, `expectation`, and `decision_ids`; every
data-bearing surface covers empty and
populated representative/maximum-density data plus applicable loading, partial,
validation/error, permission/read-only, offline/unavailable, optimistic,
pending, and success states. Use risk-based combinations across input, data,
and size, including interaction during recovery and resize while work is active.
Every selected `scenario_matrix` row carries an executable
`interaction_script`: non-empty preconditions, a selected start state, ordered
input/action/expected-feedback steps, and bounded branches. Cover applicable
success, failure, timeout, cancel, retry, duplicate, and out-of-order outcomes;
bind every expected state to the scenario's selected data states and preserve
setup, feedback, focus, announcement, continuation, completion, and recovery.
These are immutable scenario truth, not downstream test prose.
Add explicit rows for rapid/repeated activation, duplicate submission, drag
cancellation, async completion order, timeout, navigation/reload/close, session
expiry, and external updates whenever stale feedback, duplicate effects, or
lost work are possible.

Editing rows carry `id`, `surface`, `input_methods`, `composition_behavior`,
`paste_autofill_behavior`, `selection_caret_behavior`, `formatting_behavior`,
`validation_timing`, `validation_feedback`, `dirty_state_behavior`,
`persistence_behavior`, `undo_redo_behavior`, `conflict_behavior`,
`read_only_disabled_behavior`, `submission_behavior`, and `decision_ids`;
scenarios select them through exact `editing_ids`. Cover IME composition,
paste/autofill, caret and selection, formatting, validation feedback, dirty
state, drafts/autosave/reload, undo/redo, edit conflict resolution, read-only
and disabled controls, and pending/retry/duplicate submission.

## Accessibility Contract

Store surface-specific requirements in `verification.accessibility_matrix`.
Rows carry `id`, `surface`, `semantics`, `reading_order`, `focus_order`,
`keyboard`, `announcements`, `target_size`, `contrast`, `zoom_reflow`,
`alternatives`, and `decision_ids`; the top-level `accessibility` summary cannot
replace it. Target WCAG 2.2 AA or
the platform equivalent. Cover Name/Role/Value, semantics, reading and focus
order, visible focus, keyboard and drag alternatives, dynamic status
announcement, image/icon alternatives, applicable 24x24 (24×24 CSS px) Web and
44pt native targets, 4.5:1 and 3:1 contrast, 400% zoom/reflow, forced colors/high
contrast, text scaling, and non-color cues. Bind each expectation to a surface
or component and a verification route.

## Navigation Contract

Use `verification.navigation_matrix` rows with `id`, `surface`, `entry`,
`destination`, `trigger`, `back_behavior`, `deep_link_behavior`,
`interruption_recovery`, and `decision_ids` for page/surface hierarchy, entry
points,
primary task, back/close behavior, deep links, interruption recovery,
consistent navigation, and orientation landmarks. Preserve focus, task state,
and unsaved work through applicable refresh, relaunch, authentication,
permission, and external-navigation transitions.

## Content Contract

Use `verification.content_matrix` rows with `id`, `surface`, `state`, `purpose`,
`copy`, `primary_action`, `trust_requirement`, `localization`,
`content_limits`, and `decision_ids` for CTA, empty, loading, error, permission,
destructive action, confirmation, undo/recovery, privacy, and trust copy.
Constrain long text, wrapping/truncation, right-to-left (RTL)/bidirectional
layout,
localization expansion, terminology, and locale-aware date, number, currency,
and time zone presentation. Copy must name the next safe action without relying
only on color, iconography, or an unspecified toast.

## Motion Rules

Define `verification.motion_contract` with `purpose`, `transitions`,
`reduced_motion`, and `feedback_timing`. Each transition carries `id`,
`surface`, `trigger`, `response`, `duration_ms`, `easing`,
`interrupt_behavior`, and `decision_ids`; cover spatial continuity,
interruption/cancel behavior, reduced-motion alternative,
and perceived-performance threshold for immediate feedback, waiting, and
progress. Motion never blocks input or hides completion and error states.

## Responsive Behavior

Define viewport, density, hierarchy, overflow, and input adaptations that must
be verified, including stretch behavior, overflow recovery, and what changes
after resize or container compression. Every responsive row carries
`stretch_behavior` and `overflow_behavior` and preserves or explicitly changes
focus, selection, scroll position, overlays, and unsaved input during continuous
resize—not only at named breakpoint captures.
Stress long/localized content, text zoom or scaling, software keyboards, safe
areas, high contrast, and reduced motion when applicable.

## Content And Imagery

Name representative content, localization stress cases, data volume, image
sources, and missing-asset behavior. Include empty, partial, populated, error,
permission-limited, offline, and recovery states whenever they matter.

## Usability Validation

Record `verification.usability_validation`: `risk_level`, `methods`,
`critical_tasks`, `success_criteria`, `human_review_required`, and applicable
`smoothness_acceptance_ids`; name target
users and review evidence as needed. Low-risk existing-pattern changes may use
a documented cognitive walkthrough or
heuristic review. Medium- and high-risk journeys require representative target
users, task-based success criteria, and human review. Automated tests and
screenshots cannot substitute for target-user usability. Use risk-based or
pairwise coverage, not an unbounded Cartesian product, while retaining every
high-severity failure and recovery path.

## Anti-Patterns

List contextual failures for the affected surfaces, not universal aesthetic
bans.

## UI QA Checklist

- The implementation binds this exact change ID and registered SHA-256.
- Required states and viewports have real-entrypoint evidence.
- Structure, visual output, runtime diagnostics, and comparison remain distinct.
- Deviations point to affected `DS-*` and `DH-*` IDs.

## Reference Fidelity

Record each baseline/reference, its intent, what must be preserved, what may
adapt, and what must not be copied.

## Planned Gaps and Exceptions

Record only explicit, owned gaps with affected decisions and revisit criteria.

## Design Change Policy

After registration, this contract is immutable. Later work creates a new
`UD-*` change and declares `supersedes`, `depends_on`, or `conflicts_with`.
