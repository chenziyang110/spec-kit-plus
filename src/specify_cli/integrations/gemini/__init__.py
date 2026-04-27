"""Gemini CLI integration."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import json5

from ..base import TomlIntegration
from ..manifest import IntegrationManifest
from .multi_agent import GeminiMultiAgentAdapter

GEMINI_HOOK_DISPATCH = "gemini-hook-dispatch.py"
GEMINI_MANAGED_HOOK_EVENTS = {
    "SessionStart": [
        {
            "matcher": "startup",
            "hooks": [
                {
                    "name": "spec-kit-session-start",
                    "type": "command",
                    "command": f"python .gemini/hooks/{GEMINI_HOOK_DISPATCH} session-start",
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
                    "command": f"python .gemini/hooks/{GEMINI_HOOK_DISPATCH} before-agent",
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
                    "command": f"python .gemini/hooks/{GEMINI_HOOK_DISPATCH} before-tool",
                }
            ],
        }
    ],
}


class GeminiIntegration(TomlIntegration):
    key = "gemini"
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

    def _merge_managed_hook_settings(
        self,
        settings: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        merged = json.loads(json.dumps(settings))
        changed = False

        hooks = merged.get("hooks")
        if hooks is None:
            hooks = {}
            merged["hooks"] = hooks
            changed = True
        if not isinstance(hooks, dict):
            return settings, False

        for event_name, managed_entries in GEMINI_MANAGED_HOOK_EVENTS.items():
            event_entries = hooks.get(event_name)
            if event_entries is None:
                event_entries = []
                hooks[event_name] = event_entries
                changed = True
            if not isinstance(event_entries, list):
                continue

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
    ) -> list[Path]:
        settings_path = self._gemini_settings_path(project_root)
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        if not settings_path.exists():
            payload = {"hooks": GEMINI_MANAGED_HOOK_EVENTS}
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

        merged, changed = self._merge_managed_hook_settings(existing)
        if not changed:
            return []

        settings_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
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
        self._install_or_merge_hook_settings(project_root=project_root, manifest=manifest)
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
