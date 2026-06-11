"""Consistency checks for agent configuration across runtime surfaces."""

import re
from pathlib import Path

from specify_cli import AGENT_CONFIG, AI_ASSISTANT_ALIASES, AI_ASSISTANT_HELP, _get_skills_dir
from specify_cli.integrations import get_integration
from specify_cli.extensions import CommandRegistrar


REPO_ROOT = Path(__file__).resolve().parent.parent


def _compact_assignment_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


class TestAgentConfigConsistency:
    """Ensure agent config paths stay synchronized across runtime and registrar surfaces."""

    def test_get_skills_dir_uses_agent_config_for_moved_skill_agents(self, tmp_path):
        """Skills-dir resolution should follow the active agent config for moved skill agents."""
        assert _get_skills_dir(tmp_path, "agy") == tmp_path / ".agents" / "skills"
        assert _get_skills_dir(tmp_path, "cursor-agent") == tmp_path / ".cursor" / "skills"
        assert _get_skills_dir(tmp_path, "trae") == tmp_path / ".trae" / "skills"
        assert _get_skills_dir(tmp_path, "vibe") == tmp_path / ".vibe" / "skills"
        assert _get_skills_dir(tmp_path, "codex") == tmp_path / ".codex" / "skills"

    def test_runtime_config_paths_for_nonstandard_agents(self):
        """Runtime config should keep nonstandard command and skill directories synchronized."""
        expected = {
            "kiro-cli": (".kiro/", "prompts"),
            "codex": (".codex/", "skills"),
            "agy": (".agents/", "skills"),
            "cursor-agent": (".cursor/", "skills"),
            "vibe": (".vibe/", "skills"),
            "tabnine": (".tabnine/agent/", "commands"),
            "kimi": (".kimi/", "skills"),
            "trae": (".trae/", "skills"),
            "pi": (".pi/", "prompts"),
            "iflow": (".iflow/", "commands"),
            "mimo": (".mimocode/", "commands"),
        }

        for agent_key, (folder, commands_subdir) in expected.items():
            assert AGENT_CONFIG[agent_key]["folder"] == folder, agent_key
            assert AGENT_CONFIG[agent_key]["commands_subdir"] == commands_subdir, agent_key
        assert "q" not in AGENT_CONFIG
        assert AGENT_CONFIG["tabnine"]["requires_cli"] is True
        assert AGENT_CONFIG["tabnine"]["install_url"] is not None
        assert AGENT_CONFIG["kimi"]["requires_cli"] is True
        assert AGENT_CONFIG["trae"]["requires_cli"] is False
        assert AGENT_CONFIG["trae"]["install_url"] is None
        assert AGENT_CONFIG["pi"]["requires_cli"] is True
        assert AGENT_CONFIG["pi"]["install_url"] is not None
        assert AGENT_CONFIG["iflow"]["requires_cli"] is True
        assert AGENT_CONFIG["mimo"]["requires_cli"] is True
        assert AGENT_CONFIG["mimo"]["install_url"] == "https://mimo.xiaomi.com/mimocode/start"

    def test_extension_registrar_configs_for_nonstandard_agents(self):
        """Extension command registrar should target each agent's command surface."""
        expected = {
            "kiro-cli": {"dir": ".kiro/prompts"},
            "codex": {"dir": ".codex/skills", "extension": "/SKILL.md"},
            "agy": {"dir": ".agents/skills", "extension": "/SKILL.md"},
            "cursor-agent": {"dir": ".cursor/skills", "extension": "/SKILL.md"},
            "vibe": {"dir": ".vibe/skills", "extension": "/SKILL.md"},
            "tabnine": {"dir": ".tabnine/agent/commands", "format": "toml", "args": "{{args}}", "extension": ".toml"},
            "kimi": {"dir": ".kimi/skills", "extension": "/SKILL.md"},
            "trae": {"dir": ".trae/skills", "format": "markdown", "args": "$ARGUMENTS", "extension": "/SKILL.md"},
            "pi": {"dir": ".pi/prompts", "format": "markdown", "args": "$ARGUMENTS", "extension": ".md"},
            "iflow": {"dir": ".iflow/commands", "format": "markdown", "args": "$ARGUMENTS"},
            "mimo": {"dir": ".mimocode/commands", "format": "markdown", "args": "$ARGUMENTS", "extension": ".md"},
        }

        cfg = CommandRegistrar.AGENT_CONFIGS
        for agent_key, expected_fields in expected.items():
            assert agent_key in cfg
            for field, value in expected_fields.items():
                assert cfg[agent_key][field] == value, f"{agent_key}.{field}"
        assert "q" not in cfg

    def test_vibe_agent_context_scripts_use_root_agents_file(self):
        """Vibe context updates should target root AGENTS.md like its integration metadata."""
        bash_text = (REPO_ROOT / "scripts" / "bash" / "update-agent-context.sh").read_text(encoding="utf-8")
        pwsh_text = (REPO_ROOT / "scripts" / "powershell" / "update-agent-context.ps1").read_text(encoding="utf-8")
        bash_wrapper = (
            REPO_ROOT / "src" / "specify_cli" / "integrations" / "vibe" / "scripts" / "update-context.sh"
        ).read_text(encoding="utf-8")
        pwsh_wrapper = (
            REPO_ROOT / "src" / "specify_cli" / "integrations" / "vibe" / "scripts" / "update-context.ps1"
        ).read_text(encoding="utf-8")

        assert 'VIBE_FILE="$AGENTS_FILE"' in _compact_assignment_text(bash_text)
        assert "$VIBE_FILE=Join-Path$REPO_ROOT'AGENTS.md'" in _compact_assignment_text(pwsh_text)
        assert "VIBE_LEGACY_FILE" in bash_text
        assert "VIBE_LEGACY_FILE" in pwsh_text
        assert "AGENTS.md" in bash_wrapper
        assert "AGENTS.md" in pwsh_wrapper
        assert ".vibe/agents/specify-agents.md" not in bash_wrapper
        assert ".vibe/agents/specify-agents.md" not in pwsh_wrapper

    def test_codex_includes_team_template_but_claude_does_not(self):
        """The Codex-only team surface should not leak into non-Codex template lists."""
        codex = get_integration("codex")
        claude = get_integration("claude")

        assert codex is not None
        assert claude is not None
        assert any(path.name == "team.md" for path in codex.list_command_templates())
        assert all(path.name != "team.md" for path in claude.list_command_templates())

    def test_init_ai_help_includes_roo_and_kiro_alias(self):
        """CLI help text for --ai should stay in sync with agent config and alias guidance."""
        assert "roo" in AI_ASSISTANT_HELP
        for alias, target in AI_ASSISTANT_ALIASES.items():
            assert alias in AI_ASSISTANT_HELP
            assert target in AI_ASSISTANT_HELP

    def test_devcontainer_kiro_installer_uses_pinned_checksum(self):
        """Devcontainer installer should always verify Kiro installer via pinned SHA256."""
        post_create_text = (REPO_ROOT / ".devcontainer" / "post-create.sh").read_text(encoding="utf-8")

        assert 'KIRO_INSTALLER_SHA256="7487a65cf310b7fb59b357c4b5e6e3f3259d383f4394ecedb39acf70f307cffb"' in post_create_text
        assert "sha256sum -c -" in post_create_text
        assert "KIRO_SKIP_KIRO_INSTALLER_VERIFY" not in post_create_text

    def test_agent_context_scripts_use_kiro_cli(self):
        """Agent context scripts should advertise kiro-cli and not legacy q agent key."""
        bash_text = (REPO_ROOT / "scripts" / "bash" / "update-agent-context.sh").read_text(encoding="utf-8")
        pwsh_text = (REPO_ROOT / "scripts" / "powershell" / "update-agent-context.ps1").read_text(encoding="utf-8")

        assert "kiro-cli" in bash_text
        assert "kiro-cli" in pwsh_text
        assert "Amazon Q Developer CLI" not in bash_text
        assert "Amazon Q Developer CLI" not in pwsh_text

    # --- Tabnine CLI consistency checks ---

    def test_trae_in_agent_context_scripts(self):
        """Agent context scripts should target Trae context updates to its rules file."""
        bash_text = (REPO_ROOT / "scripts" / "bash" / "update-agent-context.sh").read_text(encoding="utf-8")
        pwsh_text = (REPO_ROOT / "scripts" / "powershell" / "update-agent-context.ps1").read_text(encoding="utf-8")
        bash_wrapper = (
            REPO_ROOT / "src" / "specify_cli" / "integrations" / "trae" / "scripts" / "update-context.sh"
        ).read_text(encoding="utf-8")
        pwsh_wrapper = (
            REPO_ROOT / "src" / "specify_cli" / "integrations" / "trae" / "scripts" / "update-context.ps1"
        ).read_text(encoding="utf-8")

        assert "trae" in bash_text
        assert "TRAE_FILE" in bash_text
        assert 'TRAE_FILE="$REPO_ROOT/.trae/rules/project_rules.md"' in _compact_assignment_text(bash_text)
        assert ".trae/rules/AGENTS.md" not in bash_text
        assert "trae" in pwsh_text
        assert "TRAE_FILE" in pwsh_text
        assert "$TRAE_FILE=Join-Path$REPO_ROOT'.trae/rules/project_rules.md'" in _compact_assignment_text(pwsh_text)
        assert ".trae/rules/AGENTS.md" not in pwsh_text
        assert ".trae/rules/project_rules.md" in bash_wrapper
        assert ".trae/rules/project_rules.md" in pwsh_wrapper
        assert ".trae/rules/AGENTS.md" not in bash_wrapper
        assert ".trae/rules/AGENTS.md" not in pwsh_wrapper

    def test_powershell_validate_set_includes_nonstandard_agents(self):
        """PowerShell update-agent-context ValidateSet should include nonstandard agent keys."""
        ps_text = (REPO_ROOT / "scripts" / "powershell" / "update-agent-context.ps1").read_text(encoding="utf-8")

        validate_set_match = re.search(r"\[ValidateSet\(([^)]*)\)\]", ps_text)
        assert validate_set_match is not None
        validate_set_values = re.findall(r"'([^']+)'", validate_set_match.group(1))

        for agent_key in ("kimi", "trae", "pi"):
            assert agent_key in validate_set_values

    def test_agent_context_scripts_include_simple_nonstandard_agents(self):
        """Agent context scripts should support nonstandard agents without bespoke path semantics."""
        bash_text = (REPO_ROOT / "scripts" / "bash" / "update-agent-context.sh").read_text(encoding="utf-8")
        pwsh_text = (REPO_ROOT / "scripts" / "powershell" / "update-agent-context.ps1").read_text(encoding="utf-8")

        assert "tabnine" in bash_text
        assert "TABNINE_FILE" in bash_text
        assert "tabnine" in pwsh_text
        assert "TABNINE_FILE" in pwsh_text
        assert "pi" in bash_text
        assert "Pi Coding Agent" in bash_text
        assert "pi" in pwsh_text
        assert "Pi Coding Agent" in pwsh_text
        assert "iflow" in bash_text
        assert "IFLOW_FILE" in bash_text
        assert "iflow" in pwsh_text
        assert "IFLOW_FILE" in pwsh_text
        assert "mimo" in bash_text
        assert "MiMo Code" in bash_text
        assert "mimo" in pwsh_text
        assert "MiMo Code" in pwsh_text

    def test_ai_help_includes_nonstandard_agents(self):
        """CLI help text for --ai should include nonstandard agent keys."""
        for agent_key in ("tabnine", "kimi", "trae", "pi", "iflow", "mimo"):
            assert agent_key in AI_ASSISTANT_HELP
