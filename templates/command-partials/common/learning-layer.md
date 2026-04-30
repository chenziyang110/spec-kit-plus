## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command {COMMAND} --format json` when available so passive learning files exist, the current run sees relevant shared project memory, and repeated candidates, including repeated high-signal candidates, can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader command-local context.
- Review `.planning/learnings/candidates.md` only when it still contains relevant candidate learnings after the passive start step, especially repeated workflow gaps, user preferences, or project constraints for the touched area.
- [AGENT] When friction appears, run `specify hook signal-learning --command {COMMAND} ...` with {SIGNAL_TYPES}.
- [AGENT] Before final completion or blocked reporting, run `specify hook review-learning --command {COMMAND} --terminal-status <resolved|blocked> ...`; use `--decision none --rationale "..."` only when no reusable {REVIEW_TYPES} exists.
- [AGENT] Prefer `specify learning capture-auto --command {COMMAND} --feature-dir "$FEATURE_DIR" --format json` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `specify hook capture-learning --command {COMMAND} ...` when the durable state does not capture the reusable lesson cleanly.
- Treat this as a passive shared-memory layer, not as a separate user workflow. Do not redirect the user into a dedicated learning-management command.
