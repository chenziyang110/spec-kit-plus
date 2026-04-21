# Research: Stack for v1.3 Implement Orchestrator Runtime

## Existing Baseline

- Python CLI code lives under `src/specify_cli/`.
- Shared orchestration primitives already exist in `src/specify_cli/orchestration/`.
- `sp-implement` behavior is primarily shipped through `templates/commands/implement.md` and the generated Codex mirror at `.agents/skills/sp-implement/SKILL.md`.
- Regression coverage already exists around implement routing in `tests/orchestration/`, `tests/codex_team/`, and `tests/test_alignment_templates.py`.

## Recommended Stack Additions

- Reuse the existing orchestration models and state store for leader-session state instead of introducing a new runtime package.
- Add explicit scheduler and worker-result abstractions under `src/specify_cli/orchestration/` so milestone execution logic is separate from policy selection.
- Keep execution planning artifacts in Markdown and existing `.planning/` state files rather than introducing a database or external queue.
- Extend current tests with milestone-scheduler and worker-dispatch coverage rather than relying only on prompt/template assertions.

## What Not To Add

- No external durable queue, broker, or service process for this milestone.
- No new strategy vocabulary replacing `single-agent`, `native-multi-agent`, or `sidecar-runtime`.
- No integration-specific runtime abstraction that bypasses the shared orchestration core.

## Integration Notes

- `CapabilitySnapshot` and `ExecutionDecision` already model the current strategy contract and should remain source-of-truth inputs to the leader.
- Codex-specific escalation language should remain a post-processing layer, not the place where milestone scheduler truth lives.
- The scheduler will likely need task-batch and phase-state models that sit above `choose_execution_strategy(...)`.
