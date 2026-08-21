---
design_system:
  schema: spec-kit-design-v1
  name: commerce-tactile
  version: 1
  status: seed
  seed_warning: "Aesthetic seed only. Not approval truth. Never substitute for design approve or an approved DESIGN.md."
  platforms:
    - web
    - mobile
    - desktop
  taste:
    dials:
      variance: 6
      motion: 4
      density: 7
    aesthetic_family: commerce-tactile
    surface_types:
      - storefront
      - product-catalog
      - checkout
      - marketplace
    anti_slop_locks:
      - ban-extreme-neon-dark
      - ban-flat-unstyled-cta
      - ban-vague-product-hierarchy
  tokens:
    color:
      surface.canvas:
        value: "#fafafa"
        usage: neutral storefront base
      surface.panel:
        value: "#ffffff"
        usage: product cards and purchase surfaces
      text.primary:
        value: "#111827"
        usage: product and pricing text
      text.secondary:
        value: "#4b5563"
        usage: metadata, filters, and small labels
      text.inverse:
        value: "#ffffff"
        usage: button text and emphasis
      border.subtle:
        value: "#e2e8f0"
        usage: card boundaries and content groups
      accent.primary:
        value: "#f59e0b"
        usage: primary commerce actions
      accent.secondary:
        value: "#3b82f6"
        usage: secondary links and quick actions
      accent.success:
        value: "#16a34a"
        usage: stock-confirmation and order-success
      accent.warning:
        value: "#d97706"
        usage: out-of-stock and caution notices
      accent.danger:
        value: "#dc2626"
        usage: payment or compliance block
    spacing:
      scale.1:
        value: "4px"
        usage: dense listing metadata
      scale.2:
        value: "8px"
        usage: image metadata spacing
      scale.3:
        value: "12px"
        usage: cards and list rows
      scale.4:
        value: "18px"
        usage: product sections and option blocks
      scale.5:
        value: "24px"
        usage: checkout rhythm and callouts
    radius:
      control:
        value: "10px"
        usage: tactile CTA and filters
      panel:
        value: "12px"
        usage: cards and checkout panels
    typography:
      body.family:
        value: "system-ui, Arial, sans-serif"
        usage: fast-scannable commerce copy
      body.size:
        value: "14px"
        usage: product list baseline
      heading.family:
        value: "system-ui, Arial, sans-serif"
        usage: concise catalog headings
      heading.weight:
        value: "700"
        usage: visual priority for product and price
    motion:
      duration.fast:
        value: "120ms"
        usage: immediate control feedback
      duration.base:
        value: "220ms"
        usage: panel reveal and selection
      easing.standard:
        value: "cubic-bezier(0.2, 0, 0, 1)"
        usage: deliberate but controlled interaction
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
    contrast_intent: WCAG AA for text and interactive contrast in daylight and low-light contexts
    focus_visible: required
    keyboard_navigation: required
    reduced_motion: optional
---

# Commerce Tactile

**Not approval truth.** This seed is a reusable shopping/product UI direction and cannot replace approved product truth.

## Intended feel

- Product-first hierarchy with visible price, action, and trust cues
- Tactile, button-led controls tuned to shopping and checkout flows
- No dedicated dark-mode emphasis unless explicitly introduced in the approved change

## Platform notes

- Web: prioritize product scannability, clear price hierarchy, and stable filters.
- Mobile: larger touch actions for add-to-cart, quick variants, and checkout continuation.
- Desktop: retain card density while keeping clear CTA size and spacing.

## Anti-patterns

- Avoid full-screen dark themes by default; do not let dark mode become implicit baseline.
- Avoid vague “add to cart” patterns without explicit item and variant priority.
- Avoid purely icon-only controls for critical commerce decisions.

## Design Change Policy

Update this preset through `sp-design` before changing product-first hierarchy, checkout priority, dark-mode defaults, or CTA semantics.

