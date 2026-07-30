## Adaptive Artifact-Phase Execution

This partial governs artifact-producing adaptive phases such as `sp-design`, `sp-plan`, and `sp-tasks`. `sp-implement` has its own task-level adaptive controller; debug, map, PRD, and other workflows keep their command-specific execution contracts.

Select the execution mode before dispatch:

- `light`: low-risk, single-lane artifact work that is safe for leader-inline synthesis.
- `standard`: bounded planning or task-generation work where native subagents should be used when available.
- `heavy`: safety-critical, cross-boundary, high-risk, or hard-to-packetize work that requires safe native delegation before synthesis continues.

Record the adaptive decision fields exactly:

- `execution_model: adaptive`
- `execution_mode: light | standard | heavy`
- `workflow_status: ready | blocked`
- `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`
- `execution_surface: leader-inline | native-subagents | none`
- `capability_degraded: false | true`
- `blocked_reason: required when blocked`

Use `choose_subagent_dispatch(command_name="plan" | "tasks", snapshot, workload_shape)` as the shared policy contract. Derive `workload_shape.lightweight_safe` from workload shape and risk keys; do not invent a separate template-only boolean.

Dispatch rules:

- Light mode records `dispatch_shape: leader-inline`, `execution_surface: leader-inline`, `workflow_status: ready`, and `capability_degraded: false`.
- Standard mode uses native subagents when available: one validated lane records `one-subagent`; two or more isolated lanes record `parallel-subagents`.
- Standard mode may degrade to leader-inline only when native subagents are unavailable and no high-risk trigger is present; record `capability_degraded: true`.
- Heavy mode must use native subagents with safely packetized lanes. If native subagents are unavailable, or if the work cannot be packetized safely, record `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, and `blocked_reason`.

Artifact-producing delegated lanes must use execution-capable native subagents, but no worker receives direct workflow-artifact write authority. Each lane builds its bounded result in memory and submits it through the runtime-provided inline result channel; the runtime alone materializes the canonical handoff path. Product/source write scope remains explicit when a lane actually implements code, while planning and task-generation lanes are read-only outside their result channel. If a delegated lane returns prose, idle state, or no accepted CLI result, stop or re-dispatch with the complete runtime-owned result argv and inline payload contract.

Delegated lanes still require structured handoffs before synthesis. If delegated lanes were used, consume the one lane manifest and every accepted lane result before final output; do not duplicate the same events into evidence-index and checkpoint logs. If no lanes were delegated, report the delegated-lane field as `none`.

Managed-team fallback is not part of adaptive plan/tasks dispatch. Do not route blocked adaptive planning or task generation to `sp-teams`, managed-team lifecycle language, or a durable team fallback from this command.
