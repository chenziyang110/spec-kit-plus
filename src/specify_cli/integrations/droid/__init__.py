"""Factory Droid integration."""

from __future__ import annotations

from ..base import SkillsIntegration


class DroidIntegration(SkillsIntegration):
    """Install workflow skills for Factory Droid."""

    key = "droid"
    config = {
        "name": "Factory Droid",
        "folder": ".factory/",
        "commands_subdir": "skills",
        "install_url": "https://docs.factory.com/droid-cli/quickstart",
        "requires_cli": True,
        "shared_project_skills": True,
    }
    registrar_config = {
        "dir": ".factory/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    context_file = "AGENTS.md"
