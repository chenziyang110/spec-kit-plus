"""Tests for GeminiIntegration."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import _bootstrap_integration_context_file, app
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import render_hook_launcher_command
from .test_base import _assert_subagent_using_surfaces_have_discovery


def _load_gemini_hook_dispatch_module():
    import importlib.util

    repo_root = Path(__file__).resolve().parents[2]
    hook_path = repo_root / "src" / "specify_cli" / "integrations" / "gemini" / "hooks" / "gemini-hook-dispatch.py"
    spec = importlib.util.spec_from_file_location("gemini_hook_dispatch_for_tests", hook_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gemini_hook_infers_active_context_from_specify_features_root(tmp_path):
    module = _load_gemini_hook_dispatch_module()
    project_root = tmp_path / "gemini-hook-features-root"
    feature_dir = project_root / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: executing",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "next_action: continue execution",
            ]
        ),
        encoding="utf-8",
    )

    inferred = module._infer_active_context(project_root)

    assert inferred is not None
    assert inferred["command_name"] == "implement"
    assert inferred["feature_dir"] == str(feature_dir)


def test_gemini_hook_infers_map_update_active_context(tmp_path):
    module = _load_gemini_hook_dispatch_module()
    project_root = tmp_path / "gemini-hook-map-update"
    feature_dir = project_root / "specs" / "003-map-update"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Map Update",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-map-update`",
                "- status: `executing`",
            ]
        ),
        encoding="utf-8",
    )

    inferred = module._infer_active_context(project_root)

    assert inferred is not None
    assert inferred["command_name"] == "map-update"
    assert inferred["feature_dir"] == str(feature_dir)


def test_gemini_hook_treats_custom_complete_statuses_as_terminal(tmp_path):
    module = _load_gemini_hook_dispatch_module()
    project_root = tmp_path / "gemini-hook-terminal-compat"

    implement_dir = project_root / ".specify" / "features" / "001-implement"
    implement_dir.mkdir(parents=True, exist_ok=True)
    (implement_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: complete_with_cognition_review",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "next_action: Optional follow-up: run `$sp-map-update` if needed.",
            ]
        ),
        encoding="utf-8",
    )

    quick_dir = project_root / ".planning" / "quick" / "001-quick"
    quick_dir.mkdir(parents=True, exist_ok=True)
    (quick_dir / "STATUS.md").write_text(
        "---\nstatus: completed_with_partial_cognition_closeout\n---\n",
        encoding="utf-8",
    )

    workflow_dir = project_root / "specs" / "002-workflow"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-plan`",
                "- status: `completed_with_partial_cognition_closeout`",
                "",
                "## Next Action",
                "",
                "- Optional follow-up: manual review if needed.",
            ]
        ),
        encoding="utf-8",
    )

    assert module._infer_active_context(project_root) is None


def test_gemini_hook_suppresses_optional_compaction_resume_cue(tmp_path, monkeypatch):
    module = _load_gemini_hook_dispatch_module()
    context = {"command_name": "plan", "feature_dir": str(tmp_path / "specs" / "001-demo")}
    monkeypatch.setattr(module, "_infer_active_context", lambda _project_root: context)

    def fake_run_shared_hook(_project_root, args):
        if args[0] == "read-compaction":
            return {
                "status": "ok",
                "data": {
                    "artifact": {
                        "phase_state": {
                            "next_action": "Optional follow-up: run `$sp-map-update` if needed."
                        }
                    }
                },
            }
        return None

    monkeypatch.setattr(module, "_run_shared_hook", fake_run_shared_hook)

    assert module._compaction_resume_context(tmp_path, build=False, trigger="prompt") == ""


def test_gemini_hook_suppresses_optional_recovery_summary_next_action(tmp_path, monkeypatch):
    module = _load_gemini_hook_dispatch_module()
    context = {"command_name": "plan", "feature_dir": str(tmp_path / "specs" / "001-demo")}
    monkeypatch.setattr(module, "_infer_active_context", lambda _project_root: context)

    def fake_run_shared_hook(_project_root, args):
        if args[0] == "read-compaction":
            return {
                "status": "ok",
                "data": {
                    "artifact": {
                        "recovery_summary": {
                            "next_action": "Optional follow-up: run `$sp-map-update` if needed."
                        }
                    }
                },
            }
        return None

    monkeypatch.setattr(module, "_run_shared_hook", fake_run_shared_hook)

    assert module._compaction_resume_context(tmp_path, build=False, trigger="prompt") == ""


def test_gemini_integration_metadata():
    integration = get_integration("gemini")

    assert integration is not None
    assert integration.config["folder"] == ".gemini/"
    assert integration.config["commands_subdir"] == "commands"
    assert integration.context_file == "GEMINI.md"


def test_gemini_toml_install_contract_tracks_commands_scripts_and_context(tmp_path):
    integration = get_integration("gemini")
    manifest = IntegrationManifest("gemini", tmp_path)

    integration.setup(tmp_path, manifest, script_type="sh")
    _bootstrap_integration_context_file(tmp_path, integration, manifest)

    commands_dir = integration.commands_dest(tmp_path)
    command_files = sorted(commands_dir.glob("*.toml"))
    assert command_files

    parsed_commands = [tomllib.loads(path.read_text(encoding="utf-8")) for path in command_files]
    assert any(parsed.get("description") and parsed.get("prompt") for parsed in parsed_commands)

    plan_command = commands_dir / "sp.plan.toml"
    assert plan_command.exists()
    assert ".gemini/commands/sp.plan.toml" in manifest.files

    for rel_path in (
        ".specify/integrations/gemini/scripts/update-context.sh",
        ".specify/integrations/gemini/scripts/update-context.ps1",
        "GEMINI.md",
    ):
        assert (tmp_path / rel_path).exists()
        assert rel_path in manifest.files

    context_content = (tmp_path / "GEMINI.md").read_text(encoding="utf-8")
    assert "## Active Technologies" in context_content


def test_gemini_generated_map_workflows_include_native_agent_discovery(tmp_path):
    integration = get_integration("gemini")
    manifest = IntegrationManifest("gemini", tmp_path)
    integration.setup(tmp_path, manifest, script_type="sh")

    for name in ("map-scan", "map-build", "map-update"):
        content = (integration.commands_dest(tmp_path) / f"sp.{name}.toml").read_text(encoding="utf-8").lower()
        assert "map subagent capability discovery" in content
        assert "native subagent capability discovery" in content
        assert "@generalist" in content
        assert "do not record `subagent-blocked`" in content


def test_gemini_generated_subagent_workflows_include_capability_discovery(tmp_path):
    integration = get_integration("gemini")
    manifest = IntegrationManifest("gemini", tmp_path)
    integration.setup(tmp_path, manifest, script_type="sh")

    _assert_subagent_using_surfaces_have_discovery(integration.commands_dest(tmp_path).glob("sp.*.toml"))


def test_gemini_init_outputs_parseable_runtime_toml_commands(tmp_path):
    runner = CliRunner()
    target = tmp_path / "gemini-runtime-toml"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "gemini", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai gemini failed: {result.output}"

    for rel_path in (
        ".gemini/commands/sp.implement.toml",
        ".gemini/commands/sp.debug.toml",
        ".gemini/commands/sp.quick.toml",
    ):
        content = (target / rel_path).read_text(encoding="utf-8")
        parsed = tomllib.loads(content)

        assert parsed["description"]
        assert parsed["prompt"]
        assert "{SCRIPT}" not in content
        assert "__AGENT__" not in content
        assert "{ARGS}" not in content
        assert "\nscripts:\n" not in content
        assert "\nagent_scripts:\n" not in content


class TestGeminiIntegration:

    @staticmethod
    def _expected_launcher_command(route: str, *, script_type: str = "sh") -> str:
        return render_hook_launcher_command(
            "gemini",
            route,
            project_dir_env_var="GEMINI_PROJECT_DIR",
            script_type=script_type,
        )

    def test_setup_installs_hook_assets_and_settings_json(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        settings_path = tmp_path / ".gemini" / "settings.json"
        shared_launcher = tmp_path / ".specify" / "bin" / "specify-hook.py"

        assert hook_script.exists()
        assert settings_path.exists()
        assert shared_launcher.exists()

        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "hooks" in payload
        assert "SessionStart" in payload["hooks"]
        assert "BeforeAgent" in payload["hooks"]
        assert "BeforeTool" in payload["hooks"]

        commands = [
            hook["command"]
            for entries in payload["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict) and isinstance(hook.get("command"), str)
        ]
        assert any(command == self._expected_launcher_command("session-start", script_type="sh") for command in commands)
        assert any(command == self._expected_launcher_command("before-agent", script_type="sh") for command in commands)
        assert any(command == self._expected_launcher_command("before-tool", script_type="sh") for command in commands)

        assert ".gemini/hooks/gemini-hook-dispatch.py" in manifest.files
        assert ".gemini/settings.json" in manifest.files
        assert ".specify/bin/specify-hook.py" in manifest.files

    def test_setup_merges_existing_settings_json_without_overwriting_user_values(self, tmp_path):
        integration = get_integration("gemini")
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True, exist_ok=True)
        settings_path = gemini_dir / "settings.json"
        settings_path.write_text(
            json.dumps(
                {
                    "custom.setting": True,
                    "hooks": {
                        "BeforeTool": [
                            {
                                "matcher": "*",
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

        manifest = IntegrationManifest("gemini", tmp_path)
        created = integration.setup(tmp_path, manifest, script_type="sh")

        merged = json.loads(settings_path.read_text(encoding="utf-8"))
        assert merged["custom.setting"] is True
        assert any(
            hook["command"] == 'python "/tmp/user-hook.py"'
            for entry in merged["hooks"]["BeforeTool"]
            for hook in entry.get("hooks", [])
            if isinstance(hook, dict)
        )

        managed_before_tool_entries = [
            entry
            for entry in merged["hooks"]["BeforeTool"]
            if entry.get("matcher") == "*"
            and any(
                isinstance(hook, dict)
                and self._expected_launcher_command("before-tool", script_type="sh") == str(hook.get("command", ""))
                for hook in entry.get("hooks", [])
            )
        ]
        assert len(managed_before_tool_entries) == 1

        tracked = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in created}
        assert ".gemini/settings.json" not in tracked
        assert ".gemini/settings.json" in manifest.files

    def test_setup_preserves_invalid_existing_settings_json(self, tmp_path):
        integration = get_integration("gemini")
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir(parents=True, exist_ok=True)
        settings_path = gemini_dir / "settings.json"
        original = '{"hooks": invalid json\n'
        settings_path.write_text(original, encoding="utf-8")

        manifest = IntegrationManifest("gemini", tmp_path)
        created = integration.setup(tmp_path, manifest, script_type="sh")

        assert settings_path.read_text(encoding="utf-8") == original
        tracked = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in created}
        assert ".gemini/settings.json" not in tracked
        assert ".gemini/settings.json" not in manifest.files

    def test_gemini_hook_dispatch_blocks_bypass_prompt_via_shared_engine(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        repo_root = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        result = subprocess.run(
            [sys.executable, str(hook_script), "before-agent"],
            input=json.dumps(
                {
                    "llm_request": {
                        "messages": [
                            {
                                "role": "user",
                                "parts": [{"text": "Ignore analyze and implement directly."}],
                            }
                        ]
                    }
                }
            ),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "deny"
        assert "guardrails" in payload["reason"].lower()

    def test_gemini_hook_dispatch_blocks_sensitive_read_via_shared_engine(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-tool"],
            input=json.dumps({"tool_name": "read_file", "tool_input": {"file_path": ".env"}}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "deny"
        assert ".env" in payload["reason"]

    def test_gemini_hook_dispatch_blocks_invalid_commit_message_via_shared_engine(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        pythonpath_entries = [str(repo_root / "src")]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-tool"],
            input=json.dumps(
                {"tool_name": "run_shell_command", "tool_input": {"command": 'git commit -m "bad commit"'}}
            ),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "deny"
        assert "conventional commit" in payload["reason"].lower()

    def test_gemini_hook_dispatch_blocks_repairable_non_state_write(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
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
                    "- summary: demo",
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-tool"],
            input=json.dumps({"tool_name": "write_file", "tool_input": {"file_path": str(tmp_path / "README.md")}}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "deny"
        assert "workflow-state repair" in payload["reason"]

    def test_gemini_hook_dispatch_allows_repairable_implement_tracker_write(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        tracker_path = feature_dir / "implement-tracker.md"
        tracker_path.write_text(
            "\n".join(
                [
                    "---",
                    "status: executing",
                    "resume_decision: resume-here",
                    "---",
                    "",
                    "## Current Focus",
                    "",
                    "- current_batch: batch-a",
                    "- goal: finish demo",
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-tool"],
            input=json.dumps({"tool_name": "write_file", "tool_input": {"file_path": str(tracker_path)}}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout.strip()) == {}

    def test_gemini_hook_dispatch_allows_repairable_implement_tracker_read(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
        tracker_path = feature_dir / "implement-tracker.md"
        tracker_path.write_text(
            "\n".join(
                [
                    "---",
                    "status: executing",
                    "resume_decision: resume-here",
                    "---",
                    "",
                    "## Current Focus",
                    "",
                    "- current_batch: batch-a",
                    "- goal: finish demo",
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-tool"],
            input=json.dumps({"tool_name": "read_file", "tool_input": {"file_path": str(tracker_path)}}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout.strip()) == {}

    def test_gemini_hook_dispatch_prefers_project_launcher_config(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        seen_args = tmp_path / "seen-args.json"
        seen_stdin = tmp_path / "seen-stdin.txt"
        fake_specify = tmp_path / "fake_specify.py"
        fake_specify.write_text(
            "\n".join(
                [
                    "import json",
                    "import sys",
                    "from pathlib import Path",
                    "Path(sys.argv[1]).write_text(json.dumps(sys.argv[3:]), encoding='utf-8')",
                    "Path(sys.argv[2]).write_text(sys.stdin.read(), encoding='utf-8')",
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
                        "argv": [sys.executable, str(fake_specify), str(seen_args), str(seen_stdin)],
                    }
                }
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-agent"],
            input=json.dumps({"prompt": "continue"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "deny"
        assert payload["reason"] == "configured launcher used"
        assert json.loads(seen_args.read_text(encoding="utf-8")) == [
            "hook",
            "validate-prompt",
            "--prompt-stdin",
        ]
        assert seen_stdin.read_text(encoding="utf-8") == "continue"

    def test_gemini_shared_hook_timeout_fails_open(self, tmp_path, monkeypatch):
        module = _load_gemini_hook_dispatch_module()
        monkeypatch.setattr(
            module,
            "_shared_hook_commands",
            lambda _project_root, _args: [[sys.executable, "-c", "print('never')"]],
        )

        def fake_run(command, **kwargs):
            assert kwargs["input"] == "secret prompt"
            assert kwargs["timeout"] > 0
            raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

        monkeypatch.setattr(module.subprocess, "run", fake_run)

        result = module._invoke_shared_hook(
            tmp_path,
            ["validate-prompt", "--prompt-stdin"],
            stdin_text="secret prompt",
        )

        assert result.status == "timeout"
        assert result.payload is None
        assert result.timeout_seconds > 0
        assert module._run_shared_hook(
            tmp_path,
            ["validate-prompt", "--prompt-stdin"],
            stdin_text="secret prompt",
        ) is None

    def test_gemini_shared_hook_client_maps_blocked_payload(self, tmp_path, monkeypatch):
        module = _load_gemini_hook_dispatch_module()
        monkeypatch.setattr(
            module,
            "_shared_hook_commands",
            lambda _project_root, _args: [[sys.executable, "-c", "print('blocked')"]],
        )

        def fake_run(command, **kwargs):
            assert kwargs["input"] == "secret prompt"
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "status": "blocked",
                        "errors": ["configured launcher used"],
                        "warnings": [],
                        "actions": [],
                    }
                ),
                stderr="",
            )

        monkeypatch.setattr(module.subprocess, "run", fake_run)

        result = module._invoke_shared_hook(
            tmp_path,
            ["validate-prompt", "--prompt-stdin"],
            stdin_text="secret prompt",
        )

        assert result.status == "blocked"
        assert result.payload["status"] == "blocked"
        assert result.attempted_plan

    def test_gemini_shared_hook_client_redacts_invalid_output(self, tmp_path, monkeypatch):
        module = _load_gemini_hook_dispatch_module()
        monkeypatch.setattr(
            module,
            "_shared_hook_commands",
            lambda _project_root, _args: [[sys.executable, "-c", "print('secret prompt')"]],
        )

        def fake_run(command, **kwargs):
            assert kwargs["input"] == "secret prompt"
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="invalid output containing secret prompt",
                stderr="",
            )

        monkeypatch.setattr(module.subprocess, "run", fake_run)

        result = module._invoke_shared_hook(
            tmp_path,
            ["validate-prompt", "--prompt-stdin"],
            stdin_text="secret prompt",
        )

        assert result.status == "invalid-output"
        assert "secret prompt" not in result.stdout_preview
        assert "[REDACTED_PROMPT]" in result.stdout_preview
        assert module._run_shared_hook(
            tmp_path,
            ["validate-prompt", "--prompt-stdin"],
            stdin_text="secret prompt",
        ) is None

    def test_gemini_shared_hook_client_maps_unavailable(self, tmp_path, monkeypatch):
        module = _load_gemini_hook_dispatch_module()
        monkeypatch.setattr(
            module,
            "_shared_hook_commands",
            lambda _project_root, _args: [[sys.executable, "-m", "missing_specify_hook"]],
        )

        def fake_run(command, **kwargs):
            raise OSError("missing command")

        monkeypatch.setattr(module.subprocess, "run", fake_run)

        result = module._invoke_shared_hook(tmp_path, ["validate-prompt", "--prompt-stdin"])

        assert result.status == "unavailable"
        assert result.payload is None
        assert result.attempted_plans
        assert module._run_shared_hook(tmp_path, ["validate-prompt", "--prompt-stdin"]) is None

    def test_gemini_hook_dispatch_blocks_when_project_launcher_is_invalid(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)
        env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-agent"],
            input=json.dumps({"prompt": "continue"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "deny"
        assert "launcher" in payload["reason"].lower()

    def test_gemini_hook_dispatch_does_not_deny_repairable_before_agent(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
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
                    "- summary: demo",
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-agent"],
            input=json.dumps({"prompt": "continue"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["hookSpecificOutput"]["hookEventName"] == "BeforeAgent"
        assert "--autofix" in payload["hookSpecificOutput"]["additionalContext"]

    def test_gemini_hook_dispatch_adds_statusline_context_on_session_start(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
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
        assert "plan:design-only" in payload["systemMessage"]

    def test_gemini_hook_dispatch_reads_compaction_resume_context_on_session_start(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
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
        assert "plan:design-only" in payload["systemMessage"]
        assert "Resume cue: finish design review." in payload["systemMessage"]

    def test_gemini_hook_dispatch_blocks_active_workflow_policy_violation(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
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
                    "- summary: demo",
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-agent"],
            input=json.dumps({"prompt": "continue"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert "hookSpecificOutput" in payload
        assert payload["hookSpecificOutput"]["hookEventName"] == "BeforeAgent"

    def test_gemini_hook_before_agent_returns_redirect_for_phase_drift(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        compaction_path = tmp_path / ".specify" / "runtime" / "compaction" / "specify-001-demo" / "latest.json"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-agent"],
            input=json.dumps({"prompt": "start editing code now"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "deny"
        assert "/sp.plan" in payload["systemMessage"]
        assert not compaction_path.exists()

    def test_gemini_hook_dispatch_surfaces_learning_signal_on_before_agent(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
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
                    "- retry_attempts: 3",
                    "",
                    "## False Starts",
                    "",
                    "- assumed it was a tool problem before checking the workflow state",
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
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-agent"],
            input=json.dumps(
                {
                    "llm_request": {
                        "messages": [
                            {
                                "role": "user",
                                "parts": [{"text": "continue"}],
                            }
                        ]
                    }
                }
            ),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        additional_context = payload["hookSpecificOutput"]["additionalContext"]
        assert "learning pain score" in additional_context
        assert "record a learning review decision for `sp-implement`" in additional_context
        assert ".specify/memory/learnings/INDEX.md" in additional_context
        assert "init --here --force ..." not in additional_context

    def test_install_uninstall_roundtrip(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        created = integration.install(tmp_path, manifest)
        assert len(created) > 0
        manifest.save()

        removed, skipped = integration.uninstall(tmp_path, manifest)

        removed_rel = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in removed}
        assert ".gemini/hooks/README.md" in removed_rel
        assert ".gemini/hooks/gemini-hook-dispatch.py" in removed_rel
        assert ".gemini/settings.json" in removed_rel
        assert skipped == []


def test_gemini_runtime_commands_hard_gate_project_cognition_reads(tmp_path):
    runner = CliRunner()
    target = tmp_path / "gemini-project-cognition-gate"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "gemini", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai gemini failed: {result.output}"

    for rel in (
        ".gemini/commands/sp.implement.toml",
        ".gemini/commands/sp.debug.toml",
        ".gemini/commands/sp.quick.toml",
    ):
        content = (target / rel).read_text(encoding="utf-8").lower()
        assert "map-scan" in content
        assert "map-build" in content
        if "sp.implement" in rel:
            assert "current-task navigation repair" in content
            assert "only when a required ref is stale, missing, or contradicted by live code" in content
            assert "project-cognition query --query-plan" not in content
        elif "sp.debug" in rel:
            assert "crucial first step" in content
            assert "debug-handbook.md" in content
            assert "debug-workflow-contract" in content
        else:
            assert "crucial first step" in content
            assert "build-handbook.md" in content
            assert "build-workflow-contract" in content


def test_gemini_question_driven_commands_prefer_ask_user_with_fallback(tmp_path):
    runner = CliRunner()
    target = tmp_path / "gemini-question-tool"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "gemini", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai gemini failed: {result.output}"

    for rel in (
        ".gemini/commands/sp.specify.toml",
        ".gemini/commands/sp.clarify.toml",
        ".gemini/commands/sp.checklist.toml",
        ".gemini/commands/sp.quick.toml",
    ):
        content = (target / rel).read_text(encoding="utf-8")
        lower = content.lower()
        assert "ask_user" in content
        assert "`choice`, `yesno`, and `text`" in content
        assert "`header`" in content
        assert "`type`" in content
        assert "auto_default_recommendation" in content
        assert "must auto-resolve" in lower
        assert "do not invoke the native structured question tool" in lower
        assert "active question exactly once" in lower
        assert (
            "fall back to the" in lower
            or "existing plain-text" in lower
            or "plain-text confirmation question" in lower
            or "textual question format" in lower
            or "plain-text clarification" in lower
        )
