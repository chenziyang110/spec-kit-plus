## Mandatory Subagent Execution

All substantive work in ordinary `sp-*` workflows MUST use subagents once a validated lane exists.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane MUST have a task contract with:
- objective
- authoritative inputs
- allowed read scope
- allowed write scope
- forbidden paths or forbidden drift
- acceptance checks
- required validation evidence
- structured handoff format

A lane is dispatch-ready only when its validated packet or equivalent execution contract contains all required fields.

If a validated lane exists, leader-inline execution of that lane's substantive work is forbidden.

If no validated lane can be packetized safely, the workflow MUST mark `subagent-blocked` and stop.

Idle, silent, or prose-only subagent output is not an accepted result.

A workflow MAY continue past a join point only after the required structured handoff and required evidence are present.

Keep delegated lanes bounded and role-specific. Use fixed analysis or verification roles when the parent workflow defines them explicitly, rather than ad hoc managed-team structures.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

Do not rely on leader-inline fallback semantics or managed-team lifecycle language in this shared partial. The parent workflow must state any command-specific analysis roles, join points, or escalation rules directly.
