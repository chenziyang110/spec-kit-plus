from pathlib import Path

from specify_cli.execution.packet_compiler import compile_worker_task_packet


def test_compile_worker_task_packet_merges_constitution_plan_and_task_sources(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
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
