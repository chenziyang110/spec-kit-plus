Trigger: before delegating research, data-model, contract, or quickstart planning lanes.

Purpose: preserve adaptive dispatch, runtime-owned lane results, compact manifest consumption, and subagent-blocked behavior.

Preserved Contract: delegated planning lanes must submit structured handoffs through the CLI and cannot be replaced by chat-only prose.

## Subagent Dispatch Contract

     - `allowed_artifact_writes: plan.md, research.md, data-model.md, contracts/, quickstart.md, plan-contract.json, planning/lane-manifest.json, planning/handoffs/*.json, workflow-state.md` declares the leader/runtime mutation scope only; every entry is created or changed through its registered CLI owner.
     - `authoritative_files: spec-contract.json, plan-contract.json`
   - [AGENT] Before plan synthesis begins, split the work only into the supported plan lanes: `research`, `data model`, `contracts`, and `quickstart and validation scenarios`.
   - [AGENT] Before dispatch begins, assess the current agent capability snapshot and apply the shared policy contract: `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)`.
   - If the workload is standard and native subagents are available, dispatch `one-subagent` for exactly one validated planning lane, or for two or more lanes that share inputs/outputs and cannot safely isolate handoffs; dispatch `parallel-subagents` only for two or more **isolated** planning lanes.
   - Write-scope or handoff-surface conflict among planning lanes is a serial `one-subagent` signal, not permission for unrecorded leader-inline synthesis of those lanes while native subagents remain available.
   - If heavy/safety-critical work temporarily lacks a native worker, retry capability discovery, wait, or redispatch a safely packetized serial lane in the same invocation. If no safe surface exists, record an agent-owned capability blocker with `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, concrete reason, and exact resume action; stop synthesis but never ask the user to repair dispatch state or reconstruct the lane.
   - Delegated planning lanes have no direct workflow-artifact write scope. Give each execution-capable lane the complete runtime-owned result-submit argv prefix and inline payload contract; `planning/handoffs/<lane-id>.json` is materialized only by the runtime.
   - A read-only evidence worker may satisfy a planning lane when it can return the complete structured payload through that CLI channel; chat-only prose or an idle result cannot.
- Each delegated planning lane submits its structured handoff with `specify-runtime result submit --command plan --feature-dir <feature-dir> --lane-id <lane-id> --result-json <inline-json|@path|->`; keep small payloads inline, use stdin for large model-authored JSON, and reserve `@path` for an existing runtime-owned or registered project artifact. The runtime owns `planning/handoffs/<lane-id>.json`.
   - Record lane id, input refs, result ref, status, integration target, and blocker once in `planning/lane-manifest.json`; consume each accepted result exactly once before final synthesis.
   - Do not create separate evidence-index and checkpoint logs for the same lane events.
   - Do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results.
