---
design_system:
  schema: spec-kit-design-v1
  name: consumer-mobile-polished
  version: 1
  platforms:
    - mobile
    - web
  tokens:
    color:
      surface.canvas:
        value: "#fffaf5"
        usage: warm white app canvas
      surface.panel:
        value: "#ffffff"
        usage: sheets, cards, and grouped app surfaces
      text.primary:
        value: "#1f2937"
        usage: charcoal primary text
      text.secondary:
        value: "#667085"
        usage: helper text and secondary labels
      text.inverse:
        value: "#ffffff"
        usage: text on primary actions
      border.subtle:
        value: "#e5e7eb"
        usage: soft dividers and input outlines
      accent.primary:
        value: "#f04438"
        usage: coral primary actions and active states
      accent.success:
        value: "#0f766e"
        usage: teal success and positive confirmations
      accent.warning:
        value: "#f59e0b"
        usage: warning and attention states
    spacing:
      scale.1:
        value: "4px"
        usage: icon and label gaps
      scale.2:
        value: "8px"
        usage: compact inline spacing
      scale.3:
        value: "12px"
        usage: control padding and list rows
      scale.4:
        value: "16px"
        usage: card padding and section groups
      scale.6:
        value: "24px"
        usage: mobile screen rhythm
    radius:
      control:
        value: "10px"
        usage: buttons, inputs, pills
      panel:
        value: "12px"
        usage: mobile cards, sheets, panels
    typography:
      body.family:
        value: "system-ui"
        usage: native-feeling app text
      body.size:
        value: "15px"
        usage: default mobile copy
      heading.family:
        value: "system-ui"
        usage: screen and section headings
      heading.weight:
        value: "700"
        usage: polished app hierarchy
  components:
    button:
      required_states:
        - default
        - hover
        - focus
        - disabled
        - loading
      token_refs:
        background: "{color.accent.primary}"
        text: "{color.text.inverse}"
        radius: "{radius.control}"
    input:
      required_states:
        - default
        - hover
        - focus
        - disabled
        - error
      token_refs:
        background: "{color.surface.panel}"
        text: "{color.text.primary}"
        border: "{color.border.subtle}"
        radius: "{radius.control}"
    card:
      required_states:
        - default
        - hover
        - selected
        - loading
        - empty
      token_refs:
        background: "{color.surface.panel}"
        border: "{color.border.subtle}"
        radius: "{radius.panel}"
  accessibility:
    contrast_intent: WCAG AA for ordinary text where platform rendering allows
    focus_visible: required
    keyboard_navigation: required
---

# Consumer Mobile Polished

This is a Spec Kit Plus owned, second-created preset. It abstracts reusable product design principles and does not copy external brand expression.

Do not copy external brand expression.

## Product Feel

Use polished consumer mobile patterns and cross-platform app shells with warm surfaces, clear calls to action, and native-feeling spacing.

## Platforms

- Mobile: prioritize thumb-friendly controls, stable safe-area layouts, readable empty states, and polished transitions.
- Web: preserve the same app-shell hierarchy at responsive widths without becoming a marketing page.

## Component Rules

- Buttons, inputs, and cards must expose all required states from the schema.
- Use 10px control radius and 12px panel radius consistently.
- Keep coral for primary action emphasis and teal for success confirmation.

## Anti-Patterns

- Do not make app screens feel like generic landing pages.
- Do not use tiny controls or dense desktop tables on mobile.
- Do not rely on color alone for success, warning, or error states.

## UI QA Checklist

- Controls are readable and reachable on mobile widths.
- Loading, empty, disabled, and error states are polished and explicit.
- Web layouts preserve app-shell structure without overlapping text.

## Design Change Policy

Update this preset through `sp-design` before changing mobile density, action color semantics, radius, or core app-shell component rules.
