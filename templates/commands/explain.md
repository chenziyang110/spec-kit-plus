---
description: Use when the user needs the current stage artifact or handbook/project-map atlas artifact explained in plain language without changing the underlying files.
workflow_contract:
  when_to_use: The user needs to understand the current planning-stage artifact or handbook/project-map atlas view before deciding whether to continue, revise, or proceed.
  primary_objective: Translate the current artifact into plain language while staying faithful to what is actually on disk.
  primary_outputs: A structured explanation only; do not rewrite stage artifacts or atlas documents unless another command explicitly requests it.
  default_handoff: /sp-plan or /sp-tasks only after the user is satisfied with the current understanding and wants to advance.
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

{{spec-kit-include: ../command-partials/explain/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Outline

Goal: Read the current stage artifact or atlas artifact and explain it in plain language so the user can understand what the system currently believes, what is decided, what is still open, and what the next phase or next relevant atlas view will do.

1. Run `{SCRIPT}` from repo root once (`--json --paths-only` / `-Json -PathsOnly`) and parse the available feature paths.

2. Resolve the stage artifact deterministically:
   - If the user explicitly names a stage, honor it.
   - If the user explicitly asks about handbook, `PROJECT-HANDBOOK.md`, `project-map`, `architecture`, `structure`, `conventions`, `integrations`, `workflows`, `testing`, or `operations`, resolve that artifact directly.
   - Explain the architecture or atlas artifact directly instead of forcing a planning-stage fallback.
   - Otherwise prefer the most advanced available artifact in this order:
     - `tasks` -> `FEATURE_DIR/tasks.md`
     - `plan` -> `FEATURE_DIR/plan.md`
     - `specify` -> `FEATURE_DIR/spec.md`
   - Supporting files:
     - `specify`: also read `FEATURE_DIR/alignment.md` and `FEATURE_DIR/references.md` if present
     - `clarify`: read `FEATURE_DIR/spec.md`, `FEATURE_DIR/alignment.md`, and `FEATURE_DIR/references.md` together, then explain the enhancement state as an extension of the current spec package
     - `plan`: also read `FEATURE_DIR/research.md`, `FEATURE_DIR/data-model.md`, `FEATURE_DIR/contracts/`, and `FEATURE_DIR/quickstart.md` when present
     - `tasks`: also read `FEATURE_DIR/plan.md` and `FEATURE_DIR/spec.md` when needed for explanation
     - `implement`: if there is no canonical implementation status artifact, explain that implementation status is unavailable from the current file set and fall back to the most recent planning artifact instead of guessing
     - `handbook/project-map`: read the resolved atlas artifact plus the smallest supporting handbook/project-map files needed to explain ownership, dependencies, lifecycle, change impact, or verification routes accurately

3. Read the resolved artifact and any immediately supporting artifact needed to explain it accurately.
   - If present, also read `.specify/memory/constitution.md` so the explanation honors the project constitution and its constraints on the current stage artifact.

4. Before translating the artifact, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="explain", snapshot, workload_shape)`.
   - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
   - Default to leader explanation for small artifacts. Dispatch a cross-check subagent only when an independent verification lane would materially improve correctness.
   - If collaboration is justified, keep `explain` lanes limited to:
     - primary artifact reading
     - supporting artifact cross-check
   - Required join point:
     - before rendering the final explanation
   - Report the chosen strategy, reason, fallback if any, and whether supporting cross-check lanes were used.

5. Translate the artifact into plain language:
   - what this stage is trying to accomplish
   - what has already been decided
   - what remains open or risky
   - what the next stage will do with this information
   - for handbook/project-map atlas views: explain verified facts, inferred relationships, important unknowns, and the next relevant atlas view

6. Present the explanation as a structured terminal UI built from open blocks, not a raw dump.

## TUI Requirements

The output should use a polished terminal presentation with:

- a stage header
- a status block
- an explanation block
- a risk block
- a next-step block

The explanation must remain stage-aware:

- `specify`: explain the requirement package and what it means in everyday terms
- `plan`: explain the implementation approach in plain language
- `tasks`: explain what concrete work is about to happen
- `implement`: explain progress, current scope, and active risks
- `handbook/project-map`: explain ownership, dependencies, lifecycle, change impact, confidence, and the next relevant atlas view in plain language

## Rules

- Keep the explanation grounded in the actual artifact on disk.
- Default to leader explanation for small artifacts unless the artifact genuinely benefits from a supporting cross-check lane.
- If a supporting cross-check lane is used, converge back to one final render step before presenting the explanation.
- Use the user's current language for user-visible output unless literal command names, file paths, or fixed status values must remain unchanged.
- Prefer clarity over jargon.
- Do not invent missing state; if something is absent, say it is absent.
