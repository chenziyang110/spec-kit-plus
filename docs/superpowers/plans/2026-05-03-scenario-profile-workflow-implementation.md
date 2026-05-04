# Scenario Profile Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `sp-*` 工作流落地首批 `scenario profile` 机制，在不分裂主模板家族的前提下，给 `Standard Delivery` 和 `Reference-Implementation` 提供显式路由、模板覆盖、门禁继承和证据型收口。

**Architecture:** 这次实现严格限定为“共享核心模板 + profile contract + 首批两类 profile”。修改主要落在 `templates/commands/*.md`、`templates/*-template.md`、`templates/workflow-state-template.md`、`src/specify_cli/hooks/*` 的状态/产物校验层，以及对应的模板/钩子测试。第一阶段不引入独立大模板，不扩展到 `Brownfield Enhancement` 或 `Debug / Repair` 的完整执行逻辑，只把它们保留为 taxonomy 术语，不接入首批运行面。

**Tech Stack:** Markdown templates, Python (`specify_cli` hooks/serializers), pytest

---

## File Structure

| File | Responsibility | Change Type |
|------|----------------|-------------|
| `templates/spec-template.md` | 承载 shared skeleton，并新增 profile-aware 的 spec 必填区和约束提示 | modify |
| `templates/plan-template.md` | 承载 profile contract 消费位、Reference-Implementation 的 constitution 强化位 | modify |
| `templates/tasks-template.md` | 承载 profile-aware task shaping、fidelity checkpoint、evidence carry-forward 提示 | modify |
| `templates/workflow-state-template.md` | 承载 durable `profile contract` 字段 | modify |
| `templates/commands/specify.md` | 工作流入口路由、profile activation、workflow-state 持久化 | modify |
| `templates/commands/plan.md` | 消费 profile contract，并转译为 constitution / planning checks | modify |
| `templates/commands/tasks.md` | 消费 profile contract，并转译为 task shaping / evidence rules | modify |
| `templates/commands/implement.md` | 消费 profile contract，并执行 profile-specific exit evidence discipline | modify |
| `src/specify_cli/hooks/checkpoint_serializers.py` | 解析 workflow-state 中的 profile contract 关键字段 | modify |
| `src/specify_cli/hooks/state_validation.py` | 保持现有 phase validation，并为 profile state presence 提供基础校验 | modify |
| `src/specify_cli/hooks/artifact_validation.py` | 对 profile-required artifact sections 做首批校验 | modify |
| `tests/test_alignment_templates.py` | 模板 contract 测试，验证 command/template 文案和 gate 约束 | modify |
| `tests/hooks/test_state_hooks.py` | workflow-state serializer / validate-state 测试 | modify |
| `tests/hooks/test_artifact_hooks.py` | artifact validation 针对 profile-required sections 的测试 | modify |
| `tests/contract/test_hook_cli_surface.py` | hook CLI surface 对 profile fields 的 JSON 输出测试 | modify |
| `docs/superpowers/specs/2026-05-03-scenario-profile-workflow-design.md` | 设计基线，只读参考，不修改 | read-only |

## Delivery Scope

本计划只实现首批最小可落地切片：

- shared core templates 保持单骨架
- 引入 durable `profile contract`
- 首批支持 `Standard Delivery` 和 `Reference-Implementation`
- `sp-specify -> sp-plan -> sp-tasks -> sp-implement` 全链路继承同一合同
- 首批只做文档/模板/validator 层的强约束，不做额外 runtime orchestration 子系统

明确不做：

- 多套完整模板家族
- `Brownfield Enhancement` / `Debug / Repair` 的全量 wiring
- 新建隐藏式自动路由引擎而不落文档/状态
- 让 `sp-implement` 二次推断任务类型

## Verification Commands

计划中的最小可信验证命令集：

```bash
pytest tests/test_alignment_templates.py -q
pytest tests/hooks/test_state_hooks.py tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q
pytest tests/integrations/test_cli.py -q -k "shared_workflow_skills or shared_infra_skips_existing_files"
```

如果模板 contract 改动波及面更大，再补跑：

```bash
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

---

### Task 1: Extend Workflow State With Durable Profile Contract

**Files:**
- Modify: `templates/workflow-state-template.md`
- Modify: `src/specify_cli/hooks/checkpoint_serializers.py`
- Test: `tests/hooks/test_state_hooks.py`
- Test: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Write the failing state-serialization test for profile fields**

Add a test in `tests/hooks/test_state_hooks.py` that writes a `workflow-state.md`
fixture containing these new sections and expects them to round-trip through
`workflow.state.validate` data:

```markdown
## Scenario Profile

- active_profile: `reference-implementation`
- routing_reason: reference fidelity is the primary success condition
- confidence_level: `high`

## Profile Obligations

- required_sections: Fidelity Requirements, Profile Activation
- activated_gates: profile-required-sections, profile-required-evidence
- task_shaping_rules: fidelity-checkpoints, deviation-review
- required_evidence: comparison-evidence, deviation-log
- transition_policy: explicit-only
```

Expected assertion shape:

```python
assert payload["data"]["checkpoint"]["active_profile"] == "reference-implementation"
assert "comparison-evidence" in payload["data"]["checkpoint"]["required_evidence"]
```

- [ ] **Step 2: Run the new test and verify it fails for missing serialized fields**

Run:

```bash
pytest tests/hooks/test_state_hooks.py -q
```

Expected: FAIL because `serialize_workflow_state()` does not yet expose
`active_profile`, `routing_reason`, `confidence_level`, or the profile
obligation lists.

- [ ] **Step 3: Update the shared workflow-state template with profile sections**

In `templates/workflow-state-template.md`, insert new sections after `## Phase Mode`
and before `## Allowed Artifact Writes`:

```markdown
## Scenario Profile

- active_profile: `standard-delivery | reference-implementation | brownfield-enhancement | debug-repair`
- routing_reason: fidelity to the reference object is the primary success condition
- confidence_level: `high | medium | low`

## Profile Obligations

- required_sections:
  - Fidelity Requirements
- activated_gates:
  - fidelity-required-sections
- task_shaping_rules:
  - fidelity-checkpoints
- required_evidence:
  - comparison-evidence
- transition_policy: `sticky-unless-explicit-transition`
```

Do not remove any existing sections.

- [ ] **Step 4: Extend `serialize_workflow_state()` to parse the new sections**

In `src/specify_cli/hooks/checkpoint_serializers.py`, update
`serialize_workflow_state()` to read:

- `Scenario Profile`
- `Profile Obligations`

and return:

```python
"active_profile": extract_field(scenario_profile, "active_profile"),
"routing_reason": extract_field(scenario_profile, "routing_reason"),
"confidence_level": extract_field(scenario_profile, "confidence_level"),
"required_sections": _extract_named_list(profile_obligations, "required_sections"),
"activated_gates": _extract_named_list(profile_obligations, "activated_gates"),
"task_shaping_rules": _extract_named_list(profile_obligations, "task_shaping_rules"),
"required_evidence": _extract_named_list(profile_obligations, "required_evidence"),
"transition_policy": extract_field(profile_obligations, "transition_policy"),
```

Implement `_extract_named_list()` as a focused helper that reads nested bullets
under one list label without changing the behavior of existing parsers.

- [ ] **Step 5: Re-run the state tests and verify they pass**

Run:

```bash
pytest tests/hooks/test_state_hooks.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS, including the new assertions for serialized profile fields.

- [ ] **Step 6: Commit**

```bash
git add templates/workflow-state-template.md src/specify_cli/hooks/checkpoint_serializers.py tests/hooks/test_state_hooks.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: add profile contract fields to workflow state"
```

---

### Task 2: Make `sp-specify` The Explicit Profile Routing Point

**Files:**
- Modify: `templates/commands/specify.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write the failing template guidance test for profile routing**

In `tests/test_alignment_templates.py`, add assertions to the
`test_specify_template_uses_alignment_first_contract` coverage block, or add a
new focused test, requiring `templates/commands/specify.md` to contain all of:

```python
assert "## Scenario Profile Routing" in content
assert "active_profile" in content
assert "routing_reason" in content
assert "Reference-Implementation" in content
assert "If the success criterion is fidelity to a reference object" in content
assert "persist at least these fields for the active pass" in content
assert "required_sections" in content
assert "activated_gates" in content
```

- [ ] **Step 2: Run the template test and verify it fails**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: FAIL because `specify.md` does not yet define scenario-profile routing.

- [ ] **Step 3: Add explicit profile routing guidance to `specify.md`**

In `templates/commands/specify.md`, after task classification and before deeper
decomposition, add a new subsection:

```markdown
## Scenario Profile Routing

Infer one active profile for this feature lifecycle and persist it into
`workflow-state.md`. Use this priority:

1. user-explicit profile selection
2. `Reference-Implementation` when the primary success criterion is fidelity to a reference object
3. `Debug / Repair` when diagnosis and corrective recovery are the dominant objective
4. `Brownfield Enhancement` when safe evolution of an existing system is the dominant risk
5. `Standard Delivery` otherwise

For the first release, only `Standard Delivery` and `Reference-Implementation`
are active implementation profiles. The other taxonomy terms may be recorded as
future-facing classifications but must not activate unsupported downstream gates.
```

Then update both `Workflow Phase Lock` field lists to persist:

```markdown
- `active_profile: standard-delivery | reference-implementation`
- `routing_reason: fidelity to a named reference object is the primary success condition`
- `confidence_level: high | medium | low`
- `required_sections: Overview, Scope Boundaries, Scenarios, Success Criteria`
- `activated_gates: baseline-artifact-completeness`
- `task_shaping_rules: story-oriented-decomposition`
- `required_evidence: behavior-validation`
- `transition_policy: sticky-unless-explicit-transition`
```

Document the first-release obligation mapping inline:

- `Standard Delivery`
  - `required_sections`: Overview, Scope Boundaries, Scenarios, Success Criteria
  - `activated_gates`: baseline-artifact-completeness
  - `task_shaping_rules`: story-oriented decomposition
  - `required_evidence`: behavior-validation
- `Reference-Implementation`
  - `required_sections`: Fidelity Requirements, Canonical References
  - `activated_gates`: fidelity-required-sections, fidelity-required-evidence
  - `task_shaping_rules`: fidelity-checkpoints, deviation-review
  - `required_evidence`: comparison-evidence, deviation-log, fidelity-audit

- [ ] **Step 4: Re-run the template test and verify it passes**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: PASS for the new routing contract assertions.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/specify.md tests/test_alignment_templates.py
git commit -m "feat: add scenario profile routing to sp-specify"
```

---

### Task 3: Add Profile-Aware Shared Template Overlays

**Files:**
- Modify: `templates/spec-template.md`
- Modify: `templates/plan-template.md`
- Modify: `templates/tasks-template.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write failing template assertions for shared overlay surfaces**

Add assertions in `tests/test_alignment_templates.py` requiring:

For `templates/spec-template.md`:

```python
assert "## Fidelity Requirements" in content
assert "copy-exact" in content.lower() or "reference-implementation" in content.lower()
assert "reference object" in content.lower()
```

For `templates/plan-template.md`:

```python
assert "reference fidelity contract" in content.lower()
assert "profile-driven implementation constraints" in content.lower() or "profile obligations" in content.lower()
```

For `templates/tasks-template.md`:

```python
assert "Fidelity Checkpoint" in content
assert "Deviation Review" in content
assert "required evidence" in content.lower()
```

- [ ] **Step 2: Run the template test and verify it fails**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: FAIL because the shared templates are not yet profile-aware.

- [ ] **Step 3: Extend `spec-template.md` with a profile-aware fidelity section**

In `templates/spec-template.md`, insert after `## Implementation-Oriented Analysis`
or before `## Decision Capture`:

```markdown
## Fidelity Requirements *(required for `Reference-Implementation` profile)*

### Reference Object

- Preserve the named reference object, its truth-owning boundary, and the implementation shape that downstream work must not bypass.

### Required Fidelity

- Keep structure, behavior, and interface semantics aligned with the approved reference object.
- Do not drift at lifecycle, protocol, or boundary ownership seams that the reference object defines.

### Allowed Deviations

- Record every user-approved deviation together with rationale and downstream impact.
- If no deviations are allowed, write `No approved deviations.` instead of omitting the section silently.
```

Keep this as a shared template overlay section, not a separate template.

- [ ] **Step 4: Extend `plan-template.md` to consume profile obligations explicitly**

Add a new section after `## Locked Planning Decisions`:

```markdown
## Scenario Profile Inputs

### Active Profile

- `Reference-Implementation` is active because fidelity to the named reference object is the primary success condition for this feature.

### Profile-Driven Implementation Constraints

- Carry forward the active profile's required sections, gates, task-shaping rules, and required evidence from `workflow-state.md`.
- Preserve every profile-activated reference, gate, and evidence type as a downstream implementation constraint rather than reinterpreting it later.
```

Then strengthen the `Implementation Constitution` guidance by adding:

```markdown
- Preserve the reference fidelity contract whenever the active profile requires structural or behavioral alignment with a named reference object.
```

and include wording that these constraints are part of a `reference fidelity contract`
when the profile is `Reference-Implementation`.

- [ ] **Step 5: Extend `tasks-template.md` with profile-aware execution gates**

In `templates/tasks-template.md`, add to `Planning Inputs`:

```markdown
- **Scenario profile inputs**: Carry forward the active profile, activated gates, task-shaping rules, and required evidence from `workflow-state.md` and `plan.md`
```

Add to `Task Shaping Rules`:

```markdown
- If the active profile is `Reference-Implementation`, add explicit `Fidelity Checkpoint` tasks after each meaningful implementation batch.
- If any implementation intentionally diverges from the reference fidelity contract, add a `Deviation Review` task before the next downstream batch continues.
```

Add to `Phase 0: Implementation Guardrails`:

```markdown
- [ ] T002 Confirm the active profile and list its required evidence before implementation batches begin
```

- [ ] **Step 6: Re-run the template tests and verify they pass**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: PASS for the new shared-template profile overlay assertions.

- [ ] **Step 7: Commit**

```bash
git add templates/spec-template.md templates/plan-template.md templates/tasks-template.md tests/test_alignment_templates.py
git commit -m "feat: add profile-aware overlays to shared workflow templates"
```

---

### Task 4: Wire `sp-plan` To Consume The Profile Contract

**Files:**
- Modify: `templates/commands/plan.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add a failing plan-template guidance assertion**

Extend `tests/test_alignment_templates.py` so `test_plan_template_requires_alignment_report_before_planning`
or a new focused test requires `templates/commands/plan.md` to contain:

```python
assert "Scenario Profile Inputs" in content
assert "Read `FEATURE_DIR/workflow-state.md` if present" in content
assert "active_profile" in content
assert "Profile-Driven Implementation Constraints" in content
assert "Reference-Implementation" in content
assert "do not perform a second informal task classification pass" in content.lower()
```

- [ ] **Step 2: Run the template test and verify it fails**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: FAIL because `plan.md` does not yet consume the profile contract explicitly.

- [ ] **Step 3: Update `templates/commands/plan.md` to consume profile state**

In the `Load context` list, make `workflow-state.md` semantically required when present
for profile-aware planning:

```markdown
- Read `FEATURE_DIR/workflow-state.md` if present and treat `active_profile`, `required_sections`, `activated_gates`, `task_shaping_rules`, and `required_evidence` as planning inputs, not as status-only metadata
```

In the outline where planning artifacts are synthesized, add:

```markdown
- Add `Scenario Profile Inputs` using the active profile and obligations recorded in `workflow-state.md`
- If the active profile is `Reference-Implementation`, promote fidelity-preservation rules into `Implementation Constitution`
- Do not perform a second informal task classification pass; consume the existing profile contract unless an explicit transition decision is recorded
```

Add a plan-level rule that first-release profile support is limited to
`Standard Delivery` and `Reference-Implementation`.

- [ ] **Step 4: Re-run the template test and verify it passes**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: PASS for the plan contract assertions.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/plan.md tests/test_alignment_templates.py
git commit -m "feat: wire scenario profile inputs into sp-plan"
```

---

### Task 5: Wire `sp-tasks` To Compile Profile-Specific Task Shaping

**Files:**
- Modify: `templates/commands/tasks.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add a failing task-generation guidance assertion**

Extend `tests/test_alignment_templates.py` so the `tasks` coverage requires:

```python
assert "Scenario profile inputs" in content
assert "fidelity checkpoints" in content.lower()
assert "deviation review" in content.lower()
assert "required evidence" in content.lower()
assert "consume the same profile contract" in content.lower() or "active profile" in content.lower()
```

- [ ] **Step 2: Run the template test and verify it fails**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: FAIL because `tasks.md` does not yet express profile-specific task shaping.

- [ ] **Step 3: Update `templates/commands/tasks.md` to compile profile-aware batches**

In `Load design documents`, add:

```markdown
- **Required when present**: `workflow-state.md` (active profile, activated gates, task-shaping rules, required evidence)
```

In the task-generation workflow section, add:

```markdown
- Extract the active profile and its obligations from `workflow-state.md`
- If the active profile is `Reference-Implementation`, add explicit fidelity checkpoints after implementation batches that materially change the reference-preserved surface
- If the implementation may intentionally diverge from the reference contract, add a Deviation Review join point before downstream work continues
- Carry profile-required evidence into task completion criteria instead of relying on generic behavior validation only
```

Keep the first-release scope wording limited to the two supported profiles.

- [ ] **Step 4: Re-run the template test and verify it passes**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: PASS for the new task-shaping assertions.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/tasks.md tests/test_alignment_templates.py
git commit -m "feat: add profile-aware task shaping to sp-tasks"
```

---

### Task 6: Wire `sp-implement` To Enforce Profile-Matched Exit Evidence

**Files:**
- Modify: `templates/commands/implement.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add a failing implement-template assertion**

Extend `tests/test_alignment_templates.py` or add a focused test requiring
`templates/commands/implement.md` to contain:

```python
assert "profile-matched evidence" in content.lower()
assert "required_evidence" in content
assert "active_profile" in content
assert "Reference-Implementation" in content
assert "comparison evidence" in content.lower()
assert "deviation log" in content.lower()
```

- [ ] **Step 2: Run the template test and verify it fails**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: FAIL because `sp-implement` currently validates generic execution state,
not profile-matched exit evidence.

- [ ] **Step 3: Update `templates/commands/implement.md` with profile-evidence discipline**

In the implementation context-loading section, add:

```markdown
- **REQUIRED WHEN PRESENT**: Read `FEATURE_DIR/workflow-state.md` and treat `active_profile` and `required_evidence` as execution constraints
```

In the orchestration or execution outline, add:

```markdown
- Before accepting a batch as complete, verify that the batch handoff includes the evidence type required by the active profile
- For `Standard Delivery`, behavior validation and regression proof remain sufficient unless stronger evidence is explicitly activated
- For `Reference-Implementation`, completion requires profile-matched evidence such as comparison evidence, deviation log, or fidelity audit notes when those were activated upstream
- Do not treat generic "tests passed" output as sufficient when the active profile requires stronger exit evidence
```

This is documentation/contract wiring only; do not add a new runtime subsystem here.

- [ ] **Step 4: Re-run the template test and verify it passes**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: PASS for the implement evidence-discipline assertions.

- [ ] **Step 5: Commit**

```bash
git add templates/commands/implement.md tests/test_alignment_templates.py
git commit -m "feat: require profile-matched exit evidence in sp-implement"
```

---

### Task 7: Add First-Release Artifact Validation For Profile-Required Sections

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Test: `tests/hooks/test_artifact_hooks.py`

- [ ] **Step 1: Write the failing artifact-validation test**

Add a test in `tests/hooks/test_artifact_hooks.py` that creates:

- `spec.md` without `## Fidelity Requirements`
- `workflow-state.md` with `active_profile: reference-implementation`

and runs:

```python
result = run_quality_hook(
    project,
    "workflow.artifacts.validate",
    {"command_name": "specify", "feature_dir": str(feature_dir)},
)
```

Expected assertion:

```python
assert result.status == "blocked"
assert any("Fidelity Requirements" in message for message in result.errors)
```

Add a second test proving success when the section exists.

- [ ] **Step 2: Run the hook test and verify it fails**

Run:

```bash
pytest tests/hooks/test_artifact_hooks.py -q
```

Expected: FAIL because profile-required section checks do not exist yet.

- [ ] **Step 3: Extend artifact validation for first-release profiles**

In `src/specify_cli/hooks/artifact_validation.py`:

1. Reuse `serialize_workflow_state()` to read `active_profile` and `required_sections`
2. For `command_name == "specify"` and `active_profile == "reference-implementation"`,
   validate that `spec.md` contains:

- `## Fidelity Requirements`
- `### Reference Object`
- `### Required Fidelity`

3. Emit clear blocked errors when any required section is missing.

Keep this validation narrow to first-release supported profiles only.

- [ ] **Step 4: Re-run the hook tests and verify they pass**

Run:

```bash
pytest tests/hooks/test_artifact_hooks.py tests/hooks/test_state_hooks.py -q
```

Expected: PASS for the new first-release profile validation.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/hooks/artifact_validation.py tests/hooks/test_artifact_hooks.py tests/hooks/test_state_hooks.py
git commit -m "feat: validate reference-implementation required spec sections"
```

---

### Task 8: Update Repo Workflow/Testing Guidance And Run Final Regression

**Files:**
- Modify: `templates/project-map/root/WORKFLOWS.md`
- Modify: `templates/project-map/root/TESTING.md`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add failing assertions for root workflow/testing docs**

In `tests/test_alignment_templates.py`, add assertions requiring:

For `templates/project-map/root/WORKFLOWS.md`:

```python
assert "scenario profile" in content.lower()
assert "standard delivery" in content.lower()
assert "reference-implementation" in content.lower()
```

For `templates/project-map/root/TESTING.md`:

```python
assert "profile-matched evidence" in content.lower()
assert "reference fidelity" in content.lower()
```

- [ ] **Step 2: Run the template tests and verify they fail**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: FAIL because the atlas templates do not yet describe scenario-profile behavior.

- [ ] **Step 3: Update root workflow and testing atlas templates**

In `templates/project-map/root/WORKFLOWS.md`, document:

- the existence of one active profile per feature lifecycle
- first-release support for `Standard Delivery` and `Reference-Implementation`
- profile routing happening at workflow entry and flowing through
  `sp-specify -> sp-plan -> sp-tasks -> sp-implement`

In `templates/project-map/root/TESTING.md`, document:

- completion evidence varies by scenario
- default verification remains lightweight for `Standard Delivery`
- `Reference-Implementation` requires evidence beyond generic passing tests when
  activated upstream

Keep both docs high-level and atlas-oriented; do not duplicate command-template detail.

- [ ] **Step 4: Run the final focused regression suite**

Run:

```bash
pytest tests/test_alignment_templates.py tests/hooks/test_state_hooks.py tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q
pytest tests/integrations/test_cli.py -q -k "shared_workflow_skills or shared_infra_skips_existing_files"
```

Expected: PASS. If any integration-facing template contract changed more broadly,
expand to the Codex and Claude integration tests before closing.

- [ ] **Step 5: Commit**

```bash
git add templates/project-map/root/WORKFLOWS.md templates/project-map/root/TESTING.md tests/test_alignment_templates.py
git commit -m "docs: add scenario profile guidance to atlas workflow and testing templates"
```

---

## Self-Review Checklist

- [ ] `spec`-level profile routing is defined exactly once at entry and persisted durably
- [ ] Shared templates remain single-family; no separate full template set was introduced
- [ ] First release only supports `Standard Delivery` and `Reference-Implementation`
- [ ] `workflow-state.md` carries the profile contract fields needed downstream
- [ ] `sp-plan`, `sp-tasks`, and `sp-implement` consume the persisted profile instead of reclassifying task type
- [ ] Artifact/state validation stays bounded to first-release profile obligations
- [ ] Default-path weight stays low; high-risk rules only activate when the profile demands them

## Final Verification

Run before declaring the implementation plan executable:

```bash
pytest tests/test_alignment_templates.py tests/hooks/test_state_hooks.py tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q
pytest tests/integrations/test_cli.py -q -k "shared_workflow_skills or shared_infra_skips_existing_files"
```
