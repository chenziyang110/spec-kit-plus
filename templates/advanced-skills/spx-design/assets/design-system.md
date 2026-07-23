---
design_system:
  schema: spec-kit-design-v1
  name: "{{product_name}}-design-system"
  version: 1
  status: approved
  approval:
    status: approved
    direction: "{{approved_direction}}"
    source_refs: ["{{product_or_repository_source}}"]
    visual_refs: ["{{approved_visual_ref}}"]
  product_context:
    subject: "{{subject}}"
    audience: "{{audience}}"
    single_job: "{{single_job}}"
  direction_contract:
    visual_thesis: "{{visual_thesis}}"
    content_thesis: "{{content_thesis}}"
    interaction_thesis: "{{interaction_thesis}}"
    signature_element: "{{signature_element}}"
  platforms: ["{{approved_platforms}}"]
  tokens:
    color:
      surface.canvas: {value: "{{surface_canvas}}", usage: "{{surface_canvas_usage}}"}
      text.primary: {value: "{{text_primary}}", usage: primary readable text}
      accent.primary: {value: "{{accent_primary}}", usage: "{{accent_primary_usage}}"}
    spacing:
      compact: {value: "{{compact_spacing}}", usage: "{{compact_spacing_usage}}"}
      section: {value: "{{section_spacing}}", usage: "{{section_spacing_usage}}"}
    radius:
      control: {value: "{{control_radius}}", usage: "{{control_radius_usage}}"}
      surface: {value: "{{surface_radius}}", usage: "{{surface_radius_usage}}"}
    typography:
      body.family: {value: "{{body_font_family}}", usage: "{{body_font_usage}}"}
      body.size: {value: "{{body_font_size}}", usage: "{{body_size_usage}}"}
    motion:
      duration.fast: {value: "{{motion_duration_fast}}", usage: direct control feedback}
      duration.base: {value: "{{motion_duration_base}}", usage: state transitions}
      duration.slow: {value: "{{motion_duration_slow}}", usage: staged hierarchy reveal}
      easing.standard: {value: "{{motion_easing_standard}}", usage: continuous state change}
      easing.emphasized: {value: "{{motion_easing_emphasized}}", usage: entrance and confirmation}
  components: {}
  accessibility:
    contrast_intent: WCAG AA for ordinary text
    focus_visible: required
    keyboard_navigation: required
---

# {{product_name}} Design System

## Product Feel

State the subject, audience, single user job, and experience principles that
distinguish this product. Keep them observable and reusable.

## Design Direction

Record the visual, content, and interaction theses; the signature element; and
the exact approved `round-NN.html#direction-id` visual reference. Separate safe
system choices from deliberate creative risks and their costs.

## Visual And Interaction Signature

Name the product-specific choice users should recognize and how it appears in
hierarchy, density, typography, color, motion, or interaction. Avoid generic
style adjectives without implementable consequences.

## Platforms

List the actual platforms and their responsive, input, density, and evidence
requirements. Keep `design_system.platforms` above in sync.

## Component Rules

Define shared component anatomy, variants, composition, and required
default/hover/focus/disabled/loading/error/empty states. Add machine-readable
component entries above when a rule becomes canonical. Map meaningful entrance,
feedback, state-transition, loading, and reduced-motion behavior to the motion
tokens rather than adding untracked animation.

## Anti-Patterns

List visual or interaction choices this product must avoid.

## UI QA Checklist

- Tokens and existing components are reused.
- Responsive, keyboard, focus, contrast, loading, empty, and error states pass.
- Evidence covers structure, visual capture, runtime diagnostics, and comparison
  at real entry points.

## Reference Fidelity

Record source references, required fidelity, adopted decisions, and intentional
departures. Do not copy protected brand expression without authorization.

## Planned Gaps and Exceptions

Record only explicit, owned gaps with a revisit condition.

## Design Change Policy

Update this contract when product-wide tokens, components, interaction rules,
brand, density, accessibility, or platform expectations change.

All `{{...}}` placeholders must be replaced before ready lint and handoff.
