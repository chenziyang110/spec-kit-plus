Trigger: when creating, resuming, recovering, closing, or archiving a quick-task workspace.

Purpose: preserve `.planning/quick` workspace layout, STATUS.md scaffold, recovery routing, lifecycle commands, and learning capture.

Preserved Contract: STATUS.md remains the source of truth and quick-task workspaces stay recoverable and id-based.

## Quick-Task Workspace Protocol

- Every quick task must have a dedicated id-based workspace under `.planning/quick/<id>-<slug>/`.
- If a matching active workspace already exists, resume it instead of creating a second parallel quick-task directory for the same goal.
- The minimum artifact set is:
  - `STATUS.md`: the source of truth for the current quick-task state.
  - `SUMMARY.md`: the final outcome, `changed_code_paths`, `changed_behavior_surfaces`, verification evidence, residual risk, and `project_cognition_refresh` outcome.
  - Optional lightweight support artifacts only when needed for the task shape, such as `PLAN.md`, `RESEARCH.md`, or `DISCUSSION.md`.
- `STATUS.md` is the lifecycle source of truth for the quick task. `.planning/quick/index.json` is a derived projection for management and recovery commands.
- The quick-task directory format is `<id>-<slug>`. Do not use slug-only workspace names for the enhanced quick flow.
- Constitution read is the first hard gate. `STATUS.md` initialization comes immediately after it.
- `STATUS.md` must stay compact and overwrite the active state rather than growing into a long log. It must always make these fields obvious:
  - current focus
  - execution strategy
  - active lane or batch
  - join point, if any
  - blocked dispatch or escalation state, if any
  - next action
  - recovery action
  - retry attempts
  - blocker reason
  - blockers, if any
- Update `STATUS.md` before each material phase transition: after scope lock, after planning, before delegation, after each join point, before validation, and before final summary.
- After the constitution gate, `STATUS.md` initialization is the next hard gate. Do not perform substantial repository analysis, implementation design, or code reading beyond scope-lock context until the workspace exists and the first lane is recorded.
- When the quick task completes, preserve `SUMMARY.md` and move resolved state under `.planning/quick/resolved/` if the local project convention prefers archiving over keeping active quick-task folders in place.

## STATUS.md Scaffold

Use the fixed artifact scaffold instead of writing the fixed `STATUS.md` skeleton by hand.
The scaffold renders the `STATUS.md template`; valid lifecycle values are
`status: gathering | planned | executing | validating | blocked | resolved`.

Command shape:

```text
{{specify-subcmd:artifact scaffold --kind quick-status --out ".planning/quick/<id>-<slug>/STATUS.md" --vars "<compact-json>" --format json}}
```

`--out` must be project-relative. Do not pass an absolute path. The scaffold is create-only and returns `agent_fill_required` plus `fill_targets`; write semantic quick-task content only at those returned anchors.

The compact JSON variables are:

- `id`: quick-task id
- `slug`: quick-task slug
- `title`: short quick-task title
- `trigger`: verbatim user input

The generated scaffold initializes `understanding_confirmed: false`, `status: gathering`, `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, and `execution_surface: native-subagents`. It also creates fixed sections for discussion handoff source, current focus, execution intent, understanding checkpoint, execution, validation, summary pointer, and senior consequence analysis. The agent must fill the semantic values through the returned `fill_targets` and keep `STATUS.md` compact.

## Recovery Routing

- `sp-quick <description>` creates a new quick task.
- Empty `sp-quick` should look for unfinished quick tasks before asking for a new description.
- If exactly one unfinished quick task exists, resume it automatically.
- If multiple unfinished quick tasks exist, ask the user which quick task to continue.
- The selection list should show `id`, title, current status, and `next_action`.
- Treat `gathering`, `planned`, `executing`, `validating`, and `blocked` as unfinished quick-task states for recovery routing.
- If resuming a `blocked` quick task, prioritize `blocker_reason`, `recovery_action`, and `next_action` before widening scope.

## Lifecycle Commands

- `close` controls lifecycle semantics. Use it to place a quick task into `resolved` or `blocked`.
- `archive` controls storage semantics. Use it only after the quick task has already been closed.
- Do not treat archive as an implied synonym for resolved. Closure says what happened; archive says where the closed task now lives.

{{spec-kit-include: ../../command-partials/common/learning-layer.md}}

**This command tier: light.** Auto-capture learnings on resolution only. No review, no signal.
