---
name: spx-quick
description: Lean tracked-change workflow for advanced coding models. Use when work is small but non-trivial and needs lightweight scope, resumability, implementation, and verification without a full feature specification.
---

# SPX Quick

Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/task-contract.md`. Read `references/worker-contract.md` only
when delegating. Read `references/consequence-gate.md` when the change affects
lifecycle, shared state, destructive behavior, compatibility, migration,
security, concurrency, retry, recovery, or generated consumers. Resolve
`assets/` paths relative to this Skill.

Accept bounded work that is too coupled or uncertain for `$spx-fast` but does
not need feature-level requirements and architecture. Route unresolved failures
to `$spx-debug` and acceptance-heavy or multi-capability work to
`$spx-specify`.

Create new state from `assets/status.md` or resume
`.planning/quick/<id>-<slug>/STATUS.md`. Use `specify quick list|status|resume`
for deterministic discovery. Keep state compact and ask the user only for
decisions the repository cannot supply.

Inspect the current diff and cognition-selected paths, then implement the full
bounded scope. Delegate only independent lanes that improve throughput or
confidence; do not manufacture packets for leader-direct work. Use a failing
test or credible baseline when practical. Check changed behavior, consumers,
and generated/mirrored copies, then run verification proportional to risk.

Update `STATUS.md` at meaningful transitions and render `SUMMARY.md` from
`assets/summary.md` on completion or blockage. Close with `specify quick close`
only after terminal truth is recorded; archive is a separate explicit action.
After verified repository changes, close out cognition with canonical workflow
`quick`. Report changed paths, evidence, and remaining risk.
