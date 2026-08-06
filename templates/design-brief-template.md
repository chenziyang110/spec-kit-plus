---
design_brief:
  schema: spec-kit-design-brief-v1
  status: draft
  task_type: null
  input_strategy: null
  route_reason: null
  review_round: 0
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
  approved_handoff_ref: null
  approved_handoff_sha256: null
  approved_handoff_contract_ids: []
---

# Design Brief

This file stores confirmed design decisions, not a conversation transcript.
After each answer that changes the direction comparison or handoff, patch only
the affected frontmatter fields or sections through a fresh
`specify-runtime artifact patch` lease.

## Taste Intake

Fill these before authoring three-direction previews for visual `create` or
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

## Confirmed Experience

- Product subject:
- Primary audience:
- Single user job:
- Visual thesis:
- Content thesis:
- Interaction thesis:
- Signature element:

## Comparison Baseline

Keep these identical across all three directions so the user compares the
design system rather than unrelated content:

- Component inventory:
- Required states:
- Representative information density:
- Review viewports:
- Real or representative content:
- Surface modules:
- Color mode used for direction comparison:
- Additional modes to validate after selection:

## Direction Axes

Keep the task and evidence baseline stable, but force meaningful divergence in
dial vectors and signature. Shared specimen content stays constant. For each
direction record:

| Direction | Variance | Motion | Density | Visual | Content | Interaction | Signature | Gain | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A |  |  |  |  |  |  |  |  |  |
| B |  |  |  |  |  |  |  |  |  |
| C |  |  |  |  |  |  |  |  |  |

Undifferentiated boards (identical dial triples or duplicate signatures) fail
ready-level `design preview-lint`.

## Motion Contract

- Purposeful motion moments:
- Duration scale:
- Easing:
- Spatial behavior:
- Loading or progress behavior:
- Reduced-motion equivalent:

## References And Fidelity

| Reference | Use intent | Fidelity | Must preserve | Must not copy |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Decision Boundaries

- Must preserve:
- May adapt:
- Must not:

## Open Design Questions

Keep only unresolved questions that can materially change the three directions,
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
- Immutable handoff ref:
- Handoff SHA-256:
- Approved decision IDs:
- Approved handoff contract IDs:
- User-requested revisions:
