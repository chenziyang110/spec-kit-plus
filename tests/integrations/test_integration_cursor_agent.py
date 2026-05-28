"""Tests for CursorAgentIntegration."""


def test_cursor_skills_init_installs_command_and_passive_skills(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "cursor-skills-runtime"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "cursor-agent", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai cursor-agent failed: {result.output}"
    assert (target / ".cursor" / "skills" / "sp-plan" / "SKILL.md").exists()
    assert (target / ".cursor" / "skills" / "spec-kit-workflow-routing" / "SKILL.md").exists()


def test_cursor_generated_sp_quick_confirms_understanding_before_execution(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "cursor-quick-runtime"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "cursor-agent", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai cursor-agent failed: {result.output}"

    skill_path = target / ".cursor" / "skills" / "sp-quick" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert ".specify/memory/constitution.md" in content
    assert "understanding checkpoint" in content
    assert "understanding_confirmed: true" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "cursor leader gate" in content
    assert "cursor subagent execution" in content
    assert "do not proceed to code edits, broad repository analysis, delegation, or validation commands until `understanding_confirmed: true` is recorded" in content
    assert "subagent-blocked" in content
    assert "read `.specify/memory/constitution.md` first if it exists" in content
    assert "do **not** perform broad repository analysis" in content
    assert "use cursor's native subagent path for bounded lanes when available" in content
    assert "start execution routing only after `status.md` exists and `understanding_confirmed: true` is recorded" in content
    assert "materially improve throughput" in content
    assert "managed-team" in content
    assert "subagent-blocked" in content
    assert "use cursor's native subagent path" in content
    assert "status.md" in content
    assert "continue automatically until the quick task is complete or a concrete blocker prevents further safe progress" in content
    assert "attempt the smallest safe recovery step before declaring the task blocked" in content
    assert "retry_attempts" in content
    assert "blocker_reason" in content
    assert "subagent dispatch contract" in content
    assert "subagent result contract" in content
    assert "result handoff path" in content
    assert "done_with_concerns" in content
    assert "needs_context" in content
    assert "workertaskresult" in content
    assert ".planning/quick/<id>-<slug>/status.md" in content
    assert ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json" in content
    assert ".planning/quick/<slug>" not in content


def test_cursor_runtime_skills_hard_gate_project_cognition_reads(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "cursor-project-cognition-gate"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "cursor-agent", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai cursor-agent failed: {result.output}"

    for rel in (
        ".cursor/skills/sp-constitution/SKILL.md",
        ".cursor/skills/sp-implement/SKILL.md",
        ".cursor/skills/sp-debug/SKILL.md",
        ".cursor/skills/sp-quick/SKILL.md",
    ):
        content = (target / rel).read_text(encoding="utf-8").lower()
        assert "map-scan" in content
        assert "map-build" in content
        for stale_phrase in (
            "path-index-" + "incomplete",
            "unadoptable " + "coverage gaps",
            "blocked by " + "unadoptable",
            "unadoptable " + "path-index gaps",
            "map " + "repair",
            "first-baseline " + "map " + "repair",
            "user explicitly requested " + "map " + "repair",
            "reported map-maintenance action as follow-up " + "unless",
            "when the user wants " + "map " + "repair",
            "missing or " + "stale",
            "follow-up map maintenance when " + "useful",
            "recommend sp-map-update or " + "sp-map-scan -> sp-map-build",
            "recommend map-update or " + "map-scan -> map-build",
            "user wants " + "repair",
            "the user wants " + "repair",
            "path-index " + "incomplete",
        ):
            assert stale_phrase not in content
        if "sp-constitution" in rel:
            assert "stale or weak for an existing usable baseline" in content
            assert "recommend `/sp-map-update`" in content
            assert "first/missing/unusable baseline" in content
            assert "schema failure" in content
            assert "zero active-generation `path_index` rows" in content
            assert "`explicit_rebuild_requested`" in content
            assert "`baseline_identity_invalid`" in content
            continue
        assert (
            "use map-update for ordinary existing-baseline gaps. use map-scan -> map-build "
            "only for first/missing/unusable baseline, schema failure, zero active-generation "
            "path_index rows, explicit_rebuild_requested, or baseline_identity_invalid"
        ) in content
        assert "entry advisory is not closeout ownership" in content
        assert "workflow-owned mutation closeout" in content
        assert "inline project cognition update" in content
        assert "sp-map-update is for manual/external maintenance" in content
        assert "crucial first step" in content
        if "sp-debug" in rel:
            assert "query --intent debug" in content
            assert "debug session state" in content
            assert "debug-handbook.md" not in content
            assert "debug-workflow-contract" not in content
        else:
            assert "query --intent implement" in content
            assert "task-local bundle" in content
            assert "minimal_live_reads" in content
            assert "build-handbook.md" not in content
            assert "build-workflow-contract" not in content


def test_cursor_closeout_advisory_uses_exact_heading_marker(tmp_path):
    from specify_cli.integrations.cursor_agent import CursorAgentIntegration
    from specify_cli.integrations.manifest import IntegrationManifest

    integration = CursorAgentIntegration()
    manifest = IntegrationManifest("cursor-agent", tmp_path)
    skill_path = tmp_path / ".cursor" / "skills" / "sp-implement" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "\n".join(
            (
                "# Skill",
                "## Cursor Project Cognition Closeout Advisory Notes",
                "Existing related-but-different closeout note.",
                "## Orchestration Model",
                "Leader text.",
            )
        ),
        encoding="utf-8",
    )

    first = integration._append_runtime_handbook_compatibility_to_file(
        project_root=tmp_path,
        manifest=manifest,
        path=skill_path,
        command_name="implement",
    )
    assert first == skill_path
    content = skill_path.read_text(encoding="utf-8")
    assert content.count("## Cursor Project Cognition Closeout Advisory Notes") == 1
    assert (
        sum(
            line.strip() == "## Cursor Project Cognition Closeout Advisory"
            for line in content.splitlines()
        )
        == 1
    )
    assert "Entry advisory is not closeout ownership" in content

    second = integration._append_runtime_handbook_compatibility_to_file(
        project_root=tmp_path,
        manifest=manifest,
        path=skill_path,
        command_name="implement",
    )
    assert second is None
    updated_lines = skill_path.read_text(encoding="utf-8").splitlines()
    assert (
        sum(
            line.strip() == "## Cursor Project Cognition Closeout Advisory"
            for line in updated_lines
        )
        == 1
    )
