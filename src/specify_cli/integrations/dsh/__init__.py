"""DeepSeek Harness integration."""

from __future__ import annotations

from ..base import SkillsIntegration


class DshIntegration(SkillsIntegration):
    """Install workflow skills for DeepSeek Harness."""

    key = "dsh"
    config = {
        "name": "DeepSeek Harness",
        "folder": ".dsh/",
        "commands_subdir": "skills",
        "install_url": "https://github.com/deepseek-ai/deepseek-harness#run",
        "requires_cli": True,
        "shared_project_skills": True,
        "flat_project_skills": True,
    }
    registrar_config = {
        "dir": ".dsh/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    context_file = "AGENTS.md"
