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
    "implement-teams": "Optional implementation scope or coordination guidance for the Agent Teams run",
    "analyze": "Optional focus areas for analysis, such as boundary guardrail drift (BG1/BG2/BG3)",
    "constitution": "Principles or values for the project constitution",
    "checklist": "Domain or focus area for the checklist",
    "test": "Optional testing-system scope, module focus, or audit-only guidance",
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
    question_tool_config = {
        "tool_name": "AskUserQuestion",
        "question_limit": "1-4 questions per call",
        "option_limit": "2-4 options per question",
        "question_fields": ["question", "header", "options", "multiSelect"],
        "option_fields": ["label", "description", "preview (optional)"],
        "extra_notes": [
            "Use `multiSelect: false` unless the workflow explicitly needs multiple selections.",
            "Use `metadata` only when tracking or analytics context adds value; otherwise keep the call minimal.",
        ],
    }

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

    def _replace_frontmatter_description(
        self,
        *,
        content: str,
        description: str,
    ) -> str:
        """Replace the frontmatter description while preserving file structure."""
        lines = content.splitlines(keepends=True)
        out: list[str] = []
        dash_count = 0
        replaced = False

        for line in lines:
            stripped = line.rstrip("\n\r")
            if stripped == "---":
                dash_count += 1
                out.append(line)
                continue
            if dash_count == 1 and not replaced and stripped.startswith("description:"):
                if line.endswith("\r\n"):
                    eol = "\r\n"
                elif line.endswith("\n"):
                    eol = "\n"
                else:
                    eol = ""
                escaped = description.replace("\\", "\\\\").replace('"', '\\"')
                out.append(f'description: "{escaped}"{eol}')
                replaced = True
                continue
            out.append(line)
        return "".join(out)

    def _append_dispatch_first_gate(
        self,
        *,
        content: str,
    ) -> str:
        marker = "## Claude Dispatch-First Gate"
        if marker in content:
            return content

        addendum = (
            "\n"
            "## Claude Dispatch-First Gate\n\n"
            "- For `sp-implement`, attempt delegated execution before leader-local implementation.\n"
            "- Use Claude's native delegated child-worker path as the default first attempt for the current ready batch whenever the batch is safe to delegate.\n"
            "- Treat `single-lane` as one delegated child-worker lane, not as permission for the leader to implement directly.\n"
            "- Treat legacy `single-agent` state as a compatibility alias for the same delegated single-lane path.\n"
            "- If multiple safe worker lanes exist for the current batch, dispatch them in parallel instead of defaulting to serial leader-local work.\n"
            "- Prefer delegated child-worker fan-out over local deep-dive execution when the ready tasks have isolated write sets and stable upstream inputs.\n"
            "- Do not begin concrete implementation on the leader path while an untried delegated path is available for the current batch.\n"
            "- Only fall back to leader-local execution after recording a concrete fallback reason in `FEATURE_DIR/implement-tracker.md`.\n"
            "- If the current batch needs durable shared coordination or explicit teammate messaging, escalate to `/sp-implement-teams` instead of simulating that coordination on the leader path.\n"
        )
        if "## Leader Role" in content:
            return content.replace("## Leader Role", addendum + "\n## Leader Role", 1)
        return content + addendum

    def _append_agent_teams_escalation(
        self,
        *,
        content: str,
    ) -> str:
        marker = "## Claude Agent Teams Escalation"
        if marker in content:
            return content

        addendum = (
            "\n"
            "## Claude Agent Teams Escalation\n\n"
            "- If durable coordinated execution is required, switch to `/sp-implement-teams` instead of inventing an ad hoc leader-local loop.\n"
            "- Treat `/sp-implement-teams` as a backend swap for `/sp-implement`, not as a separate implementation contract.\n"
            "- Treat `/sp-implement-teams` as the Claude-native surface for shared team state, task dependencies, teammate messaging, and shutdown.\n"
            "- Do not redirect Claude users to Codex runtime surfaces or Codex extension commands.\n"
        )
        return content + addendum

    def _install_claude_specific_skills(
        self,
        *,
        project_root: Path,
        manifest: IntegrationManifest,
        skills_dir: Path,
        script_type: str,
        arg_placeholder: str,
    ) -> list[Path]:
        template = Path(__file__).resolve().parent / "templates" / "implement-teams.md"
        if not template.is_file():
            return []

        raw = template.read_text(encoding="utf-8")
        frontmatter = self._parse_skill_frontmatter(raw)
        description = frontmatter.get(
            "description",
            "Execute implementation through Claude Code Agent Teams when you explicitly want durable multi-worker execution.",
        )
        skill_content = self._render_skill_content(
            raw=raw,
            skill_name="sp-implement-teams",
            description=description,
            source="src/specify_cli/integrations/claude/templates/implement-teams.md",
            script_type=script_type,
            arg_placeholder=arg_placeholder,
        )
        skill_path = skills_dir / "sp-implement-teams" / "SKILL.md"
        return [
            self.write_file_and_record(
                skill_content,
                skill_path,
                project_root,
                manifest,
            )
        ]

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
        script_type = opts.get("script_type", "sh")
        arg_placeholder = (
            self.registrar_config.get("args", "$ARGUMENTS")
            if self.registrar_config
            else "$ARGUMENTS"
        )
        created.extend(
            self._install_claude_specific_skills(
                project_root=project_root,
                manifest=manifest,
                skills_dir=skills_dir,
                script_type=script_type,
                arg_placeholder=arg_placeholder,
            )
        )

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
            if command_name == "implement":
                content = self._replace_frontmatter_description(
                    content=content,
                    description="Execute the implementation plan by dispatching tasks to worker agents and integrating their results",
                )
                content = self._append_dispatch_first_gate(content=content)
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
            if command_name == "implement":
                content = self._append_agent_teams_escalation(content=content)
            path.write_bytes(content.encode("utf-8"))
            self.record_file_in_manifest(path, project_root, manifest)

        implement_teams_skill = skills_dir / "sp-implement-teams" / "SKILL.md"
        if implement_teams_skill.exists():
            self._augment_implement_teams_shared_contract(
                created,
                project_root,
                manifest,
                implement_teams_skill,
                canonical_command="/sp-implement",
                teams_command="/sp-implement-teams",
                backend_label="Claude Code Agent Teams",
            )
            content = implement_teams_skill.read_text(encoding="utf-8")
            content = self._append_worker_result_contract(
                content=content,
                skill_name="implement",
            )
            implement_teams_skill.write_bytes(content.encode("utf-8"))
            self.record_file_in_manifest(implement_teams_skill, project_root, manifest)

        return created


__all__ = ["ClaudeIntegration", "ClaudeMultiAgentAdapter"]
