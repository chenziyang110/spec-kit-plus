"""Claude Code integration."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import json5
import yaml

from ..base import SkillsIntegration
from ..manifest import IntegrationManifest
from ...launcher import install_shared_hook_launcher_assets, render_hook_launcher_command
from ...orchestration import CapabilitySnapshot, describe_delegation_surface
from .multi_agent import ClaudeMultiAgentAdapter

# Mapping of command template stem → argument-hint text shown inline
# when a user invokes the slash command in Claude Code.
ARGUMENT_HINTS: dict[str, str] = {
    "specify": "Describe the feature you want to specify",
    "clarify": "Describe what in the current spec package needs deeper analysis or correction",
    "deep-research": "Describe the feasibility question, research tracks, or demo proof needed before planning handoff",
    "research": "Describe the feasibility question; routes to sp-deep-research without separate artifacts",
    "explain": "Optionally name the stage or artifact you want explained",
    "debug": "Describe the bug to investigate, or leave blank to resume the most recent session",
    "fast": "Describe the trivial local fix, or leave blank to use the current fast-path context",
    "quick": "Describe the bounded quick task, or leave blank to resume the current quick-task workspace",
    "auto": "Optional continue request or routing hint; leave blank to let repository state choose the next workflow",
    "plan": "Optional guidance for the planning phase",
    "tasks": "Optional task generation constraints",
    "prd": "Describe the existing project or PRD extraction target to reverse-document",
    "implement": "Optional implementation guidance or task filter",
    "integrate": "Optional feature lane or closeout focus for integration readiness",
    "implement-teams": "Optional implementation scope or coordination guidance for the Agent Teams run",
    "analyze": "Optional focus areas for analysis, such as boundary guardrail drift (BG1/BG2/BG3)",
    "constitution": "Principles or values for the project constitution",
    "checklist": "Domain or focus area for the checklist",
    "test": "Optional testing-system routing hint; leave blank to choose scan or build from repository state",
    "test-scan": "Optional module, package, or risk area to emphasize during the read-only testing-system scan",
    "test-build": "Optional wave, lane, or module filter for building from the existing test scan",
    "map-scan": "Optional subsystem, directory, or workflow area to emphasize while scanning",
    "map-build": "Optional scan package or atlas area to emphasize while building the project map",
    "taskstoissues": "Optional filter or label for GitHub issues",
}

CLAUDE_HOOK_DISPATCH = "claude-hook-dispatch.py"


class ClaudeIntegration(SkillsIntegration):
    """Integration for Claude Code skills."""

    key = "claude"

    @staticmethod
    def _hook_dispatch_command(route: str, *, script_type: str = "sh") -> str:
        return render_hook_launcher_command(
            "claude",
            route,
            project_dir_env_var="CLAUDE_PROJECT_DIR",
            script_type=script_type,
        )

    @classmethod
    def _build_managed_hook_events(cls, *, script_type: str = "sh") -> dict[str, list[dict[str, Any]]]:
        return {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": cls._hook_dispatch_command("session-start", script_type=script_type),
                        }
                    ]
                }
            ],
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": cls._hook_dispatch_command("user-prompt-submit", script_type=script_type),
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Bash|Edit|Write|MultiEdit|Task",
                    "hooks": [
                        {
                            "type": "command",
                            "command": cls._hook_dispatch_command("post-tool-session-state", script_type=script_type),
                        }
                    ],
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": cls._hook_dispatch_command("stop-monitor", script_type=script_type),
                        }
                    ]
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "Read",
                    "hooks": [
                        {
                            "type": "command",
                            "command": cls._hook_dispatch_command("pre-tool-read", script_type=script_type),
                        }
                    ],
                },
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": cls._hook_dispatch_command("pre-tool-bash", script_type=script_type),
                        }
                    ],
                },
            ],
        }

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

    @staticmethod
    def _hook_assets_dir() -> Path | None:
        assets_dir = Path(__file__).resolve().parent / "hooks"
        return assets_dir if assets_dir.is_dir() else None

    @staticmethod
    def _claude_settings_path(project_root: Path) -> Path:
        return project_root / ".claude" / "settings.json"

    @staticmethod
    def _managed_hook_command_suffixes() -> tuple[str, ...]:
        return (
            f"{CLAUDE_HOOK_DISPATCH} session-start",
            f"{CLAUDE_HOOK_DISPATCH} user-prompt-submit",
            f"{CLAUDE_HOOK_DISPATCH} post-tool-session-state",
            f"{CLAUDE_HOOK_DISPATCH} stop-monitor",
            f"{CLAUDE_HOOK_DISPATCH} pre-tool-read",
            f"{CLAUDE_HOOK_DISPATCH} pre-tool-bash",
        )

    @staticmethod
    def _is_stale_managed_hook_command(command: str, managed_suffixes: tuple[str, ...]) -> bool:
        normalized = str(command or "")
        if any(suffix in normalized for suffix in managed_suffixes):
            return True
        if ".specify/bin/specify-hook" in normalized and '"$CLAUDE_PROJECT_DIR"' in normalized:
            return True
        return False

    def _install_hook_assets(
        self,
        *,
        project_root: Path,
        manifest: IntegrationManifest,
    ) -> list[Path]:
        assets_dir = self._hook_assets_dir()
        if not assets_dir:
            return []

        created: list[Path] = []
        hooks_dir = project_root / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        for src_file in sorted(assets_dir.iterdir()):
            if not src_file.is_file():
                continue
            dst_file = hooks_dir / src_file.name
            shutil.copy2(src_file, dst_file)
            if dst_file.suffix == ".py":
                dst_file.chmod(dst_file.stat().st_mode | 0o111)
            self.record_file_in_manifest(dst_file, project_root, manifest)
            created.append(dst_file)
        return created

    @staticmethod
    def _load_settings_json(settings_path: Path) -> dict[str, Any] | None:
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                loaded = json5.load(f)
        except Exception:
            return None
        return loaded if isinstance(loaded, dict) else None

    @staticmethod
    def _normalize_hook_command(command: Any) -> str:
        return str(command or "").strip()

    def _has_managed_hook_entry(
        self,
        *,
        existing_entries: list[Any],
        matcher: str | None,
        command: str,
    ) -> bool:
        normalized_command = self._normalize_hook_command(command)
        for entry in existing_entries:
            if not isinstance(entry, dict):
                continue
            if matcher is not None and entry.get("matcher") != matcher:
                continue
            hooks = entry.get("hooks", [])
            if not isinstance(hooks, list):
                continue
            for hook in hooks:
                if not isinstance(hook, dict):
                    continue
                if self._normalize_hook_command(hook.get("command")) == normalized_command:
                    return True
        return False

    @staticmethod
    def _strip_stale_managed_hooks(
        entries: list[Any],
        managed_suffixes: tuple[str, ...],
    ) -> tuple[list[Any], bool]:
        stripped: list[Any] = []
        changed = False
        for entry in entries:
            if not isinstance(entry, dict):
                stripped.append(entry)
                continue
            hooks = entry.get("hooks", [])
            if not isinstance(hooks, list):
                stripped.append(entry)
                continue
            kept: list[Any] = []
            for hook in hooks:
                if isinstance(hook, dict) and ClaudeIntegration._is_stale_managed_hook_command(
                    str(hook.get("command", "")),
                    managed_suffixes,
                ):
                    changed = True
                else:
                    kept.append(hook)
            if kept:
                next_entry = dict(entry)
                next_entry["hooks"] = kept
                stripped.append(next_entry)
            else:
                changed = True
        return stripped, changed

    def _merge_managed_hook_settings(
        self,
        settings: dict[str, Any],
        managed_events: dict[str, list[dict[str, Any]]],
    ) -> tuple[dict[str, Any], bool]:
        merged = json.loads(json.dumps(settings))
        changed = False
        managed_suffixes = self._managed_hook_command_suffixes()

        hooks = merged.get("hooks")
        if hooks is None:
            hooks = {}
            merged["hooks"] = hooks
            changed = True
        if not isinstance(hooks, dict):
            return settings, False

        for event_name, managed_entries in managed_events.items():
            event_entries = hooks.get(event_name)
            if event_entries is None:
                event_entries = []
                hooks[event_name] = event_entries
                changed = True
            if not isinstance(event_entries, list):
                continue

            stripped_entries, strip_changed = self._strip_stale_managed_hooks(
                event_entries, managed_suffixes
            )
            if strip_changed:
                hooks[event_name] = stripped_entries
                event_entries = stripped_entries
                changed = True

            for managed_entry in managed_entries:
                matcher = managed_entry.get("matcher")
                hooks_list = managed_entry.get("hooks", [])
                if not isinstance(hooks_list, list):
                    continue
                command = next(
                    (
                        self._normalize_hook_command(hook.get("command"))
                        for hook in hooks_list
                        if isinstance(hook, dict)
                    ),
                    "",
                )
                if not command:
                    continue
                if self._has_managed_hook_entry(
                    existing_entries=event_entries,
                    matcher=matcher if isinstance(matcher, str) else None,
                    command=command,
                ):
                    continue
                event_entries.append(json.loads(json.dumps(managed_entry)))
                changed = True

        return merged, changed

    def _install_or_merge_hook_settings(
        self,
        *,
        project_root: Path,
        manifest: IntegrationManifest,
        script_type: str = "sh",
    ) -> list[Path]:
        settings_path = self._claude_settings_path(project_root)
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        managed_events = self._build_managed_hook_events(script_type=script_type)

        if not settings_path.exists():
            payload = {"hooks": managed_events}
            created = self.write_file_and_record(
                json.dumps(payload, indent=2) + "\n",
                settings_path,
                project_root,
                manifest,
            )
            return [created]

        existing = self._load_settings_json(settings_path)
        if existing is None:
            return []

        merged, changed = self._merge_managed_hook_settings(existing, managed_events)
        if not changed:
            return []

        settings_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        self.record_file_in_manifest(settings_path, project_root, manifest)
        return []

    def teardown(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        *,
        force: bool = False,
    ) -> tuple[list[Path], list[Path]]:
        pre_removed: list[Path] = []
        pre_skipped: list[Path] = []
        settings_path = self._claude_settings_path(project_root)
        if settings_path.exists():
            existing = self._load_settings_json(settings_path)
            if isinstance(existing, dict):
                hooks = existing.get("hooks")
                if isinstance(hooks, dict):
                    changed = False
                    for event_name, entries in list(hooks.items()):
                        if not isinstance(entries, list):
                            continue
                        next_entries = []
                        for entry in entries:
                            if not isinstance(entry, dict):
                                next_entries.append(entry)
                                continue
                            hook_list = entry.get("hooks", [])
                            if not isinstance(hook_list, list):
                                next_entries.append(entry)
                                continue
                            filtered_hooks = [
                                hook
                                for hook in hook_list
                                if not (
                                    isinstance(hook, dict)
                                    and self._is_stale_managed_hook_command(
                                        self._normalize_hook_command(hook.get("command")),
                                        self._managed_hook_command_suffixes(),
                                    )
                                )
                            ]
                            if len(filtered_hooks) != len(hook_list):
                                changed = True
                            if filtered_hooks:
                                next_entry = dict(entry)
                                next_entry["hooks"] = filtered_hooks
                                next_entries.append(next_entry)
                        if next_entries:
                            hooks[event_name] = next_entries
                        else:
                            hooks.pop(event_name, None)
                    if changed:
                        if hooks:
                            settings_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
                        else:
                            existing.pop("hooks", None)
                            if existing:
                                settings_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
                            elif ".claude/settings.json" in manifest.files:
                                settings_path.unlink(missing_ok=True)
                                pre_removed.append(settings_path)
            elif force:
                pre_skipped.append(settings_path)

        removed, skipped = super().teardown(project_root, manifest, force=force)
        merged_removed = [*pre_removed, *[path for path in removed if path not in pre_removed]]
        merged_skipped = [*pre_skipped, *[path for path in skipped if path not in pre_skipped]]
        return merged_removed, merged_skipped

    def _runtime_capability_snapshot(self) -> CapabilitySnapshot:
        """Runtime capability adapter — used by the base class delegation surface."""
        return self._claude_capability_snapshot()

    def _claude_capability_snapshot(self) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            integration_key=self.key,
            native_subagents=True,
            managed_team_supported=True,
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
        marker = "## Claude Code Subagent Result Contract"
        if marker in content:
            return content

        descriptor = describe_delegation_surface(
            command_name=skill_name,
            snapshot=self._claude_capability_snapshot(),
        )
        addendum = (
            "\n"
            "## Claude Code Subagent Result Contract\n\n"
            f"- Preferred result contract: {descriptor.result_contract_hint}\n"
            f"- Result file handoff path: {descriptor.result_handoff_hint}\n"
            "- Normalize subagent-reported statuses like `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, and `NEEDS_CONTEXT` into the shared `WorkerTaskResult` contract before the leader accepts the handoff.\n"
            "- Keep `reported_status` when normalization occurs so the leader can distinguish raw subagent language from canonical orchestration state.\n"
            "- Wait for every subagent's structured handoff before accepting the join point, closing the batch, or declaring completion.\n"
            "- Do not treat an idle subagent as done work; idle without a consumed handoff means the result channel is still unresolved.\n"
            "- Do not interrupt or shut down subagent work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
            "- Treat `DONE_WITH_CONCERNS` as completed work plus follow-up concerns, not as silent success.\n"
            "- Treat `NEEDS_CONTEXT` as a blocked handoff that must carry the missing context or failed assumption explicitly.\n"
        )
        return content + addendum

    def _append_agent_teams_teammate_result_contract(
        self,
        *,
        content: str,
    ) -> str:
        marker = "## Claude Agent Teams Teammate Result Contract"
        if marker in content:
            return content

        descriptor = describe_delegation_surface(
            command_name="implement",
            snapshot=self._claude_capability_snapshot(),
        )
        addendum = (
            "\n"
            "## Claude Agent Teams Teammate Result Contract\n\n"
            f"- Preferred result contract: {descriptor.result_contract_hint}\n"
            f"- Result file handoff path: {descriptor.result_handoff_hint}\n"
            "- Normalize teammate-reported statuses like `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, and `NEEDS_CONTEXT` into the shared `WorkerTaskResult` contract before the leader accepts the handoff.\n"
            "- Keep `reported_status` when normalization occurs so the leader can distinguish raw teammate language from canonical orchestration state.\n"
            "- Wait for every Agent Teams teammate's structured handoff before accepting the join point, closing the team wave, or declaring completion.\n"
            "- Do not treat an idle teammate as done work; idle without a consumed handoff means the team result channel is still unresolved.\n"
            "- Do not interrupt or shut down teammate work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
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
            "- For `sp-implement`, attempt native subagent execution before leader-inline fallback.\n"
            "- Use Claude's native subagent path for `one-subagent` and `parallel-subagents` dispatch shapes whenever the batch is safe to dispatch.\n"
            "- Prefer subagent fan-out over local deep-dive execution when ready tasks have isolated write sets and stable upstream inputs.\n"
            "- Do not begin concrete implementation on the leader path while an untried native subagent path is available for the current batch.\n"
            "- Only use `leader-inline-fallback` after recording the concrete fallback reason in `FEATURE_DIR/implement-tracker.md`.\n"
        )
        if "## Leader Role" in content:
            return content.replace("## Leader Role", addendum + "\n## Leader Role", 1)
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
            "Execute implementation through Claude Code Agent Teams when you explicitly want durable team execution.",
        )
        skill_content = self._render_skill_content(
            raw=raw,
            skill_name="sp-implement-teams",
            description=description,
            source="src/specify_cli/integrations/claude/templates/implement-teams.md",
            project_root=project_root,
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
        created.extend(
            self._install_hook_assets(
                project_root=project_root,
                manifest=manifest,
            )
        )
        created.extend(
            install_shared_hook_launcher_assets(
                project_root,
                manifest=manifest,
            )
        )
        created.extend(
            self._install_or_merge_hook_settings(
                project_root=project_root,
                manifest=manifest,
                script_type=script_type,
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
                    description="Execute the implementation plan by dispatching subagents and integrating their results",
                )
            content = self._append_delegation_surface_contract(
                content=content,
                agent_name="Claude Code",
                command_name=command_name,
                snapshot=snapshot,
                heading="Subagent Dispatch Contract",
            )
            content = self._append_worker_result_contract(
                content=content,
                skill_name=command_name,
            )
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
            content = self._append_agent_teams_teammate_result_contract(content=content)
            implement_teams_skill.write_bytes(content.encode("utf-8"))
            self.record_file_in_manifest(implement_teams_skill, project_root, manifest)

        return created

    def repair_runtime_assets(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        **opts: Any,
    ) -> list[Path]:
        created: list[Path] = []
        created.extend(self.install_scripts(project_root, manifest))
        created.extend(
            self._install_hook_assets(
                project_root=project_root,
                manifest=manifest,
            )
        )
        created.extend(
            install_shared_hook_launcher_assets(
                project_root,
                manifest=manifest,
            )
        )
        created.extend(
            self._install_or_merge_hook_settings(
                project_root=project_root,
                manifest=manifest,
                script_type=opts.get("script_type", "sh"),
            )
        )
        return created


__all__ = ["ClaudeIntegration", "ClaudeMultiAgentAdapter"]
