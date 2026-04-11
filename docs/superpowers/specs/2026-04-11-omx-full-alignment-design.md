# OMX Full Alignment Design

## Goal

Make `spec-kit-plus` fully align with the `oh-my-codex` team-orchestration model rather than only exposing a lightweight Codex-specific team entrypoint. The aligned end state must support durable team runtime behavior, worker lifecycle management, status and recovery surfaces, Codex routing guidance, and workflow-level execution decisions comparable to OMX.

## Scope

This effort covers the full Codex team surface and its required infrastructure:

- durable team runtime state
- worker lifecycle and tmux session management
- task dispatch, claims, join points, and recovery
- CLI and JSON interop surfaces under `specify team`
- project-level Codex guidance and routing behavior
- workflow integration, especially `sp-implement`

This effort does not attempt to align unrelated OMX features such as non-team specialty workflows unless they are required to support the team/runtime contract.

## Constraints

- Preserve `specify team` as the official product surface for this repository.
- Avoid leaking Codex-only team behavior into non-Codex integrations.
- Keep the Python CLI as the top-level product interface.
- Design the runtime boundary so that the backend can evolve without breaking the `specify` user-facing contract.
- Maintain install/uninstall contract integrity for generated assets.

## Architecture

The aligned architecture should be split into five bounded subsystems that can be implemented incrementally while still converging on the OMX model.

### 1. Runtime Core

Add a real Codex team runtime under `.specify/codex-team/state` with explicit state models for:

- team config
- worker identity and heartbeat
- tasks and task claims
- dispatch requests
- mailbox/messages
- phase state
- monitor snapshots
- shutdown requests and acknowledgements
- append-only event log

This subsystem is the minimum foundation for durable team behavior. Without it, the product can only fan out temporary agents rather than run a true team runtime.

### 2. Session and Worker Lifecycle

Add a controlled worker-launch and teardown layer for:

- tmux session creation and reuse
- worker pane creation
- worktree allocation or equivalent isolated workspaces
- worker bootstrap instructions
- leader/worker role separation
- cleanup and orphan recovery

The design must support both startup safety checks and non-destructive re-entry, so duplicate teams and stale state can be detected and handled explicitly.

### 3. CLI and API Surface

Expand `specify team` from a status-only entrypoint into a full runtime surface with subcommands comparable in intent to OMX:

- `specify team`
- `specify team status`
- `specify team await`
- `specify team resume`
- `specify team shutdown`
- `specify team cleanup`
- `specify team api <operation>`

The API surface must use stable JSON envelopes so other layers can interact with the runtime without scraping human-readable output.

### 4. Codex Routing Brain

Strengthen Codex project guidance so the project-level agent contract can decide when to:

- stay in solo execution
- use native Codex subagents
- escalate to `specify team`

This routing layer should remain Codex-only and must be grounded in project-generated guidance rather than ad-hoc prompt fragments.

### 5. Workflow Integration

Connect the aligned runtime into the existing Spec Kit workflow, especially:

- `sp-plan`
- `sp-tasks`
- `sp-implement`

`sp-implement` should become the main workflow entry that can choose sequential execution, native subagents, or `specify team` based on batch structure and runtime availability. Join points and shared-surface conflicts must remain first-class execution constraints.

  The workflow guidance must treat `specify team` as the durable team runtime: escalate only when the batch shape demands long-lived coordination, join points are blocking, and the runtime availability checks (tmux, session health, the expanded runtime/API status surface) succeed. Keep join-point semantics explicit so every strategy change is auditable, keep shared-surface safety rules intact during and after each escalation, and tie the narrative back to the runtime/API semantics described earlier (start/status/await/resume/shutdown/cleanup).

## Data Flow

The desired execution path is:

1. User enters a Codex project with generated Codex guidance and skills.
2. A workflow such as `sp-implement` or an explicit `specify team` invocation determines that durable parallel execution is warranted.
3. `specify team` initializes team runtime state and creates the session/workers.
4. Workers receive isolated assignments, communicate through runtime-managed state, and report progress through status and events.
5. The leader or workflow layer observes join points, resolves failures, and either resumes execution or shuts the runtime down cleanly.
6. Final runtime state, verification artifacts, and cleanup output remain inspectable after completion.

## Error Handling

The aligned design must explicitly handle:

- missing or unsupported tmux environments
- duplicate team-name conflicts
- stale or orphaned team state
- worker death or non-reporting workers
- task claim conflicts
- join-point blocking after partial parallel failure
- cleanup after interrupted runs

Each of these should produce machine-readable outcomes for the runtime/API surface and clear operator guidance for the CLI surface.

## Testing Strategy

The aligned implementation should be protected by regression coverage across:

- runtime state helpers
- CLI contract tests for `specify team`
- generated Codex asset tests
- lifecycle tests for start/status/await/resume/shutdown/cleanup
- workflow-template tests for routing and parallel decision rules
- non-Codex isolation tests

## Delivery Plan

The implementation should be executed in stages, but all stages serve one end state:

1. Runtime core parity
2. Worker/session lifecycle parity
3. CLI/API parity
4. Codex routing parity
5. Workflow parity and release hardening

## Open Decisions Resolved

- The official surface remains `specify team`, not `omx team`.
- The first implementation target is full behavioral alignment, not a cosmetic imitation.
- Python remains the top-level product layer; backend evolution is allowed as long as the product contract stays stable.
- This effort is intentionally broader than `sp-implement` and must be treated as a repository-level feature program.
