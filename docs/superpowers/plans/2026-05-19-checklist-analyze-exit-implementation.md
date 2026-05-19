# Checklist Analyze Exit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the default generated Spec Kit Plus workflow `specify -> plan -> tasks -> implement` while preserving `sp-checklist` and `sp-analyze` as optional diagnostics and legacy compatibility routes.

**Architecture:** Update the contract tests first so the new mainline is protected before editing templates or runtime routing. Then update runtime state parsing, boundary validation, preflight, and lane reconcile so clean task-generation state with `next_command: /sp.implement` is executable without an existing analyze gate or implement tracker. Finally update generated workflow templates, passive skills, CLI/docs guidance, and integration projection tests so every surfaced recommendation matches the same state model.

**Tech Stack:** Python 3.11+, pytest, Typer CLI, Markdown command templates, YAML frontmatter, PowerShell/Bash generated command partials.

---

## Reference Spec

- `docs/superpowers/specs/2026-05-19-checklist-analyze-exit-design.md`

## File Structure

- `src/specify_cli/hooks/workflow_boundary.py`: allow the new `tasks -> implement` workflow and `task-generation-only -> execution-only` phase transition while keeping `tasks -> analyze` and `analysis-only -> execution-only` for legacy states.
- `src/specify_cli/hooks/checkpoint_serializers.py`: parse `Analyze Gate` fields from `workflow-state.md` so clean handoff values such as `gate_status: cleared` and `highest_invalid_stage: none` are machine-checkable.
- `src/specify_cli/hooks/state_validation.py`: change `sp-tasks` autofix defaults from `/sp.analyze` to `/sp.implement` and include the clean handoff state fields in repaired task-generation state.
- `src/specify_cli/hooks/preflight.py`: keep blocking any explicit non-implement `next_command`, but add coverage proving a clean completed `sp-tasks` state permits `/sp.implement`.
- `src/specify_cli/hooks/session_state.py`: keep existing implement tracker checks; tests should show completed `sp-tasks` plus active tracker is consistent when `next_command` is `/sp.implement`.
- `src/specify_cli/lanes/reconcile.py`: treat a completed `sp-tasks` lane with `/sp.implement` and a task package as an implement-launchable resume candidate even before `implement-tracker.md` exists.
- `src/specify_cli/lanes/resolution.py`: no structural rewrite expected; new tests protect that `sp-auto` infers `implement` from clean `/sp.implement` workflow-state and still preserves explicit legacy `/sp.analyze`.
- `src/specify_cli/__init__.py`: update workflow descriptions and user-facing workflow lists so `analyze` and `checklist` are support diagnostics, not default gates.
- `templates/commands/plan.md`: remove `sp-checklist` from default handoff and make plan completion prove task-readiness inputs before `/sp.tasks`.
- `templates/commands/tasks.md`: make `/sp.implement` the clean handoff, rename analyze-compatible self-audit to implementation-readiness self-audit, and keep analyze remediation only as an explicit legacy mode.
- `templates/command-partials/tasks/shell.md`: align shell guidance with direct implementation handoff after task readiness passes.
- `templates/tasks-template.md`: rename the generated self-audit section and change final handoff language from `sp-analyze` to `sp-implement`.
- `templates/commands/implement.md`: trust clean task handoff state and only mention `/sp.analyze` as an explicit legacy gate.
- `templates/command-partials/implement/shell.md`: update any remaining analyze-gate wording if grep finds it during the task.
- `templates/commands/checklist.md`: when checklist output is clean, recommend `/sp-tasks`, not `/sp-analyze`.
- `templates/commands/analyze.md`: reword from default pre-implementation gate to optional read-only diagnostic and legacy revalidation command; keep convergence and read-only behavior.
- `templates/commands/auto.md`: route clean completed task-generation state to `/sp.implement`; surface `/sp.analyze` only when recorded explicitly by legacy state.
- `templates/workflow-state-template.md`: document exact clean task-to-implement transition values.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: make `sp-analyze` and `sp-checklist` optional diagnostics and teach `sp-auto` clean tasks-to-implement routing.
- `README.md`, `docs/quickstart.md`, `PROJECT-HANDBOOK.md`, `templates/project-handbook-template.md`: update operator-facing workflow guidance to the new mainline and legacy diagnostic language.
- Tests under `tests/hooks/`, `tests/lanes/`, `tests/test_alignment_templates.py`, `tests/test_tasks_reporting_guidance.py`, `tests/test_specify_guidance_docs.py`, `tests/test_extension_skills.py`, `tests/test_passive_skill_guidance.py`, and integration projection tests.

## State Contract

Clean `sp-tasks -> sp-implement` handoff means `workflow-state.md` records all of these values:

```markdown
## Current Command

- active_command: `sp-tasks`
- status: `completed`

## Phase Mode

- phase_mode: `task-generation-only`
- summary: `task package ready for implementation`

## Fixed Lifecycle State

- current_stage: `task-generation`
- current_domain: `none`
- next_action: `hand off to implement`
- blocker_reason: `None`
- final_handoff_decision: `/sp.implement`

## Analyze Gate

- gate_status: `cleared`
- gate_cycle: `0`
- highest_invalid_stage: `none`
- blocker_bundle:
  - none
- blocker_attribution_values: `none`

## Reopen Contract

- reopen_source: `none`
- reopen_target: `none`
- reopen_reason: `none`

## Handoff Files

- handoff_to_implement: `handoff-to-implement.json`

## Next Command

- `/sp.implement`
```

Legacy compatibility means `next_command: /sp.analyze` remains readable and routable only when a persisted state file explicitly says so. New clean task-generation state must not infer or recommend analyze.

---

### Task 1: Lock Runtime Transition Tests

**Files:**
- Modify: `tests/hooks/test_workflow_boundary_hooks.py`
- Modify: `tests/hooks/test_phase_boundary_hooks.py`

- [ ] **Step 1: Add a failing workflow-boundary test for the new mainline**

Append this test to `tests/hooks/test_workflow_boundary_hooks.py` after `test_workflow_boundary_allows_mainline_transition`:

```python
def test_workflow_boundary_allows_tasks_to_implement_mainline(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "tasks", "to_command": "implement"},
    )

    assert result.status == "ok"
    assert result.data == {"from_command": "tasks", "to_command": "implement"}
```

Append this legacy-compatibility test after it:

```python
def test_workflow_boundary_keeps_tasks_to_analyze_legacy_route(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.boundary.validate",
        {"from_command": "tasks", "to_command": "analyze"},
    )

    assert result.status == "ok"
    assert result.data == {"from_command": "tasks", "to_command": "analyze"}
```

- [ ] **Step 2: Add a failing phase-boundary test for direct execution**

Append this test to `tests/hooks/test_phase_boundary_hooks.py` before the planning skip blocker test:

```python
def test_phase_boundary_allows_task_generation_to_execution(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": "task-generation-only", "to_phase_mode": "execution-only"},
    )

    assert result.status == "ok"
```

Keep `test_phase_boundary_allows_analysis_to_execution` unchanged so explicit legacy analyze states still work.

- [ ] **Step 3: Run the new tests and confirm the intended failures**

Run:

```powershell
uv run --extra test pytest tests/hooks/test_workflow_boundary_hooks.py tests/hooks/test_phase_boundary_hooks.py -q
```

Expected: fail on `tasks -> implement` and `task-generation-only -> execution-only` not being allowed. Existing `tasks -> analyze` and `analysis-only -> execution-only` should pass.

- [ ] **Step 4: Implement the allowed transition changes**

In `src/specify_cli/hooks/workflow_boundary.py`, update the transition sets exactly as follows:

```python
ALLOWED_WORKFLOW_TRANSITIONS = {
    ("specify", "plan"),
    ("specify", "clarify"),
    ("specify", "deep-research"),
    ("clarify", "plan"),
    ("clarify", "deep-research"),
    ("deep-research", "plan"),
    ("deep-research", "clarify"),
    ("plan", "tasks"),
    ("plan", "checklist"),
    ("tasks", "implement"),
    ("tasks", "analyze"),
    ("analyze", "implement"),
    ("implement", "debug"),
    ("quick", "debug"),
    ("fast", "quick"),
}

ALLOWED_PHASE_TRANSITIONS = {
    ("planning-only", "design-only"),
    ("planning-only", "research-only"),
    ("research-only", "design-only"),
    ("design-only", "task-generation-only"),
    ("task-generation-only", "execution-only"),
    ("task-generation-only", "analysis-only"),
    ("analysis-only", "execution-only"),
}
```

- [ ] **Step 5: Re-run transition tests**

Run:

```powershell
uv run --extra test pytest tests/hooks/test_workflow_boundary_hooks.py tests/hooks/test_phase_boundary_hooks.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit runtime transition tests and code**

Run:

```powershell
git add src/specify_cli/hooks/workflow_boundary.py tests/hooks/test_workflow_boundary_hooks.py tests/hooks/test_phase_boundary_hooks.py
git commit -m "feat: allow tasks to implement workflow transition"
```

Expected: commit succeeds.

---

### Task 2: Make Workflow-State Clean Handoff Machine-Readable

**Files:**
- Modify: `src/specify_cli/hooks/checkpoint_serializers.py`
- Modify: `src/specify_cli/hooks/state_validation.py`
- Modify: `tests/hooks/test_state_hooks.py`

- [ ] **Step 1: Add a failing serializer/state test for clean task handoff fields**

Append this test to `tests/hooks/test_state_hooks.py` after `test_validate_state_exposes_route_lock_and_reopen_fields`:

```python
def test_validate_state_exposes_clean_tasks_to_implement_handoff(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-tasks`",
                "- status: `completed`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `task-generation-only`",
                "- summary: `task package ready for implementation`",
                "",
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `task-generation`",
                "- current_domain: `none`",
                "- next_action: `hand off to implement`",
                "- blocker_reason: `None`",
                "- final_handoff_decision: `/sp.implement`",
                "",
                "## Analyze Gate",
                "",
                "- gate_status: `cleared`",
                "- gate_cycle: `0`",
                "- highest_invalid_stage: `none`",
                "- blocker_bundle:",
                "  - none",
                "- blocker_attribution_values: `none`",
                "",
                "## Reopen Contract",
                "",
                "- reopen_source: `none`",
                "- reopen_target: `none`",
                "- reopen_reason: `none`",
                "",
                "## Handoff Files",
                "",
                "- handoff_to_implement: `handoff-to-implement.json`",
                "",
                "## Allowed Artifact Writes",
                "",
                "- tasks.md",
                "- handoff-to-implement.json",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- tasks.md",
                "- task-index.json",
                "",
                "## Next Command",
                "",
                "- `/sp.implement`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.state.validate",
        {"command_name": "tasks", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    checkpoint = result.data["checkpoint"]
    assert checkpoint["active_command"] == "sp-tasks"
    assert checkpoint["status"] == "completed"
    assert checkpoint["phase_mode"] == "task-generation-only"
    assert checkpoint["current_stage"] == "task-generation"
    assert checkpoint["current_domain"] == "none"
    assert checkpoint["next_action"] == "hand off to implement"
    assert checkpoint["blocker_reason"] == "None"
    assert checkpoint["final_handoff_decision"] == "/sp.implement"
    assert checkpoint["handoff_to_implement"] == "handoff-to-implement.json"
    assert checkpoint["next_command"] == "/sp.implement"
    assert checkpoint["gate_status"] == "cleared"
    assert checkpoint["gate_cycle"] == "0"
    assert checkpoint["highest_invalid_stage"] == "none"
    assert checkpoint["blocker_attribution_values"] == "none"
    assert checkpoint["reopen_source"] == "none"
    assert checkpoint["reopen_target"] == "none"
    assert checkpoint["reopen_reason"] == "none"
```

Expected initial failure: `gate_status`, `gate_cycle`, `highest_invalid_stage`, and `blocker_attribution_values` are missing from the serialized checkpoint.

- [ ] **Step 2: Update the tasks autofix test to expect `/sp.implement`**

In `tests/hooks/test_state_hooks.py`, inside `test_validate_state_autofix_tasks_includes_task_generation_surfaces`, add this assertion after the existing task-generation surface assertions:

```python
    assert "- `/sp.implement`" in content
    assert "- `/sp.analyze`" not in content
```

The existing fixture may still start with `/sp.analyze` to simulate stale state; the autofix snippet must append the new clean default.

- [ ] **Step 3: Run state tests and confirm intended failures**

Run:

```powershell
uv run --extra test pytest tests/hooks/test_state_hooks.py::test_validate_state_exposes_clean_tasks_to_implement_handoff tests/hooks/test_state_hooks.py::test_validate_state_autofix_tasks_includes_task_generation_surfaces -q
```

Expected: fail because `Analyze Gate` fields are not serialized and task autofix still appends `/sp.analyze`.

- [ ] **Step 4: Parse Analyze Gate fields**

In `src/specify_cli/hooks/checkpoint_serializers.py`, in `serialize_workflow_state()`, add the section body near the existing section variables:

```python
    analyze_gate = section_body(text, "Analyze Gate")
```

In the returned dictionary, add these keys near the lifecycle and reopen fields:

```python
        "gate_status": extract_field(analyze_gate, "gate_status"),
        "gate_cycle": extract_field(analyze_gate, "gate_cycle"),
        "highest_invalid_stage": extract_field(analyze_gate, "highest_invalid_stage"),
        "blocker_attribution_values": extract_field(analyze_gate, "blocker_attribution_values"),
```

Do not parse `blocker_bundle` as a structured list in this task; no runtime consumer needs it for the clean handoff decision.

- [ ] **Step 5: Change task-generation autofix to `/sp.implement`**

In `src/specify_cli/hooks/state_validation.py`, in `_autofix_sections_for_command()` under the `"tasks"` config, change:

```python
            "next_command": "/sp.analyze",
```

to:

```python
            "next_command": "/sp.implement",
```

Leave the `"analyze"` config as `"next_command": "/sp.implement"` for explicit legacy analyze runs.

- [ ] **Step 6: Extend the tasks autofix snippet with clean handoff fields**

Still in `src/specify_cli/hooks/state_validation.py`, change `_autofix_sections_for_command()` so task autofix appends the clean state sections before `Allowed Artifact Writes`.

Add this helper block just before the `return (` line:

```python
    clean_tasks_handoff = ""
    if command_name == "tasks":
        clean_tasks_handoff = (
            "## Fixed Lifecycle State\n\n"
            "- current_stage: `task-generation`\n"
            "- current_domain: `none`\n"
            "- next_action: `hand off to implement`\n"
            "- blocker_reason: `None`\n"
            "- final_handoff_decision: `/sp.implement`\n\n"
            "## Analyze Gate\n\n"
            "- gate_status: `cleared`\n"
            "- gate_cycle: `0`\n"
            "- highest_invalid_stage: `none`\n"
            "- blocker_bundle:\n"
            "  - none\n"
            "- blocker_attribution_values: `none`\n\n"
            "## Reopen Contract\n\n"
            "- reopen_source: `none`\n"
            "- reopen_target: `none`\n"
            "- reopen_reason: `none`\n\n"
            "## Handoff Files\n\n"
            "- handoff_to_implement: `handoff-to-implement.json`\n\n"
        )
```

Then insert `f"{clean_tasks_handoff}"` at the start of the returned snippet:

```python
    return (
        f"{clean_tasks_handoff}"
        "## Allowed Artifact Writes\n\n"
        f"{allowed}\n\n"
        ...
    )
```

This keeps autofix conservative for every other command.

- [ ] **Step 7: Re-run state tests**

Run:

```powershell
uv run --extra test pytest tests/hooks/test_state_hooks.py::test_validate_state_exposes_clean_tasks_to_implement_handoff tests/hooks/test_state_hooks.py::test_validate_state_autofix_tasks_includes_task_generation_surfaces -q
```

Expected: both tests pass.

- [ ] **Step 8: Commit workflow-state parsing and defaults**

Run:

```powershell
git add src/specify_cli/hooks/checkpoint_serializers.py src/specify_cli/hooks/state_validation.py tests/hooks/test_state_hooks.py
git commit -m "feat: record clean tasks implement handoff state"
```

Expected: commit succeeds.

---

### Task 3: Route Clean Tasks State Through Implement and Auto

**Files:**
- Modify: `src/specify_cli/lanes/reconcile.py`
- Modify: `tests/lanes/test_reconcile.py`
- Modify: `tests/lanes/test_resolution.py`

- [ ] **Step 1: Generalize the workflow-state test helper in lane tests**

In both `tests/lanes/test_reconcile.py` and `tests/lanes/test_resolution.py`, replace `_write_workflow_state(feature_dir: Path, next_command: str)` with this implementation:

```python
def _write_workflow_state(
    feature_dir: Path,
    next_command: str,
    *,
    active_command: str = "sp-analyze",
    status: str = "completed",
    phase_mode: str = "analysis-only",
    next_action: str = "continue",
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                f"- active_command: `{active_command}`",
                f"- status: `{status}`",
                "",
                "## Phase Mode",
                "",
                f"- phase_mode: `{phase_mode}`",
                "- summary: demo",
                "",
                "## Fixed Lifecycle State",
                "",
                "- current_stage: `task-generation`",
                "- current_domain: `none`",
                f"- next_action: `{next_action}`",
                "- blocker_reason: `None`",
                f"- final_handoff_decision: `{next_command}`",
                "",
                "## Analyze Gate",
                "",
                "- gate_status: `cleared`",
                "- gate_cycle: `0`",
                "- highest_invalid_stage: `none`",
                "- blocker_bundle:",
                "  - none",
                "- blocker_attribution_values: `none`",
                "",
                "## Reopen Contract",
                "",
                "- reopen_source: `none`",
                "- reopen_target: `none`",
                "- reopen_reason: `none`",
                "",
                "## Handoff Files",
                "",
                "- handoff_to_implement: `handoff-to-implement.json`",
                "",
                "## Next Command",
                "",
                f"- `{next_command}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
```

Existing tests that do not pass keyword arguments keep their legacy `sp-analyze` completed state.

- [ ] **Step 2: Add a task package helper**

Add this helper to both lane test files below `_write_implement_tracker()`:

```python
def _write_task_package(feature_dir: Path) -> None:
    (feature_dir / "tasks.md").write_text("# Tasks\n\n- [ ] T001 Demo task\n", encoding="utf-8")
    (feature_dir / "task-index.json").write_text('{"tasks": [{"id": "T001"}]}\n', encoding="utf-8")
    (feature_dir / "handoff-to-implement.json").write_text('{"status": "ready"}\n', encoding="utf-8")
```

- [ ] **Step 3: Add failing reconcile coverage for launchable implement without tracker**

Append this test to `tests/lanes/test_reconcile.py` after `test_reconcile_marks_consistent_implement_lane_resumable`:

```python
def test_reconcile_marks_clean_tasks_handoff_launchable_for_implement_without_tracker(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        "/sp.implement",
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_action="hand off to implement",
    )
    _write_task_package(feature_dir)
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="tasked",
        last_command="tasks",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "resumable"
    assert reconciled.last_stable_checkpoint == "handoff-to-implement"
    assert reconciled.recovery_reason == ""
```

Append this negative test after it:

```python
def test_reconcile_blocks_clean_tasks_handoff_without_task_package(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        "/sp.implement",
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_action="hand off to implement",
    )
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="tasked",
        last_command="tasks",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "blocked"
    assert reconciled.recovery_reason == "missing implement launch artifacts"
```

- [ ] **Step 4: Add failing auto-routing coverage for clean and legacy states**

Append this test to `tests/lanes/test_resolution.py` after `test_resolve_lane_auto_inferrs_implement_from_tracker_and_workflow_state`:

```python
def test_resolve_lane_auto_routes_clean_tasks_handoff_to_implement_without_tracker(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        "/sp.implement",
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_action="hand off to implement",
    )
    _write_task_package(feature_dir)
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="tasked",
        recovery_state="resumable",
        last_command="tasks",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}]})

    result = resolve_lane_for_command(tmp_path, command_name="auto")

    assert result.mode == "resume"
    assert result.selected_lane_id == "lane-001"
    assert result.candidates[0].last_command == "implement"
    assert result.candidates[0].last_stable_checkpoint == "handoff-to-implement"
```

Append this legacy route test after it:

```python
def test_resolve_lane_auto_preserves_explicit_legacy_analyze_state(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        "/sp.analyze",
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_action="run legacy analyze gate",
    )
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="tasked",
        recovery_state="resumable",
        last_command="tasks",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}]})

    result = resolve_lane_for_command(tmp_path, command_name="auto")

    assert result.mode == "resume"
    assert result.selected_lane_id == "lane-001"
    assert result.candidates[0].last_command == "analyze"
```

- [ ] **Step 5: Run lane tests and confirm intended failure**

Run:

```powershell
uv run --extra test pytest tests/lanes/test_reconcile.py tests/lanes/test_resolution.py -q
```

Expected: clean tasks handoff tests fail because `reconcile_lane(..., command_name="implement")` currently requires `implement-tracker.md`.

- [ ] **Step 6: Implement launchable clean tasks handoff in reconcile**

In `src/specify_cli/lanes/reconcile.py`, replace the first implement branch guard:

```python
    if command_name == "implement":
        if not workflow_path.exists() or not tracker_path.exists():
            updated.recovery_state = "blocked"
            updated.recovery_reason = "missing implement stage artifacts"
            _persist_recovery_summary(project_root, updated, command_name=command_name)
            return updated

        workflow = serialize_workflow_state(workflow_path)
        tracker = serialize_implement_tracker(tracker_path)
```

with:

```python
    if command_name == "implement":
        if not workflow_path.exists():
            updated.recovery_state = "blocked"
            updated.recovery_reason = "missing workflow-state.md"
            _persist_recovery_summary(project_root, updated, command_name=command_name)
            return updated

        workflow = serialize_workflow_state(workflow_path)
        next_command = str(workflow.get("next_command") or "")

        if not tracker_path.exists():
            task_package_exists = (
                (feature_dir / "tasks.md").exists()
                and (
                    (feature_dir / "handoff-to-implement.json").exists()
                    or (feature_dir / "task-index.json").exists()
                )
            )
            clean_tasks_handoff = (
                next_command == "/sp.implement"
                and str(workflow.get("active_command") or "") == "sp-tasks"
                and str(workflow.get("status") or "") == "completed"
                and str(workflow.get("phase_mode") or "") == "task-generation-only"
            )
            if clean_tasks_handoff and task_package_exists:
                updated.recovery_state = "resumable"
                updated.last_stable_checkpoint = "handoff-to-implement"
                updated.recovery_reason = ""
                _persist_recovery_summary(project_root, updated, command_name=command_name)
                return updated
            updated.recovery_state = "blocked"
            updated.recovery_reason = "missing implement launch artifacts"
            _persist_recovery_summary(project_root, updated, command_name=command_name)
            return updated

        tracker = serialize_implement_tracker(tracker_path)
```

Then remove the later duplicate line:

```python
        next_command = str(workflow.get("next_command") or "")
```

Keep the conflict check and lease handling unchanged.

- [ ] **Step 7: Re-run lane tests**

Run:

```powershell
uv run --extra test pytest tests/lanes/test_reconcile.py tests/lanes/test_resolution.py -q
```

Expected: all lane tests pass, including explicit legacy `/sp.analyze` route.

- [ ] **Step 8: Commit lane routing**

Run:

```powershell
git add src/specify_cli/lanes/reconcile.py tests/lanes/test_reconcile.py tests/lanes/test_resolution.py
git commit -m "feat: route clean tasks handoff through implement"
```

Expected: commit succeeds.

---

### Task 4: Update Implement Preflight and Session-State Coverage

**Files:**
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/hooks/test_session_state_hooks.py`
- Modify: `src/specify_cli/hooks/preflight.py` only if the new test exposes a real blocker

- [ ] **Step 1: Add clean implement preflight coverage**

In `tests/hooks/test_preflight_hooks.py`, rename `test_preflight_blocks_implement_when_workflow_state_requires_analyze` to:

```python
def test_preflight_blocks_implement_when_workflow_state_explicitly_requires_legacy_analyze(tmp_path: Path):
```

Keep the fixture with `next_command="/sp.analyze"` and the existing assertions. This preserves compatibility safety.

Append this test after it:

```python
def test_preflight_allows_implement_when_tasks_state_hands_off_to_implement(tmp_path: Path):
    project = _create_project(tmp_path)
    _write_cognition_baseline(project)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
        next_command="/sp.implement",
    )

    result = run_quality_hook(
        project,
        "workflow.preflight",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.errors == []
```

The cognition baseline is required because preflight still evaluates project cognition for implement.

- [ ] **Step 2: Make session-state helper support clean task state**

In `tests/hooks/test_session_state_hooks.py`, replace `_write_workflow_state(feature_dir: Path, next_command: str)` with:

```python
def _write_workflow_state(
    feature_dir: Path,
    next_command: str,
    *,
    active_command: str = "sp-analyze",
    status: str = "completed",
    phase_mode: str = "analysis-only",
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                f"- active_command: `{active_command}`",
                f"- status: `{status}`",
                "",
                "## Phase Mode",
                "",
                f"- phase_mode: `{phase_mode}`",
                "- summary: demo",
                "",
                "## Next Action",
                "",
                "- continue",
                "",
                "## Next Command",
                "",
                f"- `{next_command}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
```

- [ ] **Step 3: Add session-state coverage for completed tasks plus implement tracker**

Append this test after `test_session_state_accepts_consistent_implement_resume_state`:

```python
def test_session_state_accepts_clean_tasks_handoff_with_active_implement_tracker(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(
        feature_dir,
        "/sp.implement",
        active_command="sp-tasks",
        status="completed",
        phase_mode="task-generation-only",
    )
    _write_implement_tracker(feature_dir)

    result = run_quality_hook(
        project,
        "workflow.session_state.validate",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"
    assert result.data["state_summary"]["next_command"] == "/sp.implement"
    assert result.data["state_summary"]["workflow_status"] == "completed"
    assert result.data["state_summary"]["tracker_status"] == "executing"
```

- [ ] **Step 4: Run preflight and session-state tests**

Run:

```powershell
uv run --extra test pytest tests/hooks/test_preflight_hooks.py::test_preflight_blocks_implement_when_workflow_state_explicitly_requires_legacy_analyze tests/hooks/test_preflight_hooks.py::test_preflight_allows_implement_when_tasks_state_hands_off_to_implement tests/hooks/test_session_state_hooks.py -q
```

Expected: pass if preflight already accepts `/sp.implement`. If the clean preflight test fails only because of cognition fixture changes, fix the fixture. If it fails because `preflight.py` treats `sp-tasks` active command as blocked despite `/sp.implement`, remove that condition; keep the explicit `next_command != "/sp.implement"` blocker.

- [ ] **Step 5: Commit preflight/session coverage**

Run:

```powershell
git add tests/hooks/test_preflight_hooks.py tests/hooks/test_session_state_hooks.py src/specify_cli/hooks/preflight.py
git commit -m "test: cover clean tasks implement preflight"
```

Expected: commit succeeds. If `src/specify_cli/hooks/preflight.py` was unchanged, omit it from `git add`.

---

### Task 5: Change Template Contract Tests for the New Default Path

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_tasks_reporting_guidance.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Update owned handoff token assertions**

In `tests/test_alignment_templates.py`, update `test_task3_owned_handoffs_keep_canonical_tokens_without_invocation_placeholders()` so the expected mapping for plan/tasks is:

```python
    expected_tokens = {
        "templates/commands/plan.md": ["/sp.tasks"],
        "templates/commands/tasks.md": ["/sp.implement"],
        "templates/commands/analyze.md": ["/sp.implement"],
        "templates/commands/implement.md": ["/sp.implement"],
    }
```

If the local test uses a differently named dictionary, preserve the surrounding structure and only change the expected tokens. Do not require `/sp.checklist` in `plan.md` and do not require `/sp.analyze` in `tasks.md`.

- [ ] **Step 2: Replace old tasks-to-analyze contract test**

In `tests/test_alignment_templates.py`, replace `test_tasks_template_fail_closes_into_analyze_before_implement()` with:

```python
def test_tasks_template_clean_completion_hands_off_to_implement():
    content = Path("templates/commands/tasks.md").read_text(encoding="utf-8")

    assert "default_handoff: '/sp.implement for clean task generation" in content
    assert "`next_command: /sp.implement`" in content
    assert "`gate_status: cleared`" in content
    assert "`highest_invalid_stage: none`" in content
    assert "Do not create a clean implement handoff unless all task-readiness gates pass" in content
    assert "Legacy Analyze Remediation Mapping" in content
```

- [ ] **Step 3: Replace analyze-compatible self-audit assertions**

In `tests/test_alignment_templates.py`, replace `test_tasks_template_requires_analyze_compatible_self_audit_and_remediation_mode()` with:

```python
def test_tasks_template_requires_implementation_readiness_self_audit_and_legacy_remediation_mode():
    content = Path("templates/commands/tasks.md").read_text(encoding="utf-8")

    assert "Implementation-Readiness Task Self-Audit" in content
    assert "Before finalizing `tasks.md` for `/sp.implement`" in content
    assert "Legacy Analyze Remediation Mapping" in content
    assert "Use this only when an existing `workflow-state.md` explicitly points to `/sp.analyze`" in content
    assert "Task packet readiness covers `DP1`, `DP2`, and `DP3`" in content
    assert "repeated legacy `tasks -> analyze -> tasks` loops are abnormal" in content
```

- [ ] **Step 4: Replace implement analyze-gate test**

In `tests/test_alignment_templates.py`, replace `test_implement_template_honors_pending_analyze_gate_from_workflow_state()` with:

```python
def test_implement_template_trusts_clean_tasks_handoff_and_respects_legacy_analyze_state():
    content = Path("templates/commands/implement.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "clean completed `sp-tasks` state with `next_command: /sp.implement` authorizes implementation entry" in lowered
    assert "legacy `/sp.analyze` state" in lowered
    assert "only stop for `/sp.analyze` when `workflow_state_file` explicitly records it" in lowered
    assert "stop and run `/sp-analyze` first" not in lowered
```

- [ ] **Step 5: Update auto route template test**

In `tests/test_alignment_templates.py`, adjust `test_auto_template_routes_from_existing_state_surfaces()` so it asserts:

```python
    assert "Clean completed task-generation state routes to `/sp.implement`" in content
    assert "`/sp.analyze` is a legacy or explicitly requested diagnostic route only" in content
    assert "must not infer `/sp.analyze` for a clean task package" in content
```

Keep any existing assertions that `/sp.analyze` remains a known canonical token only if the test labels it as explicit legacy state.

- [ ] **Step 6: Update workflow-state template test**

In `tests/test_alignment_templates.py`, extend `test_workflow_state_template_supports_analyze_gate_phase()` with:

```python
    assert "## Clean Task-To-Implement Handoff" in content
    assert "active_command: sp-tasks" in content
    assert "next_command: /sp.implement" in content
    assert "gate_status: cleared" in content
    assert "highest_invalid_stage: none" in content
```

- [ ] **Step 7: Update checklist clean recommendation test**

In `tests/test_alignment_templates.py`, inside `test_checklist_template_prefers_native_question_tools_with_textual_fallback`, change:

```python
    assert "recommend `/sp-analyze`" in lowered
```

to:

```python
    assert "recommend `/sp-tasks`" in lowered
    assert "recommend `/sp-analyze`" not in lowered
```

- [ ] **Step 8: Update tasks reporting guidance test**

In `tests/test_tasks_reporting_guidance.py`, replace `test_tasks_template_includes_analyze_remediation_mapping_and_self_audit()` with:

```python
def test_tasks_template_includes_implementation_readiness_self_audit_and_legacy_remediation_mapping():
    content = Path("templates/tasks-template.md").read_text(encoding="utf-8")

    assert "## Legacy Analyze Remediation Mapping" in content
    assert "Use this section only when regenerating tasks after an explicit legacy `sp-analyze` blocker" in content
    assert "## Implementation-Readiness Task Self-Audit" in content
    assert "Before final handoff to `sp-implement`, confirm:" in content
    assert "`DP1`, `DP2`, and `DP3`" in content
```

- [ ] **Step 9: Update generated extension skill tests**

In `tests/test_extension_skills.py`, change the tasks skill assertions near the existing boundary guardrail test:

```python
        assert "clean task generation hands off to `/sp-implement`" in tasks_body.lower()
        assert "implementation-readiness task self-audit" in tasks_body.lower()
        assert "implementation remains blocked until `/sp-analyze`" not in tasks_body.lower()
```

Change the implement skill assertion:

```python
        assert "only stop for `/sp.analyze` when `workflow_state_file` explicitly records it" in implement_body.lower()
```

Change the checklist assertion:

```python
        assert "recommend `/sp-tasks`" in checklist_lower
        assert "recommend `/sp-analyze`" not in checklist_lower
```

Leave assertions that `sp-analyze` exists as a generated command unless they call it the default gate.

- [ ] **Step 10: Add passive routing guidance coverage**

If `tests/test_passive_skill_guidance.py` already has a workflow-routing test, extend it with:

```python
    routing = Path("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").read_text(encoding="utf-8")
    assert "default generated path is `sp-specify -> sp-plan -> sp-tasks -> sp-implement`" in routing
    assert "Use `sp-analyze` only for optional diagnostics, explicit user requests, or persisted legacy `/sp.analyze` state." in routing
    assert "Clean completed `sp-tasks` state with `/sp.implement` should route through `sp-auto` to `sp-implement`." in routing
```

If there is no existing test, add:

```python
from pathlib import Path


def test_workflow_routing_skill_teaches_direct_tasks_to_implement_default_path() -> None:
    routing = Path("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").read_text(encoding="utf-8")

    assert "default generated path is `sp-specify -> sp-plan -> sp-tasks -> sp-implement`" in routing
    assert "Use `sp-analyze` only for optional diagnostics, explicit user requests, or persisted legacy `/sp.analyze` state." in routing
    assert "Clean completed `sp-tasks` state with `/sp.implement` should route through `sp-auto` to `sp-implement`." in routing
```

- [ ] **Step 11: Update docs guidance tests**

In `tests/test_specify_guidance_docs.py`, replace assertions that say analyze is required/default with these expectations:

```python
    assert "the normal generated delivery path is `specify -> plan -> tasks -> implement`" in content
    assert "`analyze` is an optional diagnostic and legacy revalidation route" in content
    assert "`checklist` is an optional requirements-quality aid" in content
```

Replace `test_guidance_docs_explain_analyze_tasks_convergence_contract()` with:

```python
def test_guidance_docs_explain_tasks_to_implement_default_and_legacy_analyze_contract() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    quickstart = Path("docs/quickstart.md").read_text(encoding="utf-8")
    handbook = Path("PROJECT-HANDBOOK.md").read_text(encoding="utf-8")

    for content in (readme, quickstart, handbook):
        assert "specify -> plan -> tasks -> implement" in content
        assert "optional diagnostic and legacy revalidation" in content
        assert "clean `tasks` completion writes `next_command: /sp.implement`" in content
        assert "tasks -> analyze -> implement" not in content
        assert "required gate before implementation" not in content
```

- [ ] **Step 12: Run focused template/doc tests and confirm failures**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py::test_task3_owned_handoffs_keep_canonical_tokens_without_invocation_placeholders tests/test_alignment_templates.py::test_tasks_template_clean_completion_hands_off_to_implement tests/test_alignment_templates.py::test_tasks_template_requires_implementation_readiness_self_audit_and_legacy_remediation_mode tests/test_alignment_templates.py::test_implement_template_trusts_clean_tasks_handoff_and_respects_legacy_analyze_state tests/test_tasks_reporting_guidance.py tests/test_extension_skills.py tests/test_passive_skill_guidance.py tests/test_specify_guidance_docs.py -q
```

Expected: fail because templates and docs still teach checklist/analyze as default path.

- [ ] **Step 13: Commit the failing contract tests**

Run:

```powershell
git add tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py tests/test_extension_skills.py tests/test_passive_skill_guidance.py tests/test_specify_guidance_docs.py
git commit -m "test: lock direct tasks implement workflow guidance"
```

Expected: commit succeeds even though the focused suite is red, because this is the RED commit for the template change. If repository policy rejects red commits in this environment, skip this commit and commit tests with implementation in Task 7.

---

### Task 6: Update Workflow Templates

**Files:**
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/command-partials/tasks/shell.md`
- Modify: `templates/tasks-template.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/command-partials/implement/shell.md` if grep finds analyze-gate wording
- Modify: `templates/commands/checklist.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/auto.md`
- Modify: `templates/workflow-state-template.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`

- [ ] **Step 1: Update `sp-plan` frontmatter and completion handoff**

In `templates/commands/plan.md`, change frontmatter:

```yaml
  default_handoff: '/sp.tasks for decomposition, optionally /sp.checklist for quality checks on the resulting plan package.'
```

to:

```yaml
  default_handoff: '/sp.tasks for decomposition once the planning package passes its built-in readiness checks.'
```

If the `handoffs:` frontmatter contains a checklist item, remove that checklist item from frontmatter. Do not remove prose that says checklist is available as an optional manual diagnostic; only remove it from default handoff routing.

Add this bullet near the plan final validation/checkpoint section:

```markdown
- Before handing off to `{{invoke:tasks}}`, prove plan readiness inside this workflow: locked decisions, must-preserve items, validation strategy, risk handling, dispatch compilation hints, and any required `Implementation Constitution` are present or explicitly not applicable. Do not use `{{invoke:checklist}}` as the normal next-step quality net.
```

- [ ] **Step 2: Update `sp-tasks` frontmatter**

In `templates/commands/tasks.md`, set the frontmatter default handoff to:

```yaml
  default_handoff: '/sp.implement for clean task generation; /sp.plan, /sp.clarify, or /sp.deep-research when task-readiness checks expose missing upstream truth; /sp.analyze only for explicit legacy diagnostic revalidation.'
```

Update the frontmatter `handoffs:` block so the normal handoff is implement:

```yaml
  handoffs:
    - label: Implement Project
      agent: sp.implement
      prompt: Execute the ready implementation task package
      send: false
```

If the template also has non-frontmatter handoff examples, keep `sp-analyze` only in a legacy diagnostic paragraph.

- [ ] **Step 3: Replace tasks phase-lock wording**

In `templates/commands/tasks.md`, replace the workflow phase lock language that says implementation remains blocked until analyze with:

```markdown
- Implementation may begin only after task-readiness passes and `WORKFLOW_STATE_FILE` records `next_command: /sp.implement`.
- Do not create a clean implement handoff unless all task-readiness gates pass. If coverage, locked-decision preservation, guardrail mapping, packet readiness, dependency ordering, or write-set isolation is not proven, reopen the owning upstream stage instead of handing off to implementation.
- Use legacy analyze remediation mode only when an existing `WORKFLOW_STATE_FILE` explicitly points to `/sp.analyze` or the user explicitly invokes `{{invoke:analyze}}` for diagnostic revalidation.
```

Add the exact clean state field list:

```markdown
Clean task completion MUST write these state values before final response:

- `active_command: sp-tasks`
- `status: completed`
- `phase_mode: task-generation-only`
- `current_stage: task-generation`
- `current_domain: none`
- `next_action: hand off to implement`
- `blocker_reason: None`
- `final_handoff_decision: /sp.implement`
- `handoff_to_implement: handoff-to-implement.json`
- `next_command: /sp.implement`
- `gate_status: cleared`
- `highest_invalid_stage: none`
- `reopen_source: none`
- `reopen_target: none`
- `reopen_reason: none`
```

- [ ] **Step 4: Rename the tasks self-audit section**

In `templates/commands/tasks.md`, replace:

```markdown
- **Analyze-Compatible Task Self-Audit**: Before finalizing `tasks.md`, run the task-layer subset of the `sp-analyze` checks against the generated task package.
```

with:

```markdown
- **Implementation-Readiness Task Self-Audit**: Before finalizing `tasks.md` for `/sp.implement`, run the task-layer readiness checks that used to be deferred to the default analyze gate.
```

Change the report section label from:

```markdown
- Analyze-Compatible Task Self-Audit result:
```

to:

```markdown
- Implementation-Readiness Task Self-Audit result:
```

Change the persistence bullet:

```markdown
- `next_command: /sp.analyze` only for normal completed or non-escalated task generation
```

to:

```markdown
- `next_command: /sp.implement` only for clean completed task generation
```

Keep an adjacent legacy bullet:

```markdown
- `next_command: /sp.analyze` only when preserving an explicit legacy analyze state or user-requested diagnostic route; never infer it for a clean task package.
```

- [ ] **Step 5: Update task partial wording**

In `templates/command-partials/tasks/shell.md`, replace:

```markdown
Validate resulting task graph before handing off to analysis or implementation.
```

with:

```markdown
Validate the resulting task graph before handing off to implementation; use analysis only for explicit legacy or diagnostic revalidation.
```

- [ ] **Step 6: Update generated tasks template**

In `templates/tasks-template.md`, change:

```markdown
## Analyze Remediation Mapping

Use this section only when regenerating tasks after a blocked `sp-analyze` gate. Leave it as `No prior analyze blockers for this task package.` for first-pass task generation.
```

to:

```markdown
## Legacy Analyze Remediation Mapping

Use this section only when regenerating tasks after an explicit legacy `sp-analyze` blocker or user-requested diagnostic revalidation. Leave it as `No prior analyze blockers for this task package.` for first-pass task generation.
```

Change:

```markdown
## Analyze-Compatible Task Self-Audit

Before final handoff to `sp-analyze`, confirm:
```

to:

```markdown
## Implementation-Readiness Task Self-Audit

Before final handoff to `sp-implement`, confirm:
```

- [ ] **Step 7: Update implement template entry rules**

In `templates/commands/implement.md`, replace pre-execution wording that says:

```markdown
Confirm project cognition freshness, analyze-gate status, and valid execution entry
```

with:

```markdown
Confirm project cognition freshness, workflow-state `next_command`, task-readiness status, and valid execution entry; legacy analyze gates apply only when explicitly recorded.
```

Add this paragraph near workflow-state validation:

```markdown
A clean completed `sp-tasks` state with `next_command: /sp.implement` authorizes implementation entry when the task package and handoff files are present. Only stop for `/sp.analyze` when `workflow_state_file` explicitly records a legacy `/sp.analyze` state; in that case, preserve the legacy gate and ask the user to run `{{invoke:analyze}}` before implementation continues.
```

Remove any sentence that says:

```markdown
stop and run `/sp-analyze` first
```

or that makes analyze the normal pre-implementation gate.

- [ ] **Step 8: Update checklist clean recommendation**

In `templates/commands/checklist.md`, replace:

```markdown
- If the checklist is materially satisfied and execution preparation should continue through cross-artifact validation, recommend `/sp-analyze`.
```

with:

```markdown
- If the checklist is materially satisfied and execution preparation should continue, recommend `/sp-tasks` so task generation performs the built-in implementation-readiness gate.
```

- [ ] **Step 9: Reword analyze as optional diagnostic**

In `templates/commands/analyze.md`, change frontmatter description and `when_to_use` from default pre-implementation wording to:

```yaml
description: Use when tasks.md exists and you need an optional read-only cross-artifact diagnostic, legacy analyze-gate revalidation, or execution drift investigation.
workflow_contract:
  when_to_use: '`tasks.md` is available and the user explicitly requests analysis, existing workflow-state records `/sp.analyze`, or implementation drift requires read-only revalidation.'
```

In `## Goal`, change the first paragraph to:

```markdown
Identify inconsistencies, duplications, ambiguities, and underspecified items across the core planning artifacts (`spec.md`, `context.md`, `plan.md`, `tasks.md`) when optional diagnostic revalidation is requested, when a legacy workflow state explicitly routes here, or when execution drift needs read-only analysis. This command MUST run only after the canonical `/sp.tasks` workflow has successfully produced a complete `tasks.md`; it is no longer the default pre-implementation gate for clean task packages.
```

Change the re-entry chain bullets near the end:

```markdown
- If the highest invalid stage is `clarify`, the re-entry chain MUST be `{{invoke:clarify}} -> {{invoke:plan}} -> {{invoke:tasks}} -> {{invoke:implement}}`; run `{{invoke:analyze}}` again only if the user requested diagnostic revalidation or the legacy state still records `/sp.analyze`.
- If the highest invalid stage is `deep-research`, the re-entry chain MUST be `{{invoke:deep-research}} -> {{invoke:plan}} -> {{invoke:tasks}} -> {{invoke:implement}}`; run `{{invoke:analyze}}` again only if the user requested diagnostic revalidation or the legacy state still records `/sp.analyze`.
- If the highest invalid stage is `plan`, the re-entry chain MUST be `{{invoke:plan}} -> {{invoke:tasks}} -> {{invoke:implement}}`; run `{{invoke:analyze}}` again only if the user requested diagnostic revalidation or the legacy state still records `/sp.analyze`.
- If the highest invalid stage is `tasks`, the re-entry chain MUST be `{{invoke:tasks}} -> {{invoke:implement}}`; run `{{invoke:analyze}}` again only if the user requested diagnostic revalidation or the legacy state still records `/sp.analyze`.
```

Keep the read-only planning artifact constraints and complete blocker bundle behavior.

- [ ] **Step 10: Update auto template routing**

In `templates/commands/auto.md`, update the guardrail bullet that lists preserved downstream commands so it still includes `/sp.analyze` but labels it legacy:

```markdown
- Do not rewrite the underlying workflow state to `/sp.auto`; preserve the canonical downstream `next_command` such as `/sp.plan`, `/sp.tasks`, `/sp.implement`, `/sp.debug`, `/sp.quick`, `/sp.fast`, `/sp.clarify`, or `/sp.deep-research`. Preserve `/sp.analyze` only when an existing state file explicitly records that legacy or diagnostic route.
```

In `Authoritative State Surfaces`, change the canonical state token bullet to:

```markdown
- Treat `FEATURE_DIR/workflow-state.md` as the primary phase-lock and `next_command` source for feature workflows. Canonical state tokens include `/sp.plan`, `/sp.tasks`, `/sp.implement`, `/sp.clarify`, and `/sp.deep-research`; `/sp.analyze` is a legacy or explicitly requested diagnostic route only.
```

Add this bullet under Active feature `workflow-state.md`:

```markdown
- Clean completed task-generation state routes to `/sp.implement` when `active_command: sp-tasks`, `status: completed`, `phase_mode: task-generation-only`, and `next_command: /sp.implement` are present. `sp-auto` must not infer `/sp.analyze` for a clean task package.
```

In Route Resolution, replace:

```markdown
- Never bypass canonical upstream gates such as `/sp.clarify`, `/sp.deep-research`, `/sp.plan`, `/sp.tasks`, or `/sp.analyze` just because downstream artifacts already exist.
```

with:

```markdown
- Never bypass canonical upstream gates such as `/sp.clarify`, `/sp.deep-research`, `/sp.plan`, or `/sp.tasks` just because downstream artifacts already exist. Treat `/sp.analyze` as an upstream gate only when persisted workflow state explicitly records that legacy or diagnostic route.
```

- [ ] **Step 11: Update workflow-state template**

In `templates/workflow-state-template.md`, change `Fixed Lifecycle State` final handoff options:

```markdown
- final_handoff_decision: [/sp.plan | /sp.clarify | /sp.deep-research | /sp.implement | undecided]
```

Add this section after `## Analyze Gate`:

```markdown
## Clean Task-To-Implement Handoff

Use these exact values when `sp-tasks` completes cleanly and implementation may begin without an analyze diagnostic pass:

- active_command: sp-tasks
- status: completed
- phase_mode: task-generation-only
- current_stage: task-generation
- current_domain: none
- next_action: hand off to implement
- blocker_reason: None
- final_handoff_decision: /sp.implement
- handoff_to_implement: handoff-to-implement.json
- next_command: /sp.implement
- gate_status: cleared
- highest_invalid_stage: none
- reopen_source: none
- reopen_target: none
- reopen_reason: none
```

Change the `Next Command` examples to:

```markdown
- [`/sp.plan` | `/sp.tasks` | `/sp.implement` | `/sp.clarify` | `/sp.deep-research` | `/sp.analyze` only for explicit legacy diagnostic state | other canonical next workflow token]
```

- [ ] **Step 12: Update passive workflow routing skill**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, add this paragraph under Recommendation Rules before individual command bullets:

```markdown
The default generated path is `sp-specify -> sp-plan -> sp-tasks -> sp-implement`. `sp-checklist` and `sp-analyze` remain visible optional diagnostics, but they are not default quality nets for clean workflow progress.
```

Change:

```markdown
- Use `sp-implement` only after tasks are ready and execution should begin.
```

to:

```markdown
- Use `sp-implement` after `sp-tasks` produces a clean task package and records `/sp.implement`.
```

Change:

```markdown
- Use `sp-analyze` for drift, consistency, or readiness checks across existing spec/plan/tasks artifacts.
```

to:

```markdown
- Use `sp-analyze` only for optional diagnostics, explicit user requests, or persisted legacy `/sp.analyze` state.
```

Add:

```markdown
- Clean completed `sp-tasks` state with `/sp.implement` should route through `sp-auto` to `sp-implement`.
```

- [ ] **Step 13: Run focused template tests**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py::test_task3_owned_handoffs_keep_canonical_tokens_without_invocation_placeholders tests/test_alignment_templates.py::test_tasks_template_clean_completion_hands_off_to_implement tests/test_alignment_templates.py::test_tasks_template_requires_implementation_readiness_self_audit_and_legacy_remediation_mode tests/test_alignment_templates.py::test_implement_template_trusts_clean_tasks_handoff_and_respects_legacy_analyze_state tests/test_tasks_reporting_guidance.py tests/test_extension_skills.py tests/test_passive_skill_guidance.py -q
```

Expected: pass after template updates, except generated extension tests may still fail until integration projection updates in Task 8.

- [ ] **Step 14: Commit template contract updates**

Run:

```powershell
git add templates/commands/plan.md templates/commands/tasks.md templates/command-partials/tasks/shell.md templates/tasks-template.md templates/commands/implement.md templates/command-partials/implement/shell.md templates/commands/checklist.md templates/commands/analyze.md templates/commands/auto.md templates/workflow-state-template.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md
git commit -m "feat: make tasks implement the default workflow handoff"
```

Expected: commit succeeds.

---

### Task 7: Update CLI and Documentation Guidance

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `templates/project-map/**` only if grep finds current generated workflow guidance there

- [ ] **Step 1: Update CLI skill descriptions**

In `src/specify_cli/__init__.py`, find `SKILL_DESCRIPTIONS` and update entries:

```python
"tasks": "Generate implementation-ready tasks from planning artifacts and hand off clean task packages directly to implement.",
"implement": "Execute an implementation-ready tasks.md package when workflow state records /sp.implement.",
"analyze": "Optional read-only diagnostic and legacy revalidation pass across spec/plan/tasks artifacts.",
"checklist": "Optional requirements-quality checklist aid; not part of the default delivery path.",
"auto": "Resume the canonical next workflow from state, including clean tasks-to-implement handoffs.",
```

Keep exact dictionary style and nearby descriptions as currently written.

- [ ] **Step 2: Update CLI workflow display**

In `src/specify_cli/__init__.py`, update any display line that says:

```text
analyze [default gate before implement]
```

to:

```text
analyze [optional diagnostic / legacy revalidation]
```

Ensure the mainline list reads `specify -> plan -> tasks -> implement`. Keep support skills list including `checklist` and `analyze`.

- [ ] **Step 3: Update README mainline guidance**

In `README.md`, replace the old analyze-required block around the workflow guidance with:

```markdown
The normal generated delivery path is `specify -> plan -> tasks -> implement`.

- `checklist` is an optional requirements-quality aid. It is useful when you want a tailored checklist over requirements or planning artifacts, but it is not a default gate after planning.
- `analyze` is an optional diagnostic and legacy revalidation route. Use it when a user explicitly requests cross-artifact analysis, when existing `workflow-state.md` records `/sp.analyze`, or when implementation drift needs read-only diagnosis.
- Clean `tasks` completion writes `next_command: /sp.implement`, `gate_status: cleared`, and `highest_invalid_stage: none`.
- If task readiness fails, `tasks` routes directly to `plan`, `clarify`, or `deep-research` with blocking evidence instead of sending a clean package through `analyze`.
```

Remove prose that says `analyze` is the default pre-implementation gate, that the normal path is `tasks -> analyze -> implement`, or that tasks should run an analyze-compatible self-audit before final handoff. Replace “analyze-compatible self-audit” with “implementation-readiness self-audit”.

- [ ] **Step 4: Update quickstart walkthrough**

In `docs/quickstart.md`, update the main command walkthrough so it shows:

```text
/sp-specify
/sp-plan
/sp-tasks
/sp-implement
```

Move `/sp-checklist` and `/sp-analyze` into an optional diagnostics section:

```markdown
Optional diagnostics:

- Run `/sp-checklist` when you want a requirements-quality checklist before planning or task generation continues.
- Run `/sp-analyze` when you explicitly need read-only cross-artifact diagnostics, are resuming a legacy `/sp.analyze` state, or need drift revalidation after implementation has started.
```

Remove any line that says `analyze` is the required gate before implementation once `tasks.md` exists.

- [ ] **Step 5: Update handbook convergence note**

In `PROJECT-HANDBOOK.md`, replace the current analyze/tasks convergence bullet with:

```markdown
- **Tasks/implement default contract**: `sp-tasks` must run an implementation-readiness self-audit before handoff. Clean completion writes `next_command: /sp.implement`, `gate_status: cleared`, and `highest_invalid_stage: none`; `sp-analyze` remains an optional diagnostic and legacy revalidation route only when explicitly invoked or recorded in existing state.
```

In `templates/project-handbook-template.md`, update consequence obligation language to avoid implying analyze is on the default path:

```markdown
Use `CA-###` IDs for consequence obligations that must survive handoff from `discussion` to `specify`, `plan`, `tasks`, and `implement`; `analyze` consumes the same obligations only when run as an optional diagnostic or legacy revalidation pass.
```

- [ ] **Step 6: Search generated project-map guidance and update active surfaces**

Run:

```powershell
rg -n "tasks -> analyze -> implement|default pre-implementation gate|required gate before implementation|analyze-compatible|sp-tasks -> sp-analyze|sp-analyze.*default" templates/project-map README.md docs PROJECT-HANDBOOK.md src/specify_cli/__init__.py
```

Expected before edits: hits in README/quickstart/handbook and possibly project-map templates.

For any hit under `templates/project-map/**`, replace the old default path with direct `tasks -> implement` language and describe analyze as optional diagnostic/legacy revalidation. Do not edit historical files under `docs/superpowers/specs/**` or `docs/superpowers/plans/**` in this task.

- [ ] **Step 7: Run docs tests**

Run:

```powershell
uv run --extra test pytest tests/test_specify_guidance_docs.py -q
```

Expected: pass after docs updates.

- [ ] **Step 8: Commit docs and CLI guidance**

Run:

```powershell
git add src/specify_cli/__init__.py README.md docs/quickstart.md PROJECT-HANDBOOK.md templates/project-handbook-template.md templates/project-map
git commit -m "docs: teach direct tasks implement workflow"
```

Expected: commit succeeds. If `templates/project-map` has no changes, omit it from `git add`.

---

### Task 8: Update Integration Projection Tests and Generated Skill Assertions

**Files:**
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py` if failing
- Modify: `tests/integrations/test_integration_base_markdown.py` if failing
- Modify: `tests/integrations/test_integration_base_toml.py` if failing
- Modify: `tests/integrations/test_integration_base_skills.py` if failing
- Modify: `tests/integrations/test_cli.py` if failing
- Modify: `tests/test_extension_skills.py` if not already fully handled

- [ ] **Step 1: Run generated skill and integration projection tests**

Run:

```powershell
uv run --extra test pytest tests/test_extension_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_cli.py -q
```

Expected: failures where tests still assert `/sp-analyze` as default gate or checklist recommendation. Generated command presence tests for `sp-analyze` should continue to pass.

- [ ] **Step 2: Update Codex generated skill assertions**

In `tests/integrations/test_integration_codex.py`, keep assertions that generated projects include an `sp-analyze` skill. Replace any assertion that tasks or implement skill text requires analyze before implementation with:

```python
    assert "clean task generation hands off to `/sp-implement`" in tasks_content.lower()
    assert "implementation-readiness task self-audit" in tasks_content.lower()
    assert "implementation remains blocked until `/sp-analyze`" not in tasks_content.lower()
    assert "legacy `/sp.analyze` state" in implement_content.lower()
    assert "only stop for `/sp.analyze` when `workflow_state_file` explicitly records it" in implement_content.lower()
```

Use the actual local variable names from the test. If the generated invocation style uses `/sp.implement` instead of `/sp-implement`, assert the style that the renderer produces for that integration.

- [ ] **Step 3: Update CLI generated command list expectations only where semantic**

In `tests/integrations/test_cli.py`, keep `/sp-analyze` in command lists because the command remains available. Replace output assertions that label it as required/default with:

```python
assert "optional diagnostic" in result.output.lower()
assert "default gate before implement" not in result.output.lower()
```

If a test only checks that `/sp-analyze` appears in help output, leave it unchanged.

- [ ] **Step 4: Update base integration projection tests if they assert old template strings**

For any failing assertion in base integration tests, use this rule:

- Keep `sp-analyze` present in generated assets.
- Remove expectations that `sp-plan` defaults to checklist.
- Remove expectations that `sp-tasks` defaults to analyze.
- Add expectations that rendered `sp-tasks` includes direct implement handoff and implementation-readiness self-audit.
- Add expectations that rendered `sp-auto` says `/sp.analyze` is explicit legacy/diagnostic only.

Use concrete assertions matching generated output, for example:

```python
assert "/sp.implement for clean task generation" in rendered_tasks
assert "Implementation-Readiness Task Self-Audit" in rendered_tasks
assert "`/sp.analyze` is a legacy or explicitly requested diagnostic route only" in rendered_auto
```

- [ ] **Step 5: Re-run integration projection tests**

Run:

```powershell
uv run --extra test pytest tests/test_extension_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_cli.py -q
```

Expected: pass.

- [ ] **Step 6: Commit integration test updates**

Run:

```powershell
git add tests/test_extension_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_cli.py
git commit -m "test: update generated workflow projections for direct implement handoff"
```

Expected: commit succeeds. Omit unchanged files from `git add`.

---

### Task 9: Full Focused Regression and Stale-Text Sweep

**Files:**
- Modify only files exposed by the verification commands.

- [ ] **Step 1: Run hook and lane regression**

Run:

```powershell
uv run --extra test pytest tests/hooks/test_workflow_boundary_hooks.py tests/hooks/test_phase_boundary_hooks.py tests/hooks/test_state_hooks.py tests/hooks/test_preflight_hooks.py tests/hooks/test_session_state_hooks.py tests/lanes/test_resolution.py tests/lanes/test_reconcile.py -q
```

Expected: pass.

- [ ] **Step 2: Run template and documentation regression**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py tests/test_tasks_reporting_guidance.py tests/test_specify_guidance_docs.py tests/test_extension_skills.py tests/test_passive_skill_guidance.py -q
```

Expected: pass.

- [ ] **Step 3: Run integration projection regression**

Run:

```powershell
uv run --extra test pytest tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py -q
```

Expected: pass.

- [ ] **Step 4: Sweep active surfaces for stale default-path language**

Run:

```powershell
rg -n "default gate before implement|required gate before implementation|tasks -> analyze -> implement|/sp\\.analyze for normal|recommend `/sp-analyze`|do not hand off directly to.*implement|Implementation remains blocked until.*analyze|analyze-compatible task self-audit|sp-tasks -> sp-analyze" templates src tests README.md docs PROJECT-HANDBOOK.md
```

Expected: no hits in active product surfaces except historical design/plan files under `docs/superpowers/**` and tests that explicitly assert legacy compatibility. If active template, runtime, README, quickstart, or handbook hits remain, edit them to direct `tasks -> implement` or optional diagnostic wording and re-run Steps 2-4.

- [ ] **Step 5: Sweep for `sp-checklist` default-handoff remnants**

Run:

```powershell
rg -n "default_handoff:.*checklist|optionally /sp\\.checklist|/sp-checklist.*default|checklist.*normal next step|recommend `/sp-checklist`" templates src tests README.md docs PROJECT-HANDBOOK.md
```

Expected: no hits that make checklist part of the default path. Hits that describe optional checklist diagnostics are acceptable only when the wording includes `optional`.

- [ ] **Step 6: Run package-level smoke tests if focused suites changed shared integration code**

Run:

```powershell
uv run --extra test pytest tests/contract/test_hook_cli_surface.py tests/test_command_surface_semantics.py tests/test_alignment_templates.py -q
```

Expected: pass.

- [ ] **Step 7: Review git diff**

Run:

```powershell
git diff --stat
git diff -- templates/commands/tasks.md templates/commands/auto.md src/specify_cli/lanes/reconcile.py src/specify_cli/hooks/state_validation.py
```

Expected: diff shows only the planned workflow routing, clean state, template, docs, and test changes. No unrelated generated local `.specify/` state should be included.

- [ ] **Step 8: Final commit**

If any verification fixes were made after prior commits, run:

```powershell
git add templates src tests README.md docs PROJECT-HANDBOOK.md
git commit -m "fix: remove stale analyze default path references"
```

Expected: commit succeeds or reports nothing to commit if all prior task commits already captured the final state.

---

## Self-Review

- Spec coverage: The plan covers the three requested clarifications: `templates/commands/auto.md` routing, exact clean task-to-implement state fields, and clean checklist recommendation. It also covers runtime hooks, lane reconcile, templates, docs, passive skills, generated integrations, and stale-text sweeps.
- Placeholder scan: No task uses TBD/TODO/fill-in language. Where a failing integration test may expose a specific assertion, the plan gives concrete replacement rules and example assertions.
- Type consistency: New serializer keys are `gate_status`, `gate_cycle`, `highest_invalid_stage`, and `blocker_attribution_values`; those names match the proposed tests and workflow-state template fields. The clean handoff value is consistently `/sp.implement`, and legacy compatibility remains `/sp.analyze`.
