"""Gemini CLI integration."""

from ..base import TomlIntegration
from .multi_agent import GeminiMultiAgentAdapter


class GeminiIntegration(TomlIntegration):
    key = "gemini"
    config = {
        "name": "Gemini CLI",
        "folder": ".gemini/",
        "commands_subdir": "commands",
        "install_url": "https://github.com/google-gemini/gemini-cli",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".gemini/commands",
        "format": "toml",
        "args": "{{args}}",
        "extension": ".toml",
    }
    context_file = "GEMINI.md"
    question_tool_config = {
        "tool_name": "ask_user",
        "question_limit": "up to 4 questions per call",
        "option_limit": "2-4 options for `choice` questions",
        "question_fields": ["header", "type", "question"],
        "option_fields": ["label", "description"],
        "extra_notes": [
            "Supported question types are `choice`, `yesno`, and `text`.",
            "Use `choice` by default for clarification and bounded selections; use `placeholder` only for `text` questions.",
        ],
    }


__all__ = ["GeminiIntegration", "GeminiMultiAgentAdapter"]
