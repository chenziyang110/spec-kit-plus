---
design_system:
  schema: spec-kit-design-v1
  name: project-design-system
  version: 1
  platforms:
    - web
    - mobile
    - desktop
    - tui
    - cli
  tokens:
    color:
      surface.canvas:
        value: "#ffffff"
        usage: primary application background
      surface.panel:
        value: "#f8fafc"
        usage: raised panels, grouped controls, secondary surfaces
      surface.inverse:
        value: "#111827"
        usage: inverse headers, terminal panels, high-emphasis surfaces
      text.primary:
        value: "#111827"
        usage: primary readable text
      text.secondary:
        value: "#4b5563"
        usage: secondary text, helper copy, metadata
      text.inverse:
        value: "#ffffff"
        usage: text on inverse surfaces
      border.subtle:
        value: "#d1d5db"
        usage: controls, dividers, quiet card boundaries
      accent.primary:
        value: "#2563eb"
        usage: primary action, selected states, active navigation
      accent.danger:
        value: "#dc2626"
        usage: destructive actions and error states
      accent.success:
        value: "#16a34a"
        usage: success states and positive confirmations
    spacing:
      scale.1:
        value: "4px"
        usage: icon and label gaps
      scale.2:
        value: "8px"
        usage: compact control padding and tight stack gaps
      scale.3:
        value: "12px"
        usage: form row gaps and compact panel padding
      scale.4:
        value: "16px"
        usage: default section gap and card padding
      scale.6:
        value: "24px"
        usage: page sections and major groups
      scale.8:
        value: "32px"
        usage: screen-level spacing
    radius:
      control:
        value: "6px"
        usage: buttons, inputs, tabs, compact cards
      panel:
        value: "8px"
        usage: repeated cards, panels, dialogs
    typography:
      body.family:
        value: "system-ui"
        usage: default interface text
      body.size:
        value: "14px"
        usage: dense application copy
      heading.family:
        value: "system-ui"
        usage: page and section headings
      heading.weight:
        value: "650"
        usage: hierarchy without oversized type
    shadow:
      panel:
        value: "0 1px 2px rgba(15, 23, 42, 0.08)"
        usage: restrained elevation for overlays and active panels
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

# Project Design System

This file is the project design-system contract. Read it before creating or changing user-facing UI, including web, mobile, desktop, TUI, and CLI output.

## Product Feel

Use a clear, task-focused interface with restrained visual treatment. Prefer strong information hierarchy, consistent spacing, stable controls, and readable states over decorative styling.

## Platforms

- Web: responsive layouts, keyboard access, visible focus, stable control sizes, and screenshots for key viewports.
- Mobile: thumb-friendly controls, native-feeling density, readable empty and error states.
- Desktop: efficient layouts, command discoverability, and stateful controls that do not jump.
- TUI: readable narrow-width output, no-color mode, clear selected and error states.
- CLI: concise output, scan-friendly tables, predictable success and error messages, no reliance on color alone.

## Component Rules

- Buttons must have default, hover, focus, disabled, and loading states.
- Inputs must have default, hover, focus, disabled, and error states.
- Repeated cards may use `radius.panel`; controls should use `radius.control`.
- Prefer existing component patterns before adding variants.
- Do not invent styling outside the token set without updating this file.

## Anti-Patterns

- Do not ship generic gradient-heavy screens that ignore product context.
- Do not mix unrelated radius, spacing, shadow, or typography systems.
- Do not hide loading, empty, error, disabled, or permission states.
- Do not rely on color alone for status.
- Do not create UI evidence that proves behavior while ignoring visual layout.

## UI QA Checklist

- Tokens are used for colors, spacing, radius, typography, and elevation.
- Required component states are implemented or explicitly out of scope for the surface.
- Text fits inside controls and panels at mobile and desktop widths.
- Keyboard and focus behavior are visible where the platform supports them.
- Evidence captures the platform: screenshots for graphical UI, representative output for TUI/CLI.

## Design Change Policy

Update this file through `sp-design` when a change affects product-wide style, brand, density, component rules, token values, or platform-specific interface expectations.
