---
design_system:
  schema: spec-kit-design-v1
  name: marketing-editorial-asymmetric
  version: 1
  status: seed
  seed_warning: "Aesthetic seed only. Not approval truth. Never substitute for design approve or an approved DESIGN.md."
  platforms:
    - web
    - content
  taste:
    dials:
      variance: 8
      motion: 7
      density: 3
    aesthetic_family: marketing-editorial-asymmetric
    surface_types:
      - landing
    anti_slop_locks:
      - ban-ai-neon-hero
      - ban-three-equal-feature-cards
      - ban-section-number-eyebrows
  tokens:
    color:
      surface.canvas:
        value: "#f7f3ee"
        usage: warm paper canvas for editorial marketing
      surface.panel:
        value: "#ffffff"
        usage: story cards and media frames
      text.primary:
        value: "#1c1917"
        usage: primary editorial body and headlines
      text.secondary:
        value: "#57534e"
        usage: supporting copy and captions
      text.inverse:
        value: "#fafaf9"
        usage: text on dark media or accent fills
      border.subtle:
        value: "#d6d3d1"
        usage: hairlines and figure frames
      accent.primary:
        value: "#0f766e"
        usage: singular teal accent for CTA and links
      accent.danger:
        value: "#b91c1c"
        usage: rare destructive or urgency accents
    spacing:
      scale.1:
        value: "8px"
        usage: inline gaps
      scale.2:
        value: "16px"
        usage: paragraph and control spacing
      scale.3:
        value: "32px"
        usage: section rhythm
      scale.4:
        value: "64px"
        usage: large marketing section breaks
    radius:
      control:
        value: "999px"
        usage: pill CTAs
      panel:
        value: "4px"
        usage: media frames stay nearly square
    typography:
      body.family:
        value: "ui-sans-serif"
        usage: readable body and UI chrome
      body.size:
        value: "18px"
        usage: marketing body default
      heading.family:
        value: "ui-sans-serif"
        usage: display headlines without default AI serif
      heading.weight:
        value: "650"
        usage: confident hierarchy without scream scale
    motion:
      duration.fast:
        value: "160ms"
        usage: hover and focus feedback
      duration.base:
        value: "280ms"
        usage: section entrance and media reveal
      easing.standard:
        value: "cubic-bezier(0.2, 0.8, 0.2, 1)"
        usage: soft marketing motion
---

# Marketing Editorial Asymmetric (seed)

**Not approval truth.** Copy tokens only after the user approves a project-specific
preview direction. This seed biases toward asymmetric landing and editorial
marketing composition with one accent and generous whitespace.

## Suggested dials

- Variance: 8
- Motion: 7
- Density: 3

## Signature hints

- Split hero with media occupying a dominant uneven column
- One primary CTA; no secondary "Learn more" clutter by default
- Section rhythm driven by whitespace and type scale, not card grids
