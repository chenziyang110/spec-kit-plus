{{spec-kit-include: ../common/user-input.md}}

## Objective

Translate the approved specification package into explicit implementation design artifacts, research findings, and execution guidance that can safely feed task generation.

## Context

- Primary inputs: `spec.md`, `alignment.md`, `context.md`, `references.md`, the project handbook/project-map set, and passive learning files.
- Working state lives in the active `FEATURE_DIR`, especially `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, and `workflow-state.md`.
- This command is design-only. Planning does not grant permission to start execution.

## Process

- Recover the active feature context and validate that the specification package is ready for planning.
- Refresh or inspect repository navigation artifacts until task-relevant coverage is sufficient.
- Research, model, and document the implementation approach with explicit constraints and guardrails.
- Validate the resulting plan package before handing off to task generation.

## Output Contract

- Write the implementation plan artifact set needed by `/sp-tasks`.
- Surface risks, unresolved decisions, and planning-time constitution/guardrail requirements explicitly.
- Keep the resulting artifact set consistent enough that task generation does not need to rediscover obvious design decisions.

## Guardrails

- Do not implement code, edit tests, or start execution from `sp-plan`.
- Do not leave locked planning decisions implicit or scattered only in prose.
- Do not trust stale navigation coverage when handbook/project-map context should be the source of truth.
