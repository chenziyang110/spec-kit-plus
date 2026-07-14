---
name: spx-integrate
description: Independent feature-lane integration and closeout for advanced coding models. Use when isolated lanes are implementation-complete and need readiness, overlap, sequencing, and recovery checks before mainline merge or PR follow-through.
---

# SPX Integrate

Read `references/project-cognition.md`, using cognition intent `implement`, and
`references/integration-contract.md`. Read `references/consequence-gate.md`
when integration crosses a shared state, migration, compatibility, security, or
generated-consumer boundary.

Discover candidates with `{{specify-subcmd:integrate}}`. For each selected lane,
inspect its recorded ownership, feature/workflow state, branch and worktree,
implementation closeout evidence, current diff, dependency order, overlapping
writes, drift from mainline, unresolved conflicts, and required combined
verification.

Integrate in dependency order using the repository's normal version-control
mechanism. The `integrate` helper only inspects and closes lane state; it does
not perform a Git merge. Do not treat a merge, copied files, or green isolated
tests as lane closeout. Resolve conflicts against the authoritative spec/plan
and live consumers; route unknown behavior to `$spx-debug` and unfinished
feature work back to `$spx-implement`.

Run the combined real-entrypoint checks after the integrated tree exists. Only
when readiness and verification pass may you close a lane with
`{{specify-subcmd:integrate --feature-dir <feature-dir> --close}}`. Preserve a
blocked lane and its recovery evidence instead of forcing terminal state.

Close out project cognition for actual integrated repository changes. Report
lane order, overlap/conflict decisions, checks run, closed lanes, and remaining
mainline or PR actions.
