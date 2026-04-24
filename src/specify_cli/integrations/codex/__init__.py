"""Codex CLI integration — skills-based agent.

Codex uses the ``.codex/skills/sp-<name>/SKILL.md`` layout.
Commands are deprecated; ``--skills`` defaults to ``True``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import IntegrationOption, SkillsIntegration
from ...orchestration import CapabilitySnapshot
from .multi_agent import CodexMultiAgentAdapter


class CodexIntegration(SkillsIntegration):
    """Integration for OpenAI Codex CLI."""

    key = "codex"
    config = {
        "name": "Codex CLI",
        "folder": ".codex/",
        "commands_subdir": "skills",
        "install_url": "https://github.com/openai/codex",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".codex/skills",
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
        """Return the shared skills plus the Codex-only runtime skills."""
        templates = list(super().list_command_templates())
        commands_dir = self.shared_commands_dir()
        if not commands_dir:
            return templates

        for name in ("team.md", "implement-teams.md"):
            template = commands_dir / name
            if template.exists():
                templates.append(template)
        return sorted(templates, key=lambda path: path.name)

    def setup(
        self,
        project_root: Path,
        manifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        # Run base setup which handles the core sp-skill creation and default augmentation
        # for implement, debug, quick, plan, tasks, etc.
        return super().setup(
            project_root,
            manifest,
            parsed_options=parsed_options,
            **opts,
        )

    def augment_generated_skills(
        self,
        created: list[Path],
        project_root: Path,
        manifest,
        skills_dir: Path,
    ) -> None:
        """Apply Codex-only leader/runtime guidance to generated skills."""
        agent_name_full = self.config.get("name", self.key.capitalize())
        agent_name = agent_name_full.replace(" CLI", "")
        codex_snapshot = CapabilitySnapshot(
            integration_key=self.key,
            native_multi_agent=True,
            sidecar_runtime_supported=True,
            structured_results=False,
            durable_coordination=True,
            native_worker_surface="spawn_agent",
            delegation_confidence="high",
            model_family="codex",
            runtime_probe_succeeded=True,
        )

        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-specify" / "SKILL.md",
            f"## {agent_name} Native Multi-Agent Execution",
            (
                "\n"
                f"## {agent_name} Native Multi-Agent Execution\n\n"
                f"When running `sp-specify` in {agent_name}, prefer native worker delegation whenever the selected strategy is `native-multi-agent`.\n"
                f"- Use `spawn_agent` (or native handoffs) for bounded lanes such as repository and local context analysis, references analysis, and ambiguity/risk analysis.\n"
                f"- Use `wait_agent` only at the documented join points before capability decomposition and before writing `spec.md`, `alignment.md`, and `context.md`.\n"
                f"- Use `close_agent` after integrating finished worker results.\n"
                "- Keep the shared workflow language integration-neutral in user-visible output.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-plan" / "SKILL.md",
            f"## {agent_name} Native Multi-Agent Execution",
            (
                "\n"
                f"## {agent_name} Native Multi-Agent Execution\n\n"
                f"When running `sp-plan` in {agent_name}, prefer native worker delegation whenever the selected strategy is `native-multi-agent`.\n"
                f"- Use `spawn_agent` (or native handoffs) for bounded lanes such as research, data model design, contracts drafting, and quickstart or validation scenario generation.\n"
                f"- Use `wait_agent` only at the documented join points before the final constitution and risk re-check and before writing the consolidated implementation plan.\n"
                f"- Use `close_agent` after integrating finished worker results.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-tasks" / "SKILL.md",
            f"## {agent_name} Native Multi-Agent Execution",
            (
                "\n"
                f"## {agent_name} Native Multi-Agent Execution\n\n"
                f"When running `sp-tasks` in {agent_name}, prefer native worker delegation whenever the selected strategy is `native-multi-agent`.\n"
                f"- Use `spawn_agent` (or native handoffs) for bounded lanes such as story and phase decomposition, dependency graph analysis, and write-set or parallel-safety analysis.\n"
                f"- Use `wait_agent` only at the documented join points before writing `tasks.md` and before emitting canonical parallel batches and join points.\n"
                f"- Use `close_agent` after integrating finished worker results.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-map-codebase" / "SKILL.md",
            f"## {agent_name} Native Multi-Agent Execution",
            (
                "\n"
                f"## {agent_name} Native Multi-Agent Execution\n\n"
                f"When running `sp-map-codebase` in {agent_name}, prefer native worker delegation whenever the selected strategy is `native-multi-agent`.\n"
                f"- Use `spawn_agent` (or native handoffs) for bounded lanes such as architecture/structure mapping, conventions/testing mapping, integrations/runtime mapping, and workflows/operations mapping.\n"
                f"- Use `wait_agent` only at the documented join points before writing `PROJECT-HANDBOOK.md` and before the final consistency pass.\n"
                f"- Use `close_agent` after integrating finished worker results.\n"
            ),
        )

        self._augment_implement_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-implement" / "SKILL.md",
            snapshot=codex_snapshot,
        )
        self._augment_debug_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-debug" / "SKILL.md",
            snapshot=codex_snapshot,
        )
        self._augment_quick_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-quick" / "SKILL.md",
            snapshot=codex_snapshot,
        )
        self._augment_implement_teams_shared_contract(
            created,
            project_root,
            manifest,
            skills_dir / "sp-implement-teams" / "SKILL.md",
            canonical_command="sp-implement",
            teams_command="sp-implement-teams",
            backend_label="the teams runtime",
        )
        self._augment_implement_teams_result_contract(
            created,
            project_root,
            manifest,
            skills_dir / "sp-implement-teams" / "SKILL.md",
            snapshot=codex_snapshot,
        )


__all__ = ["CodexIntegration", "CodexMultiAgentAdapter"]
