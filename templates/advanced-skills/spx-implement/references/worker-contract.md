# Implementation worker contract

Delegate only a bounded task with stable inputs and isolated writes. The leader
retains task graph, join, acceptance, review, and final verification ownership.

Provide the worker:

- full task outcome and authoritative contract refs;
- allowed read/write paths and forbidden paths;
- dependencies, must-preserve and consequence obligations;
- acceptance, RED/baseline expectation, and required real-entrypoint evidence;
- exact structured result destination or return shape.

Require a result containing status, changed paths, validation, consumer or UI
evidence when triggered, blockers, failed assumptions, and recovery guidance.
Validate packet/result with the installed hook helpers when available. Do not
accept idle execution, an unwritten handoff, or synthetic-only proof for a
real-entrypoint requirement.

The leader must not edit an active worker write scope. After the join, inspect
the integrated diff and rerun the meaningful verification. A worker may report
concerns; it may not redefine confirmed product scope or declare the whole
feature complete.
