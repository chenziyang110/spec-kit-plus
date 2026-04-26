from pathlib import Path

import json
import pytest

from specify_cli.execution.result_handoff import (
    build_result_handoff_path,
    describe_result_handoff_template,
    write_normalized_result_handoff,
)


def test_describe_result_handoff_template_matches_supported_workflows() -> None:
    assert describe_result_handoff_template(command_name="implement", integration_key="claude") == "FEATURE_DIR/worker-results/<task-id>.json"
    assert describe_result_handoff_template(command_name="quick", integration_key="cursor-agent") == ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json"
    assert describe_result_handoff_template(command_name="debug", integration_key="claude") == ".planning/debug/results/<session-slug>/<lane-id>.json"
    assert describe_result_handoff_template(command_name="implement", integration_key="codex") == ".specify/codex-team/state/results/<request-id>.json"


def test_build_result_handoff_path_for_codex_runtime(project_root: Path = Path("F:/tmp/project")) -> None:
    path = build_result_handoff_path(
        project_root,
        command_name="implement",
        integration_key="codex",
        request_id="req-1",
    )

    assert str(path).replace("\\", "/").endswith(".specify/codex-team/state/results/req-1.json")


def test_build_result_handoff_path_for_feature_worker_result(project_root: Path = Path("F:/tmp/project")) -> None:
    feature_dir = project_root / "specs" / "001-feature"
    path = build_result_handoff_path(
        project_root,
        command_name="implement",
        integration_key="claude",
        feature_dir=feature_dir,
        task_id="T007",
    )

    assert path == feature_dir / "worker-results" / "T007.json"


def test_build_result_handoff_path_for_quick_workspace(project_root: Path = Path("F:/tmp/project")) -> None:
    workspace = project_root / ".planning" / "quick" / "001-fix"
    path = build_result_handoff_path(
        project_root,
        command_name="quick",
        integration_key="cursor-agent",
        quick_workspace=workspace,
        lane_id="lane-a",
    )

    assert path == workspace / "worker-results" / "lane-a.json"


def test_build_result_handoff_path_for_debug_workspace(project_root: Path = Path("F:/tmp/project")) -> None:
    path = build_result_handoff_path(
        project_root,
        command_name="debug",
        integration_key="claude",
        debug_session_slug="cache-stuck",
        lane_id="evidence-a",
    )

    assert str(path).replace("\\", "/").endswith(".planning/debug/results/cache-stuck/evidence-a.json")


def test_write_normalized_result_handoff_rejects_pending_template_payload(
    project_root: Path = Path("F:/tmp/project"),
) -> None:
    with pytest.raises(ValueError, match="Pending result templates cannot be written"):
        write_normalized_result_handoff(
            project_root,
            command_name="quick",
            integration_key="cursor-agent",
            raw_result=json.dumps(
                {
                    "task_id": "lane-a",
                    "status": "pending",
                    "validation_results": [
                        {
                            "command": "pytest -q",
                            "status": "skipped",
                            "output": "NOT RUN - replace with actual command output after execution",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            quick_workspace=project_root / ".planning" / "quick" / "001-fix",
            lane_id="lane-a",
        )
