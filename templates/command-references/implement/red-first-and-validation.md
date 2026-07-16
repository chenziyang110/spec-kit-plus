Trigger: before code-writing, test execution, or validation closeout.

Purpose: preserve RED-first expectations, pre-dispatch validation, validation evidence, and no-greenwashing rules.

Preserved Contract: implementation must prove red/validation state before changes and verify completed work before closeout.

## Current Task Gate

Before code changes:

1. Validate current task dependencies, required refs, expected write scope, forbidden drift, acceptance, and verification route. If delegated, validate the just-in-time WorkerTaskPacket; leader-direct work uses the same task gate without packet boilerplate.
2. For parallel lanes, require zero overlapping writes and an explicit join validation target. Serialize overlapping work.
3. For a behavior change, bug fix, or refactor, write or select the smallest failing test or reproducible check first and run it before production edits. Record the RED command/check and expected failure in the task lifecycle record.
4. If an honest RED state cannot be produced, record why, the replacement baseline, and residual risk; block when acceptance cannot be proven.

## GREEN And Closeout

After the change:

1. Rerun the same RED gate and require GREEN.
2. Run task-specific acceptance and regression checks, including real-entrypoint or UI evidence when required.
3. Record commands/checks, outcomes, changed paths, and remaining manual checks once in the task lifecycle record.
4. Do not claim success from task markers, worker narration, or unrelated passing tests.
