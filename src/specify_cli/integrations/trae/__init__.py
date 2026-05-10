"""Trae IDE integration."""

from ..base import IntegrationOption, SkillsIntegration


class TraeIntegration(SkillsIntegration):
    key = "trae"
    config = {
        "name": "Trae",
        "folder": ".trae/",
        "commands_subdir": "skills",
        "install_url": None,
        "requires_cli": False,
    }
    registrar_config = {
        "dir": ".trae/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    context_file = ".trae/rules/project_rules.md"
    multi_install_safe = True

    @classmethod
    def options(cls) -> list[IntegrationOption]:
        return [
            IntegrationOption(
                "--skills",
                is_flag=True,
                default=True,
                help="Install as agent skills (default for Trae)",
            ),
        ]
