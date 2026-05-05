import json
from pathlib import Path
import re
import time
import os
import tempfile

import pytest

from specify_cli.codex_team.auto_dispatch import (
    AutoDispatchError,
    AutoDispatchUnavailableError,
    complete_dispatched_batch,
    find_next_ready_parallel_batch,
    parse_tasks_markdown,
    run_notify_hook,
    route_ready_parallel_batch,
)
from specify_cli.codex_team.state_paths import (
    batch_record_path,
    dispatch_record_path,
    result_record_path,
    runtime_session_path,
    task_record_path,
    worker_heartbeat_path,
)
from specify_cli.execution import worker_task_result_payload
from specify_cli.execution.result_schema import RuleAcknowledgement, ValidationResult, WorkerTaskResult
from specify_cli.codex_team.task_ops import TaskOpsError, claim_task, get_task, transition_task_status


@pytest.fixture(autouse=True)
def _enable_legacy_executor(monkeypatch):
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_EXECUTOR", "legacy-heartbeat-runtime")


def _write_feature_tasks(project_root: Path, content: str) -> Path:
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (project_root / ".specify" / "memory").mkdir(parents=True, exist_ok=True)
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for delegated public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Implementation Constitution",
                "",
                "### Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "### Forbidden Implementation Drift",
                "",
                "- Do not create a parallel auth stack",
            ]
        ),
        encoding="utf-8",
    )
    normalized_lines: list[str] = []
    for line in content.splitlines():
        match = re.match(r"^(- \[[ xX]\] (T\d+)(?: \[P\])? .+)$", line)
        if match and "/" not in line:
            normalized_lines.append(f"{match.group(1)} in src/{match.group(2).lower()}.py")
        else:
            normalized_lines.append(line)
    normalized = "\n".join(normalized_lines)
    if "## Validation Gates" not in normalized:
        normalized = (
            normalized.rstrip()
            + "\n\n## Validation Gates\n\n- pytest tests/unit/test_auth_service.py -q\n"
        )
    tasks_path = feature_dir / "tasks.md"
    tasks_path.write_text(normalized, encoding="utf-8")
    return feature_dir


def _write_fake_agent_teams_runtime_cli(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "import json, os, sys",
                "from pathlib import Path",
                "",
                "payload = json.loads(sys.stdin.read())",
                "state_root = Path(os.environ['SPECIFY_TEAM_STATE_ROOT'])",
                "team_name = payload['teamName']",
                "tasks_dir = state_root / 'team' / team_name / 'tasks'",
                "tasks_dir.mkdir(parents=True, exist_ok=True)",
                "marker_start = 'BEGIN_WORKER_TASK_RESULT_JSON'",
                "marker_end = 'END_WORKER_TASK_RESULT_JSON'",
                "for index, task in enumerate(payload['tasks'], start=1):",
                "    description = task['description']",
                "    start = description.index(marker_start) + len(marker_start)",
                "    end = description.index(marker_end)",
                "    payload_text = description[start:end].strip()",
                "    result_payload = json.loads(payload_text)",
                "    result_payload['status'] = 'success'",
                "    for item in result_payload.get('validation_results', []):",
                "        item['status'] = 'passed'",
                "        item['output'] = '1 passed'",
                "    paths_read = [line[2:] for line in description.splitlines() if line.startswith('- src/')]",
                "    result_payload['rule_acknowledgement'] = {",
                "        'required_references_read': True,",
                "        'forbidden_drift_respected': True,",
                "        'context_bundle_read': True,",
                "        'paths_read': paths_read,",
                "        'critical_notes': ['validated fake runtime result for contract test'],",
                "    }",
                "    result_text = json.dumps(result_payload, ensure_ascii=False, indent=2)",
                "    task_payload = {",
                "        'id': str(index),",
                "        'subject': task['subject'],",
                "        'description': description,",
                "        'status': 'completed',",
                "        'result': f'{marker_start}\\n{result_text}\\n{marker_end}',",
                "        'created_at': '2026-04-25T00:00:00Z',",
                "    }",
                "    (tasks_dir / f'task-{index}.json').write_text(json.dumps(task_payload, ensure_ascii=False, indent=2), encoding='utf-8')",
                "json.dump({'status': 'completed', 'teamName': team_name, 'taskResults': [], 'duration': 0, 'workerCount': len(payload['tasks'])}, sys.stdout)",
            ]
        ),
        encoding="utf-8",
    )


def _wait_for_result_files(project_root: Path, request_ids: list[str], timeout_s: float = 8.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if all(result_record_path(project_root, request_id).exists() for request_id in request_ids):
            return
        time.sleep(0.1)
    missing = [request_id for request_id in request_ids if not result_record_path(project_root, request_id).exists()]
    raise AssertionError(f"timed out waiting for canonical result files: {', '.join(missing)}")


def test_parse_tasks_markdown_finds_parallel_batches_and_statuses(codex_team_project_root: Path):
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge
""",
    )

    parsed = parse_tasks_markdown(feature_dir / "tasks.md")

    assert [task.task_id for task in parsed.tasks] == ["T001", "T002", "T003"]
    assert parsed.tasks[0].completed is True
    assert parsed.tasks[1].parallel is True
    assert parsed.parallel_batches[0].batch_name == "Parallel Batch 1.1"
    assert parsed.parallel_batches[0].task_ids == ["T002", "T003"]


def test_run_notify_hook_scans_specify_features_root(monkeypatch, codex_team_project_root: Path):
    feature_dir = codex_team_project_root / ".specify" / "features" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    seen: list[Path] = []

    def _route(project_root: Path, *, feature_dir: Path, session_id: str = "default"):
        seen.append(feature_dir)
        raise AutoDispatchError("stop after probe")

    monkeypatch.setattr("specify_cli.codex_team.auto_dispatch.route_ready_parallel_batch", _route)

    run_notify_hook({"cwd": str(codex_team_project_root), "session_id": "default"})

    assert seen == [feature_dir]


def test_parse_tasks_markdown_captures_agent_required_without_redefining_parallel(
    codex_team_project_root: Path,
):
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Setup
- [ ] T002 [AGENT] Read handbook
- [ ] T003 [P] [AGENT] Worker lane
""",
    )

    parsed = parse_tasks_markdown(feature_dir / "tasks.md")

    assert parsed.tasks[1].agent_required is True
    assert parsed.tasks[1].parallel is False
    assert parsed.tasks[1].summary == "Read handbook in src/t002.py"
    assert parsed.tasks[2].agent_required is True
    assert parsed.tasks[2].parallel is True
    assert parsed.tasks[2].summary == "Worker lane in src/t003.py"


def test_parse_tasks_markdown_ignores_literal_marker_text_inside_task_summary(
    codex_team_project_root: Path,
):
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [ ] T001 Document literal [AGENT] token in docs/markers.md
- [ ] T002 [P] Preserve literal [AGENT] token in docs/parallel.md
""",
    )

    parsed = parse_tasks_markdown(feature_dir / "tasks.md")

    assert parsed.tasks[0].agent_required is False
    assert parsed.tasks[0].parallel is False
    assert parsed.tasks[0].summary == "Document literal [AGENT] token in docs/markers.md"
    assert parsed.tasks[1].agent_required is False
    assert parsed.tasks[1].parallel is True
    assert parsed.tasks[1].summary == "Preserve literal [AGENT] token in docs/parallel.md"


def test_find_next_ready_parallel_batch_requires_prior_tasks_complete(codex_team_project_root: Path):
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [ ] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B
- [X] T004 Done later

**Parallel Batch 1.1**

- `T002`
- `T003`
""",
    )

    parsed = parse_tasks_markdown(feature_dir / "tasks.md")

    assert find_next_ready_parallel_batch(parsed) is None


def test_find_next_ready_parallel_batch_blocks_incomplete_sequential_work_between_batch_members(
    codex_team_project_root: Path,
):
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [X] T002 [P] Worker A
- [ ] T003 Sequential prerequisite
- [ ] T004 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T004`
""",
    )

    parsed = parse_tasks_markdown(feature_dir / "tasks.md")

    assert find_next_ready_parallel_batch(parsed) is None


def test_materialize_runtime_batch_from_tracker_uses_current_batch_metadata(
    codex_team_project_root: Path,
):
    from specify_cli.codex_team import auto_dispatch as auto_dispatch_module

    feature_dir = codex_team_project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text(
        """---
status: executing
feature: 001-test-feature
created: 2026-04-25T00:00:00+00:00
updated: 2026-04-25T00:00:00+00:00
resume_decision: resume-here
---

## Current Focus
current_batch: phase3-bll-aria2
goal: Resume the active refactor batch
next_action: Dispatch BLL and Aria2 lanes

## Execution State
completed_tasks:
  - T001
in_progress_tasks:
failed_tasks:
retry_attempts: 0
""",
        encoding="utf-8",
    )
    (feature_dir / "phase3-refactor-plan.md").write_text(
        """## Batch phase3-bll-aria2

- BLL-lane Refactor BLLDownloadManager in JZDownloader/BLLDownloadManager.cpp
- Aria2-lane Continue the Aria2 split in JZDownloader/Aria2Adapter.cpp
""",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        """# Tasks

- [ ] T001 Old foundational task
""",
        encoding="utf-8",
    )

    batch = auto_dispatch_module.materialize_runtime_batch(feature_dir)

    assert batch.batch_name == "phase3-bll-aria2"
    assert batch.join_point_name == "phase3-bll-aria2-join"
    assert [task.task_id for task in batch.tasks] == ["BLL-lane", "Aria2-lane"]


def test_route_ready_parallel_batch_prefers_tracker_state_over_stale_tasks(
    monkeypatch, codex_team_project_root: Path
):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: True)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: {
            "psmux": r"C:\psmux.exe",
            "codex": r"C:\codex.exe",
            "node": r"C:\node.exe",
            "npm": r"C:\npm.cmd",
            "cargo": r"C:\cargo.exe",
            "git": r"C:\git.exe",
        }.get(name),
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})
    monkeypatch.setattr(
        "specify_cli.codex_team.auto_dispatch.launch_dispatched_worker",
        lambda *args, **kwargs: None,
    )

    feature_dir = codex_team_project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (codex_team_project_root / ".specify" / "memory").mkdir(parents=True, exist_ok=True)
    (codex_team_project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for delegated public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Implementation Constitution",
                "",
                "### Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "### Forbidden Implementation Drift",
                "",
                "- Do not create a parallel auth stack",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        """---
status: executing
feature: 001-test-feature
created: 2026-04-25T00:00:00+00:00
updated: 2026-04-25T00:00:00+00:00
resume_decision: resume-here
---

## Current Focus
current_batch: phase3-bll-aria2
goal: Resume the active refactor batch
next_action: Dispatch BLL and Aria2 lanes

## Execution State
completed_tasks:
  - T001
in_progress_tasks:
failed_tasks:
retry_attempts: 0
""",
        encoding="utf-8",
    )
    (feature_dir / "phase3-refactor-plan.md").write_text(
        """## Batch phase3-bll-aria2

- BLL-lane [US1] Refactor BLLDownloadManager in JZDownloader/BLLDownloadManager.cpp
- Aria2-lane [US1] Continue the Aria2 split in JZDownloader/Aria2Adapter.cpp
""",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        """# Tasks

- [ ] T001 Old foundational task in src/t001.py

## Validation Gates

- pytest -q -k phase3_bll_aria2
""",
        encoding="utf-8",
    )

    result = route_ready_parallel_batch(
        codex_team_project_root,
        feature_dir=feature_dir,
        session_id="default",
    )

    assert result.batch_name == "phase3-bll-aria2"
    assert result.dispatched_task_ids == ["BLL-lane", "Aria2-lane"]


def test_route_ready_parallel_batch_dispatches_each_task(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    launched: list[tuple[str, str, str, str]] = []

    def _launch(
        project_root: Path,
        *,
        session_id: str,
        worker_id: str,
        task_id: str,
        request_id: str = "",
        result_path: str = "",
    ) -> None:
        launched.append((worker_id, task_id, request_id, result_path))
        worker_heartbeat_path(project_root, worker_id).parent.mkdir(parents=True, exist_ok=True)
        worker_heartbeat_path(project_root, worker_id).write_text(
            '{"worker_id":"%s","status":"ready","details":{},"schema_version":"1.0","created_at":"2026-04-13T00:00:00+00:00"}'
            % worker_id,
            encoding="utf-8",
        )

    monkeypatch.setattr("specify_cli.codex_team.auto_dispatch.launch_dispatched_worker", _launch)

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B
- [ ] T004 Sequential follow-up

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    result = route_ready_parallel_batch(
        codex_team_project_root,
        feature_dir=feature_dir,
        session_id="default",
    )

    assert result.batch_name == "Parallel Batch 1.1"
    assert result.dispatched_task_ids == ["T002", "T003"]
    assert json.loads(runtime_session_path(codex_team_project_root, "default").read_text(encoding="utf-8"))["status"] == "running"
    assert dispatch_record_path(codex_team_project_root, "default-parallel-batch-1-1-t002").exists()
    assert dispatch_record_path(codex_team_project_root, "default-parallel-batch-1-1-t003").exists()
    batch_payload = json.loads(batch_record_path(codex_team_project_root, "default-parallel-batch-1-1").read_text(encoding="utf-8"))
    assert batch_payload["batch_name"] == "Parallel Batch 1.1"
    assert batch_payload["join_point_name"] == "Join Point 1.1"
    assert batch_payload["batch_classification"] == "strict"
    assert batch_payload["safe_preparation"] is False
    assert batch_payload["status"] == "dispatched"
    assert batch_payload["task_ids"] == ["T002", "T003"]
    assert batch_payload["request_ids"] == [
        "default-parallel-batch-1-1-t002",
        "default-parallel-batch-1-1-t003",
    ]
    assert launched == [
        (
            "t002",
            "T002",
            "default-parallel-batch-1-1-t002",
            str(codex_team_project_root / ".specify" / "teams" / "state" / "results" / "default-parallel-batch-1-1-t002.json"),
        ),
        (
            "t003",
            "T003",
            "default-parallel-batch-1-1-t003",
            str(codex_team_project_root / ".specify" / "teams" / "state" / "results" / "default-parallel-batch-1-1-t003.json"),
        ),
    ]
    assert worker_heartbeat_path(codex_team_project_root, "t002").exists()
    assert worker_heartbeat_path(codex_team_project_root, "t003").exists()
    dispatch_payload = json.loads(
        dispatch_record_path(
            codex_team_project_root,
            "default-parallel-batch-1-1-t002",
        ).read_text(encoding="utf-8")
    )
    assert dispatch_payload["packet_path"]
    assert dispatch_payload["packet_summary"]["task_id"] == "T002"
    assert dispatch_payload["result_path"].endswith("default-parallel-batch-1-1-t002.json")
    assert dispatch_payload["delegation_metadata"]["native_subagent_surface"] == "spawn_agent"
    task = get_task(codex_team_project_root, "T002")
    assert task.metadata["join_points"]["Join Point 1.1"]["status"] == "pending"
    assert task.metadata["join_points"]["Join Point 1.1"]["details"]["batch_name"] == "Parallel Batch 1.1"
    assert task.metadata["join_points"]["Join Point 1.1"]["details"]["batch_classification"] == "strict"


def test_route_ready_parallel_batch_records_review_policy(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    monkeypatch.setattr(
        "specify_cli.codex_team.auto_dispatch.classify_review_gate_policy",
        lambda **kwargs: type(
            "Policy",
            (),
            {
                "requires_review_gate": True,
                "peer_review_lane_recommended": True,
                "reason": "schema_change",
            },
        )(),
    )

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(
        codex_team_project_root,
        feature_dir=feature_dir,
        session_id="default",
    )

    batch_payload = json.loads(
        batch_record_path(
            codex_team_project_root,
            "default-parallel-batch-1-1",
        ).read_text(encoding="utf-8")
    )
    assert batch_payload["review_required"] is True
    assert batch_payload["peer_review_lane_recommended"] is True
    assert batch_payload["review_reason"] == "schema_change"
    assert batch_payload["review_status"] == "awaiting_review"


def test_route_ready_parallel_batch_requires_runtime_backend(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: None)

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`
""",
    )

    with pytest.raises(AutoDispatchUnavailableError):
        route_ready_parallel_batch(
            codex_team_project_root,
            feature_dir=feature_dir,
            session_id="default",
        )


def test_route_ready_parallel_batch_requires_configured_executor(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\tmux.exe" if name == "tmux" else None,
    )
    monkeypatch.delenv("SPECIFY_CODEX_TEAM_EXECUTOR", raising=False)

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`
""",
    )

    with pytest.raises(AutoDispatchUnavailableError, match="No packet executor is configured"):
        route_ready_parallel_batch(
            codex_team_project_root,
            feature_dir=feature_dir,
            session_id="default",
        )


def test_route_ready_parallel_batch_uses_agent_teams_batch_executor_when_available(
    monkeypatch,
    codex_team_project_root: Path,
):
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_EXECUTOR", "agent-teams-runtime")
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\tool.exe" if name in {"tmux", "node"} else None,
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})

    runtime_cli = codex_team_project_root / ".specify" / "extensions" / "agent-teams" / "engine" / "dist" / "team" / "runtime-cli.js"
    runtime_cli.parent.mkdir(parents=True, exist_ok=True)
    runtime_cli.write_text("// fake runtime cli\n", encoding="utf-8")

    launched: list[dict[str, object]] = []

    monkeypatch.setattr(
        "specify_cli.codex_team.auto_dispatch.launch_agent_teams_batch_executor",
        lambda project_root, **kwargs: launched.append(kwargs),
    )
    monkeypatch.setattr(
        "specify_cli.codex_team.auto_dispatch.launch_dispatched_worker",
        lambda *args, **kwargs: pytest.fail("legacy worker launcher should not run in agent-teams mode"),
    )

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`
""",
    )

    result = route_ready_parallel_batch(
        codex_team_project_root,
        feature_dir=feature_dir,
        session_id="default",
    )

    assert result.batch_name == "Parallel Batch 1.1"
    assert len(launched) == 1
    assert launched[0]["batch_id"] == "default-parallel-batch-1-1"
    assert launched[0]["runtime_cli_path"] == str(runtime_cli)
    assert [task["task_id"] for task in launched[0]["task_specs"]] == ["T002", "T003"]
    assert "Execution context bundle (read before claiming work):" in launched[0]["task_specs"][0]["description"]
    assert "src/contracts/auth.py [task_reference]" in launched[0]["task_specs"][0]["description"]
    assert "Acknowledge the execution context bundle in `rule_acknowledgement`" in launched[0]["task_specs"][0]["description"]


def test_route_ready_parallel_batch_agent_teams_executor_completes_end_to_end(
    monkeypatch,
    codex_team_project_root: Path,
):
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_EXECUTOR", "agent-teams-runtime")
    runtime_cli = codex_team_project_root / "fake-runtime-cli.py"
    _write_fake_agent_teams_runtime_cli(runtime_cli)
    monkeypatch.setenv("SPECIFY_CODEX_TEAM_RUNTIME_CLI", str(runtime_cli))
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\tool.exe" if name in {"tmux", "node"} else None,
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})
    write_calls: list[Path] = []

    def _tracking_write_json(path: Path, payload: dict) -> Path:
        write_calls.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f"{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(json.dumps(payload, indent=2) + "\n")
            os.replace(temp_path, path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)
        return path

    monkeypatch.setattr("specify_cli.codex_team.task_ops.write_json", _tracking_write_json, raising=False)
    monkeypatch.setattr("specify_cli.codex_team.batch_ops.write_json", _tracking_write_json, raising=False)
    monkeypatch.setattr("specify_cli.codex_team.auto_dispatch.write_json", _tracking_write_json, raising=False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.write_json", _tracking_write_json, raising=False)

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    result = route_ready_parallel_batch(
        codex_team_project_root,
        feature_dir=feature_dir,
        session_id="default",
    )

    request_ids = [
        "default-parallel-batch-1-1-t002",
        "default-parallel-batch-1-1-t003",
    ]
    _wait_for_result_files(codex_team_project_root, request_ids)

    completion = complete_dispatched_batch(
        codex_team_project_root,
        batch_id=result.batch_id,
        session_id="default",
    )

    assert completion.status == "completed"
    task_payload = get_task(codex_team_project_root, "T002")
    assert task_payload.metadata["worker_result"]["status"] == "success"
    assert task_payload.metadata["join_points"]["Join Point 1.1"]["status"] == "complete"
    expected_atomic_paths = {
        batch_record_path(codex_team_project_root, result.batch_id),
        runtime_session_path(codex_team_project_root, "default"),
        task_record_path(codex_team_project_root, "T002"),
        task_record_path(codex_team_project_root, "T003"),
    }
    assert expected_atomic_paths <= set(write_calls)


def test_complete_dispatched_batch_tolerates_result_submission_after_task_already_completed(
    monkeypatch,
    codex_team_project_root: Path,
):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(
        codex_team_project_root,
        feature_dir=feature_dir,
        session_id="default",
    )

    for task_id in ("T002", "T003"):
        request_id = f"default-parallel-batch-1-1-{task_id.lower()}"
        result_path = result_record_path(codex_team_project_root, request_id)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result = WorkerTaskResult(
            task_id=task_id,
            status="success",
            changed_files=[f"src/{task_id.lower()}.py"],
            validation_results=[
                ValidationResult(
                    command="pytest tests/unit/test_auth_service.py -q",
                    status="passed",
                    output="1 passed",
                )
            ],
            summary=f"{task_id} finished cleanly",
            rule_acknowledgement=RuleAcknowledgement(
                required_references_read=True,
                forbidden_drift_respected=True,
                context_bundle_read=True,
                paths_read=["src/contracts/auth.py"],
            ),
        )
        result_path.write_text(
            json.dumps(worker_task_result_payload(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    from specify_cli.codex_team.runtime_bridge import submit_runtime_result as real_submit_runtime_result

    raced_request_ids: set[str] = set()

    def _submit_after_external_completion(project_root: Path, *, session_id: str, request_id: str, result: object):
        if request_id.endswith("t003") and request_id not in raced_request_ids:
            raced_request_ids.add(request_id)
            record = get_task(project_root, "T003")
            token = claim_task(
                project_root,
                task_id="T003",
                worker_id="t003-worker",
                expected_version=record.version,
            )
            in_progress = transition_task_status(
                project_root,
                task_id="T003",
                new_status="in_progress",
                owner="t003-worker",
                expected_version=record.version + 1,
                claim_token=token,
            )
            transition_task_status(
                project_root,
                task_id="T003",
                new_status="completed",
                owner="t003-worker",
                expected_version=in_progress.version,
                claim_token=token,
            )

        return real_submit_runtime_result(
            project_root,
            session_id=session_id,
            request_id=request_id,
            result=result,
        )

    monkeypatch.setattr(
        "specify_cli.codex_team.auto_dispatch.submit_runtime_result",
        _submit_after_external_completion,
    )

    completion = complete_dispatched_batch(
        codex_team_project_root,
        batch_id="default-parallel-batch-1-1",
        session_id="default",
    )

    assert completion.status == "completed"
    task_payload = get_task(codex_team_project_root, "T003")
    assert task_payload.status == "completed"
    assert task_payload.metadata["worker_result"]["status"] == "success"
    assert task_payload.metadata["join_points"]["Join Point 1.1"]["status"] == "complete"


def test_route_ready_parallel_batch_rejects_explicit_batches_with_unknown_task_ids(
    monkeypatch, codex_team_project_root: Path
):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    monkeypatch.setattr(
        "specify_cli.codex_team.auto_dispatch.launch_dispatched_worker",
        lambda *args, **kwargs: None,
    )

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T999`
""",
    )

    with pytest.raises(AutoDispatchError, match="unknown task ids"):
        route_ready_parallel_batch(
            codex_team_project_root,
            feature_dir=feature_dir,
            session_id="default",
        )


def test_route_ready_parallel_batch_cleans_up_partial_state_when_later_dispatch_fails(
    monkeypatch, codex_team_project_root: Path
):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    from specify_cli.codex_team.runtime_bridge import dispatch_runtime_task as real_dispatch_runtime_task

    launched: list[str] = []

    def _dispatch_with_failure(*args, **kwargs):
        request_id = kwargs["request_id"]
        if request_id.endswith("t003"):
            raise RuntimeError("dispatch boom")
        return real_dispatch_runtime_task(*args, **kwargs)

    def _launch(*args, **kwargs):
        launched.append(kwargs["task_id"])

    monkeypatch.setattr("specify_cli.codex_team.auto_dispatch.dispatch_runtime_task", _dispatch_with_failure)
    monkeypatch.setattr("specify_cli.codex_team.auto_dispatch.launch_dispatched_worker", _launch)

    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`
""",
    )

    with pytest.raises(RuntimeError, match="dispatch boom"):
        route_ready_parallel_batch(
            codex_team_project_root,
            feature_dir=feature_dir,
            session_id="default",
        )

    first_request_id = "default-parallel-batch-1-1-t002"
    second_request_id = "default-parallel-batch-1-1-t003"
    packets_root = codex_team_project_root / ".specify" / "codex-team" / "state" / "packets"

    assert launched == []
    assert batch_record_path(codex_team_project_root, "default-parallel-batch-1-1").exists() is False
    assert dispatch_record_path(codex_team_project_root, first_request_id).exists() is False
    assert dispatch_record_path(codex_team_project_root, second_request_id).exists() is False
    assert (packets_root / f"{first_request_id}.json").exists() is False
    assert (packets_root / f"{second_request_id}.json").exists() is False
    assert runtime_session_path(codex_team_project_root, "default").exists()
    session_payload = json.loads(runtime_session_path(codex_team_project_root, "default").read_text(encoding="utf-8"))
    assert session_payload["status"] == "ready"
    with pytest.raises(TaskOpsError, match="task T002 not found"):
        get_task(codex_team_project_root, "T002")
    with pytest.raises(TaskOpsError, match="task T003 not found"):
        get_task(codex_team_project_root, "T003")


def test_terminal_task_completion_auto_completes_batch(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    for task_id in ("T002", "T003"):
        record = get_task(codex_team_project_root, task_id)
        token = claim_task(
            codex_team_project_root,
            task_id=task_id,
            worker_id=f"{task_id.lower()}-worker",
            expected_version=record.version,
        )
        in_progress = transition_task_status(
            codex_team_project_root,
            task_id=task_id,
            new_status="in_progress",
            owner=f"{task_id.lower()}-worker",
            expected_version=record.version + 1,
            claim_token=token,
        )
        transition_task_status(
            codex_team_project_root,
            task_id=task_id,
            new_status="completed",
            owner=f"{task_id.lower()}-worker",
            expected_version=in_progress.version,
            claim_token=token,
        )

    for task_id in ("T002", "T003"):
        request_id = f"default-parallel-batch-1-1-{task_id.lower()}"
        result_path = result_record_path(codex_team_project_root, request_id)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result = WorkerTaskResult(
            task_id=task_id,
            status="success",
            changed_files=[f"src/{task_id.lower()}.py"],
            validation_results=[
                ValidationResult(
                    command="pytest tests/unit/test_auth_service.py -q",
                    status="passed",
                    output="1 passed",
                )
            ],
            summary=f"{task_id} finished cleanly",
            rule_acknowledgement=RuleAcknowledgement(
                required_references_read=True,
                forbidden_drift_respected=True,
                context_bundle_read=True,
                paths_read=["src/contracts/auth.py"],
            ),
        )
        result_path.write_text(
            json.dumps(worker_task_result_payload(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    completion = complete_dispatched_batch(
        codex_team_project_root,
        batch_id="default-parallel-batch-1-1",
        session_id="default",
    )

    batch_payload = json.loads(batch_record_path(codex_team_project_root, "default-parallel-batch-1-1").read_text(encoding="utf-8"))
    assert completion.status == "completed"
    assert batch_payload["status"] == "completed"
    task_payload = get_task(codex_team_project_root, "T002")
    assert task_payload.metadata["join_points"]["Join Point 1.1"]["status"] == "complete"


def test_complete_dispatched_batch_validates_structured_worker_results(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    for task_id in ("T002", "T003"):
        request_id = f"default-parallel-batch-1-1-{task_id.lower()}"
        result_path = result_record_path(codex_team_project_root, request_id)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result = WorkerTaskResult(
            task_id=task_id,
            status="success",
            changed_files=[f"src/{task_id.lower()}.py"],
            validation_results=[
                ValidationResult(
                    command="pytest tests/unit/test_auth_service.py -q",
                    status="passed",
                    output="1 passed",
                )
            ],
            summary=f"{task_id} finished cleanly",
            rule_acknowledgement=RuleAcknowledgement(
                required_references_read=True,
                forbidden_drift_respected=True,
                context_bundle_read=True,
                paths_read=["src/contracts/auth.py"],
            ),
        )
        result_path.write_text(
            json.dumps(worker_task_result_payload(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    completion = complete_dispatched_batch(
        codex_team_project_root,
        batch_id="default-parallel-batch-1-1",
        session_id="default",
    )

    assert completion.status == "completed"
    task_payload = get_task(codex_team_project_root, "T002")
    assert task_payload.metadata["worker_result"]["status"] == "success"
    assert task_payload.metadata["worker_result"]["summary"] == "T002 finished cleanly"


def test_complete_dispatched_batch_waits_for_review_when_review_gate_is_required(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    monkeypatch.setattr(
        "specify_cli.codex_team.auto_dispatch.classify_review_gate_policy",
        lambda **kwargs: type(
            "Policy",
            (),
            {
                "requires_review_gate": True,
                "peer_review_lane_recommended": True,
                "reason": "schema_change",
            },
        )(),
    )
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    for task_id in ("T002", "T003"):
        request_id = f"default-parallel-batch-1-1-{task_id.lower()}"
        result_path = result_record_path(codex_team_project_root, request_id)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result = WorkerTaskResult(
            task_id=task_id,
            status="success",
            changed_files=[f"src/{task_id.lower()}.py"],
            validation_results=[
                ValidationResult(
                    command="pytest tests/unit/test_auth_service.py -q",
                    status="passed",
                    output="1 passed",
                )
            ],
            summary=f"{task_id} finished cleanly",
            rule_acknowledgement=RuleAcknowledgement(
                required_references_read=True,
                forbidden_drift_respected=True,
                context_bundle_read=True,
                paths_read=["src/contracts/auth.py"],
            ),
        )
        result_path.write_text(
            json.dumps(worker_task_result_payload(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    completion = complete_dispatched_batch(
        codex_team_project_root,
        batch_id="default-parallel-batch-1-1",
        session_id="default",
    )

    batch_payload = json.loads(
        batch_record_path(codex_team_project_root, "default-parallel-batch-1-1").read_text(encoding="utf-8")
    )
    assert completion.status == "awaiting_review"
    assert batch_payload["status"] == "awaiting_review"
    assert batch_payload["review_status"] == "awaiting_review"
    task_payload = get_task(codex_team_project_root, "T002")
    assert task_payload.metadata["join_points"]["Join Point 1.1"]["status"] == "review_pending"

@pytest.mark.parametrize("mode", ["missing", "corrupt"])
def test_complete_dispatched_batch_fails_closed_when_dispatch_record_is_missing_or_corrupt(
    monkeypatch,
    codex_team_project_root: Path,
    mode: str,
):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    request_id = "default-parallel-batch-1-1-t003"
    path = dispatch_record_path(codex_team_project_root, request_id)
    if mode == "missing":
        path.unlink()
    else:
        path.write_text("{", encoding="utf-8")

    with pytest.raises(AutoDispatchError, match="dispatch record"):
        complete_dispatched_batch(
            codex_team_project_root,
            batch_id="default-parallel-batch-1-1",
            session_id="default",
        )

def test_complete_dispatched_batch_requires_result_when_structured_results_expected(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    with pytest.raises(AutoDispatchError, match="missing structured worker result"):
        complete_dispatched_batch(
            codex_team_project_root,
            batch_id="default-parallel-batch-1-1",
            session_id="default",
        )


def test_complete_dispatched_batch_rejects_pending_result_placeholders(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    for task_id in ("T002", "T003"):
        request_id = f"default-parallel-batch-1-1-{task_id.lower()}"
        path = result_record_path(codex_team_project_root, request_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        pending_result = WorkerTaskResult(
            task_id=task_id,
            status="pending",
            summary=f"{task_id} still running",
        )
        path.write_text(
            json.dumps(worker_task_result_payload(pending_result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    with pytest.raises(AutoDispatchError, match="not complete: pending"):
        complete_dispatched_batch(
            codex_team_project_root,
            batch_id="default-parallel-batch-1-1",
            session_id="default",
        )


def test_terminal_task_failure_marks_batch_failed(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    record = get_task(codex_team_project_root, "T002")
    token = claim_task(
        codex_team_project_root,
        task_id="T002",
        worker_id="t002-worker",
        expected_version=record.version,
    )
    in_progress = transition_task_status(
        codex_team_project_root,
        task_id="T002",
        new_status="in_progress",
        owner="t002-worker",
        expected_version=record.version + 1,
        claim_token=token,
    )
    transition_task_status(
        codex_team_project_root,
        task_id="T002",
        new_status="failed",
        owner="t002-worker",
        expected_version=in_progress.version,
        claim_token=token,
    )

    batch_payload = json.loads(batch_record_path(codex_team_project_root, "default-parallel-batch-1-1").read_text(encoding="utf-8"))
    assert batch_payload["status"] == "failed"
    task_payload = get_task(codex_team_project_root, "T002")
    assert task_payload.metadata["join_points"]["Join Point 1.1"]["status"] == "failed"


def test_non_critical_failure_blocks_mixed_tolerance_batch_without_failing_session(monkeypatch, codex_team_project_root: Path):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        """# Tasks

- [X] T001 Shared setup
- [ ] T002 [P] Worker A
- [ ] T003 [P] Worker B

**Parallel Batch 1.1**

- `T002`
- `T003`

**Join Point 1.1**: merge before T004
""",
    )

    route_ready_parallel_batch(codex_team_project_root, feature_dir=feature_dir, session_id="default")

    batch_path = batch_record_path(codex_team_project_root, "default-parallel-batch-1-1")
    batch_payload = json.loads(batch_path.read_text(encoding="utf-8"))
    batch_payload["batch_classification"] = "mixed_tolerance"
    batch_path.write_text(json.dumps(batch_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    record = get_task(codex_team_project_root, "T002")
    token = claim_task(
        codex_team_project_root,
        task_id="T002",
        worker_id="t002-worker",
        expected_version=record.version,
    )
    in_progress = transition_task_status(
        codex_team_project_root,
        task_id="T002",
        new_status="in_progress",
        owner="t002-worker",
        expected_version=record.version + 1,
        claim_token=token,
    )
    transition_task_status(
        codex_team_project_root,
        task_id="T002",
        new_status="failed",
        owner="t002-worker",
        expected_version=in_progress.version,
        claim_token=token,
        failure_class="non_critical",
    )

    updated_batch = json.loads(batch_path.read_text(encoding="utf-8"))
    session_payload = json.loads(runtime_session_path(codex_team_project_root, "default").read_text(encoding="utf-8"))
    task_payload = get_task(codex_team_project_root, "T002")

    assert updated_batch["status"] == "blocked"
    assert task_payload.metadata["join_points"]["Join Point 1.1"]["status"] == "blocked"
    assert session_payload["status"] == "running"
