Trigger: before delegating research, data-model, contract, or quickstart planning lanes.

Purpose: preserve adaptive dispatch, runtime-owned lane results, compact manifest consumption, and subagent-blocked behavior.

Preserved Contract: delegated planning lanes must submit structured handoffs through the CLI and cannot be replaced by chat-only prose.

## Subagent Dispatch Contract

     - `allowed_artifact_writes: plan.md, research.md, data-model.md, contracts/, quickstart.md, plan-contract.json, planning/lane-manifest.json, planning/handoffs/*.json, workflow-state.md` declares the leader/runtime mutation scope only; every entry is created or changed through its registered CLI owner.
     - `authoritative_files: spec-contract.json, plan-contract.json`
   - [AGENT] Before plan synthesis begins, split the work only into the supported plan lanes: `research`, `data model`, `contracts`, and `quickstart and validation scenarios`.
   - [AGENT] Before dispatch begins, assess the current agent capability snapshot and apply the shared policy contract: `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)`.
   - If the workload is standard and native subagents are available, dispatch `one-subagent` for exactly one validated isolated planning lane or `parallel-subagents` for two or more isolated planning lanes.
   - If the workload is heavy or safety-critical and native subagents are unavailable, or if heavy work cannot be packetized safely, record `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason`; stop before synthesizing planning artifacts.
   - Delegated planning lanes have no direct workflow-artifact write scope. Give each execution-capable lane the complete runtime-owned result-submit argv prefix and inline payload contract; `planning/handoffs/<lane-id>.json` is materialized only by the runtime.
   - A read-only evidence worker may satisfy a planning lane when it can return the complete structured payload through that CLI channel; chat-only prose or an idle result cannot.
- Each delegated planning lane submits its structured handoff inline with `specify-runtime result submit --command plan --feature-dir <feature-dir> --lane-id <lane-id> --result-json '<inline-json>'`; the runtime owns `planning/handoffs/<lane-id>.json`.
   - Record lane id, input refs, result ref, status, integration target, and blocker once in `planning/lane-manifest.json`; consume each accepted result exactly once before final synthesis.
   - Do not create separate evidence-index and checkpoint logs for the same lane events.
   - Do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results.
