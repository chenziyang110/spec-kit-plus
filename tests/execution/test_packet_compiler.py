from pathlib import Path

from specify_cli.execution.packet_compiler import compile_worker_task_packet


def test_compile_worker_task_packet_merges_constitution_plan_and_task_sources(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-map").mkdir(parents=True)
    (project_root / ".specify" / "testing").mkdir(parents=True)
    (project_root / "PROJECT-HANDBOOK.md").write_text("# Handbook\n", encoding="utf-8")
    (project_root / ".specify" / "project-map" / "ARCHITECTURE.md").write_text(
        "# Architecture\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-map" / "WORKFLOWS.md").write_text(
        "# Workflows\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-map" / "OPERATIONS.md").write_text(
        "# Operations\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-map" / "TESTING.md").write_text(
        "# Testing\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "testing" / "TESTING_CONTRACT.md").write_text(
        "# Testing Contract\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "testing" / "TESTING_PLAYBOOK.md").write_text(
        "# Testing Playbook\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
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
                "",
                "### Platform Guardrails",
                "",
                "- supported_platforms: windows, linux",
                "- require conditional compilation for unix-only APIs",
                "",
                "### Completion Handoff Protocol",
                "",
                "- send task_started before long-running work",
                "- write structured result handoff before idling",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_auth_service.py -q",
                "",
                "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert packet.task_id == "T017"
    assert packet.story_id == "US1"
    assert "src/contracts/auth.py" in [ref.path for ref in packet.required_references]
    assert any("public behavior" in rule.lower() for rule in packet.hard_rules)
    assert packet.scope.write_scope == ["src/services/auth_service.py"]
    assert packet.validation_gates == ["pytest tests/unit/test_auth_service.py -q"]
    assert [item.path for item in packet.context_bundle] == [
        "PROJECT-HANDBOOK.md",
        ".specify/project-map/ARCHITECTURE.md",
        ".specify/project-map/WORKFLOWS.md",
        ".specify/project-map/OPERATIONS.md",
        ".specify/project-map/TESTING.md",
        ".specify/testing/TESTING_CONTRACT.md",
        ".specify/testing/TESTING_PLAYBOOK.md",
        "src/contracts/auth.py",
    ]
    assert [item.read_order for item in packet.context_bundle] == list(range(1, 9))
    assert packet.context_bundle[0].kind == "handbook"
    assert packet.context_bundle[-1].kind == "task_reference"
    assert "PROJECT-HANDBOOK.md" in packet.scope.read_scope
    assert ".specify/testing/TESTING_PLAYBOOK.md" in packet.scope.read_scope
    assert packet.platform_guardrails == [
        "supported_platforms: windows, linux",
        "require conditional compilation for unix-only APIs",
    ]
    assert packet.handoff_requirements[-2:] == [
        "send task_started before long-running work",
        "write structured result handoff before idling",
    ]


def test_compile_worker_task_packet_accepts_materialized_task_input(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / "PROJECT-HANDBOOK.md").write_text("# Handbook\n", encoding="utf-8")
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST preserve the runtime contract\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="BLL-lane",
        task_body="[US1] Refactor BLL lane in src/bll_manager.py",
    )

    assert packet.task_id == "BLL-lane"
    assert packet.story_id == "US1"
    assert packet.scope.write_scope == ["src/bll_manager.py"]
    assert packet.context_bundle[0].path == "PROJECT-HANDBOOK.md"
