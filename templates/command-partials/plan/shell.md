{{spec-kit-include: ../common/user-input.md}}

## Objective

Translate the approved specification package into explicit implementation design artifacts, research findings, and execution guidance that can safely feed task generation.

## Context

- Primary inputs: `spec.md`, `alignment.md`, `context.md`, `references.md`, the compiled brainstorming truth and any `plan-contract.json` contract, the task-local project cognition query bundle with readiness and returned `minimal_live_reads`, and passive learning files.
- Working state lives in the active `FEATURE_DIR`, especially `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `workflow-state.md`, `plan-contract.json`, `planning/handoffs/`, `planning/evidence-index.json`, and `planning/checkpoints.ndjson`.
- This command is design-only. Planning does not grant permission to start execution.

## Process

- Recover the active feature context and validate that the specification package is ready for planning.
- Validate `FEATURE_DIR/brainstorming/handoff-to-specify.json` before planning from a discussion handoff.
- Stop when `planning_gate_status` is not `ready`, `quality_gate.user_confirmed` is missing, `context_boundary` is incomplete, target project root is required but missing, hard unknowns remain open, or conflicts remain open.
- For cross-project implementation, plan from the target project context and record that current project cognition cannot prove target-project implementation facts.
- Use target cognition, minimal live reads in the target, user confirmation, or explicit assumptions for target evidence; do not ask the user to rebuild current-project cognition for target files.
- Refresh or inspect repository navigation artifacts until task-relevant coverage is sufficient.
- Research, model, and document the implementation approach with explicit constraints and guardrails.
- Design every carried `CA-###` consequence obligation into operational behavior, dependency impact, recovery/validation proof, and stop-and-reopen conditions before task handoff.
- Validate the resulting plan package before handing off to task generation.

## Output Contract

- Write the implementation plan artifact set needed by `/sp-tasks`.
- Write `plan-contract.json` so route, intent, complexity, must-preserve invariants, and allowed optimization scope survive as machine-readable truth.
- Persist planning lane evidence before synthesis: every delegated planning lane writes `planning/handoffs/<lane-id>.json`, the leader updates `planning/evidence-index.json`, and checkpoint records go to `planning/checkpoints.ndjson`.
- Consume every accepted planning handoff before final synthesis: each accepted handoff must be integrated into `plan.md`, `research.md`, `quickstart.md`, `data-model.md`, `contracts/`, or `plan-contract.json`, or explicitly recorded as deferred or blocked with a reason.
- Surface risks, unresolved decisions, and planning-time constitution/guardrail requirements explicitly.
- Keep the resulting artifact set consistent enough that task generation does not need to rediscover obvious design decisions.

## Guardrails

- Do not implement code, edit tests, or start execution from `sp-plan`.
- Do not leave locked planning decisions implicit or scattered only in prose.
- Do not trust stale navigation coverage as evidence; use the project cognition query bundle as advisory navigation and prove claims from live project facts.
- Use anchorable section headings (`## Section Name`) in all output artifacts so that downstream task generation can produce precise `file#section` context pointers.
