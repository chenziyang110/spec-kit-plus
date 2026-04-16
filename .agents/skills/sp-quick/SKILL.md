---
name: "sp-quick"
description: "Execute a small ad-hoc task through a lightweight planning and validation path."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/quick.md"
---

## User Input

```text
$ARGUMENTS
```

## Objective
Execute a small, ad-hoc task through a lightweight planning and validation path without entering the full `specify -> plan -> tasks` workflow.

This command will skip the full feature-spec workflow while preserving lightweight planning and verification.

Use this for work that is too large for `sp-fast` but still too small or too well understood to justify a full spec flow: small bug fixes, small features, focused UX adjustments, template tweaks, or narrow CLI behavior changes.

## Scope Gate

Use `sp-quick` when all of these are true:
- The task is bounded and clearly described.
- The work is small but non-trivial.
- A lightweight plan is useful, but a full spec package would be overhead.
- The task does not require a new long-lived feature spec under `specs/<feature>/`.

If the task is trivial and local:
- Use `/sp-fast`.

If the task changes architecture, introduces broad product decisions, or needs a durable feature specification:
- Use `/sp-specify`.

## Execution Modes

The following flags are available and composable:
- `--discuss`: Do a lightweight clarification pass before planning.
- `--research`: Investigate implementation approaches before planning.
- `--validate`: Add plan checking and post-execution verification.
- `--full`: Equivalent to `--discuss --research --validate`.

## Process

1. **Scope gate**
   - Confirm the task is small but non-trivial.
   - Redirect to `/sp-fast` or `/sp-specify` if the task is outside the quick-task band.

2. **Create lightweight quick-task context**
   - Track the task under `.planning/quick/`.
   - Keep quick-task artifacts separate from the main phase/spec workflow.

3. **Optional pre-execution phases**
   - If `--discuss` is present, clarify assumptions and lock the minimum decisions needed.
   - If `--research` is present, gather focused implementation guidance.

4. **Lightweight planning**
   - Produce only the plan needed to execute this ad-hoc task safely.
   - Keep the work atomic and self-contained.

5. **Execution**
   - Implement the task.
   - Keep changes tightly scoped to the quick-task goal.

6. **Validation**
   - If `--validate` or `--full` is present, perform plan checking and post-execution verification.
   - Otherwise still verify the change with the smallest meaningful check.

7. **Summary**
   - Write a concise summary artifact for what changed and how it was verified.
   - Prefer `SUMMARY.md` in the quick-task area or an equivalent quick-task summary artifact.

## Guardrails

- Do not create a new full feature spec for quick tasks.
- Keep quick-task tracking under `.planning/quick/`.
- Preserve a lightweight planning and validation path rather than skipping discipline entirely.
- Keep quick tasks atomic and self-contained.
