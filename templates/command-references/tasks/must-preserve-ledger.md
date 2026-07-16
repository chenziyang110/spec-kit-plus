Trigger: when carrying planning decisions, consequence obligations, capability operations, reference fidelity, or user-observable paths into tasks.

Purpose: preserve CA/MP obligations, capability coverage, and user-observable path coverage.

Preserved Contract: confirmed obligations must map to tasks, packet fields, join points, validation tasks, or named deferral and stop contracts.

## Consequence Obligation Mapping

Before the task package is complete, map every triggered `CA-###` consequence obligation into executable work or an explicit downstream stop condition.

- Read consequence and must-preserve refs from canonical `plan-contract.json`; open a referenced spec/plan view only when the ref or evidence is missing, stale, or contradictory.
- For each `CA-###`, name the affected objects, required state behavior, dependency impact, recovery and validation requirement, owning task or join point, and latest safe resolve phase.
- Map each obligation to at least one task, packet field, join point, validation task, review checkpoint, refinement checkpoint, valid blocker, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- Each mapped task or packet must include objective, write set, affected state or dependency, required references, forbidden drift, validation command or concrete manual check, done condition, and stop-and-reopen condition.
- Emit each mapping once in canonical `task-index.json`; render it in `tasks.md` only when it has project-review value. A compatibility transition references the canonical mapping instead of copying it.
- Preserve `CA-###` IDs verbatim in task-index metadata and just-in-time worker packet shaping instructions so `sp-analyze` and `sp-implement` cannot drop them.
- If a consequence obligation is unmapped, do not emit a normal `/sp.analyze` handoff. Repair the task package or route back to `{{invoke:plan}}`, `{{invoke:clarify}}`, or `{{invoke:deep-research}}` with the unmapped obligation named.

## Capability Operation Coverage

Before finalizing the task graph, map every preserved or in-scope operation-shaped capability referenced by `plan-contract.json`.

- Operation-shaped capabilities include new/create/scaffold/authoring/template-creation, CLI path, TUI path, lifecycle action, API entry point, and any user workflow verb that changes implementation or validation shape.
- For each capability operation, create at least one implementation task, test/quickstart task, join point, packet field, refinement checkpoint, valid blocker, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- Treat template-only task output as insufficient for a confirmed create/scaffold capability unless the plan explicitly selected manual copy as the entry point.
- Detect semantic degradation: if an upstream create/scaffold operation becomes manual copy docs, static template-only support, or an authoring guide with no executable entry point, stop and route back to `{{invoke:plan}}` or `{{invoke:clarify}}`.
- Anti-goals must include a does-not-remove guard when they restrict command, route, API, lifecycle, or public surface growth. Example: "Do not add public commands beyond X; does-not-remove guard: preserve scaffold capability via TUI route or core API."
- Do not generate an anti-goal that forbids a public command and also leaves the underlying operation without another selected entry point.

## User-Observable Path Coverage

Before finalizing `tasks.md`, add a real-entrypoint validation path for every user-observable UI, TUI, CLI, API route, installer, registry/factory/config wiring, generated asset, or runtime boundary affected by the feature.

- For each visible or runtime-consumed behavior, map: real entrypoint -> producer data -> transformer/state builder -> consumer surface -> executor/boundary -> validation task.
- Do not treat synthetic component, reducer, helper, or hand-built state tests as sufficient by themselves when the feature is visible through a real route, command, TUI screen, API, installer, or runtime executor.
- At least one task for each mapped path must carry required consumer and real-entrypoint evidence refs for leader-direct execution or just-in-time packet compilation.
- If no real-entrypoint validation surface exists yet, create the smallest feasible validation task, add a refinement checkpoint, identify a valid blocker, or record a user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
