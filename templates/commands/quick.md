---
description: Use when a task is small but non-trivial and needs lightweight tracked planning, validation, or resumable execution outside the full workflow.
workflow_contract:
  when_to_use: The task is too large or risky for `sp-fast` but does not justify the full `{{specify-subcmd:-> plan -> tasks -> implement}}` flow.
  primary_objective: Keep the task resumable and tracked while applying only the minimum planning, research, and validation depth it needs.
  primary_outputs: '`.planning/quick/<id>-<slug>/STATUS.md`, quick-task summary artifacts, and the scoped implementation changes for the task.'
  default_handoff: 'Resume the quick task until resolved, or escalate to /sp.specify if the scope grows into multi-capability or acceptance-criteria-heavy work.'
---

{{spec-kit-include: ../command-partials/quick/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Main Flow

1. Accept only bounded quick work; otherwise route to `{{invoke:specify}}`, `{{invoke:debug}}`, or the appropriate upstream workflow.
2. Create or resume `.planning/quick/<id>-<slug>/STATUS.md`, confirm the Understanding Checkpoint, and keep `understanding_confirmed: false` blocking substantive work until confirmed.
3. Consume eligible discussion handoff or quick-task context without widening scope; record consequence boundary and escalation decision.
4. Use `choose_subagent_dispatch(command_name="quick", snapshot, workload_shape)` and packetized `WorkerTaskPacket` or equivalent contracts for substantive lanes.
5. Execute the quick task, update STATUS.md at phase transitions, validate changed surfaces, write `SUMMARY.md`, and close as resolved or blocked with truthful coverage.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [intake and checkpoint](references/intake-and-checkpoint.md)
- [workspace state](references/workspace-state.md)
- [handoff consumption](references/handoff-consumption.md)
- [packetized work](references/packetized-work.md)
- [validation and closeout](references/validation-and-closeout.md)
