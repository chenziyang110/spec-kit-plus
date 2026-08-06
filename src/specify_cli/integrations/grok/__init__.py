"""Grok Build CLI integration — skills-based agent (xAI).

Grok uses the ``.grok/skills/sp-<name>/SKILL.md`` layout with slash-command
invocation (``/sp-<name>``) and root ``AGENTS.md`` as the project context file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import IntegrationOption, SkillsIntegration
from ..manifest import IntegrationManifest
from ...orchestration import CapabilitySnapshot, describe_delegation_surface
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
        """Apply Grok-native spawn_subagent routing to generated skills."""
        snapshot = self._runtime_capability_snapshot()
        agent_name = "Grok"

        for command_name, heading, body in self._grok_dispatch_sections(
            agent_name=agent_name,
            snapshot=snapshot,
        ):
            self._augment_shared_skill(
                created,
                project_root,
                manifest,
                skills_dir / f"sp-{command_name}" / "SKILL.md",
                heading,
                body,
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
    def _grok_dispatch_sections(
        *,
        agent_name: str,
        snapshot: CapabilitySnapshot,
    ) -> list[tuple[str, str, str]]:
        """Return Grok-specific adaptive dispatch sections keyed by command."""

        sections: list[tuple[str, str, str]] = []
        for command_name, title, lane_hint in (
            (
                "specify",
                "Subagents-First Dispatch",
                "bounded evidence, challenge, and artifact-review lanes",
            ),
            (
                "plan",
                "Adaptive Dispatch",
                "research, data-model, contracts, and validation-scenario lanes",
            ),
            (
                "tasks",
                "Adaptive Dispatch",
                "task-graph partitioning, dependency analysis, and packet drafting lanes",
            ),
            (
                "implement",
                "Adaptive Dispatch",
                "bounded implementation, test, and validation lanes",
            ),
            (
                "review",
                "Adaptive Dispatch",
                "read-only review, bounded fix, and revalidation lanes",
            ),
            (
                "debug",
                "Investigation Dispatch",
                "read-only evidence and targeted repro lanes",
            ),
            (
                "quick",
                "Adaptive Dispatch",
                "bounded Q-item implementation and validation lanes",
            ),
            (
                "map-scan",
                "Map Packet Dispatch",
                "bounded scan-packet workers",
            ),
            (
                "clarify",
                "Evidence Dispatch",
                "bounded clarification evidence lanes",
            ),
            (
                "deep-research",
                "Evidence Dispatch",
                "bounded research and feasibility evidence lanes",
            ),
        ):
            descriptor = describe_delegation_surface(
                command_name=command_name,
                snapshot=snapshot,
            )
            heading = f"## {agent_name} {title}"
            body = (
                "\n"
                f"{heading}\n\n"
                f"When running `sp-{command_name}` in {agent_name}, use Grok native "
                f"subagents for {lane_hint} only when the adaptive decision selects "
                "`one-subagent` or `parallel-subagents`.\n"
                f"- Capability discovery: {descriptor.native_discovery_hint}\n"
                f"- Dispatch: {descriptor.native_dispatch_hint}\n"
                f"- Join: {descriptor.native_join_hint}\n"
                "- Light mode stays `leader-inline`.\n"
                "- Standard mode dispatches when native surface is available; if "
                "unavailable and no high-risk trigger is present, record "
                "`capability_degraded: true` with `execution_surface: leader-inline`.\n"
                "- Heavy or safety-critical work that needs native lanes must "
                "record `subagent-blocked` with `execution_surface: none` rather "
                "than silently remaining inline.\n"
                "- Workers return structured evidence or inline result payloads. "
                "The Leader alone runs stage-owned `specify-runtime result submit` "
                "(or implement `result-merge`) and mutates workflow artifacts "
                "through leased `specify-runtime artifact` / `tasks` commands.\n"
                f"- Result contract: {descriptor.result_contract_hint}\n"
                f"- Result submit: {descriptor.result_submit_hint}\n"
            )
            sections.append((command_name, heading, body))
        return sections


__all__ = ["GrokIntegration", "GrokMultiAgentAdapter"]
