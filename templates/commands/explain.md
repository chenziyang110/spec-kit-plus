---
description: Explain the current stage artifact in plain language with a structured terminal presentation.
handoffs:
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Build a plan once the user is satisfied with the current stage understanding.
  - label: Generate Tasks
    agent: sp.tasks
    prompt: Generate tasks from the current implementation plan.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --paths-only
  ps: scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

Goal: Read the current stage artifact and explain it in plain language so the user can understand what the system currently believes, what is decided, what is still open, and what the next phase will do.

1. Run `{SCRIPT}` from repo root once (`--json --paths-only` / `-Json -PathsOnly`) and parse the available feature paths.

2. Resolve the stage artifact deterministically:
   - If the user explicitly names a stage, honor it.
   - Otherwise prefer the most advanced available artifact in this order:
     - `tasks` -> `FEATURE_DIR/tasks.md`
     - `plan` -> `FEATURE_DIR/plan.md`
     - `specify` -> `FEATURE_DIR/spec.md`
   - Supporting files:
     - `specify`: also read `FEATURE_DIR/alignment.md` and `FEATURE_DIR/references.md` if present
     - `spec-extend`: read `FEATURE_DIR/spec.md`, `FEATURE_DIR/alignment.md`, and `FEATURE_DIR/references.md` together, then explain the enhancement state as an extension of the current spec package
     - `plan`: also read `FEATURE_DIR/research.md`, `FEATURE_DIR/data-model.md`, `FEATURE_DIR/contracts/`, and `FEATURE_DIR/quickstart.md` when present
     - `tasks`: also read `FEATURE_DIR/plan.md` and `FEATURE_DIR/spec.md` when needed for explanation
     - `implement`: if there is no canonical implementation status artifact, explain that implementation status is unavailable from the current file set and fall back to the most recent planning artifact instead of guessing

3. Read the resolved artifact and any immediately supporting artifact needed to explain it accurately.

4. Translate the artifact into plain language:
   - what this stage is trying to accomplish
   - what has already been decided
   - what remains open or risky
   - what the next stage will do with this information

5. Present the explanation as a structured terminal UI, not a raw dump.

## TUI Requirements

The output should use a polished terminal presentation with:

- a stage banner
- a status card
- a main narrative section
- an open-risk panel
- a next-step panel

The explanation must remain stage-aware:

- `specify`: explain the requirement package and what it means in everyday terms
- `plan`: explain the implementation approach in plain language
- `tasks`: explain what concrete work is about to happen
- `implement`: explain progress, current scope, and active risks

## Rules

- Keep the explanation grounded in the actual artifact on disk.
- Use the user's current language for user-visible output unless literal command names, file paths, or fixed status values must remain unchanged.
- Prefer clarity over jargon.
- Do not invent missing state; if something is absent, say it is absent.
