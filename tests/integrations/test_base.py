"""Tests for IntegrationOption, IntegrationBase, MarkdownIntegration, and primitives."""

from pathlib import Path

import pytest

from specify_cli.integrations.base import (
    IntegrationBase,
    IntegrationOption,
    MarkdownIntegration,
)
from specify_cli.integrations.manifest import IntegrationManifest
from .conftest import StubIntegration


SUBAGENT_DISPATCH_TRIGGERS = (
    "## mandatory subagent execution",
    "choose_subagent_dispatch",
    "choose_evidence_lane_dispatch",
    "choose_ui_reference_lane_dispatch",
    "execution_model: subagent-mandatory",
    "execution model: `subagents-first`",
    "dispatch_shape: one-subagent",
    "dispatch `one-subagent`",
    "parallel-subagents",
    "subagent-assisted",
    "native-subagents",
    "spawn_agent",
    "task tool",
)


def _generated_command_name(path):
    name = path.name.lower()
    if name == "skill.md":
        return path.parent.name.removeprefix("sp-")
    return (
        name.removeprefix("sp.")
        .removesuffix(".agent.md")
        .removesuffix(".toml")
        .removesuffix(".md")
    )


def _assert_subagent_using_surfaces_have_discovery(paths):
    checked: set[str] = set()

    for path in paths:
        content = path.read_text(encoding="utf-8").lower()
        command_name = _generated_command_name(path)
        if command_name == "fast":
            continue
        if not any(trigger in content for trigger in SUBAGENT_DISPATCH_TRIGGERS):
            continue
        checked.add(command_name)
        assert "native subagent capability discovery" in content, f"{path} lacks discovery guidance"
        assert "do not record `subagent-blocked`" in content, f"{path} lacks blocked-before-discovery guard"

    assert {"specify", "plan", "tasks", "implement", "debug", "quick", "map-scan", "map-build", "map-update"} <= checked


def _assert_canonical_cognition_intake_contract(content: str) -> None:
    normalized = " ".join(
        content.replace('\\"', '"').replace("\\n", "\n").split()
    ).lower()

    for required in (
        "project-cognition compass",
        "project-cognition query",
        "--query-plan",
        "lexicon -> semantic_intake -> query",
        "alias catalog",
        "semantic_intake",
        "workflow_intent",
        "normalized_query",
        "intent_facets",
        "negative_constraints",
        "alias_interpretations",
        '{"alias": "<user term>", "meaning": "<project term>", "confidence": "medium"}',
        "selected_concepts",
        "rejected_concepts",
        "concept_decisions",
        "covered_facets",
        "missing_facets",
        "match_sources",
        "lexicon_generation_id",
        "minimal_live_reads",
        "first_pass_paths",
        "coverage_diagnostics",
        "repository_search_terms",
        "project-language search terms",
        "do not search only the raw user words",
        "warnings",
        "repair_hints",
        "query_plan",
        "errors",
        "expected_shape",
        "readiness",
        "task-local bundle",
        "semantic_work_contract_begin",
        "workcontract v1",
        "semantic-intake",
        "permissiondecision",
        "maximum_without_live_evidence",
        "learningcontract",
        "single unified entrypoint",
        "do not choose debug, implement, plan, or research from the user's raw words",
        "do not claim root cause, fixed, complete, or release-safe",
        "semantic_work_contract_end",
    ):
        assert required in normalized

    assert '"alias_interpretations": ["' not in normalized


class TestIntegrationOption:
    def test_defaults(self):
        opt = IntegrationOption(name="--flag")
        assert opt.name == "--flag"
        assert opt.is_flag is False
        assert opt.required is False
        assert opt.default is None
        assert opt.help == ""

    def test_flag_option(self):
        opt = IntegrationOption(name="--skills", is_flag=True, default=True, help="Enable skills")
        assert opt.is_flag is True
        assert opt.default is True
        assert opt.help == "Enable skills"

    def test_required_option(self):
        opt = IntegrationOption(name="--commands-dir", required=True, help="Dir path")
        assert opt.required is True

    def test_frozen(self):
        opt = IntegrationOption(name="--x")
        with pytest.raises(AttributeError):
            opt.name = "--y"  # type: ignore[misc]


class TestIntegrationBase:
    def test_key_and_config(self):
        i = StubIntegration()
        assert i.key == "stub"
        assert i.config["name"] == "Stub Agent"
        assert i.registrar_config["format"] == "markdown"
        assert i.context_file == "STUB.md"

    def test_options_default_empty(self):
        assert StubIntegration.options() == []

    def test_shared_commands_dir(self):
        i = StubIntegration()
        cmd_dir = i.shared_commands_dir()
        assert cmd_dir is not None
        assert cmd_dir.is_dir()

    def test_setup_uses_shared_templates(self, tmp_path):
        i = StubIntegration()
        manifest = IntegrationManifest("stub", tmp_path)
        created = i.setup(tmp_path, manifest)
        assert len(created) > 0
        command_dir = tmp_path / ".stub" / "commands"
        command_files = [f for f in created if f.parent == command_dir]
        assert command_files
        for f in command_files:
            assert f.parent == tmp_path / ".stub" / "commands"
            assert f.name.startswith("sp.")
            assert f.name.endswith(".md")

    def test_map_workflows_include_shared_subagent_capability_discovery(self, tmp_path):
        i = StubIntegration()
        manifest = IntegrationManifest("stub", tmp_path)
        i.setup(tmp_path, manifest)

        for name in ("map-scan", "map-build", "map-update"):
            content = (tmp_path / ".stub" / "commands" / f"sp.{name}.md").read_text(encoding="utf-8").lower()
            assert "map subagent capability discovery" in content
            assert "native subagent capability discovery" in content
            assert "do not record `subagent-blocked`" in content
            assert "exact unavailable or unsafe surface" in content

    def test_all_generated_subagent_workflows_include_capability_discovery(self, tmp_path):
        i = StubIntegration()
        manifest = IntegrationManifest("stub", tmp_path)
        i.setup(tmp_path, manifest)

        _assert_subagent_using_surfaces_have_discovery((tmp_path / ".stub" / "commands").glob("sp.*.md"))

    def test_setup_copies_templates(self, tmp_path, monkeypatch):
        tpl = tmp_path / "_templates"
        tpl.mkdir()
        (tpl / "plan.md").write_text("plan content", encoding="utf-8")
        (tpl / "specify.md").write_text("spec content", encoding="utf-8")

        i = StubIntegration()
        monkeypatch.setattr(type(i), "list_command_templates", lambda self: sorted(tpl.glob("*.md")))
        monkeypatch.setattr(type(i), "shared_command_references_dir", lambda self: None)

        project = tmp_path / "project"
        project.mkdir()
        created = i.setup(project, IntegrationManifest("stub", project))
        assert len(created) == 2
        assert (project / ".stub" / "commands" / "sp.plan.md").exists()
        assert (project / ".stub" / "commands" / "sp.specify.md").exists()

    def test_install_delegates_to_setup(self, tmp_path):
        i = StubIntegration()
        manifest = IntegrationManifest("stub", tmp_path)
        result = i.install(tmp_path, manifest)
        assert len(result) > 0

    def test_uninstall_delegates_to_teardown(self, tmp_path):
        i = StubIntegration()
        manifest = IntegrationManifest("stub", tmp_path)
        removed, skipped = i.uninstall(tmp_path, manifest)
        assert removed == []
        assert skipped == []


class TestMarkdownIntegration:
    def test_is_subclass_of_base(self):
        assert issubclass(MarkdownIntegration, IntegrationBase)

    def test_stub_is_markdown(self):
        assert isinstance(StubIntegration(), MarkdownIntegration)


class TestBasePrimitives:
    def test_shared_commands_dir_returns_path(self):
        i = StubIntegration()
        cmd_dir = i.shared_commands_dir()
        assert cmd_dir is not None
        assert cmd_dir.is_dir()

    def test_shared_templates_dir_returns_path(self):
        i = StubIntegration()
        tpl_dir = i.shared_templates_dir()
        assert tpl_dir is not None
        assert tpl_dir.is_dir()

    def test_list_command_templates_returns_md_files(self):
        i = StubIntegration()
        templates = i.list_command_templates()
        assert len(templates) > 0
        assert all(t.suffix == ".md" for t in templates)

    def test_command_filename_default(self):
        i = StubIntegration()
        assert i.command_filename("plan") == "sp.plan.md"

    def test_commands_dest(self, tmp_path):
        i = StubIntegration()
        dest = i.commands_dest(tmp_path)
        assert dest == tmp_path / ".stub" / "commands"

    def test_commands_dest_no_config_raises(self, tmp_path):
        class NoConfig(MarkdownIntegration):
            key = "noconfig"
        with pytest.raises(ValueError, match="config is not set"):
            NoConfig().commands_dest(tmp_path)

    def test_copy_command_to_directory(self, tmp_path):
        src = tmp_path / "source.md"
        src.write_text("content", encoding="utf-8")
        dest_dir = tmp_path / "output"
        result = IntegrationBase.copy_command_to_directory(src, dest_dir, "sp.plan.md")
        assert result == dest_dir / "sp.plan.md"
        assert result.read_text(encoding="utf-8") == "content"

    def test_record_file_in_manifest(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello", encoding="utf-8")
        m = IntegrationManifest("test", tmp_path)
        IntegrationBase.record_file_in_manifest(f, tmp_path, m)
        assert "f.txt" in m.files

    def test_write_file_and_record(self, tmp_path):
        m = IntegrationManifest("test", tmp_path)
        dest = tmp_path / "sub" / "f.txt"
        result = IntegrationBase.write_file_and_record("content", dest, tmp_path, m)
        assert result == dest
        assert dest.read_text(encoding="utf-8") == "content"
        assert "sub/f.txt" in m.files

    def test_setup_copies_shared_templates(self, tmp_path):
        i = StubIntegration()
        m = IntegrationManifest("stub", tmp_path)
        created = i.setup(tmp_path, m)
        assert len(created) > 0
        command_files = [f for f in created if f.parent.name == "commands"]
        assert command_files
        for f in command_files:
            assert f.parent.name == "commands"
            assert f.name.startswith("sp.")
            assert f.name.endswith(".md")

    def test_resolve_template_includes_supports_nested_partials(self, tmp_path):
        templates = tmp_path / "templates"
        templates.mkdir()
        nested = templates / "nested.md"
        nested.write_text("Nested body\n", encoding="utf-8")
        partial = templates / "partial.md"
        partial.write_text(
            "Partial start\n{{spec-kit-include: nested.md}}Partial end\n",
            encoding="utf-8",
        )
        root = templates / "root.md"
        root.write_text(
            "Top\n{{spec-kit-include: partial.md}}Bottom\n",
            encoding="utf-8",
        )

        resolved = IntegrationBase.resolve_template_includes(
            root.read_text(encoding="utf-8"),
            root.parent,
        )

        assert resolved == "Top\nPartial start\nNested body\nPartial end\nBottom\n"

    def test_resolve_template_includes_rejects_cycles(self, tmp_path):
        templates = tmp_path / "templates"
        templates.mkdir()
        first = templates / "first.md"
        second = templates / "second.md"
        first.write_text("{{spec-kit-include: second.md}}\n", encoding="utf-8")
        second.write_text("{{spec-kit-include: first.md}}\n", encoding="utf-8")

        with pytest.raises(ValueError, match="include cycle"):
            IntegrationBase.resolve_template_includes(
                first.read_text(encoding="utf-8"),
                first.parent,
            )

    def test_process_template_renders_workflow_contract_summary_from_frontmatter(self, tmp_path):
        template = tmp_path / "plan.md"
        template.write_text(
            "---\n"
            "description: Use when the spec package is ready for planning.\n"
            "workflow_contract:\n"
            "  when_to_use: The spec package is planning-ready.\n"
            "  primary_objective: Produce implementation design artifacts.\n"
            "  primary_outputs: plan.md, research.md, and quickstart.md.\n"
            "  default_handoff: /sp-tasks after planning is complete.\n"
            "scripts:\n"
            "  sh: scripts/bash/setup-plan.sh --json\n"
            "---\n\n"
            "## Objective\n\n"
            "Translate the specification into a planning package.\n",
            encoding="utf-8",
        )

        processed = IntegrationBase.process_template(
            template.read_text(encoding="utf-8"),
            "stub",
            "sh",
            template_path=template,
        )

        assert "## Workflow Contract Summary" in processed
        assert "- **When to use**: The spec package is planning-ready." in processed
        assert "- **Primary objective**: Produce implementation design artifacts." in processed
        assert "- **Primary outputs**: plan.md, research.md, and quickstart.md." in processed
        assert "- **Default handoff**: /sp-tasks after planning is complete." in processed
        assert "routing metadata only" in processed.lower()
        assert processed.index("## Workflow Contract Summary") < processed.index("## Objective")

    def test_command_reference_templates_are_discovered_from_workflow_stem(self, tmp_path, monkeypatch):
        refs_root: Path = tmp_path / "command-references"
        workflow_refs = refs_root / "plan"
        workflow_refs.mkdir(parents=True)
        (workflow_refs / "INDEX.md").write_text(
            "# Plan References\n\n- [details](details.md): Trigger: planning detail\n",
            encoding="utf-8",
        )
        (workflow_refs / "details.md").write_text(
            "Trigger: when planning needs details\n\n"
            "Purpose: exercise discovery\n\n"
            "Preserved Contract: keep the plan rules\n",
            encoding="utf-8",
        )

        i = StubIntegration()
        monkeypatch.setattr(type(i), "shared_command_references_dir", lambda self: refs_root, raising=False)

        assert [path.name for path in i.list_command_reference_templates("plan")] == [
            "INDEX.md",
            "details.md",
        ]
        assert i.list_command_reference_templates("specify") == []
        assert i.list_command_reference_templates("../plan") == []
        assert i.list_command_reference_templates("plan/details") == []
        assert i.list_command_reference_templates(r"plan\details") == []

    def test_render_command_reference_uses_owner_template_context(self, tmp_path):
        command = tmp_path / "plan.md"
        command.write_text(
            "---\n"
            "description: Plan command\n"
            "scripts:\n"
            "  sh: scripts/bash/setup-plan.sh --json\n"
            "---\n\n"
            "# Plan\n\n"
            "Main body for __AGENT__ using {SCRIPT}, {ARGS}, and {{invoke:tasks}}.\n",
            encoding="utf-8",
        )
        reference = tmp_path / "references" / "details.md"
        reference.parent.mkdir()
        reference.write_text(
            "Trigger: when planning detail is needed\n\n"
            "Purpose: verify owner context\n\n"
            "Preserved Contract: preserve command substitutions\n\n"
            "Use {SCRIPT}, {ARGS}, __AGENT__, and {{invoke:tasks}} here.\n",
            encoding="utf-8",
        )

        rendered = IntegrationBase.render_command_reference_content(
            reference.read_text(encoding="utf-8"),
            owner_template_raw=command.read_text(encoding="utf-8"),
            owner_template_path=command,
            reference_path=reference,
            agent_name="stub",
            script_type="sh",
            arg_placeholder="$ARGUMENTS",
            project_root=tmp_path,
        )

        assert "scripts/bash/setup-plan.sh --json" in rendered
        assert "$ARGUMENTS" in rendered
        assert "/sp.tasks" in rendered
        assert "Purpose: verify owner context" in rendered
        assert "Main body for" not in rendered
        assert "__AGENT__" not in rendered
        assert "{SCRIPT}" not in rendered
        assert "{ARGS}" not in rendered
        assert "{{invoke:tasks}}" not in rendered

    def test_render_command_reference_uses_only_renderer_context_frontmatter(
        self, tmp_path
    ):
        command = tmp_path / "plan.md"
        command.write_text(
            "---\n"
            "description: Plan command should not render in references\n"
            "workflow_contract:\n"
            "  when_to_use: UNIQUE WORKFLOW WHEN TEXT\n"
            "  primary_objective: UNIQUE WORKFLOW OBJECTIVE TEXT\n"
            "  primary_outputs: UNIQUE WORKFLOW OUTPUT TEXT\n"
            "  default_handoff: UNIQUE WORKFLOW HANDOFF TEXT\n"
            "scripts:\n"
            "  sh: scripts/bash/setup-plan.sh --json\n"
            "---\n\n"
            "# Plan\n\n"
            "Owner body should not render.\n",
            encoding="utf-8",
        )
        reference = tmp_path / "references" / "details.md"
        reference.parent.mkdir()
        reference.write_text(
            "UNIQUE REFERENCE PHRASE uses {SCRIPT}.\n",
            encoding="utf-8",
        )

        rendered = IntegrationBase.render_command_reference_content(
            reference.read_text(encoding="utf-8"),
            owner_template_raw=command.read_text(encoding="utf-8"),
            owner_template_path=command,
            reference_path=reference,
            agent_name="stub",
            script_type="sh",
            arg_placeholder="$ARGUMENTS",
            project_root=tmp_path,
        )

        assert "UNIQUE REFERENCE PHRASE" in rendered
        assert "scripts/bash/setup-plan.sh --json" in rendered
        assert "## Workflow Contract Summary" not in rendered
        assert "UNIQUE WORKFLOW WHEN TEXT" not in rendered
        assert "UNIQUE WORKFLOW OBJECTIVE TEXT" not in rendered
        assert "UNIQUE WORKFLOW OUTPUT TEXT" not in rendered
        assert "UNIQUE WORKFLOW HANDOFF TEXT" not in rendered

    def test_validate_no_unresolved_renderer_tokens_reports_path(self, tmp_path):
        path = tmp_path / "references" / "details.md"
        path.parent.mkdir()
        path.write_text("Use {SCRIPT}\n", encoding="utf-8")

        with pytest.raises(ValueError) as exc_info:
            IntegrationBase.validate_no_unresolved_renderer_tokens(
                path.read_text(encoding="utf-8"),
                path,
            )
        message = str(exc_info.value)
        assert "details.md" in message
        assert "{SCRIPT}" in message
