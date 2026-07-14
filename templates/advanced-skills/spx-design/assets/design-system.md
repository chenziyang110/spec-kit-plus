---
design_system:
  schema: spec-kit-design-v1
  name: "{{product_name}}-design-system"
  version: 1
  platforms: [web]
  tokens:
    color:
      surface.canvas: {value: "#ffffff", usage: primary application background}
      text.primary: {value: "#111827", usage: primary readable text}
      accent.primary: {value: "#2563eb", usage: primary action and focus}
    spacing:
      scale.2: {value: "8px", usage: compact gaps}
      scale.4: {value: "16px", usage: default section and control spacing}
    radius:
      control: {value: "6px", usage: interactive controls}
      panel: {value: "8px", usage: cards and panels}
    typography:
      body.family: {value: "system-ui", usage: default interface text}
      body.size: {value: "14px", usage: ordinary interface copy}
  components: {}
  accessibility:
    contrast_intent: WCAG AA for ordinary text
    focus_visible: required
    keyboard_navigation: required
---

# {{product_name}} Design System

## Product Feel

State the product experience principles and anti-patterns that distinguish this
interface. Keep them observable and reusable.

## Platforms

List the actual platforms and their responsive, input, density, and evidence
requirements. Keep `design_system.platforms` above in sync.

## Component Rules

Define shared component anatomy, variants, composition, and required
default/hover/focus/disabled/loading/error/empty states. Add machine-readable
component entries above when a rule becomes canonical.

## Anti-Patterns

List visual or interaction choices this product must avoid.

## UI QA Checklist

- Tokens and existing components are reused.
- Responsive, keyboard, focus, contrast, loading, empty, and error states pass.
- Evidence uses real entry points and representative viewports or output.

## Reference Fidelity

Record source references, required fidelity, adopted decisions, and intentional
departures. Do not copy protected brand expression without authorization.

## Planned Gaps and Exceptions

Record only explicit, owned gaps with a revisit condition.

## Design Change Policy

Update this contract when product-wide tokens, components, interaction rules,
brand, density, accessibility, or platform expectations change.
