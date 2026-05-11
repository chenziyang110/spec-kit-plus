## Passive Project Learning Layer

Learning capture is proportional to command complexity:

| Tier | Learning Behavior |
|------|-------------------|
| trivial | Skip learning unless the task escalates or exposes reusable project memory. |
| light | Read the learning index and auto-capture from durable state on resolution when useful. |
| heavy | Full learning: start -> read index -> signal friction -> closeout capture into index/detail. |

### Learning Reflex

Before final closeout, ask whether a future senior engineer would benefit from
seeing this lesson before related work. If yes, update the learning index and
detail document. Do not ask the user for routine permission to record low-risk
project memory. Do not bury reusable lessons only in chat, task files, or
workflow-state.

### Tier: trivial
- Do not run `{{specify-subcmd:learning start}}` unless the task escalates.
- Do not invoke learning hooks for ordinary one-off edits.

### Tier: light
- Run `{{specify-subcmd:learning start}}` with the current command name when available.
- Read `.specify/memory/project-rules.md` and `.specify/memory/learnings/INDEX.md` before local context.
- Open only detail docs linked from relevant index entries.
- On resolution, prefer `{{specify-subcmd:learning capture-auto}}` when durable state contains reusable friction.

### Tier: heavy
- Run `{{specify-subcmd:learning start}}` with the current command name so shared memory and relevant detail refs are visible.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader command-local context.
- Open only linked detail docs whose `applies_to` or `trigger_signals` match the current work.
- When friction appears, signal it through `{{specify-subcmd:hook signal-learning}}` with relevant counts.
- Before final completion or blocked reporting, perform learning closeout: capture or merge an index/detail lesson when future reuse is plausible, or explicitly decide the run was one-off.
- Prefer `{{specify-subcmd:learning capture-auto}}` when durable state already preserves route reasons, false starts, hidden dependencies, validation gaps, or reusable constraints.
- Use manual `capture-learning` only when durable state does not capture the lesson cleanly.
  Required options: `--command`, `--type`, `--summary`, `--evidence`
- Promote to `project-rules.md` or constitution only after recurrence, explicit user confirmation, or stable cross-workflow governance value.
