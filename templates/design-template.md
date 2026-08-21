---
design_system:
  schema: spec-kit-design-v1
  name: bootstrap-design-seed
  version: 1
  status: bootstrap
  approval:
    status: unapproved
    direction: null
    review_round: null
    source_refs: []
    visual_refs: []
    preview_sha256: null
    manifest_sha256: null
    visual_medium: null
    prompt_ref: null
    prompt_sha256: null
    inspection_owner: null
    handoff_ref: null
    handoff_sha256: null
    decision_ids: []
    handoff_contract_ids: []
    capability_profile_ids: []
    specimen_ids: []
  product_context:
    subject: null
    audience: null
    single_job: null
  professional_skill_route:
    catalog_version: spec-kit-ui-professional-v1
    status: unresolved
    domain_skill_id: null
    style_skill_id: null
    specialist_skill_ids: []
    matched_signals: {}
    loaded_refs: []
    unresolved_candidates: []
    mature_web_ui_resource_ids: []
    web_ui_asset_inventory:
      status: not-scanned
      manifest_refs: []
      lockfile_refs: []
      framework_ids: []
      installed_resources: []
      component_roots: []
      token_refs: []
      theme_refs: []
      surface_refs: []
    mature_web_ui_selection:
      status: not-applicable
      primary_resource_id: null
      supporting_resource_ids: []
      agent_resource_ids: []
      candidates: []
      confirmation_codes: []
    smoothness_acceptance_ids: []
  style_authority:
    mode: unresolved
    scope_level: null
    source_refs: []
    protected_surfaces: []
    allowed_style_delta_surfaces: []
    authorization_source: null
  direction_contract:
    visual_thesis: null
    content_thesis: null
    interaction_thesis: null
    signature_element: null
    safe_system_choices: []
    creative_risks: []
  platforms:
    - select-during-sp-design
  capability_profiles: []
  specimens: []
  tokens:
    color: {}
    spacing: {}
    radius: {}
    typography: {}
    motion: {}
    elevation: {}
    sizing: {}
    layout: {}
  color_modes: {}
  components: {}
  responsive:
    breakpoints: {}
    adaptations: []
  content:
    voice_rules: []
    real_content_sources: []
    imagery_rules: []
  decisions: []
  verification:
    required_viewports: []
    required_states: []
    surface_catalog: []
    scenario_matrix: []
    interaction_matrix: []
    editing_matrix: []
    data_state_matrix: []
    accessibility_matrix: []
    navigation_matrix: []
    content_matrix: []
    motion_contract: {}
    usability_validation: {}
    visual_tolerance: null
    accepted_deviations: []
  accessibility:
    contrast_intent: WCAG AA for ordinary text where platform rendering allows
    focus_visible: required
    keyboard_navigation: required
    reduced_motion: required
    touch_target: platform appropriate
    forced_colors: supported where the platform exposes it
---

# Project Design System

This packaged template exists only for legacy root-contract compatibility. Init
does not copy it into new projects, and a pre-existing root `DESIGN.md` is
read-only baseline input rather than current approval truth. Before substantive
new UI, use `specify-runtime design change` to create a bounded `UD-*`
workspace, and register its change-local `DESIGN.md`. Never replace this root
file in place.
Downstream agents must not treat `status: bootstrap` as locked visual truth or
resolve it as an implicit latest design.

## Product Feel

This seed intentionally contains no palette, type scale, spacing scale, radius,
or component style to copy. Select them from product context and live evidence.

## Design Personality / DNA

Record design personality when this system is approved (not as bootstrap filler):

- Product subject and audience
- Personality traits (for example trustworthy, intelligent, calm)
- Explicit avoid list (for example playful toy feel, generic SaaS dashboard)
- Global dials when set in the design brief: variance / motion / density (1-10)

Downstream agents must read approved DNA and dials before generating UI. They
are not free-form style adjectives after approval—they bind visual hierarchy,
motion, and density choices.

## Design Direction

Record the subject, audience, single user job, visual/content/interaction
theses, signature element, and the inspectable visual artifact the user
approved. A prose label alone is not visual approval.

## Visual And Interaction Signature

Record the recognizable project-specific element and the safe system choices or
deliberate risks that create it. Every implementable statement should map to a
stable `DS-*` decision ID.

## Foundations

Define semantic color modes, typography hierarchy, spacing, geometry,
elevation, sizing, layout, and motion. Record resolved font behavior and
foreground/background contrast pairs instead of relying on aesthetic labels.

When values were reverse-engineered from screenshots or live UI, record
**Design Evidence v1** per material token (`measured` | `inferred` |
`assumption`; alias `evidence-backed-inference`) so downstream work does not
treat guesses as measured truth. Non-measured claims need rationale; inferred
claims need source or source_gap.

## Platforms

- Web: responsive layouts, keyboard access, visible focus, stable control sizes, and screenshots for key viewports.
- Mobile: thumb-friendly controls, native-feeling density, readable empty and error states.
- Desktop: efficient layouts, command discoverability, and stateful controls that do not jump.
- TUI: readable narrow-width output, no-color mode, clear selected and error states.
- CLI: concise output, scan-friendly tables, predictable success and error messages, no reliance on color alone.

## Component Rules

- For Web UI, prefer inspected live components, then one compatible mature
  primary system plus only exact headless/specialist gaps from
  `mature_web_ui_resource_ids`; custom primitives require a recorded gap.
- Final Web selection requires a scanned `web_ui_asset_inventory`; retain the
  selected candidate, compact reason codes, and confirmation codes from
  `mature_web_ui_selection`.
- Buttons must have default, hover, focus, disabled, and loading states.
- Inputs must have default, hover, focus, disabled, and error states.
- Record mouse/pointer, keyboard/focus, touch, and shortcut behavior for each
  changed interactive component.
- Record empty, representative-data, dense-data, and failure expectations when
  a component changes meaning across data conditions.
- Repeated cards may use `radius.panel`; controls should use `radius.control`.
- Prefer existing component patterns before adding variants.
- Approved `component_contracts` record `variants`, `content_constraints`,
  `semantic_token_refs`, `governance`, and `iconography`; governance chooses
  reuse, extension, or justified new work and assigns gaps and deprecation.
- Do not invent styling outside the token set; approve a new design round and
  regenerate this file only through `specify-runtime design export`.

## Motion Rules

- Preserve the structured `motion_contract`: `purpose`, transition `id`,
  `surface`, `trigger`, `response`, `duration_ms`, `easing`,
  `interrupt_behavior`, `decision_ids`, `reduced_motion`, and
  `feedback_timing` (`immediate_ms`, `progress_ms`, `timeout_ms`).
- Use motion to reveal hierarchy, reinforce action, or explain state change.
- Every meaningful animation needs a `prefers-reduced-motion` equivalent.
- The approved project-level image-primary or HTML-primary round is the visual motion reference;
  feature-level targets still define concrete composition and state coverage.

## Responsive Behavior

- Define content-driven breakpoints and the navigation, density, hierarchy,
  overflow, and input changes at each boundary.
- Name stretch behavior, min/max useful sizes, and overflow recovery after
  resize or container compression.
- Record the required viewport and state matrix under `verification`.
- Treat mobile as an adaptation of priorities, not a uniformly shrunken desktop.

## Content And Imagery

- Name real content sources, long-copy or localization stress cases, and visible
  data-volume expectations.
- Record owned/licensed image sources, crop behavior, aspect ratios, and missing
  asset recovery.
- Do not silently substitute lorem ipsum, generic stock art, or decorative
  placeholders that hide layout risk.

## Professional Verification Contracts

An approved change-local successor—not this bootstrap seed—must carry exact
`interaction_matrix`, `editing_matrix`, `data_state_matrix`, `accessibility_matrix`,
`navigation_matrix`, `content_matrix`, `motion_contract`, and
`usability_validation` values under `design_change.verification`. The top-level
accessibility summary is never a substitute for per-surface matrix rows.
Interaction rows use exact event sequence, immediate feedback, focus, repeat,
cancellation, and pending behavior fields; one aggregate expectation is not a
current interaction contract.
Accessibility targets WCAG 2.2 AA or platform equivalent, Name/Role/Value,
reading/focus order, keyboard and drag alternatives, dynamic status
announcements, target size, contrast, 400% reflow, forced colors, and
image/icon alternatives. Navigation covers entry, hierarchy, back/close, deep
links, interruption recovery, consistency, and landmarks. Content covers CTA,
empty/loading/error/permission/destructive/confirmation/undo/privacy states,
RTL, localization, truncation, and locale-aware date/number/time-zone output.
`usability_validation` is risk based: low-risk work may use cognitive or
heuristic review; medium/high-risk work names target users, critical tasks,
success criteria, human review, and applicable `smoothness_acceptance_ids`.
Use risk-based or pairwise coverage, never
an unbounded Cartesian product; automated tests and screenshots do not prove
target-user usability.

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

## Reference Fidelity

Record each source, use intent, adopted decision IDs, permitted adaptation, and
forbidden copying. The approved preview reference, manifest digest, and
direction must resolve to the same immutable approval sidecar.

## Planned Gaps and Exceptions

Record only explicit, owned gaps with a revisit condition and affected decision
IDs. Absence from the contract is not permission to reinterpret the design.

## Design Change Policy

Promote this seed to `status: approved` only through `sp-design`/`spx-design`
after a direction is selected from product and repository evidence. Later
changes to product-wide style, brand, density, component rules, token values,
or platform expectations require a new approved design round followed by
`specify-runtime design export`; never edit this file or its approval provenance
directly.
