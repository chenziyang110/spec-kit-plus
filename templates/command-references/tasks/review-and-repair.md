Trigger: before marking the task graph ready, after a task-layer defect, or when upstream truth appears invalid.

Purpose: validate and repair execution readiness without repeating full specification/plan review or generating premature worker packets.

Preserved Contract: implementation stays blocked until complete scope, dependencies, boundaries, obligations, acceptance, validation, and recovery are executable.

## Deterministic Task-Graph Review

Validate:

- every in-scope acceptance criterion maps to implementation and verification work;
- dependencies are acyclic and interface consumes/produces are ordered;
- parallel write sets do not overlap and shared state is serialized;
- target root/path discovery is explicit;
- each task has objective, bounded scope, required refs, forbidden drift, acceptance, and verification;
- task-relevant `MP-*`, `CA-###`, capability operations, fidelity obligations, and user-observable paths are mapped;
- stop/reopen conditions and valid user-confirmed deferrals remain traceable;
- light/leader-direct work does not carry delegated-packet ceremony;
- delegated/high-risk tasks contain enough stable fields for just-in-time packet compilation.

Use agent review only for residual judgment: ambiguous task boundary, uncertain dependency, unsafe parallelization, or conflicting evidence.

## Repair Boundary

Repair task ids, objectives, dependencies, expected paths, required refs, packet mode, batches, join points, acceptance, and verification locally when upstream meaning is unchanged.

Route upstream when repair changes goal, confirmed scope, architecture, feasibility, target boundary, protected obligation, or a user-owned decision.

Completed task IDs remain stable. New repair/refinement tasks append and reference the task they repair.

## Ready Transition

Set ready only after deterministic validation passes. Transition to `sp-implement` with canonical task ref, semantic delta, required refs, blockers, and recovery. Do not attach duplicate task bodies or pre-generated packets.

Prepare event-triggered implementation review conditions for repository drift, parallel joins, write-scope drift, validation failure, worker concern, obligation conflict, real-entrypoint gaps, and sequential change-window limits.
