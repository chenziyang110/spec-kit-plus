## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Keep delegated lanes bounded and role-specific. Prefer fixed analysis or verification roles when the parent workflow defines them explicitly, rather than ad hoc managed-team structures.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

Do not rely on leader-inline fallback semantics or managed-team lifecycle language in this shared partial. The parent workflow must state any command-specific analysis roles, join points, or escalation rules directly.
