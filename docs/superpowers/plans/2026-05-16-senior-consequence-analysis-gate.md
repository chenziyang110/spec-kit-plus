# Senior Consequence Analysis Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared senior consequence analysis gate so generated `sp-*` workflows identify affected objects, lifecycle states, dependency impact, recovery behavior, and validation obligations before handoff or execution.

**Architecture:** Implement this as a cross-workflow contract with one shared command partial, workflow-specific prompt sections, artifact template fields, and structured validators for JSON and worker packet surfaces that already exist. Project cognition remains the evidence source; the new gate turns its facts and coverage gaps into concrete product and implementation obligations without changing the cognition database schema in this increment.

**Tech Stack:** Python 3.11+, pytest, Markdown command templates, JSON artifact templates, dataclass packet/result schemas, hook validators.

---

## Source Spec

- Design: `docs/superpowers/specs/2026-05-16-senior-consequence-analysis-gate-design.md`
- Related existing plans:
  - `docs/superpowers/plans/2026-05-16-discussion-split-handoff.md`
  - `docs/superpowers/plans/2026-05-15-discussion-to-specify-fidelity-implementation.md`

## Scope Check

This is one product behavior change across multiple generated workflow surfaces. Do not split it into separate plans because the acceptance condition is propagation: `discussion -> specify -> plan -> tasks -> analyze -> implement`, plus direct-work routing in `fast`, `quick`, and `debug`.

Keep the first increment bounded:

- Add prompt-contract coverage for Markdown-only workflow outputs.
- Add structured validation where JSON or durable machine-readable state already exists.
- Do not redesign `.specify/project-cognition/project-cognition.db`.
- Do not add a new public workflow command.
- Do not require legacy projects to materialize optional JSON artifacts that are not currently required.

## File Structure

Create:

- `templates/command-partials/common/senior-consequence-analysis-gate.md`: shared generated workflow language for triggers, required outputs, project cognition relationship, and stand-down behavior.

Modify workflow templates:

- `templates/commands/discussion.md`: add Senior Maintainer Review and Markdown/JSON/candidate handoff obligations.
- `templates/commands/specify.md`: add Consequence Completeness Gate before planning readiness.
- `templates/commands/plan.md`: add Operational Consequence Design before `sp-tasks`.
- `templates/commands/tasks.md`: add Consequence Obligation Mapping before task package completion.
- `templates/commands/fast.md`: treat gate triggers as upgrade triggers unless stand-down is recorded.
- `templates/commands/quick.md`: add bounded consequence fields to `STATUS.md` and escalation rules.
- `templates/commands/debug.md`: add dependency-loop consequence investigation rules.
- `templates/commands/clarify.md`: preserve and resolve unresolved consequence gaps.
- `templates/commands/deep-research.md`: preserve consequence-sensitive feasibility tracks into Planning Handoff.
- `templates/commands/analyze.md`: verify tasks and packets did not drop consequence obligations.
- `templates/commands/implement.md`: consume packet consequence obligations and stop when they prove wrong or impossible.

Modify command partials:

- `templates/command-partials/discussion/shell.md`
- `templates/command-partials/specify/shell.md`
- `templates/command-partials/plan/shell.md`
- `templates/command-partials/tasks/shell.md`
- `templates/command-partials/fast/shell.md`
- `templates/command-partials/quick/shell.md`
- `templates/command-partials/debug/shell.md`
- `templates/command-partials/implement/shell.md`

Modify artifact templates:

- `templates/discussion-state-template.md`
- `templates/spec-template.md`
- `templates/alignment-template.md`
- `templates/context-template.md`
- `templates/references-template.md`
- `templates/plan-template.md`
- `templates/tasks-template.md`
- `templates/brainstorming-handoff-specify-template.json`
- `templates/plan-contract-template.json`
- `templates/task-index-template.json`
- `templates/task-packet-template.json`
- `templates/implement-execution-state-template.json`
- `templates/debug.md`

Modify runtime validation:

- `src/specify_cli/hooks/artifact_validation.py`: validate consequence JSON fields when present and block ready states with missing consequence sections.
- `src/specify_cli/execution/packet_schema.py`: add `ConsequenceObligation` and optional packet field.
- `src/specify_cli/execution/packet_compiler.py`: compile task-level `CA-###` obligation lines into packets when tasks name them.
- `src/specify_cli/execution/packet_validator.py`: validate obligation shape when packet obligations are present.
- `src/specify_cli/execution/result_schema.py`: add consequence evidence.
- `src/specify_cli/execution/result_validator.py`: require evidence when packet consequence obligations are present and the result succeeds.

Modify docs and passive skill guidance:

- `README.md`
- `docs/quickstart.md`
- `PROJECT-HANDBOOK.md`
- `templates/project-handbook-template.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`

Modify tests:

- `tests/test_alignment_templates.py`
- `tests/test_fast_template_guidance.py`
- `tests/test_quick_template_guidance.py`
- `tests/test_debug_template_guidance.py`
- `tests/test_runtime_handbook_contract.py`
- `tests/test_specify_guidance_docs.py`
- `tests/hooks/test_artifact_hooks.py`
- `tests/execution/test_packet_schema.py`
- `tests/execution/test_packet_validator.py`
- `tests/execution/test_packet_compiler.py`
- `tests/execution/test_result_validator.py`
- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_toml.py`
- `tests/integrations/test_integration_base_skills.py`

## Implementation Notes

- Use `CA-###` as the stable ID prefix for consequence obligations.
- Do not stage unrelated dirty work. Before each commit, run the exact `git diff -- ...` command for the files named in that task and stage only those files.
- Keep validator behavior backward compatible: optional consequence JSON files are validated when present, and existing legacy artifacts without a triggered consequence gate still pass.
- In generated workflow text, use "must not mark ready" or "must block readiness" only where a prompt contract or structured validator backs the statement.

---

### Task 1: Add Failing Template Contract Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_debug_template_guidance.py`

- [ ] **Step 1: Add shared helper assertions**

In `tests/test_alignment_templates.py`, add this helper near the existing helper assertions:

```python
def _assert_senior_consequence_gate_contract(content: str) -> None:
    lowered = content.lower()
    assert "senior consequence analysis gate" in lowered
    assert "project cognition first" in lowered
    assert "senior consequence analysis second" in lowered
    assert "affected object map" in lowered
    assert "state-behavior matrix" in lowered
    assert "dependency impact table" in lowered
    assert "recovery and validation contract" in lowered
    assert "coverage gaps" in lowered
    assert "lifecycle operations" in lowered
    assert "running" in lowered
    assert "destructive" in lowered
    assert "shared state" in lowered
    assert "downstream consumers" in lowered
    assert "stand-down reason" in lowered
```

Add this helper after it:

```python
def _assert_consequence_json_contract(content: str) -> None:
    assert '"consequence_gate"' in content
    assert '"consequence_analysis"' in content
    assert '"consequence_obligations"' in content
    assert '"affected_object_map"' in content
    assert '"state_behavior_matrix"' in content
    assert '"dependency_impact"' in content
    assert '"recovery_and_validation"' in content
    assert '"coverage_gaps"' in content
    assert '"stop_and_reopen_conditions"' in content
```

- [ ] **Step 2: Add primary workflow tests**

Append these tests near the existing workflow template contract tests in `tests/test_alignment_templates.py`:

```python
def test_primary_workflows_include_senior_consequence_analysis_gate() -> None:
    for rel_path in (
        "templates/commands/discussion.md",
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/commands/fast.md",
        "templates/commands/quick.md",
        "templates/commands/debug.md",
    ):
        _assert_senior_consequence_gate_contract(_read(rel_path))


def test_adjacent_workflows_preserve_consequence_obligations() -> None:
    for rel_path in (
        "templates/commands/clarify.md",
        "templates/commands/deep-research.md",
        "templates/commands/analyze.md",
        "templates/commands/implement.md",
    ):
        content = _read(rel_path)
        lowered = content.lower()
        assert "consequence obligation" in lowered
        assert "ca-###" in lowered or "ca-*" in lowered
        assert "stop-and-reopen" in lowered
        assert "must not drop" in lowered or "cannot drop" in lowered
```

- [ ] **Step 3: Add discussion handoff coverage tests**

Append this test near the discussion command tests:

```python
def test_discussion_consequence_gate_covers_json_and_candidate_handoffs() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "Senior Maintainer Review" in content
    assert "handoff-to-specify.md" in content
    assert "handoff-to-specify.json" in content
    assert "CAND-001-handoff-to-specify.md" in content
    assert "CAND-001-handoff-to-specify.json" in content
    assert "markdown and json handoffs must agree" in lowered
    assert "consequence obligation ids" in lowered
    assert "must not mark the discussion `handoff-ready`" in content
    assert "selected candidate handoff" in lowered
```

- [ ] **Step 4: Add specify, plan, tasks artifact tests**

Append:

```python
def test_specify_plan_tasks_artifact_templates_preserve_consequence_analysis() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    references = _read("templates/references-template.md")
    plan = _read("templates/plan-template.md")
    tasks = _read("templates/tasks-template.md")

    for content in (spec, alignment, context, references, plan, tasks):
        lowered = content.lower()
        assert "consequence" in lowered
        assert "ca-###" in lowered or "ca-*" in lowered

    assert "Lifecycle And State Behavior" in spec
    assert "Consequence Completeness" in alignment
    assert "Affected Object Map" in context
    assert "Consequence Evidence" in references
    assert "Operational Consequence Design" in plan
    assert "Consequence Obligation Mapping" in tasks


def test_structured_consequence_json_templates_exist() -> None:
    for rel_path in (
        "templates/brainstorming-handoff-specify-template.json",
        "templates/plan-contract-template.json",
        "templates/task-index-template.json",
        "templates/task-packet-template.json",
        "templates/implement-execution-state-template.json",
    ):
        _assert_consequence_json_contract(_read(rel_path))
```

- [ ] **Step 5: Add fast upgrade trigger test**

In `tests/test_fast_template_guidance.py`, append:

```python
def test_fast_template_routes_consequence_triggers_out_of_fast_path() -> None:
    content = read_template("templates/commands/fast.md").lower()

    assert "senior consequence analysis gate" in content
    assert "upgrade to `/sp-quick` immediately if the gate triggers" in content
    assert "upgrade to `/sp-specify` immediately if" in content
    assert "lifecycle" in content
    assert "running-state" in content
    assert "shared-state" in content
    assert "destructive-operation" in content
    assert "consumer impact" in content
    assert "stand-down reason" in content
    assert "do not add planning artifacts to satisfy this gate on the fast path" in content
```

- [ ] **Step 6: Add quick durable state test**

In `tests/test_quick_template_guidance.py`, extend `test_quick_template_includes_concrete_status_template` with:

```python
    assert "## senior consequence analysis" in content
    assert "affected_objects:" in content
    assert "state_behavior_matrix:" in content
    assert "dependency_impact:" in content
    assert "recovery_and_validation:" in content
    assert "project_cognition_evidence:" in content
    assert "coverage_gaps:" in content
    assert "escalation_decision:" in content
```

Append:

```python
def test_quick_template_escalates_when_consequence_model_is_not_bounded() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "senior consequence analysis gate" in content
    assert "continue in quick only when the consequence model is bounded" in content
    assert "upgrade to `{{invoke:specify}}` immediately if" in content or "upgrade to `/sp-specify` immediately if" in content
    assert "user-level lifecycle decisions" in content
    assert "broad compatibility handling" in content
    assert "multi-capability scope" in content
```

- [ ] **Step 7: Add debug dependency-loop tests**

In `tests/test_debug_template_guidance.py`, extend `test_debug_template_documents_single_path_intake_contract` with:

```python
    assert "senior consequence analysis gate" in content
    assert "dependency loop" in content
    assert "affected objects" in content
    assert "adjacent risk targets" in content
    assert "reject surface-only fixes" in content
```

Extend `test_debug_session_template_uses_canonical_intake_fields` with:

```python
    assert "## Senior Consequence Analysis" in content
    assert "affected_objects:" in content
    assert "dependency_loop:" in content
    assert "control_state:" in content
    assert "observation_state:" in content
    assert "adjacent_risk_targets:" in content
    assert "surface_only_fixes_rejected:" in content
```

- [ ] **Step 8: Run focused template tests and verify red**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py -q
```

Expected: FAIL because the senior consequence gate language and JSON fields are not implemented yet.

- [ ] **Step 9: Commit failing tests**

```powershell
git add tests/test_alignment_templates.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py
git commit -m "test: cover senior consequence gate templates"
```

---

### Task 2: Add Failing Structured Validator Tests

**Files:**
- Modify: `tests/hooks/test_artifact_hooks.py`
- Modify: `tests/execution/test_packet_schema.py`
- Modify: `tests/execution/test_packet_validator.py`
- Modify: `tests/execution/test_packet_compiler.py`
- Modify: `tests/execution/test_result_validator.py`

- [ ] **Step 1: Add artifact hook tests for specify handoff JSON**

In `tests/hooks/test_artifact_hooks.py`, append after the specify artifact validation tests:

```python
def test_validate_artifacts_blocks_triggered_consequence_handoff_without_analysis(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)

    (feature_dir / "brainstorming" / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "close team touches running workers",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_analysis": {
                    "affected_object_map": [],
                    "state_behavior_matrix": [],
                    "dependency_impact": [],
                    "recovery_and_validation": [],
                    "coverage_gaps": [],
                },
                "consequence_obligations": [],
                "stop_and_reopen_conditions": [],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("affected_object_map" in message for message in result.errors)
    assert any("consequence_obligations" in message for message in result.errors)
```

If `json` is not imported at the top of `tests/hooks/test_artifact_hooks.py`, add:

```python
import json
```

- [ ] **Step 2: Add artifact hook tests for plan contract**

Append:

```python
def test_validate_artifacts_blocks_plan_when_consequence_contract_is_not_designed(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "plan.md").write_text("# Plan\n\n## Design\n\nClose the team.\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "team close has running-worker semantics",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Define close behavior for running workers",
                        "affected_objects": ["team", "worker", "task queue"],
                        "owner": "sp-plan",
                        "latest_resolve_phase": "plan",
                        "status": "open",
                        "stop_and_reopen_condition": "No drain/cancel/force policy is chosen",
                    }
                ],
                "operational_consequence_decisions": [],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "plan", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("Operational Consequence Design" in message for message in result.errors)
    assert any("CA-001" in message for message in result.errors)
```

- [ ] **Step 3: Add artifact hook tests for task mapping**

Append:

```python
def test_validate_artifacts_blocks_tasks_when_consequence_obligation_is_unmapped(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text("- [ ] T001 Implement close team in src/team.py\n", encoding="utf-8")
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "handoff-to-tasks.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "running worker semantics must survive tasking",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_analysis": {
                    "affected_object_map": [{"object": "worker", "reason": "running workers are affected"}],
                    "state_behavior_matrix": [{"state": "running", "behavior": "drain before close completes"}],
                    "dependency_impact": [{"surface": "submit-result", "impact": "late result policy must be defined"}],
                    "recovery_and_validation": [{"validation": "pytest tests/test_team_close.py -q"}],
                    "coverage_gaps": [{"gap": "none", "decision": "covered by task mapping"}],
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Running workers drain before close completes",
                        "affected_objects": ["worker", "team"],
                        "owner": "sp-tasks",
                        "latest_resolve_phase": "tasks",
                        "status": "open",
                        "stop_and_reopen_condition": "No task validates drain behavior",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps({"version": 1, "status": "ready", "tasks": [{"task_id": "T001"}], "parallel_batches": [], "join_points": []}),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("CA-001" in message for message in result.errors)
    assert any("consequence" in message.lower() and "task-index.json" in message for message in result.errors)
```

Append the passing counterpart:

```python
def test_validate_artifacts_accepts_tasks_when_consequence_obligation_is_mapped(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(
        "## Consequence Obligation Mapping\n\n"
        "| Obligation ID | Task IDs | Validation |\n"
        "| --- | --- | --- |\n"
        "| CA-001 | T001 | pytest tests/test_team_close.py -q |\n\n"
        "- [ ] T001 Implement close team drain behavior in src/team.py\n",
        encoding="utf-8",
    )
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n", encoding="utf-8")
    (feature_dir / "handoff-to-tasks.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "consequence_gate": {
                    "triggered": True,
                    "trigger_reason": "running worker semantics must survive tasking",
                    "status": "ready",
                    "stand_down_reason": None,
                },
                "consequence_obligations": [
                    {
                        "obligation_id": "CA-001",
                        "claim": "Running workers drain before close completes",
                        "affected_objects": ["worker", "team"],
                        "owner": "sp-tasks",
                        "latest_resolve_phase": "tasks",
                        "status": "open",
                        "stop_and_reopen_condition": "No task validates drain behavior",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "ready",
                "tasks": [
                    {
                        "task_id": "T001",
                        "consequence_obligation_ids": ["CA-001"],
                    }
                ],
                "parallel_batches": [],
                "join_points": [],
            }
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.artifacts.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []
```

- [ ] **Step 4: Add packet schema tests**

In `tests/execution/test_packet_schema.py`, update imports to include `ConsequenceObligation`:

```python
    ConsequenceObligation,
```

In the packet construction inside `test_worker_task_packet_captures_required_execution_contract`, add:

```python
        consequence_obligations=[
            ConsequenceObligation(
                obligation_id="CA-001",
                claim="Running workers drain before close completes",
                affected_objects=["team", "worker"],
                recovery_validation_refs=["pytest tests/test_team_close.py -q"],
                owner="sp-tasks",
                latest_resolve_phase="tasks",
                status="open",
                stop_and_reopen_condition="No validation proves drain behavior",
            )
        ],
```

Add assertions:

```python
    assert packet.consequence_obligations[0].obligation_id == "CA-001"
    assert packet.consequence_obligations[0].affected_objects == ["team", "worker"]
```

In `test_worker_task_packet_round_trips_through_json`, add the same `consequence_obligations` construction and assertions:

```python
    assert restored.consequence_obligations[0].obligation_id == "CA-001"
    assert restored.consequence_obligations[0].claim == "Running workers drain before close completes"
```

- [ ] **Step 5: Add packet validator tests**

In `tests/execution/test_packet_validator.py`, update imports to include `ConsequenceObligation` and add this field to `sample_packet`:

```python
        consequence_obligations=[
            ConsequenceObligation(
                obligation_id="CA-001",
                claim="Running workers drain before close completes",
                affected_objects=["team", "worker"],
                recovery_validation_refs=["pytest tests/test_team_close.py -q"],
                owner="sp-tasks",
                latest_resolve_phase="tasks",
                status="open",
                stop_and_reopen_condition="No validation proves drain behavior",
            )
        ],
```

Append:

```python
def test_validate_worker_task_packet_rejects_incomplete_consequence_obligation(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.consequence_obligations[0].claim = ""

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP2"
    assert "consequence obligation" in exc.value.message
```

- [ ] **Step 6: Add packet compiler test**

In `tests/execution/test_packet_compiler.py`, add to the `tasks.md` content in `test_compile_worker_task_packet_merges_constitution_plan_and_task_sources` before the task checklist:

```python
                "## Consequence Obligation Mapping",
                "",
                "- CA-001 | tasks: T017 | claim: Running workers drain before close completes | affected_objects: team, worker | validation: pytest tests/unit/test_auth_service.py -q | stop_and_reopen_condition: No validation proves drain behavior",
                "",
```

Add assertions after packet creation:

```python
    assert packet.consequence_obligations[0].obligation_id == "CA-001"
    assert packet.consequence_obligations[0].affected_objects == ["team", "worker"]
    assert packet.consequence_obligations[0].recovery_validation_refs == ["pytest tests/unit/test_auth_service.py -q"]
```

- [ ] **Step 7: Add result evidence test**

In `tests/execution/test_result_validator.py`, update the packet schema import list to include:

```python
    ConsequenceObligation,
```

Append this helper near the existing fixture:

```python
def _add_sample_consequence_obligation(packet: WorkerTaskPacket) -> WorkerTaskPacket:
    packet.consequence_obligations = [
        ConsequenceObligation(
            obligation_id="CA-001",
            claim="Running workers drain before close completes",
            affected_objects=["team", "worker"],
            recovery_validation_refs=["pytest tests/unit/test_auth_service.py -q"],
            owner="sp-tasks",
            latest_resolve_phase="tasks",
            status="open",
            stop_and_reopen_condition="No validation proves drain behavior",
        )
    ]
    return packet
```

Append:

```python
def test_validate_worker_task_result_rejects_success_without_consequence_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet = _add_sample_consequence_obligation(sample_packet)

    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
                output="1 passed",
            )
        ],
        summary="Implemented auth flow",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "consequence evidence" in exc.value.message
```

Add the passing counterpart:

```python
def test_validate_worker_task_result_accepts_success_with_consequence_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet = _add_sample_consequence_obligation(sample_packet)

    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
                output="1 passed",
            )
        ],
        summary="Implemented auth flow",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
        consequence_evidence=[
            {
                "obligation_id": "CA-001",
                "evidence": "pytest tests/unit/test_auth_service.py -q passed",
            }
        ],
    )

    validated = validate_worker_task_result(result, sample_packet)

    assert validated.consequence_evidence[0]["obligation_id"] == "CA-001"
```

- [ ] **Step 8: Run focused validator tests and verify red**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py -q
```

Expected: FAIL because the validator and schema fields do not exist yet.

- [ ] **Step 9: Commit failing validator tests**

```powershell
git add tests/hooks/test_artifact_hooks.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py
git commit -m "test: cover structured consequence obligations"
```

---

### Task 3: Implement Shared Prompt Contract And Primary Workflow Text

**Files:**
- Create: `templates/command-partials/common/senior-consequence-analysis-gate.md`
- Modify: `templates/commands/discussion.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/debug.md`

- [ ] **Step 1: Create the shared partial**

Create `templates/command-partials/common/senior-consequence-analysis-gate.md` with:

```markdown
## Senior Consequence Analysis Gate

Use this gate when the request or discovered scope involves lifecycle operations, running or concurrent objects, destructive or hard-to-reverse actions, shared state, upstream or downstream contracts, user-visible failure paths, compatibility or migration concerns, security or retention impact, or multiple plausible behaviors that change product semantics.

The sequence is fixed:

1. **Project Cognition First**: Query project cognition when existing-system truth, ownership, consumers, state surfaces, verification routes, or change-propagation risk matter. The query is complete only when readiness drives routing, returned `minimal_live_reads` bounds inspection, and relevant facts are carried into the workflow artifact or durable state.
2. **Senior Consequence Analysis Second**: Turn those facts and gaps into concrete product and implementation consequences.

When triggered, produce or preserve these outputs:

- **Affected Object Map**: Objects, state surfaces, roles, commands, workflows, artifacts, processes, queues, results, external dependencies, and users affected by the change.
- **State-Behavior Matrix**: Required behavior for idle, active, queued, running, blocked, failed, partial, interrupted, stale, completed, and destructive states when relevant.
- **Dependency Impact Table**: Upstream callers, downstream consumers, adjacent workflows, background processes, data contracts, generated artifacts, and verification surfaces affected by the decision.
- **Recovery And Validation Contract**: Failure behavior, idempotency, retry, rollback or de-scope path, user-visible errors, observability, and evidence required to prove correctness.
- **Coverage Gaps**: What project cognition or minimal live reads could not establish, why it matters, and whether this workflow may continue with an assumption, must ask the user, must route to clarification or deep research, or must request map maintenance.

Use `CA-###` IDs for consequence obligations that must survive handoff. Each obligation needs a claim, affected objects, owner workflow, latest resolve phase, status, and stop-and-reopen condition.

The gate may stand down only for docs-only wording changes, trivial isolated fixes, or local refactors when the workflow records why no lifecycle, running-state, shared-state, destructive-operation, or consumer-impact trigger applies.
```

- [ ] **Step 2: Include the partial in primary commands**

In each file below, insert this include after the command-specific shell include and before the main workflow-specific instructions:

```markdown
{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}
```

Files:

- `templates/commands/discussion.md`
- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/fast.md`
- `templates/commands/quick.md`
- `templates/commands/debug.md`

- [ ] **Step 3: Add discussion-specific section**

In `templates/commands/discussion.md`, add:

```markdown
## Senior Maintainer Review

Before finalizing technical options or marking a discussion handoff-ready, run the Senior Consequence Analysis Gate when the idea touches lifecycle, running work, destructive behavior, shared state, downstream consumers, compatibility, or multiple possible product semantics.

For a request like "close team", do not reduce the idea to a close action. Name the affected team state, worker roster, queued tasks, running workers, heartbeat/result state, `status`, `await`, `resume`, `cleanup`, late result behavior, and recovery path. Present concrete alternatives such as block, drain, cancel, detach, force, or defer with trade-offs and senior default recommendations when evidence supports them.

Write consequence findings into:

- `requirements.md`: user-visible state rules, scope, non-goals, acceptance signals, and open behavior choices.
- `technical-options.md`: 2-3 concrete handling strategies and trade-offs.
- `project-context.md`: project cognition facts, returned `minimal_live_reads`, inference notes, and coverage gaps.
- `open-questions.md`: only decisions that materially change behavior, implementation shape, or validation.
- `handoff-to-specify.md`: human-readable `CA-###` obligations that `sp-specify` must preserve.
- `handoff-to-specify.json`: machine-readable mirror of triggered gate status, consequence analysis, `CA-###` obligations, coverage gaps, and stop-and-reopen conditions.
- `handoffs/CAND-001-handoff-to-specify.md`: candidate-specific consequence obligations when split mode selects one bounded candidate.
- `handoffs/CAND-001-handoff-to-specify.json`: same-stem JSON companion for the selected candidate.

Markdown and JSON handoffs must agree on consequence obligation IDs, claims, blocking level, owner, latest resolve phase, status, and stop-and-reopen condition. If split mode is active, the selected candidate handoff includes only consequence obligations that shape that candidate plus dependency, non-goal, or deferred-sibling obligations needed to prevent scope drift.

Do not mark the discussion `handoff-ready` when the gate triggers and no concrete Affected Object Map, State-Behavior Matrix, Dependency Impact Table, or Recovery And Validation Contract exists.
```

- [ ] **Step 4: Add specify-specific section**

In `templates/commands/specify.md`, add:

```markdown
## Consequence Completeness Gate

After project cognition intake and before final alignment release, consume any `CA-###` obligations from discussion Markdown, discussion JSON, candidate handoffs, and `brainstorming/handoff-to-specify.json`.

For triggered consequence work, `spec.md`, `alignment.md`, `context.md`, and `references.md` must preserve:

- lifecycle states and user-visible behavior per state
- failure semantics and permissions
- non-goals and deferred sibling scope
- acceptance signals and validation implications
- affected objects, state surfaces, dependencies, consumers, and coverage gaps
- project cognition query evidence and returned `minimal_live_reads`

If lifecycle, destructive, running-state, shared-state, or downstream contract semantics materially affect planning and remain unresolved, do not release `Aligned: ready for plan`. Resolve evidence-backed decisions here, ask the user when behavior is a product choice, route to `{{invoke:clarify}}` for requirement ambiguity, or route to `{{invoke:deep-research}}` when implementation-chain feasibility is unproven.
```

- [ ] **Step 5: Add plan-specific section**

In `templates/commands/plan.md`, add:

```markdown
## Operational Consequence Design

When `spec.md`, `alignment.md`, `context.md`, discussion handoff JSON, or deep-research handoff IDs contain `CA-###` obligations, convert them into implementation strategy before handing off to `{{invoke:tasks}}`.

`plan.md` must define operational state machine, ordering, locking or lease behavior, idempotency, concurrency hazards, recovery path, observability, rollout or migration notes, and verification strategy for each implementation-shaping consequence obligation.

Write `plan-contract.json` with the same `CA-###` obligations, operational decisions, unresolved coverage gaps, and stop-and-reopen conditions. A plan that says only "implement close team" without close ordering, worker/result interactions, idempotency, and validation is incomplete.
```

- [ ] **Step 6: Add tasks-specific section**

In `templates/commands/tasks.md`, add:

```markdown
## Consequence Obligation Mapping

Before completing task generation, map each implementation-shaping `CA-###` obligation from `plan.md`, `plan-contract.json`, `alignment.md`, `context.md`, or `handoff-to-tasks.json` to one or more tasks, packets, join points, validation gates, or explicit deferrals.

Each mapped task or packet must include:

- objective
- write set
- affected state or dependency
- required references
- forbidden drift
- validation command or concrete manual check
- done condition
- stop-and-reopen condition

Emit the mapping in `tasks.md`, `handoff-to-tasks.json`, `task-index.json`, and per-task JSON under `task-packets/` when those machine-readable artifacts are generated. Do not complete task generation normally when lifecycle, dependency, state, recovery, validation, or stop-and-reopen obligations from planning are unmapped.
```

- [ ] **Step 7: Add fast-specific section**

In `templates/commands/fast.md`, add:

```markdown
## Fast Path Consequence Routing

The Senior Consequence Analysis Gate is an upgrade trigger on the fast path, not a reason to create planning artifacts inside `sp-fast`.

Upgrade to `/sp-quick` immediately if the gate triggers but the consequence model is bounded to one quick workspace with concrete validation.

Upgrade to `/sp-specify` immediately if the change needs user-level lifecycle decisions, running-state semantics, destructive-operation policy, shared-state behavior, broad compatibility handling, durable acceptance criteria, or multi-capability scope.

Stay on `sp-fast` only when you can record a stand-down reason proving no lifecycle, running-state, shared-state, destructive-operation, downstream consumer, or compatibility impact exists. Do not add planning artifacts to satisfy this gate on the fast path.
```

- [ ] **Step 8: Add quick-specific section and status fields**

In `templates/commands/quick.md`, add:

```markdown
## Quick Consequence Boundary

Continue in quick only when the consequence model is bounded, implementation fits one quick workspace, and validation evidence is concrete. Escalate to `{{invoke:specify}}` when the change needs user-level lifecycle decisions, broad compatibility handling, durable feature semantics, or multi-capability scope. Escalate to `{{invoke:debug}}` when the task is a bug or regression and root cause is unknown.
```

In the `STATUS.md` template block, add:

```markdown
## Senior Consequence Analysis

affected_objects:
state_behavior_matrix:
dependency_impact:
recovery_and_validation:
project_cognition_evidence:
coverage_gaps:
escalation_decision:
```

- [ ] **Step 9: Add debug-specific section**

In `templates/commands/debug.md`, add:

```markdown
## Debug Consequence Loop

Use the Senior Consequence Analysis Gate for failures that involve lifecycle, running work, shared state, downstream consumers, destructive behavior, or multiple plausible ownership loops.

Use project cognition to identify truth owners, state surfaces, consumers, verification routes, and known unknowns. Preserve control state vs observation state. Trace the dependency loop from input event to control decision to resource allocation to state transition to external observation.

Record affected objects, dependency loop, control state, observation state, candidate queue, adjacent risk targets, root-cause evidence, and loop restoration proof. Reject surface-only fixes that hide symptoms without restoring the owning loop.
```

- [ ] **Step 10: Run template tests and verify primary workflow tests pass**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py -q
```

Expected: Primary workflow tests added in Task 1 pass. JSON and artifact template tests may still fail until later tasks.

- [ ] **Step 11: Commit primary workflow prompt contract**

```powershell
git add templates/command-partials/common/senior-consequence-analysis-gate.md templates/commands/discussion.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/fast.md templates/commands/quick.md templates/commands/debug.md
git commit -m "feat: add senior consequence workflow gate"
```

---

### Task 4: Implement Adjacent Workflow And Shell Partial Carry-Forward

**Files:**
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/command-partials/discussion/shell.md`
- Modify: `templates/command-partials/specify/shell.md`
- Modify: `templates/command-partials/plan/shell.md`
- Modify: `templates/command-partials/tasks/shell.md`
- Modify: `templates/command-partials/fast/shell.md`
- Modify: `templates/command-partials/quick/shell.md`
- Modify: `templates/command-partials/debug/shell.md`
- Modify: `templates/command-partials/implement/shell.md`

- [ ] **Step 1: Include the shared gate in adjacent commands**

Insert this include after the shell include or near the context-loading section in each adjacent command:

```markdown
{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}
```

Files:

- `templates/commands/clarify.md`
- `templates/commands/deep-research.md`
- `templates/commands/analyze.md`
- `templates/commands/implement.md`

- [ ] **Step 2: Add clarify carry-forward section**

In `templates/commands/clarify.md`, add:

```markdown
## Consequence Clarification Lane

When `sp-specify` or upstream artifacts carry unresolved `CA-###` consequence obligations, preserve the same IDs and resolve the blocking decision by user answer or evidence-backed clarification. Update the canonical requirement artifacts instead of creating a parallel truth source.

Return clarified lifecycle, destructive-operation, dependency, state-behavior, recovery, validation, and stop-and-reopen decisions to `spec.md`, `alignment.md`, `context.md`, and `brainstorming/handoff-to-specify.json`.
```

- [ ] **Step 3: Add deep-research carry-forward section**

In `templates/commands/deep-research.md`, add:

```markdown
## Consequence-Sensitive Research Tracks

When requirements are clear but a `CA-###` obligation depends on external tools, platform behavior, runtime libraries, protocol behavior, or a disposable demo, preserve it as a research track. The Planning Handoff must include the obligation ID, evidence or spike ID, implementation-chain implication, validation implication, residual risk, and any decision `sp-plan` must not weaken into an assumption.
```

- [ ] **Step 4: Add analyze carry-forward section**

In `templates/commands/analyze.md`, add:

```markdown
## Consequence Preservation Analysis

Before clearing implementation, verify that `tasks.md`, `handoff-to-tasks.json`, `task-index.json`, and task packets preserve `CA-###` obligations from `plan.md`, `plan-contract.json`, `alignment.md`, and `context.md`.

Block when lifecycle, dependency, state, recovery, validation, or stop-and-reopen obligations were dropped during task generation. Route back to `{{invoke:tasks}}`, `{{invoke:plan}}`, `{{invoke:clarify}}`, or `{{invoke:deep-research}}` according to where the missing truth belongs.
```

- [ ] **Step 5: Add implement carry-forward section**

In `templates/commands/implement.md`, add:

```markdown
## Consequence Obligation Execution

Implementation lanes consume `CA-###` obligations from `WorkerTaskPacket`, `task-packets/*.json`, `task-index.json`, and `handoff-to-implement.json`. Do not reinterpret or drop affected states, dependency guardrails, required references, validation commands, done conditions, or stop-and-reopen conditions during execution.

If repository evidence proves an obligation is wrong, incomplete, or impossible, stop and reopen upstream instead of silently changing the product or operational semantics. Completion evidence must show each packet consequence obligation was honored, deferred under an approved condition, or returned upstream.
```

- [ ] **Step 6: Update shell partials**

Add this concise bullet group to each shell partial listed in this task:

```markdown
- Senior consequence analysis: if lifecycle, running-state, destructive-operation, shared-state, downstream consumer, compatibility, or multiple-behavior semantics are in scope, preserve `CA-###` obligations through affected objects, state behavior, dependency impact, recovery/validation, coverage gaps, and stop-and-reopen conditions.
- Project cognition supports the analysis but does not replace product semantics; record coverage gaps when cognition or minimal live reads cannot decide behavior.
```

For `templates/command-partials/fast/shell.md`, use this second bullet instead:

```markdown
- On `sp-fast`, a triggered senior consequence gate is an upgrade trigger; stay on fast only with a recorded stand-down reason and do not create planning artifacts to satisfy the gate.
```

- [ ] **Step 7: Run focused tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -q
```

Expected: Adjacent workflow tests pass.

- [ ] **Step 8: Commit adjacent workflow carry-forward**

```powershell
git add templates/commands/clarify.md templates/commands/deep-research.md templates/commands/analyze.md templates/commands/implement.md templates/command-partials/discussion/shell.md templates/command-partials/specify/shell.md templates/command-partials/plan/shell.md templates/command-partials/tasks/shell.md templates/command-partials/fast/shell.md templates/command-partials/quick/shell.md templates/command-partials/debug/shell.md templates/command-partials/implement/shell.md
git commit -m "feat: preserve consequence obligations across adjacent workflows"
```

---

### Task 5: Update Artifact Templates

**Files:**
- Modify: `templates/discussion-state-template.md`
- Modify: `templates/spec-template.md`
- Modify: `templates/alignment-template.md`
- Modify: `templates/context-template.md`
- Modify: `templates/references-template.md`
- Modify: `templates/plan-template.md`
- Modify: `templates/tasks-template.md`
- Modify: `templates/brainstorming-handoff-specify-template.json`
- Modify: `templates/plan-contract-template.json`
- Modify: `templates/task-index-template.json`
- Modify: `templates/task-packet-template.json`
- Modify: `templates/implement-execution-state-template.json`
- Modify: `templates/debug.md`

- [ ] **Step 1: Add Markdown artifact sections**

Add the following section to `templates/discussion-state-template.md`:

```markdown
## Senior Consequence Analysis

- consequence_gate_status: not-triggered | triggered | ready | blocked | stood-down
- trigger_reason: none
- stand_down_reason: none
- active_consequence_obligations: []
- latest_consequence_handoff: none
- coverage_gap_count: 0
```

Add this section to `templates/spec-template.md`:

```markdown
## Lifecycle And State Behavior

- `CA-###`: [Affected object] -> [state] -> [required user-visible behavior]
```

Add this section to `templates/alignment-template.md`:

```markdown
## Consequence Completeness

- Gate status: [not-triggered | ready | blocked | stood-down]
- Resolved `CA-###` obligations:
- Unresolved planning blockers:
- Force-carried risks:
- Required next workflow:
```

Add this section to `templates/context-template.md`:

```markdown
## Affected Object Map

| Obligation ID | Object / State Surface | Owner | Consumers | Evidence | Coverage Gap |
| --- | --- | --- | --- | --- | --- |
| CA-### | [object] | [owner] | [consumers] | [project cognition or live read] | [gap or none] |

## Dependency Impact Table

| Obligation ID | Upstream / Downstream Surface | Impact | Required Handling |
| --- | --- | --- | --- |
| CA-### | [surface] | [impact] | [handling] |
```

Add this section to `templates/references-template.md`:

```markdown
## Consequence Evidence

- `CA-###`: project cognition query, returned `minimal_live_reads`, discussion handoff, source evidence, or research evidence that supports the obligation.
```

Add this section to `templates/plan-template.md`:

```markdown
## Operational Consequence Design

| Obligation ID | State Machine / Ordering Decision | Concurrency And Idempotency | Recovery Path | Validation Evidence |
| --- | --- | --- | --- | --- |
| CA-### | [decision] | [lock, lease, queue, or ordering rule] | [retry, rollback, de-scope, or reopen path] | [command or manual check] |
```

Add this section to `templates/tasks-template.md`:

```markdown
## Consequence Obligation Mapping

| Obligation ID | Task IDs | Affected State / Dependency | Required References | Validation | Stop And Reopen |
| --- | --- | --- | --- | --- | --- |
| CA-### | T### | [state or dependency] | [files or artifacts] | [command or manual check] | [condition] |
```

- [ ] **Step 2: Update brainstorming handoff JSON template**

Replace `templates/brainstorming-handoff-specify-template.json` with:

```json
{
  "version": 1,
  "status": "pending",
  "facts_file": "brainstorming/facts.json",
  "route_file": "brainstorming/route.json",
  "intent_file": "brainstorming/intent.json",
  "complexity_file": "brainstorming/complexity.json",
  "entry_source": "none",
  "discussion_slug": null,
  "candidate_id": null,
  "candidate_title": null,
  "source_split_plan": null,
  "source_handoff": null,
  "source_handoff_json": null,
  "prior_candidates": [],
  "deferred_candidates": [],
  "stage_scope_boundary": null,
  "soft_unknowns": [],
  "must_preserve": [],
  "conflicts": [],
  "coverage_status": "not-applicable",
  "handoff_integrity": "not-checked",
  "compile_ready": false,
  "consequence_gate": {
    "triggered": false,
    "trigger_reason": null,
    "status": "not-applicable",
    "stand_down_reason": null
  },
  "consequence_analysis": {
    "affected_object_map": [],
    "state_behavior_matrix": [],
    "dependency_impact": [],
    "recovery_and_validation": [],
    "coverage_gaps": []
  },
  "consequence_obligations": [],
  "stop_and_reopen_conditions": []
}
```

- [ ] **Step 3: Update plan contract JSON template**

Replace `templates/plan-contract-template.json` with:

```json
{
  "version": 1,
  "status": "pending",
  "route": null,
  "intent": null,
  "complexity_level": null,
  "must_preserve": [],
  "allowed_optimization_scope": [],
  "acceptance_obligations": [],
  "handoff_to_tasks_ready": false,
  "consequence_gate": {
    "triggered": false,
    "trigger_reason": null,
    "status": "not-applicable",
    "stand_down_reason": null
  },
  "consequence_analysis": {
    "affected_object_map": [],
    "state_behavior_matrix": [],
    "dependency_impact": [],
    "recovery_and_validation": [],
    "coverage_gaps": []
  },
  "consequence_obligations": [],
  "operational_consequence_decisions": [],
  "stop_and_reopen_conditions": []
}
```

- [ ] **Step 4: Update task index JSON template**

Replace `templates/task-index-template.json` with:

```json
{
  "version": 1,
  "status": "pending",
  "tasks": [],
  "parallel_batches": [],
  "join_points": [],
  "consequence_gate": {
    "triggered": false,
    "trigger_reason": null,
    "status": "not-applicable",
    "stand_down_reason": null
  },
  "consequence_analysis": {
    "affected_object_map": [],
    "state_behavior_matrix": [],
    "dependency_impact": [],
    "recovery_and_validation": [],
    "coverage_gaps": []
  },
  "consequence_obligations": [],
  "consequence_task_map": [],
  "stop_and_reopen_conditions": []
}
```

- [ ] **Step 5: Update task packet JSON template**

Replace `templates/task-packet-template.json` with:

```json
{
  "version": 1,
  "task_id": "",
  "objective": "",
  "complexity_level": null,
  "authoritative_inputs": [],
  "must_preserve": [],
  "allowed_optimization_scope": [],
  "required_validation": [],
  "stop_and_reopen_conditions": [],
  "consequence_gate": {
    "triggered": false,
    "trigger_reason": null,
    "status": "not-applicable",
    "stand_down_reason": null
  },
  "consequence_analysis": {
    "affected_object_map": [],
    "state_behavior_matrix": [],
    "dependency_impact": [],
    "recovery_and_validation": [],
    "coverage_gaps": []
  },
  "consequence_obligations": [],
  "affected_states": [],
  "dependency_guardrails": [],
  "recovery_validation": []
}
```

- [ ] **Step 6: Update implement execution state JSON template**

Add these fields to `templates/implement-execution-state-template.json` without removing existing fields:

```json
  "consequence_gate": {
    "triggered": false,
    "trigger_reason": null,
    "status": "not-applicable",
    "stand_down_reason": null
  },
  "consequence_analysis": {
    "affected_object_map": [],
    "state_behavior_matrix": [],
    "dependency_impact": [],
    "recovery_and_validation": [],
    "coverage_gaps": []
  },
  "consequence_obligations": [],
  "applied_consequence_obligations": [],
  "stop_and_reopen_conditions": []
```

Keep valid JSON commas around the inserted object members.

- [ ] **Step 7: Update debug session template**

In `templates/debug.md`, add:

```markdown
## Senior Consequence Analysis

affected_objects:
dependency_loop:
control_state:
observation_state:
state_behavior_matrix:
dependency_impact:
recovery_and_validation:
coverage_gaps:
adjacent_risk_targets:
surface_only_fixes_rejected:
```

- [ ] **Step 8: Run template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_debug_template_guidance.py -q
```

Expected: Template and JSON contract tests pass, except any structured validator tests that still depend on Python changes.

- [ ] **Step 9: Commit artifact templates**

```powershell
git add templates/discussion-state-template.md templates/spec-template.md templates/alignment-template.md templates/context-template.md templates/references-template.md templates/plan-template.md templates/tasks-template.md templates/brainstorming-handoff-specify-template.json templates/plan-contract-template.json templates/task-index-template.json templates/task-packet-template.json templates/implement-execution-state-template.json templates/debug.md
git commit -m "feat: carry consequence obligations in artifacts"
```

---

### Task 6: Implement Artifact Validation

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Test: `tests/hooks/test_artifact_hooks.py`

- [ ] **Step 1: Add consequence validation helpers**

In `src/specify_cli/hooks/artifact_validation.py`, add near the existing constants:

```python
CONSEQUENCE_ANALYSIS_REQUIRED_KEYS = (
    "affected_object_map",
    "state_behavior_matrix",
    "dependency_impact",
    "recovery_and_validation",
    "coverage_gaps",
)

CONSEQUENCE_OBLIGATION_REQUIRED_KEYS = (
    "obligation_id",
    "claim",
    "affected_objects",
    "owner",
    "latest_resolve_phase",
    "status",
    "stop_and_reopen_condition",
)

CONSEQUENCE_OPERATIONAL_REQUIRED_SECTION = "## Operational Consequence Design"
CONSEQUENCE_TASK_MAPPING_REQUIRED_SECTION = "## Consequence Obligation Mapping"
```

Add these helper functions after `_validate_unknown_objects`:

```python
def _json_gate_is_triggered(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    gate = payload.get("consequence_gate")
    if not isinstance(gate, dict):
        return False
    return gate.get("triggered") is True


def _validate_consequence_json_payload(payload: Any, label: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{label} must be a JSON object before consequence validation can run"]
    if not _json_gate_is_triggered(payload):
        return []

    errors: list[str] = []
    analysis = payload.get("consequence_analysis")
    if not isinstance(analysis, dict):
        return [f"{label} consequence_analysis must be an object when consequence_gate.triggered is true"]

    for key in CONSEQUENCE_ANALYSIS_REQUIRED_KEYS:
        value = analysis.get(key)
        if not isinstance(value, list) or not value:
            errors.append(f"{label} consequence_analysis.{key} must be a non-empty array when the gate is triggered")

    obligations = payload.get("consequence_obligations")
    if not isinstance(obligations, list) or not obligations:
        errors.append(f"{label} consequence_obligations must be a non-empty array when the gate is triggered")
        return errors

    for index, obligation in enumerate(obligations):
        if not isinstance(obligation, dict):
            errors.append(f"{label} consequence_obligations[{index}] must be an object")
            continue
        for key in CONSEQUENCE_OBLIGATION_REQUIRED_KEYS:
            value = obligation.get(key)
            if isinstance(value, list):
                if not value:
                    errors.append(f"{label} consequence_obligations[{index}].{key} must not be empty")
            elif not str(value or "").strip():
                errors.append(f"{label} consequence_obligations[{index}].{key} must not be empty")

    return errors


def _consequence_obligation_ids(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    obligations = payload.get("consequence_obligations")
    if not isinstance(obligations, list):
        return set()
    return {
        str(item.get("obligation_id") or "").strip()
        for item in obligations
        if isinstance(item, dict) and str(item.get("obligation_id") or "").strip()
    }
```

- [ ] **Step 2: Validate brainstorming handoff JSON**

In `_validate_specify_draft_artifacts`, replace the existing direct handoff validation call:

```python
    errors.extend(
        _validate_brainstorming_json_artifact(
            feature_dir,
            "brainstorming/handoff-to-specify.json",
            validate_unknowns=True,
        )
    )
```

with:

```python
    handoff_payload, handoff_errors = _read_json_artifact(
        feature_dir / "brainstorming" / "handoff-to-specify.json",
        "brainstorming/handoff-to-specify.json",
    )
    if handoff_errors:
        errors.extend(handoff_errors)
    else:
        errors.extend(_validate_unknown_objects(handoff_payload, "brainstorming/handoff-to-specify.json"))
        errors.extend(_validate_consequence_json_payload(handoff_payload, "brainstorming/handoff-to-specify.json"))
```

- [ ] **Step 3: Validate plan consequence contract**

Add:

```python
def _validate_plan_consequence_contract(feature_dir: Path) -> list[str]:
    contract_path = feature_dir / "plan-contract.json"
    if not contract_path.exists():
        return []
    payload, read_errors = _read_json_artifact(contract_path, "plan-contract.json")
    if read_errors:
        return read_errors
    errors = _validate_consequence_json_payload(payload, "plan-contract.json")
    if not _json_gate_is_triggered(payload):
        return errors

    plan_path = feature_dir / "plan.md"
    plan_content = plan_path.read_text(encoding="utf-8", errors="replace")
    if CONSEQUENCE_OPERATIONAL_REQUIRED_SECTION not in plan_content:
        ids = ", ".join(sorted(_consequence_obligation_ids(payload))) or "triggered consequence obligations"
        errors.append(f"plan.md is missing {CONSEQUENCE_OPERATIONAL_REQUIRED_SECTION} for {ids}")

    operational_decisions = payload.get("operational_consequence_decisions") if isinstance(payload, dict) else None
    if not isinstance(operational_decisions, list) or not operational_decisions:
        ids = ", ".join(sorted(_consequence_obligation_ids(payload))) or "triggered consequence obligations"
        errors.append(f"plan-contract.json operational_consequence_decisions must map {ids}")

    return errors
```

In `validate_artifacts_hook`, inside `if command_name == "plan":`, add:

```python
        validation_errors.extend(_validate_plan_consequence_contract(feature_dir))
```

- [ ] **Step 4: Validate task consequence mapping**

Add:

```python
def _task_index_consequence_ids(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    ids: set[str] = set()
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return ids
    for task in tasks:
        if not isinstance(task, dict):
            continue
        raw_ids = task.get("consequence_obligation_ids")
        if isinstance(raw_ids, list):
            ids.update(str(item).strip() for item in raw_ids if str(item).strip())
    return ids


def _validate_tasks_consequence_contract(feature_dir: Path) -> list[str]:
    handoff_path = feature_dir / "handoff-to-tasks.json"
    if not handoff_path.exists():
        return []

    handoff_payload, handoff_errors = _read_json_artifact(handoff_path, "handoff-to-tasks.json")
    if handoff_errors:
        return handoff_errors

    errors = _validate_consequence_json_payload(handoff_payload, "handoff-to-tasks.json")
    if not _json_gate_is_triggered(handoff_payload):
        return errors

    required_ids = _consequence_obligation_ids(handoff_payload)
    task_index_path = feature_dir / "task-index.json"
    if not task_index_path.exists():
        errors.append("task-index.json is required when handoff-to-tasks.json carries triggered consequence obligations")
        return errors

    task_index_payload, task_index_errors = _read_json_artifact(task_index_path, "task-index.json")
    if task_index_errors:
        errors.extend(task_index_errors)
        return errors

    mapped_ids = _task_index_consequence_ids(task_index_payload)
    missing_ids = sorted(required_ids - mapped_ids)
    if missing_ids:
        errors.append(
            "task-index.json is missing consequence mapping for: " + ", ".join(missing_ids)
        )

    tasks_content = (feature_dir / "tasks.md").read_text(encoding="utf-8", errors="replace")
    if CONSEQUENCE_TASK_MAPPING_REQUIRED_SECTION not in tasks_content:
        errors.append(f"tasks.md is missing {CONSEQUENCE_TASK_MAPPING_REQUIRED_SECTION}")

    return errors
```

In `validate_artifacts_hook`, inside `if command_name == "tasks":`, add:

```python
        validation_errors.extend(_validate_tasks_consequence_contract(feature_dir))
```

- [ ] **Step 5: Run artifact hook tests**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit artifact validation**

```powershell
git add src/specify_cli/hooks/artifact_validation.py tests/hooks/test_artifact_hooks.py
git commit -m "feat: validate consequence artifacts"
```

---

### Task 7: Implement Packet And Result Consequence Contracts

**Files:**
- Modify: `src/specify_cli/execution/packet_schema.py`
- Modify: `src/specify_cli/execution/packet_compiler.py`
- Modify: `src/specify_cli/execution/packet_validator.py`
- Modify: `src/specify_cli/execution/result_schema.py`
- Modify: `src/specify_cli/execution/result_validator.py`
- Test: `tests/execution/test_packet_schema.py`
- Test: `tests/execution/test_packet_validator.py`
- Test: `tests/execution/test_packet_compiler.py`
- Test: `tests/execution/test_result_validator.py`

- [ ] **Step 1: Add packet schema dataclass**

In `src/specify_cli/execution/packet_schema.py`, add before `WorkerTaskPacket`:

```python
@dataclass(slots=True)
class ConsequenceObligation:
    obligation_id: str
    claim: str = ""
    affected_objects: list[str] = field(default_factory=list)
    state_behavior_refs: list[str] = field(default_factory=list)
    dependency_refs: list[str] = field(default_factory=list)
    recovery_validation_refs: list[str] = field(default_factory=list)
    owner: str = ""
    latest_resolve_phase: str = ""
    status: str = "open"
    stop_and_reopen_condition: str = ""
```

Add this field to `WorkerTaskPacket`:

```python
    consequence_obligations: list[ConsequenceObligation] = field(default_factory=list)
```

Keep `packet_version: int = 2` for backward compatibility.

- [ ] **Step 2: Parse consequence obligations from JSON**

In `worker_task_packet_from_json`, add before the `WorkerTaskPacket` construction:

```python
    consequence_obligations = [
        ConsequenceObligation(**_filter_dataclass_payload(ConsequenceObligation, item))
        for item in payload.get("consequence_obligations", [])
        if isinstance(item, dict)
    ]
```

Add to `packet_payload`:

```python
    packet_payload["consequence_obligations"] = consequence_obligations
```

- [ ] **Step 3: Validate packet obligations**

In `src/specify_cli/execution/packet_validator.py`, add inside `validate_worker_task_packet` before `return packet`:

```python
    for obligation in packet.consequence_obligations:
        if not obligation.obligation_id.strip():
            raise PacketValidationError("DP2", "consequence obligation is missing obligation_id")
        if not obligation.claim.strip():
            raise PacketValidationError("DP2", f"consequence obligation {obligation.obligation_id} is missing claim")
        if not obligation.affected_objects:
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing affected_objects",
            )
        if not obligation.stop_and_reopen_condition.strip():
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing stop_and_reopen_condition",
            )
```

- [ ] **Step 4: Compile consequence obligations from tasks**

In `src/specify_cli/execution/packet_compiler.py`, import `ConsequenceObligation`:

```python
    ConsequenceObligation,
```

Add helper functions before `compile_worker_task_packet`:

```python
CONSEQUENCE_ID_RE = re.compile(r"\bCA-\d{3}\b")


def _parse_pipe_fields(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_part in line.split("|"):
        part = raw_part.strip().strip("-").strip()
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    return fields


def _split_csv_field(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _consequence_obligations_for_task(tasks_text: str, task_id: str) -> list[ConsequenceObligation]:
    section = _section_body(tasks_text, "Consequence Obligation Mapping")
    obligations: list[ConsequenceObligation] = []
    seen: set[str] = set()
    for raw_line in section.splitlines():
        if task_id not in raw_line:
            continue
        match = CONSEQUENCE_ID_RE.search(raw_line)
        if not match:
            continue
        obligation_id = match.group(0)
        if obligation_id in seen:
            continue
        seen.add(obligation_id)
        fields = _parse_pipe_fields(raw_line)
        obligations.append(
            ConsequenceObligation(
                obligation_id=obligation_id,
                claim=fields.get("claim", raw_line.strip()),
                affected_objects=_split_csv_field(fields.get("affected_objects", "")),
                recovery_validation_refs=_split_csv_field(fields.get("validation", "")),
                owner="sp-tasks",
                latest_resolve_phase="tasks",
                status=fields.get("status", "open"),
                stop_and_reopen_condition=fields.get("stop_and_reopen_condition", ""),
            )
        )
    return obligations
```

In the `WorkerTaskPacket(...)` call, add:

```python
        consequence_obligations=_consequence_obligations_for_task(tasks_text, task_id),
```

- [ ] **Step 5: Add result schema field**

In `src/specify_cli/execution/result_schema.py`, add to `WorkerTaskResult`:

```python
    consequence_evidence: list[dict[str, str]] = field(default_factory=list)
```

In `worker_task_result_from_json`, normalize it:

```python
    result_payload["consequence_evidence"] = _normalize_evidence_items(
        result_payload.get("consequence_evidence", [])
    )
```

- [ ] **Step 6: Validate result evidence**

In `src/specify_cli/execution/result_validator.py`, inside the `if result.status == "success":` block after validation command checks, add:

```python
        if packet.consequence_obligations:
            evidence_ids = {
                str(item.get("obligation_id") or "").strip()
                for item in result.consequence_evidence
                if isinstance(item, dict)
            }
            required_ids = {
                obligation.obligation_id
                for obligation in packet.consequence_obligations
                if obligation.obligation_id.strip()
            }
            missing_ids = sorted(required_ids - evidence_ids)
            if missing_ids:
                raise PacketValidationError(
                    "DP3",
                    "worker result is missing consequence evidence for: " + ", ".join(missing_ids),
                )
```

- [ ] **Step 7: Run execution contract tests**

Run:

```powershell
pytest tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit packet/result contracts**

```powershell
git add src/specify_cli/execution/packet_schema.py src/specify_cli/execution/packet_compiler.py src/specify_cli/execution/packet_validator.py src/specify_cli/execution/result_schema.py src/specify_cli/execution/result_validator.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py
git commit -m "feat: carry consequence obligations in packets"
```

---

### Task 8: Update Docs, Passive Skills, And Integration Assertions

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `tests/test_runtime_handbook_contract.py`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Add docs tests**

In `tests/test_runtime_handbook_contract.py`, append:

```python
def test_docs_explain_project_cognition_supports_but_does_not_replace_consequence_analysis() -> None:
    for rel_path in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    ):
        content = _read(rel_path).lower()

        assert "senior consequence analysis gate" in content
        assert "project cognition" in content
        assert "necessary but not sufficient" in content
        assert "affected object map" in content
        assert "state-behavior matrix" in content
        assert "dependency impact" in content
        assert "coverage gaps" in content
```

In `tests/test_specify_guidance_docs.py`, append:

```python
def test_guidance_docs_teach_consequence_gate_across_workflow_mainline() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        lowered = content.lower()
        assert "senior consequence analysis gate" in lowered
        assert "`discussion`" in content
        assert "`specify`" in content
        assert "`plan`" in content
        assert "`tasks`" in content
        assert "`fast`" in content
        assert "`quick`" in content
        assert "`debug`" in content
        assert "close team" in lowered
        assert "running workers" in lowered
        assert "ca-###" in lowered
```

- [ ] **Step 2: Add Markdown integration rendering assertions**

In `tests/integrations/test_integration_base_markdown.py`, add these assertions to `_assert_discussion_contract`:

```python
    assert "senior consequence analysis gate" in command_lower
    assert "affected object map" in command_lower
    assert "state-behavior matrix" in command_lower
    assert "handoff-to-specify.json" in command_content
```

Add this method to `MarkdownIntegrationTests`:

```python
    def test_generated_primary_workflows_include_consequence_gate(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        generated = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in i.commands_dest(tmp_path).glob("**/*")
            if path.is_file()
        )

        assert "senior consequence analysis gate" in generated
        assert "affected object map" in generated
        assert "state-behavior matrix" in generated
        assert "dependency impact table" in generated
        assert "ca-###" in generated
```

- [ ] **Step 3: Add TOML integration rendering assertions**

In `tests/integrations/test_integration_base_toml.py`, add these assertions to `_assert_discussion_contract`:

```python
    assert "senior consequence analysis gate" in command_lower
    assert "affected object map" in command_lower
    assert "state-behavior matrix" in command_lower
    assert "handoff-to-specify.json" in command_content
```

Add this method to `TomlIntegrationTests`:

```python
    def test_generated_primary_workflows_include_consequence_gate(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        generated = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in i.commands_dest(tmp_path).glob("**/*")
            if path.is_file()
        )

        assert "senior consequence analysis gate" in generated
        assert "affected object map" in generated
        assert "state-behavior matrix" in generated
        assert "dependency impact table" in generated
        assert "ca-###" in generated
```

- [ ] **Step 4: Add skills integration rendering assertions**

In `tests/integrations/test_integration_base_skills.py`, add these assertions to `_assert_discussion_contract`:

```python
    assert "senior consequence analysis gate" in skill_lower
    assert "affected object map" in skill_lower
    assert "state-behavior matrix" in skill_lower
    assert "handoff-to-specify.json" in skill_content
```

Add this method to `SkillsIntegrationTests`:

```python
    def test_generated_primary_workflows_include_consequence_gate(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        generated = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in i.skills_dest(tmp_path).glob("**/*")
            if path.is_file()
        )

        assert "senior consequence analysis gate" in generated
        assert "affected object map" in generated
        assert "state-behavior matrix" in generated
        assert "dependency impact table" in generated
        assert "ca-###" in generated
```

- [ ] **Step 5: Add docs text**

Add this section to `README.md`, `docs/quickstart.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md`:

```markdown
## Senior Consequence Analysis Gate

Project cognition is necessary but not sufficient for dependency analysis. It gives workflow agents ownership, consumers, state surfaces, change-propagation facts, verification routes, conflicts, and known unknowns. The Senior Consequence Analysis Gate turns those facts into product and implementation obligations.

When work involves lifecycle operations, running or concurrent objects, destructive actions, shared state, downstream consumers, compatibility, security, or multiple plausible behaviors, workflows must preserve:

- Affected Object Map
- State-Behavior Matrix
- Dependency Impact Table
- Recovery And Validation Contract
- Coverage Gaps

For example, "close team" must consider running workers, queued tasks, late result submission, heartbeat state, `status`, `await`, `resume`, `cleanup`, idempotency, and validation evidence before the workflow can claim the feature is ready for the next stage.

Use `CA-###` IDs for consequence obligations that must survive handoff from `discussion` to `specify`, `plan`, `tasks`, `analyze`, and `implement`. `fast` upgrades when the gate triggers; `quick` may continue only when the consequence model is bounded; `debug` traces the dependency loop and rejects surface-only fixes.
```

- [ ] **Step 6: Update passive skill guidance**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, add:

```markdown
## Senior Consequence Analysis Relationship

Project cognition is necessary but not sufficient. Use it first to identify ownership, consumers, state surfaces, verification routes, and coverage gaps. Then run the Senior Consequence Analysis Gate when lifecycle, running-state, destructive-operation, shared-state, downstream consumer, compatibility, or multiple-behavior semantics matter.

The gate output must name affected objects, state behavior, dependency impact, recovery and validation, and coverage gaps. If project cognition cannot decide product semantics, record the gap and route to the appropriate workflow instead of treating the graph as authoritative.
```

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, add:

```markdown
## Consequence-Aware Routing

Route away from `fast` when a request triggers the Senior Consequence Analysis Gate. Use `quick` only for bounded consequence work with durable `STATUS.md` fields. Use `discussion` or `specify` when lifecycle semantics, running work, destructive policy, shared state, downstream consumers, or acceptance criteria need product decisions. Use `debug` when the issue is a failure with unknown root cause.
```

- [ ] **Step 7: Run docs and integration tests**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit docs and integration coverage**

```powershell
git add README.md docs/quickstart.md PROJECT-HANDBOOK.md templates/project-handbook-template.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py
git commit -m "docs: explain senior consequence analysis gate"
```

---

### Task 9: Full Verification And Regression Sweep

**Files:**
- Inspect all modified files.
- No planned source edits unless verification finds a regression.

- [ ] **Step 1: Run focused regression suite**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py tests/hooks/test_artifact_hooks.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py -q
```

Expected: PASS.

- [ ] **Step 2: Run integration rendering tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py -q
```

Expected: PASS.

- [ ] **Step 3: Run cross-surface search checks**

Run:

```powershell
rg -n "Senior Consequence Analysis Gate|CA-###|Affected Object Map|State-Behavior Matrix|Dependency Impact Table|Recovery And Validation Contract" templates README.md docs PROJECT-HANDBOOK.md tests src
```

Expected: Hits across command templates, artifact templates, docs, tests, and validation code.

Run:

```powershell
rg -n "sp-discussion|discussion|handoff-to-specify|plan-contract|task-index|task-packet|consequence" templates src scripts tests README.md PROJECT-HANDBOOK.md pyproject.toml
```

Expected: No newly discovered surface contradicts the gate. If a relevant command surface contains old wording that says handoff is Markdown-only, update it and add a focused assertion.

- [ ] **Step 4: Inspect git diff**

Run:

```powershell
git diff -- templates src tests README.md docs PROJECT-HANDBOOK.md
git status --short
```

Expected: Only intentional files from this plan are modified or committed. Unrelated preexisting dirty files remain untouched.

- [ ] **Step 5: Handle verification fixes**

If Step 1 or Step 2 fails, return to the task that owns the failing file, apply the fix there, rerun that task's focused test command, and use that task's exact commit command. If no fixes were needed, do not create an empty commit.

---

## Acceptance Checklist

- [ ] `sp-discussion` has Senior Maintainer Review and preserves `CA-###` obligations in Markdown, JSON, and selected candidate handoffs.
- [ ] `sp-specify` blocks planning readiness when triggered consequence semantics are unresolved.
- [ ] `sp-plan` records operational state machine, concurrency, idempotency, recovery, and validation decisions for `CA-###` obligations.
- [ ] `sp-tasks` maps `CA-###` obligations to tasks, packets, join points, validations, or explicit deferrals.
- [ ] `sp-fast` treats triggered consequence analysis as an upgrade trigger unless a stand-down reason is recorded.
- [ ] `sp-quick` records bounded consequence fields in `STATUS.md` or escalates.
- [ ] `sp-debug` traces affected objects, dependency loop, control state, observation state, adjacent risk targets, and rejects surface-only fixes.
- [ ] `sp-clarify`, `sp-deep-research`, `sp-analyze`, and `sp-implement` consume or preserve consequence obligations without dropping them.
- [ ] JSON artifact validators reject triggered gates with empty analysis, missing obligations, missing operational design, or unmapped task obligations.
- [ ] Worker packets and results carry consequence obligations and evidence when present.
- [ ] Docs explain that `sp-map-build` and project cognition are necessary but not sufficient for product semantics.
- [ ] Focused tests and integration rendering tests pass.
