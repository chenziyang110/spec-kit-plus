from pathlib import Path

import json
import pytest

from specify_cli.execution.result_handoff import (
    build_result_handoff_path,
    describe_result_handoff_template,
    describe_result_submit_template,
    write_normalized_result_handoff,
)


def test_describe_result_handoff_template_matches_supported_workflows() -> None:
    assert (
        describe_result_handoff_template(
            command_name="implement", integration_key="claude"
        )
        == "FEATURE_DIR/worker-results/<task-id>.json"
    )
    assert (
        describe_result_handoff_template(
            command_name="review", integration_key="claude"
        )
        == "FEATURE_DIR/review-results/<lane-id>.json"
    )
    assert (
        describe_result_handoff_template(
            command_name="quick", integration_key="cursor-agent"
        )
        == ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json"
    )
    assert (
        describe_result_handoff_template(command_name="debug", integration_key="claude")
        == ".planning/debug/results/<session-slug>/<lane-id>.json"
    )
    assert (
        describe_result_handoff_template(
            command_name="implement", integration_key="codex"
        )
        == ".specify/teams/state/results/<request-id>.json"
    )
    assert (
        describe_result_handoff_template(command_name="plan", integration_key="codex")
        == "FEATURE_DIR/planning/handoffs/<lane-id>.json"
    )
    assert (
        describe_result_handoff_template(command_name="tasks", integration_key="codex")
        == "FEATURE_DIR/task-generation/handoffs/<lane-id>.json"
    )


def test_describe_result_submit_template_uses_inline_cli_channels() -> None:
    assert "implement result-merge" in describe_result_submit_template(
        command_name="implement", integration_key="claude"
    )
    assert "--result-json" in describe_result_submit_template(
        command_name="quick", integration_key="cursor-agent"
    )
    codex_implement = describe_result_submit_template(
        command_name="implement", integration_key="codex"
    )
    assert "implement result-merge" in codex_implement
    assert "--result-file" not in codex_implement
    codex_quick = describe_result_submit_template(
        command_name="quick", integration_key="codex"
    )
    assert "result submit --command quick" in codex_quick
    assert "sp-teams submit-result" not in codex_quick
    assert "--result-file" not in codex_quick


@pytest.mark.parametrize("command_name", ["clarify", "plan", "tasks", "deep-research"])
def test_describe_result_submit_template_for_codex_stage_commands_uses_generic_result_submit(
    command_name: str,
) -> None:
    template = describe_result_submit_template(
        command_name=command_name,
        integration_key="codex",
    )

    assert f"result submit --command {command_name}" in template
    assert "--feature-dir <feature-dir>" in template
    assert "--lane-id <lane-id>" in template
    assert "--result-json '<inline-json>'" in template
    assert "sp-teams submit-result" not in template
    assert "--result-file" not in template


def test_build_result_handoff_path_for_codex_runtime(
    project_root: Path = Path("F:/tmp/project"),
) -> None:
    path = build_result_handoff_path(
        project_root,
        command_name="implement",
        integration_key="codex",
        request_id="req-1",
    )

    assert (
        str(path).replace("\\", "/").endswith(".specify/teams/state/results/req-1.json")
    )


@pytest.mark.parametrize(
    ("command_name", "suffix"),
    [
        ("clarify", "clarification/handoffs/lane-a.json"),
        ("plan", "planning/handoffs/lane-a.json"),
        ("tasks", "task-generation/handoffs/lane-a.json"),
        ("deep-research", "research/handoffs/lane-a.json"),
    ],
)
def test_build_result_handoff_path_for_codex_stage_commands_uses_stage_owned_paths(
    command_name: str,
    suffix: str,
    project_root: Path = Path("F:/tmp/project"),
) -> None:
    feature_dir = project_root / ".specify" / "features" / "001-feature"

    path = build_result_handoff_path(
        project_root,
        command_name=command_name,
        integration_key="codex",
        feature_dir=feature_dir,
        lane_id="lane-a",
    )

    assert (
        str(path).replace("\\", "/").endswith(f".specify/features/001-feature/{suffix}")
    )


def test_build_result_handoff_path_for_feature_worker_result(
    project_root: Path = Path("F:/tmp/project"),
) -> None:
    feature_dir = project_root / "specs" / "001-feature"
    path = build_result_handoff_path(
        project_root,
        command_name="implement",
        integration_key="claude",
        feature_dir=feature_dir,
        task_id="T007",
    )

    assert path == feature_dir / "worker-results" / "T007.json"


@pytest.mark.parametrize("integration_key", ["claude", "codex"])
def test_build_result_handoff_path_for_review_lane_is_feature_owned(
    integration_key: str,
    project_root: Path = Path("F:/tmp/project"),
) -> None:
    feature_dir = project_root / ".specify" / "features" / "001-feature"

    path = build_result_handoff_path(
        project_root,
        command_name="review",
        integration_key=integration_key,
        feature_dir=feature_dir,
        lane_id="audit-primary-journey",
    )

    assert path == (feature_dir / "review-results" / "audit-primary-journey.json")


@pytest.mark.parametrize("integration_key", ["cursor-agent", "codex"])
def test_build_result_handoff_path_for_quick_workspace(
    integration_key: str,
    project_root: Path = Path("F:/tmp/project"),
) -> None:
    workspace = project_root / ".planning" / "quick" / "001-fix"
    path = build_result_handoff_path(
        project_root,
        command_name="quick",
        integration_key=integration_key,
        quick_workspace=workspace,
        lane_id="lane-a",
    )

    assert path == workspace / "worker-results" / "lane-a.json"


@pytest.mark.parametrize("integration_key", ["claude", "codex"])
def test_build_result_handoff_path_for_debug_workspace(
    integration_key: str,
    project_root: Path = Path("F:/tmp/project"),
) -> None:
    path = build_result_handoff_path(
        project_root,
        command_name="debug",
        integration_key=integration_key,
        debug_session_slug="cache-stuck",
        lane_id="evidence-a",
    )

    assert (
        str(path)
        .replace("\\", "/")
        .endswith(".planning/debug/results/cache-stuck/evidence-a.json")
    )


def test_build_result_handoff_path_for_codex_prd_scan_workspace(
    project_root: Path = Path("F:/tmp/project"),
) -> None:
    workspace = project_root / ".planning" / "prd-scan" / "001-current-product"

    path = build_result_handoff_path(
        project_root,
        command_name="prd-scan",
        integration_key="codex",
        quick_workspace=workspace,
        lane_id="surface-inventory",
    )

    assert path == workspace / "worker-results" / "surface-inventory.json"


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


def test_write_normalized_result_handoff_rejects_obsolete_ui_fields(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".planning" / "quick" / "001-fix"

    with pytest.raises(ValueError, match="ui_fidelity_evidence"):
        write_normalized_result_handoff(
            tmp_path,
            command_name="quick",
            integration_key="cursor-agent",
            raw_result={
                "task_id": "lane-a",
                "status": "success",
                "ui_fidelity_evidence": [],
            },
            quick_workspace=target,
            lane_id="lane-a",
        )

    assert not (target / "worker-results" / "lane-a.json").exists()
