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

Define affected component anatomy, variants, states, and decision references.

## Motion Rules

Define purposeful motion and its reduced-motion equivalent for this change.

## Responsive Behavior

Define viewport, density, hierarchy, overflow, and input adaptations that must
be verified.

## Content And Imagery

Name representative content, localization stress cases, data volume, image
sources, and missing-asset behavior.

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
