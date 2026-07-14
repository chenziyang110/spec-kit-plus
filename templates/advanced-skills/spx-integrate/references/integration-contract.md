# Integration contract

A lane is ready only when its implementation lifecycle is truthfully terminal,
required evidence exists, and its branch/worktree can be related to the current
integration base. Re-evaluate after every preceding lane changes that base.

Check:

- declared and actual write overlap, including generated files and migrations;
- dependency order and shared contract/version assumptions;
- drift, conflicts, missing commits, dirty worktrees, and ownership ambiguity;
- verification that must run only on the combined result;
- rollback or recovery state if integration cannot complete.

For UI-bearing lanes, isolated screenshots are inputs rather than combined
proof. Re-run the UI quality gate on the integrated entrypoint and preserve the
task viewport/state matrix, visual comparison, and human-review boundary.

Closing a lane records accepted integration truth; it must follow successful
combined validation. On partial integration, identify what landed, what remains
isolated, and the safe recovery boundary. Never erase blocked evidence to make
the lane list look clean.
