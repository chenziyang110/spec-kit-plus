"""ZCode integration."""

from __future__ import annotations

from ..base import IntegrationOption, SkillsIntegration


class ZcodeIntegration(SkillsIntegration):
    """Integration for ZCode Agent skills."""

    key = "zcode"
    config = {
        "name": "ZCode",
        "folder": ".zcode/",
        "commands_subdir": "skills",
        "install_url": "https://zcode.z.ai/en/docs/install",
        "requires_cli": False,
    }
    registrar_config = {
        "dir": ".zcode/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    context_file = "AGENTS.md"

    @classmethod
    def options(cls) -> list[IntegrationOption]:
        return [
            IntegrationOption(
                "--skills",
                is_flag=True,
                default=True,
                help="Install as agent skills (default for ZCode)",
            ),
        ]
