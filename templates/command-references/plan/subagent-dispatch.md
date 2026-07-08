Trigger: before delegating research, data-model, contract, or quickstart planning lanes.

Purpose: preserve adaptive dispatch, writable lane handoffs, evidence index consumption, and subagent-blocked behavior.

Preserved Contract: delegated planning lanes must write structured handoffs and cannot be replaced by chat-only prose or read-only lanes.

## Subagent Dispatch Contract

     - `allowed_artifact_writes: plan.md, research.md, data-model.md, contracts/, quickstart.md, plan-contract.json, planning/handoffs/*.json, planning/evidence-index.json, planning/checkpoints.ndjson, workflow-state.md`
     - `authoritative_files: spec.md, alignment.md, context.md, plan.md, research.md, plan-contract.json, planning/handoffs/*.json, planning/evidence-index.json`
   - [AGENT] Before plan synthesis begins, split the work only into the supported plan lanes: `research`, `data model`, `contracts`, and `quickstart and validation scenarios`.
   - [AGENT] Before dispatch begins, assess the current agent capability snapshot and apply the shared policy contract: `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)`.
   - If the workload is standard and native subagents are available, dispatch `one-subagent` for exactly one validated isolated planning lane or `parallel-subagents` for two or more isolated planning lanes.
   - If the workload is heavy or safety-critical and native subagents are unavailable, or if heavy work cannot be packetized safely, record `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason`; stop before synthesizing planning artifacts.
   - Artifact-writing delegated planning lanes must be dispatched as a writable, execution-capable native subagent lane. If the runtime exposes role, sandbox, or permission choices, select a role/sandbox that can write the declared handoff file; a read-only lane is not a valid lane for `planning/handoffs/<lane-id>.json`.
   - Do not dispatch a read-only explorer, reviewer, or diagnostic lane to satisfy a delegated planning lane that must write a handoff.
   - Each delegated planning lane must persist the lane's structured handoff to `planning/handoffs/<lane-id>.json` before the leader accepts the lane, waits at a join point, or synthesizes `plan.md`, `research.md`, or `plan-contract.json`.
   - Consume `planning/evidence-index.json` before final synthesis when delegated lanes were used.
   - Do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results.
