# SP Plan/Tasks Adaptive Lightweight Design

**Date:** 2026-05-22
**Status:** Approved for implementation planning
**Scope:** `sp-plan`, `sp-tasks`, command-scoped adaptive execution guidance, orchestration dispatch policy/model, generated workflow docs, and regression tests that currently lock mandatory subagent behavior and default test-heavy task generation.
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
- Persist blocked dispatch decisions explicitly when risk requires subagents but the work cannot be delegated safely.
- Update tests and docs so they protect the adaptive policy rather than the old `subagent-mandatory` blanket rule.

## Non-Goals

- Do not remove subagent support from `sp-plan` or `sp-tasks`.
- Do not weaken high-risk gates for schema changes, protocol seams, security-sensitive surfaces, native/plugin bridges, generated API surfaces, cross-project targets, or reference-fidelity work.
- Do not change deliberately heavyweight workflows such as `sp-prd-scan`, `sp-prd-build`, `sp-map-scan`, or `sp-map-build` in this pass.
- Do not make `sp-implement` leader-inline by default as part of this change.
- Do not eliminate tests from task generation; make them risk and behavior driven.

## Proposed Design

### 1. Adaptive Execution Classification

`sp-plan` and `sp-tasks` should classify the current workload before deciding whether to delegate or block.

The classification has three modes:

- `light`: Single bounded planning or task-generation lane, low-risk write surface, no cross-project target ambiguity, no schema/protocol/security/shared registration changes, no unresolved `CA-*` or `MP-*` obligations that require independent synthesis, no reference-fidelity checkpoint, and no obvious benefit from parallel evidence collection.
- `standard`: Two or more isolated lanes, meaningful parallelism, cross-module impact, or enough constraints that structured lane handoffs reduce drift.
- `heavy`: High-risk boundary work, schema or migration changes, security-sensitive changes, protocol seams, generated API surfaces, native/plugin bridges, cross-project implementation targets, reference implementation fidelity, deep-research planning handoffs, or consequence obligations that require explicit operational design and verification mapping.

`light` mode allows leader-inline planning or task generation. `standard` and `heavy` modes keep structured handoffs when delegated; `standard` may degrade to leader-inline only under the native-unavailable rule below, while `heavy` blocks unless a safe delegated execution surface is available.

Native availability rules are explicit:

- `light` mode does not require native subagents.
- `standard` mode uses native subagents when available. If native subagents are unavailable, the workflow may continue leader-inline only when no high-risk trigger is present, the leader can still preserve the required artifacts honestly, and the downgrade is recorded with `capability_degraded: true`.
- `heavy` mode requires native subagents or an explicitly selected durable team workflow outside this pass. If neither is available, the workflow blocks with `dispatch_shape: subagent-blocked`; it must not silently fall back to leader-inline.
- Managed-team fallback is not part of this `sp-plan`/`sp-tasks` adaptive pass. If future work wants managed-team fallback, it should be designed as a separate durable coordination path.

The classification should be recorded in `workflow-state.md` and the generated report:

```text
execution_model: adaptive
execution_mode: light | standard | heavy
workflow_status: ready | blocked
dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked
execution_surface: leader-inline | native-subagents | none
capability_degraded: false | true
mode_reason: <short evidence-backed reason>
blocked_reason: <required when workflow_status is blocked>
```

### 2. Shared Dispatch Policy

The shared orchestration policy should stop returning mandatory subagent decisions for every ordinary command. It should support an adaptive execution model.

For this pass, the policy can be scoped to `plan` and `tasks` while preserving current behavior for commands that still require mandatory subagent execution.

Expected behavior:

- If `command_name` is `plan` or `tasks` and `workload_shape.lightweight_safe` is true, return `dispatch_shape: leader-inline`, `execution_surface: leader-inline`, `workflow_status: ready`, and `execution_model: adaptive`.
- If the workload has one safe delegated lane and native subagents are available, return `one-subagent`.
- If the workload has multiple safe delegated lanes and native subagents are available, return `parallel-subagents`.
- If the workload is `standard`, native subagents are unavailable, and no high-risk trigger is present, return `leader-inline` with `capability_degraded: true` and a reason such as `standard-native-unavailable-leader-inline`.
- If the workload is `heavy`, or if any high-risk trigger makes delegation safety-critical, and native subagents are unavailable or the work cannot be packetized safely, return `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason`.

This preserves fail-closed behavior where delegation is required for safety while avoiding unnecessary delegation for low-risk work.

The policy contract should not rely on one invented boolean alone. The implementation should provide either a classifier helper or a documented `workload_shape` schema with these minimum keys:

```text
lightweight_safe: bool
safe_subagent_lanes: int
packet_ready: bool
native_subagents_available: bool
high_risk: bool
touches_schema_or_migration: bool
touches_security_sensitive_surface: bool
touches_protocol_or_generated_api: bool
touches_native_or_plugin_bridge: bool
touches_shared_registration_surface: bool
cross_project_target: bool
reference_fidelity_required: bool
deep_research_handoff_required: bool
consequence_obligations_require_independent_synthesis: bool
```

`lightweight_safe` should be derived from the negative case of these risk keys plus the single-lane criterion, not hand-authored independently by each template. Tests should cover the classifier or the schema interpretation so `sp-plan` and `sp-tasks` do not drift.

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

The minimum light-mode `tasks.md` contract is:

- Task ID, checkbox, phase or story label, and concrete objective.
- Target file path, write scope, or explicit path discovery step.
- Required context pointers using `file.md#section-heading` where plan or spec context matters.
- Dependencies or `none`.
- Constraints and forbidden drift when inherited from `plan.md`, `context.md`, `plan-contract.json`, or memory files.
- Validation command or concrete manual check.
- Done condition.
- Test task, or an explicit no-new-test rationale with replacement validation and residual risk.

If a later `sp-implement` run decides the light task package needs native subagent packets, it should be able to compile them from these fields. If it cannot, implementation must route back to `sp-tasks` for packet enrichment instead of guessing missing write scopes or acceptance criteria.

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
sp-plan and sp-tasks use adaptive execution: leader-inline for low-risk single-lane planning or task generation, native subagents for standard/heavy work when available, recorded leader-inline degradation for standard work when native subagents are unavailable and no high-risk trigger is present, and blocked dispatch for heavy or safety-critical work that cannot be delegated safely.
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
  -> native subagent dispatch when available
  -> standard may record capability_degraded and continue leader-inline only when no high-risk trigger is present
  -> planning handoffs + evidence index + checkpoints
  -> synthesize core planning package
  -> next_command: /sp.tasks
```

Blocked heavy `sp-plan`:

```text
sp-plan
  -> classify workload as heavy or safety-critical
  -> native subagents unavailable or lane cannot be packetized safely
  -> workflow_status: blocked
  -> dispatch_shape: subagent-blocked
  -> blocked_reason recorded in workflow-state.md
  -> stop before planning synthesis
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
  -> native subagent dispatch when available
  -> standard may record capability_degraded and continue leader-inline only when no high-risk trigger is present
  -> task-generation handoffs + evidence index + checkpoints
  -> tasks.md + handoff/task-index/task-packets
  -> join points, review gates, validation commands
  -> next_command: /sp.implement
```

Blocked heavy `sp-tasks`:

```text
sp-tasks
  -> classify workload as heavy or safety-critical
  -> native subagents unavailable or lane cannot be packetized safely
  -> workflow_status: blocked
  -> dispatch_shape: subagent-blocked
  -> blocked_reason recorded in workflow-state.md
  -> stop before task synthesis
```

## Files Expected to Change

Primary surfaces:

- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- A new adaptive execution partial used by `plan` and `tasks`; avoid changing the shared mandatory subagent partial unless the change is strictly backward-compatible for workflows that remain mandatory
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
- `standard` and `heavy` modes preserve native subagent dispatch and structured handoffs when native subagents are available.
- `standard` mode records `capability_degraded: true` when it continues leader-inline because native subagents are unavailable.
- `heavy` mode blocks when native subagents are unavailable and no explicitly selected durable team workflow exists.
- High-risk work that cannot be packetized safely persists `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, and `blocked_reason` instead of silently downgrading to leader-inline.
- The workload classifier or documented `workload_shape` schema is implemented and tested rather than leaving `lightweight_safe` as an ad hoc template boolean.
- `sp-plan` delegation artifacts are required only when delegated planning lanes are used.
- `sp-tasks` enriched packet and task-generation artifacts are mode-sensitive rather than always mandatory.
- Light-mode `tasks.md` includes the minimum downstream contract required for later packet compilation.
- `sp-tasks` uses risk and behavior driven validation instead of blanket test generation.
- When task generation omits tests, it records the omission reason, replacement validation, and residual risk.
- README and handbook describe adaptive execution for `sp-plan` and `sp-tasks`.
- Regression tests protect adaptive behavior and no longer require `subagent-mandatory` for `plan` and `tasks`.
- Existing high-risk mandatory-subagent workflows remain protected by tests.
- Tests prove the shared mandatory subagent partial still protects workflows that remain mandatory.

## Risks and Mitigations

- **Risk:** Agents overuse `light` mode to skip useful decomposition.
  **Mitigation:** Define high-risk triggers explicitly and require mode reason evidence in `workflow-state.md`.

- **Risk:** Downstream `sp-implement` expects task packets that light mode omits.
  **Mitigation:** Keep the minimum light-mode `tasks.md` contract strong enough for later packet compilation, and route back to `sp-tasks` when packet compilation would require guessing.

- **Risk:** Removing default test tasks reduces regression coverage.
  **Mitigation:** Require tests by default for behavior, bugfix, refactor, API, persistence, security, and generated-output risk, and require explicit omission rationale otherwise.

- **Risk:** Shared orchestration model changes ripple into other workflows.
  **Mitigation:** Scope adaptive behavior to `plan` and `tasks` first; prefer a new adaptive partial or command-scoped branch, and leave intentionally mandatory workflows unchanged.

- **Risk:** Template tests become too loose after removing blanket wording assertions.
  **Mitigation:** Replace wording locks with behavioral contracts for classification, dispatch choices, artifact conditionality, and validation requirements.

## Open Decisions

- Scope the first implementation to `sp-plan` and `sp-tasks`.
- Keep `sp-prd-scan`, `sp-prd-build`, `sp-map-scan`, and `sp-map-build` mandatory-subagent for now.
- Keep `sp-implement` behavior unchanged in this pass.
- Allow light mode to omit planning/task-generation handoff metadata only when no delegated lanes are used.
- Treat omitted tests as acceptable only with a recorded reason, replacement validation path, and residual risk.
- Persist blocked adaptive dispatch as `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, and `blocked_reason`.
- Permit standard-mode leader-inline degradation only when native subagents are unavailable and no high-risk trigger is present.
