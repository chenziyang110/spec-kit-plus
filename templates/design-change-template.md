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
    required_viewports: []
    required_states: []
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
compare three directions, then approve one immutable direction before setting
`status: approved`.

## Product Feel

Describe the intended feeling for this change and why it fits the affected
audience, job, surfaces, and existing product.

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

## Motion Rules

Define purposeful motion and reduced-motion behavior that belongs to this
change. Unaffected motion remains inherited from the live baseline.

## Responsive Behavior

Define the viewport, density, hierarchy, overflow, and input adaptations that
must be verified for this change.

## Content And Imagery

Name representative content, localization stress cases, data volume, and image
sources needed to judge this change honestly.

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
