# Constitution Style Standard and Discussion UI Stage Design

## Purpose

Add two lightweight workflow improvements:

1. Generated project constitutions should tell agents to follow the current
   project's established style, structure, helper APIs, and architecture
   boundaries before inventing a different approach. This applies to every
   built-in constitution profile: `product`, `library`, `minimal`, and
   `regulated`.
2. `sp-discussion` should offer an optional UI and interaction discussion stage
   after product/functionality requirements are stable when the request has a
   user-interface surface.

Both changes improve downstream implementation quality without turning ordinary
discussion or constitution updates into a heavier process.

## Goals

- Preserve project-local engineering consistency as a default constitution rule.
- Require agents to ask the user before applying architecture changes that go
  beyond the existing project pattern.
- Let `sp-discussion` recognize UI-facing requirements and offer a dedicated
  optional UI/interaction pass before handoff.
- Frame the optional UI pass as senior natural-language guidance from a UI and
  interaction designer with deep delivery experience.
- Allow ASCII sketches as optional text artifacts that clarify layout or flow for
  downstream agents.
- Preserve existing handoff behavior: `sp-discussion` must not invoke
  `sp-specify` automatically and must still require explicit handoff request,
  self-review, and user confirmation.

## Non-Goals

- Do not add a new `sp-ui-discussion` command.
- Do not require visual mockups, image generation, browser previews, or design
  files.
- Do not make UI discussion a blocking gate for every feature.
- Do not introduce separate candidate handoff files or split planning artifacts.
- Do not weaken existing `sp-discussion` boundary, evidence, or handoff rules.

## Current Context

The constitution surface is generated from the built-in constitution template
and profiles. The product profile already includes a "Reuse Existing Patterns"
principle under simplicity, but it does not explicitly instruct agents to study
and preserve the current project's code style, structure, helper APIs, and
architecture boundaries before coding.

`sp-discussion` already operates as a staged pre-specification workflow:
context intake, product framing, context grounding, question loop, technical
options, handoff assessment, handoff draft, self-review, user review, and
handoff-ready. UI requirements currently fit inside product framing or technical
options, but there is no explicit optional stage where the agent behaves like a
senior UI and interaction design partner.

## Design

### Constitution Engineering Standard

Add a concise engineering standard to all built-in constitution profiles:
`product`, `library`, `minimal`, and `regulated`.

- Before implementing, agents should inspect and follow the current project's
  established style, file organization, naming conventions, helper APIs,
  framework patterns, and architecture boundaries.
- Agents should extend existing modules and patterns when they satisfy the
  requirement.
- When the agent believes a larger architecture improvement is warranted, it
  should present the recommendation, trade-offs, and expected impact to the user
  before making the change.

The rule should live in the constitution profile layer so newly initialized
projects inherit it regardless of the selected built-in profile. Existing tests
that assert constitution profile content should be updated so this behavior
cannot drift.

### Optional UI and Interaction Stage

Add `ui-interaction-discussion` as an optional `sp-discussion` stage between
stable product/functionality discussion and handoff assessment.

The stage is triggered when the matured requirement includes UI-facing scope,
including screens, components, layout, navigation, visual hierarchy, interaction
states, user-facing copy, accessibility, or workflow feedback. The agent should
offer the stage after the functional discussion is stable:

- If the user accepts, continue with focused UI/interaction questions and
  guidance.
- If the user skips, record that UI details are deferred or not locked, then
  continue toward handoff when the other handoff gates are satisfied.

The stage is optional by design. A skipped UI pass is not a blocker unless the
feature itself cannot be specified without UI decisions.

### UI Discussion Persona and Behavior

During `ui-interaction-discussion`, the agent should act as a senior UI and
interaction designer with 15 years of practical project experience. The agent
should guide the user through choices that downstream implementers can turn into
requirements:

- primary screens or surfaces
- user journey and task flow
- information architecture and hierarchy
- component responsibilities
- key interaction details
- loading, empty, success, warning, error, disabled, and permission states
- validation and feedback behavior
- responsive or density expectations when relevant
- accessibility and keyboard/focus expectations when relevant
- user-facing copy tone and placement when it affects interaction quality
- acceptance signals for the intended UI behavior

The agent should remain natural-language-first. It should ask only high-impact
questions and offer opinionated recommendations when the user benefits from UI
expert judgment.

### ASCII Sketches

ASCII sketches are allowed as optional supporting guidance. They can show rough
screen structure, layout grouping, state transitions, or flow relationships.

Example uses:

```text
+--------------------------------------------------+
| Header: Project name                 Primary CTA |
+--------------------+-----------------------------+
| Navigation         | Main task panel             |
| - Overview         |                             |
| - Activity         | Empty / loading / error     |
| - Settings         | states described below      |
+--------------------+-----------------------------+
```

ASCII sketches are not binding pixel specifications. They should be treated as
communication aids that preserve intent for `sp-specify`, `sp-plan`, designers,
or implementation agents.

### Artifacts and Handoff

The change should reuse the existing discussion package instead of adding a new
required file:

- `discussion-state.md` records `ui_discussion_status` with one of:
  `not_applicable`, `offered`, `accepted`, `skipped`, `completed`, or
  `deferred`.
- `requirements.md` captures confirmed UI requirements when they affect product
  behavior.
- `technical-options.md` captures UI implementation options only when strategy
  materially affects requirements.
- `open-questions.md` records unresolved UI decisions that must not be silently
  invented later.
- `handoff-to-specify.md` is the primary carrier for any ASCII sketches because
  Markdown preserves multi-line readability.
- `handoff-to-specify.json` preserves structured UI status and references
  instead of duplicating raw multi-line sketches. Use fields such as
  `ui_discussion_status`, `ui_sketches_present`, `ui_sketch_summary`, and
  `ui_sketch_reference` to point back to the Markdown section.

The unified handoff remains the only handoff package. The UI stage must not
create candidate-specific handoffs or route automatically to `sp-specify`.

## Testing and Verification

Implementation should update targeted regression tests around:

- built-in constitution profile/default content containing the new project-style
  engineering standard
- `sp-discussion` command/template content describing the optional
  `ui-interaction-discussion` stage
- generated integration command content preserving the discussion contract
- any state-template or handoff assertions touched by the new UI status fields

Full verification can remain focused on existing template alignment and
integration rendering tests affected by these files.

## Risks and Mitigations

- Risk: UI discussion becomes another mandatory heavy gate.
  Mitigation: document it as optional and explicitly allow skipping.
- Risk: ASCII sketches are mistaken for pixel-perfect design specs.
  Mitigation: label them as rough text guidance only.
- Risk: UI details vanish between discussion and specification.
  Mitigation: preserve confirmed UI decisions and deferred UI unknowns in the
  existing unified handoff pair.
- Risk: the constitution standard encourages unrelated refactors.
  Mitigation: require user confirmation before architecture improvements that
  depart from the current project pattern.

## Acceptance Criteria

- New initialized projects using any built-in constitution profile receive
  constitution guidance to follow current project style and structure before
  inventing new architecture.
- Generated discussion workflow guidance offers an optional UI/interaction stage
  for UI-facing requirements after functional discussion stabilizes.
- The UI stage uses a senior UI/interaction design persona and remains
  natural-language-first.
- ASCII sketches are permitted as optional explanatory text.
- Skipping UI discussion is recorded as a deferred decision, not treated as a
  failed handoff gate.
- Existing `sp-discussion` handoff rules remain intact.
