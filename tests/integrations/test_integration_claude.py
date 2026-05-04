"""Tests for ClaudeIntegration."""

import importlib.util
import json
import os
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path

import yaml

from specify_cli.integrations import INTEGRATION_REGISTRY, get_integration
from specify_cli.integrations.base import IntegrationBase
from specify_cli.integrations.claude import ARGUMENT_HINTS
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import render_hook_launcher_command

SPEC_KIT_BLOCK_START = "<!-- SPEC-KIT:BEGIN -->"


def _load_claude_hook_dispatch_module():
    repo_root = Path(__file__).resolve().parents[2]
    hook_path = repo_root / "src" / "specify_cli" / "integrations" / "claude" / "hooks" / "claude-hook-dispatch.py"
    spec = importlib.util.spec_from_file_location("claude_hook_dispatch_for_tests", hook_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestClaudeIntegration:
    @staticmethod
    def _expected_launcher_command(route: str, *, script_type: str = "sh") -> str:
        return render_hook_launcher_command(
            "claude",
            route,
            project_dir_env_var="CLAUDE_PROJECT_DIR",
            script_type=script_type,
        )

    @staticmethod
    def _command_stems() -> list[str]:
        claude = get_integration("claude")
        return [template.stem for template in claude.list_command_templates()]

    @staticmethod
    def _template_files() -> list[str]:
        claude = get_integration("claude")
        templates_dir = claude.shared_templates_dir()
        if not templates_dir or not templates_dir.is_dir():
            return []

        return sorted(
            path.relative_to(templates_dir).as_posix()
            for path in templates_dir.rglob("*")
            if path.is_file() and path.name != "vscode-settings.json"
        )

    @staticmethod
    def _passive_skill_names() -> list[str]:
        claude = get_integration("claude")
        passive_dir = claude.shared_passive_skills_dir()
        if not passive_dir or not passive_dir.is_dir():
            return []

        return sorted(
            path.name
            for path in passive_dir.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )

    @staticmethod
    def _passive_skill_files() -> list[str]:
        claude = get_integration("claude")
        passive_dir = claude.shared_passive_skills_dir()
        if not passive_dir or not passive_dir.is_dir():
            return []

        return sorted(
            path.relative_to(passive_dir).as_posix()
            for path in passive_dir.rglob("*")
            if path.is_file()
        )

    @classmethod
    def _expected_inventory(cls, script_variant: str) -> list[str]:
        skills_prefix = ".claude/skills"
        expected = []

        for stem in cls._command_stems():
            expected.append(f"{skills_prefix}/sp-{stem}/SKILL.md")
        expected.append(f"{skills_prefix}/sp-implement-teams/SKILL.md")
        for relative_file in cls._passive_skill_files():
            expected.append(f"{skills_prefix}/{relative_file}")

        expected.extend(
            [
                "CLAUDE.md",
                ".claude/hooks/README.md",
                ".claude/hooks/claude-hook-dispatch.py",
                ".claude/settings.json",
                ".specify/bin/specify-hook",
                ".specify/bin/specify-hook.cmd",
                ".specify/bin/specify-hook.py",
                ".specify/init-options.json",
                ".specify/integration.json",
                ".specify/integrations/claude.manifest.json",
                ".specify/integrations/claude/scripts/update-context.ps1",
                ".specify/integrations/claude/scripts/update-context.sh",
                ".specify/integrations/speckit.manifest.json",
                ".specify/memory/constitution.md",
                ".specify/memory/project-learnings.md",
                ".specify/memory/project-rules.md",
                ".specify/project-map/status.json",
                ".specify/project-map/index/status.json",
            ]
        )

        if script_variant == "sh":
            expected.extend(
                [
                    ".specify/scripts/bash/check-prerequisites.sh",
                    ".specify/scripts/bash/common.sh",
                    ".specify/scripts/bash/create-new-feature.sh",
                    ".specify/scripts/bash/prd-state.sh",
                    ".specify/scripts/bash/project-map-freshness.sh",
                    ".specify/scripts/bash/quick-state.sh",
                    ".specify/scripts/bash/setup-plan.sh",
                    ".specify/scripts/bash/sync-ecc-to-codex.sh",
                    ".specify/scripts/bash/update-agent-context.sh",
                ]
            )
        else:
            expected.extend(
                [
                    ".specify/scripts/powershell/check-prerequisites.ps1",
                    ".specify/scripts/powershell/common.ps1",
                    ".specify/scripts/powershell/create-new-feature.ps1",
                    ".specify/scripts/powershell/prd-state.ps1",
                    ".specify/scripts/powershell/project-map-freshness.ps1",
                    ".specify/scripts/powershell/quick-state.ps1",
                    ".specify/scripts/powershell/setup-plan.ps1",
                    ".specify/scripts/powershell/sync-ecc-to-codex.ps1",
                    ".specify/scripts/powershell/update-agent-context.ps1",
                ]
            )

        expected.extend(f".specify/templates/{name}" for name in cls._template_files())
        return sorted(expected)

    def test_registered(self):
        assert "claude" in INTEGRATION_REGISTRY
        assert get_integration("claude") is not None

    def test_is_base_integration(self):
        assert isinstance(get_integration("claude"), IntegrationBase)

    def test_config_uses_skills(self):
        integration = get_integration("claude")
        assert integration.config["folder"] == ".claude/"
        assert integration.config["commands_subdir"] == "skills"

    def test_registrar_config_uses_skill_layout(self):
        integration = get_integration("claude")
        assert integration.registrar_config["dir"] == ".claude/skills"
        assert integration.registrar_config["format"] == "markdown"
        assert integration.registrar_config["args"] == "$ARGUMENTS"
        assert integration.registrar_config["extension"] == "/SKILL.md"

    def test_context_file(self):
        integration = get_integration("claude")
        assert integration.context_file == "CLAUDE.md"

    def test_setup_creates_skill_files(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        created = integration.setup(tmp_path, manifest, script_type="sh")

        skill_files = [path for path in created if path.name == "SKILL.md"]
        assert skill_files

        skills_dir = tmp_path / ".claude" / "skills"
        assert skills_dir.is_dir()

        plan_skill = skills_dir / "sp-plan" / "SKILL.md"
        assert plan_skill.exists()

        content = plan_skill.read_text(encoding="utf-8")
        assert "{SCRIPT}" not in content
        assert "{ARGS}" not in content
        assert "__AGENT__" not in content

        parts = content.split("---", 2)
        parsed = yaml.safe_load(parts[1])
        assert parsed["name"] == "sp-plan"
        assert parsed["user-invocable"] is True
        assert parsed["disable-model-invocation"] is True
        assert parsed["metadata"]["source"] == "templates/commands/plan.md"
        assert (skills_dir / "sp-implement-teams" / "SKILL.md").exists()

    def test_setup_keeps_passive_skills_model_invokable(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        passive_skill = tmp_path / ".claude" / "skills" / "spec-kit-workflow-routing" / "SKILL.md"
        assert passive_skill.exists()

        content = passive_skill.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        parsed = yaml.safe_load(parts[1])

        assert parsed["name"] == "spec-kit-workflow-routing"
        assert "user-invocable" not in parsed
        assert "disable-model-invocation" not in parsed
        assert parsed["metadata"]["source"] == "templates/passive-skills/spec-kit-workflow-routing/SKILL.md"

    def test_setup_installs_update_context_scripts(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        created = integration.setup(tmp_path, manifest, script_type="sh")

        scripts_dir = tmp_path / ".specify" / "integrations" / "claude" / "scripts"
        assert scripts_dir.is_dir()
        assert (scripts_dir / "update-context.sh").exists()
        assert (scripts_dir / "update-context.ps1").exists()

        tracked = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in created}
        assert ".specify/integrations/claude/scripts/update-context.sh" in tracked
        assert ".specify/integrations/claude/scripts/update-context.ps1" in tracked

    def test_setup_installs_hook_assets_and_settings_json(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        created = integration.setup(tmp_path, manifest, script_type="sh")

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        settings_path = tmp_path / ".claude" / "settings.json"
        shared_launcher = tmp_path / ".specify" / "bin" / "specify-hook.py"

        assert hook_script.exists()
        assert settings_path.exists()
        assert shared_launcher.exists()

        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "hooks" in payload
        assert "UserPromptSubmit" in payload["hooks"]
        assert "PreToolUse" in payload["hooks"]

        commands = [
            hook["command"]
            for entries in payload["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict) and isinstance(hook.get("command"), str)
        ]
        assert any(command == self._expected_launcher_command("user-prompt-submit", script_type="sh") for command in commands)
        assert any(command == self._expected_launcher_command("pre-tool-read", script_type="sh") for command in commands)
        assert any(command == self._expected_launcher_command("pre-tool-bash", script_type="sh") for command in commands)
        assert any(command == self._expected_launcher_command("session-start", script_type="sh") for command in commands)
        assert any(command == self._expected_launcher_command("post-tool-session-state", script_type="sh") for command in commands)
        assert any(command == self._expected_launcher_command("stop-monitor", script_type="sh") for command in commands)

        tracked = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in created}
        assert ".claude/hooks/claude-hook-dispatch.py" in tracked
        assert ".claude/settings.json" in tracked
        assert ".specify/bin/specify-hook.py" in tracked

    def test_setup_writes_windows_safe_hook_commands(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="ps")

        settings_path = tmp_path / ".claude" / "settings.json"
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for entries in payload["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict) and isinstance(hook.get("command"), str)
        ]

        assert commands
        for command in commands:
            assert command.startswith('"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook.cmd claude ')
            assert "$env:CLAUDE_PROJECT_DIR" not in command

    def test_setup_refreshes_existing_managed_hook_asset(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        hook_script.write_text("# stale managed hook\n", encoding="utf-8")

        manifest_second = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest_second, script_type="sh")

        refreshed = hook_script.read_text(encoding="utf-8")
        assert "# stale managed hook" not in refreshed
        assert "def _handle_stop_monitor" in refreshed

    def test_claude_hook_adapter_respects_event_specific_output_schema(self):
        module = _load_claude_hook_dispatch_module()
        blocked = {
            "status": "blocked",
            "errors": ["blocked reason"],
            "warnings": ["warning context"],
            "actions": ["action context"],
        }
        warned = {
            "status": "warn",
            "errors": [],
            "warnings": ["warning context"],
            "actions": [],
        }

        pre_tool = module._shared_to_claude_output(hook_event_name="PreToolUse", shared_payload=blocked)
        assert pre_tool == {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "blocked reason",
            }
        }

        prompt = module._shared_to_claude_output(hook_event_name="UserPromptSubmit", shared_payload=blocked)
        assert prompt["decision"] == "block"
        assert prompt["reason"] == "blocked reason"
        assert "hookSpecificOutput" not in prompt

        post_tool = module._shared_to_claude_output(hook_event_name="PostToolUse", shared_payload=blocked)
        post_tool_output = post_tool["hookSpecificOutput"]
        assert post_tool_output["hookEventName"] == "PostToolUse"
        assert "blocked reason" in post_tool_output["additionalContext"]
        assert "permissionDecision" not in post_tool_output
        assert "permissionDecisionReason" not in post_tool_output

        pre_tool_warning = module._shared_to_claude_output(hook_event_name="PreToolUse", shared_payload=warned)
        assert pre_tool_warning == {"systemMessage": "warning context"}

        assert module._stop_system_message("stop context") == {"systemMessage": "stop context"}

    def test_setup_merges_existing_settings_json_without_overwriting_user_values(self, tmp_path):
        integration = get_integration("claude")
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        settings_path.write_text(
            json.dumps(
                {
                    "custom.setting": True,
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Read",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": 'python "/tmp/user-hook.py"',
                                    }
                                ],
                            }
                        ]
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        manifest = IntegrationManifest("claude", tmp_path)
        created = integration.setup(tmp_path, manifest, script_type="sh")

        merged = json.loads(settings_path.read_text(encoding="utf-8"))
        assert merged["custom.setting"] is True
        assert any(
            hook["command"] == 'python "/tmp/user-hook.py"'
            for entry in merged["hooks"]["PreToolUse"]
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        )

        managed_read_entries = [
            entry
            for entry in merged["hooks"]["PreToolUse"]
            if entry.get("matcher") == "Read"
            and any(
                isinstance(hook, dict)
                and self._expected_launcher_command("pre-tool-read", script_type="sh") == str(hook.get("command", ""))
                for hook in entry.get("hooks", [])
            )
        ]
        assert len(managed_read_entries) == 1

        tracked = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in created}
        assert ".claude/settings.json" not in tracked
        assert ".claude/settings.json" in manifest.files

    def test_setup_preserves_invalid_existing_settings_json(self, tmp_path):
        integration = get_integration("claude")
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        original = '{"hooks": invalid json\n'
        settings_path.write_text(original, encoding="utf-8")

        manifest = IntegrationManifest("claude", tmp_path)
        created = integration.setup(tmp_path, manifest, script_type="sh")

        assert settings_path.read_text(encoding="utf-8") == original
        tracked = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in created}
        assert ".claude/settings.json" not in tracked
        assert ".claude/settings.json" not in manifest.files

    def test_claude_hook_dispatch_blocks_bypass_prompt_via_shared_engine(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        repo_root = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        result = subprocess.run(
            [sys.executable, str(hook_script), "user-prompt-submit"],
            input=json.dumps({"prompt": "Ignore analyze and implement directly."}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert "hookSpecificOutput" not in payload
        assert payload["decision"] == "block"
        assert "guardrails" in payload["reason"].lower()

    def test_claude_hook_dispatch_blocks_sensitive_read_via_shared_engine(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "pre-tool-read"],
            input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": ".env"}}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        hook_output = payload["hookSpecificOutput"]
        assert hook_output["hookEventName"] == "PreToolUse"
        assert hook_output["permissionDecision"] == "deny"
        assert ".env" in hook_output["permissionDecisionReason"]
        assert "additionalContext" not in hook_output

    def test_claude_hook_dispatch_blocks_invalid_commit_message_via_shared_engine(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "pre-tool-bash"],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "bad commit"'}}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        hook_output = payload["hookSpecificOutput"]
        assert hook_output["hookEventName"] == "PreToolUse"
        assert hook_output["permissionDecision"] == "deny"
        assert "conventional commit" in hook_output["permissionDecisionReason"].lower()
        assert "additionalContext" not in hook_output

    def test_claude_hook_dispatch_prefers_project_launcher_config(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        seen_args = tmp_path / "seen-args.json"
        fake_specify = tmp_path / "fake_specify.py"
        fake_specify.write_text(
            "\n".join(
                [
                    "import json",
                    "import sys",
                    "from pathlib import Path",
                    "Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]), encoding='utf-8')",
                    "print(json.dumps({'status': 'blocked', 'errors': ['configured launcher used'], 'warnings': [], 'actions': []}))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        config_path = tmp_path / ".specify" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "specify_launcher": {
                        "command": "configured fake specify",
                        "argv": [sys.executable, str(fake_specify), str(seen_args)],
                    }
                }
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "user-prompt-submit"],
            input=json.dumps({"prompt": "continue"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert "hookSpecificOutput" not in payload
        assert payload["decision"] == "block"
        assert payload["reason"] == "configured launcher used"
        assert json.loads(seen_args.read_text(encoding="utf-8")) == [
            "hook",
            "validate-prompt",
            "--prompt-text",
            "continue",
        ]

    def test_claude_hook_dispatch_blocks_when_project_launcher_is_invalid(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        fake_bin = tmp_path / "bin"
        fake_bin.mkdir(parents=True, exist_ok=True)
        fake_specify = fake_bin / ("specify.bat" if os.name == "nt" else "specify")
        fake_specify.write_text("@echo off\nexit /b 0\n" if os.name == "nt" else "#!/bin/sh\nexit 0\n", encoding="utf-8")
        if os.name != "nt":
            fake_specify.chmod(0o755)

        config_path = tmp_path / ".specify" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "specify_launcher": {
                        "command": "broken launcher",
                        "argv": ["definitely-missing-specify-command", "specify"],
                    }
                }
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "user-prompt-submit"],
            input=json.dumps({"prompt": "continue"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "block"
        assert "launcher" in payload["reason"].lower()

    def test_claude_hook_dispatch_adds_statusline_context_on_session_start(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-plan`",
                    "- status: `active`",
                    "",
                    "## Phase Mode",
                    "",
                    "- phase_mode: `design-only`",
                    "- summary: demo",
                    "",
                    "## Next Action",
                    "",
                    "- refine execution approach",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "session-start"],
            input=json.dumps({}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        hook_output = payload["hookSpecificOutput"]
        assert hook_output["hookEventName"] == "SessionStart"
        assert "plan:design-only" in hook_output["additionalContext"]

    def test_claude_hook_session_start_appends_recovery_summary(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-specify`",
                    "- status: `active`",
                    "",
                    "## Phase Mode",
                    "",
                    "- phase_mode: `planning-only`",
                    "- summary: draft specification",
                    "",
                    "## Allowed Artifact Writes",
                    "",
                    "- spec.md",
                    "- checklists/requirements.md",
                    "",
                    "## Forbidden Actions",
                    "",
                    "- edit source code",
                    "- run implementation tasks",
                    "",
                    "## Authoritative Files",
                    "",
                    "- spec.md",
                    "- workflow-state.md",
                    "",
                    "## Next Action",
                    "",
                    "- refine scope",
                    "",
                    "## Next Command",
                    "",
                    "- `/sp.plan`",
                    "",
                    "## Learning Signals",
                    "",
                    "- route_reason: `spec not yet approved for implementation`",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        compaction_path = tmp_path / ".specify" / "runtime" / "compaction" / "specify-001-demo" / "latest.json"
        result = subprocess.run(
            [sys.executable, str(hook_script), "session-start"],
            input=json.dumps({}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        additional_context = payload["hookSpecificOutput"]["additionalContext"]
        assert "planning-only" in additional_context
        assert "/sp.plan" in additional_context
        assert compaction_path.exists()

    def test_claude_hook_dispatch_adds_session_state_warning_on_post_tool_use(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-implement`",
                    "- status: `active`",
                    "",
                    "## Phase Mode",
                    "",
                    "- phase_mode: `execution-only`",
                    "",
                    "## Next Command",
                    "",
                    "- `/sp.plan`",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (feature_dir / "implement-tracker.md").write_text(
            "\n".join(
                [
                    "---",
                    "status: active",
                    "resume_decision: resume-here",
                    "---",
                    "",
                    "## Current Focus",
                    "",
                    "- current_batch: batch-1",
                    "- goal: finish demo",
                    "- next_action: keep coding",
                    "",
                    "## Execution State",
                    "",
                    "- retry_attempts: 0",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "post-tool-session-state"],
            input=json.dumps({"tool_name": "Write"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        hook_output = payload["hookSpecificOutput"]
        assert hook_output["hookEventName"] == "PostToolUse"
        assert "next_command is /sp.plan" in hook_output["additionalContext"]

    def test_claude_hook_dispatch_surfaces_learning_signal_on_post_tool_use(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-plan`",
                    "- status: `active`",
                    "- retry_attempts: `3`",
                    "",
                    "## False Starts",
                    "",
                    "- assumed it was an implementation issue before checking planning dependencies",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "post-tool-session-state"],
            input=json.dumps({"tool_name": "Write"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        hook_output = payload["hookSpecificOutput"]
        assert hook_output["hookEventName"] == "PostToolUse"
        assert "learning pain score" in hook_output["additionalContext"]
        assert "review-learning --command plan" in hook_output["additionalContext"]

    def test_claude_hook_dispatch_blocks_stop_when_checkpoint_state_is_missing(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-implement`",
                    "- status: `active`",
                    "",
                    "## Phase Mode",
                    "",
                    "- phase_mode: `execution-only`",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "stop-monitor"],
            input=json.dumps({}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "block"
        assert "implement-tracker.md is missing" in payload["reason"]
        assert "hookSpecificOutput" not in payload

    def test_claude_hook_dispatch_surfaces_stop_checkpoint_warning_as_system_message(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-plan`",
                    "- status: `active`",
                    "",
                    "## Phase Mode",
                    "",
                    "- phase_mode: `design-only`",
                    "",
                    "## Next Action",
                    "",
                    "- run manual scenarios from quickstart.md to validate all user stories",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "stop-monitor"],
            input=json.dumps({}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert "hookSpecificOutput" not in payload
        assert payload["systemMessage"].startswith("checkpoint recommended before further work continues")
        assert "Resume cue: run manual scenarios from quickstart.md to validate all user stories." in payload["systemMessage"]

    def test_claude_hook_dispatch_session_start_builds_without_read_side_fallback(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-specify`",
                    "- status: `active`",
                    "",
                    "## Phase Mode",
                    "",
                    "- phase_mode: `planning-only`",
                    "- summary: draft specification",
                    "",
                    "## Next Action",
                    "",
                    "- refine scope",
                    "",
                    "## Next Command",
                    "",
                    "- `/sp.plan`",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        compaction_path = tmp_path / ".specify" / "runtime" / "compaction" / "specify-001-demo" / "latest.json"
        result = subprocess.run(
            [sys.executable, str(hook_script), "user-prompt-submit"],
            input=json.dumps({"prompt": "continue"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        assert not compaction_path.exists()

    def test_claude_hook_dispatch_reads_compaction_resume_context_on_session_start(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-plan`",
                    "- status: `active`",
                    "",
                    "## Phase Mode",
                    "",
                    "- phase_mode: `design-only`",
                    "- summary: demo",
                    "",
                    "## Next Action",
                    "",
                    "- refine execution approach",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        compaction_dir = tmp_path / ".specify" / "runtime" / "compaction" / "plan-001-demo"
        compaction_dir.mkdir(parents=True, exist_ok=True)
        (compaction_dir / "latest.json").write_text(
            json.dumps(
                {
                    "phase_state": {"next_action": "finish design review"},
                    "resume_cue": ["Resume cue: finish design review."],
                }
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "session-start"],
            input=json.dumps({}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        hook_output = payload["hookSpecificOutput"]
        assert "plan:design-only" in hook_output["additionalContext"]
        assert "Resume cue: finish design review." in hook_output["additionalContext"]
        assert "Phase:" not in hook_output["additionalContext"]

    def test_claude_hook_dispatch_surfaces_learning_signal_on_stop(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "workflow-state.md").write_text(
            "\n".join(
                [
                    "# Workflow State: Demo",
                    "",
                    "## Current Command",
                    "",
                    "- active_command: `sp-plan`",
                    "- status: `active`",
                    "- retry_attempts: `3`",
                    "",
                    "## Next Action",
                    "",
                    "- capture planning dependency learning",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "stop-monitor"],
            input=json.dumps({}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert "hookSpecificOutput" not in payload
        assert "learning pain score" in payload["systemMessage"]
        assert "review-learning --command plan" in payload["systemMessage"]

    def test_uninstall_preserves_user_settings_while_removing_managed_hooks(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.install(tmp_path, manifest, script_type="sh")
        manifest.save()

        settings_path = tmp_path / ".claude" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        settings["custom.setting"] = True
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

        removed, skipped = integration.uninstall(tmp_path, manifest)

        assert settings_path.exists()
        remaining = json.loads(settings_path.read_text(encoding="utf-8"))
        assert remaining["custom.setting"] is True
        remaining_commands = [
            hook["command"]
            for entries in remaining.get("hooks", {}).values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict) and isinstance(hook.get("command"), str)
        ]
        assert not any("claude-hook-dispatch.py" in command for command in remaining_commands)
        assert (tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py") in removed
        assert skipped == [] or settings_path in skipped

    def test_setup_does_not_duplicate_managed_hook_entries_on_repeat_install(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        manifest_second = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest_second, script_type="sh")

        settings_path = tmp_path / ".claude" / "settings.json"
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for entries in payload["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict) and isinstance(hook.get("command"), str)
        ]
        suffixes = (
            self._expected_launcher_command("session-start", script_type="sh"),
            self._expected_launcher_command("user-prompt-submit", script_type="sh"),
            self._expected_launcher_command("pre-tool-read", script_type="sh"),
            self._expected_launcher_command("pre-tool-bash", script_type="sh"),
            self._expected_launcher_command("post-tool-session-state", script_type="sh"),
            self._expected_launcher_command("stop-monitor", script_type="sh"),
        )
        for suffix in suffixes:
            assert sum(command == suffix for command in commands) == 1

    def test_uninstall_removes_install_owned_settings_json_when_only_managed_hooks_exist(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.install(tmp_path, manifest, script_type="sh")
        manifest.save()

        settings_path = tmp_path / ".claude" / "settings.json"
        assert settings_path.exists()

        removed, skipped = integration.uninstall(tmp_path, manifest)

        assert settings_path in removed
        assert not settings_path.exists()
        assert skipped == []

    def test_complete_file_inventory_sh(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-inventory-sh"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(
                app,
                [
                    "init",
                    "--here",
                    "--integration",
                    "claude",
                    "--script",
                    "sh",
                    "--no-git",
                    "--ignore-agent-tools",
                ],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        actual = sorted(
            path.relative_to(project).as_posix()
            for path in project.rglob("*")
            if path.is_file()
        )
        expected = self._expected_inventory("sh")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
        )

    def test_complete_file_inventory_ps(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-inventory-ps"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(
                app,
                [
                    "init",
                    "--here",
                    "--integration",
                    "claude",
                    "--script",
                    "ps",
                    "--no-git",
                    "--ignore-agent-tools",
                ],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        actual = sorted(
            path.relative_to(project).as_posix()
            for path in project.rglob("*")
            if path.is_file()
        )
        expected = self._expected_inventory("ps")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
        )

    def test_ai_flag_auto_promotes_and_enables_skills(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-promote"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "init",
                    "--here",
                    "--ai",
                    "claude",
                    "--script",
                    "sh",
                    "--no-git",
                    "--ignore-agent-tools",
                ],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert (project / ".claude" / "skills" / "sp-plan" / "SKILL.md").exists()
        assert (project / ".claude" / "skills" / "spec-kit-workflow-routing" / "SKILL.md").exists()
        assert (project / ".claude" / "skills" / "spec-kit-project-map-gate" / "SKILL.md").exists()
        assert not (project / ".claude" / "commands").exists()

        init_options = json.loads(
            (project / ".specify" / "init-options.json").read_text(encoding="utf-8")
        )
        assert init_options["ai"] == "claude"
        assert init_options["ai_skills"] is True
        assert init_options["integration"] == "claude"

    def test_init_bootstraps_context_file(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-context"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "init",
                    "--here",
                    "--ai",
                    "claude",
                    "--script",
                    "sh",
                    "--no-git",
                    "--ignore-agent-tools",
                ],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert (project / "CLAUDE.md").is_file()

    def test_init_bootstrapped_context_file_contains_managed_guidance(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-context-guidance"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "init",
                    "--here",
                    "--ai",
                    "claude",
                    "--script",
                    "sh",
                    "--no-git",
                    "--ignore-agent-tools",
                ],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        content = (project / "CLAUDE.md").read_text(encoding="utf-8")
        assert "## Active Technologies" in content
        assert SPEC_KIT_BLOCK_START in content
        assert "[AGENT]" in content
        assert "specify -> plan" in content
        assert "PROJECT-HANDBOOK.md" in content
        assert ".specify/project-map/" in content
        assert ".specify/memory/project-rules.md" in content
        assert "Shared project memory is always available" in content
        assert "not just when a `sp-*` workflow is active" in content
        assert "## Workflow Routing" in content
        assert "sp-fast" in content
        assert "sp-quick" in content
        assert "sp-specify" in content
        assert "sp-debug" in content
        assert "sp-test-scan" in content
        assert "sp-test-build" in content
        assert "## Artifact Priority" in content
        assert "workflow-state.md" in content
        assert "alignment.md" in content
        assert "context.md" in content
        assert "plan.md" in content
        assert "tasks.md" in content
        assert ".specify/testing/TESTING_CONTRACT.md" in content
        assert ".specify/project-map/index/status.json" in content
        assert "## Map Maintenance" in content
        assert "refresh `PROJECT-HANDBOOK.md`" in content
        assert "git-baseline freshness" in content.lower()
        assert "complete-refresh" in content
        assert "manual override/fallback" in content.lower()

    def test_init_augments_existing_context_file_with_managed_guidance(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-context-existing"
        project.mkdir()
        claude_file = project / "CLAUDE.md"
        initial = "# User CLAUDE\n\nCustom note.\n"
        claude_file.write_text(initial, encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "init",
                    "--here",
                    "--force",
                    "--ai",
                    "claude",
                    "--script",
                    "sh",
                    "--no-git",
                    "--ignore-agent-tools",
                ],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        content = claude_file.read_text(encoding="utf-8")
        assert content.startswith(initial)
        assert SPEC_KIT_BLOCK_START in content
        assert "PROJECT-HANDBOOK.md" in content
        assert ".specify/project-map/" in content
        assert "## Workflow Routing" in content
        assert "## Artifact Priority" in content
        assert "## Map Maintenance" in content

    def test_integration_flag_creates_skill_files(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-integration"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "init",
                    "--here",
                    "--integration",
                    "claude",
                    "--script",
                    "sh",
                    "--no-git",
                    "--ignore-agent-tools",
                ],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert (project / ".claude" / "skills" / "sp-specify" / "SKILL.md").exists()
        assert (project / ".specify" / "integrations" / "claude.manifest.json").exists()

    def test_interactive_claude_selection_uses_integration_path(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / "claude-interactive"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            with patch("specify_cli.select_with_arrows", return_value="claude"):
                result = runner.invoke(
                    app,
                    [
                        "init",
                        "--here",
                        "--script",
                        "sh",
                        "--no-git",
                        "--ignore-agent-tools",
                    ],
                    catch_exceptions=False,
                )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert (project / ".specify" / "integration.json").exists()
        assert (project / ".specify" / "integrations" / "claude.manifest.json").exists()

        skill_file = project / ".claude" / "skills" / "sp-plan" / "SKILL.md"
        assert skill_file.exists()
        skill_content = skill_file.read_text(encoding="utf-8")
        assert "user-invocable: true" in skill_content
        assert "disable-model-invocation: true" in skill_content

        init_options = json.loads(
            (project / ".specify" / "init-options.json").read_text(encoding="utf-8")
        )
        assert init_options["ai"] == "claude"
        assert init_options["ai_skills"] is True
        assert init_options["integration"] == "claude"

    def test_claude_init_remains_usable_when_converter_fails(self, tmp_path):
        """Claude init should succeed even without install_ai_skills."""
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "fail-proj"

        result = runner.invoke(
            app,
            ["init", str(target), "--ai", "claude", "--script", "sh", "--no-git", "--ignore-agent-tools"],
        )

        assert result.exit_code == 0
        assert (target / ".claude" / "skills" / "sp-specify" / "SKILL.md").exists()

    def test_claude_hooks_render_skill_invocation(self, tmp_path):
        from specify_cli.extensions import HookExecutor

        project = tmp_path / "claude-hooks"
        project.mkdir()
        init_options = project / ".specify" / "init-options.json"
        init_options.parent.mkdir(parents=True, exist_ok=True)
        init_options.write_text(json.dumps({"ai": "claude", "ai_skills": True}))

        hook_executor = HookExecutor(project)
        message = hook_executor.format_hook_message(
            "before_plan",
            [
                {
                    "extension": "test-ext",
                    "command": "sp.plan",
                    "optional": False,
                }
            ],
        )

        assert "Executing: `/sp-plan`" in message
        assert "EXECUTE_COMMAND: sp.plan" in message
        assert "EXECUTE_COMMAND_INVOCATION: /sp-plan" in message

    def test_claude_preset_creates_new_skill_without_commands_dir(self, tmp_path):
        from specify_cli import save_init_options
        from specify_cli.presets import PresetManager

        project = tmp_path / "claude-preset-skill"
        project.mkdir()
        save_init_options(project, {"ai": "claude", "ai_skills": True, "script": "sh"})

        skills_dir = project / ".claude" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        preset_dir = tmp_path / "claude-skill-command"
        preset_dir.mkdir()
        (preset_dir / "commands").mkdir()
        (preset_dir / "commands" / "sp.research.md").write_text(
            "---\n"
            "description: Research workflow\n"
            "---\n\n"
            "preset:claude-skill-command\n"
        )
        manifest_data = {
            "schema_version": "1.0",
            "preset": {
                "id": "claude-skill-command",
                "name": "Claude Skill Command",
                "version": "1.0.0",
                "description": "Test",
            },
            "requires": {"speckit_version": ">=0.1.0"},
            "provides": {
                "templates": [
                    {
                        "type": "command",
                        "name": "sp.research",
                        "file": "commands/sp.research.md",
                    }
                ]
            },
        }
        with open(preset_dir / "preset.yml", "w") as f:
            yaml.dump(manifest_data, f)

        manager = PresetManager(project)
        manager.install_from_directory(preset_dir, "0.1.5")

        skill_file = skills_dir / "sp-research" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text(encoding="utf-8")
        assert "preset:claude-skill-command" in content
        assert "name: sp-research" in content
        assert "user-invocable: true" in content
        assert "disable-model-invocation: true" in content

        metadata = manager.registry.get("claude-skill-command")
        assert "sp-research" in metadata.get("registered_skills", [])


class TestClaudeArgumentHints:
    """Verify that argument-hint frontmatter is injected for Claude skills."""

    @staticmethod
    def _explicit_skill_files(created):
        return [
            f
            for f in created
            if f.name == "SKILL.md" and f.parent.name.startswith("sp-")
        ]

    def test_all_skills_have_hints(self, tmp_path):
        """Every explicit Claude workflow skill must contain an argument-hint line."""
        i = get_integration("claude")
        m = IntegrationManifest("claude", tmp_path)
        created = i.setup(tmp_path, m, script_type="sh")
        skill_files = self._explicit_skill_files(created)
        assert len(skill_files) > 0
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            assert "argument-hint:" in content, (
                f"{f.parent.name}/SKILL.md is missing argument-hint frontmatter"
            )

    def test_hints_match_expected_values(self, tmp_path):
        """Each skill's argument-hint must match the expected text."""
        i = get_integration("claude")
        m = IntegrationManifest("claude", tmp_path)
        created = i.setup(tmp_path, m, script_type="sh")
        skill_files = self._explicit_skill_files(created)
        for f in skill_files:
            stem = f.parent.name
            if stem.startswith("sp-"):
                stem = stem[len("sp-"):]
            expected_hint = ARGUMENT_HINTS.get(stem)
            assert expected_hint is not None, (
                f"No expected hint defined for skill '{stem}'"
            )
            content = f.read_text(encoding="utf-8")
            assert f'argument-hint: "{expected_hint}"' in content, (
                f"{f.parent.name}/SKILL.md: expected hint '{expected_hint}' not found"
            )

    def test_hint_is_inside_frontmatter(self, tmp_path):
        """argument-hint must appear between the --- delimiters, not in the body."""
        i = get_integration("claude")
        m = IntegrationManifest("claude", tmp_path)
        created = i.setup(tmp_path, m, script_type="sh")
        skill_files = self._explicit_skill_files(created)
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            assert len(parts) >= 3, f"No frontmatter in {f.parent.name}/SKILL.md"
            frontmatter = parts[1]
            body = parts[2]
            assert "argument-hint:" in frontmatter, (
                f"{f.parent.name}/SKILL.md: argument-hint not in frontmatter section"
            )
            assert "argument-hint:" not in body, (
                f"{f.parent.name}/SKILL.md: argument-hint leaked into body"
            )

    def test_hint_appears_after_description(self, tmp_path):
        """argument-hint must immediately follow the description line."""
        i = get_integration("claude")
        m = IntegrationManifest("claude", tmp_path)
        created = i.setup(tmp_path, m, script_type="sh")
        skill_files = self._explicit_skill_files(created)
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            found_description = False
            for idx, line in enumerate(lines):
                if line.startswith("description:"):
                    found_description = True
                    assert idx + 1 < len(lines), (
                        f"{f.parent.name}/SKILL.md: description is last line"
                    )
                    assert lines[idx + 1].startswith("argument-hint:"), (
                        f"{f.parent.name}/SKILL.md: argument-hint does not follow description"
                    )
                    break
            assert found_description, (
                f"{f.parent.name}/SKILL.md: no description: line found in output"
            )

    def test_inject_argument_hint_only_in_frontmatter(self):
        """inject_argument_hint must not modify description: lines in the body."""
        from specify_cli.integrations.claude import ClaudeIntegration

        content = (
            "---\n"
            "description: My command\n"
            "---\n"
            "\n"
            "description: this is body text\n"
        )
        result = ClaudeIntegration.inject_argument_hint(content, "Test hint")
        lines = result.splitlines()
        hint_count = sum(1 for ln in lines if ln.startswith("argument-hint:"))
        assert hint_count == 1, (
            f"Expected exactly 1 argument-hint line, found {hint_count}"
        )

    def test_inject_argument_hint_skips_if_already_present(self):
        """inject_argument_hint must not duplicate if argument-hint already exists."""
        from specify_cli.integrations.claude import ClaudeIntegration

        content = (
            "---\n"
            "description: My command\n"
            'argument-hint: "Existing hint"\n'
            "---\n"
            "\n"
            "Body text\n"
        )
        result = ClaudeIntegration.inject_argument_hint(content, "New hint")
        assert result == content, "Content should be unchanged when hint already exists"
        lines = result.splitlines()
        hint_count = sum(1 for ln in lines if ln.startswith("argument-hint:"))
        assert hint_count == 1


def test_claude_generated_runtime_facing_skills_include_native_subagent_contract(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-subagent-contract"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    skills_dir = target / ".claude" / "skills"
    for skill_name in ("sp-implement", "sp-debug", "sp-quick"):
        content = (skills_dir / skill_name / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "subagent dispatch contract" in content
        assert "delegation surface contract" in content
        assert "result contract" in content
        assert "result handoff path" in content
        assert "wait for every subagent's structured handoff" in content
        assert "do not treat an idle subagent as done work" in content
        assert "do not interrupt or shut down subagent work before the handoff has been written" in content
        assert "done_with_concerns" in content
        assert "needs_context" in content
        assert "workertaskresult" in content
        assert "spawn_agent" not in content
        assert "specify team" not in content
    implement_content = (skills_dir / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()
    debug_content = (skills_dir / "sp-debug" / "SKILL.md").read_text(encoding="utf-8").lower()
    quick_content = (skills_dir / "sp-quick" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "feature_dir/worker-results/<task-id>.json" in implement_content
    assert ".planning/debug/results/<session-slug>/<lane-id>.json" in debug_content
    assert ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json" in quick_content


def test_claude_generated_implement_skill_includes_shared_leader_gate(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-implement-leader-gate"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    content = (target / ".claude" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "/sp-implement-teams" not in content
    assert "## orchestration model" in content
    assert "leader and orchestrator" in content
    assert "not the concrete implementer" in content
    assert "autonomous blocker recovery" in content
    assert "delegation surface contract" in content
    assert "claude code subagent result contract" in content
    assert "dispatch `one-subagent` when one validated `workertaskpacket` is ready" in content
    assert "dispatch `parallel-subagents` when multiple validated packets have isolated write sets" in content
    assert "dispatch only from validated `workertaskpacket`" in content
    assert "## claude dispatch-first gate" not in content
    assert "attempt native subagent execution before leader-inline fallback" not in content


def test_claude_generated_sp_implement_description_prefers_subagent_dispatch(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-implement-subagent-description"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    content = (target / ".claude" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8")
    parts = content.split("---", 2)
    parsed = yaml.safe_load(parts[1])

    assert parsed["description"] == (
        "Execute the implementation plan by dispatching subagents and integrating their results"
    )


def test_claude_generated_sp_implement_teams_skill_uses_agent_teams_surface(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-implement-teams"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    skill_path = target / ".claude" / "skills" / "sp-implement-teams" / "SKILL.md"
    assert skill_path.exists()

    content = skill_path.read_text(encoding="utf-8")
    lower = content.lower()
    team_bootstrap_idx = content.find("## Team Bootstrap Gate")
    shared_contract_idx = content.find("## Shared Contract With `/sp-implement`")
    execution_contract_idx = content.find("## Execution Contract")

    assert team_bootstrap_idx != -1
    assert shared_contract_idx != -1
    assert execution_contract_idx != -1
    assert team_bootstrap_idx < shared_contract_idx < execution_contract_idx
    assert "the first non-prerequisite action is creating or resuming the claude agent team" in lower
    assert "do not read `plan.md`, `tasks.md` beyond the minimum existence/status check" in lower
    assert "do not run validation, edit files, or inspect broad implementation context before this gate passes" in lower
    assert "claude code agent teams" in lower
    assert "teamcreate" in lower
    assert "taskcreate" in lower
    assert "taskupdate" in lower
    assert "sendmessage" in lower
    assert "tasklist" in lower
    assert "taskget" in lower
    assert "teamdelete" in lower
    assert "~/.claude/teams/" in content
    assert "~/.claude/tasks/" in content
    assert "settings.json" in lower
    assert "claude_code_experimental_agent_teams" in lower
    assert "if the first `teamcreate` / agent teams call fails as though the feature is disabled" in lower
    assert "explicitly remind the user to enable agent teams in claude code settings or environment" in lower
    assert "hard prerequisite for `/sp-implement-teams`" in lower
    assert "executioncontextbundle" in lower or "execution context bundle" in lower
    assert "project-handbook.md" in lower
    assert ".specify/project-map/root/workflows.md" in lower
    assert ".specify/testing/TESTING_CONTRACT.md".lower() in lower
    assert ".specify/testing/TESTING_PLAYBOOK.md".lower() in lower
    assert "read-order" in lower or "read order" in lower
    assert "ack the context bundle before claiming work" in lower
    assert "sendmessage" in lower and "context_ack" in lower
    assert "create the full task set before wiring `blockedby` / `blocks` dependencies" in lower
    assert "write set and shared surfaces" in lower
    assert "explicit verification command or acceptance check" in lower
    assert "canonical result handoff path" in lower
    assert "completion protocol covering start, blocker, and final completion evidence" in lower
    assert "task_started" in lower
    assert "task_blocked" in lower
    assert "task_completed" in lower
    assert "supported_platforms: windows, linux" in lower
    assert "conditional compilation" in lower
    assert "inherit claude code's configured subagent model behavior" in lower
    assert "`claude_code_subagent_model`" in lower
    assert "do not derive teammate model from `anthropic_model`" in lower
    assert "do not ask the user for an explicit teammate model" in lower
    assert "do not require local `.claude/agents/<team-name>-<role>.md` teammate definitions solely to force a model choice" in lower
    assert "prompt-only specialization is acceptable" in lower
    assert "claude code's configured subagent model behavior" in lower
    assert "enters `idle` without consuming its first probe message" in lower
    assert "treat startup as failed rather than successful" in lower
    assert "ordinary `agent` tool" in lower
    assert "must not be used as a teammate substitute" in lower
    assert "if no native agent teams teammate launch surface is available" in lower
    assert "stop instead of falling back to ordinary subagents" in lower
    assert "agent teams teammate result contract" in lower
    assert "team wave protocol" in lower
    assert "implementation teammate" in lower
    assert "review teammate" in lower
    assert "verification teammate" in lower
    assert "interface_change" in lower
    assert "review_requested" in lower
    assert "verification_started" in lower
    assert "team_synthesis" in lower
    assert "check-prerequisites.sh --json --require-tasks --include-tasks" in lower
    assert "parse `feature_dir` and `available_docs` list" in lower
    assert "all paths must be absolute" in lower
    assert "minimal readiness probe message before task assignment" in lower
    assert "shared contract with `/sp-implement`" in lower
    assert "canonical implementation workflow" in lower
    assert "implement-tracker.md" in lower
    assert "workertaskpacket" in lower
    assert "execution_model" in lower
    assert "dispatch_shape" in lower
    assert "execution_surface" in lower
    assert "join point" in lower
    assert "worker-results" in lower
    assert "subagent result contract" not in lower
    assert "subagent dispatch contract" not in lower
    assert "result file handoff path" in lower
    assert "feature_dir/worker-results/<task-id>.json" in lower
    assert "core implementation complete" in lower
    assert "ready for integration testing" in lower
    assert "overall feature completion" in lower
    assert "e2e" in lower
    assert "polish" in lower
    assert "shutdown_response" in lower
    assert "accepted shutdown, not that it already left the team" in lower
    assert "if a team for the same feature slug is already active, reuse or resume it" in lower
    assert "do not create a second parallel team for the same feature" in lower
    assert "after each completed join point or ready batch, immediately re-read the shared task ledger" in lower
    assert "select the next ready batch and continue automatically" in lower
    assert "stop only when no ready work remains, a real blocker stops progress, or an explicit human approval gate is reached" in lower
    assert "planned validation tasks are still ready work" in lower
    assert "do not stop to ask whether validation should start" in lower
    assert "do not stop after a single completed batch just because the current assignee went idle" in lower
    assert "specify team" not in lower
    assert "sp.agent-teams.run" not in lower
    assert "specify extension add agent-teams" not in lower
    assert "tmux" not in lower


def test_claude_implement_teams_template_keeps_only_backend_specific_guidance():
    template = Path(
        "src/specify_cli/integrations/claude/templates/implement-teams.md"
    ).read_text(encoding="utf-8")
    lower = template.lower()

    assert "## Shared Contract With `/sp-implement`" not in template
    assert "scripts:" in template
    assert "--require-tasks --include-tasks" in template
    assert "Run `{SCRIPT}` from repo root and parse `FEATURE_DIR` and `AVAILABLE_DOCS` list." in template
    assert "## Team Bootstrap Gate" in template
    assert "the first non-prerequisite action is creating or resuming the Claude Agent Team" in template
    assert "Do not read `plan.md`, `tasks.md` beyond the minimum existence/status check" in template
    assert "Do not run validation, edit files, or inspect broad implementation context before this gate passes" in template
    assert "`claude_code_subagent_model`" in lower
    assert "do not derive teammate model from `anthropic_model`" in lower
    assert "prompt-only specialization is acceptable" in lower
    assert "ordinary `agent` tool" in lower
    assert "must not be used as a teammate substitute" in lower
    assert "team wave protocol" in lower
    assert "review teammate" in lower
    assert "claude_code_experimental_agent_teams" in lower
    assert "hard prerequisite" in lower
    assert "idle" in lower
    assert "shared completion contract is fully satisfied" in lower
    assert "reuse or resume" in lower
    assert "continue automatically" in lower
    assert "task_started" in lower
    assert "task_completed" in lower
    assert "shutdown_response" in lower


def test_claude_generated_skills_preserve_agent_required_marker_lines(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-agent-marker"
    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, result.output

    for skill_name in ("sp-fast", "sp-quick", "sp-map-scan", "sp-map-build", "sp-implement", "sp-specify", "sp-plan", "sp-tasks", "sp-debug"):
        content = (target / ".claude" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "[AGENT]" in content


def test_claude_question_driven_skills_prefer_ask_user_question_with_fallback(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-question-tool"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai claude failed: {result.output}"

    for skill_name in ("sp-specify", "sp-clarify", "sp-checklist", "sp-quick"):
        content = (target / ".claude" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "AskUserQuestion" in content
        assert "`question`" in content
        assert "`header`" in content
        assert "`multiSelect`" in content
        assert "fallback-only guidance" in lower
        assert "must use it" in lower
        assert "do not render the textual fallback block" in lower
        assert "do not self-authorize textual fallback" in lower
        assert "active question exactly once" in lower
        assert (
            "fall back to the" in lower
            or "plain-text confirmation question" in lower
            or "textual question format" in lower
            or "plain-text clarification" in lower
        )

    specify_content = (target / ".claude" / "skills" / "sp-specify" / "SKILL.md").read_text(encoding="utf-8")
    assert "If the runtime's native structured question tool is available for the current turn, you must use it." in specify_content
    assert "Treat the shared open question block structure below as fallback-only text format guidance" in specify_content
