---
description: Use when one or more independent feature lanes have completed implementation and need a dedicated closeout workflow before mainline integration.
workflow_contract:
  when_to_use: One or more isolated feature lanes are implementation-complete and need lane-level closeout, readiness checks, and integration sequencing before merge.
  primary_objective: Discover completed lanes, run integration prechecks, surface drift or overlap risk, and close the lane cleanly without hiding lane state behind ad hoc merge steps.
  primary_outputs: Integration readiness results, lane completion state updates, and explicit closeout guidance for one or more completed lanes.
  default_handoff: Mainline merge or PR follow-through after readiness is confirmed; do not route back into `sp-implement` as a substitute for closeout.
---

## Objective

Use `sp-integrate` to discover completed lanes, run integration prechecks,
surface drift or overlap risk, and close the lane cleanly.

## Context

- Primary inputs: completed lane state, verification evidence, lane closeout metadata, and the smallest relevant project cognition query bundle or handbook guidance for merge-sensitive shared surfaces.
- This workflow is a dedicated closeout lane after implementation, not a substitute for `sp-implement`.

## Process

1. Discover candidate completed lanes and their readiness state.
2. Check shared-surface overlap, merge sequencing risk, and required closeout evidence.
3. Surface any unresolved integration blockers instead of hiding them behind a generic "done" status.
4. Produce explicit closeout guidance for merge or PR follow-through.
5. For every UI-bearing lane, treat isolated screenshots as input only. After
   the integrated tree exists, run the real entry points and recapture the
   required viewport/state matrix with typed structure, visual, and runtime
   evidence. Update lifecycle `evidence_scope: integrated` and
   `integration_base_ref`, compare against the approved direction and task
   contracts, repair drift, and recapture. The close helper must remain blocked
   while only task-scope evidence exists or human review is unresolved.

## Output Contract

- Integration readiness result for each candidate lane.
- Explicit blocked reasons when closeout cannot proceed safely.
- Recommended next merge or PR follow-through step when readiness is confirmed.

## Guardrails

- Do not fold this workflow into `sp-implement`.
- Do not guess merge order when conflicts or overlap are unclear.
- Treat completed lane state and verification evidence as prerequisites to closeout.
