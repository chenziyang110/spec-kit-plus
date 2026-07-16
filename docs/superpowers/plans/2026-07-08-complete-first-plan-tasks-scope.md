# Complete-First Plan Tasks Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden `sp-plan` and `sp-tasks` so confirmed scope is planned and tasked complete-first instead of being shrunk into agent-invented versions, priorities, MVPs, or future phases.

**Architecture:** This is a shared-template contract change. Tests in `tests/test_alignment_templates.py` lock the wording and JSON contract fields first, then Markdown command/templates and structured JSON templates are updated to satisfy those tests. Repository docs are updated last so operator guidance matches generated workflow behavior.

**Tech Stack:** Markdown workflow templates, JSON template contracts, pytest template-contract tests.

---

## File Structure

- Modify `F:\github\spec-kit-plus\tests\test_alignment_templates.py`: add regression tests near the existing scope-preservation tests so failures localize to generated workflow contracts.
- Modify `F:\github\spec-kit-plus\templates\commands\plan.md`: add complete-first planning rules and clarify adaptive blocker behavior.
- Modify `F:\github\spec-kit-plus\templates\plan-template.md`: add generated `plan.md` sections for complete-first scope and user-confirmed deferrals.
- Modify `F:\github\spec-kit-plus\templates\plan-contract-template.json`: add machine-readable complete-first and deferral contract fields for downstream task generation.
- Modify `F:\github\spec-kit-plus\templates\commands\tasks.md`: add complete-first task-generation rules, tighten deferral wording, and clarify progressive refinement.
- Modify `F:\github\spec-kit-plus\templates\tasks-template.md`: add generated `tasks.md` sections that distinguish execution phases from delivery deferral.
- Modify `F:\github\spec-kit-plus\templates\task-index-template.json`: carry the complete-first and deferral contract into task indexes.
- Modify `F:\github\spec-kit-plus\templates\task-packet-template.json`: carry the same fields into per-task execution packets.
- Modify `F:\github\spec-kit-plus\templates\implement-execution-state-template.json`: carry confirmed scope and deferrals into implementation execution state.
- Modify `F:\github\spec-kit-plus\templates\passive-skills\spec-kit-workflow-routing\SKILL.md`: update routing guidance so route minimization cannot become delivery minimization.
- Modify `F:\github\spec-kit-plus\PROJECT-HANDBOOK.md`: update repository-level workflow guidance.
- Modify `F:\github\spec-kit-plus\templates\project-handbook-template.md`: keep generated handbook guidance aligned with `PROJECT-HANDBOOK.md`.
- Modify `F:\github\spec-kit-plus\README.md`: update user-facing workflow documentation.
- Do not touch unrelated dirty worktree files unless a test proves they are direct generated-context surfaces for this change.

## Task 1: Add Failing Template-Contract Tests

**Files:**
- Modify: `F:\github\spec-kit-plus\tests\test_alignment_templates.py`
- Test: `F:\github\spec-kit-plus\tests\test_alignment_templates.py`

- [ ] **Step 1: Insert the complete-first regression tests**

Add these test functions after `test_tasks_templates_preserve_user_confirmed_delivery_scope_not_mvp` and before `test_workflow_templates_preserve_create_scaffold_capabilities_when_surface_is_minimized`:

```python
def test_plan_tasks_templates_enforce_complete_first_scope_preservation() -> None:
    plan = _read("templates/commands/plan.md")
    plan_template = _read("templates/plan-template.md")
    tasks = _read("templates/commands/tasks.md")
    tasks_template = _read("templates/tasks-template.md")
    routing = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")

    combined = "\n".join([plan, plan_template, tasks, tasks_template, routing])
    lowered = combined.lower()

    assert "complete-first scope preservation" in lowered
    assert "complete user-confirmed scope" in lowered
    assert "complexity alone is not a valid reason" in lowered
    assert "do not shrink scope" in lowered
    assert "execution phases are ordering, not delivery deferral" in lowered
    assert "runtime capability limits are blockers only under the adaptive execution policy" in lowered
    assert "heavy, safety-critical, or unpacketizable" in lowered
    assert "user story priorities such as `p1`, `p2`, and `p3` remain ordering labels" in lowered
    assert "agent-invented `v1/v2`" in lowered
    assert "agent-invented `p0/p1`" in lowered
    assert "future-work delivery slice" in lowered


def test_complete_first_deferrals_require_full_contract_fields() -> None:
    checked_templates = [
        _read("templates/commands/plan.md"),
        _read("templates/plan-template.md"),
        _read("templates/commands/tasks.md"),
        _read("templates/tasks-template.md"),
    ]
    combined = "\n".join(checked_templates).lower()

    for phrase in (
        "confirmation source",
        "exact excluded behavior",
        "residual risk",
        "reopen or stop condition",
        "downstream artifact",
    ):
        assert phrase in combined

    assert "if the user did not confirm the deferral" in combined
    assert "task the behavior" in combined
    assert "create a refinement or validation checkpoint" in combined


def test_structured_templates_carry_complete_first_scope_contract() -> None:
    plan_contract = json.loads(_read("templates/plan-contract-template.json"))
    task_index = json.loads(_read("templates/task-index-template.json"))
    task_packet = json.loads(_read("templates/task-packet-template.json"))
    implement_state = json.loads(_read("templates/implement-execution-state-template.json"))

    for payload in (plan_contract, task_index, task_packet, implement_state):
        assert "confirmed_delivery_scope" in payload
        assert "complete_first_scope_preservation" in payload
        assert "user_confirmed_deferrals" in payload
        assert "deferral_contract_required_fields" in payload
        assert payload["deferral_contract_required_fields"] == [
            "confirmation_source",
            "exact_excluded_behavior",
            "residual_risk",
            "reopen_or_stop_condition",
            "downstream_artifact",
        ]

    assert plan_contract["complete_first_scope_preservation"]["default"] == "plan_and_task_complete_confirmed_scope"
    assert task_index["complete_first_scope_preservation"]["phase_policy"] == "execution_order_not_delivery_deferral"
    assert task_packet["complete_first_scope_preservation"]["scope_reduction_allowed"] is False
    assert implement_state["complete_first_scope_preservation"]["scope_reduction_allowed"] is False
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py -k "complete_first or preserve_user_confirmed_delivery_scope" -q
```

Expected: FAIL. The new tests should report missing `complete-first scope preservation` wording and missing JSON keys before template changes are made.

- [ ] **Step 3: Commit the failing tests**

Run:

```powershell
git add tests/test_alignment_templates.py
git commit -m "test: cover complete-first scope preservation"
```

Expected: commit succeeds and only `tests/test_alignment_templates.py` is staged.

## Task 2: Update Plan Workflow Templates

**Files:**
- Modify: `F:\github\spec-kit-plus\templates\commands\plan.md`
- Modify: `F:\github\spec-kit-plus\templates\plan-template.md`
- Modify: `F:\github\spec-kit-plus\templates\plan-contract-template.json`
- Test: `F:\github\spec-kit-plus\tests\test_alignment_templates.py`

- [ ] **Step 1: Add complete-first planning guidance to `templates/commands/plan.md`**

Insert this section after `## Scenario Profile Inputs` and before `## Operational Consequence Design`:

```markdown
## Complete-First Scope Preservation

The active feature scope is the complete user-confirmed scope from `spec.md`,
`alignment.md`, `context.md`, `plan-contract.json`, and approved discussion or
brainstorming handoffs. `sp-plan` may choose architecture, sequencing, dependency
order, dispatch shape, and validation strategy, but it must not shrink scope.

- Complexity alone is not a valid reason to split, defer, block, or return upstream.
- Handle complex but clear work through dependency ordering, implementation
  guardrails, design artifacts, validation paths, and refinement checkpoints.
- Do not convert confirmed scope into an MVP, pilot, prototype, first release,
  future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1`.
- User story priorities such as `P1`, `P2`, and `P3` remain ordering labels from
  `spec.md`; they are not delivery-scope buckets.
- If a deferral is valid, it must be user-confirmed and record confirmation source,
  exact excluded behavior, residual risk, reopen or stop condition, and downstream
  artifact.
- If the user did not confirm the deferral, plan the behavior, create a refinement
  or validation checkpoint that keeps it inside the current feature, or identify a
  valid hard blocker.
- Runtime capability limits are blockers only under the adaptive execution policy
  for heavy, safety-critical, or unpacketizable work. They are not permission to
  shrink scope or relabel confirmed behavior as a later version.
```

- [ ] **Step 2: Clarify adaptive blocker wording in `templates/commands/plan.md`**

After the existing adaptive decision bullet that starts `If the workload is heavy or safety-critical`, add:

```markdown
     - This adaptive blocker preserves scope. It may stop synthesis when execution
       cannot proceed safely, but it must not convert confirmed behavior into a
       smaller MVP, future phase, or agent-invented release slice.
```

- [ ] **Step 3: Add complete-first generated plan sections to `templates/plan-template.md`**

Insert this section after `## Locked Planning Decisions` and before `## Must-Preserve Carry-Forward`:

```markdown
## Complete-First Delivery Scope

<!--
  Restate the complete user-confirmed scope that this plan must preserve.
  Execution order, dependency order, and validation order may vary, but planning
  must not reduce delivery scope unless a user-confirmed deferral is recorded in
  the deferral contract below.
-->

- **Scope source files**: `spec.md`, `alignment.md`, `context.md`, `plan-contract.json`, and approved handoff files
- **Delivery rule**: Plan and task the complete confirmed scope; do not shrink scope because the work is complex
- **Forbidden reductions**: MVP by default, pilot by default, prototype by default, first-release slice, agent-invented `v1/v2`, agent-invented `P0/P1`, or future-work delivery slice
- **Priority labels**: User story priorities such as `P1`, `P2`, and `P3` are ordering labels, not delivery-scope buckets
- **Adaptive blocker carve-out**: Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and do not reduce scope

## User-Confirmed Deferral Contract

| Confirmation Source | Exact Excluded Behavior | Residual Risk | Reopen Or Stop Condition | Downstream Artifact |
| --- | --- | --- | --- | --- |
| None | None | None | None | None |

- If the user did not confirm a deferral, keep the behavior in scope through design,
  a refinement checkpoint, or a named valid blocker.
```

- [ ] **Step 4: Add structured fields to `templates/plan-contract-template.json`**

Add these keys immediately after `"allowed_optimization_scope": [],`:

```json
  "confirmed_delivery_scope": [],
  "complete_first_scope_preservation": {
    "default": "plan_and_task_complete_confirmed_scope",
    "scope_reduction_allowed": false,
    "complexity_response": "decompose_order_validate_refine_without_shrinking",
    "phase_policy": "execution_order_not_delivery_deferral",
    "adaptive_blocker_carve_out": "Runtime capability limits block only under adaptive execution for heavy, safety-critical, or unpacketizable work; they do not reduce scope.",
    "priority_label_policy": "User story P1/P2/P3 labels are ordering labels, not delivery-scope buckets.",
    "forbidden_reduction_patterns": [
      "mvp_by_default",
      "pilot_by_default",
      "prototype_by_default",
      "first_release_slice",
      "agent_invented_v1_v2",
      "agent_invented_p0_p1",
      "future_work_delivery_slice"
    ]
  },
  "user_confirmed_deferrals": [],
  "deferral_contract_required_fields": [
    "confirmation_source",
    "exact_excluded_behavior",
    "residual_risk",
    "reopen_or_stop_condition",
    "downstream_artifact"
  ],
```

Use a JSON parser or `python -m json.tool templates/plan-contract-template.json` after editing to confirm commas are valid.

- [ ] **Step 5: Run the focused tests and verify partial progress**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py -k "complete_first or preserve_user_confirmed_delivery_scope" -q
```

Expected: Some assertions still fail for task templates and other JSON templates, but plan-specific assertions should pass.

- [ ] **Step 6: Commit plan template changes**

Run:

```powershell
python -m json.tool templates/plan-contract-template.json > $null
git add templates/commands/plan.md templates/plan-template.md templates/plan-contract-template.json
git commit -m "docs: add complete-first planning contract"
```

Expected: commit succeeds with only the three plan files staged.

## Task 3: Update Tasks Workflow and Structured Execution Templates

**Files:**
- Modify: `F:\github\spec-kit-plus\templates\commands\tasks.md`
- Modify: `F:\github\spec-kit-plus\templates\tasks-template.md`
- Modify: `F:\github\spec-kit-plus\templates\task-index-template.json`
- Modify: `F:\github\spec-kit-plus\templates\task-packet-template.json`
- Modify: `F:\github\spec-kit-plus\templates\implement-execution-state-template.json`
- Test: `F:\github\spec-kit-plus\tests\test_alignment_templates.py`

- [ ] **Step 1: Add complete-first task generation guidance to `templates/commands/tasks.md`**

Insert this section after `## User-Observable Path Coverage` and before `4. **Execute task generation workflow**`:

```markdown
## Complete-First Task Generation

Task generation must cover the complete user-confirmed scope from `spec.md`,
`alignment.md`, `context.md`, `plan.md`, `plan-contract.json`, and approved handoff
files. `sp-tasks` may choose execution phases, dependency order, parallel batches,
join points, and refinement checkpoints, but it must not shrink scope.

- Complexity alone is not a valid reason to split, defer, block, or route upstream.
- Handle complex but clear work through dependency ordering, isolated write sets,
  parallel-safe batches, join-point validation, refinement tasks, and verification
  tasks.
- Execution phases are ordering, not delivery deferral.
- Do not move confirmed behavior to an MVP, pilot, prototype, first release,
  future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1`.
- User story priorities such as `P1`, `P2`, and `P3` remain ordering labels from
  `spec.md`; they are not delivery-scope buckets.
- Runtime capability limits are blockers only under the adaptive execution policy
  for heavy, safety-critical, or unpacketizable work. They are not permission to
  shrink scope.
- Every valid deferral must be user-confirmed and record confirmation source, exact
  excluded behavior, residual risk, reopen or stop condition, and downstream
  artifact.
- If the user did not confirm the deferral, task the behavior, create a refinement
  or validation checkpoint that keeps it inside the current feature, or identify a
  valid hard blocker.
```

- [ ] **Step 2: Tighten progressive refinement wording in `templates/commands/tasks.md`**

Replace the current line:

```markdown
    - Stop decomposition once the current executable window is atomic. Leave later phases at the coarser story or phase level when their exact shape depends on earlier join-point evidence
```

with:

```markdown
    - Stop decomposition once the current executable window is atomic. Leave later execution phases at the coarser story or phase level only when their exact task shape depends on earlier join-point evidence; this is refinement inside the current confirmed delivery, not delivery deferral or future work.
```

- [ ] **Step 3: Tighten task self-audit deferral checks in `templates/commands/tasks.md`**

Replace:

```markdown
    - Confirm every buildable `FR-*` and buildable success criterion has at least one task, checkpoint, or explicit deferred note.
```

with:

```markdown
    - Confirm every buildable `FR-*` and buildable success criterion has at least one task, checkpoint, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
```

Replace:

```markdown
    - Confirm every UI/TUI/CLI/API/runtime-visible path has User-Observable Path Coverage with a real-entrypoint validation task or user-confirmed deferral.
```

with:

```markdown
    - Confirm every UI/TUI/CLI/API/runtime-visible path has User-Observable Path Coverage with a real-entrypoint validation task or a user-confirmed deferral carrying the full five-field deferral contract.
```

- [ ] **Step 4: Add generated task sections to `templates/tasks-template.md`**

Insert this section after `## Planning Inputs` and before `## Task Guardrail Index`:

```markdown
## Complete-First Delivery Scope

- **Delivery rule**: Task the complete user-confirmed scope from `spec.md`, `alignment.md`, `context.md`, `plan.md`, `plan-contract.json`, and approved handoff files.
- **Complexity response**: Use ordering, dependencies, isolated write sets, parallel batches, join points, refinement tasks, and validation; do not shrink scope because the work is complex.
- **Execution phase policy**: Execution phases are ordering, not delivery deferral.
- **Forbidden reductions**: Do not create an MVP, pilot, prototype, first-release slice, agent-invented `v1/v2`, agent-invented `P0/P1`, or future-work delivery slice unless the user explicitly confirmed that delivery boundary.
- **Priority labels**: User story priorities such as `P1`, `P2`, and `P3` remain ordering labels, not delivery-scope buckets.
- **Adaptive blocker carve-out**: Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and do not reduce scope.

## User-Confirmed Deferral Contract

| Confirmation Source | Exact Excluded Behavior | Residual Risk | Reopen Or Stop Condition | Downstream Artifact |
| --- | --- | --- | --- | --- |
| None | None | None | None | None |

- If the user did not confirm a deferral, task the behavior, create a refinement or
  validation checkpoint, or record a valid hard blocker.
```

- [ ] **Step 5: Tighten generated task shaping wording in `templates/tasks-template.md`**

Replace:

```markdown
- Leave later phases at the coarser story or phase level when their exact shape depends on earlier join points, then refine them after the checkpoint instead of guessing too early.
```

with:

```markdown
- Leave later execution phases at the coarser story or phase level only when their exact task shape depends on earlier join points, then refine them after the checkpoint inside the current confirmed delivery instead of guessing too early.
```

Replace:

```markdown
4. Preserve user-confirmed deferrals and non-goals explicitly; do not infer a smaller release from User Story 1
```

with:

```markdown
4. Preserve user-confirmed deferrals and non-goals explicitly with confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact; do not infer a smaller release from User Story 1 or any execution phase
```

- [ ] **Step 6: Add structured fields to `templates/task-index-template.json`**

Add these keys immediately after `"status": "pending",`:

```json
  "confirmed_delivery_scope": [],
  "complete_first_scope_preservation": {
    "default": "plan_and_task_complete_confirmed_scope",
    "scope_reduction_allowed": false,
    "complexity_response": "decompose_order_validate_refine_without_shrinking",
    "phase_policy": "execution_order_not_delivery_deferral",
    "adaptive_blocker_carve_out": "Runtime capability limits block only under adaptive execution for heavy, safety-critical, or unpacketizable work; they do not reduce scope.",
    "priority_label_policy": "User story P1/P2/P3 labels are ordering labels, not delivery-scope buckets.",
    "forbidden_reduction_patterns": [
      "mvp_by_default",
      "pilot_by_default",
      "prototype_by_default",
      "first_release_slice",
      "agent_invented_v1_v2",
      "agent_invented_p0_p1",
      "future_work_delivery_slice"
    ]
  },
  "user_confirmed_deferrals": [],
  "deferral_contract_required_fields": [
    "confirmation_source",
    "exact_excluded_behavior",
    "residual_risk",
    "reopen_or_stop_condition",
    "downstream_artifact"
  ],
```

- [ ] **Step 7: Add structured fields to `templates/task-packet-template.json`**

Add these keys immediately after `"complexity_level": null,`:

```json
  "confirmed_delivery_scope": [],
  "complete_first_scope_preservation": {
    "default": "execute_task_without_reducing_confirmed_scope",
    "scope_reduction_allowed": false,
    "complexity_response": "complete_assigned_scope_or_return_valid_blocker",
    "phase_policy": "task_phase_is_ordering_not_delivery_deferral",
    "adaptive_blocker_carve_out": "Runtime capability limits block only under adaptive execution for heavy, safety-critical, or unpacketizable work; they do not reduce scope.",
    "priority_label_policy": "User story P1/P2/P3 labels are ordering labels, not delivery-scope buckets.",
    "forbidden_reduction_patterns": [
      "mvp_by_default",
      "pilot_by_default",
      "prototype_by_default",
      "first_release_slice",
      "agent_invented_v1_v2",
      "agent_invented_p0_p1",
      "future_work_delivery_slice"
    ]
  },
  "user_confirmed_deferrals": [],
  "deferral_contract_required_fields": [
    "confirmation_source",
    "exact_excluded_behavior",
    "residual_risk",
    "reopen_or_stop_condition",
    "downstream_artifact"
  ],
```

- [ ] **Step 8: Add structured fields to `templates/implement-execution-state-template.json`**

Add these keys immediately after `"complexity_level": null,`:

```json
  "confirmed_delivery_scope": [],
  "complete_first_scope_preservation": {
    "default": "execute_current_task_graph_without_reducing_confirmed_scope",
    "scope_reduction_allowed": false,
    "complexity_response": "repair_tasks_or_return_valid_blocker_without_shrinking_scope",
    "phase_policy": "execution_phase_is_ordering_not_delivery_deferral",
    "adaptive_blocker_carve_out": "Runtime capability limits block only under adaptive execution for heavy, safety-critical, or unpacketizable work; they do not reduce scope.",
    "priority_label_policy": "User story P1/P2/P3 labels are ordering labels, not delivery-scope buckets.",
    "forbidden_reduction_patterns": [
      "mvp_by_default",
      "pilot_by_default",
      "prototype_by_default",
      "first_release_slice",
      "agent_invented_v1_v2",
      "agent_invented_p0_p1",
      "future_work_delivery_slice"
    ]
  },
  "user_confirmed_deferrals": [],
  "deferral_contract_required_fields": [
    "confirmation_source",
    "exact_excluded_behavior",
    "residual_risk",
    "reopen_or_stop_condition",
    "downstream_artifact"
  ],
```

- [ ] **Step 9: Run JSON validation and focused tests**

Run:

```powershell
python -m json.tool templates/task-index-template.json > $null
python -m json.tool templates/task-packet-template.json > $null
python -m json.tool templates/implement-execution-state-template.json > $null
python -m pytest tests/test_alignment_templates.py -k "complete_first or preserve_user_confirmed_delivery_scope" -q
```

Expected: JSON validation passes. Focused pytest should pass or fail only on docs/routing surfaces not yet updated.

- [ ] **Step 10: Commit task template changes**

Run:

```powershell
git add templates/commands/tasks.md templates/tasks-template.md templates/task-index-template.json templates/task-packet-template.json templates/implement-execution-state-template.json
git commit -m "docs: add complete-first task contract"
```

Expected: commit succeeds with only task workflow and structured execution template files staged.

## Task 4: Update Shared Routing and Documentation

**Files:**
- Modify: `F:\github\spec-kit-plus\templates\passive-skills\spec-kit-workflow-routing\SKILL.md`
- Modify: `F:\github\spec-kit-plus\PROJECT-HANDBOOK.md`
- Modify: `F:\github\spec-kit-plus\templates\project-handbook-template.md`
- Modify: `F:\github\spec-kit-plus\README.md`
- Test: `F:\github\spec-kit-plus\tests\test_alignment_templates.py`
- Test: `F:\github\spec-kit-plus\tests\test_project_handbook_templates.py`

- [ ] **Step 1: Update passive workflow routing guidance**

Replace the existing workflow-route minimization bullet in `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`:

```markdown
- Workflow-route minimization is only about choosing the command surface. Preserve the user's confirmed product scope; do not steer the product toward a smaller MVP, pilot, prototype, or first-story release unless the user asked for that shape or confirmed it after a named constraint/trade-off.
```

with:

```markdown
- Workflow-route minimization is only about choosing the command surface. Preserve the user's complete user-confirmed scope; do not shrink scope toward a smaller MVP, pilot, prototype, first-story release, future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1` unless the user asked for that shape or confirmed it after a named constraint/trade-off. Complexity alone is not a valid reason to defer or block ordinary work; use sequencing, dependencies, batches, join points, refinement checkpoints, and validation paths. Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and they do not reduce scope.
```

- [ ] **Step 2: Update `PROJECT-HANDBOOK.md`**

Replace the `User-confirmed product scope` bullet with:

```markdown
- **User-confirmed product scope**: Generated workflows preserve the user's complete user-confirmed scope. Workflow routing may choose the lightest safe command surface, but `sp-plan` and `sp-tasks` must not convert the user's product intent into a smaller MVP, pilot, prototype, first-story release, future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1`. Scope reduction requires user confirmation, including when a named constraint forces a scope decision. Complexity alone is not a valid reason to shrink scope, defer ordinary work, or block; use sequencing, dependencies, batches, join points, refinement checkpoints, and validation paths. Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and they do not reduce scope.
```

- [ ] **Step 3: Update `templates/project-handbook-template.md`**

Replace the generated handbook `User-confirmed product scope` bullet with the same text from Step 2, preserving the existing bullet location under `High-Value Capabilities`.

- [ ] **Step 4: Update `README.md`**

Replace the paragraph beginning `Generated workflows preserve the user's confirmed product scope.` with:

```markdown
Generated workflows preserve the user's complete user-confirmed scope. Scope reduction requires user confirmation: agents should not steer a requirement toward an MVP, pilot, prototype, first-story release, future-work delivery slice, agent-invented `v1/v2`, agent-invented `P0/P1`, or smaller validation build unless the user asked for that shape, the request already defines that boundary, or a named constraint makes reduced scope a decision the user confirms. Complexity alone is not a valid reason to shrink, defer, or block ordinary work; `sp-plan` and `sp-tasks` should use sequencing, dependencies, batches, join points, refinement checkpoints, and validation paths. Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and they do not reduce scope.
```

- [ ] **Step 5: Run documentation-focused tests**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py -k "complete_first or product_minimization or preserve_user_confirmed_delivery_scope" -q
python -m pytest tests/test_project_handbook_templates.py -q
```

Expected: both commands pass, or failures point to exact additional handbook/README drift to update.

- [ ] **Step 6: Commit routing and docs**

Run:

```powershell
git add templates/passive-skills/spec-kit-workflow-routing/SKILL.md PROJECT-HANDBOOK.md templates/project-handbook-template.md README.md
git commit -m "docs: document complete-first workflow scope"
```

Expected: commit succeeds with only routing/docs files staged.

## Task 5: Final Verification and Cleanup

**Files:**
- Inspect: `F:\github\spec-kit-plus\tests\test_alignment_templates.py`
- Inspect: `F:\github\spec-kit-plus\templates\commands\plan.md`
- Inspect: `F:\github\spec-kit-plus\templates\commands\tasks.md`
- Inspect: `F:\github\spec-kit-plus\templates\plan-contract-template.json`
- Inspect: `F:\github\spec-kit-plus\templates\task-index-template.json`
- Inspect: `F:\github\spec-kit-plus\templates\task-packet-template.json`
- Inspect: `F:\github\spec-kit-plus\templates\implement-execution-state-template.json`

- [ ] **Step 1: Validate all touched JSON templates**

Run:

```powershell
python -m json.tool templates/plan-contract-template.json > $null
python -m json.tool templates/task-index-template.json > $null
python -m json.tool templates/task-packet-template.json > $null
python -m json.tool templates/implement-execution-state-template.json > $null
```

Expected: all four commands exit with code 0.

- [ ] **Step 2: Run the full alignment template test module**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py -q
```

Expected: all tests in `tests/test_alignment_templates.py` pass.

- [ ] **Step 3: Run nearby documentation/template tests**

Run:

```powershell
python -m pytest tests/test_project_handbook_templates.py tests/test_agents_guidance.py tests/test_agent_context_managed_block.py -q
```

Expected: all selected tests pass. If `test_agent_context_managed_block.py` fails because generated AGENTS managed-block guidance must include complete-first scope text, update `scripts/bash/update-agent-context.sh` and `scripts/powershell/update-agent-context.ps1` together, then rerun this command.

- [ ] **Step 4: Inspect changed files only**

Run:

```powershell
git diff --stat HEAD
git diff -- tests/test_alignment_templates.py templates/commands/plan.md templates/plan-template.md templates/plan-contract-template.json templates/commands/tasks.md templates/tasks-template.md templates/task-index-template.json templates/task-packet-template.json templates/implement-execution-state-template.json templates/passive-skills/spec-kit-workflow-routing/SKILL.md PROJECT-HANDBOOK.md templates/project-handbook-template.md README.md
```

Expected: diffs contain only complete-first scope preservation, deferral contract, adaptive blocker carve-out, structured JSON fields, and aligned docs. No unrelated dirty worktree files should appear in the scoped diff.

- [ ] **Step 5: Final commit if verification required fixups**

If Step 2 or Step 3 required fixups after Task 4, run:

```powershell
git add tests/test_alignment_templates.py templates/commands/plan.md templates/plan-template.md templates/plan-contract-template.json templates/commands/tasks.md templates/tasks-template.md templates/task-index-template.json templates/task-packet-template.json templates/implement-execution-state-template.json templates/passive-skills/spec-kit-workflow-routing/SKILL.md PROJECT-HANDBOOK.md templates/project-handbook-template.md README.md scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 tests/test_agent_context_managed_block.py tests/test_agents_guidance.py
git commit -m "test: align complete-first workflow surfaces"
```

Expected: commit succeeds only if there were verification-driven fixups. If no fixups were needed, skip this commit.

## Self-Review

- Spec coverage: The plan covers complete-first scope preservation, complexity handling, narrow blockers with adaptive carve-out, five-field deferral contract, progressive refinement without scope loss, Markdown templates, JSON templates, routing docs, README, handbook surfaces, and tests.
- Placeholder scan: The plan uses concrete file paths, exact snippets, exact commands, and expected outcomes. Template snippets intentionally include generated-template labels such as `P1`, `P2`, and `P3` because those are part of the product surface being implemented.
- Type consistency: JSON keys are consistent across tests and templates: `confirmed_delivery_scope`, `complete_first_scope_preservation`, `user_confirmed_deferrals`, and `deferral_contract_required_fields`.
