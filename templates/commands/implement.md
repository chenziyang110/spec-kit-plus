---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
Treat non-empty `$ARGUMENTS` as first-class implementation context for the current feature execution, not as disposable chat-only guidance.

## Role Definition

**⚠️ CRITICAL: [AGENT] markers denote MANDATORY execution**
All actions marked with **[AGENT]** are hard-coded procedural guardrails. The AI agent **MUST** explicitly execute these actions and is strictly forbidden from skipping them or simulating them in memory.

**⚠️ CRITICAL: Leader is the Orchestrator, not the Worker**

```
┌─────────────────────────────────────────────────────────────┐
│  Leader (You)                                               │
│  - Read planning docs and task lists                        │
│  - Select execution strategy                                │
│  - Compile WorkerTaskPacket                                 │
│  - Dispatch tasks to sub-agents                             │
│  - Collect results and validate                             │
│  - Advance across join points                               │
├─────────────────────────────────────────────────────────────┤
│  Worker (Sub-agent)                                         │
│  - Execute specific implementation tasks                    │
│  - Write code files                                         │
│  - Return structured results                                │
└─────────────────────────────────────────────────────────────┘
```

**Forbidden Actions**:
- ❌ Leader directly using `Write`/`Edit` tools to write code.
- ❌ Leader executing tasks locally by default.
- ❌ Skipping Agent dispatch to perform work directly.

**Mandatory Actions**:
- ✅ MUST use `Agent` tools for task dispatch.
- ✅ MUST wait for structured handoffs.
- ✅ MUST collect Worker results before proceeding.

---

## Hard Rules

| Rule | Description |
|------|-------------|
| **RULE-01** | Leader is forbidden from using Write/Edit tools directly to write code. |
| **RULE-02** | MUST compile a `WorkerTaskPacket` before dispatching. |
| **RULE-03** | MUST use Agent tools for task dispatch. |
| **RULE-04** | MUST wait for a structured handoff before proceeding. |
| **RULE-05** | Idle sub-agent ≠ Completed work. |

---

## Pre-Execution Checks

**Check for extension hooks (before implementation)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_implement` key.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    
    Wait for the result of the hook command before proceeding to the Outline.
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently.

## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command implement --format json` when available so passive learning files exist, the current implementation run sees relevant shared project memory, and repeated non-high-signal candidates can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader execution context.
- Review `.planning/learnings/candidates.md` only when it still contains implementation-relevant candidate learnings after the passive start step, especially repeated pitfalls, recovery paths, or project constraints for the touched area.
- Treat this as passive shared memory, not as a separate user-visible execution command.

## Implement Tracker Protocol

- `FEATURE_DIR/implement-tracker.md` is the execution-state source of truth for `sp-implement`.
- [AGENT] Create it if missing after `FEATURE_DIR` is known. If it already exists and is not terminal, resume from it instead of restarting from chat memory.
- Treat terminal states as `resolved` or `blocked`. Treat `gathering`, `executing`, `recovering`, `replanning`, and `validating` as resumable states.
- Update the tracker before each material phase transition: after scope recovery, before dispatching a ready batch, after each join point, before validation, when entering replanning, and before final completion reporting.
- The tracker must keep these fields obvious: `status`, `current_batch`, `next_action`, `completed_tasks`, `failed_tasks`, `retry_attempts`, `blockers`, `recovery_action`, `open_gaps`, `user_execution_notes`, and `resume_decision`.
- If the user supplied important execution details in `$ARGUMENTS`, extract and persist them in the tracker before dispatching work. Typical examples include:
  - build or compile order
  - startup commands
  - required environment setup
  - known failing commands to avoid
  - recovery hints the runtime must remember on future resumes
- Treat these notes as binding for the current implementation run unless direct evidence shows they are wrong. Do not drop them silently on resume.

### Tracker Structure

```markdown
---
status: gathering | executing | recovering | replanning | validating | blocked | resolved
feature: [feature slug]
created: [ISO timestamp]
updated: [ISO timestamp]
resume_decision: resume-here | blocked-waiting | resolved
---

## Current Focus
current_batch: [ready batch or validation pass]
goal: [current implementation objective]
next_action: [immediate next step]

## Execution Intent
intent_outcome: [the concrete outcome this batch is trying to deliver]
intent_constraints:
  - [forbidden drift, boundary rules, or execution constraints that stay active for this batch]
success_evidence:
  - [checks or observations required before the leader can accept this batch]

## Execution State
completed_tasks:
  - [task ids already completed]
in_progress_tasks:
  - [task ids currently running]
failed_tasks:
  - [task ids that failed in the current pass]
retry_attempts: [0 if none]

## Blockers
- task: [task id]
  type: technical | external | human-action
  evidence: [short command output or observed failure]
  recovery_action: [smallest safe next recovery step]

## Validation
planned_checks:
  - [independent tests, acceptance checks, or validation commands]
completed_checks:
  - [checks already run]
human_needed_checks:
  - [manual verification still required]

## Open Gaps
- type: execution_gap | research_gap | plan_gap | spec_gap
  summary: [what is still not true]
  source: [task id, validation check, or user-visible outcome]
  next_action: [specific next step]

## User Execution Notes
- note: [important user-supplied execution detail from `$ARGUMENTS`]
  source: sp-implement arguments
  priority: high | normal
  applies_to: current feature execution
```

## Outline

1. Run `{SCRIPT}` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. Use escape syntax for single quotes in args.

2. **Check checklists status** (if FEATURE_DIR/checklists/ exists):
   - Scan all checklist files in the checklists/ directory.
   - Count total, completed, and incomplete items.
   - Create a status table.
   - **If any checklist is incomplete**: STOP and ask: "Some checklists are incomplete. Do you want to proceed with implementation anyway? (yes/no)".

3. Load and analyze the implementation context:
   - **REQUIRED**: [AGENT] Create or resume `FEATURE_DIR/implement-tracker.md` immediately after `FEATURE_DIR` is known.
   - **IF TRACKER EXISTS WITH STATUS `blocked` OR `replanning`**: Read `blockers`, `open_gaps`, `recovery_action`, and `next_action` first.
   - **REQUIRED**: Check whether `.specify/project-map/status.json` exists and assess freshness.
   - **IF FRESHNESS IS `missing` OR `stale`**: Run `/sp-map-codebase` before continuing.
   - **REQUIRED**: [AGENT] Read `PROJECT-HANDBOOK.md` and the smallest relevant combination of `.specify/project-map/*.md`.
   - **REQUIRED**: Read `.specify/memory/constitution.md`, `project-rules.md`, and `project-learnings.md` if present.
   - **REQUIRED**: Read `tasks.md` for the complete task list and `plan.md` for tech stack/architecture.
   - **REQUIRED FOR DELEGATED EXECUTION**: Compile and validate a `WorkerTaskPacket` for each delegated task.
   - **REQUIRED FOR DELEGATED EXECUTION**: [AGENT] The leader must wait for and consume the structured handoff before closing the join point.
   - **HARD RULE**: Dispatch only from validated `WorkerTaskPacket`. Do not dispatch from raw task text alone.

4. **Project Setup Verification**:
   - **REQUIRED**: Create/verify ignore files (.gitignore, .dockerignore, .eslintignore, etc.) based on actual project setup and tech stack.

## Step 3: Parse Tasks

5. Parse `tasks.md` structure and extract:
   - Task phases, dependencies, IDs, descriptions, file paths, and parallel markers [P].
   - Identify parallel batches and join points.

## Step 4: Select Strategy

6. Select an execution strategy for each ready batch before writing code:

### Strategy Decision Table

| Scenario | Recommended Strategy | Decision Logic |
|------|----------|----------|
| **Default / Sequential Tasks** | `single-agent` | `parallel_batches <= 0` or presence of `overlapping_writes` |
| **Independent Parallel Tasks** | `native-multi-agent` | `native_multi_agent` supported and confidence is not `low` |
| **Complex / Special Environments** | `sidecar-runtime` | `sidecar_runtime_supported` and native is unsupported |

**⚠️ IMPORTANT**: `single-agent` still means dispatching via an Agent, not Leader self-execution!

## Step 5: Compile WorkerTaskPacket (Mandatory)

**HARD RULE**: MUST compile a `WorkerTaskPacket` before dispatching! Use the following structure:

```markdown
# WorkerTaskPacket

## Task Information
task_id: [Task ID]
description: [Task Description]

## Output Files
files_to_create: [Files to create]
files_to_modify: [Files to modify]

## Constraints & References
constraints:
  - [Forbidden behaviors / mandatory standards]
references:
  - [Related file paths]

## Success Criteria
success_criteria:
  - [Completion standards]
```

## Step 6: Dispatch Tasks

7. Execute implementation following the task plan:
   - **Phase-by-phase execution**: Complete each phase before moving to the next.
   - **Autonomous Loop**: You **MUST** continue processing next ready sequential tasks automatically without stopping after a single task. Stop only at **Join Points** or when a phase is complete.
   - **Respect dependencies**: Run sequential tasks in order; run [P] tasks in parallel batches.

   **Dispatch Command Template**:
   ```bash
   Agent(
     name="[worker-name]",
     prompt="[WorkerTaskPacket content]",
     subagent_type="general-purpose"
   )
   ```

8. Implementation execution rules:
   - **Setup first**: Initialize project structure, dependencies, configuration.
   - **Tests before code**: Write tests for contracts, entities, and integration scenarios.
   - **Core development**: Implement models, services, CLI commands, endpoints.
   - **Integration work**: Database connections, middleware, logging, external services.
   - **Polish and validation**: Unit tests, performance optimization, documentation.

## Step 7: Collect Results

9. Progress tracking and error handling:
   - Report progress after each completed task.
   - **Halt execution if any non-parallel task fails.**
   - **REQUIRED**: MUST wait for and parse structured `WorkerTaskResult`.
   - **WorkerTaskResult Structure**:
     ```json
     {
       "task_id": "[Task ID]",
       "status": "DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT",
       "changed_files": ["File list"],
       "validation_evidence": "Validation evidence",
       "blockers": { "summary": "...", "failed_assumption": "..." }
     }
     ```
   - Persist state in `implement-tracker.md` immediately.
   - Attempt smallest safe recovery before blocking.
   - **IMPORTANT**: Mark completed tasks as [X] in the tasks file.

## Step 8: Validate Completion

10. Completion validation:
   - Enter `validating` status in tracker after the last implementation task is complete.
   - Verify all required tasks match the original specification.
   - If gaps exist, record `open_gaps` (execution_gap, research_gap, plan_gap, or spec_gap).
   - Only mark `resolved` after the validation pass is truthfully green.
   - [AGENT] Before final completion report, capture any new `pitfall`, `recovery_path`, or `project_constraint` learning.

## Step 9: Extension Hooks

11. Check and execute `hooks.after_implement` from `.specify/extensions.yml`.
