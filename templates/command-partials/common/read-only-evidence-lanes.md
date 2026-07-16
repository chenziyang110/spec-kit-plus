## Read-Only Evidence Lane Dispatch

Use this shared dispatch contract when a workflow needs independent evidence gathering but the delegated lane must not mutate project state.

Call `choose_evidence_lane_dispatch(command_name="<workflow>", snapshot, workload_shape)` before dispatching read-only evidence lanes.

Perform native subagent capability discovery before recording a delegated lane. Do not record `subagent-blocked` until the active tool surface has been checked and the blocker is specific: no safe lane, no lane contract, no native subagent surface, or unsafe packetization.

Record the selected fields when a lane is used or blocked:

- `lane_mode: read-only-evidence`
- `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`
- `execution_surface: leader-inline | native-subagents | none`
- `structured_result: evidence_packet`
- `blocked_reason` when `dispatch_shape: subagent-blocked`

Dispatch rules:

- Stay `leader-inline` for simple questions or one narrow evidence check.
- Dispatch `one-subagent` when exactly one safe read-only evidence lane is useful and the runtime exposes native subagents.
- Dispatch `parallel-subagents` when two or more independent read-only evidence lanes can run without overlapping conclusions or state ownership.
- Record `subagent-blocked` only when a read-only evidence lane is required but no safe lane, no lane contract, or no native subagent surface is available.

Every read-only evidence lane must have a compact lane contract:

- objective
- user question or discussion decision it supports
- authoritative inputs
- allowed read scope
- forbidden operations
- acceptance checks
- evidence packet format
- join condition

Allowed delegated operations are file reads, `rg`, project cognition navigation/query output, project memory reads, generated-state reads, docs reads, and template reads.

Forbidden delegated operations are file writes, state writes, handoff writes, tests, builds, package managers, project CLI commands, app/server launch, branch creation, and workflow invocation.

The parent workflow owns judgment. Subagents return evidence packets only; they do not decide product direction, readiness, handoff status, final answers, or next workflow.
