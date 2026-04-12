---
phase: 02-contextual-intelligence
plan: 03
subsystem: debug
tags: [pydantic-graph, fsm, context-awareness, prioritization, elimination]
dependency_graph:
  requires: ["02-02"]
  provides: ["investigation-loop-v2"]
  affects: [src/specify_cli/debug/graph.py, tests/test_debug_graph_nodes.py]
tech_stack:
  added: []
  patterns: [state-driven prioritization, command-pattern in next_action]
key_files:
  created: []
  modified: [src/specify_cli/debug/graph.py, tests/test_debug_graph_nodes.py]
decisions:
  - "Use 'Eliminate:' prefix in 'next_action' as a mechanism for the LLM to signal hypothesis elimination."
  - "InvestigatingNode should reset focus and prioritization after elimination."
metrics:
  duration: 15m
  completed_date: "2026-04-12T23:45:00Z"
---

# Phase 02 Plan 03: Contextual Intelligence Summary

## Objective
Update the `InvestigatingNode` to utilize loaded context for better hypothesis generation and ensure thorough recording of eliminated theories.

## Implementation Details

### Prioritization in InvestigatingNode
When `InvestigatingNode` runs and there is no current focus or hypothesis, it now automatically populates `next_action` with a nudge towards files found in `ctx.state.context.modified_files` and `ctx.state.recently_modified`. This ensures the LLM agent starts its search in the most likely areas.

### Hypothesis Elimination
A new mechanism was added where the LLM can signal that a hypothesis has been eliminated by setting `next_action` to a string starting with `Eliminate:`. When this is detected:
1. The current hypothesis and evidence are appended to the `eliminated` list.
2. The current focus fields are reset.
3. The node returns `self`, allowing the prioritization logic to run and provide a new `next_action`.

## Deviations from Plan
None.

## Self-Check
- [x] All tasks executed
- [x] Each task committed individually
- [x] All deviations documented
- [x] SUMMARY.md created
- [x] STATE.md updated
- [x] ROADMAP.md updated
- [x] Final metadata commit made

## Commits
- `b65c403`: feat(02-03): implement prioritization and elimination in InvestigatingNode
- `4dff03e`: test(02-03): add unit tests for prioritization and elimination
