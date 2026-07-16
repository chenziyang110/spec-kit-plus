---
name: "spec-kit-ui-design"
description: "Use when UI, UX, visual design, design-system, accessibility, component, platform interface, TUI, or CLI output quality matters in a Spec Kit Plus project."
origin: spec-kit-plus
---

# Spec Kit UI Design

This passive skill keeps UI work aligned with the product's design system before
implementation invents generic one-off styling. Use it whenever UI, UX, visual
design, design-system, accessibility, component coverage, platform interface,
TUI, or CLI output quality affects the outcome.

## Design System Gate

- Before substantive UI work, look for `DESIGN.md` or an equivalent committed
  design-system source. Treat `DESIGN.md` as the expected design contract name
  when documenting or testing this gate.
- If `DESIGN.md` is present, implementation must follow it for layout,
  component usage, color, typography, motion, density, interaction states,
  accessibility expectations, and evidence requirements.
- A `DESIGN.md` with `design_system.status: bootstrap` is only an initialized
  seed. Do not let its generic tokens suppress project-specific design work or
  treat it as an approved product direction.
- If `DESIGN.md` is missing, contradictory, or too thin for high-risk UI work,
  recommend `sp-design` and the projected invocation `{{invoke:design}}` before
  implementation. Do not let implementation invent a substitute visual system.
- Small UI work may proceed without `sp-design` only when the existing design
  intent is clear and the change is a narrow component variant, copy/state
  adjustment, internal form refinement, or low-risk TUI/CLI wording update.
  Record the soft risk and the design assumption in the closeout.

## UI Reference Input Gate

- UI quality applies to every changed user-visible screen, component, layout,
  interaction, responsive state, TUI layout, or CLI presentation—not only work
  with an external screenshot. Substantive UI work needs a feature
  `ui-brief.md`; narrow existing-pattern fixes may record a compact inline
  contract instead.
- Treat screenshots, HTML/CSS mockups, UI framework snippets, Figma exports,
  reference URLs, existing pages, and "make it like this" language as UI
  reference input.
- In `sp-specify`, UI reference input requires
  `choose_ui_reference_lane_dispatch` and `lane_mode: ui-reference-artifact`.
- The UI reference lane writes `ui-reference-notes.md`, `ui-brief.md`, and
  optional `ui-target.html`.
- `approximate` is the default fidelity mode. `high` requires visual
  comparison; `inspiration` extracts principles only.
- If the environment cannot prove visual similarity, the workflow must record
  `pending-human-review`.
- The agent must not claim a UI visually matches a reference without agent
  visual comparison or human approval.

## Platform Rules

- Web work must respect responsive layout, semantic markup, keyboard operation,
  focus states, contrast, motion preferences, viewport screenshots, and browser
  console cleanliness.
- Mobile work must respect platform navigation, touch targets, safe areas,
  density, offline/loading/error states, screen-reader labels, and device-form
  evidence.
- Desktop work must respect resize behavior, keyboard shortcuts, menus,
  platform conventions, window density, high-DPI rendering, and pointer/focus
  interaction evidence.
- TUI work must respect terminal widths, color fallback, readable alignment,
  non-color indicators, progressive output, error states, and copyable command
  output.
- CLI work must respect command help clarity, stable text contracts,
  machine-readable output when applicable, error/action pairing, localization
  concerns, and accessible plain-text formatting.

## Component Coverage

- Cover every user-visible component state that the task can affect: default,
  hover, focus, active, disabled, selected, loading, empty, error, success, and
  permission-limited states where relevant.
- Keep component decisions tied to the design system. Reuse existing tokens,
  components, spacing rules, and interaction patterns before adding new ones.
- If a new component or design token is required, name the source design problem
  and how the new element fits the system.
- Avoid generic one-off styling, unexplained palette shifts, and unrelated bold
  aesthetics that solve presentation but not the product interface problem.

## Evidence

- UI closeout needs platform-appropriate evidence, not only code or unit tests.
- For web, capture viewport screenshots at the relevant desktop and mobile
  widths, check for layout overflow, inspect console errors, and include
  accessibility checks when the surface is interactive.
- For mobile and desktop, include simulator/device/window evidence for the
  affected states and screen sizes.
- For TUI and CLI, include representative terminal captures or exact command
  output for narrow and normal widths, including errors and help text when
  touched.
- Evidence should be visual regression-friendly where screenshots are available:
  use stable paths, deterministic state, and names that describe viewport,
  route, and scenario.
- Before closeout, iterate through real entry point -> capture -> visual inspect
  -> repair -> recapture. Do not equate automated behavior checks with visual
  or interaction acceptance.
