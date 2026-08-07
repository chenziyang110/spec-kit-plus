# UI quality gate

Read this reference only when work changes a user-visible screen, component,
layout, navigation or interaction flow, responsive behavior, visual state,
desktop/mobile surface, TUI layout, or CLI presentation. UI work does not
require an external screenshot to trigger this gate.

Use the deterministic `design profiles` capability catalog for substantive
design work. `no-ui` is valid only with current evidence of no user-visible
presentation; record `design_system_status: not-applicable` and skip the visual
artifact chain. Do not use `no-ui` to downgrade a content, CLI, TUI, mobile,
desktop, or Web presentation surface.

## Design readiness

Query the root `DESIGN.md` through `specify-runtime artifact show` and inspect relevant live surfaces. `design_system.status:
bootstrap` is an initialized seed, not product direction. Route a new product
surface, redesign, rebrand, shared component language, or unresolved visual
direction to `$spx-design`. A narrow existing-pattern fix may continue only
when the governing tokens/components and affected states are clear.

Avoid generic defaults that are not grounded in product purpose or current
language. Separate work type from surface type (`landing`,
`product-workspace`, `hybrid`, `existing-pattern-maintenance`) and platform.
Name subject, audience, single job, visual/content/interaction theses, and one
recognizable signature. Apply the surface-aware anti-slop policy from
`design-library/anti-slop-policy.md` only as a bias correction subordinate to
approved `DESIGN.md`: landing/marketing favors higher variance and bans common
AI-hero fingerprints; product-workspace favors density and bans marketing
theatrics; trust-public favors restraint and real design-system foundations.
This gate never authorizes production implementation inside design workflows.
New or high-visibility direction requires an
inspectable approved visual reference; a narrow existing-pattern exception must
name its live governing surface. Reuse approved tokens and components.
When `sp-design` produced a project-level HTML preview, preserve the exact
immutable `round-NN.html#direction-id` reference and its motion/reduced-motion
contract, preview/manifest/handoff SHA-256 values, immutable handoff ref,
approved `DS-*` decision IDs, and applicable `DH-*` handoff contract IDs.
Do not replace them with a prose summary or the later feature target.

## Delivery chain

For substantive UI work preserve one contract through the workflow:

`DESIGN.md + approved preview/approval/handoff sidecars + original references -> ui-brief.md -> plan ui_design_contract -> task ui_contract -> comparison report + real-entrypoint evidence`

The UI brief is required for substantive UI work even without external
references. It identifies entry points, required states and viewports,
must-preserve/may-adapt/must-not decisions, responsive/accessibility rules, and
visual acceptance evidence. Preserve the approval hashes, required design and
handoff contract IDs, component anatomy, color modes, motion contract, viewport/state
matrix, capability profile and specimen IDs, and real content/image plans. Each UI task carries only its applicable
decision subset; all UI tasks together must cover the plan's required set.
When references
exist, keep the original inspectable assets and assign each a use intent; prose
alone is not a fidelity source. Default reference fidelity is
`approximate`; `high` requires comparison and a difference/deviation record.
Treat third-party source as evidence, not a license to copy protected brand,
artwork, trade dress, or proprietary implementation.

## Implementation acceptance

Do not stop at code correctness. Query `DESIGN.md` and the feature UI brief through targeted `specify-runtime artifact show` calls, run the real entry point, capture the required
representative viewport/state matrix, and inspect it against those returned sections, the
brief, prior surfaces, and original references, fix concrete drift, then
recapture. Submit the observed entrypoint/revision, typed evidence refs, matrix
rows, structural/visual differences, covered decision/handoff IDs, explicit
verdict, and reviewer through `specify-runtime evidence visual-compare`; the CLI
derives and owns the approved bindings, tolerance, accepted deviations, report,
path, and digest. For web UI also check overflow, console errors, keyboard/focus, and
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

## Design Intelligence

Horizontal Design Intelligence Engine for every UI-bearing stage: **Taste
Intelligence** + **Design System Reverse Engineering** + **Visual Validation**.
Not a new mainline command. Reuse design-brief dials (`variance` / `motion` /
`density`), `design_read`, anti-slop locks, and approved `DESIGN.md`—do not
invent a second parameter system or approval authority. UI is a design-system
modeling problem: Evidence → System → Implementation. Prefer tokens, components,
states, and responsive rules over one-shot page clones.

### Taste DNA and dials

Record or inherit design personality (feeling/tone, what to avoid), one-line
`design_read`, dials 1-10 with inference reason, surface type, and active
anti-slop locks before generating or materially changing UI.

### Evidence Level and UI System Model

Reverse-engineered claims carry `measured` | `evidence-backed-inference` |
`assumption` with a reason when not measured. Model UI as pixel / system /
behavior / engineering layers: tokens, components, state matrix (including
hover/focus/loading/empty/error), responsive rules, and keyboard/behavior.
Bind into approved `DESIGN.md` and `.specify/design/design-system.json`—not a
parallel root `.design/` tree. Structured design-context JSON **MUST** conform
to DesignContext v1 (`templates/design-intelligence/schema/design-context.schema.json`).

### Stage hooks

- **Discussion — design discovery**: when UI is involved, capture durable
  `design_context` (not chat-only): `ui_involved`, `feeling_tone`, dials or
  deferred nulls, reference products/intents, information density, interaction
  complexity, anti-slop locks, whether UI Evidence Analysis is needed, and
  whether `$spx-design` is required. Persist in Design Carry-Forward and handoff
  `discussion_decision_digest.design_context`.
- **Design — reverse engineering**: on synthesize or live refine, extract
  tokens/components/states/responsive with evidence levels before boards;
  approve only through design approve/export.
- **Specify — UI Requirements + acceptance**: layout pattern; design-system
  token/component use; required states (loading/empty/error/success/disabled/
  focus); responsive targets; quality (no generic dashboard/template; maintain
  DNA/dials); visual evidence kinds.
- **Quick — UI Audit then design-before-code**: UI Audit issue list first →
  analyze → identify issue → propose before/after → implement → visual check.
  Do not jump straight to code edits.
- **Debug — UI Debug Mode**: classify visual/layout (spacing, alignment,
  overflow, responsive), UX/interaction (unclear action, hover/focus/keyboard,
  loading/empty/error), or taste/generic-look. Name issue, reason, and
  design-aware fix before coding.
- **Implement / Review**: query approved design + UI System Model + anti-slop +
  task `ui_contract` before UI generation; prefer visual hierarchy over
  equal-weight card grids; visual validation loop
  (capture → compare → fix → recapture) or `pending-human-review`.
