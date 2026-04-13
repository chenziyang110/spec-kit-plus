"""Codex CLI integration — skills-based agent.

Codex uses the ``.agents/skills/sp-<name>/SKILL.md`` layout.
Commands are deprecated; ``--skills`` defaults to ``True``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import IntegrationOption, SkillsIntegration
from .multi_agent import CodexMultiAgentAdapter


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
                    "When running in Codex, treat Step 6's unified execution strategy selection as a runtime-aware escalation.\n"
                    "For each ready parallel batch:\n"
                    "- Apply the shared policy contract first: `parallel_batches <= 0` or overlapping write sets -> `single-agent`; otherwise `native-multi-agent` when `native_multi_agent`, otherwise `sidecar-runtime` when `sidecar_runtime_supported`, else `single-agent` fallback.\n"
                    "- Interpret `single-agent` as solo execution (single-worker sequential path).\n"
                    "- Interpret `native-multi-agent` as the native subagents path.\n"
                    "- Interpret `sidecar-runtime` as escalation via **`specify team`**.\n"
                    "- Decision order must stay fixed: `no-safe-batch` -> `native-supported` -> `native-missing` -> `fallback`.\n"
                    "- When you choose `sidecar-runtime`, call **`specify team auto-dispatch --feature-dir \"<FEATURE_DIR>\"`** instead of stopping at a recommendation.\n"
                    "- Follow a fixed order: capture the Step 1 `FEATURE_DIR`, inspect the next ready explicit parallel batch, run the auto-dispatch command, read the result, and only then fall back if the command reports a concrete blocker.\n"
                    "- Re-check the strategy after every join point instead of assuming the first choice still applies.\n"
                )
                self.write_file_and_record(
                    content + addendum,
                    implement_skill,
                    project_root,
                    manifest,
                )

        return created


__all__ = ["CodexIntegration", "CodexMultiAgentAdapter"]
