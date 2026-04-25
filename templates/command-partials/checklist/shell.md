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

## Output Contract

- Produce a tailored checklist that can be used to review the current requirement or planning artifact set.
- Make the checklist specific enough that reviewers can tell what is missing or underspecified.
- Keep it scoped to requirement quality rather than implementation behavior.

## Guardrails

- Do not turn the checklist into a code test plan.
- Do not ask redundant questions the current artifacts already answer clearly.
- Do not hallucinate risk domains that are not supported by the current request or artifacts.
