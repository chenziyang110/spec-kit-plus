"""Codex CLI integration — skills-based agent.

Codex uses the ``.codex/skills/sp-<name>/SKILL.md`` layout.
Commands are deprecated; ``--skills`` defaults to ``True``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import IntegrationOption, SkillsIntegration
from ...orchestration import CapabilitySnapshot
from ...codex_team.installer import restore_codex_team_project_configs
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
    question_tool_config = {
        "tool_name": "request_user_input",
        "availability_note": "if the current Codex runtime exposes it",
        "question_limit": "1-3 short questions per call",
        "option_limit": "2-3 options per question",
        "question_fields": ["header", "id", "question", "options"],
        "option_fields": ["label", "description"],
        "extra_notes": [
            "Put the recommended option first and suffix its label with `(Recommended)` when that distinction matters.",
            "Use this native surface for one bounded clarification or selection step; if it is unavailable or too narrow for the needed interaction, fall back immediately to the template's textual question format.",
        ],
    }

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

    def teardown(
        self,
        project_root: Path,
        manifest,
        *,
        force: bool = False,
    ) -> tuple[list[Path], list[Path]]:
        restore_codex_team_project_configs(project_root)
        return super().teardown(project_root, manifest, force=force)

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
            native_subagents=True,
            managed_team_supported=True,
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
            f"## {agent_name} Subagents-First Dispatch",
            (
                "\n"
                f"## {agent_name} Subagents-First Dispatch\n\n"
                f"When running `sp-specify` in {agent_name}, use the subagents-first dispatch model.\n"
                "- Use `spawn_agent` for bounded lanes when `dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current `parallel-subagents` wave before waiting.\n"
                "- Use `leader-inline-fallback` only after recording why Codex native subagents are unavailable or unsafe.\n"
                "- Suggested bounded lanes include repository and local context analysis, references analysis, and ambiguity/risk analysis.\n"
                f"- Use `wait_agent` only at the documented join points before capability decomposition and before writing `spec.md`, `alignment.md`, and `context.md`.\n"
                f"- Use `close_agent` after integrating finished subagent results.\n"
                "- Keep the shared workflow language integration-neutral in user-visible output.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-plan" / "SKILL.md",
            f"## {agent_name} Subagents-First Dispatch",
            (
                "\n"
                f"## {agent_name} Subagents-First Dispatch\n\n"
                f"When running `sp-plan` in {agent_name}, use the subagents-first dispatch model.\n"
                "- Use `spawn_agent` for bounded lanes when `dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current `parallel-subagents` wave before waiting.\n"
                "- Use `leader-inline-fallback` only after recording why Codex native subagents are unavailable or unsafe.\n"
                "- Suggested bounded lanes include research, data model design, contracts drafting, and quickstart or validation scenario generation.\n"
                f"- Use `wait_agent` only at the documented join points before the final constitution and risk re-check and before writing the consolidated implementation plan.\n"
                f"- Use `close_agent` after integrating finished subagent results.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-tasks" / "SKILL.md",
            f"## {agent_name} Subagents-First Dispatch",
            (
                "\n"
                f"## {agent_name} Subagents-First Dispatch\n\n"
                f"When running `sp-tasks` in {agent_name}, use the subagents-first dispatch model.\n"
                "- Use `spawn_agent` for bounded lanes when `dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current `parallel-subagents` wave before waiting.\n"
                "- Use `leader-inline-fallback` only after recording why Codex native subagents are unavailable or unsafe.\n"
                "- Suggested bounded lanes include story and phase decomposition, dependency graph analysis, and write-set or parallel-safety analysis.\n"
                f"- Use `wait_agent` only at the documented join points before writing `tasks.md` and before emitting canonical parallel batches and join points.\n"
                f"- Use `close_agent` after integrating finished subagent results.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-map-scan" / "SKILL.md",
            f"## {agent_name} Subagents-First Dispatch",
            (
                "\n"
                f"## {agent_name} Subagents-First Dispatch\n\n"
                f"When running `sp-map-scan` in {agent_name}, use the subagents-first dispatch model.\n"
                "- Use `spawn_agent` for bounded lanes when `dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current `parallel-subagents` wave before waiting.\n"
                "- Use `leader-inline-fallback` only after recording why Codex native subagents are unavailable or unsafe.\n"
                "- Suggested bounded scan lanes include repository tree inventory, source/runtime surfaces, testing/operations surfaces, and generated/cache exclusion review.\n"
                f"- Keep each subagent responsible for scan evidence only; the leader owns the coverage ledger, reverse coverage closure, and final completeness decision.\n"
                f"- Use `wait_agent` only at the documented join points before finalizing `coverage-ledger.md`, `coverage-ledger.json`, `scan-packets/<lane-id>.md`, and `map-state.md`.\n"
                f"- Use `close_agent` after integrating finished subagent results.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-map-build" / "SKILL.md",
            f"## {agent_name} Subagents-First Dispatch",
            (
                "\n"
                f"## {agent_name} Subagents-First Dispatch\n\n"
                f"When running `sp-map-build` in {agent_name}, use the subagents-first dispatch model.\n"
                "- Use `spawn_agent` for bounded lanes when `dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current `parallel-subagents` wave before waiting.\n"
                "- Use `leader-inline-fallback` only after recording why Codex native subagents are unavailable or unsafe.\n"
                "- Suggested bounded atlas synthesis lanes include root architecture/structure, conventions/testing, integrations/runtime, and workflow/operations mapping.\n"
                f"- Use the scan package as the subagent input contract; do not let subagents invent unscanned coverage or skip reverse coverage checks.\n"
                f"- Use `wait_agent` only at the documented join points before writing `PROJECT-HANDBOOK.md`, before updating `.specify/project-map/`, and before the final packet evidence and consistency pass.\n"
                f"- Use `close_agent` after integrating finished subagent results.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-test-scan" / "SKILL.md",
            f"## {agent_name} Subagents-First Dispatch",
            (
                "\n"
                f"## {agent_name} Subagents-First Dispatch\n\n"
                f"When running `sp-test-scan` in {agent_name}, use the subagents-first dispatch model for read-only scout work.\n"
                "- Use `spawn_agent` for bounded lanes when `dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current `parallel-subagents` wave before waiting.\n"
                "- Use `leader-inline-fallback` only after recording why Codex native subagents are unavailable or unsafe.\n"
                "- Suggested bounded lanes include module, framework, coverage-command, and risk-review scan lanes.\n"
                "- Each scan subagent is read-only and must return inspected files, public entrypoints, existing tests, missing scenarios, recommended build lanes, validation commands, and blockers.\n"
                f"- Use `wait_agent` only at the documented scan join points before final risk ranking, before writing `TEST_BUILD_PLAN.md` / `TEST_BUILD_PLAN.json`, and before marking scan complete.\n"
                f"- Use `close_agent` after integrating finished scout results.\n"
                "- Do not let scan subagents edit repository files or `.specify/testing/*` artifacts directly.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-test-build" / "SKILL.md",
            f"## {agent_name} Subagents-First Dispatch",
            (
                "\n"
                f"## {agent_name} Subagents-First Dispatch\n\n"
                f"When running `sp-test-build` in {agent_name}, use the subagents-first dispatch model.\n"
                "- Use `spawn_agent` for bounded lanes when `dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current `parallel-subagents` wave before waiting.\n"
                "- Use `leader-inline-fallback` only after recording why Codex native subagents are unavailable or unsafe.\n"
                "- Dispatch validated `TestBuildPacket` lanes with isolated write sets.\n"
                "- Keep shared config, global fixture, CI, dependency, and production-code testability lanes on the leader path unless the packet explicitly authorizes a serial lane.\n"
                f"- Use `wait_agent` only at the documented build join points after each parallel wave and before consolidated testing artifacts are updated.\n"
                f"- Use `close_agent` after integrating finished build or review results.\n"
                "- Wait for every subagent's structured handoff before accepting a lane, starting the next wave, or marking build complete.\n"
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
