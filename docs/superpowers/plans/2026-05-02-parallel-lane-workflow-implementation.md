# Parallel Lane Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add crash-safe concurrent feature lanes so root-level `sp-*` workflows can isolate independent features by lane, resume safely after interruption, and close completed lanes through a dedicated `sp-integrate` workflow.

**Architecture:** Reuse existing orchestration state, hooks, workflow-state artifacts, feature directories, and Codex worktree primitives instead of inventing a second runtime. First lock the new lane model with failing tests, then add lane-local durable state plus reconcile logic, then route root-level `sp-*` commands through command-semantic lane resolution, then automate branch/worktree isolation, and finally add `sp-integrate` as the closeout workflow and update shared templates/docs.

**Tech Stack:** Python 3.13, Typer CLI, pytest, Markdown command templates, Bash/PowerShell helper scripts, existing workflow hooks, existing Codex worktree/runtime helpers.

---

## Context

Read before editing:

- `docs/superpowers/specs/2026-05-02-parallel-lane-workflow-design.md`
- `PROJECT-HANDBOOK.md`
- `templates/project-map/root/WORKFLOWS.md`
- `templates/project-map/root/ARCHITECTURE.md`
- `templates/project-map/root/CONVENTIONS.md`
- `src/specify_cli/__init__.py`
- `src/specify_cli/orchestration/models.py`
- `src/specify_cli/orchestration/policy.py`
- `src/specify_cli/orchestration/state_store.py`
- `src/specify_cli/debug/context.py`
- `src/specify_cli/hooks/checkpoint_serializers.py`
- `src/specify_cli/hooks/session_state.py`
- `src/specify_cli/codex_team/worktree_ops.py`
- `src/specify_cli/codex_team/auto_dispatch.py`
- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`
- `templates/commands/auto.md`
- `templates/workflow-state-template.md`
- `scripts/bash/create-new-feature.sh`
- `scripts/powershell/create-new-feature.ps1`

The working tree may contain user changes. Do not reset or revert unrelated files. If a task touches a dirty file, inspect it first and patch only the relevant lines.

## File Structure

Create:

- `src/specify_cli/lanes/__init__.py`
- `src/specify_cli/lanes/models.py`
- `src/specify_cli/lanes/state_store.py`
- `src/specify_cli/lanes/reconcile.py`
- `src/specify_cli/lanes/resolution.py`
- `src/specify_cli/lanes/lease.py`
- `src/specify_cli/lanes/worktree.py`
- `src/specify_cli/lanes/integration.py`
- `templates/commands/integrate.md`
- `tests/lanes/test_models.py`
- `tests/lanes/test_state_store.py`
- `tests/lanes/test_reconcile.py`
- `tests/lanes/test_resolution.py`
- `tests/lanes/test_lease.py`
- `tests/lanes/test_integration.py`

Modify:

- `src/specify_cli/__init__.py`
- `src/specify_cli/orchestration/models.py`
- `src/specify_cli/orchestration/state_store.py`
- `src/specify_cli/debug/context.py`
- `src/specify_cli/hooks/checkpoint_serializers.py`
- `src/specify_cli/hooks/session_state.py`
- `src/specify_cli/codex_team/worktree_ops.py`
- `scripts/bash/create-new-feature.sh`
- `scripts/powershell/create-new-feature.ps1`
- `templates/workflow-state-template.md`
- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`
- `templates/commands/auto.md`
- `README.md`
- `docs/quickstart.md`
- `PROJECT-HANDBOOK.md`
- `templates/project-map/root/ARCHITECTURE.md`
- `templates/project-map/root/WORKFLOWS.md`
- `templates/project-map/root/CONVENTIONS.md`

Update tests:

- `tests/orchestration/test_models.py`
- `tests/orchestration/test_state_store.py`
- `tests/hooks/test_session_state_hooks.py`
- `tests/hooks/test_checkpoint_hooks.py`
- `tests/hooks/test_statusline_hooks.py`
- `tests/hooks/test_preflight_hooks.py`
- `tests/test_alignment_templates.py`
- `tests/test_extension_skills.py`
- `tests/integrations/test_cli.py`
- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_base_toml.py`
- `tests/integrations/test_integration_claude.py`
- `tests/integrations/test_integration_codex.py`
- `tests/codex_team/test_worktree_ops.py`
- `tests/codex_team/test_auto_dispatch.py`
- `tests/codex_team/test_runtime_bridge.py`

## Implementation Constraints

- Preserve existing root-level `sp-*` command names; do not require a separate lane-picking command for ordinary usage.
- Treat `.specify/lanes/index.json` as a rebuildable cache, not the truth source.
- Make lane-local durable state and real feature artifacts the truth source for recovery.
- Never auto-resume a lane classified as `uncertain`.
- Auto-resume only when exactly one safe candidate exists for the command domain.
- Keep branch/worktree isolation mandatory for the parallel-lane model.
- Keep the first release focused on independent features, not stacked feature chains.
- Add `sp-integrate` as a dedicated closeout workflow rather than folding closeout into `sp-implement`.

---

### Task 1: Lock the lane model with failing tests

**Files:**
- Create: `tests/lanes/test_models.py`
- Create: `tests/lanes/test_state_store.py`
- Create: `tests/lanes/test_reconcile.py`
- Create: `tests/lanes/test_resolution.py`
- Create: `tests/lanes/test_lease.py`
- Create: `tests/lanes/test_integration.py`
- Modify: `tests/orchestration/test_models.py`
- Modify: `tests/hooks/test_session_state_hooks.py`
- Modify: `tests/codex_team/test_worktree_ops.py`

- [ ] **Step 1: Add lane model literal and dataclass tests**

Create `tests/lanes/test_models.py` with:

```python
from dataclasses import asdict

from specify_cli.lanes.models import (
    LaneLifecycleState,
    LaneRecoveryState,
    LaneRecord,
    LaneLease,
)


def test_lane_record_defaults_to_draft_and_blocked_safe_values():
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-parallel-lane",
        feature_dir="specs/001-parallel-lane",
        branch_name="001-parallel-lane",
        worktree_path=".specify/lanes/worktrees/lane-001",
    )

    payload = asdict(lane)

    assert lane.lifecycle_state == "draft"
    assert lane.recovery_state == "blocked"
    assert lane.last_command == ""
    assert payload["lane_id"] == "lane-001"
    assert payload["feature_id"] == "001-parallel-lane"


def test_lane_lease_tracks_owner_and_expiry_fields():
    lease = LaneLease(
        lane_id="lane-001",
        session_id="sess-1",
        owner_command="implement",
        acquired_at="2026-05-02T00:00:00+00:00",
        renew_until="2026-05-02T00:05:00+00:00",
        repo_root="F:/github/spec-kit-plus",
        runtime_token="tok-1",
    )

    assert lease.owner_command == "implement"
    assert lease.session_id == "sess-1"
    assert lease.runtime_token == "tok-1"
```

- [ ] **Step 2: Add lane state-store round-trip tests**

Create `tests/lanes/test_state_store.py` with:

```python
from pathlib import Path

from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.state_store import (
    lane_index_path,
    lane_record_path,
    read_lane_index,
    read_lane_record,
    write_lane_index,
    write_lane_record,
)


def test_lane_paths_live_under_specify_lanes(tmp_path: Path):
    assert lane_index_path(tmp_path) == tmp_path / ".specify" / "lanes" / "index.json"
    assert lane_record_path(tmp_path, "lane-001") == tmp_path / ".specify" / "lanes" / "lane-001" / "lane.json"


def test_write_and_read_lane_record_round_trip(tmp_path: Path):
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        last_command="implement",
    )

    write_lane_record(tmp_path, lane)
    loaded = read_lane_record(tmp_path, "lane-001")

    assert loaded is not None
    assert loaded.lane_id == "lane-001"
    assert loaded.recovery_state == "resumable"
    assert loaded.last_command == "implement"


def test_write_and_read_lane_index_round_trip(tmp_path: Path):
    payload = {
        "lanes": [
            {"lane_id": "lane-001", "feature_id": "001-demo", "last_command": "implement"}
        ]
    }

    write_lane_index(tmp_path, payload)
    assert read_lane_index(tmp_path) == payload
```

- [ ] **Step 3: Add reconcile classification tests for resumable, uncertain, and blocked**

Create `tests/lanes/test_reconcile.py` with:

```python
from pathlib import Path

from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.reconcile import reconcile_lane


def _write_workflow_state(feature_dir: Path, next_command: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-analyze`",
                "- status: `completed`",
                "",
                "## Next Command",
                "",
                f"- `{next_command}`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_implement_tracker(feature_dir: Path, status: str = "executing") -> None:
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                f"status: {status}",
                "feature: 001-demo",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: execute batch",
                "next_action: collect worker result",
                "",
                "## Execution State",
                "retry_attempts: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_reconcile_marks_consistent_implement_lane_resumable(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(feature_dir, "/sp.implement")
    _write_implement_tracker(feature_dir, "executing")
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        last_command="implement",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "resumable"
    assert reconciled.last_stable_checkpoint != ""


def test_reconcile_marks_conflicting_implement_lane_uncertain(tmp_path: Path):
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_workflow_state(feature_dir, "/sp.tasks")
    _write_implement_tracker(feature_dir, "executing")
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        last_command="implement",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "uncertain"
    assert "next_command" in reconciled.recovery_reason


def test_reconcile_marks_missing_stage_artifacts_blocked(tmp_path: Path):
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        last_command="implement",
    )

    reconciled = reconcile_lane(tmp_path, lane, command_name="implement")

    assert reconciled.recovery_state == "blocked"
```

- [ ] **Step 4: Add resolution tests for unique safe resume vs ambiguous resume**

Create `tests/lanes/test_resolution.py` with:

```python
from pathlib import Path

from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.resolution import resolve_lane_for_command
from specify_cli.lanes.state_store import write_lane_index, write_lane_record


def test_resolve_lane_returns_unique_resumable_candidate(tmp_path: Path):
    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        last_command="implement",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}]})

    result = resolve_lane_for_command(tmp_path, command_name="implement")

    assert result.mode == "resume"
    assert result.selected_lane_id == "lane-001"


def test_resolve_lane_requires_choice_for_multiple_resumable_candidates(tmp_path: Path):
    lane_a = LaneRecord(
        lane_id="lane-001",
        feature_id="001-alpha",
        feature_dir="specs/001-alpha",
        branch_name="001-alpha",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="resumable",
        last_command="implement",
    )
    lane_b = LaneRecord(
        lane_id="lane-002",
        feature_id="002-beta",
        feature_dir="specs/002-beta",
        branch_name="002-beta",
        worktree_path=".specify/lanes/worktrees/lane-002",
        lifecycle_state="implementing",
        recovery_state="resumable",
        last_command="implement",
    )
    write_lane_record(tmp_path, lane_a)
    write_lane_record(tmp_path, lane_b)
    write_lane_index(
        tmp_path,
        {"lanes": [{"lane_id": "lane-001"}, {"lane_id": "lane-002"}]},
    )

    result = resolve_lane_for_command(tmp_path, command_name="implement")

    assert result.mode == "choose"
    assert result.selected_lane_id == ""
    assert [candidate.feature_id for candidate in result.candidates] == ["001-alpha", "002-beta"]
```

- [ ] **Step 5: Add lease expiry and single-writer tests**

Create `tests/lanes/test_lease.py` with:

```python
from datetime import datetime, timedelta, timezone

from specify_cli.lanes.lease import lane_lease_expired, validate_lane_write_lease
from specify_cli.lanes.models import LaneLease


def test_lane_lease_expired_returns_true_when_renew_until_is_past():
    lease = LaneLease(
        lane_id="lane-001",
        session_id="sess-1",
        owner_command="implement",
        acquired_at="2026-05-02T00:00:00+00:00",
        renew_until=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        repo_root="F:/github/spec-kit-plus",
        runtime_token="tok-1",
    )

    assert lane_lease_expired(lease) is True


def test_validate_lane_write_lease_blocks_second_active_writer():
    lease = LaneLease(
        lane_id="lane-001",
        session_id="sess-1",
        owner_command="implement",
        acquired_at="2026-05-02T00:00:00+00:00",
        renew_until=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        repo_root="F:/github/spec-kit-plus",
        runtime_token="tok-1",
    )

    status = validate_lane_write_lease(lease, requester_session_id="sess-2")

    assert status == "blocked"
```

- [ ] **Step 6: Add `sp-integrate` readiness tests**

Create `tests/lanes/test_integration.py` with:

```python
from pathlib import Path

from specify_cli.lanes.integration import collect_integration_candidates
from specify_cli.lanes.models import LaneRecord
from specify_cli.lanes.state_store import write_lane_index, write_lane_record


def test_collect_integration_candidates_returns_completed_or_ready_lanes(tmp_path: Path):
    ready_lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        lifecycle_state="implementing",
        recovery_state="completed",
        last_command="implement",
    )
    blocked_lane = LaneRecord(
        lane_id="lane-002",
        feature_id="002-demo",
        feature_dir="specs/002-demo",
        branch_name="002-demo",
        worktree_path=".specify/lanes/worktrees/lane-002",
        lifecycle_state="implementing",
        recovery_state="blocked",
        last_command="implement",
    )
    write_lane_record(tmp_path, ready_lane)
    write_lane_record(tmp_path, blocked_lane)
    write_lane_index(
        tmp_path,
        {"lanes": [{"lane_id": "lane-001"}, {"lane_id": "lane-002"}]},
    )

    candidates = collect_integration_candidates(tmp_path)

    assert [candidate.feature_id for candidate in candidates] == ["001-demo"]
```

- [ ] **Step 7: Add regression tests around existing surfaces that must change**

Add these assertions:

`tests/orchestration/test_models.py`

```python
from typing import get_args

from specify_cli.orchestration.models import DispatchShape


def test_dispatch_shape_literals_include_leader_inline_fallback():
    assert "leader-inline-fallback" in get_args(DispatchShape)
```

`tests/hooks/test_session_state_hooks.py`

```python
def test_session_state_warns_when_lane_recovery_is_uncertain(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    _write_workflow_state(feature_dir, "/sp.tasks")
    _write_implement_tracker(feature_dir, status="executing")

    result = run_quality_hook(
        project,
        "workflow.session_state.validate",
        {"command_name": "implement", "feature_dir": str(feature_dir)},
    )

    assert result.status == "warn"
    assert any("/sp.tasks" in message for message in result.warnings)
```

`tests/codex_team/test_worktree_ops.py`

```python
from specify_cli.codex_team.worktree_ops import lane_worktree_path


def test_lane_worktree_path_is_rooted_within_project(codex_team_project_root):
    expected = codex_team_project_root / ".specify" / "lanes" / "worktrees" / "lane-001"
    assert lane_worktree_path(codex_team_project_root, lane_id="lane-001") == expected
```

- [ ] **Step 8: Run targeted tests and confirm they fail before implementation**

Run:

```bash
pytest tests/lanes/test_models.py tests/lanes/test_state_store.py tests/lanes/test_reconcile.py tests/lanes/test_resolution.py tests/lanes/test_lease.py tests/lanes/test_integration.py tests/orchestration/test_models.py tests/hooks/test_session_state_hooks.py tests/codex_team/test_worktree_ops.py -q
```

Expected:

- FAIL because `specify_cli.lanes` does not exist yet
- FAIL because `DispatchShape` does not yet include `leader-inline-fallback`
- FAIL because lane worktree helpers do not exist yet

- [ ] **Step 9: Commit the red-state test suite**

```bash
git add tests/lanes tests/orchestration/test_models.py tests/hooks/test_session_state_hooks.py tests/codex_team/test_worktree_ops.py
git commit -m "test: lock parallel lane workflow behavior"
```

### Task 2: Add lane models and durable state primitives

**Files:**
- Create: `src/specify_cli/lanes/__init__.py`
- Create: `src/specify_cli/lanes/models.py`
- Create: `src/specify_cli/lanes/state_store.py`
- Modify: `src/specify_cli/orchestration/state_store.py`
- Test: `tests/lanes/test_models.py`
- Test: `tests/lanes/test_state_store.py`

- [ ] **Step 1: Add the lane dataclasses and literals**

Create `src/specify_cli/lanes/models.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


LaneLifecycleState = Literal[
    "draft",
    "specified",
    "planned",
    "tasked",
    "implementing",
    "integrating",
    "completed",
    "abandoned",
]

LaneRecoveryState = Literal[
    "resumable",
    "uncertain",
    "blocked",
    "completed",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class LaneRecord:
    lane_id: str
    feature_id: str
    feature_dir: str
    branch_name: str
    worktree_path: str
    lifecycle_state: LaneLifecycleState = "draft"
    recovery_state: LaneRecoveryState = "blocked"
    last_command: str = ""
    last_stable_checkpoint: str = ""
    recovery_reason: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class LaneLease:
    lane_id: str
    session_id: str
    owner_command: str
    acquired_at: str
    renew_until: str
    repo_root: str
    runtime_token: str = ""


@dataclass(slots=True)
class LaneResolutionCandidate:
    lane_id: str
    feature_id: str
    feature_dir: str
    last_command: str
    recovery_state: LaneRecoveryState
    last_stable_checkpoint: str
    recovery_reason: str = ""


@dataclass(slots=True)
class LaneResolutionResult:
    mode: Literal["resume", "choose", "start", "blocked"]
    selected_lane_id: str = ""
    reason: str = ""
    candidates: list[LaneResolutionCandidate] = field(default_factory=list)
```

- [ ] **Step 2: Add lane persistence helpers**

Create `src/specify_cli/lanes/state_store.py` with:

```python
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import LaneLease, LaneRecord


def lanes_root(project_root: Path) -> Path:
    return project_root / ".specify" / "lanes"


def lane_index_path(project_root: Path) -> Path:
    return lanes_root(project_root) / "index.json"


def lane_dir(project_root: Path, lane_id: str) -> Path:
    return lanes_root(project_root) / lane_id


def lane_record_path(project_root: Path, lane_id: str) -> Path:
    return lane_dir(project_root, lane_id) / "lane.json"


def lane_events_path(project_root: Path, lane_id: str) -> Path:
    return lane_dir(project_root, lane_id) / "events.ndjson"


def lane_lease_path(project_root: Path, lane_id: str) -> Path:
    return lane_dir(project_root, lane_id) / "lease.json"


def lane_recovery_path(project_root: Path, lane_id: str) -> Path:
    return lane_dir(project_root, lane_id) / "recovery.json"


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_lane_index(project_root: Path, payload: dict[str, object]) -> Path:
    return _write_json(lane_index_path(project_root), payload)


def read_lane_index(project_root: Path) -> dict[str, object] | None:
    return _read_json(lane_index_path(project_root))


def write_lane_record(project_root: Path, lane: LaneRecord) -> Path:
    return _write_json(lane_record_path(project_root, lane.lane_id), asdict(lane))


def read_lane_record(project_root: Path, lane_id: str) -> LaneRecord | None:
    payload = _read_json(lane_record_path(project_root, lane_id))
    if payload is None:
        return None
    return LaneRecord(**payload)


def write_lane_lease(project_root: Path, lease: LaneLease) -> Path:
    return _write_json(lane_lease_path(project_root, lease.lane_id), asdict(lease))


def read_lane_lease(project_root: Path, lane_id: str) -> LaneLease | None:
    payload = _read_json(lane_lease_path(project_root, lane_id))
    if payload is None:
        return None
    return LaneLease(**payload)


def append_lane_event(project_root: Path, lane_id: str, payload: dict[str, object]) -> Path:
    path = lane_events_path(project_root, lane_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return path
```

- [ ] **Step 3: Export lane APIs**

Create `src/specify_cli/lanes/__init__.py` with:

```python
from .models import (
    LaneLease,
    LaneLifecycleState,
    LaneRecord,
    LaneRecoveryState,
    LaneResolutionCandidate,
    LaneResolutionResult,
)
from .state_store import (
    append_lane_event,
    lane_index_path,
    lane_record_path,
    read_lane_index,
    read_lane_lease,
    read_lane_record,
    write_lane_index,
    write_lane_lease,
    write_lane_record,
)

__all__ = [
    "LaneLease",
    "LaneLifecycleState",
    "LaneRecord",
    "LaneRecoveryState",
    "LaneResolutionCandidate",
    "LaneResolutionResult",
    "append_lane_event",
    "lane_index_path",
    "lane_record_path",
    "read_lane_index",
    "read_lane_lease",
    "read_lane_record",
    "write_lane_index",
    "write_lane_lease",
    "write_lane_record",
]
```

- [ ] **Step 4: Add lane recovery snapshots and index rebuild helpers**

Extend `src/specify_cli/lanes/state_store.py` with:

```python
def write_lane_recovery(project_root: Path, lane_id: str, payload: dict[str, object]) -> Path:
    return _write_json(lane_recovery_path(project_root, lane_id), payload)


def read_lane_recovery(project_root: Path, lane_id: str) -> dict[str, object] | None:
    return _read_json(lane_recovery_path(project_root, lane_id))


def rebuild_lane_index(project_root: Path) -> dict[str, object]:
    lanes: list[dict[str, object]] = []
    root = lanes_root(project_root)
    if root.exists():
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            record = read_lane_record(project_root, child.name)
            if record is None:
                continue
            lanes.append(
                {
                    "lane_id": record.lane_id,
                    "feature_id": record.feature_id,
                    "feature_dir": record.feature_dir,
                    "last_command": record.last_command,
                    "recovery_state": record.recovery_state,
                }
            )
    payload = {"lanes": lanes}
    write_lane_index(project_root, payload)
    return payload
```

Also export `write_lane_recovery`, `read_lane_recovery`, and
`rebuild_lane_index` from `src/specify_cli/lanes/__init__.py`.

- [ ] **Step 5: Reuse generic JSON write helpers without duplicating semantics**

Update `src/specify_cli/orchestration/state_store.py` to keep `write_json` and `read_json` as the shared low-level helpers and leave lane-specific path logic in `src/specify_cli/lanes/state_store.py`.

No behavior change beyond ensuring the lane store can import or mirror the same JSON newline semantics.

- [ ] **Step 6: Extend orchestration dispatch-shape literals for recovery-aware fallback**

Update `src/specify_cli/orchestration/models.py` with:

```python
DispatchShape = Literal["one-subagent", "parallel-subagents", "leader-inline-fallback"]
_CANONICAL_DISPATCH_SHAPES = frozenset(
    {"one-subagent", "parallel-subagents", "leader-inline-fallback"}
)
```

Do not remove the existing ordinary-command checks or `should_attempt_one_subagent`;
only extend the canonical dispatch-shape vocabulary so recorded local fallback
state can be represented cleanly.

- [ ] **Step 7: Run lane model/state tests**

Run:

```bash
pytest tests/lanes/test_models.py tests/lanes/test_state_store.py -q
```

Expected:

- PASS for model literals, defaults, and round-trip persistence

- [ ] **Step 8: Commit the lane model/state layer**

```bash
git add src/specify_cli/lanes src/specify_cli/orchestration/state_store.py tests/lanes/test_models.py tests/lanes/test_state_store.py
git commit -m "feat: add lane state primitives"
```

### Task 3: Add lease handling and reconcile logic

**Files:**
- Create: `src/specify_cli/lanes/lease.py`
- Create: `src/specify_cli/lanes/reconcile.py`
- Modify: `src/specify_cli/hooks/checkpoint_serializers.py`
- Modify: `src/specify_cli/hooks/session_state.py`
- Test: `tests/lanes/test_reconcile.py`
- Test: `tests/lanes/test_lease.py`
- Test: `tests/hooks/test_session_state_hooks.py`

- [ ] **Step 1: Add lease expiry helpers**

Create `src/specify_cli/lanes/lease.py` with:

```python
from __future__ import annotations

from datetime import datetime, timezone

from .models import LaneLease


def lane_lease_expired(lease: LaneLease, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    return datetime.fromisoformat(lease.renew_until) <= current


def validate_lane_write_lease(
    lease: LaneLease | None,
    *,
    requester_session_id: str,
    now: datetime | None = None,
) -> str:
    if lease is None:
        return "available"
    if lease.session_id == requester_session_id:
        return "owned"
    if lane_lease_expired(lease, now=now):
        return "expired"
    return "blocked"
```

- [ ] **Step 2: Reuse checkpoint serializers to inspect workflow state and tracker truth**

Update `src/specify_cli/hooks/checkpoint_serializers.py` only as needed so `serialize_workflow_state` and `serialize_implement_tracker` remain the canonical parsing helpers consumed by lane reconcile logic.

Do not fork a second parser.

- [ ] **Step 3: Add the reconcile classifier**

Create `src/specify_cli/lanes/reconcile.py` with:

```python
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from specify_cli.hooks.checkpoint_serializers import (
    serialize_implement_tracker,
    serialize_workflow_state,
)

from .models import LaneRecord
from .state_store import read_lane_lease


def reconcile_lane(project_root: Path, lane: LaneRecord, *, command_name: str) -> LaneRecord:
    feature_dir = project_root / lane.feature_dir
    workflow_path = feature_dir / "workflow-state.md"
    tracker_path = feature_dir / "implement-tracker.md"

    updated = replace(lane)

    if command_name == "implement":
        if not workflow_path.exists() or not tracker_path.exists():
            updated.recovery_state = "blocked"
            updated.recovery_reason = "missing implement stage artifacts"
            return updated

        workflow = serialize_workflow_state(workflow_path)
        tracker = serialize_implement_tracker(tracker_path)
        lease = read_lane_lease(project_root, lane.lane_id)

        next_command = str(workflow.get("next_command") or "")
        tracker_status = str(tracker.get("status") or "")

        if next_command != "/sp.implement" and tracker_status not in {"blocked", "resolved"}:
            updated.recovery_state = "uncertain"
            updated.recovery_reason = f"next_command {next_command} conflicts with tracker status {tracker_status}"
            return updated

        if lease is not None:
            from .lease import lane_lease_expired

            if lane_lease_expired(lease) and tracker_status not in {"blocked", "resolved"} and not tracker.get("next_action"):
                updated.recovery_state = "uncertain"
                updated.recovery_reason = "expired lease without reliable next action"
                return updated

        updated.recovery_state = "resumable"
        updated.last_stable_checkpoint = str(tracker.get("current_batch") or "implement-ready")
        updated.recovery_reason = ""
        return updated

    if not workflow_path.exists():
        updated.recovery_state = "blocked"
        updated.recovery_reason = "missing workflow-state.md"
        return updated

    workflow = serialize_workflow_state(workflow_path)
    next_command = str(workflow.get("next_command") or "")
    expected = f"/sp.{command_name}"
    if next_command and next_command != expected:
        updated.recovery_state = "uncertain"
        updated.recovery_reason = f"next_command {next_command} does not match {expected}"
        return updated

    updated.recovery_state = "resumable"
    updated.last_stable_checkpoint = str(workflow.get("next_action") or expected)
    updated.recovery_reason = ""
    return updated
```

- [ ] **Step 4: Persist reconcile summaries to lane recovery state**

After each reconcile decision, write a summary through
`write_lane_recovery(project_root, lane.lane_id, payload)` with:

- `command_name`
- `recovery_state`
- `recovery_reason`
- `last_stable_checkpoint`

This keeps `recovery.json` useful for diagnostics and later index rebuild.

- [ ] **Step 5: Extend session-state hook to expose lane uncertainty cleanly**

Update `src/specify_cli/hooks/session_state.py` so the `implement` branch continues warning on workflow/tracker divergence and is easy to reuse from lane reconcile without duplicating logic. Preserve the current warnings payload shape.

- [ ] **Step 6: Run reconcile and lease tests**

Run:

```bash
pytest tests/lanes/test_reconcile.py tests/lanes/test_lease.py tests/hooks/test_session_state_hooks.py -q
```

Expected:

- PASS for `resumable`, `uncertain`, and `blocked` classify cases
- PASS for lease expiry and write-lock behavior

- [ ] **Step 7: Commit the reconcile layer**

```bash
git add src/specify_cli/lanes/lease.py src/specify_cli/lanes/reconcile.py src/specify_cli/hooks/checkpoint_serializers.py src/specify_cli/hooks/session_state.py tests/lanes/test_reconcile.py tests/lanes/test_lease.py tests/hooks/test_session_state_hooks.py
git commit -m "feat: add lane reconcile and lease checks"
```

### Task 4: Add lane resolution and root-level command routing

**Files:**
- Create: `src/specify_cli/lanes/resolution.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/debug/context.py`
- Test: `tests/lanes/test_resolution.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add lane resolution logic**

Create `src/specify_cli/lanes/resolution.py` with:

```python
from __future__ import annotations

from pathlib import Path

from .models import LaneResolutionCandidate, LaneResolutionResult
from .reconcile import reconcile_lane
from .state_store import read_lane_index, read_lane_record


def _candidate_lane_ids(project_root: Path) -> list[str]:
    index = read_lane_index(project_root) or {}
    lanes = index.get("lanes", [])
    if isinstance(lanes, list):
        return [str(item.get("lane_id")) for item in lanes if isinstance(item, dict) and item.get("lane_id")]
    return []


def resolve_lane_for_command(project_root: Path, *, command_name: str) -> LaneResolutionResult:
    candidates: list[LaneResolutionCandidate] = []

    for lane_id in _candidate_lane_ids(project_root):
        lane = read_lane_record(project_root, lane_id)
        if lane is None:
            continue
        if lane.last_command and lane.last_command != command_name and command_name != "auto":
            continue

        reconciled = reconcile_lane(project_root, lane, command_name=lane.last_command or command_name)
        candidates.append(
            LaneResolutionCandidate(
                lane_id=reconciled.lane_id,
                feature_id=reconciled.feature_id,
                feature_dir=reconciled.feature_dir,
                last_command=reconciled.last_command,
                recovery_state=reconciled.recovery_state,
                last_stable_checkpoint=reconciled.last_stable_checkpoint,
                recovery_reason=reconciled.recovery_reason,
            )
        )

    resumable = [candidate for candidate in candidates if candidate.recovery_state == "resumable"]
    uncertain = [candidate for candidate in candidates if candidate.recovery_state == "uncertain"]

    if len(resumable) == 1 and not uncertain:
        return LaneResolutionResult(
            mode="resume",
            selected_lane_id=resumable[0].lane_id,
            reason="unique-safe-candidate",
            candidates=candidates,
        )
    if resumable or uncertain:
        return LaneResolutionResult(
            mode="choose",
            reason="ambiguous-or-uncertain",
            candidates=candidates,
        )
    return LaneResolutionResult(mode="start", reason="no-resumable-candidate", candidates=candidates)
```

- [ ] **Step 2: Replace newest-`tasks.md` active-feature fallback with lane-aware lookup**

Update `src/specify_cli/debug/context.py`:

```python
from specify_cli.lanes.resolution import resolve_lane_for_command


def find_active_feature(self) -> Optional[Path]:
    resolved = resolve_lane_for_command(self.root_dir, command_name="auto")
    if resolved.mode == "resume" and resolved.selected_lane_id:
        lane = next(
            candidate for candidate in resolved.candidates if candidate.lane_id == resolved.selected_lane_id
        )
        return self.root_dir / lane.feature_dir
    return None
```

Keep the old newest-`tasks.md` scan only as an explicit fallback when there is no lane registry at all.

- [ ] **Step 3: Add CLI helpers that normalize `--feature-dir` through lane resolution**

In `src/specify_cli/__init__.py`, add a helper near other CLI utility functions:

```python
def _resolve_feature_dir_for_command(
    project_root: Path,
    *,
    command_name: str,
    feature_dir: str | None,
) -> Path | None:
    if feature_dir:
        resolved = Path(feature_dir)
        return resolved if resolved.is_absolute() else (project_root / resolved).resolve()

    from specify_cli.lanes.resolution import resolve_lane_for_command
    from specify_cli.lanes.state_store import read_lane_record

    lane_result = resolve_lane_for_command(project_root, command_name=command_name)
    if lane_result.mode == "resume" and lane_result.selected_lane_id:
        lane = read_lane_record(project_root, lane_result.selected_lane_id)
        if lane is not None:
            return (project_root / lane.feature_dir).resolve()
    return None
```

- [ ] **Step 4: Add CLI helpers for lane registration and machine-readable resolution**

In `src/specify_cli/__init__.py`, add a lane sub-app or equivalent grouped CLI
surface with:

```python
@lane_app.command("register")
def lane_register(
    feature_dir: str,
    branch: str,
    worktree: str,
    command_name: str,
    lane_id: str = typer.Option(..., "--lane-id"),
):
    ...


@lane_app.command("resolve")
def lane_resolve(
    command_name: str = typer.Option(..., "--command"),
    feature_dir: str | None = typer.Option(None, "--feature-dir"),
):
    ...
```

Required behavior:

- `lane register` writes or updates `LaneRecord`, appends an event, and rebuilds
  the lane index
- `lane resolve` returns JSON describing `resume`, `choose`, `start`, or
  `blocked` plus candidate summaries

- [ ] **Step 5: Route root-level resumable commands through the helper**

Update the CLI entrypoints that already accept `--feature-dir` or infer active feature:

- `sp-auto` routing helpers
- implement-related CLI surfaces that currently expect `feature_dir`
- any status/closeout helpers that currently do "active feature" detection

Minimum rule:

- explicit `--feature-dir` still wins
- otherwise use lane resolution
- if multiple candidates or uncertainty exist, surface a concise blocking message instead of guessing

- [ ] **Step 6: Add CLI regression tests for unique resume vs ambiguous resume**

Add to `tests/integrations/test_cli.py`:

```python
def test_root_level_feature_resolution_prefers_unique_resumable_lane(tmp_path, monkeypatch):
    from specify_cli.lanes.models import LaneRecord
    from specify_cli.lanes.state_store import write_lane_index, write_lane_record
    from specify_cli.__init__ import _resolve_feature_dir_for_command

    lane = LaneRecord(
        lane_id="lane-001",
        feature_id="001-demo",
        feature_dir="specs/001-demo",
        branch_name="001-demo",
        worktree_path=".specify/lanes/worktrees/lane-001",
        recovery_state="resumable",
        last_command="implement",
    )
    write_lane_record(tmp_path, lane)
    write_lane_index(tmp_path, {"lanes": [{"lane_id": "lane-001"}]})

    resolved = _resolve_feature_dir_for_command(tmp_path, command_name="implement", feature_dir=None)

    assert resolved == (tmp_path / "specs" / "001-demo").resolve()
```

Also add an ambiguous case that returns `None` and requires user choice.

- [ ] **Step 7: Run routing tests**

Run:

```bash
pytest tests/lanes/test_resolution.py tests/integrations/test_cli.py -q
```

Expected:

- PASS for unique safe resume
- PASS for ambiguous/uncertain stop behavior

- [ ] **Step 8: Commit lane resolution**

```bash
git add src/specify_cli/lanes/resolution.py src/specify_cli/__init__.py src/specify_cli/debug/context.py tests/lanes/test_resolution.py tests/integrations/test_cli.py
git commit -m "feat: route resumable commands through lane resolution"
```

### Task 5: Add branch/worktree automation for lanes

**Files:**
- Create: `src/specify_cli/lanes/worktree.py`
- Modify: `src/specify_cli/codex_team/worktree_ops.py`
- Modify: `scripts/bash/create-new-feature.sh`
- Modify: `scripts/powershell/create-new-feature.ps1`
- Test: `tests/codex_team/test_worktree_ops.py`
- Test: `tests/codex_team/test_runtime_bridge.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add lane worktree path helpers**

Create `src/specify_cli/lanes/worktree.py` with:

```python
from __future__ import annotations

import os
from pathlib import Path


LANE_WORKTREE_RELATIVE_ROOT = Path(".specify") / "lanes" / "worktrees"


def lane_worktrees_root(project_root: Path) -> Path:
    return project_root / LANE_WORKTREE_RELATIVE_ROOT


def _ensure_within_lane_root(project_root: Path, candidate: Path) -> Path:
    root = lane_worktrees_root(project_root).resolve(strict=False)
    resolved = candidate.resolve(strict=False)
    if os.path.commonpath([str(root), str(resolved)]) != str(root):
        raise ValueError(f"Lane worktree path {candidate} escapes {root}")
    return candidate


def lane_worktree_path(project_root: Path, *, lane_id: str) -> Path:
    return _ensure_within_lane_root(project_root, lane_worktrees_root(project_root) / lane_id)
```

- [ ] **Step 2: Re-export lane worktree path from Codex worktree helpers**

Update `src/specify_cli/codex_team/worktree_ops.py`:

```python
from specify_cli.lanes.worktree import lane_worktree_path

__all__ = [
    "WORKTREE_RELATIVE_ROOT",
    "codex_team_worktrees_root",
    "worker_worktree_path",
    "lane_worktree_path",
]
```

- [ ] **Step 3: Extend create-new-feature scripts to emit lane metadata fields**

Update both `scripts/bash/create-new-feature.sh` and `scripts/powershell/create-new-feature.ps1` so their JSON output includes:

- `BRANCH_NAME`
- `FEATURE_DIR`
- `SPEC_FILE`
- `LANE_ID`
- `LANE_WORKTREE`

The lane worktree should default to:

- `.specify/lanes/worktrees/<branch-name>`

Do not create the worktree in dry-run mode.

- [ ] **Step 4: Add tests for lane worktree output and path safety**

Add to `tests/codex_team/test_worktree_ops.py`:

```python
from specify_cli.lanes.worktree import lane_worktree_path


def test_lane_worktree_path_rejects_escape(codex_team_project_root):
    from pathlib import Path
    import pytest

    with pytest.raises(ValueError):
        lane_worktree_path(codex_team_project_root, lane_id="../escape")
```

Add to the timestamp/create-feature script coverage in `tests/test_alignment_templates.py` or adjacent script tests:

```python
assert "LANE_ID" in sh_create
assert "LANE_WORKTREE" in sh_create
assert "LANE_ID" in ps_create
assert "LANE_WORKTREE" in ps_create
```

- [ ] **Step 5: Run worktree/script tests**

Run:

```bash
pytest tests/codex_team/test_worktree_ops.py tests/codex_team/test_runtime_bridge.py tests/test_alignment_templates.py -q
```

Expected:

- PASS for safe lane worktree path generation
- PASS for create-feature scripts exposing lane metadata

- [ ] **Step 6: Commit the lane worktree layer**

```bash
git add src/specify_cli/lanes/worktree.py src/specify_cli/codex_team/worktree_ops.py scripts/bash/create-new-feature.sh scripts/powershell/create-new-feature.ps1 tests/codex_team/test_worktree_ops.py tests/codex_team/test_runtime_bridge.py tests/test_alignment_templates.py
git commit -m "feat: add lane worktree automation"
```

### Task 6: Teach workflow state and command templates about lanes and safe resume

**Files:**
- Modify: `templates/workflow-state-template.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/auto.md`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_extension_skills.py`
- Test: `tests/integrations/test_integration_claude.py`
- Test: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Extend workflow-state template with lane-aware fields**

Add these fields to `templates/workflow-state-template.md`:

```markdown
## Lane Context

- lane_id: [stable lane identifier for this feature workflow]
- branch_name: [branch bound to this lane]
- worktree_path: [isolated worktree bound to this lane]
- recovery_state: `resumable | uncertain | blocked | completed`
- last_stable_checkpoint: [most recent durable resume point]
```

Keep the existing sections intact; this is an additive extension, not a rewrite.

- [ ] **Step 2: Update `sp-specify` to create or resume lane state explicitly**

In `templates/commands/specify.md`, add guidance that:

- `sp-specify` creates or resumes lane metadata after `FEATURE_DIR` is known
- after `create-new-feature.*` returns `LANE_ID` and `LANE_WORKTREE`, call `{{specify-subcmd:lane register --lane-id "$LANE_ID" --feature-dir "$FEATURE_DIR" --branch "$BRANCH_NAME" --worktree "$LANE_WORKTREE" --command specify}}`
- new feature intent creates a new lane
- root-level recovery may resume an existing `specify`-domain lane only when it is uniquely safe
- lane metadata and workflow-state must be kept in sync

- [ ] **Step 3: Update `sp-plan`, `sp-tasks`, and `sp-implement` to treat lane resolution as the resume gate**

Add to each template:

- if `--feature-dir` is omitted, resolve the lane by command semantics
- use `{{specify-subcmd:lane resolve --command <command-name>}}` as the machine-readable resolution surface when available
- if multiple candidates exist, do not guess
- if the lane is `uncertain`, stop and surface the conflict instead of continuing

For `templates/commands/implement.md`, also add:

- `implement-tracker.md` and lane reconcile must agree before execution resumes

- [ ] **Step 4: Update `sp-auto` to prefer lane-aware command-semantic routing**

In `templates/commands/auto.md`, replace pure state-surface recency framing with:

- lane registry discovery
- command-semantic candidate filtering
- reconcile before resume
- unique-safe-candidate auto-resume only
- minimal choose flow when multiple or uncertain candidates exist

Preserve the rule that `sp-auto` does not rewrite downstream workflow-state to `/sp-auto`.

- [ ] **Step 5: Add template regressions**

Add to `tests/test_alignment_templates.py`:

```python
def test_workflow_state_template_includes_lane_context():
    content = _read("templates/workflow-state-template.md")
    assert "## Lane Context" in content
    assert "lane_id:" in content
    assert "recovery_state:" in content
    assert "last_stable_checkpoint:" in content


def test_auto_template_requires_reconcile_before_resume():
    content = _read("templates/commands/auto.md").lower()
    assert "lane registry" in content
    assert "reconcile" in content
    assert "unique safe" in content or "exactly one `resumable`" in content
    assert "do not guess" in content
```

Add equivalent generated-surface assertions in `tests/test_extension_skills.py`, `tests/integrations/test_integration_claude.py`, and `tests/integrations/test_integration_codex.py`.

- [ ] **Step 6: Run template and integration tests**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_extension_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q
```

Expected:

- PASS for lane-aware workflow-state and auto-routing guidance

- [ ] **Step 7: Commit template updates**

```bash
git add templates/workflow-state-template.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/commands/auto.md tests/test_alignment_templates.py tests/test_extension_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py
git commit -m "docs: teach workflow templates about lane recovery"
```

### Task 7: Add `sp-integrate` closeout workflow and lane completion flow

**Files:**
- Create: `src/specify_cli/lanes/integration.py`
- Modify: `src/specify_cli/__init__.py`
- Create: `templates/commands/integrate.md`
- Test: `tests/lanes/test_integration.py`
- Test: `tests/integrations/test_cli.py`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_base_skills.py`
- Test: `tests/integrations/test_integration_base_toml.py`

- [ ] **Step 1: Add the integration candidate collector**

Create `src/specify_cli/lanes/integration.py` with:

```python
from __future__ import annotations

from pathlib import Path

from .models import LaneRecord
from .state_store import read_lane_index, read_lane_record, write_lane_record


def collect_integration_candidates(project_root: Path) -> list[LaneRecord]:
    payload = read_lane_index(project_root) or {}
    candidates: list[LaneRecord] = []
    for item in payload.get("lanes", []):
        if not isinstance(item, dict) or not item.get("lane_id"):
            continue
        lane = read_lane_record(project_root, str(item["lane_id"]))
        if lane is None:
            continue
        if lane.recovery_state == "completed" or (
            lane.lifecycle_state == "implementing" and lane.recovery_state == "completed"
        ):
            candidates.append(lane)
    return candidates


def mark_lane_integrated(project_root: Path, lane: LaneRecord) -> LaneRecord:
    lane.lifecycle_state = "completed"
    lane.recovery_state = "completed"
    lane.last_command = "integrate"
    write_lane_record(project_root, lane)
    return lane
```

- [ ] **Step 2: Add a lightweight CLI surface for `sp-integrate`**

In `src/specify_cli/__init__.py`, add a Typer command:

```python
@app.command("integrate")
def integrate(feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory to close out")):
    ...
```

First release behavior:

- if `--feature-dir` is passed, resolve the matching lane and print readiness
- otherwise list integration candidates
- do not auto-merge code
- mark a lane completed only after explicit readiness handling is wired and validated

- [ ] **Step 3: Add the shared command template**

Create `templates/commands/integrate.md` with a minimal contract:

```markdown
---
description: Use when one or more independent feature lanes have completed implementation and need a dedicated closeout workflow before mainline integration.
---

## Objective

Use `sp-integrate` to discover completed lanes, run integration prechecks, surface drift or overlap risk, and close the lane cleanly.

## Guardrails

- Do not fold this workflow into `sp-implement`.
- Do not guess merge order when conflicts or overlap are unclear.
- Treat completed lane state and verification evidence as prerequisites to closeout.
```

- [ ] **Step 4: Add CLI and collector tests**

Add to `tests/integrations/test_cli.py`:

```python
def test_integrate_command_is_registered(runner):
    result = runner.invoke(app, ["integrate", "--help"])
    assert result.exit_code == 0
    assert "closeout" in result.output.lower()
```

Use the existing `tests/lanes/test_integration.py` collector assertions from Task 1 to cover candidate discovery.

Add generated-surface regressions that assert `sp-integrate` is emitted into:

- markdown integrations
- skills-based integrations
- TOML integrations

- [ ] **Step 5: Run integration workflow tests**

Run:

```bash
pytest tests/lanes/test_integration.py tests/integrations/test_cli.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected:

- PASS for candidate discovery
- PASS for `integrate` command registration and help surface

- [ ] **Step 6: Commit `sp-integrate`**

```bash
git add src/specify_cli/lanes/integration.py src/specify_cli/__init__.py templates/commands/integrate.md tests/lanes/test_integration.py tests/integrations/test_cli.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
git commit -m "feat: add integrate workflow for lane closeout"
```

### Task 8: Update docs and verify the full end state

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-map/root/ARCHITECTURE.md`
- Modify: `templates/project-map/root/WORKFLOWS.md`
- Modify: `templates/project-map/root/CONVENTIONS.md`
- Modify: `docs/superpowers/plans/2026-05-02-parallel-lane-workflow-implementation.md`

- [ ] **Step 1: Update public docs to replace branch-only active-feature assumptions**

Update:

- `docs/quickstart.md`
- `README.md`
- `PROJECT-HANDBOOK.md`

Required changes:

- branch name is no longer the sole source of active feature truth once parallel lanes exist
- root-level `sp-*` commands may resolve by lane registry plus reconcile
- `sp-auto` only resumes when there is one uniquely safe candidate
- `sp-integrate` is the dedicated closeout workflow

- [ ] **Step 2: Update project-map/root docs to describe lanes as the concurrency boundary**

Update:

- `templates/project-map/root/ARCHITECTURE.md`
- `templates/project-map/root/WORKFLOWS.md`
- `templates/project-map/root/CONVENTIONS.md`

Required topics:

- lane-local durable state
- registry as cache, not truth
- reconcile-before-resume
- crash-consistency red line
- branch/worktree isolation

- [ ] **Step 3: Run the focused regression suite**

Run:

```bash
pytest tests/lanes -q
pytest tests/hooks/test_session_state_hooks.py tests/hooks/test_checkpoint_hooks.py tests/hooks/test_statusline_hooks.py tests/hooks/test_preflight_hooks.py -q
pytest tests/orchestration/test_models.py tests/orchestration/test_state_store.py -q
pytest tests/codex_team/test_worktree_ops.py tests/codex_team/test_auto_dispatch.py tests/codex_team/test_runtime_bridge.py -q
pytest tests/test_alignment_templates.py tests/test_extension_skills.py tests/integrations/test_cli.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q
```

Expected:

- PASS across lane runtime, hooks, orchestration, worktree helpers, templates, and integration surfaces

- [ ] **Step 4: Run a broader regression pass**

Run:

```bash
uv run --extra test pytest tests/lanes tests/hooks tests/orchestration tests/codex_team tests/integrations -q
```

Expected:

- PASS or only pre-existing unrelated failures

- [ ] **Step 5: Record verification notes in this plan**

Append a `## Verification Notes` section to this file with:

- commands executed
- whether the full pass succeeded
- any scoped follow-up risks

- [ ] **Step 6: Commit documentation and verification notes**

```bash
git add README.md docs/quickstart.md PROJECT-HANDBOOK.md templates/project-map/root/ARCHITECTURE.md templates/project-map/root/WORKFLOWS.md templates/project-map/root/CONVENTIONS.md docs/superpowers/plans/2026-05-02-parallel-lane-workflow-implementation.md
git commit -m "docs: describe parallel lane workflow model"
```

## Verification Notes

- `pytest tests/lanes/test_models.py tests/lanes/test_state_store.py tests/lanes/test_reconcile.py tests/lanes/test_resolution.py tests/lanes/test_lease.py tests/lanes/test_integration.py tests/orchestration/test_models.py tests/hooks/test_session_state_hooks.py tests/codex_team/test_worktree_ops.py -q`
- `pytest tests/lanes/test_reconcile.py tests/lanes/test_lease.py tests/hooks/test_session_state_hooks.py -q`
- `pytest tests/lanes/test_resolution.py tests/integrations/test_cli.py -q`
- `pytest tests/codex_team/test_worktree_ops.py tests/codex_team/test_runtime_bridge.py tests/test_alignment_templates.py -q`
- `pytest tests/test_alignment_templates.py tests/test_extension_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q`
- `pytest tests/lanes -q`
- `pytest tests/hooks/test_session_state_hooks.py tests/hooks/test_checkpoint_hooks.py tests/hooks/test_statusline_hooks.py tests/hooks/test_preflight_hooks.py -q`
- `pytest tests/orchestration/test_models.py tests/orchestration/test_state_store.py -q`
- `pytest tests/codex_team/test_worktree_ops.py tests/codex_team/test_auto_dispatch.py tests/codex_team/test_runtime_bridge.py -q`
- `pytest tests/test_alignment_templates.py tests/test_extension_skills.py tests/integrations/test_cli.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q`
- `uv run --extra test pytest tests/lanes tests/hooks tests/orchestration tests/codex_team tests/integrations -q`

Result:

- The focused lane runtime, hook, orchestration, CLI, template, Codex team, and integration suites passed after the lane runtime, lane CLI surface, template guidance, and integration-hint updates were completed.
- `uv run --extra test pytest tests/lanes tests/hooks tests/orchestration tests/codex_team tests/integrations -q` timed out in one combined pass on this machine, so the same coverage was verified by split suites instead:
  - `pytest tests/lanes tests/hooks tests/orchestration -q`
  - `pytest tests/codex_team -q`
  - `pytest tests/integrations -q`
- Final verification status: passing for the exercised lane runtime, Codex team, and integration surfaces used by this change set.
