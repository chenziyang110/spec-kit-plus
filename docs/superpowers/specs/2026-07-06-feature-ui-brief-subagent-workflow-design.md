# Feature UI Brief Subagent Workflow Design

**Date:** 2026-07-06
**Status:** Proposed
**Owner:** Codex

## Summary

Extend the UI design workflow so concrete feature UI intent can move from user
references into worker implementation packets with less drift.

The previous UI design workflow makes `DESIGN.md` the project-wide design-system
contract. This design adds a feature-scoped UI contract layer:

- `sp-specify` detects UI reference inputs in feature requests.
- `sp-specify` asks how the reference should be used, defaulting to approximate
  recreation.
- UI reference processing is done by subagents, not by the `sp-specify` leader.
- Subagents write `FEATURE_DIR/ui-reference-notes.md` and
  `FEATURE_DIR/ui-brief.md`.
- Optional `FEATURE_DIR/ui-target.html` is a low-dependency visual target, not
  production source.
- `sp-plan`, `sp-tasks`, and `sp-implement` carry the UI contract into worker
  packets and verification evidence.
- UI verification uses a ladder: agent self-verification first, vision-capable
  agent review when available, and human review when visual fidelity cannot be
  proven by the agent environment.

The guiding rule is:

> `DESIGN.md` defines product style; `ui-brief.md` defines what this feature's UI
> must preserve.

## Problem Statement

The root `DESIGN.md` tells agents what the product should feel like, which tokens
to use, and which UI patterns to avoid. It does not fully preserve a user's
specific UI intent for a feature.

Users may provide:

- screenshots
- HTML/CSS mockups
- Tailwind, shadcn, React, Vue, Svelte, or other UI framework code
- Figma exports or design notes
- existing product pages or public reference pages
- natural-language instructions such as "make it basically like this"

If those inputs are passed to implementation workers as informal context, the
result can drift: a table becomes cards, a dense workbench becomes a marketing
layout, key states disappear, or an HTML mockup gets copied into an incompatible
production stack.

Spec Kit Plus needs a workflow contract that turns UI references into explicit,
worker-ready UI obligations.

## Goals

- Preserve feature-specific UI intent through specification, planning, tasks, and
  implementation.
- Default UI reference handling to approximate recreation while supporting high
  fidelity and inspiration-only modes.
- Require subagent processing for UI reference inputs during `sp-specify`.
- Create stable artifact formats for `ui-reference-notes.md`, `ui-brief.md`, and
  optional `ui-target.html`.
- Prevent `ui-target.html` from becoming production source or from introducing
  heavy dependencies that reduce implementation fidelity.
- Make worker packets carry concrete UI requirements instead of vague reference
  language.
- Prefer agent verification, but require human review when the environment cannot
  prove visual fidelity.

## Non-Goals

- Do not promise pixel-perfect or lossless UI transfer.
- Do not add a new `sp-ui` or `sp-ui-brief` workflow in this version.
- Do not move project-wide design-system ownership out of `sp-design`.
- Do not make every small text-only UI request require subagents.
- Do not require visual diff tooling in v1 of this feature.
- Do not copy third-party source code, protected brand expression, or proprietary
  design assets into generated project artifacts.

## Workflow Ownership

`sp-design` remains responsible for project-wide `DESIGN.md` creation, synthesis,
refinement, and audit.

`sp-specify` owns feature-scoped UI reference intake. It creates the feature UI
contract when a feature request includes concrete UI references or asks for a
specific UI to be reproduced.

No separate `sp-ui` workflow is introduced. The user should not need to learn a
new entrypoint just to specify a feature that includes a UI reference.

## UI Reference Input Detection

`sp-specify` must enter a UI reference processing lane when a feature request
includes any of the following:

- an uploaded or linked screenshot
- HTML, CSS, Tailwind, shadcn, React, Vue, Svelte, or similar UI code supplied as
  a reference or design draft
- a Figma export, image, product page, or reference URL
- language such as "same as this", "basically like this", "copy this layout",
  "use this as the design", "match this screen", or "restore this exact UI"
- a high-visibility UI surface where the user gives layout, density, hierarchy,
  or interaction requirements that should not be reinterpreted by workers

Pure text requests without a specific reference may still create UI requirements,
but they do not require the UI reference subagent lane unless the surface is
high-risk or the user asks for a concrete visual target.

## Fidelity Modes

When UI reference input exists, `sp-specify` asks the user how the reference
should be used. If the user does not choose explicitly, the default is
`approximate`.

### approximate

Default. Preserve layout, density, information hierarchy, visible data volume,
visual rhythm, primary components, and major interaction structure. Use the
project's actual technology stack, components, and `DESIGN.md` rules. Allow
minor differences in font rendering, icons, exact copy, minor spacing, and
framework-specific markup.

### high

Aim for a close visual match. Require stronger visual evidence, reference versus
implementation comparison, and a documented deviation list. High fidelity still
does not permit copying third-party code or protected brand expression.

### inspiration

Extract design principles only. Do not pursue a similar-looking result. Use this
for third-party references, brand-heavy inspiration, or cases where the user only
wants a general feel.

## Subagent Requirement

When UI reference input is present, `sp-specify` leader must not directly parse
the design reference and write the UI contract itself.

The leader is responsible for:

1. detecting UI reference input
2. asking or recording the fidelity mode
3. dispatching one or more bounded UI reference subagents
4. checking the produced artifacts for completeness and scope safety
5. carrying `ui-brief.md` into downstream specification artifacts

The UI reference subagent is responsible for:

1. reading the UI reference inputs
2. extracting visual, layout, density, component, state, interaction, and
   responsive facts
3. classifying ownership and reuse constraints
4. writing `ui-reference-notes.md`
5. writing `ui-brief.md`
6. creating `ui-target.html` only when a visual target is materially useful

For complex inputs, `sp-specify` may dispatch separate subagents for screenshot
analysis, code/HTML analysis, and UI brief compilation. The default can be one
subagent when the input is small enough.

## Writable UI Reference Lane

This feature cannot reuse the existing read-only evidence lane as-is. Current
`sp-specify` delegated lanes are read-only evidence or review lanes, and they
forbid file writes. This design requires a new or extended writable UI reference
lane with a deliberately narrow write scope.

The lane should be represented explicitly in orchestration policy and generated
workflow guidance, for example as `lane_mode: ui-reference-artifact`.

Allowed operations:

- file reads
- repository search
- project cognition reads
- memory and docs reads
- reference input reads
- writing only the assigned feature UI artifacts:
  - `FEATURE_DIR/ui-reference-notes.md`
  - `FEATURE_DIR/ui-brief.md`
  - `FEATURE_DIR/ui-target.html` when requested by the lane contract

Forbidden operations:

- source code writes
- test writes
- app styling or component implementation writes
- package manager commands
- builds
- app servers
- broad state writes outside the assigned feature artifacts
- handoff writes that claim downstream readiness without leader validation

The `sp-specify` leader owns lane dispatch, artifact validation, and final
specification package integration. The UI reference subagent owns analysis and
the assigned UI artifact writes. The implementation plan must update the shared
orchestration model and policy surfaces rather than describing this as another
read-only evidence lane.

If subagent capability is unavailable:

- `approximate` and `high` fidelity block by default or require explicit user
  approval for an inline fallback.
- `inspiration` may proceed inline with a recorded soft risk.
- The leader must not claim visual fidelity has been proven when no subagent or
  vision-capable verification was available.

## Artifact Model

### `FEATURE_DIR/ui-reference-notes.md`

Subagent-authored reference analysis. This file records what the references
contain, not what workers must implement.

Required sections:

- Reference Inputs
- Fidelity Mode
- Ownership And Reuse Constraints
- Visual Facts
- Layout Facts
- Density And Visible Data
- Component Facts
- State Facts
- Interaction Facts
- Responsive Facts
- Must Preserve Candidates
- Adaptation Candidates
- Risks And Gaps

### `FEATURE_DIR/ui-brief.md`

Subagent-authored worker-facing UI contract. This is the authoritative
feature-scoped UI source for downstream planning and task packets.

Required sections:

- Source Design System
- Reference Inputs
- Fidelity Contract
- Screen Structure
- Information Hierarchy
- Components And States
- Interactions
- Responsive Behavior
- Accessibility And Keyboard Requirements
- Must Preserve
- May Adapt
- Must Not
- Required Evidence
- Worker Contract

### `FEATURE_DIR/ui-target.html`

Optional. Use only when a visual target will reduce ambiguity for complex UI,
high fidelity requests, or user-provided HTML/code references.

`ui-target.html` is a disposable visual target. It is not production code and it
must not introduce implementation dependencies.

Allowed by default:

- single-file HTML
- native HTML and CSS
- small vanilla JavaScript only when necessary for state demonstration
- inline CSS
- inline SVG icons only when necessary
- fixed demo data
- explicit viewport markers
- explicit state sections
- no build step
- no package manager
- no remote runtime dependency

Disallowed by default:

- React, Vue, Svelte, or similar runtimes
- Tailwind CDN
- Bootstrap, shadcn, or component library CDN
- charting libraries
- animation libraries
- icon libraries
- remote fonts
- external CSS or JavaScript
- generated image URLs
- canvas or WebGL unless the target UI itself is canvas or WebGL

Required structure:

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>UI Target - Feature Name</title>
  <style>
    /* Local CSS only. No external dependencies. */
  </style>
</head>
<body>
  <main data-ui-target="feature-name" data-fidelity="approximate">
    <section data-viewport="desktop-1440">
      <!-- target composition -->
    </section>

    <section data-viewport="mobile-390">
      <!-- target composition -->
    </section>

    <section data-state="empty">
      <!-- empty state -->
    </section>

    <section data-state="error">
      <!-- error state -->
    </section>
  </main>
</body>
</html>
```

The success standard for `ui-target.html` is fidelity and implementability, not
visual flourish. For data-dense, workbench, admin, dashboard, table, terminal, or
operations UI, the target must preserve visible item count, table density,
control density, region proportions, and primary information priority.

## Reference-Implementation Mapping

Feature UI references must map onto the existing `Reference-Implementation`
scenario profile and `Fidelity Requirements` contract instead of creating a
parallel fidelity system.

`approximate` and `high` fidelity UI references activate the
`Reference-Implementation` profile for the feature UI surface. This applies even
when the reference is third-party or unknown, but the required fidelity must
exclude copied source, protected brand expression, proprietary naming, and
protected imagery. `inspiration` does not activate `Reference-Implementation` by
default; it remains a design-system and product-direction input unless another
non-UI reference implementation also triggers the profile.

When `Reference-Implementation` is activated by UI reference input, `sp-specify`
must populate the existing `Fidelity Requirements` section:

- **Reference Object:** list the UI reference inputs, `ui-reference-notes.md`,
  optional `ui-target.html`, ownership classification, and canonical evidence
  paths that define the UI reference.
- **Required Fidelity:** record the fidelity mode, must-preserve items,
  allowed-adaptation boundaries, must-not-copy constraints, and any user-approved
  deviations from the reference.
- **Reference Behavior Inventory:** enumerate layout regions, visible data
  density, component states, primary interactions, responsive behavior,
  accessibility or keyboard behavior, and error/loading/empty state behavior as
  preserve, redesign, or defer items.

`workflow-state.md` must carry profile-aware evidence terms when UI references
activate the profile. At minimum:

- `active_profile: Reference-Implementation`
- `required_sections` includes `Fidelity Requirements`
- `required_evidence` includes `reference_source_evidence`,
  `ui_fidelity_criteria`, `real_entrypoint_ui_evidence`,
  `visual_comparison_or_human_review`, and `deviation_log` for high fidelity

`sp-plan` and `sp-implement` already consume `Reference-Implementation` and
`required_evidence`; this design extends those existing fields with UI-specific
evidence names instead of inventing a separate completion channel.

## Workflow Propagation

### `sp-specify`

- Detect UI reference input.
- Ask for fidelity mode with approximate as the default.
- Dispatch UI reference subagent processing through the writable UI reference
  lane, not through the read-only evidence lane.
- Require `ui-reference-notes.md` for UI reference inputs.
- Require `ui-brief.md` when the feature includes a concrete UI surface.
- For `approximate` and `high` fidelity, activate the existing
  `Reference-Implementation` profile and populate `Fidelity Requirements`.
- Record UI brief paths in `spec.md`, `alignment.md`, `context.md`, and workflow
  state.
- Include UI reference processing status in closeout.

### `sp-plan`

- Read `ui-brief.md` when present.
- Treat `ui-brief.md` as a planning input alongside `DESIGN.md`.
- Add UI architecture constraints, implementation boundaries, and verification
  strategy to `plan.md`.
- Identify whether the UI requires screenshots, responsive checks,
  accessibility checks, terminal captures, or human visual review.

### `sp-tasks`

- Compile `ui-brief.md` into each affected worker packet.
- Include a `UI Implementation Contract` section in UI-bearing task packets.
- Do not pass raw "make it like this" language to workers without the compiled
  contract.

### `sp-implement`

- Require platform-appropriate UI evidence before marking UI tasks complete.
- Reject synthetic-only proof when the task packet requires real entrypoint UI
  evidence.
- Record the UI verification result as pass, failed, or pending human review.

## Worker Packet Contract

Each worker packet for UI-bearing work should include:

```md
## UI Implementation Contract

### Design Sources
- Root design system: DESIGN.md
- Feature UI brief: FEATURE_DIR/ui-brief.md
- Reference notes: FEATURE_DIR/ui-reference-notes.md
- Visual target: FEATURE_DIR/ui-target.html, if present

### Fidelity Level
- approximate | high | inspiration

### Must Preserve
- layout structure
- information hierarchy
- component density
- visible data volume
- primary interactions
- required responsive behavior

### May Adapt
- exact icons
- minor spacing
- copy
- implementation-specific component names
- framework-specific markup

### Must Not
- reinterpret the layout into a different pattern
- replace dense tables or workbench views with cards unless the brief allows it
- add decorative gradients, hero sections, or unrelated visual treatment
- copy third-party source code or protected brand expression
- treat ui-target.html as production source

### Required States
- loading
- empty
- error
- selected
- disabled
- permission-limited
- success or failure feedback

### Required Evidence
- desktop or primary-width screenshot
- mobile or narrow-width screenshot when responsive behavior is relevant
- key state screenshots or captures
- keyboard and focus check
- browser console check for web UI
- accessibility check when the surface is interactive
```

## UI Verification Ladder

Verification must prefer agent proof but must not invent confidence when the
environment lacks the required capability.

### Level 0: Contract validation

Check that `ui-reference-notes.md`, `ui-brief.md`, and optional
`ui-target.html` use the required formats. This does not require vision.

### Level 1: Runtime evidence validation

Run the relevant UI entrypoint, generate screenshots or terminal captures, and
check console output, overflow, focus behavior, accessibility basics, and
required state coverage. This may not require image understanding, but it must
produce reviewable evidence.

### Level 2: Agent visual comparison

When a vision-capable agent or tool is available, compare reference screenshots
or `ui-target.html` captures against implementation screenshots. Report:

- layout match
- density match
- information hierarchy match
- component and state coverage
- visible deviations
- severity and recommended fix

### Level 3: Human review

Use human review when:

- the environment has no reliable visual comparison capability
- agent visual comparison is unavailable, inconclusive, or failed
- approximate fidelity cannot be proven from automated evidence
- the design question is materially subjective
- the user explicitly asks to confirm visual similarity

The agent may close implementation as functionally complete with
`fidelity_status: pending-human-review`, but it must not claim the UI reference
was visually matched without agent visual comparison or human approval.

Closeout should record:

```yaml
ui_verification:
  contract_check: pass
  runtime_evidence: pass
  visual_comparison: pass | unavailable | needs-human-review | failed
  fidelity_status: pass | pending-human-review | failed
  reviewer: agent | vision-subagent | human
```

Mode-specific verification:

- `inspiration`: contract and runtime evidence may be enough; human review is
  optional unless requested.
- `approximate`: agent self-verification runs first. If no visual comparison is
  available, screenshots are required and fidelity remains pending human review.
- `high`: visual comparison is required. Use a vision-capable agent when
  available; otherwise human review is mandatory.

## Safety And Reuse Rules

Each UI reference must be classified as:

- `user-owned`
- `project-owned`
- `third-party`
- `unknown`

`user-owned` and `project-owned` references may be used for closer fidelity when
the user asks for it. `third-party` and `unknown` references may guide layout,
density, interaction, and general visual principles, but must not be copied as
source, brand expression, proprietary naming, imagery, or protected identity.

When ownership is unclear, default to `unknown` and avoid copying expression.

## Test Strategy

Implementation should add tests that prove:

- `sp-specify` guidance detects UI reference inputs and routes to a
  writable subagent-required UI reference lane.
- `sp-specify` asks for or records fidelity mode with `approximate` as default.
- orchestration models and policy distinguish the writable UI reference lane
  from read-only evidence lanes and restrict writes to assigned UI artifacts.
- generated `spec.md`, `alignment.md`, `context.md`, and workflow state can carry
  UI brief paths and UI reference processing status.
- approximate and high UI reference inputs activate `Reference-Implementation`
  and fill `Reference Object`, `Required Fidelity`, `Reference Behavior
  Inventory`, and UI-specific `required_evidence` terms.
- `sp-plan` templates read and preserve `ui-brief.md`.
- `sp-tasks` templates emit the `UI Implementation Contract`.
- `sp-implement` guidance requires UI evidence and records pending human review
  when visual comparison is unavailable.
- passive UI design guidance says UI reference input requires subagent handling.
- `ui-brief.md` and `ui-reference-notes.md` format requirements are present in
  templates or command guidance.
- `ui-target.html` guidance forbids external dependencies and production-source
  reuse by default.
- no command template suggests copying third-party UI code or protected brand
  expression.

## Acceptance Criteria

- A user can provide a screenshot, HTML mockup, or UI framework snippet during
  `sp-specify` and receive a feature-scoped `ui-brief.md`.
- The default reference mode is approximate recreation.
- Users can choose high fidelity or inspiration-only handling.
- UI reference processing is subagent-owned when subagents are available.
- UI reference subagents write only the assigned UI artifacts through a dedicated
  writable UI reference lane.
- If subagents are unavailable, approximate and high-fidelity processing block or
  require explicit inline fallback approval.
- Approximate and high fidelity UI references activate the existing
  `Reference-Implementation` profile and required evidence terms.
- Worker packets receive compiled UI contracts instead of raw reference language.
- Implementation closeout distinguishes functional completion from visual
  fidelity approval.
- Human review is requested when visual fidelity cannot be proven by the agent
  environment.

## Example Flow

User request:

```text
Add an order exception handling page. Use this screenshot as the design and keep
it basically the same.
```

Expected workflow:

1. `sp-specify` detects UI reference input.
2. `sp-specify` records default `fidelity: approximate` or asks the user to
   confirm another mode.
3. `sp-specify` dispatches a UI reference subagent.
4. The subagent writes `ui-reference-notes.md` and `ui-brief.md`.
5. `sp-specify` validates the artifacts and records them in the spec package.
6. `sp-plan` turns the UI brief into implementation and verification strategy.
7. `sp-tasks` compiles the UI brief into worker packets.
8. The worker implements the UI in the real project stack.
9. `sp-implement` captures screenshots and state evidence.
10. A vision-capable agent compares the result, or the workflow requests human
    review when visual comparison is unavailable.
