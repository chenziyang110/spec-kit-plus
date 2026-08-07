"""Grok Build CLI integration — skills-based agent (xAI).

Grok uses the ``.grok/skills/sp-<name>/SKILL.md`` layout with slash-command
invocation (``/sp-<name>``) and root ``AGENTS.md`` as the project context file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import IntegrationOption, SkillsIntegration
from ..manifest import IntegrationManifest
from ...orchestration import (
    NATIVE_SUBAGENT_TERMINAL_GUIDANCE,
    CapabilitySnapshot,
)
from .multi_agent import GrokMultiAgentAdapter


class GrokIntegration(SkillsIntegration):
    """Integration for Grok Build CLI (xAI)."""

    key = "grok"
    config = {
        "name": "Grok",
        "folder": ".grok/",
        "commands_subdir": "skills",
        "install_url": "https://x.ai/cli",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".grok/skills",
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
                help="Install as agent skills (default for Grok)",
            ),
        ]

    def _runtime_capability_snapshot(self) -> CapabilitySnapshot:
        return GrokMultiAgentAdapter().detect_capabilities()

    @staticmethod
    def _inject_frontmatter_flag(content: str, key: str, value: str = "true") -> str:
        """Insert ``key: value`` before the closing frontmatter marker."""
        lines = content.splitlines(keepends=True)

        dash_count = 0
        for line in lines:
            stripped = line.rstrip("\n\r")
            if stripped == "---":
                dash_count += 1
                if dash_count == 2:
                    break
                continue
            if dash_count == 1 and stripped.startswith(f"{key}:"):
                return content

        out: list[str] = []
        dash_count = 0
        injected = False
        for line in lines:
            stripped = line.rstrip("\n\r")
            if stripped == "---":
                dash_count += 1
                if dash_count == 2 and not injected:
                    if line.endswith("\r\n"):
                        eol = "\r\n"
                    elif line.endswith("\n"):
                        eol = "\n"
                    else:
                        eol = ""
                    out.append(f"{key}: {value}{eol}")
                    injected = True
            out.append(line)
        return "".join(out)

    def setup(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        created = super().setup(
            project_root,
            manifest,
            parsed_options=parsed_options,
            **opts,
        )

        # Grok exposes skills as slash commands when user-invocable is true.
        skills_dir = self.skills_dest(project_root).resolve()
        for path in created:
            try:
                path.resolve().relative_to(skills_dir)
            except ValueError:
                continue
            if path.name != "SKILL.md" or not (
                path.parent.name.startswith("sp-")
                or path.parent.name.startswith("spx-")
            ):
                continue

            content = path.read_text(encoding="utf-8")
            updated = self._inject_frontmatter_flag(content, "user-invocable")
            if updated != content:
                path.write_text(updated, encoding="utf-8")
                self.record_file_in_manifest(path, project_root, manifest)

        return created

    def augment_generated_skills(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        skills_dir: Path,
    ) -> None:
        """Apply Codex-standard dispatch policy with Grok-native tool names."""
        snapshot = self._runtime_capability_snapshot()
        agent_name = "Grok"
        dispatch_tool, join_tool = self.native_dispatch_join_tools(snapshot)
        tool_surface = self._grok_tool_surface_lines(
            dispatch_tool=dispatch_tool,
            join_tool=join_tool,
        )

        # Mirror Codex command coverage and policy strength; only tool names differ.
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-specify" / "SKILL.md",
            f"## {agent_name} Subagents-First Dispatch",
            (
                "\n"
                f"## {agent_name} Subagents-First Dispatch\n\n"
                f"When running `sp-specify` in {agent_name}, use Grok native "
                "subagents for bounded evidence, challenge, and artifact-review "
                "lanes that support the current collaborative specification pass.\n"
                "- Do not let subagents invent scope, semantic-term choices, or "
                "upstream signal dispositions outside the leader-owned artifacts.\n"
                f"- Use `{dispatch_tool}` for bounded source-file sweep, repository "
                "evidence, semantic-drift challenge, and artifact validation lanes.\n"
                "- Use join points before section approval, before artifact "
                "self-review, and before the user review gate when delegated lanes "
                "are active.\n"
                "- Launch all independent lanes in the current "
                "`parallel-subagents` wave before waiting.\n"
                "- Suggested bounded lanes include discussion source sweep, "
                "targeted repository evidence, semantic-term challenge, upstream "
                "disposition review, and written artifact validation.\n"
                "- Keep structured artifact discipline: Grok subagents may return "
                "evidence and challenges, but the leader mutates `spec.md`, "
                "`alignment.md`, `context.md`, and `workflow-state.md` only through "
                "leased `specify-runtime artifact patch` calls, and binds the "
                "compatibility `brainstorming/handoff-to-specify.json` pointer only "
                "through `specify-runtime discussion bind-consumer`.\n"
                f"- Use `{join_tool}` only at explicit review join points and before "
                "final user review.\n"
                f"{tool_surface}"
                f"- {NATIVE_SUBAGENT_TERMINAL_GUIDANCE}\n"
                "- Keep the shared workflow language integration-neutral in "
                "user-visible output.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-plan" / "SKILL.md",
            f"## {agent_name} Adaptive Dispatch",
            (
                "\n"
                f"## {agent_name} Adaptive Dispatch\n\n"
                f"When running `sp-plan` in {agent_name}, apply the adaptive "
                "dispatch decision recorded by `choose_subagent_dispatch`.\n"
                "- Light mode records `dispatch_shape: leader-inline` and "
                "`execution_surface: leader-inline`; do not spawn planning lanes "
                "for light work.\n"
                f"- Standard mode uses `{dispatch_tool}` for bounded lanes when "
                "`dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Standard native-unavailable degradation records "
                "`execution_surface: leader-inline` and "
                "`capability_degraded: true` only when no high-risk trigger is "
                "present.\n"
                "- Heavy or safety-critical blocked work records "
                "`dispatch_shape: subagent-blocked` and `execution_surface: none` "
                "with `blocked_reason`.\n"
                "- Launch all independent lanes in the current "
                "`parallel-subagents` wave before waiting.\n"
                "- Suggested bounded lanes include research, data model design, "
                "contracts drafting, and quickstart or validation scenario "
                "generation.\n"
                f"- Use `{join_tool}` only at the documented join points before "
                "the final constitution and risk re-check and before writing the "
                "consolidated implementation plan.\n"
                f"{tool_surface}"
                f"- {NATIVE_SUBAGENT_TERMINAL_GUIDANCE}\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-tasks" / "SKILL.md",
            f"## {agent_name} Adaptive Dispatch",
            (
                "\n"
                f"## {agent_name} Adaptive Dispatch\n\n"
                f"When running `sp-tasks` in {agent_name}, apply the adaptive "
                "dispatch decision recorded by `choose_subagent_dispatch`.\n"
                "- Light mode records `dispatch_shape: leader-inline` and "
                "`execution_surface: leader-inline`; do not spawn task-generation "
                "lanes for light work.\n"
                f"- Standard mode uses `{dispatch_tool}` for bounded lanes when "
                "`dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Standard native-unavailable degradation records "
                "`execution_surface: leader-inline` and "
                "`capability_degraded: true` only when no high-risk trigger is "
                "present.\n"
                "- Heavy or safety-critical blocked work records "
                "`dispatch_shape: subagent-blocked` and `execution_surface: none` "
                "with `blocked_reason`.\n"
                "- Launch all independent lanes in the current "
                "`parallel-subagents` wave before waiting.\n"
                "- Suggested bounded lanes include story and phase decomposition, "
                "dependency graph analysis, and write-set or parallel-safety "
                "analysis.\n"
                f"- Use `{join_tool}` only at the documented join points before "
                "calling `specify-runtime tasks finalize` and "
                "`specify-runtime tasks handoff`; `specify-runtime tasks finalize` "
                "renders `tasks.md`, and `specify-runtime tasks handoff` emits "
                "canonical parallel batches and join points.\n"
                f"{tool_surface}"
                f"- {NATIVE_SUBAGENT_TERMINAL_GUIDANCE}\n"
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
                f"When running `sp-map-scan` in {agent_name}, use the "
                "subagents-first dispatch model.\n"
                f"- Use `{dispatch_tool}` for bounded lanes when "
                "`dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current "
                "`parallel-subagents` wave before waiting.\n"
                "- Use `leader-inline-fallback` only after recording why Grok "
                "native subagents are unavailable or unsafe.\n"
                "- Suggested bounded scan lanes include repository tree inventory, "
                "source/runtime surfaces, testing/operations surfaces, and "
                "generated/cache exclusion review.\n"
                "- Keep each subagent responsible for scan evidence only; the "
                "leader owns the coverage ledger, reverse coverage closure, and "
                "final completeness decision.\n"
                f"- Use `{join_tool}` only at the documented join points before "
                "finalizing `coverage-ledger.md`, `coverage-ledger.json`, "
                "`scan-packets/<lane-id>.md`, and `map-state.md`.\n"
                f"{tool_surface}"
                f"- {NATIVE_SUBAGENT_TERMINAL_GUIDANCE}\n"
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
                f"When running `sp-map-build` in {agent_name}, use the "
                "subagents-first dispatch model.\n"
                f"- Use `{dispatch_tool}` for bounded lanes when "
                "`dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current "
                "`parallel-subagents` wave before waiting.\n"
                "- Use `leader-inline-fallback` only after recording why Grok "
                "native subagents are unavailable or unsafe.\n"
                "- Suggested bounded atlas synthesis lanes include root "
                "architecture/structure, conventions/testing, "
                "integrations/runtime, and workflow/operations mapping.\n"
                "- Use the scan package as the subagent input contract; do not "
                "let subagents invent unscanned coverage or skip reverse coverage "
                "checks.\n"
                f"- Use `{join_tool}` only at the documented join points before "
                "writing compatibility/export outputs such as "
                "`PROJECT-HANDBOOK.md`, before updating project cognition "
                "workbench outputs, and before the final packet evidence and "
                "consistency pass.\n"
                f"{tool_surface}"
                f"- {NATIVE_SUBAGENT_TERMINAL_GUIDANCE}\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-map-update" / "SKILL.md",
            f"## {agent_name} Subagents-First Dispatch",
            (
                "\n"
                f"## {agent_name} Subagents-First Dispatch\n\n"
                f"When running `sp-map-update` in {agent_name}, use the "
                "subagents-first dispatch model.\n"
                "- Prefer the smallest executable update lane set.\n"
                "- User-supplied scope remains authoritative unless repository "
                "evidence disproves it.\n"
                f"- Use `{dispatch_tool}` for bounded lanes when "
                "`dispatch_shape` is `one-subagent` or `parallel-subagents`.\n"
                "- Launch all independent lanes in the current "
                "`parallel-subagents` wave before waiting, but only after "
                "confirming the refresh is not metadata-only or single-slice.\n"
                "- Use `leader-inline-fallback` only after recording why Grok "
                "native subagents are unavailable or unsafe.\n"
                "- Leader-inline-fallback for a one-lane update is preferred over "
                "forcing extra subagents.\n"
                "- Suggested bounded update lanes include diff impact closure, "
                "affected graph and alias refresh, user supplement normalization, "
                "and route-pack reconciliation.\n"
                "- Do not turn a one-slice or metadata-only refresh into "
                "scan-style parallel exploration.\n"
                f"- Use `{join_tool}` only at the documented join points before "
                "updating graph, path-index, alias-index, and route-pack "
                "outputs.\n"
                f"{tool_surface}"
                f"- {NATIVE_SUBAGENT_TERMINAL_GUIDANCE}\n"
            ),
        )
        self._augment_implement_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-implement" / "SKILL.md",
            snapshot=snapshot,
        )
        self._augment_debug_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-debug" / "SKILL.md",
            snapshot=snapshot,
        )
        self._augment_quick_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-quick" / "SKILL.md",
            snapshot=snapshot,
        )

        for command_name in ("implement", "debug", "quick", "plan", "tasks", "review"):
            skill_path = skills_dir / f"sp-{command_name}" / "SKILL.md"
            if not skill_path.is_file():
                continue
            content = skill_path.read_text(encoding="utf-8")
            content = self._append_runtime_worker_result_contract(
                content=content,
                agent_name=agent_name,
                command_name=command_name,
                snapshot=snapshot,
            )
            content = self._append_delegation_surface_contract(
                content=content,
                agent_name=agent_name,
                command_name=command_name,
                snapshot=snapshot,
                heading="Subagent Dispatch Contract",
            )
            if content != skill_path.read_text(encoding="utf-8"):
                self._write_augmented_skill(
                    content, skill_path, project_root, manifest
                )

    @staticmethod
    def _grok_tool_surface_lines(*, dispatch_tool: str, join_tool: str) -> str:
        """Compact Grok-native tool footnote; policy stays Codex-standard."""

        return (
            f"- Tool surface (Grok Build install): dispatch with `{dispatch_tool}` "
            f"(required `prompt` + short `description`); join with `{join_tool}` "
            "(`task_ids`, optional `timeout_ms`); cancel unfinished work only with "
            "`kill_command_or_subagent`. Prefer `explore`+`capability_mode=read-only` "
            "for evidence, `plan`+`read-only` for planning analysis, and "
            "`general-purpose` with the narrowest safe mode for implement/test/"
            "validation. Default isolation `none`; use `worktree` only when "
            "independent source edits must not collide. Do not use the Rhai "
            "`workflow` tool or invent `sp-teams` as a managed-team fallback.\n"
        )


__all__ = ["GrokIntegration", "GrokMultiAgentAdapter"]
