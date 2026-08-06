---
design_system:
  schema: spec-kit-design-v1
  name: industrial-brutalist
  version: 1
  status: seed
  seed_warning: "Aesthetic seed only. Not approval truth. Never substitute for design approve or an approved DESIGN.md."
  platforms:
    - web
    - content
  taste:
    dials:
      variance: 9
      motion: 3
      density: 5
    aesthetic_family: industrial-brutalist
    surface_types:
      - landing
    anti_slop_locks:
      - ban-soft-glassmorphism-default
      - ban-ai-neon-hero
      - ban-generic-card-grid
  tokens:
    color:
      surface.canvas:
        value: "#f5f5f4"
        usage: raw paper/stone canvas
      surface.panel:
        value: "#e7e5e4"
        usage: hard panels and slabs
      text.primary:
        value: "#0c0a09"
        usage: high-contrast ink
      text.secondary:
        value: "#44403c"
        usage: secondary labels
      text.inverse:
        value: "#fafaf9"
        usage: inverse on solid blackish fills
      border.subtle:
        value: "#0c0a09"
        usage: hard rules replace soft shadows
      accent.primary:
        value: "#dc2626"
        usage: singular industrial accent
      accent.warning:
        value: "#ca8a04"
        usage: caution marks
    spacing:
      scale.1:
        value: "4px"
        usage: tight mechanical gaps
      scale.2:
        value: "12px"
        usage: control packing
      scale.3:
        value: "24px"
        usage: block rhythm
      scale.4:
        value: "40px"
        usage: slab section breaks
    radius:
      control:
        value: "0px"
        usage: sharp controls
      panel:
        value: "0px"
        usage: no soft corners
    typography:
      body.family:
        value: "ui-monospace"
        usage: mechanical body where appropriate
      body.size:
        value: "15px"
        usage: dense but readable mono body
      heading.family:
        value: "ui-sans-serif"
        usage: heavy sans display
      heading.weight:
        value: "800"
        usage: industrial weight
    motion:
      duration.fast:
        value: "80ms"
        usage: abrupt feedback
      duration.base:
        value: "160ms"
        usage: hard cuts over soft fades
      easing.standard:
        value: "linear"
        usage: mechanical motion language
---

# Industrial Brutalist (seed)

**Not approval truth.** Experimental marketing and portfolio lean only. Do not
apply to trust-public or dense ops workspaces without an explicit brief.

## Suggested dials

- Variance: 9
- Motion: 3
- Density: 5

## Signature hints

- Hard borders, zero radius, mono labels, singular loud accent
- Asymmetric slabs instead of soft card stacks
- Motion is sparse and mechanical, not cinematic
