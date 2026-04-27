# Research: Architecture for v1.3 Implement Orchestrator Runtime

## Integration Points

- `templates/commands/implement.md` defines the generic implement contract and must be updated so leader-only execution is the baseline behavior.
- `.agents/skills/sp-implement/SKILL.md` mirrors the shipped Codex surface and must stay aligned with the shared template.
- `src/specify_cli/orchestration/policy.py` remains responsible for strategy choice, but not end-to-end milestone scheduling.
- `src/specify_cli/orchestration/models.py` is the natural home for additional scheduler/session/result models.
- `src/specify_cli/orchestration/state_store.py` and related event surfaces are likely candidates for persisted execution progress.

## New or Changed Components

- Milestone scheduler: chooses the next executable phase or batch and enforces default roadmap order.
- Worker dispatch contract: describes how sequential and parallel work is delegated without leader execution.
- Result convergence layer: consumes worker outcomes, updates state, and decides whether join points are satisfied.
- Failure policy layer: classifies retryable vs blocking failures and decides when unrelated work can continue.

## Data Flow

1. Leader loads roadmap, tasks, and current state.
2. Leader computes the next ready phase and batch.
3. Leader uses shared policy to pick `single-lane`, `native-multi-agent`, or `sidecar-runtime` for that batch.
4. Leader dispatches one or more workers.
5. Workers execute and report structured outcomes.
6. Leader reconciles results, updates planning artifacts, and either advances, retries, or halts.

## Suggested Build Order

1. Define scheduler and leader/worker runtime contract.
2. Add result convergence and failure classification.
3. Integrate planning artifact updates and shipped surface alignment.
