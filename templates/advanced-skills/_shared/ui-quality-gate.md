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
language. Separate work type from surface type (`landing`,
`product-workspace`, `hybrid`, `existing-pattern-maintenance`) and platform.
Name subject, audience, single job, visual/content/interaction theses, and one
recognizable signature. New or high-visibility direction requires an
inspectable approved visual reference; a narrow existing-pattern exception must
name its live governing surface. Reuse approved tokens and components.
When `sp-design` produced a project-level HTML preview, preserve the exact
immutable `round-NN.html#direction-id` reference and its motion/reduced-motion
contract. Do not replace it with a prose summary or the later feature target.

## Delivery chain

For substantive UI work preserve one contract through the workflow:

`DESIGN.md + approved design preview + original references -> ui-brief.md -> plan ui_design_contract -> task ui_contract -> real-entrypoint evidence`

The UI brief is required for substantive UI work even without external
references. It identifies entry points, required states and viewports,
must-preserve/may-adapt/must-not decisions, responsive/accessibility rules, and
visual acceptance evidence. Preserve real content/image plans. When references
exist, keep the original inspectable assets and assign each a use intent; prose
alone is not a fidelity source. Default reference fidelity is
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
localization where supported. Persist the platform-neutral evidence triad:
`structure_snapshot`, `visual_capture`, and `runtime_diagnostics`, plus
`visual_comparison_or_human_review`. For web these mean accessibility/DOM
snapshot, viewport screenshot, and console/runtime output. Tests passed and
visual acceptance are separate claims.

For approved motion, exercise the named entrance, feedback, loading, and state
transition moments at the real entry point and verify the reduced-motion
equivalent. Keep this evidence within the existing structure snapshot, visual
capture, runtime diagnostics, and comparison/review kinds rather than inventing
a parallel motion-evidence schema.

If visual comparison is unavailable, record `pending-human-review` and the
exact evidence/decision needed. Never claim visual match from prose, component
tests, or source inspection alone.
