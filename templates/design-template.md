---
design_system:
  schema: spec-kit-design-v1
  name: bootstrap-design-seed
  version: 1
  status: bootstrap
  approval:
    status: unapproved
    direction: null
    source_refs: []
    visual_refs: []
  product_context:
    subject: null
    audience: null
    single_job: null
  direction_contract:
    visual_thesis: null
    content_thesis: null
    interaction_thesis: null
    signature_element: null
  platforms:
    - select-during-sp-design
  tokens:
    color: {}
    spacing: {}
    radius: {}
    typography: {}
  components: {}
  accessibility:
    contrast_intent: WCAG AA for ordinary text where platform rendering allows
    focus_visible: required
    keyboard_navigation: required
---

# Project Design System

This file is a structurally valid bootstrap seed, not an approved product design.
Before substantive new UI, run `sp-design`/`spx-design`, select a project-specific
direction, replace generic starter choices, and set the approval metadata above.
Downstream agents must not treat `status: bootstrap` as locked visual truth.

## Product Feel

This seed intentionally contains no palette, type scale, spacing scale, radius,
or component style to copy. Select them from product context and live evidence.

## Design Direction

Record the subject, audience, single user job, visual/content/interaction
theses, signature element, and the inspectable visual artifact the user
approved. A prose label alone is not visual approval.

## Platforms

- Web: responsive layouts, keyboard access, visible focus, stable control sizes, and screenshots for key viewports.
- Mobile: thumb-friendly controls, native-feeling density, readable empty and error states.
- Desktop: efficient layouts, command discoverability, and stateful controls that do not jump.
- TUI: readable narrow-width output, no-color mode, clear selected and error states.
- CLI: concise output, scan-friendly tables, predictable success and error messages, no reliance on color alone.

## Component Rules

- Buttons must have default, hover, focus, disabled, and loading states.
- Inputs must have default, hover, focus, disabled, and error states.
- Repeated cards may use `radius.panel`; controls should use `radius.control`.
- Prefer existing component patterns before adding variants.
- Do not invent styling outside the token set without updating this file.

## Anti-Patterns

- Do not ship generic gradient-heavy screens that ignore product context.
- Do not mix unrelated radius, spacing, shadow, or typography systems.
- Do not hide loading, empty, error, disabled, or permission states.
- Do not rely on color alone for status.
- Do not create UI evidence that proves behavior while ignoring visual layout.

## UI QA Checklist

- Approved project tokens are used consistently.
- Required component states are implemented or explicitly out of scope for the surface.
- Text fits inside controls and panels at mobile and desktop widths.
- Keyboard and focus behavior are visible where the platform supports them.
- Evidence captures structure, visual output, runtime diagnostics, and comparison
  at real entry points; browser evidence maps these to accessibility snapshots,
  screenshots, console/runtime output, and visual comparison or human review.

## Design Change Policy

Promote this seed to `status: approved` only through `sp-design`/`spx-design`
after a direction is selected from product and repository evidence. Later
changes to product-wide style, brand, density, component rules, token values,
or platform expectations must update this file and its approval provenance.
