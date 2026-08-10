from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.execution.packet_compiler import compile_worker_task_packet


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / "specs" / "001-test-design"
    feature.mkdir(parents=True)

    templates = project / ".specify" / "templates"
    templates.mkdir(parents=True)
    (templates / "task-index-template.json").write_text(
        _read("templates/task-index-template.json"),
        encoding="utf-8",
    )
    (templates / "task-packet-template.json").write_text(
        _read("templates/task-packet-template.json"),
        encoding="utf-8",
    )

    memory_dir = project / ".specify" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "constitution.md").write_text(
        "# Constitution\n\n- Preserve authored test design inputs.\n",
        encoding="utf-8",
    )

    (feature / "plan-contract.json").write_text(
        json.dumps(
            {
                "status": "ready",
                "acceptance_refs": [],
                "source_revision": 7,
            }
        ),
        encoding="utf-8",
    )
    (feature / "plan.md").write_text(
        "\n".join(
            [
                "# Plan",
                "",
                "## Required Implementation References",
                "- docs/test-design.md",
                "",
            ]
        )
        + "\n",
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


def test_tasks_surfaces_treat_optional_test_design_handoff_as_authoritative_input() -> (
    None
):
    classic = _read("templates/commands/tasks.md").lower()
    advanced = _read("templates/advanced-skills/spx-tasks/SKILL.md").lower()

    for content in (classic, advanced):
        assert "test-design handoff" in content
        assert "authoritative input" in content
        assert "test_case_refs" in content
        assert "test_data_refs" in content


def test_tasks_build_preserves_test_design_refs_in_canonical_task_index(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    definition = {
        "title": "Test design consumption",
        "source_revision": 7,
        "tasks": [
            {
                "id": "T001",
                "objective": "Implement the tested publish flow",
                "dependencies": [],
                "expected_write_scope": ["src/publish.py"],
                "required_refs": ["docs/test-design.md"],
                "acceptance": ["Publish flow matches the authored test design"],
                "verification": ["pytest tests/unit/test_publish.py -q"],
                "test_case_refs": [
                    "test-design-handoff.json#/test_cases/TC-001",
                    "test-design-handoff.json#/test_cases/TC-002",
                ],
                "test_data_refs": [
                    "test-design-handoff.json#/test_data/TD-001",
                ],
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
    task_index = json.loads((feature / "task-index.json").read_text(encoding="utf-8"))
    task = task_index["tasks"][0]
    assert task["test_case_refs"] == [
        "test-design-handoff.json#/test_cases/TC-001",
        "test-design-handoff.json#/test_cases/TC-002",
    ]
    assert task["test_data_refs"] == [
        "test-design-handoff.json#/test_data/TD-001",
    ]


def test_jit_worker_packet_carries_test_design_refs_to_implement(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    (feature / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "tasks": [
                    {
                        "id": "T001",
                        "objective": "Implement the tested publish flow",
                        "expected_write_scope": ["src/publish.py"],
                        "read_scope": ["docs/test-design.md"],
                        "required_refs": ["docs/test-design.md"],
                        "acceptance": ["Publish flow matches the authored test design"],
                        "verification": ["pytest tests/unit/test_publish.py -q"],
                        "test_case_refs": [
                            "test-design-handoff.json#/test_cases/TC-001",
                        ],
                        "test_data_refs": [
                            "test-design-handoff.json#/test_data/TD-001",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks: Test design consumption",
                "",
                "## T001 — Implement the tested publish flow",
                "",
                "### Scope Boundaries",
                "",
                "| Field | Value |",
                "| --- | --- |",
                "| read_scope | [docs/test-design.md] |",
                "| write_scope | [src/publish.py] |",
                "| required_refs | [docs/test-design.md] |",
                "| test_case_refs | [test-design-handoff.json#/test_cases/TC-001] |",
                "| test_data_refs | [test-design-handoff.json#/test_data/TD-001] |",
                "",
                "### Acceptance and Verification",
                "",
                "- Acceptance: [Publish flow matches the authored test design]",
                "- Verification: [pytest tests/unit/test_publish.py -q]",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project,
        feature_dir=feature,
        task_id="T001",
    )

    assert packet.test_case_refs == [
        "test-design-handoff.json#/test_cases/TC-001",
    ]
    assert packet.test_data_refs == [
        "test-design-handoff.json#/test_data/TD-001",
    ]
