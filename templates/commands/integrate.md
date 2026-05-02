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

## Guardrails

- Do not fold this workflow into `sp-implement`.
- Do not guess merge order when conflicts or overlap are unclear.
- Treat completed lane state and verification evidence as prerequisites to closeout.
