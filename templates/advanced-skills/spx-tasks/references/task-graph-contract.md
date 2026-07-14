# Task graph contract

Tasks express independently verifiable outcomes, not a narrated coding recipe.
Trace every confirmed requirement, plan decision, must-preserve behavior, and
triggered consequence obligation to at least one task or explicit deferral.

A task is ready when its authoritative inputs and dependencies are stable, its
write surface is bounded, and a worker can tell completion from failure. Use
dependency edges for true prerequisites, not display ordering. Two tasks are
parallel-safe only when neither consumes the other's uncommitted result and
their writes, generated outputs, state mutations, and verification fixtures do
not collide.

Keep setup and foundational work before feature slices; verify at natural join
points. If a task discovers unknown product behavior or architecture, the task
graph is not the place to decide it—reopen the owning upstream workflow.

UI tasks additionally consume the plan `ui_design_contract` and feature
`ui-brief.md`. Each task owns a bounded surface/state outcome and carries
task-specific `ui_contract`, fidelity level, design inputs, required states,
real entry points, v2 direction fields, task-relevant reference/content/image
records, structure/visual/runtime evidence, and comparison or human review. Use
`assets/ui-task.md` for the project-facing detail and
`assets/ui-task-index-entry.json` for the exact canonical JSON pair. General UI
without an external fidelity target still uses `ui_fidelity_requirements.level:
approximate` against the approved design/brief; `ui_contract.fidelity_level`
may remain `none` or `inspiration`. Missing UI fields are a graph defect, not
`not_applicable`.
