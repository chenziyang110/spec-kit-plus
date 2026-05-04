from pathlib import Path

import pytest

from specify_cli.execution.packet_compiler import compile_worker_task_packet
from specify_cli.execution.packet_validator import PacketValidationError


def test_compile_worker_task_packet_merges_constitution_plan_and_task_sources(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-map" / "root").mkdir(parents=True)
    (project_root / ".specify" / "testing").mkdir(parents=True)
    (project_root / "PROJECT-HANDBOOK.md").write_text("# Handbook\n", encoding="utf-8")
    (project_root / ".specify" / "project-map" / "root" / "ARCHITECTURE.md").write_text(
        "# Architecture\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-map" / "root" / "WORKFLOWS.md").write_text(
        "# Workflows\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-map" / "root" / "OPERATIONS.md").write_text(
        "# Operations\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-map" / "root" / "TESTING.md").write_text(
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
    (project_root / ".specify" / "testing" / "COVERAGE_BASELINE.json").write_text(
        '{"schema_version": 1, "modules": []}\n',
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
        ".specify/project-map/root/ARCHITECTURE.md",
        ".specify/project-map/root/WORKFLOWS.md",
        ".specify/project-map/root/OPERATIONS.md",
        ".specify/project-map/root/TESTING.md",
        ".specify/testing/TESTING_CONTRACT.md",
        ".specify/testing/TESTING_PLAYBOOK.md",
        ".specify/testing/COVERAGE_BASELINE.json",
        "src/contracts/auth.py",
    ]
    assert [item.read_order for item in packet.context_bundle] == list(range(1, 10))
    assert packet.context_bundle[0].kind == "handbook"
    assert packet.context_bundle[-1].kind == "task_reference"
    assert "PROJECT-HANDBOOK.md" in packet.scope.read_scope
    assert ".specify/testing/TESTING_PLAYBOOK.md" in packet.scope.read_scope
    assert ".specify/testing/COVERAGE_BASELINE.json" in packet.scope.read_scope
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
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_bll_manager.py -q",
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
    assert packet.validation_gates == ["pytest tests/unit/test_bll_manager.py -q"]


def test_compile_worker_task_packet_preserves_testing_control_plane_context(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "testing").mkdir(parents=True)
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
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
    (project_root / ".specify" / "testing" / "COVERAGE_BASELINE.json").write_text(
        '{"schema_version": 1, "modules": []}\n',
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

    context_by_path = {item.path: item for item in packet.context_bundle}
    assert ".specify/testing/TESTING_CONTRACT.md" in packet.scope.read_scope
    assert ".specify/testing/TESTING_PLAYBOOK.md" in packet.scope.read_scope
    assert ".specify/testing/COVERAGE_BASELINE.json" in packet.scope.read_scope
    assert (
        ".specify/testing/TESTING_CONTRACT.md" in context_by_path
    ), "testing contract must remain in the execution context bundle"
    assert (
        ".specify/testing/TESTING_PLAYBOOK.md" in context_by_path
    ), "testing playbook must remain in the execution context bundle"
    assert (
        ".specify/testing/COVERAGE_BASELINE.json" in context_by_path
    ), "coverage baseline must remain in the execution context bundle"
    testing_contract = context_by_path[".specify/testing/TESTING_CONTRACT.md"]
    testing_playbook = context_by_path[".specify/testing/TESTING_PLAYBOOK.md"]
    coverage_baseline = context_by_path[".specify/testing/COVERAGE_BASELINE.json"]
    assert testing_contract.kind == "testing_contract"
    assert testing_contract.required_for == ["validation", "forbidden_drift"]
    assert testing_contract.must_read is True
    assert (
        testing_contract.selection_reason
        == "testing contract constrains what counts as complete"
    )
    assert testing_playbook.kind == "testing_playbook"
    assert testing_playbook.required_for == ["validation"]
    assert testing_playbook.must_read is True
    assert (
        testing_playbook.selection_reason
        == "testing playbook provides runnable verification commands"
    )
    assert coverage_baseline.kind == "coverage_baseline"
    assert coverage_baseline.required_for == ["validation"]
    assert coverage_baseline.must_read is True
    assert (
        coverage_baseline.selection_reason
        == "coverage baseline captures current covered-module status"
    )


def test_compile_worker_task_packet_requires_explicit_validation_gates(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / "PROJECT-HANDBOOK.md").write_text("# Handbook\n", encoding="utf-8")
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
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py\n",
        encoding="utf-8",
    )

    with pytest.raises(PacketValidationError) as exc:
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T017",
        )

    assert exc.value.code == "DP1"
    assert "validation_gates" in exc.value.message
