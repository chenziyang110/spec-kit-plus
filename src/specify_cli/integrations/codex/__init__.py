"""Codex CLI integration — skills-based agent.

Codex uses the ``.agents/skills/sp-<name>/SKILL.md`` layout.
Commands are deprecated; ``--skills`` defaults to ``True``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import IntegrationOption, SkillsIntegration


class CodexIntegration(SkillsIntegration):
    """Integration for OpenAI Codex CLI."""

    key = "codex"
    config = {
        "name": "Codex CLI",
        "folder": ".agents/",
        "commands_subdir": "skills",
        "install_url": "https://github.com/openai/codex",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".agents/skills",
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
                help="Install as agent skills (default for Codex)",
            ),
        ]

    def list_command_templates(self) -> list[Path]:
        """Return the shared skills plus the Codex-only team skill."""
        templates = list(super().list_command_templates())
        commands_dir = self.shared_commands_dir()
        if not commands_dir:
            return templates

        team_template = commands_dir / "team.md"
        if team_template.exists():
            templates.append(team_template)
        return sorted(templates, key=lambda path: path.name)

    def setup(
        self,
        project_root: Path,
        manifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        created = super().setup(
            project_root,
            manifest,
            parsed_options=parsed_options,
            **opts,
        )

        implement_skill = self.skills_dest(project_root) / "sp-implement" / "SKILL.md"
        if implement_skill in created and implement_skill.is_file():
            content = implement_skill.read_text(encoding="utf-8")
            marker = "## Codex Auto-Parallel Execution"
            if marker not in content:
                addendum = (
                    "\n"
                    "## Codex Auto-Parallel Execution\n\n"
                    "When running in Codex, treat Step 6's execution strategy selection as a runtime-aware escalation.\n"
                    "For each ready parallel batch:\n"
                    "- Solo execution (single-worker sequential path) is the default when the change is localized, write sets overlap, or the runtime cannot host subagents. Fall back to this path whenever the Codex team runtime is unavailable.\n"
                    "- Prefer **native subagents** when the batch is small, bounded, and has isolated write sets.\n"
                    "- Escalate to **`specify team`** when the batch needs durable coordination, explicit status tracking, or wider multi-lane recovery. The Codex runtime will route those batches into the team surface.\n"
                    "- Re-check the strategy after every join point instead of assuming the first choice still applies.\n"
                )
                self.write_file_and_record(
                    content + addendum,
                    implement_skill,
                    project_root,
                    manifest,
                )

        return created
