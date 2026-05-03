"""Gemini CLI integration."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import json5

from ..base import TomlIntegration
from ..manifest import IntegrationManifest
from ...launcher import install_shared_hook_launcher_assets, render_hook_launcher_command
from .multi_agent import GeminiMultiAgentAdapter

GEMINI_HOOK_DISPATCH = "gemini-hook-dispatch.py"


class GeminiIntegration(TomlIntegration):
    key = "gemini"

    @classmethod
    def _build_managed_hook_events(cls, *, script_type: str = "sh") -> dict[str, list[dict[str, Any]]]:
        return {
            "SessionStart": [
                {
                    "matcher": "startup",
                    "hooks": [
                        {
                            "name": "spec-kit-session-start",
                            "type": "command",
                            "command": render_hook_launcher_command(
                                "gemini",
                                "session-start",
                                project_dir_env_var="GEMINI_PROJECT_DIR",
                                script_type=script_type,
                            ),
                        }
                    ],
                }
            ],
            "BeforeAgent": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "name": "spec-kit-before-agent",
                            "type": "command",
                            "command": render_hook_launcher_command(
                                "gemini",
                                "before-agent",
                                project_dir_env_var="GEMINI_PROJECT_DIR",
                                script_type=script_type,
                            ),
                        }
                    ],
                }
            ],
            "BeforeTool": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "name": "spec-kit-before-tool",
                            "type": "command",
                            "command": render_hook_launcher_command(
                                "gemini",
                                "before-tool",
                                project_dir_env_var="GEMINI_PROJECT_DIR",
                                script_type=script_type,
                            ),
                        }
                    ],
                }
            ],
        }

    config = {
        "name": "Gemini CLI",
        "folder": ".gemini/",
        "commands_subdir": "commands",
        "install_url": "https://github.com/google-gemini/gemini-cli",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".gemini/commands",
        "format": "toml",
        "args": "{{args}}",
        "extension": ".toml",
    }
    context_file = "GEMINI.md"
    question_tool_config = {
        "tool_name": "ask_user",
        "question_limit": "up to 4 questions per call",
        "option_limit": "2-4 options for `choice` questions",
        "question_fields": ["header", "type", "question"],
        "option_fields": ["label", "description"],
        "extra_notes": [
            "Supported question types are `choice`, `yesno`, and `text`.",
            "Use `choice` by default for clarification and bounded selections; use `placeholder` only for `text` questions.",
        ],
    }

    @staticmethod
    def _hook_assets_dir() -> Path | None:
        assets_dir = Path(__file__).resolve().parent / "hooks"
        return assets_dir if assets_dir.is_dir() else None

    @staticmethod
    def _gemini_settings_path(project_root: Path) -> Path:
        return project_root / ".gemini" / "settings.json"

    @staticmethod
    def _managed_hook_command_suffixes() -> tuple[str, ...]:
        return (
            f"{GEMINI_HOOK_DISPATCH} session-start",
            f"{GEMINI_HOOK_DISPATCH} before-agent",
            f"{GEMINI_HOOK_DISPATCH} before-tool",
        )

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
        hooks_dir = project_root / ".gemini" / "hooks"
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
                if isinstance(hook, dict) and any(
                    suffix in str(hook.get("command", ""))
                    for suffix in managed_suffixes
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
        settings_path = self._gemini_settings_path(project_root)
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
        self._install_hook_assets(project_root=project_root, manifest=manifest)
        install_shared_hook_launcher_assets(
            project_root,
            manifest=manifest,
        )
        self._install_or_merge_hook_settings(
            project_root=project_root,
            manifest=manifest,
            script_type=opts.get("script_type", "sh"),
        )
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

    def teardown(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        *,
        force: bool = False,
    ) -> tuple[list[Path], list[Path]]:
        pre_removed: list[Path] = []
        pre_skipped: list[Path] = []
        settings_path = self._gemini_settings_path(project_root)
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
                                    and any(
                                        suffix in self._normalize_hook_command(hook.get("command"))
                                        for suffix in self._managed_hook_command_suffixes()
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
                            elif ".gemini/settings.json" in manifest.files:
                                settings_path.unlink(missing_ok=True)
                                pre_removed.append(settings_path)
            elif force:
                pre_skipped.append(settings_path)

        removed, skipped = super().teardown(project_root, manifest, force=force)
        merged_removed = [*pre_removed, *[path for path in removed if path not in pre_removed]]
        merged_skipped = [*pre_skipped, *[path for path in skipped if path not in pre_skipped]]
        return merged_removed, merged_skipped


__all__ = ["GeminiIntegration", "GeminiMultiAgentAdapter"]
