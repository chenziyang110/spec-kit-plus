# Quick And Debug Execution Design

Date: 2026-05-23

## Purpose

`sp-quick` currently tends to run from a short user request all the way through execution. That is useful for speed, but it gives the user too little chance to catch a misunderstood goal or wrong execution direction before the workflow changes files.

`sp-debug` currently presents debug work as mandatory-subagent execution. That is too heavy for small, focused investigations where the leader can inspect one failing path directly, while still being useful for broad or parallel evidence gathering.

This design changes the generated workflow contracts so:

- `sp-quick` performs one default understanding checkpoint before substantive execution.
- `sp-debug` chooses between leader-inline and subagent-assisted execution based on investigation complexity.

## `sp-quick` Understanding Checkpoint

`sp-quick` adds a default one-time confirmation gate after minimal context intake and before substantive planning, delegation, or source changes.

The checkpoint is lightweight. It is not a full spec, not a `sp-plan` substitute, and not a detailed task plan approval. Its job is to expose the agent's understanding before work proceeds.

Before the checkpoint, `sp-quick` may read the smallest necessary context and ask the minimum number of clarifying questions when the request cannot be understood safely.

Once enough information is available, the workflow must present:

- `Problem understood`: what the agent believes the user wants solved.
- `Planned outcome`: what result the agent intends to deliver.
- `Scope boundary`: what the agent will not do in this quick task.
- `Execution approach`: how the agent expects to proceed.
- `Validation`: what evidence will prove the quick task is complete.

The workflow then waits for user confirmation. If the user corrects the understanding, the workflow revises the checkpoint and asks again. Once the user confirms, `sp-quick` continues through its existing quick-task loop: workspace state, execution strategy, implementation, validation, summary, and learning capture when relevant.

`STATUS.md` should record the checkpoint so resumed work does not depend on chat memory. The status template should include:

- `understanding_confirmed: false | true`
- a compact confirmation summary covering the confirmed problem, outcome, scope boundary, approach, and validation evidence.

## `sp-debug` Complexity-Based Execution

`sp-debug` changes from mandatory-subagent execution to a two-path execution decision:

- Use `leader-inline` when the investigation is small, focused, and has a short evidence chain.
- Use `subagent-assisted` when the investigation has multiple independent evidence lanes, broad surface area, or meaningful parallelism.

Small focused debug work includes cases such as one failing test, one clear error, one local module, or one reproduction path. In this path, the leader can gather evidence, form hypotheses, make the fix, and verify directly, while still obeying the debug workflow's evidence-first rules.

Subagent-assisted debug work remains the right path when there are multiple plausible causes, multiple modules or logs to inspect, independent repro or verification lanes, configuration and runtime evidence to compare, or enough work that parallel evidence gathering materially improves confidence or speed.

The debug session remains leader-owned in both paths. Subagents may collect evidence or execute a bounded lane, but they must not own the debug session file, decide the final root cause, mark the session resolved, or archive the session.

The debug execution state should use these fields:

- `execution_model: leader-inline | subagent-assisted`
- `dispatch_shape: leader-inline | one-subagent | parallel-subagents`
- `execution_surface: leader-inline | native-subagents`
- `dispatch_reason`: why the leader chose inline work or subagent assistance.

The leader may change from `leader-inline` to `subagent-assisted` at a join point if the investigation grows beyond the original focused path.

## Invariants

The quick checkpoint does not relax quick-task scope control. `sp-quick` must still route to `sp-fast`, `sp-debug`, or `sp-specify` when the request belongs there.

The debug execution decision does not relax the debug safety contract:

- No speculative production fixes before evidence supports the failure mechanism.
- No production behavior change before a reproduction or equivalent evidence gate.
- The debug session file remains the source of truth.
- Root-cause claims must be supported by recorded evidence and eliminated alternatives.
- Verification evidence is required before any resolution claim.

## Change Surface

Primary implementation surfaces:

- `templates/commands/quick.md`
- `templates/command-partials/quick/shell.md`
- `templates/commands/debug.md`
- `templates/command-partials/debug/shell.md`

Synchronization surfaces that may need updates when tests expose drift:

- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `templates/passive-skills/subagent-driven-development/SKILL.md`
- `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
- README and project handbook wording that currently describes `sp-quick` or `sp-debug` as mandatory-subagent execution.
- Template and integration tests that lock dispatch wording.

This design should not start with a broad runtime rewrite. Runtime helpers or schemas should change only if existing tests or generated-surface requirements prove that template wording alone leaves contradictory behavior.

## Verification Plan

Template-focused verification should prove:

- `sp-quick` includes an `Understanding Checkpoint` before substantive execution.
- `sp-quick` records `understanding_confirmed`.
- `sp-quick` still resumes quick-task state and validates completion.
- `sp-debug` allows `leader-inline` for small focused investigations.
- `sp-debug` still uses `one-subagent` or `parallel-subagents` for broad or independent evidence lanes.
- `sp-debug` still states that subagents cannot own the debug session, final root-cause decision, or session closure.
- Documentation and passive-skill guidance no longer contradict the new quick/debug execution contracts.

Expected regression targets include:

- `tests/test_quick_template_guidance.py`
- `tests/test_debug_template_guidance.py`
- `tests/test_alignment_templates.py`
- Any integration tests that assert generated `quick` or `debug` command text.

## Out Of Scope

This design does not change `sp-implement`, `sp-map-scan`, `sp-map-build`, `sp-prd-scan`, or `sp-prd-build` execution rules.

This design does not add a multi-step approval process to `sp-quick`; it adds one default understanding checkpoint.

This design does not allow `sp-debug` to bypass evidence collection, reproduction, hypothesis recording, or verification.
