---
name: "spec-kit-ui-design"
description: "Use when UI, UX, visual design, design-system, accessibility, component, platform interface, TUI, or CLI output quality matters in a Spec Kit Plus project."
---

# Spec Kit UI Design

This passive skill keeps UI work aligned with the product's design system before
implementation invents generic one-off styling. Use it whenever UI, UX, visual
design, design-system, accessibility, component coverage, platform interface,
TUI, or CLI output quality affects the outcome.

Passive SKILL invocation must not enter any `sp-*` or `spx-*` workflow. All
`sp-*` and `spx-*` workflows are user-invoked only: recommend the projected
invocation and stop until the user explicitly invokes it. This passive
skill must not load or enter `sp-design` itself.

## Collaborative Design Studio

For `sp-design`, treat design as a guided studio conversation, not a batch
generator. Read the live product and supplied references first, state a compact
design hypothesis, then ask only one unresolved, direction-changing question at
a time. Do not advance past an unanswered question. Once the brief is coherent,
probe the current session's image generation, image inspection, and image
editing tools. Do not hard-code capability from the Agent or integration name.
Use an image-primary round when generation is available and an HTML-primary
round otherwise. Author one current concept in each immutable round, critique
it when the session can actually inspect the artifact, show it to the user, and
revise that same direction in a new round until the user gives explicit
approval.

Load these references progressively:

- Read `.specify/templates/ui-professional-skills/router.md` before visual
  authoring. Resolve `style_authority` first: live product UI governs feature,
  component, and partial-page work (`inherit-existing`, exact source refs,
  protected `global-shell`/`shared-components`, no style delta, no style skill).
  Only explicit user authorization for one exact complete-page visual overhaul
  permits `page-overhaul-authorized`; a functional-page refactor or feature
  addition does not. Then resolve `professional_skill_route`, persist `domain_skill_id`,
  `style_skill_id`, `specialist_skill_ids`, `matched_signals`, and
  `loaded_refs`, plus `mature_web_ui_resource_ids`, `web_ui_asset_inventory`,
  `mature_web_ui_selection`, deterministic `component_adoption_plan`, read-only
  official-resource refresh result, `smoothness_acceptance_ids`, and performance budgets when Web UI
  applies. Pass the actual project root for the bounded read-only scan, then
  load only the exact selected one domain, zero-or-one style, and zero-to-two
  specialists. For Web component work, read the router-triggered
  `web-component-selection.md`; load official Agent/MCP/LLM material only for a
  selected candidate. Never load the full UI professional skill catalog. If
  material ambiguity remains, ask the router's one high-impact question before
  selecting a medium-specific prompt augmentation.
- Read [references/discovery-dialogue.md](references/discovery-dialogue.md) for
  active questioning, question state, and the pre-visual checkpoint.
- Read
  [references/visual-capability-routing.md](references/visual-capability-routing.md)
  before selecting a review medium.
- For an image-primary round, read
  [references/image-generation-studio.md](references/image-generation-studio.md).
- For an HTML-primary round, read
  [references/html-prototype-studio.md](references/html-prototype-studio.md) and
  [references/prototype-craft.md](references/prototype-craft.md).
- Read [references/critique-loop.md](references/critique-loop.md) before showing
  a round, processing feedback, or asking for approval.
- Load only the target-platform guidance that applies:
  [references/platform-web.md](references/platform-web.md),
  [references/platform-apple.md](references/platform-apple.md),
  [references/platform-windows.md](references/platform-windows.md), or
  [references/platform-android.md](references/platform-android.md). For a
  multi-platform product, keep one shared intent and write distinct platform
  adaptations instead of forcing one interaction model onto every platform.

## Design Intelligence

Horizontal **Design Intelligence Engine** across discussion, design, specify,
quick, implement, debug, and review—not a separate workflow command. Combines
Taste Intelligence, Design System Reverse Engineering (Evidence → UI System
Model → Implementation), and Visual Validation. When UI is involved: read taste
DNA / personality, dials (variance · motion · density), evidence levels
(`measured` / `evidence-backed-inference` / `assumption`), UI System Model
(tokens, components, states, responsive, behavior), surface-aware anti-slop, and
design readiness. Subordinate all of these to the exact registered
`.specify/design/changes/<UD-ID>/design-change.md` plus its immutable
preview/approval/handoff—not a global root contract or parallel `.design/`
tree. No root design document participates in the workflow.
Discussion captures
durable `design_context`; design reverse-engineers system rules; specify carries
UI Requirements + Acceptance Criteria; quick runs UI Audit then
design-before-code; debug uses UI Debug Mode (layout / interaction / taste);
implement/review require system model + anti-slop + visual validation loop.

## Design System Gate

- Before substantive UI work, run
  `specify-runtime design resolve --scope <exact-surface> --format json`, then
  query metadata-only `.specify/design/index.json` through
  `specify-runtime artifact show` and select the applicable registered `UD-*` change,
  and verify its exact `design_ref` and `approval_sha256`. Never resolve
  "latest" or silently substitute a root file.
- `design resolve` is discovery only. If it reports composite coverage, require
  the leader to split the work into independently bound consumer units, each
  with one exact scope and singular binding artifact; do not merge parent and
  successor rules or choose one for a broader surface.
- Implementation must follow that exact change-local `design-change.md` for its
  declared scope: layout, component usage, color, typography, motion, density,
  interaction states, explicit pointer/mouse, keyboard/focus, touch, and
  command behavior, data-state handling, accessibility expectations, and
  evidence requirements.
- When approval points to an immutable
  `.specify/design/changes/<UD-ID>/previews/round-NN.<html|png|jpg|jpeg|webp>#<direction-id>`,
  treat that exact change-level design artifact as inspectable handoff evidence. Preserve its
  component/state, density, meaningful-motion, and reduced-motion decisions;
  do not replace it with prose or a later feature target.
- An unregistered root design document cannot authorize adoption, be selected
  as an implicit latest contract, or suppress a new bounded UI change.
- If no applicable registered change exists, its scope is contradictory, or it
  is too thin for high-risk UI work,
  recommend `sp-design` and the projected invocation `{{invoke:design}}` before
  implementation, then wait for the user's explicit invocation. Do not let
  implementation invent a substitute visual system.
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
- The UI reference lane scaffolds `ui-reference-notes.md` and `ui-brief.md`
  through `specify-runtime artifact`, patches their semantic fields, and creates
  optional `ui-target.html` through `specify-runtime design ui-target`.
- Keep the artifacts distinct: the change-level design preview approves the
  decisions declared for one `UD-*` scope, while feature-level `ui-target.html`
  describes one concrete feature composition.
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
  hover, focus, active, disabled, selected, loading, empty, populated, partial,
  error, success, offline, and permission-limited states where relevant.
- For each affected component, spell out the interaction modes and data
  scenarios rather than assuming the worker will infer them from the screenshot
  or happy-path copy alone.
- Keep component decisions tied to the design system. Reuse existing tokens,
  components, spacing rules, and interaction patterns before adding new ones.
- For Web UI, follow the mature-component preference ladder: compatible live
  component, documented extension, one mature primary system, then only an
  exact headless/specialist gap. Do not mix multiple full component systems on
  one surface or hand-build complex primitives without a recorded gap.
- Preserve every applicable `component_contracts` row, including `variants`,
  `content_constraints`, `semantic_token_refs`, reuse/extend/new `governance`,
  the exact nested adoption action/package/version/license/source/permission row,
  gap/deprecation ownership, and `iconography` source, style, sizing, optical
  alignment, semantics, and fallback.
- If a new component or design token is required, name the source design problem
  and how the new element fits the system.
- Avoid generic one-off styling, unexplained palette shifts, and unrelated bold
  aesthetics that solve presentation but not the product interface problem.

## Professional UI Contract

Carry the exact `surface_catalog`, `scenario_matrix`, `interaction_matrix`,
`editing_matrix`, `data_state_matrix`, `accessibility_matrix`, `navigation_matrix`,
`content_matrix`, `motion_contract`, and `usability_validation` from the
registered design change through Specify, Plan, Tasks, Test Design, Implement,
Review, and Accept. Quick, Debug, Analyze, and Checklist may select the affected
subset but may not omit, rename, or weaken it. A scenario references one stable
surface and the exact rows exercised together; scenarios collectively cover all
selected rows. Preserve its exact `interaction_script`: non-empty
`preconditions`, a selected `start_state_id`, ordered `steps` with
input/action/expected feedback, and bounded `branches`. Branch conditions cover
applicable success, failure, timeout, cancel, retry, duplicate, and out-of-order
outcomes; each `expected_state_id` belongs to the scenario's `data_state_ids`
and names setup, feedback, focus behavior, announcement, and continuation. Keep
`focus_checkpoint`, `announcement_checkpoint`, `completion_checkpoint`, and
`recovery_checkpoint`. Use risk-based or pairwise combinations rather than an unbounded
Cartesian product.

- Interaction rows use exact `id`, `surface`, `input`, `trigger`,
  `event_sequence`, `immediate_feedback`, `focus_behavior`, `repeat_behavior`,
  `cancellation_behavior`, `pending_behavior`, and `decision_ids`. They define
  platform input mechanics; scenario scripts define journey outcomes. Never
  collapse press/move/release or keydown/keyup, repeated activation,
  pointer/gesture cancellation, focus return, and pending-state blocking into
  one generic expectation.
- Accessibility rows cover WCAG 2.2 AA/platform equivalent, Name/Role/Value,
  semantics, reading/focus order, keyboard and drag alternatives, dynamic
  status announcement, applicable Web/native targets, contrast, 400% reflow,
  forced colors/high contrast, and image/icon alternatives. A top-level summary
  does not replace `accessibility_matrix`.
- Navigation rows cover hierarchy, entry/destination, primary task, back/close,
  deep-link behavior, interruption recovery, navigation consistency, and
  orientation landmarks.
- Content rows cover CTA, empty/loading/error/permission, destructive action,
  confirmation, undo/recovery, privacy/trust, long text, truncation, RTL,
  localization, and locale-aware date, number, currency, and time zone output.
- `motion_contract` records purpose, trigger/response, duration/easing,
  interruption/cancel, reduced-motion alternative, and perceived-performance
  feedback thresholds.
- `usability_validation` is risk-tiered. Low-risk existing-pattern changes may
  use a documented cognitive walkthrough or heuristic review. Medium/high-risk
  journeys name target users, critical tasks, success criteria, and mandatory
  human review. Web work also preserves routed `smoothness_acceptance_ids` and
  performance budgets inside this object and proves them through the CLI-owned
  Smoothness Lab report plus the existing UI evidence kinds.
  Automated tests and screenshots cannot substitute for
  target-user usability.

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
