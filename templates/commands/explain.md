---
description: Use when the user needs the current stage artifact, project cognition state, or compatibility/export atlas artifact explained in plain language without changing the underlying files.
workflow_contract:
  when_to_use: The user needs to understand the current planning-stage artifact, project cognition state, or compatibility/export atlas view before deciding whether to continue, revise, or proceed.
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

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.
Shared or overlapping write/path scopes among packets force serial `one-subagent` (resume or re-dispatch); a parallel conflict is not permission for unrecorded Leader implementation.


## Outline

Goal: Read the current stage artifact, project cognition artifact, or explicitly requested compatibility/export atlas artifact and explain it in plain language so the user can understand what the system currently believes, what is decided, what is still open, and what the next phase or next relevant view will do.

1. Run `{SCRIPT}` from repo root once (`--json --paths-only` / `-Json -PathsOnly`) and parse the available feature paths.
   - If `FEATURE_DIR` is not already explicit, use a validated managed Run feature subject or the helper's unique paths-only result; stop on ambiguity instead of inferring the feature from a private Git ref or branch name.
   - When `SPECIFY_RUN_MANAGED=1`, verify the current directory equals `SPECIFY_RUN_WORKSPACE` before explaining artifacts.

2. Resolve the stage artifact deterministically:
   - If the user explicitly names a stage, honor it.
   - If the user explicitly asks about project cognition, touched-area state, or brownfield runtime truth, run `specify-runtime cognition status --format json` and the smallest matching `compass|query|expand` call first.
   - Explain handbook artifacts only when the user explicitly requests the compatibility/export surfaces themselves.
   - If the user explicitly asks for a compatibility/export handbook, `PROJECT-HANDBOOK.md`, `architecture`, `structure`, `conventions`, `integrations`, `workflows`, `testing`, or `operations` artifact, resolve that artifact directly.
   - Explain the architecture, cognition, or compatibility/export atlas artifact directly instead of forcing a planning-stage fallback.
   - Otherwise prefer the most advanced available artifact in this order:
     - `tasks` -> `FEATURE_DIR/tasks.md`
     - `plan` -> `FEATURE_DIR/plan.md`
     - `specify` -> `FEATURE_DIR/spec.md`
   - Supporting files:
- `specify`: also query `FEATURE_DIR/alignment.md` and `FEATURE_DIR/references.md` through `specify-runtime artifact show` if present
- `clarify`: query `FEATURE_DIR/spec.md`, `FEATURE_DIR/alignment.md`, and `FEATURE_DIR/references.md` through targeted `artifact show` calls, then explain the enhancement state
- `plan`: also query `FEATURE_DIR/research.md`, `FEATURE_DIR/data-model.md`, `FEATURE_DIR/contracts/`, and `FEATURE_DIR/quickstart.md` through `specify-runtime artifact show/list` when present
- `tasks`: also query `FEATURE_DIR/plan.md` and `FEATURE_DIR/spec.md` through `artifact show` when needed
     - `implement`: if there is no canonical implementation status artifact, explain that implementation status is unavailable from the current file set and fall back to the most recent planning artifact instead of guessing
     - `project cognition`: query `specify-runtime cognition status|compass|query|expand` for only the smallest matching slice needed to explain ownership, dependencies, lifecycle, change impact, or verification routes accurately
     - `compatibility/export atlas`: read the explicitly requested handbook plus the smallest supporting export files needed to explain ownership, dependencies, lifecycle, change impact, or verification routes accurately

3. Query registered workflow artifacts through targeted `specify-runtime artifact show` calls and read ordinary source/docs only when immediately needed for accuracy.
   - If present, query `.specify/memory/constitution.md` through `specify-runtime artifact show` so the explanation honors its constraints.

4. Before translating the artifact, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="explain", snapshot, workload_shape)`.
   - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
   - If repository inspection, artifact reading beyond already-provided context, or evidence cross-checking is needed, dispatch a bounded subagent lane before final explanation.
   - If the artifact is fully provided in the current prompt and no repository inspection is needed, the leader may render the explanation directly because no substantive repository task is being executed.
   - If required subagent dispatch is unavailable, record `subagent-blocked` and stop with the missing capability or packet requirement instead of treating coordinator-authored substantive work as the ordinary path.
   - If collaboration is justified, keep `explain` lanes limited to:
     - primary artifact reading
     - supporting artifact cross-check
   - Required join point:
     - before rendering the final explanation
   - Report the chosen strategy, reason, any `subagent-blocked` condition, and whether supporting cross-check lanes were used.

5. Translate the artifact into plain language:
   - what this stage is trying to accomplish
   - what has already been decided
   - what remains open or risky
   - what the next stage will do with this information
   - for project cognition and compatibility/export atlas views: explain verified facts, inferred relationships, important unknowns, and the next relevant cognition slice or export view

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
- `project cognition`: explain ownership, dependencies, lifecycle, change impact, confidence, and the next relevant cognition slice in plain language
- `compatibility/export atlas`: explain ownership, dependencies, lifecycle, change impact, confidence, and the next relevant export view in plain language

## Rules

- Keep the explanation grounded in the actual artifact on disk.
- Use subagent lanes for explanation work that needs repository inspection or artifact cross-checking; leader synthesis is limited to fully supplied prompt context with no substantive repository task.
- If a supporting cross-check lane is used, converge back to one final render step before presenting the explanation.
- Use the user's current language for user-visible output unless literal command names, file paths, or fixed status values must remain unchanged.
- Prefer clarity over jargon.
- Do not invent missing state; if something is absent, say it is absent.
