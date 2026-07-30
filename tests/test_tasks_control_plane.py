from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


ROOT = Path(__file__).resolve().parents[1]


def _project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / "specs" / "001-task-control"
    feature.mkdir(parents=True)
    templates = project / ".specify" / "templates"
    templates.mkdir(parents=True)
    (templates / "task-index-template.json").write_text(
        (ROOT / "templates" / "task-index-template.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    (templates / "task-packet-template.json").write_text(
        (ROOT / "templates" / "task-packet-template.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    (feature / "plan-contract.json").write_text(
        json.dumps(
            {
                "status": "ready",
                "acceptance_refs": [],
                "source_revision": 3,
            }
        ),
        encoding="utf-8",
    )
    return project, feature


def _invoke(project: Path, args: list[str]):
    old_cwd = Path.cwd()
    try:
        os.chdir(project)
        return CliRunner().invoke(app, args)
    finally:
        os.chdir(old_cwd)


def test_tasks_build_expands_template_and_renders_markdown_via_cli(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    definition = {
        "title": "Task control plane",
        "source_revision": 3,
        "confirmed_delivery_scope": ["Ship the control plane"],
        "tasks": [
            {
                "id": "T001",
                "story_id": "US1",
                "objective": "Implement the typed task mutation API",
                "dependencies": [],
                "expected_write_scope": ["src/tasks.py"],
                "required_refs": ["plan-contract.json"],
                "acceptance": ["Task mutations are atomic"],
                "verification": ["pytest -q"],
                "ui_contract": {"fidelity_level": "high"},
            }
        ],
    }

    result = _invoke(
        project,
        [
            "tasks",
            "build",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--definition-json",
            json.dumps(definition),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    receipt = json.loads(result.output)
    assert receipt["status"] == "ok"
    assert receipt["transaction_id"]
    assert "definition" not in receipt
    assert len(result.output.encode("utf-8")) < 4096

    task_index = json.loads((feature / "task-index.json").read_text(encoding="utf-8"))
    assert task_index["version"] == 2
    assert task_index["status"] == "draft"
    assert task_index["validation_policy"]["mode"] == "feature_epochs"
    assert task_index["tasks"][0]["id"] == "T001"
    assert task_index["tasks"][0]["ui_contract"]["fidelity_level"] == "high"
    assert task_index["tasks"][0]["ui_contract"]["required_states"] == []
    assert "comparison_tolerance" in task_index["tasks"][0]["ui_contract"]

    rendered = (feature / "tasks.md").read_text(encoding="utf-8")
    assert "- [ ] T001 [US1] Implement the typed task mutation API" in rendered
    assert "## T001" in rendered
    assert "## Consequence Obligation Mapping" in rendered


def test_tasks_upsert_remove_and_finalize_keep_both_projections_aligned(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    initial = {
        "tasks": [
            {
                "id": "T001",
                "objective": "Initial task",
                "dependencies": [],
                "expected_write_scope": ["src/one.py"],
                "acceptance": ["One works"],
                "verification": ["pytest -q"],
            },
            {
                "id": "T002",
                "objective": "Remove me",
                "dependencies": ["T001"],
                "expected_write_scope": ["src/two.py"],
                "acceptance": ["Two works"],
                "verification": ["pytest -q"],
            },
        ]
    }
    built = _invoke(
        project,
        [
            "tasks",
            "build",
            "--feature-dir",
            "specs/001-task-control",
            "--definition-json",
            json.dumps(initial),
            "--format",
            "json",
        ],
    )
    assert built.exit_code == 0, built.output

    replacement = {
        "id": "T001",
        "objective": "Updated task",
        "dependencies": [],
        "expected_write_scope": ["src/one.py"],
        "acceptance": ["One is updated"],
        "verification": ["pytest -q"],
    }
    updated = _invoke(
        project,
        [
            "tasks",
            "upsert",
            "--feature-dir",
            "specs/001-task-control",
            "--task-json",
            json.dumps(replacement),
            "--format",
            "json",
        ],
    )
    assert updated.exit_code == 0, updated.output

    removed = _invoke(
        project,
        [
            "tasks",
            "remove",
            "--feature-dir",
            "specs/001-task-control",
            "--task-id",
            "T002",
            "--format",
            "json",
        ],
    )
    assert removed.exit_code == 0, removed.output

    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            "specs/001-task-control",
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output

    handoff = _invoke(
        project,
        [
            "tasks",
            "handoff",
            "--feature-dir",
            "specs/001-task-control",
            "--target",
            "implement",
            "--format",
            "json",
        ],
    )
    assert handoff.exit_code == 0, handoff.output

    task_index = json.loads((feature / "task-index.json").read_text(encoding="utf-8"))
    assert task_index["status"] == "ready"
    assert [task["id"] for task in task_index["tasks"]] == ["T001"]
    assert task_index["tasks"][0]["objective"] == "Updated task"
    rendered = (feature / "tasks.md").read_text(encoding="utf-8")
    assert "Updated task" in rendered
    assert "T002" not in rendered
    handoff_payload = json.loads(
        (feature / "handoff-to-implement.json").read_text(encoding="utf-8")
    )
    assert handoff_payload["status"] == "ready"
    assert handoff_payload["task_index_ref"] == "task-index.json"
    assert handoff_payload["task_count"] == 1


def test_tasks_finalize_rejects_unknown_dependencies_without_partial_write(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    definition = {
        "tasks": [
            {
                "id": "T001",
                "objective": "Broken dependency",
                "dependencies": ["T999"],
                "expected_write_scope": ["src/one.py"],
                "acceptance": ["One works"],
                "verification": ["pytest -q"],
            }
        ]
    }
    built = _invoke(
        project,
        [
            "tasks",
            "build",
            "--feature-dir",
            "specs/001-task-control",
            "--definition-json",
            json.dumps(definition),
            "--format",
            "json",
        ],
    )
    assert built.exit_code == 0, built.output
    before = (feature / "task-index.json").read_bytes()

    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            "specs/001-task-control",
            "--format",
            "json",
        ],
    )

    assert finalized.exit_code != 0
    assert "unknown dependency T999" in finalized.output
    assert (feature / "task-index.json").read_bytes() == before


def test_tasks_build_rejects_agent_authored_task_lifecycle_fields(
    tmp_path: Path,
) -> None:
    project, _feature = _project(tmp_path)
    definition = {
        "tasks": [
            {
                "id": "T001",
                "objective": "Bypass lifecycle",
                "status": "accepted",
            }
        ]
    }

    result = _invoke(
        project,
        [
            "tasks",
            "build",
            "--feature-dir",
            "specs/001-task-control",
            "--definition-json",
            json.dumps(definition),
            "--format",
            "json",
        ],
    )

    assert result.exit_code != 0
    assert "CLI-owned fields: status" in result.output

    unknown = _invoke(
        project,
        [
            "tasks",
            "build",
            "--feature-dir",
            "specs/001-task-control",
            "--definition-json",
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": "T001",
                            "objective": "Inject arbitrary payload",
                            "arbitrary_blob": {"value": "unexpected"},
                        }
                    ]
                }
            ),
            "--format",
            "json",
        ],
    )
    assert unknown.exit_code != 0
    assert "unsupported fields: arbitrary_blob" in unknown.output
