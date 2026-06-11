"""MiMo Code integration."""

from ..base import MarkdownIntegration
from .multi_agent import MimoMultiAgentAdapter


class MimoIntegration(MarkdownIntegration):
    key = "mimo"
    config = {
        "name": "MiMo Code",
        "folder": ".mimocode/",
        "commands_subdir": "commands",
        "install_url": "https://mimo.xiaomi.com/mimocode/start",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".mimocode/commands",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": ".md",
    }
    context_file = "AGENTS.md"


__all__ = ["MimoIntegration", "MimoMultiAgentAdapter"]
