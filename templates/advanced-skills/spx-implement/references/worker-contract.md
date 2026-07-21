# Implementation worker contract

Delegate only a bounded task with stable inputs and isolated writes. The leader
retains task graph, join, task acceptance, task-level review, and final
implementation verification ownership. The later system Review remains an
independent workflow.

Provide the worker:

- full task outcome and authoritative contract refs;
- allowed read/write paths and forbidden paths;
- dependencies, must-preserve and consequence obligations;
- acceptance, accepted change-set RED/baseline epoch ref or
  test-authoring-only status, cheap task checks, deferred epoch gates, and
  required real-entrypoint coverage;
- exact structured result destination or return shape.

For a UI-bearing task, the packet carries `ui_contract`, original visual
references with use intent, approved visual ref, real content/image plans,
required states, and the integrated evidence triad. Return changed surfaces,
state/viewport requirements, and visual risks; do not run the full viewport/state
capture loop per Txx. The Leader records canonical `structure_snapshot`,
`visual_capture`, and `runtime_diagnostics` with `evidence_scope: integrated`
during a validation epoch. Before dispatch, the leader ensures the worker can
read the installed skill-local `references/ui-quality-gate.md` and names it in
the dispatch context; the worker may not replace inspectable sources with a
prose summary.

Require a result containing status, changed paths, cheap task checks, test
impact, consumer or UI coverage notes when triggered, blockers, failed
assumptions, and recovery guidance. Workers must not run a test suite, full
build, service startup, E2E journey, or browser capture per Txx, and they cannot
open or increment a validation epoch.
Cheap producer-to-consumer wiring evidence remains task-local when a consumer
surface is named. Defer only runtime real-entrypoint proof to the Leader epoch;
do not defer the static "created but not wired" check.
Validate packet/result with the installed hook helpers when available. Do not
accept idle execution, an unwritten handoff, or synthetic-only proof for a
real-entrypoint requirement.

The leader must not edit an active worker write scope. After the join, inspect
the integrated diff and collect the task's gates into one change-set validation
epoch. The epoch ledger is shared across Implement and Review, permits at most
three, and is never reset. The third failed epoch blocks; never start a fourth.
Prefer targeted
edits that preserve approved working structure; do not replace whole UI files
when a bounded change can converge safely. A worker may report
concerns; it may not redefine confirmed product scope or declare the whole
feature complete.
