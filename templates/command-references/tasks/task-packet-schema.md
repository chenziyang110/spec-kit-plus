Trigger: when shaping task-index.json, a compact compatibility transition, or fields needed for just-in-time WorkerTaskPacket compilation.

Purpose: preserve the minimum task-graph fields required to compile a correct worker packet at execution time without repeating project intake.

Preserved Contract: leader-direct tasks stay compact; delegated packets carry objective, scope, required references, forbidden drift, validation, done condition, task-relevant obligations, and recovery.

## Task Packet Schema

- When lane resolution returns a materialized lane worktree, record that lane ref in the canonical task graph.
- Do not run project cognition from packet shaping. Reuse the context capsule and validation routes already stored by planning/task intake.
- Store only task-shaping fields in task-index.json: objective, dependencies, expected write scope, required refs, acceptance, verification, obligation refs, join point, and packet mode.
- Use `packet_mode: leader-direct | delegated | parallel-high-risk`.
- `leader-direct` tasks do not need a WorkerTaskPacket.
- For delegated work, `sp-implement` compiles and validates the packet just in time from the current task, live repository state, and stable contract refs.
- Carry `global_constraints`, interfaces, review risks, UI fidelity, controller checks, `MP-*`, and `CA-###` only when they affect that task.
- UI-bearing tasks use the complete current `ui_contract` as their only UI
  execution contract. Carry the direction
  core without reinterpreting it, only the task-relevant reference/content/image
  records, and all platform-neutral evidence kinds. The compiler adds verified
  plan cognition routes as compact `context_nav` instead of raw graph output.
- If live evidence invalidates a predicted path or dependency, repair the task graph or stop/reopen; do not hide drift by expanding worker scope silently.
