Trigger: before task decomposition or remediation from a prior task/analyze blocker.

Purpose: preserve pre-execution checks, learning intake, phase lock, feature directory resolution, project cognition advisory behavior, and required inputs.

Preserved Contract: sp-tasks remains task-generation-only and must not implement code or edit source/test files.

## Pre-Execution Checks

**Check for extension hooks (before tasks generation)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_tasks` key
{{spec-kit-include: ../../command-partials/common/extension-hooks-body.md}}

**Maintain workflow quality without hook choreography**:
- Confirm project cognition freshness and valid workflow entry before decomposition continues.
- Keep `workflow-state.md` current as the durable source of truth for phase, allowed artifact writes, next action, and exit criteria.
- Verify the final `tasks.md` and `workflow-state.md` outputs before handoff instead of relying on chat narration.
- Update durable state before compaction-risk transitions, major task-batch synthesis handoffs, or any stop where resume will depend on more than the visible conversation.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command tasks --format json}}` when available so passive learning files exist, the current task-generation run sees relevant shared project memory, and repeated high-signal lessons can be surfaced through the learning index at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader task-generation context.
- Open only learning detail docs linked from task-generation-relevant index entries, especially repeated workflow gaps, project constraints, or validation misses that should influence task decomposition.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- [AGENT] When task-shaping friction exposes artifact rewrites, route changes, false starts, hidden dependencies, validation gaps, or reusable constraints, make sure `workflow-state.md` captures that durable context.
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command tasks --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints.
- [AGENT] When the durable state does not capture the reusable lesson cleanly, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.
- Treat this as passive shared memory, not as a separate user-visible workflow.

## Workflow Phase Lock

- [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial task-generation analysis.
- Read `templates/workflow-state-template.md`.
- If `WORKFLOW_STATE_FILE` is missing, recreate it from the template and the current spec/plan package instead of continuing from chat memory alone.
- Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth on resume after compaction for the current command, allowed artifact writes, forbidden actions, authoritative files, next action, and exit criteria.
- Set or update the state for this run with at least:
  - `active_command: sp-tasks`
  - `phase_mode: task-generation-only`
  - `forbidden_actions: edit source code, edit tests, implement behavior, start execution from task-generation artifacts`
- Do not implement code, edit source files, edit tests, or treat task generation as permission to start execution.
- Implementation remains blocked until this task package passes the Implementation-Readiness Task Self-Audit and `WORKFLOW_STATE_FILE` records `next_command: /sp.implement`. Run `{{invoke:analyze}}` only when an existing state file explicitly records a legacy or diagnostic analysis route.
- If `WORKFLOW_STATE_FILE` records a blocked `sp-analyze` gate with `next_command: /sp.tasks`, enter remediation mode before regenerating `tasks.md`.
- In remediation mode, read the prior `Analyze Gate` blocker bundle first. Do not start from a blank task-generation pass.
- No more than one task-layer remediation cycle is expected. If repeated `sp-tasks -> sp-analyze` loops occur for blockers that were detectable before remediation, treat that as a previous analyze miss or a tasks self-audit failure. Do not treat repeated task/analyze loops as normal workflow.
- Hand off directly to `{{invoke:implement}}` from `sp-tasks` after a clean self-audit. Preserve `{{invoke:analyze}}` only when explicit legacy or diagnostic workflow state requires that route.
- When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.
