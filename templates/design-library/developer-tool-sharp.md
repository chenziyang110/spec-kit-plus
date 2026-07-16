---
design_system:
  schema: spec-kit-design-v1
  name: developer-tool-sharp
  version: 1
  platforms:
    - web
    - desktop
    - tui
    - cli
  tokens:
    color:
      surface.canvas:
        value: "#0f172a"
        usage: slate application background
      surface.panel:
        value: "#111827"
        usage: near-black inverse panels and consoles
      text.primary:
        value: "#e5e7eb"
        usage: primary interface text on dark surfaces
      text.secondary:
        value: "#94a3b8"
        usage: metadata, helper labels, inactive chrome
      text.inverse:
        value: "#020617"
        usage: text on bright action fills
      border.subtle:
        value: "#334155"
        usage: panel boundaries, editor gutters, input outlines
      accent.primary:
        value: "#22d3ee"
        usage: cyan actions, selected states, active affordances
      accent.danger:
        value: "#ef4444"
        usage: errors, destructive actions, failing jobs
      accent.success:
        value: "#22c55e"
        usage: passing checks and healthy status
    spacing:
      scale.1:
        value: "4px"
        usage: editor chrome and icon gaps
      scale.2:
        value: "8px"
        usage: compact controls and list rows
      scale.3:
        value: "12px"
        usage: panel padding and command rows
      scale.4:
        value: "16px"
        usage: section grouping
    radius:
      control:
        value: "3px"
        usage: buttons, inputs, segmented controls
      panel:
        value: "4px"
        usage: panels, command palettes, cards
    typography:
      body.family:
        value: "ui-sans-serif"
        usage: primary developer interface text
      body.size:
        value: "14px"
        usage: default UI text
      heading.family:
        value: "ui-sans-serif"
        usage: tool and panel headings
      heading.weight:
        value: "650"
        usage: sharp hierarchy without display scale
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

# Developer Tool Sharp

This is a Spec Kit Plus owned, second-created preset. It abstracts reusable product design principles and does not copy external brand expression.

Do not copy external brand expression.

## Product Feel

Use sharp, IDE-like surfaces for developer products, infrastructure consoles, and technical tools where state clarity and command speed matter.

## Platforms

- Web: keep navigation, logs, and editor-like panels stable across breakpoints.
- Desktop: support persistent panes, command surfaces, and keyboard-first workflows.
- TUI: preserve contrast and state semantics in constrained terminal widths.
- CLI: provide terse status output and clear failure details.

## Component Rules

- Buttons, inputs, and cards must expose all required states from the schema.
- Use 3px control radius and 4px panel radius consistently.
- Treat cyan as an action and focus accent, not as decoration.

## Anti-Patterns

- Do not blur critical logs or diagnostics behind atmospheric styling.
- Do not make terminal or code-like content depend on low-contrast color.
- Do not hide failure, disabled, or running states.

## UI QA Checklist

- Focus, selected, error, and loading states are distinguishable.
- Terminal-width output remains readable.
- Panels and gutters do not jump when content changes.

## Design Change Policy

Update this preset through `sp-design` before changing global contrast, console density, or core developer-tool component states.
