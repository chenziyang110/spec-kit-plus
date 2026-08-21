{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a focused checklist that validates the quality, clarity, completeness, and review readiness of the current written requirements.

## Context

- Primary inputs: the user's requested checklist focus plus the current feature artifacts and any clarifying answers.
- The checklist is for requirements quality, not for verifying a working implementation.
- Audience and rigor level materially affect the resulting checklist and should be clarified when necessary.

## Process

- Load the current feature context and derive the likely checklist focus.
- Ask only the minimum clarification questions needed to shape the checklist.
- Generate the checklist around the relevant requirement-quality dimensions and review scenario.
- For UI-bearing requirements, check whether the written contract names
  applicable pointer/mouse, keyboard/focus, touch/shortcut/command events and
  feedback; empty and populated data plus degraded/recovery states; continuous
  resize/stretch/reflow/overflow; and preservation of focus, selection, scroll,
  overlays, and unsaved input. Check risk-based combinations without turning
  the requirements checklist into an executable test plan.

## Output Contract

- Produce a tailored checklist that can be used to review the current requirement or planning artifact set.
- Make the checklist specific enough that reviewers can tell what is missing or underspecified.
- Keep it scoped to requirement quality rather than implementation behavior.

## Guardrails

- Do not turn the checklist into a code test plan.
- Do not ask redundant questions the current artifacts already answer clearly.
- Do not hallucinate risk domains that are not supported by the current request or artifacts.

## Professional UI Contract Continuity

For UI-bearing requirements, Checklist asks whether every applicable
`surface_catalog`, `scenario_matrix`, `interaction_matrix`,
`editing_matrix`, `data_state_matrix`, `accessibility_matrix`, `navigation_matrix`,
`content_matrix`, `motion_contract`, and `usability_validation` obligation is
specific, measurable, and traceable,
including component governance. Use risk-based prioritization, not an unbounded
Cartesian product; never imply automated tests/screenshots replace target-user
human review.
