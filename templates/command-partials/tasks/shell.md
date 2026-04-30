{{spec-kit-include: ../common/user-input.md}}

## Objective

Convert the plan package into dependency-aware execution tasks that preserve planning guardrails, expose parallel-safe batches, and make implementation resumable.

## Context

- Primary inputs: `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `context.md`, and the handbook/project-map set.
- Working state lives in `FEATURE_DIR/tasks.md` plus any decomposition metadata needed for later analysis or implementation routing.
- This command is task-generation-only. It should not cross into execution.

## Process

- Load the current plan package and recover the active workflow-state context.
- Carry locked planning decisions and implementation constitution rules forward into execution slices.
- Generate dependency ordering, parallel-safe batches, join points, and guardrail indexes.
- Validate the resulting task graph before handing off to analysis or implementation.

## Output Contract

- Write `tasks.md` as the authoritative execution breakdown for the current feature.
- Make execution ordering, parallelization boundaries, and required verification steps explicit.
- Preserve the guardrail information later subagent execution packets and leaders must consume.

### Subagent-Ready Task Contract

Every task written into `tasks.md` MUST carry the enriched fields below so that a worker subagent can read a single task body and begin work immediately — without asking the leader for clarification, without exploring the codebase to discover conventions, and without guessing acceptance criteria.

**Identity & Ordering**

- `agent`: Role from the agent-teams pool assigned to this task. Choose from: `security-reviewer`, `test-engineer`, `style-reviewer`, `performance-reviewer`, `quality-reviewer`, `api-reviewer`, `debugger`, `code-simplifier`, `build-fixer`, `git-master`, `executor`. Default to `executor` when no specialist role matches.
- `depends_on`: List of task IDs (with one-line descriptions) that must complete before this task can start.
- `parallel_safe`: `true` when this task's `write_scope` has zero overlap with any other task in the same ready batch, and no shared-state conflicts exist. Otherwise `false`.

**Context Navigation (pointers only — do not duplicate content)**

- Provide a table mapping each piece of knowledge the worker needs to its precise location: `file.md#section-heading`. Include at minimum: the relevant design decision from plan.md, the data model entity from data-model.md, the API contract from contracts/, and a reference implementation in the repo that follows the same pattern (if one exists).

**Scope Boundaries**

- `write_scope`: Exact list of files this task will create or modify.
- `read_scope`: Files and directories the worker may read but not modify.
- `forbidden`: Paths the worker MUST NOT touch. Always include `.env`, credential files, secrets directories, and any config surfaces the task does not own.

**Expected Outputs & Anti-Goals**

- `expected_outputs`: Concrete file list with annotations: `（新建）` or `（修改）`.
- `anti_goals`: Behaviors explicitly forbidden for this task. Examples: "do not introduce new dependencies", "do not modify the public API surface", "do not touch the database schema".

**Acceptance & Verification**

- `acceptance_criteria`: Verifiable, objective conditions — not subjective judgments.
- `verify_commands`: Runnable shell commands the worker executes to self-validate before handing off. Include the exact test runner, linter, and type-check commands.

**Handoff Format**

- `status`: `success` | `failed` | `blocked`
- `changed_files`: Precise list of paths modified
- `validation_output`: Map of command → output for each verify command
- `concerns`: Issues the leader should know about (empty list if none)
- `recovery_hints`: If failed or blocked, the smallest safe recovery step

**Failure & Escalation**

- `retry_max`: Maximum retry attempts before escalation (default `2`).
- `escalation`: Role to escalate to after retries are exhausted (default `debugger`).

### Independent Executability Gate

Before finalizing any task, confirm: a single subagent, reading only this task body plus the pointed-to context files, can complete the work without asking the leader a single question. If the answer is no, the task is not ready — refine it until it is.

## Guardrails

- Do not implement code, edit tests, or treat task generation as implicit execution approval.
- Do not emit raw task lists that lose boundary rules, locked decisions, or verification expectations.
- Do not assume stale or overly broad repository-map coverage is good enough for decomposition.
