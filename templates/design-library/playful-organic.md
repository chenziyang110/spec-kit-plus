---
design_system:
  schema: spec-kit-design-v1
  name: playful-organic
  version: 1
  status: seed
  seed_warning: "Aesthetic seed only. Not approval truth. Never substitute for design approve or an approved design-change.md."
  platforms:
    - web
    - mobile
    - desktop
  taste:
    dials:
      variance: 7
      motion: 5
      density: 4
    aesthetic_family: playful-organic
    surface_types:
      - community-app
      - education
      - onboarding
    anti_slop_locks:
      - ban-robotic-flatness
      - ban-heavy-metal-ui-aesthetics
      - ban-fluorescent-chaos
  tokens:
    color:
      surface.canvas:
        value: "#fffdf8"
        usage: warm organic base background
      surface.panel:
        value: "#fffcf5"
        usage: soft cards and playful sections
      text.primary:
        value: "#1f2937"
        usage: primary copy and headings
      text.secondary:
        value: "#52525b"
        usage: captions and hints
      text.inverse:
        value: "#ffffff"
        usage: high-contrast text on accent controls
      border.subtle:
        value: "#e7d8c8"
        usage: soft outline and separation
      accent.primary:
        value: "#e08a3f"
        usage: primary action and emotional emphasis
      accent.secondary:
        value: "#4aa9b8"
        usage: supportive links and secondary CTAs
      accent.success:
        value: "#16a34a"
        usage: confirmations and positive transitions
      accent.warning:
        value: "#b45309"
        usage: completion and waiting states
    spacing:
      scale.1:
        value: "6px"
        usage: compact control adjacency
      scale.2:
        value: "12px"
        usage: touch target breathing space
      scale.3:
        value: "16px"
        usage: card and section padding
      scale.4:
        value: "24px"
        usage: module rhythm and breathing
      scale.5:
        value: "32px"
        usage: landing-friendly transitions
    radius:
      control:
        value: "14px"
        usage: friendly controls
      panel:
        value: "18px"
        usage: soft cards and shelves
    typography:
      body.family:
        value: "Nunito, system-ui, sans-serif"
        usage: warm reading texture
      body.size:
        value: "15px"
        usage: readable baseline for web/mobile
      heading.family:
        value: "Inter, system-ui, sans-serif"
        usage: clear approachable headings
      heading.weight:
        value: "650"
        usage: friendly hierarchy with shape
    motion:
      duration.fast:
        value: "140ms"
        usage: subtle lift and response
      duration.base:
        value: "240ms"
        usage: cards, focus, and list transitions
      easing.standard:
        value: "cubic-bezier(0.2, 0.8, 0.2, 1)"
        usage: organic motion rhythm
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
    contrast_intent: WCAG AA for ordinary text; check text-over-accent on low-contrast surfaces
    focus_visible: required
    keyboard_navigation: required
    reduced_motion: required
---

# Playful Organic

**Not approval truth.** This is a reusable aesthetic seed, not an approved contract.

## Intended feel

- Friendly and relational interfaces with gentle curves and soft movement
- Balanced liveliness: visible character without visual noise
- Desktop, mobile, and web all preserve the same tactile warmth and spacing grammar

## Platform notes

- Web: use rounded surface rhythm and larger whitespace to keep content friendly and readable.
- Mobile: increase thumb comfort through larger touch areas and consistent card spacing.
- Desktop: preserve visual softness while using tighter rails for data density.

## Anti-patterns

- Avoid random micro-illustrative noise and decorative excess.
- Avoid hard 90-degree corners everywhere in preference for soft continuity.
- Avoid low-contrast text-on-accent combinations.

## Design Change Policy

Update this preset through `sp-design` before changing its density, palette logic, or required interaction states.
