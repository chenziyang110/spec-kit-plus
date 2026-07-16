---
design_system:
  schema: spec-kit-design-v1
  name: data-dense-ops
  version: 1
  platforms:
    - web
    - desktop
    - tui
  tokens:
    color:
      surface.canvas:
        value: "#f8fafc"
        usage: cool gray application background
      surface.panel:
        value: "#ffffff"
        usage: operational cards, charts, and tables
      text.primary:
        value: "#111827"
        usage: primary readable operations text
      text.secondary:
        value: "#475569"
        usage: metadata, axis labels, secondary copy
      text.inverse:
        value: "#ffffff"
        usage: text on strong status fills
      border.subtle:
        value: "#cbd5e1"
        usage: table dividers, panel boundaries, control outlines
      accent.primary:
        value: "#2563eb"
        usage: blue information and primary actions
      accent.incident:
        value: "#f97316"
        usage: incidents, degraded states, attention
      accent.success:
        value: "#16a34a"
        usage: healthy status and successful operations
    spacing:
      scale.1:
        value: "4px"
        usage: sparkline and inline label gaps
      scale.2:
        value: "8px"
        usage: compact table and control spacing
      scale.3:
        value: "12px"
        usage: chart legends and row spacing
      scale.4:
        value: "16px"
        usage: panels and dashboard groups
    radius:
      control:
        value: "4px"
        usage: buttons, filters, inputs
      panel:
        value: "6px"
        usage: metric cards, charts, and alert panels
    typography:
      body.family:
        value: "system-ui"
        usage: operational interface text
      body.size:
        value: "14px"
        usage: default dense copy
      heading.family:
        value: "system-ui"
        usage: dashboard and panel headings
      heading.weight:
        value: "650"
        usage: data hierarchy
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

# Data Dense Ops

This is a Spec Kit Plus owned, second-created preset. It abstracts reusable product design principles and does not copy external brand expression.

Do not copy external brand expression.

## Product Feel

Use information-dense operational layouts for observability, logistics, analytics, monitoring, and operations workflows that require quick comparison.

## Platforms

- Web: prioritize dashboard scanning, responsive tables, and stable chart regions.
- Desktop: support multi-panel monitoring and repeated triage actions.
- TUI: preserve status, severity, and selection without relying on color alone.

## Component Rules

- Buttons, inputs, and cards must expose all required states from the schema.
- Use 4px control radius and 6px panel radius consistently.
- Pair incident and healthy colors with labels, icons, or text.

## Anti-Patterns

- Do not use decorative charts without actionable labels.
- Do not make operational status depend on color alone.
- Do not allow changing data values to resize fixed dashboard controls.

## UI QA Checklist

- Tables, cards, and charts preserve alignment under loading and empty states.
- Incident, healthy, selected, and disabled states are visually distinct.
- TUI status output remains readable in narrow terminals.

## Design Change Policy

Update this preset through `sp-design` before changing operational density, status color semantics, or dashboard component rules.
