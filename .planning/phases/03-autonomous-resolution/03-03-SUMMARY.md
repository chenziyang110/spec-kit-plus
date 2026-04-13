---
phase: 03-autonomous-resolution
plan: 03
subsystem: debug-workflow
tags: [hitl, safety-gate, cli, reporting]
requires: [TOL-02]
provides: [hitl-handoff]
affects: [src/specify_cli/debug/graph.py, src/specify_cli/debug/persistence.py, src/specify_cli/debug/cli.py, tests/test_debug_cli.py, tests/test_debug_graph_nodes.py]
tech-stack: [pytest, typer, rich, pydantic-graph]
key-files: [src/specify_cli/debug/graph.py, src/specify_cli/debug/persistence.py, src/specify_cli/debug/cli.py]
decisions:
  - "Escalate to AwaitingHumanNode after the third failed verification attempt"
  - "Pause resumed sessions that were saved mid-verification until a human reconfirms the persisted commands"
metrics:
  duration: 20m
  completed_date: "2026-04-13"
---

# Phase 03 Plan 03: HITL Safety Gate Summary

## One-liner
Completed the Human-in-the-Loop safety gate so repeated verification failures produce a persisted handoff report and the CLI stops cleanly in an awaiting-human state.

## Key Changes
### Safety Gate
- Added `AwaitingHumanNode` and the `fail_count > 2` threshold in `VerifyingNode`.
- Failed verification now transitions into a human checkpoint instead of looping forever once the retry budget is exhausted.

### Handoff Reporting
- Added `build_handoff_report()` in `src/specify_cli/debug/persistence.py` to summarize trigger, root cause, attempted fix, verification history, eliminated hypotheses, and key evidence.
- Persisted report content is written back into the session file so the audit trail survives interruptions.

### CLI & Resume Behavior
- Updated `src/specify_cli/debug/cli.py` to surface the awaiting-human state, print the session summary, and point the operator back to the persisted markdown file.
- Hardened `run_debug_session()` resume behavior so sessions saved while mid-verification pause for confirmation instead of automatically rerunning persisted commands.

## Deviations from Plan
- The manual HITL walkthrough is now fully covered by automated tests, so the final verification pass relied on automated CLI and graph tests instead of a separate ad hoc terminal demo.

## Known Stubs
None.

## Self-Check: PASSED
- [x] All tasks executed
- [x] Safety gate covered by automated tests
- [x] CLI handoff path validated
- [x] SUMMARY.md created
- [x] Phase ready for final verification
