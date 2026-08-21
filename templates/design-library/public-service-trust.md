---
design_system:
  schema: spec-kit-design-v1
  name: public-service-trust
  version: 1
  status: seed
  seed_warning: "Aesthetic seed only. Not approval truth. Never substitute for design approve or an approved DESIGN.md."
  platforms:
    - web
    - mobile
    - desktop
  taste:
    dials:
      variance: 3
      motion: 2
      density: 6
    aesthetic_family: public-service-trust
    surface_types:
      - service-portal
      - healthcare
      - civic-flow
      - dashboard
    anti_slop_locks:
      - ban-deceptive-color-coding
      - ban-skeuomorphic-faux-urgency
      - ban-brand-only-validation
  tokens:
    color:
      surface.canvas:
        value: "#f5f7fb"
        usage: calm institutional background
      surface.panel:
        value: "#ffffff"
        usage: readable cards and forms
      text.primary:
        value: "#111827"
        usage: primary information
      text.secondary:
        value: "#334155"
        usage: secondary context and details
      text.inverse:
        value: "#ffffff"
        usage: text on deep trust accents
      border.subtle:
        value: "#cbd5e1"
        usage: reliable input and section lines
      accent.primary:
        value: "#2563eb"
        usage: primary actions and links
      accent.secondary:
        value: "#0ea5e9"
        usage: progress and supportive prompts
      accent.success:
        value: "#15803d"
        usage: confirmations and verified states
      accent.warning:
        value: "#d97706"
        usage: caution without panic
      accent.danger:
        value: "#b91c1c"
        usage: critical errors and blockers
    spacing:
      scale.1:
        value: "8px"
        usage: dense legal and service data rows
      scale.2:
        value: "12px"
        usage: compact form spacing
      scale.3:
        value: "16px"
        usage: card and block grouping
      scale.4:
        value: "24px"
        usage: section spacing
      scale.5:
        value: "32px"
        usage: secure step progression
    radius:
      control:
        value: "8px"
        usage: predictable control shape
      panel:
        value: "10px"
        usage: restrained cards and panels
    typography:
      body.family:
        value: "system-ui, 'Segoe UI', sans-serif"
        usage: plain-language readability
      body.size:
        value: "15px"
        usage: service forms and status text
      heading.family:
        value: "Georgia, serif"
        usage: trusted institutional headings
      heading.weight:
        value: "650"
        usage: stable hierarchy
    motion:
      duration.fast:
        value: "100ms"
        usage: minimal and calm interactions
      duration.base:
        value: "180ms"
        usage: step changes and status updates
      easing.standard:
        value: "cubic-bezier(0.4, 0, 0.2, 1)"
        usage: accessible neutral rhythm
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
    table:
      required_states:
        - default
        - sorted
        - error
      token_refs:
        background: "{color.surface.canvas}"
        border: "{color.border.subtle}"
        radius: "{radius.panel}"
  accessibility:
    contrast_intent: strict WCAG AA with explicit exception checks for data-dense forms
    focus_visible: required
    keyboard_navigation: required
    reduced_motion: required
---

# Public Service Trust

**Not approval truth.** This is a seed for trust-oriented interfaces only, not an approved direction.

## Intended feel

- Clear institutional clarity for healthcare, civic services, and public workflows
- Low visual noise, explicit status, and transparent action chains
- Trust comes from readability, predictable states, and accessible confirmation paths

## Accessibility and confidence rules

- Prioritize readability and predictability over novelty.
- Every important message must have text-level alternatives in addition to color.
- Keep progress, warning, and error communication explicit and non-urgent unless truly critical.

## Platform notes

- Web: strict form labeling, error summaries, and reviewability.
- Mobile: enlarge tappable targets while keeping dense service forms comprehensible.
- Desktop: preserve long-form clarity and side-by-side summaries without crowding.

## Anti-patterns

- Avoid manipulative urgency language and decorative urgency badges.
- Avoid low-contrast action links with ambiguous state.
- Avoid reducing trust by hiding confirmation and accountability actions.

## Design Change Policy

Update this preset through `sp-design` before changing service-critical states, error messaging hierarchy, or accessibility defaults.

