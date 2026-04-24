"""Claude Code integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..base import SkillsIntegration
from ..manifest import IntegrationManifest
from ...orchestration import CapabilitySnapshot, describe_delegation_surface
from .multi_agent import ClaudeMultiAgentAdapter

# Mapping of command template stem → argument-hint text shown inline
# when a user invokes the slash command in Claude Code.
ARGUMENT_HINTS: dict[str, str] = {
    "specify": "Describe the feature you want to specify",
    "spec-extend": "Describe what in the current spec package needs deeper analysis or correction",
    "explain": "Optionally name the stage or artifact you want explained",
    "debug": "Describe the bug to investigate, or leave blank to resume the most recent session",
    "fast": "Describe the trivial local fix, or leave blank to use the current fast-path context",
    "quick": "Describe the bounded quick task, or leave blank to resume the current quick-task workspace",
    "plan": "Optional guidance for the planning phase",
    "tasks": "Optional task generation constraints",
    "implement": "Optional implementation guidance or task filter",
    "analyze": "Optional focus areas for analysis, such as boundary guardrail drift (BG1/BG2/BG3)",
    "constitution": "Principles or values for the project constitution",
    "checklist": "Domain or focus area for the checklist",
    "map-codebase": "Optional subsystem or workflow area to emphasize while mapping",
    "taskstoissues": "Optional filter or label for GitHub issues",
}


class ClaudeIntegration(SkillsIntegration):
    """Integration for Claude Code skills."""

    key = "claude"
    config = {
        "name": "Claude Code",
        "folder": ".claude/",
        "commands_subdir": "skills",
        "install_url": "https://docs.anthropic.com/en/docs/claude-code/setup",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".claude/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    context_file = "CLAUDE.md"

    def _claude_capability_snapshot(self) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            integration_key=self.key,
            native_multi_agent=True,
            sidecar_runtime_supported=True,
            structured_results=True,
            durable_coordination=False,
            native_worker_surface="native-cli",
            delegation_confidence="medium",
            model_family="claude",
            runtime_probe_succeeded=True,
        )

    def _append_worker_result_contract(
        self,
        *,
        content: str,
        skill_name: str,
    ) -> str:
        marker = "## Claude Worker Result Contract"
        if marker in content:
            return content

        descriptor = describe_delegation_surface(
            command_name=skill_name,
            snapshot=self._claude_capability_snapshot(),
        )
        addendum = (
            "\n"
            "## Claude Worker Result Contract\n\n"
            f"- Preferred result contract: {descriptor.result_contract_hint}\n"
            f"- Result file handoff path: {descriptor.result_handoff_hint}\n"
            "- Normalize worker-reported statuses like `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, and `NEEDS_CONTEXT` into the shared `WorkerTaskResult` contract before the leader accepts the handoff.\n"
            "- Keep `reported_status` when normalization occurs so the leader can distinguish raw worker language from canonical orchestration state.\n"
            "- Wait for every delegated lane's structured handoff before accepting the join point, closing the batch, or declaring completion.\n"
            "- Do not treat an idle child as done work; idle without a consumed handoff means the result channel is still unresolved.\n"
            "- Do not interrupt or shut down delegated work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
            "- Treat `DONE_WITH_CONCERNS` as completed work plus follow-up concerns, not as silent success.\n"
            "- Treat `NEEDS_CONTEXT` as a blocked handoff that must carry the missing context or failed assumption explicitly.\n"
        )
        return content + addendum

    @staticmethod
    def inject_argument_hint(content: str, hint: str) -> str:
        """Insert ``argument-hint`` after the first ``description:`` in YAML frontmatter.

        Skips injection if ``argument-hint:`` already exists in the
        frontmatter to avoid duplicate keys.
        """
        lines = content.splitlines(keepends=True)

        # Pre-scan: bail out if argument-hint already present in frontmatter
        dash_count = 0
        for line in lines:
            stripped = line.rstrip("\n\r")
            if stripped == "---":
                dash_count += 1
                if dash_count == 2:
                    break
                continue
            if dash_count == 1 and stripped.startswith("argument-hint:"):
                return content  # already present

        out: list[str] = []
        in_fm = False
        dash_count = 0
        injected = False
        for line in lines:
            stripped = line.rstrip("\n\r")
            if stripped == "---":
                dash_count += 1
                in_fm = dash_count == 1
                out.append(line)
                continue
            if in_fm and not injected and stripped.startswith("description:"):
                out.append(line)
                # Preserve the exact line-ending style (\r\n vs \n)
                if line.endswith("\r\n"):
                    eol = "\r\n"
                elif line.endswith("\n"):
                    eol = "\n"
                else:
                    eol = ""
                escaped = hint.replace("\\", "\\\\").replace('"', '\\"')
                out.append(f'argument-hint: "{escaped}"{eol}')
                injected = True
                continue
            out.append(line)
        return "".join(out)

    def _render_skill(self, template_name: str, frontmatter: dict[str, Any], body: str) -> str:
        """Render a processed command template as a Claude skill."""
        skill_name = f"sp-{template_name.replace('.', '-')}"
        description = frontmatter.get(
            "description",
            f"Spec-kit workflow command: {template_name}",
        )
        skill_frontmatter = self._build_skill_fm(
            skill_name, description, f"templates/commands/{template_name}.md"
        )
        frontmatter_text = yaml.safe_dump(skill_frontmatter, sort_keys=False).strip()
        return f"---\n{frontmatter_text}\n---\n\n{body.strip()}\n"

    def _build_skill_fm(self, name: str, description: str, source: str) -> dict:
        from specify_cli.agents import CommandRegistrar
        return CommandRegistrar.build_skill_frontmatter(
            self.key, name, description, source
        )

    @staticmethod
    def _inject_frontmatter_flag(content: str, key: str, value: str = "true") -> str:
        """Insert ``key: value`` before the closing ``---`` if not already present."""
        lines = content.splitlines(keepends=True)

        # Pre-scan: bail out if already present in frontmatter
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

        # Inject before the closing --- of frontmatter
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
        """Install Claude skills, then inject user-invocable, disable-model-invocation, and augment with leader guidance."""
        # Run base setup which handles the core sp-skill creation and default augmentation
        created = super().setup(project_root, manifest, parsed_options, **opts)

        # Post-process generated skill files for Claude-specific flags
        skills_dir = self.skills_dest(project_root).resolve()

        for path in created:
            # Only touch SKILL.md files under the skills directory
            try:
                path.resolve().relative_to(skills_dir)
            except ValueError:
                continue
            if path.name != "SKILL.md":
                continue
            if not path.parent.name.startswith("sp-"):
                continue

            content_bytes = path.read_bytes()
            content = content_bytes.decode("utf-8")

            # Inject user-invocable: true (Claude skills are accessible via /command)
            updated = self._inject_frontmatter_flag(content, "user-invocable")

            # Inject disable-model-invocation: true (Claude skills run only when invoked)
            updated = self._inject_frontmatter_flag(updated, "disable-model-invocation")

            # Inject argument-hint if available for this skill
            skill_dir_name = path.parent.name  # e.g. "sp-plan"
            stem = skill_dir_name
            if stem.startswith("sp-"):
                stem = stem[len("sp-"):]
            hint = ARGUMENT_HINTS.get(stem, "")
            if hint:
                updated = self.inject_argument_hint(updated, hint)

            if updated != content:
                path.write_bytes(updated.encode("utf-8"))
                self.record_file_in_manifest(path, project_root, manifest)

        runtime_skills = {
            "implement": skills_dir / "sp-implement" / "SKILL.md",
            "debug": skills_dir / "sp-debug" / "SKILL.md",
            "quick": skills_dir / "sp-quick" / "SKILL.md",
        }
        snapshot = self._claude_capability_snapshot()
        for command_name, path in runtime_skills.items():
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            content = self._append_delegation_surface_contract(
                content=content,
                agent_name="Claude",
                command_name=command_name,
                snapshot=snapshot,
                heading="Delegation Surface Contract",
            )
            content = self._append_worker_result_contract(
                content=content,
                skill_name=command_name,
            )
            path.write_bytes(content.encode("utf-8"))
            self.record_file_in_manifest(path, project_root, manifest)

        return created


__all__ = ["ClaudeIntegration", "ClaudeMultiAgentAdapter"]
