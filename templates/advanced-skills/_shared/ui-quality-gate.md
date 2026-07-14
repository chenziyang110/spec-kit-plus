# UI quality gate

Read this reference only when work changes a user-visible screen, component,
layout, navigation or interaction flow, responsive behavior, visual state,
desktop/mobile surface, TUI layout, or CLI presentation. UI work does not
require an external screenshot to trigger this gate.

## Design readiness

Read the root `DESIGN.md` and relevant live surfaces. `design_system.status:
bootstrap` is an initialized seed, not product direction. Route a new product
surface, redesign, rebrand, shared component language, or unresolved visual
direction to `$spx-design`. A narrow existing-pattern fix may continue only
when the governing tokens/components and affected states are clear.

Avoid generic defaults that are not grounded in product purpose or current
language. Name the experience intent, information hierarchy, density, and at
least one recognizable visual or interaction signature. Reuse approved tokens
and components; make any required extension explicit.

## Delivery chain

For substantive UI work preserve one contract through the workflow:

`DESIGN.md + original references -> ui-brief.md -> plan ui_design_contract -> task ui_contract -> real-entrypoint evidence`

The UI brief is required for substantive UI work even without external
references. It identifies entry points, required states and viewports,
must-preserve/may-adapt/must-not decisions, responsive/accessibility rules, and
visual acceptance evidence. When references exist, keep the original inspectable
assets; prose alone is not a fidelity source. Default reference fidelity is
`approximate`; `high` requires comparison and a difference/deviation record.
Treat third-party source as evidence, not a license to copy protected brand,
artwork, trade dress, or proprietary implementation.

## Implementation acceptance

Do not stop at code correctness. Run the real entry point, capture the required
representative viewport/state matrix, inspect it against `DESIGN.md`, the UI
brief, prior surfaces, and original references, fix concrete drift, then
recapture. For web UI also check overflow, console errors, keyboard/focus, and
accessibility when applicable. For mobile include safe areas, touch targets,
platform navigation, and device states; for desktop include resize, high-DPI,
keyboard shortcuts, and window states; for TUI include representative terminal
widths, color fallback, and non-color state cues; for CLI include help/error
clarity, stable human text, machine-readable output, actionable recovery, and
localization where supported. Tests passed and visual acceptance are separate
claims.

If visual comparison is unavailable, record `pending-human-review` and the
exact evidence/decision needed. Never claim visual match from prose, component
tests, or source inspection alone.
