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
                    "When running `sp-implement` in Codex, treat Step 6's unified execution strategy selection as a runtime-aware escalation with a Codex-specific runtime preference.\n"
                    "For each ready parallel batch:\n"
                    "- The invoking runtime acts as the leader: it reads the current planning artifacts, selects the next executable phase and ready batch, and dispatches work instead of performing concrete implementation directly.\n"
                    "- The shared implement template is the primary source of truth for this leader-only milestone scheduler contract, and Codex-specific guidance must preserve the same semantics.\n"
                    "- Keep the shared strategy names and workload-safety checks, but for Codex `sp-implement` prefer `sidecar-runtime` whenever `snapshot.sidecar_runtime_supported` is true for the current ready batch.\n"
                    "- single-agent still means one delegated worker lane, not leader self-execution.\n"
                    "- Interpret `single-agent` as solo execution through that delegated single-worker sequential path.\n"
                    "- Interpret `native-multi-agent` as the native subagents path.\n"
                    "- Interpret `sidecar-runtime` as escalation via **`specify team`**.\n"
                    "- Decision order for Codex `sp-implement` must stay fixed: `no-safe-batch` -> `sidecar-preferred` -> `native-confirmed` -> `fallback`.\n"
                    "- When `sidecar-runtime` is available, call **`specify team auto-dispatch --feature-dir \"<FEATURE_DIR>\"`** before considering any native subagent path.\n"
                    "- Follow a fixed order: capture the Step 1 `FEATURE_DIR`, inspect the next ready explicit parallel batch, run the auto-dispatch command, read the result, and only then continue.\n"
                    "- If `specify team auto-dispatch` reports a concrete blocker or runtime unavailability, stop and ask the user whether Codex should continue via native subagents.\n"
                    "- Only switch to `native-multi-agent` after explicit user approval. If the user declines, stay on the delegated single-worker lane or halt when no safe delegated path remains.\n"
                    "- Re-check the strategy after every join point instead of assuming the first choice still applies.\n"
                    "- The leader delegates execution through these worker paths rather than executing the implementation itself.\n"
                    "- Surface join points, retry-pending work, and blocker state truthfully instead of leaving those runtime transitions implicit.\n"
                    "- After each completed batch, the leader re-evaluates milestone state, selects the next executable phase and ready batch in roadmap order, and continues automatically until the milestone is complete or blocked.\n"
                )
                self.write_file_and_record(
                    content + addendum,
                    implement_skill,
                    project_root,
                    manifest,
                )

        return created


__all__ = ["CodexIntegration", "CodexMultiAgentAdapter"]
