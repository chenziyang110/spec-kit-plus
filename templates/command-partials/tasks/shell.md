{{spec-kit-include: ../common/user-input.md}}

## Objective

Convert the plan package into dependency-aware execution tasks that preserve planning guardrails, expose parallel-safe batches, and make implementation resumable.

## Context

- Primary inputs: `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `context.md`, and the handbook/project-map set.
- Working state lives in `FEATURE_DIR/tasks.md` plus any decomposition metadata needed for later analysis or implementation routing.
- This command is task-generation-only. It should not cross into execution.

## Process

- Load the current plan package and recover the active workflow-state context.
- Carry locked planning decisions and implementation constitution rules forward into execution slices.
- Generate dependency ordering, parallel-safe batches, join points, and guardrail indexes.
- Validate the resulting task graph before handing off to analysis or implementation.

## Output Contract

- Write `tasks.md` as the authoritative execution breakdown for the current feature.
- Make execution ordering, parallelization boundaries, and required verification steps explicit.
- Preserve the guardrail information later subagent execution packets and leaders must consume.

## Guardrails

- Do not implement code, edit tests, or treat task generation as implicit execution approval.
- Do not emit raw task lists that lose boundary rules, locked decisions, or verification expectations.
- Do not assume stale or overly broad repository-map coverage is good enough for decomposition.
