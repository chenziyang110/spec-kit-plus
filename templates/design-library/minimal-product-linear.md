---
design_system:
  schema: spec-kit-design-v1
  name: minimal-product-linear
  version: 1
  status: seed
  seed_warning: "Aesthetic seed only. Not approval truth. Never substitute for design approve or an approved DESIGN.md."
  platforms:
    - web
    - desktop
    - mobile
  taste:
    dials:
      variance: 5
      motion: 3
      density: 5
    aesthetic_family: minimal-product-linear
    surface_types:
      - product-workspace
    anti_slop_locks:
      - ban-marketing-hero-theatrics
      - ban-multi-accent-rainbow
      - ban-decorative-section-numbers
  tokens:
    color:
      surface.canvas:
        value: "#ffffff"
        usage: clean product canvas
      surface.panel:
        value: "#f4f4f5"
        usage: subtle nested surfaces
      text.primary:
        value: "#18181b"
        usage: primary UI text
      text.secondary:
        value: "#71717a"
        usage: metadata and quiet labels
      text.inverse:
        value: "#fafafa"
        usage: inverse on solid actions
      border.subtle:
        value: "#e4e4e7"
        usage: hairline structure
      accent.primary:
        value: "#2563eb"
        usage: single product accent
      accent.danger:
        value: "#dc2626"
        usage: destructive actions
    spacing:
      scale.1:
        value: "4px"
        usage: tight control gaps
      scale.2:
        value: "8px"
        usage: compact rows
      scale.3:
        value: "16px"
        usage: panel padding
      scale.4:
        value: "24px"
        usage: section grouping
    radius:
      control:
        value: "6px"
        usage: restrained controls
      panel:
        value: "8px"
        usage: quiet panels
    typography:
      body.family:
        value: "ui-sans-serif"
        usage: neutral product body
      body.size:
        value: "14px"
        usage: product density default
      heading.family:
        value: "ui-sans-serif"
        usage: restrained headings
      heading.weight:
        value: "600"
        usage: clear hierarchy without display theatrics
    motion:
      duration.fast:
        value: "100ms"
        usage: micro feedback
      duration.base:
        value: "180ms"
        usage: panel and state transitions
      easing.standard:
        value: "cubic-bezier(0.2, 0, 0, 1)"
        usage: crisp product motion
---

# Minimal Product Linear (seed)

**Not approval truth.** Editorial product UI lean for tools that should feel
quiet, structured, and keyboard-friendly. Approve a project-specific direction
before treating these tokens as product truth.

## Suggested dials

- Variance: 5
- Motion: 3
- Density: 5

## Signature hints

- Hairline structure over heavy elevation
- One accent, neutral zinc/slate family, compact controls
- Motion only for state change and focus continuity
