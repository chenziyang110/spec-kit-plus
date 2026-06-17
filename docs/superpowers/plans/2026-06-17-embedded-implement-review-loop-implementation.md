# Embedded Implement Review Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sp-implement` include a default embedded review-and-repair loop before and during execution, without exposing a separate public review workflow.

**Architecture:** Add small execution-review runtime primitives for feature-dir audit records, snapshots, task ID stability, and workflow-state write validation. Update `sp-tasks`, `tasks.md`, `workflow-state.md`, `implement-execution-state`, and `sp-implement` templates so generated workflows carry an internal pre-implement and drift-review protocol. Keep existing Codex team batch review working by adapting from it rather than replacing it.

**Tech Stack:** Python dataclasses/pytest for runtime helpers; Markdown and JSON templates under `templates/`; existing Typer CLI remains unchanged for this feature.

---

## File Structure

- Create `src/specify_cli/execution/implementation_review.py`: pure helper module for embedded review records, repair records, snapshot writing, task identity helpers, and workflow-state update validation.
- Leave `src/specify_cli/execution/review_schema.py` unchanged in this milestone: existing `ReviewFinding` and `ReviewRoundRecord` stay scoped to Codex team batch review, while embedded review uses the new helper module.
- Modify `templates/commands/implement.md`: add the required embedded review loop before first implementation work and after review windows or join points.
- Modify `templates/commands/tasks.md`: require `sp-tasks` to emit review-ready metadata while still recommending `/sp.implement`.
- Modify `templates/tasks-template.md`: add the embedded implement review policy, task identity stability, review windows, and repair audit guidance to generated task packages.
- Modify `templates/workflow-state-template.md`: add an `Embedded Implement Review` section with field names allowed for embedded review to update.
- Modify `templates/implement-execution-state-template.json`: add `review_gate` and `review_window_policy` defaults.
- Modify `README.md`, `PROJECT-HANDBOOK.md`, `templates/project-handbook-template.md`, and `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: describe embedded review as part of `sp-implement` without changing the public workflow.
- Modify tests:
  - `tests/test_alignment_templates.py`
  - `tests/execution/test_implementation_review.py`
  - `tests/integrations/test_integration_base_markdown.py`
  - `tests/integrations/test_integration_base_skills.py`
  - `tests/integrations/test_integration_base_toml.py`
  - `tests/test_specify_guidance_docs.py`
  - `tests/test_passive_skill_guidance.py`

## Current Workspace Constraint

The repository already has unrelated uncommitted changes in documentation, templates, and tests. Before editing any file in this plan, inspect the current diff for that file and preserve unrelated user changes. Stage and commit only the files changed by the current task.

---

## Task 1: Lock the Embedded Review Template Contract with Failing Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Test command: `uv run --extra test pytest tests/test_alignment_templates.py -q`

- [ ] **Step 1: Inspect current test file diff before editing**

Run:

```powershell
git diff -- tests/test_alignment_templates.py
```

Expected: any existing diff is user-owned context. Keep it intact while adding new tests.

- [ ] **Step 2: Add shared template assertions**

Append these tests near the existing implement/task template contract tests in `tests/test_alignment_templates.py`:

```python
def test_tasks_and_implement_templates_embed_internal_review_loop_without_public_review_command() -> None:
    tasks = _read("templates/commands/tasks.md")
    task_template = _read("templates/tasks-template.md")
    implement = _read("templates/commands/implement.md")
    workflow_state = _read("templates/workflow-state-template.md")
    combined = "\n".join([tasks, task_template, implement, workflow_state])
    lowered = combined.lower()

    assert "embedded implement review" in lowered
    assert "pre-implement review" in lowered
    assert "join-point drift review" in lowered
    assert "review_window_policy" in combined
    assert "auto_repair_tasks" in combined
    assert "implementation-review/reviews.ndjson" in combined
    assert "implementation-review/repairs.ndjson" in combined
    assert "snapshots/" in lowered
    assert "/sp.review" not in combined
    assert "sp-review" not in combined


def test_implement_template_preserves_workflow_state_review_allowlist() -> None:
    implement = _read("templates/commands/implement.md")
    lowered = implement.lower()

    assert "workflow-state write allowlist" in lowered
    assert "active_profile" in implement
    assert "required_evidence" in implement
    assert "final_handoff_decision" in implement
    assert "analyze gate" in lowered
    assert "must not rewrite" in lowered
    assert "review_gate" in implement
    assert "review_window_policy" in implement


def test_tasks_template_requires_stable_task_identity_for_embedded_repair() -> None:
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "task identity" in lowered
    assert "completed task ids are immutable" in lowered
    assert "append-only" in lowered
    assert "repair_for" in content
    assert "task-index.json" in content
    assert "task-packets" in content
    assert "worker-result" in lowered
```

- [ ] **Step 3: Add execution state JSON assertions**

Append this test near `test_implement_execution_state_template_requires_structured_execution_contract_from_tasks`:

```python
def test_implement_execution_state_template_includes_embedded_review_defaults() -> None:
    payload = json.loads(_read("templates/implement-execution-state-template.json"))

    assert payload["review_gate"] == {
        "mode": "embedded",
        "status": "pending",
        "scope": "pre-implement",
        "auto_repair_tasks": True,
        "last_reviewed_batch": None,
        "latest_review_id": None,
        "latest_repair_id": None,
    }
    assert payload["review_window_policy"] == {
        "max_completed_tasks_before_review": 5,
        "max_unreviewed_changed_paths": 8,
        "max_unreviewed_validation_failures": 0,
    }
```

- [ ] **Step 4: Run the focused tests and verify RED**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py -q
```

Expected: the new tests fail because the templates do not yet mention embedded implement review, the workflow-state allowlist, stable task identity, or `review_gate` defaults.

- [ ] **Step 5: Commit the RED tests**

Run:

```powershell
git add tests/test_alignment_templates.py
git commit -m "test: lock embedded implement review template contract"
```

---

## Task 2: Add Failing Runtime Helper Tests

**Files:**
- Create: `tests/execution/test_implementation_review.py`
- Test command: `uv run --extra test pytest tests/execution/test_implementation_review.py -q`

- [ ] **Step 1: Create runtime helper tests**

Create `tests/execution/test_implementation_review.py`:

```python
import json
from pathlib import Path

from specify_cli.execution.implementation_review import (
    ImplementationRepairOperation,
    ImplementationRepairRecord,
    ImplementationReviewFinding,
    ImplementationReviewRecord,
    next_append_task_id,
    snapshot_artifacts,
    validate_workflow_state_review_update,
    write_repair_record,
    write_review_record,
)


def test_write_review_record_appends_feature_dir_ndjson(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    finding = ImplementationReviewFinding(
        finding_id="IR-001",
        finding_type="missing_validation",
        severity="medium",
        summary="Real entrypoint validation is missing",
        affected_artifacts=["tasks.md"],
        task_ids=["T004"],
        repairable_at_task_layer=True,
        recommendation="Insert a real-entrypoint validation task",
    )
    record = ImplementationReviewRecord(
        review_id="pre-implement-r1",
        scope="pre-implement",
        trigger="before_first_task",
        decision="repair-and-continue",
        reviewed_tasks=["T001", "T002", "T003", "T004"],
        remaining_tasks=["T001", "T002", "T003", "T004"],
        findings=[finding],
        next_action="repair task-layer validation coverage",
    )

    path = write_review_record(feature_dir, record)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert path == feature_dir / "implementation-review" / "reviews.ndjson"
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["review_id"] == "pre-implement-r1"
    assert payload["findings"][0]["finding_type"] == "missing_validation"


def test_write_repair_record_appends_feature_dir_ndjson(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    record = ImplementationRepairRecord(
        repair_id="repair-pre-implement-r1",
        source_review_id="pre-implement-r1",
        changed_artifacts=["tasks.md", "task-packets/T081.json"],
        operations=[
            ImplementationRepairOperation(
                operation="insert_task",
                task_id="T081",
                details={"repair_for": "T004", "reason": "missing real-entrypoint validation"},
            )
        ],
        completed_tasks_preserved=True,
        next_batch="T001-T005",
    )

    path = write_repair_record(feature_dir, record)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert path == feature_dir / "implementation-review" / "repairs.ndjson"
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["repair_id"] == "repair-pre-implement-r1"
    assert payload["operations"][0]["task_id"] == "T081"


def test_snapshot_artifacts_copies_existing_task_layer_files(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    (feature_dir / "handoff-to-implement.json").write_text('{"status": "ready"}\n', encoding="utf-8")

    snapshots = snapshot_artifacts(
        feature_dir,
        review_id="pre-implement-r1",
        relative_paths=["tasks.md", "handoff-to-implement.json", "missing.json"],
    )

    assert snapshots == [
        "implementation-review/snapshots/tasks.before-pre-implement-r1.md",
        "implementation-review/snapshots/handoff-to-implement.before-pre-implement-r1.json",
    ]
    for rel_path in snapshots:
        assert (feature_dir / rel_path).exists()


def test_next_append_task_id_preserves_numeric_width() -> None:
    assert next_append_task_id([]) == "T001"
    assert next_append_task_id(["T001", "T080"]) == "T081"
    assert next_append_task_id(["T009", "T099"]) == "T100"
    assert next_append_task_id(["T0009"]) == "T0010"


def test_validate_workflow_state_review_update_allows_only_review_fields() -> None:
    before = {
        "active_profile": "Reference-Implementation",
        "required_evidence": ["reference source evidence"],
        "final_handoff_decision": "/sp.implement",
        "gate_status": "cleared",
        "next_action": "begin implementation",
        "next_command": "/sp.implement",
    }
    allowed_after = before | {
        "next_action": "run pre-implement review",
        "next_command": "/sp.debug",
        "review_gate": {"status": "blocked"},
        "review_window_policy": {"max_completed_tasks_before_review": 5},
    }

    assert validate_workflow_state_review_update(before, allowed_after) == []

    blocked_after = allowed_after | {
        "required_evidence": [],
        "final_handoff_decision": "/sp.tasks",
        "gate_status": "blocked",
    }

    errors = validate_workflow_state_review_update(before, blocked_after)

    assert "required_evidence is protected for embedded review" in errors
    assert "final_handoff_decision is protected for embedded review" in errors
    assert "gate_status is protected for embedded review" in errors
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
uv run --extra test pytest tests/execution/test_implementation_review.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'specify_cli.execution.implementation_review'`.

- [ ] **Step 3: Commit the RED tests**

Run:

```powershell
git add tests/execution/test_implementation_review.py
git commit -m "test: add embedded implementation review helper coverage"
```

---

## Task 3: Implement Feature-Dir Review Audit Helpers

**Files:**
- Create: `src/specify_cli/execution/implementation_review.py`
- Test: `tests/execution/test_implementation_review.py`

- [ ] **Step 1: Add the helper module**

Create `src/specify_cli/execution/implementation_review.py`:

```python
"""Embedded implementation review records and repair helpers."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


ReviewScope = Literal["pre-implement", "join-point-drift", "sequential-window"]
ReviewDecision = Literal[
    "cleared",
    "repair-and-continue",
    "repair-and-rerun-current-window",
    "blocked-reopen-tasks",
    "blocked-reopen-plan",
    "blocked-reopen-clarify",
    "blocked-deep-research",
    "debug-required",
]
ImplementationFindingType = Literal[
    "missing_task",
    "stale_task",
    "wrong_dependency",
    "write_set_conflict",
    "missing_validation",
    "packet_field_gap",
    "join_point_gap",
    "task_order_gap",
    "implementation_gap",
    "failed_validation",
    "worker_handoff_concern",
    "consumer_wiring_gap",
    "real_entrypoint_evidence_gap",
    "spec_goal_conflict",
    "plan_architecture_conflict",
    "scope_change_required",
    "must_preserve_conflict",
    "consequence_obligation_conflict",
    "unproven_implementation_chain",
    "user_decision_required",
]
ReviewSeverity = Literal["critical", "high", "medium", "low"]
RepairOperation = Literal[
    "insert_task",
    "update_task",
    "supersede_task",
    "update_dependency",
    "regenerate_packet",
    "insert_repair_task",
    "update_tracker",
    "update_handoff",
]


WORKFLOW_STATE_REVIEW_ALLOWED_KEYS = frozenset(
    {
        "review_gate",
        "review_window_policy",
        "implementation_review",
        "next_action",
        "next_command",
        "blocker_reason",
        "blocked_reason",
    }
)


TASK_ID_RE = re.compile(r"^T(?P<number>\d+)$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ImplementationReviewFinding:
    finding_id: str
    finding_type: ImplementationFindingType
    severity: ReviewSeverity
    summary: str
    affected_artifacts: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    repairable_at_task_layer: bool = False
    recommendation: str = ""
    upstream_reentry: str = ""


@dataclass(slots=True)
class ImplementationReviewRecord:
    review_id: str
    scope: ReviewScope
    trigger: str
    decision: ReviewDecision
    reviewed_tasks: list[str] = field(default_factory=list)
    remaining_tasks: list[str] = field(default_factory=list)
    findings: list[ImplementationReviewFinding] = field(default_factory=list)
    next_action: str = ""
    created_at: str = field(default_factory=_utc_now)


@dataclass(slots=True)
class ImplementationRepairOperation:
    operation: RepairOperation
    task_id: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ImplementationRepairRecord:
    repair_id: str
    source_review_id: str
    changed_artifacts: list[str]
    operations: list[ImplementationRepairOperation]
    completed_tasks_preserved: bool
    next_batch: str
    created_at: str = field(default_factory=_utc_now)


def implementation_review_root(feature_dir: Path) -> Path:
    return feature_dir / "implementation-review"


def reviews_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "reviews.ndjson"


def repairs_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "repairs.ndjson"


def snapshots_dir(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "snapshots"


def implementation_review_record_payload(record: ImplementationReviewRecord) -> dict[str, object]:
    return asdict(record)


def implementation_repair_record_payload(record: ImplementationRepairRecord) -> dict[str, object]:
    return asdict(record)


def _append_json_line(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")
    return path


def write_review_record(feature_dir: Path, record: ImplementationReviewRecord) -> Path:
    return _append_json_line(reviews_path(feature_dir), implementation_review_record_payload(record))


def write_repair_record(feature_dir: Path, record: ImplementationRepairRecord) -> Path:
    return _append_json_line(repairs_path(feature_dir), implementation_repair_record_payload(record))


def _snapshot_name(relative_path: str, review_id: str) -> str:
    source = Path(relative_path)
    suffix = source.suffix
    stem = source.as_posix().replace("/", "__")
    if suffix:
        stem = stem[: -len(suffix)]
    return f"{stem}.before-{review_id}{suffix}"


def snapshot_artifacts(feature_dir: Path, *, review_id: str, relative_paths: list[str]) -> list[str]:
    output_dir = snapshots_dir(feature_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for relative_path in relative_paths:
        source = feature_dir / relative_path
        if not source.exists() or not source.is_file():
            continue
        target = output_dir / _snapshot_name(relative_path, review_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target.relative_to(feature_dir).as_posix())
    return copied


def next_append_task_id(task_ids: list[str]) -> str:
    max_value = 0
    width = 3
    for task_id in task_ids:
        match = TASK_ID_RE.match(task_id.strip())
        if not match:
            continue
        number_text = match.group("number")
        max_value = max(max_value, int(number_text))
        width = max(width, len(number_text))
    return f"T{max_value + 1:0{width}d}"


def validate_workflow_state_review_update(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    keys = set(before) | set(after)
    for key in sorted(keys):
        if before.get(key) == after.get(key):
            continue
        if key not in WORKFLOW_STATE_REVIEW_ALLOWED_KEYS:
            errors.append(f"{key} is protected for embedded review")
    return errors
```

- [ ] **Step 2: Run the focused tests**

Run:

```powershell
uv run --extra test pytest tests/execution/test_implementation_review.py -q
```

Expected: all tests in `tests/execution/test_implementation_review.py` pass.

- [ ] **Step 3: Run existing review loop tests to guard compatibility**

Run:

```powershell
uv run --extra test pytest tests/codex_team/test_review_loop.py tests/orchestration/test_models.py -q
```

Expected: pass. Existing Codex team review persistence remains under `.specify/teams/state/reviews/`.

- [ ] **Step 4: Commit the runtime helper**

Run:

```powershell
git add src/specify_cli/execution/implementation_review.py tests/execution/test_implementation_review.py
git commit -m "feat: add embedded implementation review helpers"
```

---

## Task 4: Add Embedded Review Metadata to State Templates

**Files:**
- Modify: `templates/implement-execution-state-template.json`
- Modify: `templates/workflow-state-template.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Update `implement-execution-state-template.json`**

Add these keys before the closing brace, after `stop_and_reopen_conditions`:

```json
  "review_gate": {
    "mode": "embedded",
    "status": "pending",
    "scope": "pre-implement",
    "auto_repair_tasks": true,
    "last_reviewed_batch": null,
    "latest_review_id": null,
    "latest_repair_id": null
  },
  "review_window_policy": {
    "max_completed_tasks_before_review": 5,
    "max_unreviewed_changed_paths": 8,
    "max_unreviewed_validation_failures": 0
  }
```

Keep the JSON valid by adding a comma after the existing `stop_and_reopen_conditions` entry.

- [ ] **Step 2: Update `workflow-state-template.md`**

Add this section after `## Analyze Gate` and before `## Handoff Files`:

```markdown
## Embedded Implement Review

- review_gate:
  - mode: [embedded]
  - status: [pending | cleared | repaired | blocked]
  - scope: [pre-implement | join-point-drift | sequential-window]
  - auto_repair_tasks: [true | false]
  - last_reviewed_batch: [batch id or none]
  - latest_review_id: [review id or none]
  - latest_repair_id: [repair id or none]
- review_window_policy:
  - max_completed_tasks_before_review: [5]
  - max_unreviewed_changed_paths: [8]
  - max_unreviewed_validation_failures: [0]
- implementation_review:
  - reviews: [implementation-review/reviews.ndjson]
  - repairs: [implementation-review/repairs.ndjson]
  - snapshots: [implementation-review/snapshots/]
- workflow_state_write_allowlist:
  - review_gate
  - review_window_policy
  - implementation_review
  - next_action
  - blocker_reason
  - blocked_reason
  - next_command
- workflow_state_protected_fields:
  - active_profile
  - required_sections
  - activated_gates
  - task_shaping_rules
  - required_evidence
  - transition_policy
  - final_handoff_decision
  - authoritative_files
  - allowed_artifact_writes
  - forbidden_actions
  - Analyze Gate
  - Reopen Contract
```

- [ ] **Step 3: Run the focused template tests**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py -q
```

Expected: execution-state assertions pass. The tests that require `implement.md` and `tasks-template.md` wording still fail until later tasks.

- [ ] **Step 4: Commit state template changes**

Run:

```powershell
git add templates/implement-execution-state-template.json templates/workflow-state-template.md tests/test_alignment_templates.py
git commit -m "templates: add embedded review state metadata"
```

---

## Task 5: Update `sp-tasks` and Generated `tasks.md` Review-Ready Contract

**Files:**
- Modify: `templates/commands/tasks.md`
- Modify: `templates/tasks-template.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Update `templates/commands/tasks.md` output guidance**

In the `primary_outputs` frontmatter value and the `allowed_artifact_writes` list, keep `/sp.implement` as the default handoff and do not add a separate public review workflow. Add wording that task generation must prepare embedded review metadata, not run implementation review itself.

Add this paragraph near the implementation-readiness self-audit guidance:

```markdown
**Embedded Implement Review Preparation**: `sp-tasks` does not expose or route to a separate public review workflow. A clean task package still records `next_command: /sp.implement`, but it must prepare the internal review contract that `sp-implement` will run before code execution. Record `embedded_review_gate: required`, `auto_repair_tasks: true`, the default `review_window_policy`, reviewable join points, and packet regeneration expectations in `tasks.md`, `task-index.json`, `task-packets/*.json`, and `handoff-to-implement.json` when those artifacts are generated.
```

Add this report bullet in the final report section:

```markdown
- Embedded implement review preparation:
  - embedded_review_gate: required
  - auto_repair_tasks: true
  - review_window_policy: max_completed_tasks_before_review=5, max_unreviewed_changed_paths=8, max_unreviewed_validation_failures=0
  - visible_review_command: none
  - next_command remains `{{invoke:implement}}`
```

- [ ] **Step 2: Update `templates/tasks-template.md`**

Add this section after `## Task Shaping Rules`:

```markdown
## Embedded Implement Review Policy

- `sp-implement` must run a pre-implement review before the first code-writing task.
- `sp-implement` must run join-point drift review after each parallel batch, phase, pipeline stage, and sequential review window.
- Review windows default to:
  - `max_completed_tasks_before_review: 5`
  - `max_unreviewed_changed_paths: 8`
  - `max_unreviewed_validation_failures: 0`
- Review may automatically repair task-layer execution artifacts when the accepted goal and plan remain valid.
- Review may not rewrite `spec.md`, `alignment.md`, `context.md`, `plan.md`, upstream-derived profile fields, required evidence, final handoff decisions, Analyze Gate truth, or Reopen Contract truth.
- Review writes audit records to `implementation-review/reviews.ndjson`, repair records to `implementation-review/repairs.ndjson`, and pre-repair snapshots under `implementation-review/snapshots/`.

### Task Identity Stability

- Completed task IDs are immutable.
- Incomplete task IDs stay stable when the objective remains the same.
- New repair or refinement tasks use append-only IDs after the highest existing numeric ID.
- Follow-up repair tasks for completed-work gaps must carry `repair_for: T###` or `refines: T###` in the task detail metadata.
- Superseded incomplete tasks must remain traceable through `task-index.json`, task packet metadata, repair records, dependencies, `implement-tracker.md`, and worker-result references.
- After repair, the dependency graph and `next_batch` fields are authoritative for execution order even when `tasks.md` remains numerically append-only.
```

- [ ] **Step 3: Run the focused template tests**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py -q
```

Expected: tasks-template assertions pass. Implement-template assertions still fail until Task 6.

- [ ] **Step 4: Commit task contract changes**

Run:

```powershell
git add templates/commands/tasks.md templates/tasks-template.md tests/test_alignment_templates.py
git commit -m "templates: prepare tasks for embedded implement review"
```

---

## Task 6: Update `sp-implement` Embedded Review Loop Contract

**Files:**
- Modify: `templates/commands/implement.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add the embedded review section before `## Orchestration Model`**

Insert this section after the shared includes and before `## Orchestration Model`:

```markdown
## Embedded Implement Review Loop

This section is **mandatory**. `sp-implement` includes an internal review-and-repair loop. Do not expose, recommend, or route to a separate public review workflow.

### Pre-Implement Review

Before the first implementation task, run a pre-implement review over `tasks.md`, `task-index.json`, `task-packets/*.json`, `handoff-to-implement.json`, `workflow-state.md`, and the upstream read-only truth artifacts needed to verify coverage.

The review must check:

- every buildable requirement, locked planning decision, `MP-*` obligation, `CA-###` obligation, user-observable path, required evidence term, write set, dependency, join point, and packet-readiness condition still has executable coverage
- the first executable batch is still valid from current repository evidence
- downstream tasks do not depend on unverified assumptions from earlier unfinished work

If only task-layer defects exist, repair task-layer artifacts automatically and continue. If the defect changes goal, scope, architecture, required evidence, `MP-*`, `CA-###`, feasibility, or user decision state, stop and route to `/sp.clarify`, `/sp.deep-research`, `/sp.plan`, `/sp.tasks`, or `/sp.debug` as justified.

### Join-Point Drift Review

After every phase, parallel batch, pipeline stage, join point, and sequential review window, run a drift review before downstream work continues.

The drift review reads actual changed paths, worker handoffs, validation evidence, `implement-tracker.md`, open gaps, blockers, remaining tasks, task packets, and review records. It decides whether the remaining task package still matches implementation reality.

### Sequential Review Window

Do not execute a long sequential task list as one unreviewed queue. Run drift review whenever any limit is reached:

```text
max_completed_tasks_before_review = 5
max_unreviewed_changed_paths = 8
max_unreviewed_validation_failures = 0
```

Validation failure, stale handoff, worker concern, open gap, or missing real-entrypoint evidence triggers immediate drift review.

### Review Decisions

Each review must record one decision:

- `cleared`
- `repair-and-continue`
- `repair-and-rerun-current-window`
- `blocked-reopen-tasks`
- `blocked-reopen-plan`
- `blocked-reopen-clarify`
- `blocked-deep-research`
- `debug-required`

### Safe Repair Boundary

Review may repair `tasks.md`, `task-index.json`, `task-packets/*.json`, `handoff-to-implement.json`, `implement-tracker.md`, selected execution-review fields in `workflow-state.md`, and `implementation-review/*`.

Review must not rewrite upstream truth artifacts or upstream-derived workflow-state fields.

### Workflow-State Write Allowlist

Embedded review may write only:

- `review_gate`
- `review_window_policy`
- `implementation_review`
- current-run review blocker rows
- `next_action`
- `blocker_reason`
- `blocked_reason`
- `next_command` when stopping the current `sp-implement` run with a review decision

Embedded review must not rewrite:

- `active_profile`
- `required_sections`
- `activated_gates`
- `task_shaping_rules`
- `required_evidence`
- `transition_policy`
- `final_handoff_decision`
- `authoritative_files`
- `allowed_artifact_writes`
- `forbidden_actions`
- existing Analyze Gate truth
- existing Reopen Contract truth
- source discussion or must-preserve disposition fields

If any protected field is wrong, stale, or insufficient, record a blocker and route to the owning upstream workflow.

### Task Identity Stability

- Completed task IDs are immutable and must not be renumbered.
- Incomplete task IDs stay stable when their objective remains the same.
- New repair and refinement tasks use append-only IDs after the highest existing numeric ID.
- Completed-work gaps become follow-up repair tasks with `repair_for: T###` or `refines: T###`.
- Superseded incomplete tasks remain traceable through `task-index.json`, task packets, dependencies, repair records, tracker state, and worker-result references.
- After repair, dependency graph and `next_batch` metadata are authoritative for execution order.

### Audit Artifacts

Before automatic repair, snapshot changed task-layer artifacts under `FEATURE_DIR/implementation-review/snapshots/`.

Record every review in `FEATURE_DIR/implementation-review/reviews.ndjson`.

Record every automatic repair in `FEATURE_DIR/implementation-review/repairs.ndjson`.

After repair, revalidate task-index consistency, packet readiness, dependencies, tracker state, and worker-result references before continuing.
```

- [ ] **Step 2: Add review-loop references to execution steps**

In the existing execution loop, add concise references where the command currently says to choose a batch, cross a join point, or proceed through sequential tasks:

```markdown
- Before selecting the first batch, the pre-implement review gate must be cleared or repaired.
- Before crossing any join point, the join-point drift review gate must be cleared or repaired.
- For sequential work, do not exceed the review window limits before running drift review.
- Planned validation tasks remain executable work, but failed or missing validation triggers drift review before downstream implementation continues.
```

- [ ] **Step 3: Run focused template tests**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py -q
```

Expected: all new alignment-template tests pass.

- [ ] **Step 4: Commit implement template change**

Run:

```powershell
git add templates/commands/implement.md tests/test_alignment_templates.py
git commit -m "templates: embed implement review loop"
```

---

## Task 7: Add Integration Rendering Regressions

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Test commands:
  - `uv run --extra test pytest tests/integrations/test_integration_base_markdown.py -q`
  - `uv run --extra test pytest tests/integrations/test_integration_base_skills.py -q`
  - `uv run --extra test pytest tests/integrations/test_integration_base_toml.py -q`

- [ ] **Step 1: Inspect current diffs before editing integration tests**

Run:

```powershell
git diff -- tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
```

Expected: unrelated existing edits may be present. Preserve them.

- [ ] **Step 2: Add a shared assertion helper**

In each integration test family, add or reuse a helper that reads the rendered implement command/skill and asserts:

```python
def _assert_embedded_implement_review_contract(content: str) -> None:
    lowered = content.lower()

    assert "embedded implement review" in lowered
    assert "pre-implement review" in lowered
    assert "join-point drift review" in lowered
    assert "review_window_policy" in content
    assert "implementation-review/reviews.ndjson" in content
    assert "implementation-review/repairs.ndjson" in content
    assert "/sp.review" not in content
    assert "sp-review" not in content
```

- [ ] **Step 3: Call the helper from generated implement-surface tests**

For Markdown command integrations, call the helper on the generated `implement` command file content.

For skills-based integrations, call the helper on the generated `sp-implement/SKILL.md` content.

For TOML integrations, call the helper on the generated `implement` prompt content after TOML rendering.

- [ ] **Step 4: Run integration rendering tests**

Run:

```powershell
uv run --extra test pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected: pass. If a specific integration escapes braces or TOML quotes, adjust the test to parse the generated surface the same way existing tests do.

- [ ] **Step 5: Commit integration regressions**

Run:

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
git commit -m "test: require embedded review in generated implement surfaces"
```

---

## Task 8: Update User and Operator Documentation

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Test commands:
  - `uv run --extra test pytest tests/test_specify_guidance_docs.py -q`
  - `uv run --extra test pytest tests/test_passive_skill_guidance.py -q`

- [ ] **Step 1: Inspect current docs diffs before editing**

Run:

```powershell
git diff -- README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/test_specify_guidance_docs.py tests/test_passive_skill_guidance.py
```

Expected: existing unrelated edits are preserved.

- [ ] **Step 2: Update public workflow wording**

In `README.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md`, keep the public path as:

```text
specify -> plan -> tasks -> implement
```

or:

```text
sp-specify -> sp-plan -> sp-tasks -> sp-implement
```

Add this concept near the existing `sp-tasks` / `sp-implement` guidance:

```markdown
`sp-implement` includes an embedded review-and-repair loop. It runs a pre-implement review before code-writing starts, then runs drift review after join points and bounded sequential windows. Safe task-layer repairs update remaining tasks, packets, handoff state, tracker state, and review audit records automatically. Product goal, scope, architecture, required evidence, `MP-*`, `CA-###`, and feasibility conflicts still block and route back to the owning upstream workflow.
```

- [ ] **Step 3: Update passive workflow routing skill**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, keep the default route to `{{invoke:implement}}`. Add this guidance near the tasks/implement route notes:

```markdown
- Clean completed `sp-tasks` state still routes to `{{invoke:implement}}`; there is no visible separate review route. `sp-implement` owns the embedded pre-implement review, join-point drift review, sequential review windows, and safe task-layer repair loop.
```

- [ ] **Step 4: Add documentation regression assertions**

In `tests/test_specify_guidance_docs.py`, add a test that reads README and handbook surfaces and asserts:

```python
def test_docs_describe_embedded_implement_review_without_public_review_route() -> None:
    surfaces = [
        Path("README.md").read_text(encoding="utf-8"),
        Path("PROJECT-HANDBOOK.md").read_text(encoding="utf-8"),
        Path("templates/project-handbook-template.md").read_text(encoding="utf-8"),
    ]
    combined = "\n".join(surfaces)
    lowered = combined.lower()

    assert "embedded review-and-repair loop" in lowered
    assert "pre-implement review" in lowered
    assert "drift review" in lowered
    assert "sp-specify -> sp-plan -> sp-tasks -> sp-implement" in combined
    assert "/sp.review" not in combined
    assert "sp-review" not in combined
```

In `tests/test_passive_skill_guidance.py`, add a passive-skill assertion:

```python
def test_workflow_routing_keeps_review_embedded_in_implement() -> None:
    content = Path("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "no visible separate review route" in lowered
    assert "embedded pre-implement review" in lowered
    assert "{{invoke:implement}}" in content
    assert "/sp.review" not in content
    assert "sp-review" not in content
```

- [ ] **Step 5: Run docs tests**

Run:

```powershell
uv run --extra test pytest tests/test_specify_guidance_docs.py tests/test_passive_skill_guidance.py -q
```

Expected: pass.

- [ ] **Step 6: Commit documentation changes**

Run:

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/test_specify_guidance_docs.py tests/test_passive_skill_guidance.py
git commit -m "docs: document embedded implement review loop"
```

---

## Task 9: Run Focused Verification and Final Sweep

**Files:**
- Verify only; no expected file edits.

- [ ] **Step 1: Run focused runtime tests**

Run:

```powershell
uv run --extra test pytest tests/execution/test_implementation_review.py tests/codex_team/test_review_loop.py tests/orchestration/test_models.py -q
```

Expected: pass.

- [ ] **Step 2: Run focused template and integration tests**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected: pass.

- [ ] **Step 3: Run focused docs tests**

Run:

```powershell
uv run --extra test pytest tests/test_specify_guidance_docs.py tests/test_passive_skill_guidance.py -q
```

Expected: pass.

- [ ] **Step 4: Confirm no public review workflow was introduced**

Run:

```powershell
rg -n "/sp\\.review|sp-review" README.md PROJECT-HANDBOOK.md templates src
```

Expected: no matches.

- [ ] **Step 5: Check formatting and staged scope**

Run:

```powershell
git diff --check
git status --short
```

Expected: `git diff --check` is clean. `git status --short` may still show unrelated pre-existing workspace changes; do not stage unrelated changes.

- [ ] **Step 6: Final implementation summary**

Prepare a concise summary naming:

- runtime helper module added
- templates updated
- docs updated
- tests run
- any unrelated dirty files left untouched

Do not claim full implementation completion if any focused verification command failed.
