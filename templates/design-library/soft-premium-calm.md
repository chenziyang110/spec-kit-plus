---
design_system:
  schema: spec-kit-design-v1
  name: soft-premium-calm
  version: 1
  status: seed
  seed_warning: "Aesthetic seed only. Not approval truth. Never substitute for design approve or an approved DESIGN.md."
  platforms:
    - web
    - mobile
  taste:
    dials:
      variance: 6
      motion: 4
      density: 3
    aesthetic_family: soft-premium-calm
    surface_types:
      - landing
      - product-workspace
    anti_slop_locks:
      - ban-oversaturated-accents
      - ban-neon-outer-glow
      - ban-pure-black-canvas
  tokens:
    color:
      surface.canvas:
        value: "#f8fafc"
        usage: calm light canvas
      surface.panel:
        value: "#ffffff"
        usage: soft elevated panels
      text.primary:
        value: "#0f172a"
        usage: primary readable text
      text.secondary:
        value: "#64748b"
        usage: quiet helper text
      text.inverse:
        value: "#f8fafc"
        usage: text on deep accent fills
      border.subtle:
        value: "#e2e8f0"
        usage: soft separators
      accent.primary:
        value: "#4f46e5"
        usage: restrained indigo accent (desaturate further if brand needs)
      accent.success:
        value: "#0f766e"
        usage: calm success states
    spacing:
      scale.1:
        value: "8px"
        usage: control gaps
      scale.2:
        value: "16px"
        usage: card padding
      scale.3:
        value: "24px"
        usage: section grouping
      scale.4:
        value: "48px"
        usage: premium breathing room
    radius:
      control:
        value: "12px"
        usage: soft controls
      panel:
        value: "20px"
        usage: large calm panels
    typography:
      body.family:
        value: "ui-sans-serif"
        usage: calm product body
      body.size:
        value: "16px"
        usage: comfortable reading size
      heading.family:
        value: "ui-sans-serif"
        usage: soft display hierarchy
      heading.weight:
        value: "600"
        usage: quiet authority
    motion:
      duration.fast:
        value: "140ms"
        usage: subtle hover
      duration.base:
        value: "240ms"
        usage: spring-soft state change
      easing.standard:
        value: "cubic-bezier(0.22, 1, 0.36, 1)"
        usage: premium ease-out
---

# Soft Premium Calm (seed)

**Not approval truth.** Use only as a starting aesthetic family for calm consumer
or polished product UI. Final tokens and signature require an approved design
round.

## Suggested dials

- Variance: 6
- Motion: 4
- Density: 3

## Signature hints

- Large radius, low-contrast elevation, one desaturated accent
- Generous empty space treated as intentional structure
- Motion clarifies state rather than decorating every element
