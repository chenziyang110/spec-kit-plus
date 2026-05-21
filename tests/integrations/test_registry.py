"""Tests for INTEGRATION_REGISTRY — mechanics, completeness, and registrar alignment."""

import tomllib

import pytest

from specify_cli import _bootstrap_integration_context_file
from specify_cli.integrations import (
    INTEGRATION_REGISTRY,
    _register,
    get_integration,
)
from specify_cli.integrations.base import MarkdownIntegration
from specify_cli.integrations.manifest import IntegrationManifest
from .conftest import StubIntegration


# Every integration key that must be registered (Stage 2 + Stage 3 + Stage 4 + Stage 5).
ALL_INTEGRATION_KEYS = [
    "copilot",
    # Stage 3 — standard markdown integrations
    "claude", "qwen", "opencode", "junie", "kilocode", "auggie",
    "roo", "codebuddy", "qodercli", "amp", "shai", "bob", "trae",
    "pi", "iflow", "kiro-cli", "windsurf", "vibe", "cursor-agent",
    # Stage 4 — TOML integrations
    "gemini", "tabnine",
    # Stage 5 — skills, generic & option-driven integrations
    "codex", "kimi", "agy", "generic",
]


class TestRegistry:
    def test_registry_is_dict(self):
        assert isinstance(INTEGRATION_REGISTRY, dict)

    def test_register_and_get(self):
        stub = StubIntegration()
        _register(stub)
        try:
            assert get_integration("stub") is stub
        finally:
            INTEGRATION_REGISTRY.pop("stub", None)

    def test_get_missing_returns_none(self):
        assert get_integration("nonexistent-xyz") is None

    def test_register_empty_key_raises(self):
        class EmptyKey(MarkdownIntegration):
            key = ""
        with pytest.raises(ValueError, match="empty key"):
            _register(EmptyKey())

    def test_register_duplicate_raises(self):
        stub = StubIntegration()
        _register(stub)
        try:
            with pytest.raises(KeyError, match="already registered"):
                _register(StubIntegration())
        finally:
            INTEGRATION_REGISTRY.pop("stub", None)


class TestRegistryCompleteness:
    """Every expected integration must be registered."""

    @pytest.mark.parametrize("key", ALL_INTEGRATION_KEYS)
    def test_key_registered(self, key):
        assert key in INTEGRATION_REGISTRY, f"{key} missing from registry"


class TestRegistrarKeyAlignment:
    """Every integration key must have a matching AGENT_CONFIGS entry.

    ``generic`` is excluded because it has no fixed directory — its
    output path comes from ``--commands-dir`` at runtime.
    """

    @pytest.mark.parametrize(
        "key",
        [k for k in ALL_INTEGRATION_KEYS if k != "generic"],
    )
    def test_integration_key_in_registrar(self, key):
        from specify_cli.agents import CommandRegistrar
        assert key in CommandRegistrar.AGENT_CONFIGS, (
            f"Integration '{key}' is registered but has no AGENT_CONFIGS entry"
        )

    def test_no_stale_cursor_shorthand(self):
        """The old 'cursor' shorthand must not appear in AGENT_CONFIGS."""
        from specify_cli.agents import CommandRegistrar
        assert "cursor" not in CommandRegistrar.AGENT_CONFIGS

    def test_team_skill_is_not_global_template_surface(self):
        """The team skill should stay Codex-only instead of leaking to every integration."""
        codex = get_integration("codex")
        claude = get_integration("claude")

        assert codex is not None
        assert claude is not None
        assert any(path.name == "team.md" for path in codex.list_command_templates())
        assert all(path.name != "team.md" for path in claude.list_command_templates())

    @pytest.mark.parametrize(
        ("key", "folder", "commands_subdir", "registrar_dir", "context_file"),
        [
            ("amp", ".agents/", "commands", ".agents/commands", "AGENTS.md"),
            ("auggie", ".augment/", "commands", ".augment/commands", ".augment/rules/specify-rules.md"),
            ("bob", ".bob/", "commands", ".bob/commands", "AGENTS.md"),
            ("codebuddy", ".codebuddy/", "commands", ".codebuddy/commands", "CODEBUDDY.md"),
            ("iflow", ".iflow/", "commands", ".iflow/commands", "IFLOW.md"),
            ("junie", ".junie/", "commands", ".junie/commands", ".junie/AGENTS.md"),
            ("kilocode", ".kilocode/", "workflows", ".kilocode/workflows", ".kilocode/rules/specify-rules.md"),
            ("kiro-cli", ".kiro/", "prompts", ".kiro/prompts", "AGENTS.md"),
            ("opencode", ".opencode/", "command", ".opencode/command", "AGENTS.md"),
            ("pi", ".pi/", "prompts", ".pi/prompts", "AGENTS.md"),
            ("qodercli", ".qoder/", "commands", ".qoder/commands", "QODER.md"),
            ("qwen", ".qwen/", "commands", ".qwen/commands", "QWEN.md"),
            ("roo", ".roo/", "commands", ".roo/commands", ".roo/rules/specify-rules.md"),
            ("shai", ".shai/", "commands", ".shai/commands", "SHAI.md"),
            ("windsurf", ".windsurf/", "workflows", ".windsurf/workflows", ".windsurf/rules/specify-rules.md"),
        ],
    )
    def test_reduced_markdown_matrix_preserves_agent_metadata(
        self,
        key,
        folder,
        commands_subdir,
        registrar_dir,
        context_file,
    ):
        integration = get_integration(key)

        assert integration is not None
        assert integration.config["folder"] == folder
        assert integration.config["commands_subdir"] == commands_subdir
        assert integration.registrar_config["dir"] == registrar_dir
        assert integration.registrar_config["format"] == "markdown"
        assert integration.registrar_config["args"] == "$ARGUMENTS"
        assert integration.registrar_config["extension"] == ".md"
        assert integration.context_file == context_file

    @pytest.mark.parametrize(
        ("key", "folder", "commands_subdir", "registrar_dir", "context_file"),
        [
            ("agy", ".agents/", "skills", ".agents/skills", "AGENTS.md"),
            ("cursor-agent", ".cursor/", "skills", ".cursor/skills", ".cursor/rules/specify-rules.mdc"),
            ("kimi", ".kimi/", "skills", ".kimi/skills", "KIMI.md"),
            ("trae", ".trae/", "skills", ".trae/skills", ".trae/rules/project_rules.md"),
            ("vibe", ".vibe/", "skills", ".vibe/skills", "AGENTS.md"),
        ],
    )
    def test_reduced_skills_matrix_preserves_agent_metadata(
        self,
        key,
        folder,
        commands_subdir,
        registrar_dir,
        context_file,
    ):
        integration = get_integration(key)

        assert integration is not None
        assert integration.config["folder"] == folder
        assert integration.config["commands_subdir"] == commands_subdir
        assert integration.registrar_config["dir"] == registrar_dir
        assert integration.registrar_config["format"] == "markdown"
        assert integration.registrar_config["args"] == "$ARGUMENTS"
        assert integration.registrar_config["extension"] == "/SKILL.md"
        assert integration.context_file == context_file

    def test_reduced_toml_matrix_preserves_tabnine_metadata(self):
        integration = get_integration("tabnine")

        assert integration is not None
        assert integration.config["folder"] == ".tabnine/agent/"
        assert integration.config["commands_subdir"] == "commands"
        assert integration.registrar_config["dir"] == ".tabnine/agent/commands"
        assert integration.registrar_config["format"] == "toml"
        assert integration.registrar_config["args"] == "{{args}}"
        assert integration.registrar_config["extension"] == ".toml"
        assert integration.context_file == "TABNINE.md"

    def test_tabnine_toml_setup_smoke(self, tmp_path):
        integration = get_integration("tabnine")
        assert integration is not None

        manifest = IntegrationManifest("tabnine", tmp_path)
        integration.setup(tmp_path, manifest)
        _bootstrap_integration_context_file(tmp_path, integration, manifest)

        command_files = sorted(integration.commands_dest(tmp_path).glob("*.toml"))
        assert command_files

        parsed = tomllib.loads(command_files[0].read_text(encoding="utf-8"))
        assert parsed["description"]
        assert parsed["prompt"]

        assert (tmp_path / "TABNINE.md").is_file()

        scripts_dir = tmp_path / ".specify" / "integrations" / "tabnine" / "scripts"
        assert (scripts_dir / "update-context.sh").is_file()
        assert (scripts_dir / "update-context.ps1").is_file()
