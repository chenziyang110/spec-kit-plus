# Implementation worker contract

Delegate only a bounded task with stable inputs and isolated writes. The leader
retains task graph, join, acceptance, review, and final verification ownership.

Provide the worker:

- full task outcome and authoritative contract refs;
- allowed read/write paths and forbidden paths;
- dependencies, must-preserve and consequence obligations;
- acceptance, RED/baseline expectation, and required real-entrypoint evidence;
- exact structured result destination or return shape.

For a UI-bearing task, the packet carries `ui_contract`, original visual
references with use intent, approved visual ref, real content/image plans,
required states, and the evidence triad. Return `ui_fidelity_evidence` kinds
`structure_snapshot`, `visual_capture`, and `runtime_diagnostics`, plus visual
comparison or human-review status. Before dispatch, the leader ensures the worker can
read the installed skill-local `references/ui-quality-gate.md` and names it in
the dispatch context; the worker may not replace inspectable sources with a
prose summary.

Require a result containing status, changed paths, validation, consumer or UI
evidence when triggered, blockers, failed assumptions, and recovery guidance.
Validate packet/result with the installed hook helpers when available. Do not
accept idle execution, an unwritten handoff, or synthetic-only proof for a
real-entrypoint requirement.

The leader must not edit an active worker write scope. After the join, inspect
the integrated diff and rerun the meaningful verification. Prefer targeted
edits that preserve approved working structure; do not replace whole UI files
when a bounded change can converge safely. A worker may report
concerns; it may not redefine confirmed product scope or declare the whole
feature complete.
