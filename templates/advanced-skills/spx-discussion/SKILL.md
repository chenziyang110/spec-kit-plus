---
name: spx-discussion
description: Resumable product and technical discussion for advanced coding models. Use when a rough idea needs durable decisions and options before formal specification.
---

# SPX Discussion

Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/discussion-contract.md`.
Read `references/ui-quality-gate.md` when product experience, interface
direction, screen hierarchy, or interaction behavior is part of the decision.

Discover or create the session with the project launcher-backed
`{{specify-subcmd:discussion list --json}}` and
`{{specify-subcmd:discussion init <slug> --json}}` helpers. Resume existing
state with `{{specify-subcmd:discussion resume <slug> --json}}` instead of
reconstructing it from chat memory.

Use the live repository only to ground product boundaries, current behavior,
technical options, and constraints. Keep the visible conversation natural:
surface one decision cluster at a time, explain meaningful tradeoffs, and
distinguish confirmed decisions, working assumptions, rejected options, and
unresolved user choices.

Persist compact semantic checkpoints only when meaning changes; do not store a
transcript. Stay in discussion until the user explicitly requests a handoff.
Then write exactly one agent-only contract with
`{{specify-subcmd:discussion write-handoff <slug> --json}}`, validate it, review
its boundary against the confirmed decisions, and ask the user to confirm that
exact revision before `{{specify-subcmd:discussion mark-ready <slug> --json}}`.

Do not create feature state, a spec, plan, tasks, or production changes. A ready
handoff continues through `$spx-specify`; mark it consumed only after the
specification successfully incorporates it.
