---
design_system:
  schema: spec-kit-design-v1
  name: workbench-precision
  version: 1
  platforms:
    - web
    - desktop
    - cli
  tokens:
    color:
      surface.canvas:
        value: "#ffffff"
        usage: primary workspace background
      surface.panel:
        value: "#f4f4f5"
        usage: dense panels, tables, grouped admin controls
      text.primary:
        value: "#18181b"
        usage: primary zinc interface text
      text.secondary:
        value: "#52525b"
        usage: labels, metadata, secondary copy
      text.inverse:
        value: "#ffffff"
        usage: text on high-emphasis actions
      border.subtle:
        value: "#d4d4d8"
        usage: table rules, form controls, panel boundaries
      accent.primary:
        value: "#2563eb"
        usage: primary actions and selected navigation
      accent.warning:
        value: "#d97706"
        usage: warnings and needs-attention states
      accent.success:
        value: "#16a34a"
        usage: success states and complete work
    spacing:
      scale.1:
        value: "4px"
        usage: icon gaps and dense inline spacing
      scale.2:
        value: "8px"
        usage: compact control padding
      scale.3:
        value: "12px"
        usage: table cell and form row spacing
      scale.4:
        value: "16px"
        usage: panel padding and section groups
    radius:
      control:
        value: "4px"
        usage: buttons, inputs, tabs
      panel:
        value: "6px"
        usage: cards, dialogs, grouped surfaces
    typography:
      body.family:
        value: "system-ui"
        usage: dense professional tool text
      body.size:
        value: "14px"
        usage: default UI copy
      heading.family:
        value: "system-ui"
        usage: concise page and panel headings
      heading.weight:
        value: "650"
        usage: compact hierarchy
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
        background: "{color.surface.canvas}"
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

# Workbench Precision

This is a Spec Kit Plus owned, second-created preset. It abstracts reusable product design principles and does not copy external brand expression.

Do not copy external brand expression.

## Product Feel

Use dense professional layouts for CRM, admin panels, and workbench-style tools where repeated scanning and precise action matter.

## Platforms

- Web: prioritize responsive data tables, stable toolbars, and keyboard-visible controls.
- Desktop: support wide, persistent work areas with compact controls and predictable state.
- CLI: use concise tables, clear status labels, and readable non-color fallbacks.

## Component Rules

- Buttons, inputs, and cards must expose all required states from the schema.
- Use 4px control radius and 6px panel radius consistently.
- Keep information density high without shrinking touch or click targets below platform norms.

## Anti-Patterns

- Do not turn operational screens into marketing layouts.
- Do not use oversized hero typography inside tool surfaces.
- Do not encode warning or success status by color alone.

## UI QA Checklist

- Dense layouts remain readable at narrow and wide widths.
- Selection, loading, warning, and empty states are visible.
- CLI output remains understandable without color.

## Design Change Policy

Update this preset through `sp-design` before using new product-wide tokens, density rules, or component states.
