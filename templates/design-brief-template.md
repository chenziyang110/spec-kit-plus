---
design_brief:
  schema: spec-kit-design-brief-v1
  status: draft
  active_command: sp-design
  phase_mode: design-only
  current_stage: context-intake
  task_type: null
  input_strategy: null
  route_reason: null
  review_round: 0
  active_question:
    id: null
    status: none
    prompt: null
    recommendation: null
    answer: null
    affects: []
  feedback_history: []
  prototype_rounds: []
  visual_collaboration:
    capability_probe:
      source: live-tool-surface
      image_generation: unknown
      image_inspection: unknown
      image_editing: unknown
      evidence: []
    primary_medium: null
    inspection_owner: user
    prompt_strategy: null
    route_reason: null
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
      component_adoption_plan: []
      official_resource_refresh:
        status: not-run
        helper_ref: ui-professional-skills/refresh.py
        selected_resource_ids: []
        selected_agent_resource_ids: []
        network_policy: blocked_by_default
        install_or_upgrade: unauthorized
        items: []
    smoothness_acceptance_ids: []
    smoothness_performance_budgets: {}
  style_authority:
    mode: unresolved
    scope_level: null
    source_refs: []
    protected_surfaces: []
    allowed_style_delta_surfaces: []
    authorization_source: null
  delivery_context:
    origin: standalone
    consumer_ref: null
    binding_ref: null
    binding_sha256: null
    return_target: null
  subject: null
  audience: null
  single_job: null
  surface_types: []
  platforms: []
  capability_profile_ids: []
  specimen_ids: []
  modules: []
  locales: []
  color_modes: []
  required_viewports: []
  required_states: []
  design_read: null
  dials:
    variance: null
    motion: null
    density: null
    inference_reason: null
  aesthetic_family: null
  foundation_strategy: null
  redesign_mode: null
  anti_slop_locks: []
  reference_board_intents: []
  decisions: []
  approved_direction: null
  approved_visual_ref: null
  approved_preview_sha256: null
  approved_manifest_sha256: null
  approved_prompt_ref: null
  approved_prompt_sha256: null
  approved_handoff_ref: null
  approved_handoff_sha256: null
  approved_handoff_contract_ids: []
---

# Design Brief

This file stores confirmed design decisions, not a conversation transcript.
After each answer that changes the current concept or handoff, patch only
the affected frontmatter fields or sections through a fresh
`specify-runtime artifact patch` lease.

## Taste Intake

Fill these before authoring the current concept for visual `create` or
project-wide `refine`. `no-ui` exits skip this section. Seeds and presets are
inspiration only; they never substitute for `design approve`.

- Design read (one line: kind / audience / vibe / foundation lean):
- Dials (1-10): variance / motion / density
- Dial inference reason:
- Aesthetic family:
- Foundation strategy (`owned-tokens` | `real-ds:<name>` | `live-product-extension`):
- Redesign mode (`greenfield` | `preserve` | `overhaul` | n/a):
- Anti-slop locks (project-specific subset of the surface-aware policy):
- Reference-board intents when synthesizing (`mood` | `layout` | `type` | `color-only`):

## UI Professional Skill Route

Resolve this route from the compact catalog before visual authoring. Keep one
domain, at most one style, and at most two specialists; `loaded_refs` lists only
those exact progressively disclosed references. Existing approved references
and registered design truth always take precedence over routed style guidance.
For Web UI, `mature_web_ui_resource_ids` is a compact, stack-compatible
shortlist. Follow `web-component-selection.md`: prefer inspected live
components, then one mature primary system and only exact headless/specialist
gaps; retrieve official Agent material only for selected candidates. Run the
bounded project-root scan first, preserve its `web_ui_asset_inventory`, use the
compact `mature_web_ui_selection` reason codes, and treat an unscanned result as
provisional.
Retain its deterministic component adoption/permission plan. Refresh only
selected official material through the offline helper, persist hash/drift
results, and treat drift as a selection-review trigger rather than install or
upgrade authority.

For local work in an existing product, resolve `style_authority.mode` to
`inherit-existing`, keep `style_skill_id: null`, and load only the domain plus
applicable specialists. A style skill is eligible only for greenfield work or
an explicitly authorized full-page overhaul.

## Style Authority And Delivery Context

- Existing UI is the default visual authority. Feature-partial work and an
  ordinary functional-page create/refactor use `inherit-existing`, cite live
  token/component/surface evidence in `source_refs`, protect `global-shell` and
  `shared-components`, and leave `allowed_style_delta_surfaces` empty.
- `page-overhaul-authorized` requires an explicit user authorization source and
  may change style only on the exact full-page surface listed in
  `allowed_style_delta_surfaces`; global shell and shared components stay
  protected.
- Persist whether this round is standalone or `post-specify`. A post-Specify
  round pins the exact feature consumer and source spec bytes and returns to
  Plan when design does not change requirement, scope, or acceptance truth.

## UI Evidence And System Model

Fill when reverse-engineering screenshots, live UI, or design exports. Skip for
pure greenfield taste-only create until sources exist.

Evidence uses Design Evidence v1 (`measured` | `inferred` | `assumption`;
prose alias `evidence-backed-inference` → `inferred`). Non-measured claims need
rationale; inferred claims need `source` or explicit `source_gap`. Durable JSON
belongs under `.specify/design/evidence/` and must validate with
`validate_design_evidence` — prompt labels are subordinate to the schema.

- Evidence sources (paths/URLs/screenshots):
- Surface / page map:
- Token inventory (value + type + source/source_gap + rationale if not measured):
- Component inventory (name + anatomy + type + rationale):
- State matrix (hover/focus/loading/empty/error/populated/permission/offline/… coverage):
- Responsive rules (desktop/tablet/mobile or content breakpoints, stretch, overflow, resize thresholds):
- Behavior / keyboard notes (mouse/pointer, keyboard, focus order, touch, shortcuts, async feedback):
- Open assumptions that must not become silent approved truth:

## Professional Contract Intake

Before concept authoring, identify the rows the approved concept must
later freeze under `design_change.verification`: `surface_catalog`,
`scenario_matrix`, `interaction_matrix`, `editing_matrix`, `data_state_matrix`,
`accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, and `usability_validation`.
For Web UI, place the routed `smoothness_acceptance_ids` and performance budgets in
`usability_validation` and bind each ID to the existing interaction, motion,
structure, visual, runtime, or human-review path that proves it.
For every applicable input path, identify the platform event sequence,
pre-completion feedback, focus continuity, repeat policy, cancellation, and
pending behavior that the eventual `interaction_matrix` must freeze.

- Surfaces and scenarios: assign stable surface IDs, then define bounded
  risk-based or pairwise scenarios that reference the exact behavior/state rows
  exercised together. Give each scenario an executable `interaction_script`
  with preconditions, a selected start-state ID, ordered
  input/action/expected-feedback steps, and bounded branches whose target IDs
  are selected data states. Cover applicable success, failure, timeout, cancel,
  retry, duplicate, and out-of-order outcomes with explicit focus,
  announcement, continuation, completion, and recovery. Cover every row
  without an unbounded Cartesian product.

- Accessibility: WCAG 2.2 AA/platform equivalent; Name/Role/Value; semantic,
  reading, and focus order; keyboard and drag alternatives; dynamic status;
  target sizes; contrast; 400% zoom/reflow; forced colors; image/icon fallback.
- Navigation: surface hierarchy, entry/destination, primary task, back/close,
  deep-link behavior, interruption recovery, consistent landmarks.
- Content: CTA, empty/loading/error/permission/destructive/confirmation/undo,
  privacy/trust; long text, truncation, RTL, localization, dates, numbers, and
  time zones.
- Components: `component_contracts` variants, `content_constraints`,
  `semantic_token_refs`, reuse/extend/new `governance`, gap/deprecation owner,
  iconography source/style/optical rules, and the selected live or mature
  component source. A Web `new` primitive requires a recorded uncovered gap.
- Motion: purpose, trigger/response, duration/easing, interrupt/cancel,
  reduced-motion behavior, and perceived-performance feedback thresholds.
- Usability: risk, target users, critical tasks, success criteria, method, and
  human-review requirement. Automated tests and screenshots cannot substitute
  for target-user validation.

Use risk-based or pairwise combinations, not an unbounded Cartesian product,
while preserving every high-severity failure and recovery path.

## Confirmed Experience

- Product subject:
- Primary audience:
- Single user job:
- Visual thesis:
- Content thesis:
- Interaction thesis:
- Signature element:

## Concept Baseline

Keep these stable across review rounds so feedback improves one coherent
direction rather than switching the product, content, or approval boundary:

- Component inventory:
- Required states:
- Required interaction paths:
- Required data scenarios:
- Representative information density:
- Review viewports:
- Real or representative content:
- Surface modules:
- Color mode used for current-concept review:
- Additional modes to validate after selection:

## Current Concept Contract

Record the one current concept. A new round may revise these values only when
the feedback history names the reason; preserve accepted parts of the same
direction.

| Concept ID | Variance | Motion | Density | Visual | Content | Interaction | Signature | Gain | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| direction-main |  |  |  |  |  |  |  |  |  |

## Dialogue And Iteration State

- Active question: keep exactly one question `open`, `answered`, or `none`.
  A request for clarification leaves it open.
- Feedback history: one compact record per reviewed round with `round`,
  `preserve`, `change`, `question`, and `out_of_scope` values.
- Prototype rounds: record the immutable path, status (`draft` | `reviewed` |
  `approved`), medium (`image-primary` | `html-primary`), exact prompt ref when
  image-generated, inspected targets, inspection owner, and source feedback
  round. Never overwrite a reviewed round.

## Visual Collaboration Route

Probe the current live capability surface at entry and resume; do not hard-code
an Agent or integration. Record `image_generation`, `image_inspection`, and
`image_editing` independently as `available` or `unavailable` with compact tool
evidence. Use `image-primary` whenever image generation is available and
`html-primary` otherwise.

- Generation + inspection: `inspection_owner: agent-and-user`; inspect actual
  pixels before presentation.
- Generation without inspection: keep `image-primary`, set
  `inspection_owner: user`, and make no visual-quality claim.
- No generation + inspection: use `html-primary`, inspect real browser captures,
  and set `inspection_owner: agent-and-user`.
- No generation or inspection: use `html-primary`, set `inspection_owner: user`,
  provide the stable deep link, and make no visual-quality claim.
- Image prompt strategy: `image-generation`; preserve the exact generate/edit
  prompt through the design CLI for the numbered round.
- HTML prompt strategy: `html-authoring`; do not reuse an image-generation
  prompt as DOM/CSS instructions.

## Motion Contract

- `motion_contract.purpose`:
- Transitions (`id`, `surface`, `trigger`, `response`, `duration_ms`, `easing`,
  `interrupt_behavior`, `decision_ids`):
- `reduced_motion`:
- `feedback_timing.immediate_ms`:
- `feedback_timing.progress_ms`:
- `feedback_timing.timeout_ms`:

## References And Fidelity

| Reference | Use intent | Fidelity | Must preserve | Must not copy |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Decision Boundaries

- Must preserve:
- May adapt:
- Must not:

## Open Design Questions

Keep only unresolved questions that can materially change the current concept,
approval scope, or downstream implementation.

Use one record per unresolved or inferred decision:

| Decision ID | Status | Source | Rationale | Affects | Acceptance method |
| --- | --- | --- | --- | --- | --- |
| DS-... | confirmed / assumed / open / not-applicable |  |  |  |  |

## Approval

- Status: unapproved
- Review round:
- Direction ID:
- Exact visual ref:
- Preview SHA-256:
- Manifest SHA-256:
- Immutable image-generation prompt ref (image-primary only):
- Image-generation prompt SHA-256 (image-primary only):
- Immutable handoff ref:
- Handoff SHA-256:
- Approved decision IDs:
- Approved handoff contract IDs:
- User-requested revisions:
