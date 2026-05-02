## Passive Project Learning Layer

Learning capture is proportional to command complexity:

| Tier | Learning Behavior |
|------|-------------------|
| trivial | Skip all learning hooks. No capture. |
| light | Auto-capture on resolution only. No review, no signal. |
| heavy | Full learning: start → signal on friction → review → capture-auto |

### Tier: trivial
- Do not run `{{specify-subcmd:learning start}}`.
- Do not read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, or `.specify/memory/project-learnings.md`.
- Do not review `.planning/learnings/candidates.md`.
- Do not invoke any learning hooks.

### Tier: light

### Tier: heavy
- Run `{{specify-subcmd:learning start}}` with the current command name to initialize passive learning files so the current run sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader command-local context.
- Review `.planning/learnings/candidates.md` only when it still contains relevant candidate learnings after the passive start step, especially repeated workflow gaps, user preferences, or project constraints for the touched area.
- When friction appears, signal it through `{{specify-subcmd:hook signal-learning}}` with relevant counts (retries, hypothesis-changes, validation-failures, false-starts, hidden-dependencies).
- Before final completion or blocked reporting, run `{{specify-subcmd:hook review-learning}}` with the terminal status; use `--decision none` only when no reusable pitfall, recovery-path, or project-constraint exists.
- Prefer `{{specify-subcmd:learning capture-auto}}` when the durable state already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `{{specify-subcmd:hook capture-learning}}` when the durable state does not capture the reusable lesson cleanly.
- Treat this as a passive shared-memory layer, not as a separate user workflow. Do not redirect the user into a dedicated learning-management command.
