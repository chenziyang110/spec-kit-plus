Trigger: when sp-quick starts from discussion or task handoff material.

Purpose: preserve quick handoff intake, compatibility fields, eligibility checks, and source scope boundaries.

Preserved Contract: quick consumes only bounded ready handoffs and escalates wider work back to specify/debug as appropriate.

## Discussion Handoff Intake

Resolve discussion handoff intake before quick-task execution.

Classify the supplied arguments before creating or resuming substantive quick-task execution:

- normal quick-task request
- `.specify/discussions/<slug>/handoff-to-specify.md`
- `.specify/discussions/<slug>/handoff-to-specify.json`
- `.specify/discussions/<slug>/handoff.md` or `.specify/discussions/<slug>/handoff.json` when a generated project has adopted neutral filenames
- a discussion `<slug>` whose workspace contains the unified handoff pair
- no arguments with exactly one unconsumed `status: handoff-ready` discussion whose `recommended_consumer` is `sp-quick` or whose JSON `consumer_eligibility.sp-quick.status` is `ready`

The `handoff-to-specify.*` filenames are compatibility names for a single unified `discussion_requirement_contract`. Do not look for or require `handoff-to-quick.*`, and do not create a second quick-specific handoff.

When a discussion handoff is selected, treat it as authoritative upstream input for the quick task and set:

- `SOURCE_HANDOFF_MD`
- `SOURCE_HANDOFF_JSON`
- `SOURCE_DISCUSSION_SLUG`

Require both Markdown and JSON companions. Missing Markdown or JSON is `blocked_by_handoff_integrity`; route back to `sp-discussion` to refresh the unified handoff instead of reconstructing it here.

Parse the JSON before quick-task execution and require:

- `entry_source: sp-discussion`
- `handoff_kind: discussion_requirement_contract` when present; legacy discussion handoffs without this field may continue only if all other gates pass
- canonical JSON `status: handoff-ready`
- a non-empty `review_digest` matching the current canonical handoff
- `quality_gate.status: user_confirmed` or `quality_gate.status: user-confirmed`
- `hard_unknown_count: 0`
- `open_conflict_count: 0`
- `consumer_eligibility.sp-quick.status: ready`
- a bounded `agent_requirement_contract.scope.in` with explicit exclusions in `scope.out`
- no planning constraint, consequence obligation, or reopen condition that requires specification first

If `consumer_eligibility.sp-quick.status` is blocked, the planning constraints require specification, the consequence model is unbounded, or the scope no longer fits one bounded quick-task workspace, stop and route to `{{invoke:specify}}` or back to `{{invoke:discussion}}` according to the handoff's `recommended_consumer` and blocker reason.

When a discussion handoff is accepted for quick, read only the agent-facing requirement contract first:

- `agent_requirement_contract.target_need`
- `agent_requirement_contract.constraints`
- `agent_requirement_contract.success_criteria`
- `agent_requirement_contract.design_direction`
- `agent_requirement_contract.optimal_solution_approach`
- `agent_requirement_contract.scope`
- `must_preserve`
- `discussion_decision_digest`
- `reopen_conditions` or `stop_and_reopen_conditions`

Read `discussion-log.jsonl`, `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` only when the unified handoff is stale, incomplete, contradictory, or explicitly references those files for evidence. Record inspected files in `source_files_read`.

Seed `STATUS.md` from the handoff before substantive work:

- `source_discussion_slug`
- `source_handoff_md`
- `source_handoff_json`
- `review_digest`
- `source_files_read`
- `locked_direction`
- `must_preserve`
- `reopen_conditions`
- `handoff_consumer: sp-quick`

Do not skip the Understanding Checkpoint. The accepted discussion handoff prepares the checkpoint; it does not replace user confirmation. Initialize or update `STATUS.md` with `understanding_confirmed: false`, then present the Quick Checkpoint from `agent_requirement_contract`, `planning_constraints`, and `must_preserve`.
