# Research: Feature Shape for v1.3 Implement Orchestrator Runtime

## Table Stakes

### Milestone Orchestration

- `sp-implement` can read the active roadmap and continue across all remaining phases by default.
- The runtime can determine the next executable work without requiring the user to relaunch for each phase.
- Phase completion advances state and unlocks later work automatically.

### Leader/Worker Separation

- The leader handles scheduling, dispatch, reconciliation, and status updates only.
- Concrete implementation, verification, and other task execution happens in worker agents.
- Sequential tasks still use workers; "single-agent" should mean one worker lane, not leader self-execution.

### Batch Coordination

- Parallel batches are dispatched only when write sets and shared surfaces are safe.
- Join points remain explicit and block downstream work until required worker results converge.
- Non-parallel work keeps deterministic execution order.

### Failure Handling

- Non-critical worker failures do not stop unrelated safe work.
- Critical-path failures and repeated failures halt with an actionable report.
- Deferred or failed work remains visible in state artifacts.

## Differentiators

- Safe cross-phase preparation work when dependencies allow, while preserving roadmap order as the default rule.
- Milestone-level progress reporting that reflects worker outcomes and blocker state in planning artifacts.
- Strong truthfulness about what the leader actually did versus what workers completed.

## Anti-Features

- A leader that still edits files or runs the core implementation tasks itself.
- Hidden phase skipping that makes roadmap order meaningless.
- Silent retries that hide instability or mutate phase state without an auditable trail.
