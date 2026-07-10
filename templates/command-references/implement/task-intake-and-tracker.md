Trigger: before selecting or resuming implementation work.

Purpose: recover compact execution truth and current task context without reloading the full upstream package.

Preserved Contract: implementation remains resumable, task-driven, evidence-backed, and honest about blockers and completion.

## Intake

1. Resolve the active feature lane/worktree.
2. Read execution state first, then canonical `task-index.json` or the light direct task list.
3. Validate task-graph revision, current ready batch, dependencies, and relevant repository baseline.
4. Load only the current task's required refs and live touched-area evidence.
5. Load constitution/rules/learning details only when the task graph lacks a current ref or the selected area has a known relevant lesson.
6. Do not reread the full spec/plan/discussion package unless revision drift, evidence conflict, or a stop/reopen condition requires it.

If the current task's required refs are stale, missing, or contradicted by live code, run at most one task-local navigation intake before expanding reads:

Run or emulate:

```text
{{specify-subcmd:project-cognition compass --intent implement --query="$ARGUMENTS" --format json}}
```

Use `compass_state`, `minimal_live_reads`, `first_pass_paths`, `coverage_diagnostics`, and `expansion_ref` only to repair the current task context; they do not replace live proof or authorize a broader implementation scope.

## Execution State

Keep compact agent state with status, current batch/task, next action, completed/failed task IDs, retry count, blockers, recovery, open gaps, validation state, and binding user execution notes. Update at semantic transitions: task start, result acceptance/failure, triggered review, validation, replanning, and terminal closeout—not every tool call.

`implement-tracker.md` remains a compatibility state surface where required by existing hooks. Treat it as agent-only and avoid explanatory prose or duplicated upstream truth.

## Resume Audit

On uncertain or terminal-looking resume, treat checked tasks as claims. Run `{{specify-subcmd:implement resume-audit --feature-dir "$FEATURE_DIR" --format json}}` when available and validate result, required consumer evidence, validation, obligations, open gaps, and worker handoff freshness.

If audit fails, move to recovery/validation and continue from the smallest executable repair. Do not preserve resolved status from appearance alone.
