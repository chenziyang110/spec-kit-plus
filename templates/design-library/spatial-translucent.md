---
design_system:
  schema: spec-kit-design-v1
  name: spatial-translucent
  version: 1
  status: seed
  seed_warning: "Aesthetic seed only. Not approval truth. Never substitute for design approve or an approved DESIGN.md."
  platforms:
    - web
    - mobile
    - desktop
  taste:
    dials:
      variance: 4
      motion: 2
      density: 5
    aesthetic_family: spatial-translucent
    surface_types:
      - dashboard
      - content-rich
      - layered-app
    anti_slop_locks:
      - ban-neon-glass-overload
      - ban-heavy-backdrop-filters
      - ban-contrast-loss-through-transparency
  tokens:
    color:
      surface.canvas:
        value: "#edf0f3"
        usage: layered neutral background
      surface.panel:
        value: "#ffffffd6"
        usage: translucent panel fill with readable fallback
      text.primary:
        value: "#1f2937"
        usage: base text on light and glass surfaces
      text.secondary:
        value: "#4b5563"
        usage: muted metadata
      text.inverse:
        value: "#0f172a"
        usage: text on warm accents
      border.subtle:
        value: "#cbd5e1"
        usage: soft separations under blur layering
      accent.primary:
        value: "#2563eb"
        usage: core controls and focus highlights
      accent.secondary:
        value: "#0ea5e9"
        usage: auxiliary controls and tabs
      accent.success:
        value: "#16a34a"
        usage: verified and complete states
      accent.danger:
        value: "#b91c1c"
        usage: destructive and error states
    spacing:
      scale.1:
        value: "6px"
        usage: compact icon-text spacing
      scale.2:
        value: "10px"
        usage: tight grouped spacing
      scale.3:
        value: "16px"
        usage: card and field padding
      scale.4:
        value: "20px"
        usage: panel rhythm
      scale.5:
        value: "28px"
        usage: breathing for layered cards
    radius:
      control:
        value: "12px"
        usage: balanced corners for layered controls
      panel:
        value: "20px"
        usage: glass card envelopes
    typography:
      body.family:
        value: "Inter, system-ui, sans-serif"
        usage: spatial interface body
      body.size:
        value: "14px"
        usage: workspace default
      heading.family:
        value: "Inter, system-ui, sans-serif"
        usage: readable hierarchy on dense surfaces
      heading.weight:
        value: "650"
        usage: section emphasis in layered cards
    motion:
      duration.fast:
        value: "120ms"
        usage: subtle lift and focus
      duration.base:
        value: "220ms"
        usage: panel and state transitions
      easing.standard:
        value: "cubic-bezier(.2, 0.8, .2, 1)"
        usage: restrained spatial movement
  components:
    button:
      required_states:
        - default
        - hover
        - focus
        - disabled
        - loading
      token_refs:
        background: "{color.surface.panel}"
        text: "{color.text.primary}"
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
  accessibility:
    contrast_intent: WCAG AA for body and controls; fallback panel tokens remove translucency when contrast drops
    focus_visible: required
    keyboard_navigation: required
    reduced_motion: required
---

# Spatial Translucent

**Not approval truth.** This seed is a design direction prototype, not approved product truth.

## Intended feel

- Restrained glass-like layering with high readability
- Spatial grouping via soft stacking, not heavy card chrome
- Explicit focus and contrast controls so translucency does not reduce legibility

## Performance & readability policy

- Prefer simple backgrounds with `backdrop-filter` as enhancement only.
- For constrained devices, older browsers, or high-contrast contexts: force the translucent panel to solid fallback (`rgba` to high opacity) and raise `text` and `border` contrast.
- Keep one blur layer per card stack; avoid stacking effects on large scroll zones.

## Platform notes

- Web: use depth through spacing and borders before blur.
- Mobile: reduce large translucent overlays; prioritize text clarity over glass effects.
- Desktop: permit layered cards on hover while preserving 1:1 fallback contrast.

## Anti-patterns

- Avoid low-contrast gradient stacking.
- Avoid blur-heavy surfaces above text blocks.
- Avoid full-page dependence on background blur for orientation.

## Design Change Policy

Update this preset through `sp-design` before changing blur strategy, panel opacity, or contrast fallback thresholds.

