# SP Plan/Tasks Adaptive Lightweight Design

**Date:** 2026-05-22
**Status:** Approved for implementation planning
**Scope:** `sp-plan`, `sp-tasks`, shared subagent execution guidance, orchestration dispatch policy/model, generated workflow docs, and regression tests that currently lock mandatory subagent behavior and default test-heavy task generation.
**Primary goal:** Make `sp-plan` and `sp-tasks` default to the lightest safe workflow while preserving the current heavyweight subagent and packet path for work that actually benefits from it.

## Context

`sp-plan` and `sp-tasks` currently treat native subagent dispatch as mandatory once a validated lane exists. The shared `subagent-execution` partial says ordinary `sp-*` workflows must use subagents for substantive work, and both `sp-plan` and `sp-tasks` persist `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, and `execution_surface: native-subagents`.

That posture protects complex work, but it makes ordinary planning and task decomposition expensive. A small low-risk plan can still be forced through lane checkpointing, structured handoffs, evidence indexes, and join points. `sp-tasks` also defaults tests into the public task graph for behavior changes, bug fixes, refactors, and regression-sensitive modules, and can add bootstrap testing work even when the operator's real need is a fast, bounded task list.

The desired product behavior is not to remove subagents or tests. The desired behavior is adaptive: default light, upgrade when risk, scale, isolation, or verification needs justify the extra machinery.

## Goals

- Allow `sp-plan` and `sp-tasks` to run leader-inline for low-risk, single-lane, artifact-focused work.
- Preserve native subagent dispatch for medium and high-risk planning or decomposition where independent lanes and structured handoffs add real value.
- Make planning and task-generation metadata conditional instead of always mandatory.
- Keep behavior, bugfix, refactor, and regression-sensitive work test-aware without forcing heavyweight test scaffolding for docs-only, process-only, config-only, or low-risk artifact changes.
- Keep generated artifacts explicit enough that downstream `sp-implement` can still execute safely.
- Update tests and docs so they protect the adaptive policy rather than the old `subagent-mandatory` blanket rule.

## Non-Goals

- Do not remove subagent support from `sp-plan` or `sp-tasks`.
- Do not weaken high-risk gates for schema changes, protocol seams, security-sensitive surfaces, native/plugin bridges, generated API surfaces, cross-project targets, or reference-fidelity work.
- Do not change deliberately heavyweight workflows such as `sp-prd-scan`, `sp-prd-build`, `sp-map-scan`, or `sp-map-build` in this pass.
- Do not make `sp-implement` leader-inline by default as part of this change.
- Do not eliminate tests from task generation; make them risk and behavior driven.

## Proposed Design

### 1. Adaptive Execution Classification

`sp-plan` and `sp-tasks` should classify the current workload before deciding whether to delegate.

The classification has three modes:

- `light`: Single bounded planning or task-generation lane, low-risk write surface, no cross-project target ambiguity, no schema/protocol/security/shared registration changes, no unresolved `CA-*` or `MP-*` obligations that require independent synthesis, no reference-fidelity checkpoint, and no obvious benefit from parallel evidence collection.
- `standard`: Two or more isolated lanes, meaningful parallelism, cross-module impact, or enough constraints that structured lane handoffs reduce drift.
- `heavy`: High-risk boundary work, schema or migration changes, security-sensitive changes, protocol seams, generated API surfaces, native/plugin bridges, cross-project implementation targets, reference implementation fidelity, deep-research planning handoffs, or consequence obligations that require explicit operational design and verification mapping.

`light` mode allows leader-inline planning or task generation. `standard` and `heavy` modes use native subagents when available and keep structured handoffs.

The classification should be recorded in `workflow-state.md` and the generated report:

```text
execution_model: adaptive
execution_mode: light | standard | heavy
dispatch_shape: leader-inline | one-subagent | parallel-subagents
execution_surface: leader-inline | native-subagents
mode_reason: <short evidence-backed reason>
```

### 2. Shared Dispatch Policy

The shared orchestration policy should stop returning mandatory subagent decisions for every ordinary command. It should support an adaptive execution model.

For this pass, the policy can be scoped to `plan` and `tasks` while preserving current behavior for commands that still require mandatory subagent execution.

Expected behavior:

- If `command_name` is `plan` or `tasks` and `workload_shape.lightweight_safe` is true, return `dispatch_shape: leader-inline`, `execution_surface: leader-inline`, and `execution_model: adaptive`.
- If the workload has one safe delegated lane, return `one-subagent`.
- If the workload has multiple safe delegated lanes, return `parallel-subagents`.
- If the workload is high risk but cannot be packetized safely, mark the workflow blocked rather than silently downgrading to leader-inline.

This preserves fail-closed behavior where delegation is required for safety while avoiding unnecessary delegation for low-risk work.

### 3. `sp-plan` Artifact Rules

`sp-plan` should always produce the core planning package:

- `plan.md`
- `research.md`, which may be compact when no external or uncertain technical research is needed
- `quickstart.md`
- `plan-contract.json`
- `workflow-state.md`

Conditional artifacts remain conditional:

- `data-model.md` only when the feature introduces entities, state transitions, persistence, or structured data contracts.
- `contracts/` only when the feature introduces or changes external interfaces, APIs, cross-service contracts, generated APIs, or protocol boundaries.

Delegation artifacts become conditional:

- `planning/handoffs/<lane-id>.json`
- `planning/evidence-index.json`
- `planning/checkpoints.ndjson`

These are required only when `standard` or `heavy` mode uses delegated planning lanes. In `light` mode, the plan should state that no delegated planning lanes were used and why.

### 4. `sp-tasks` Artifact Rules

`sp-tasks` should always produce:

- `tasks.md`
- `workflow-state.md`

`tasks.md` remains the human-readable authority and must still be immediately executable.

Machine-readable decomposition artifacts become mode-sensitive:

- `light`: `task-index.json` is optional but recommended when cheap; `handoff-to-tasks.json`, `task-packets/*.json`, `task-generation/handoffs/*`, `task-generation/evidence-index.json`, and `task-generation/checkpoints.ndjson` are optional unless needed by downstream execution or an existing integration contract.
- `standard`: Produce `handoff-to-tasks.json`, `task-index.json`, and task packets for tasks expected to be delegated by `sp-implement`.
- `heavy`: Produce the full enriched task contract set, including task-generation handoffs, evidence index, checkpoints, guardrail mapping, join points, and packet fields.

In `light` mode, each task still needs enough context to be executable, but it does not need the full subagent-ready task contract block when the task can be completed by the leader or by a future implementer using the pointed-to plan sections.

### 5. Test and Validation Strategy in Tasks

Replace the blanket "tests are default deliverables" framing with risk and behavior driven validation.

Task generation should add test tasks by default when work changes:

- Product behavior
- Bugfix behavior
- Refactored logic with regression risk
- Public API contracts
- Persistence or migration behavior
- Security-sensitive behavior
- Generated outputs that are consumed by users or other tools

Task generation may omit new tests when the work is clearly:

- Docs-only
- Process-only
- Prompt/template wording only with existing snapshot or template assertions judged sufficient
- Config-only with a more appropriate lint or smoke validation
- Low-risk artifact maintenance where a focused command or manual check is the honest validation path

When omitting tests, `tasks.md` must record:

- The reason no new test task is needed.
- The validation command or manual check that replaces it.
- Any residual risk.

If the touched area lacks a reliable automated test surface, `sp-tasks` should add the smallest runnable test surface only when the change risk requires automated proof. It should not force broad test infrastructure bootstrap for every low-risk task package.

### 6. Review Gates and Join Points

Review gates and join points should also be risk-sensitive.

Required for `heavy` mode:

- Explicit join points after delegated parallel batches.
- Review checkpoint for shared registration surfaces, schema/migration work, protocol seams, native/plugin bridges, generated API surfaces, security-sensitive changes, or reference-fidelity deviations.
- Peer-review lane when an independent read-only lane is available and useful.

Optional for `light` mode:

- A simple verification note can replace formal join points.
- Review gate may be omitted when there is no shared write surface or high-risk boundary.

### 7. Documentation and Operator Language

README and handbook guidance should describe the new posture as:

```text
sp-plan and sp-tasks use adaptive execution: leader-inline for low-risk single-lane planning or task generation, native subagents for standard/heavy work where independent lanes, structured handoffs, or risk gates materially improve correctness.
```

Docs should avoid implying that all ordinary `sp-*` workflows are still blanket `subagent-mandatory`. They can still call out workflows that remain intentionally mandatory.

### 8. Regression Test Updates

Tests that currently assert `execution_model: subagent-mandatory` for every ordinary command should be split into two contracts:

- Commands that remain mandatory subagent workflows still assert `subagent-mandatory`.
- `plan` and `tasks` assert adaptive execution language, leader-inline light mode, native-subagent standard/heavy mode, and fail-closed behavior when high-risk work cannot be packetized safely.

Template tests should stop protecting incidental wording and instead protect:

- `light | standard | heavy` mode classification exists.
- Light mode allows leader-inline.
- Standard/heavy mode preserves native subagent dispatch.
- Delegation artifacts are conditional on delegated lanes.
- Test tasks are risk and behavior driven.
- Omitted tests require a validation reason and residual risk.

## Data Flow

Light `sp-plan`:

```text
sp-plan
  -> classify workload as light
  -> leader-inline synthesis
  -> plan.md / research.md / quickstart.md / plan-contract.json / workflow-state.md
  -> no planning handoffs required
  -> next_command: /sp.tasks
```

Standard or heavy `sp-plan`:

```text
sp-plan
  -> classify workload as standard/heavy
  -> packetize planning lanes
  -> native subagent dispatch
  -> planning handoffs + evidence index + checkpoints
  -> synthesize core planning package
  -> next_command: /sp.tasks
```

Light `sp-tasks`:

```text
sp-tasks
  -> classify workload as light
  -> leader-inline task generation
  -> tasks.md + workflow-state.md
  -> optional compact task-index.json
  -> validation notes or targeted tests by risk
  -> next_command: /sp.implement
```

Standard or heavy `sp-tasks`:

```text
sp-tasks
  -> classify workload as standard/heavy
  -> packetize decomposition lanes
  -> native subagent dispatch
  -> task-generation handoffs + evidence index + checkpoints
  -> tasks.md + handoff/task-index/task-packets
  -> join points, review gates, validation commands
  -> next_command: /sp.implement
```

## Files Expected to Change

Primary surfaces:

- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/command-partials/common/subagent-execution.md`, or a new adaptive execution partial used by `plan` and `tasks`
- `src/specify_cli/orchestration/models.py`
- `src/specify_cli/orchestration/policy.py`
- `tests/orchestration/test_policy.py`
- `tests/test_subagent_mandatory_template_guidance.py`
- `tests/test_alignment_templates.py`
- `tests/test_tasks_reporting_guidance.py`
- `README.md`
- `PROJECT-HANDBOOK.md`

Likely secondary surfaces:

- `tests/integrations/test_cli.py`
- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_toml.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_codex.py`
- `tests/test_extension_skills.py`
- `tests/test_passive_skill_guidance.py`

Secondary tests should change only where generated integration output snapshots or wording checks assert the older blanket mandatory-subagent contract.

## Acceptance Criteria

- `sp-plan` guidance supports `light`, `standard`, and `heavy` execution modes.
- `sp-tasks` guidance supports `light`, `standard`, and `heavy` execution modes.
- `light` mode allows leader-inline execution for low-risk single-lane planning or task generation.
- `standard` and `heavy` modes preserve native subagent dispatch and structured handoffs.
- High-risk work that cannot be packetized safely still blocks instead of silently downgrading to leader-inline.
- `sp-plan` delegation artifacts are required only when delegated planning lanes are used.
- `sp-tasks` enriched packet and task-generation artifacts are mode-sensitive rather than always mandatory.
- `sp-tasks` uses risk and behavior driven validation instead of blanket test generation.
- When task generation omits tests, it records the omission reason, replacement validation, and residual risk.
- README and handbook describe adaptive execution for `sp-plan` and `sp-tasks`.
- Regression tests protect adaptive behavior and no longer require `subagent-mandatory` for `plan` and `tasks`.
- Existing high-risk mandatory-subagent workflows remain protected by tests.

## Risks and Mitigations

- **Risk:** Agents overuse `light` mode to skip useful decomposition.
  **Mitigation:** Define high-risk triggers explicitly and require mode reason evidence in `workflow-state.md`.

- **Risk:** Downstream `sp-implement` expects task packets that light mode omits.
  **Mitigation:** Keep `tasks.md` executable and require `standard/heavy` packet generation whenever downstream delegated implementation is expected.

- **Risk:** Removing default test tasks reduces regression coverage.
  **Mitigation:** Require tests by default for behavior, bugfix, refactor, API, persistence, security, and generated-output risk, and require explicit omission rationale otherwise.

- **Risk:** Shared orchestration model changes ripple into other workflows.
  **Mitigation:** Scope adaptive behavior to `plan` and `tasks` first; leave intentionally mandatory workflows unchanged.

- **Risk:** Template tests become too loose after removing blanket wording assertions.
  **Mitigation:** Replace wording locks with behavioral contracts for classification, dispatch choices, artifact conditionality, and validation requirements.

## Open Decisions

- Scope the first implementation to `sp-plan` and `sp-tasks`.
- Keep `sp-prd-scan`, `sp-prd-build`, `sp-map-scan`, and `sp-map-build` mandatory-subagent for now.
- Keep `sp-implement` behavior unchanged in this pass.
- Allow light mode to omit planning/task-generation handoff metadata only when no delegated lanes are used.
- Treat omitted tests as acceptable only with a recorded reason, replacement validation path, and residual risk.
