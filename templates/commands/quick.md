---
description: Use when a non-trivial task needs tracked direct delivery, scalable task-local planning, validation, or resumable execution without first creating a formal feature specification.
workflow_contract:
  when_to_use: The requested outcome is clear enough to implement directly and needs more tracking than `sp-fast`; task size, capability count, architecture, migration, compatibility, rollout, and acceptance depth do not disqualify this workflow.
  primary_objective: Keep direct-delivery work resumable while scaling task-local planning, research, decomposition, consequence analysis, and validation to the actual workload.
  primary_outputs: '`.planning/quick/<id>-<slug>/STATUS.md`, quick-task summary artifacts, and the scoped implementation changes for the task.'
  default_handoff: 'Resume the quick task until resolved or concretely blocked. Never require an upgrade to /sp.specify because the task grows; use that formal specification path only when the user explicitly chooses it.'
---

{{spec-kit-include: ../command-partials/quick/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}
{{spec-kit-include: ../command-partials/common/run-bootstrap.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

[AGENT] `sp-quick` always starts a new run. Record that new run with `specify-runtime run create`, then execute only through `specify-runtime run supervise`; do not resume another workflow's run.

## Main Flow

1. Accept non-trivial direct-delivery work of any size whose outcome can be confirmed at the Quick Checkpoint. Scale the quick workspace instead of routing to `{{invoke:specify}}` because work is large, cross-cutting, multi-capability, migration-heavy, or acceptance-heavy; route unknown failure mechanisms to `{{invoke:debug}}`.
2. Create `.planning/quick/<id>-<slug>/STATUS.md` only with `artifact scaffold --kind quick-status`; resume via `artifact show`, and mutate frontmatter/sections only through leased `artifact patch` calls.
3. Consume eligible discussion handoff or quick-task context without silently changing the confirmed scope; record consequence coverage, planning depth, and any user-owned checkpoint amendment.
4. Use `choose_subagent_dispatch(command_name="quick", snapshot, workload_shape)` and packetized `WorkerTaskPacket` or equivalent contracts for every substantive Q item. Default `one-subagent` when Q items share write scope or depend serially; use `parallel-subagents` only for isolated write sets. A parallel write-conflict error is not permission for leader-inline—record `blocked_dispatch` before any leader-inline fallback.
5. Execute through `quick packet-compile` / `item-start` / subagent join / `item-accept`, patch `STATUS.md` through the artifact CLI at phase transitions, and validate changed surfaces.
6. **Before** `quick close … resolved` on source-changing work: run inline project cognition closeout (`cognition closeout-plan` → update → validate-build/complete-refresh or mark-dirty), then record `specify-runtime quick cognition-closeout <id> --result-state ready|no_op|mark-dirty|partial --reason "…"`. Greenfield/empty graph still needs `no_op` or `mark-dirty` with reason—never skip. Create/patch `SUMMARY.md` (including `project_cognition_refresh`), confirm `quick status` shows `cognition_closeout.allowed_close=true`, and only then `specify-runtime quick close <id> resolved`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [intake and checkpoint](references/intake-and-checkpoint.md)
- [workspace state](references/workspace-state.md)
- [handoff consumption](references/handoff-consumption.md)
- [packetized work](references/packetized-work.md)
- [validation and closeout](references/validation-and-closeout.md)
