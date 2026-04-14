# Research Summary: v1.3 Implement Orchestrator Runtime

## Stack Additions

- Reuse the existing orchestration core and extend it with scheduler and worker-result models.
- Keep Markdown and `.planning/` artifacts as the durable coordination layer.
- Add focused runtime tests for milestone scheduling, worker delegation, and convergence.

## Feature Table Stakes

- Milestone-wide execution, not single-phase execution.
- Leader-only orchestration with worker-only concrete execution.
- Safe sequential and parallel batch dispatch with join points.
- Mixed failure handling with explicit blocker reporting.

## Watch Out For

- "Single-agent" must still mean a worker path, not leader self-execution.
- Cross-phase warm-up must stay bounded and auditable.
- Shipped template, generated skill, orchestration code, and regression coverage must move together.
