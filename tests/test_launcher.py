import json
import os
import stat

import specify_cli
from specify_cli.launcher import (
    HookRuntimeSpec,
    diagnose_project_runtime_compatibility,
    install_shared_hook_launcher_assets,
    SpecifyLauncherSpec,
    load_project_specify_launcher,
    project_specify_subcommand,
    render_hook_launcher_command,
    render_project_launcher_placeholders,
    resolve_hook_runtime_spec,
    write_project_specify_launcher_config,
)


def test_write_project_specify_launcher_config_preserves_existing_keys(tmp_path):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"notify": "legacy notify"}), encoding="utf-8")

    written = write_project_specify_launcher_config(
        tmp_path,
        SpecifyLauncherSpec(
            command="uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify",
            argv=(
                "uvx",
                "--from",
                "git+https://github.com/chenziyang110/spec-kit-plus.git",
                "specify",
            ),
        ),
    )

    assert written == config_path
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["notify"] == "legacy notify"
    assert payload["specify_launcher"]["argv"] == [
        "uvx",
        "--from",
        "git+https://github.com/chenziyang110/spec-kit-plus.git",
        "specify",
    ]


def test_write_project_specify_launcher_config_skips_unbound_path_launcher(tmp_path):
    written = write_project_specify_launcher_config(
        tmp_path,
        SpecifyLauncherSpec(command="specify", argv=("specify",)),
    )

    assert written is None
    assert not (tmp_path / ".specify" / "config.json").exists()


def test_shared_infra_writes_source_bound_launcher_config(monkeypatch, tmp_path):
    launcher = SpecifyLauncherSpec(
        command="uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git@abc123 specify",
        argv=(
            "uvx",
            "--from",
            "git+https://github.com/chenziyang110/spec-kit-plus.git@abc123",
            "specify",
        ),
    )
    monkeypatch.setattr("specify_cli.launcher.resolve_specify_launcher_spec", lambda: launcher)

    assert specify_cli._install_shared_infra(tmp_path, "ps")

    payload = json.loads((tmp_path / ".specify" / "config.json").read_text(encoding="utf-8"))
    assert payload["specify_launcher"]["argv"] == list(launcher.argv)


def test_load_project_specify_launcher_reads_valid_config(tmp_path):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify",
                    "argv": [
                        "uvx",
                        "--from",
                        "git+https://github.com/chenziyang110/spec-kit-plus.git",
                        "specify",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    launcher = load_project_specify_launcher(tmp_path)

    assert launcher == SpecifyLauncherSpec(
        command="uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify",
        argv=(
            "uvx",
            "--from",
            "git+https://github.com/chenziyang110/spec-kit-plus.git",
            "specify",
        ),
    )


def test_project_specify_subcommand_uses_project_launcher_config(tmp_path):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify",
                    "argv": [
                        "uvx",
                        "--from",
                        "git+https://github.com/chenziyang110/spec-kit-plus.git",
                        "specify",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    spec = project_specify_subcommand(
        tmp_path,
        ["hook", "validate-state", "--command", "plan"],
    )

    assert spec is not None
    assert spec.argv == (
        "uvx",
        "--from",
        "git+https://github.com/chenziyang110/spec-kit-plus.git",
        "specify",
        "hook",
        "validate-state",
        "--command",
        "plan",
    )
    assert spec.command.endswith("specify hook validate-state --command plan")


def test_render_project_launcher_placeholders_expands_cli_and_subcommand(tmp_path):
    config_dir = tmp_path / ".specify"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify",
                    "argv": [
                        "uvx",
                        "--from",
                        "git+https://github.com/chenziyang110/spec-kit-plus.git",
                        "specify",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    rendered = render_project_launcher_placeholders(
        tmp_path,
        'Run `{{specify-cli}}` and then `{{specify-subcmd:hook validate-state --command plan}}`.',
    )

    assert "`uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify`" in rendered
    assert (
        "`uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify hook validate-state --command plan`"
        in rendered
    )


def test_diagnose_project_runtime_compatibility_reports_broken_launcher(tmp_path):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
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

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(issue["code"] == "broken-project-launcher" for issue in issues)


def test_diagnose_project_runtime_compatibility_reports_stale_powershell_resolver(tmp_path):
    common_path = tmp_path / ".specify" / "scripts" / "powershell" / "common.ps1"
    common_path.parent.mkdir(parents=True)
    common_path.write_text(
        "function Get-FeaturePathsEnv { $featureDir = Get-FeatureDir -RepoRoot $repoRoot -Branch $currentBranch }\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(issue["code"] == "stale-powershell-feature-resolver" for issue in issues)


def test_diagnose_project_runtime_compatibility_reports_stale_claude_windows_hook_commands(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'python "$CLAUDE_PROJECT_DIR"/.claude/hooks/claude-hook-dispatch.py session-start',
                                }
                            ]
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(issue["code"] == "stale-claude-windows-hook-command" for issue in issues)


def test_diagnose_project_runtime_compatibility_reports_stale_direct_hook_launcher_command(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/claude-hook-dispatch.py session-start',
                                }
                            ]
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(issue["code"] == "stale-direct-hook-launcher-command" for issue in issues)


def test_resolve_hook_runtime_spec_prefers_runtime_command_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SPECIFY_HOOK_RUNTIME_COMMAND", "python-custom -X utf8")

    resolved = resolve_hook_runtime_spec(tmp_path)

    assert resolved == HookRuntimeSpec(
        command="python-custom -X utf8",
        argv=("python-custom", "-X", "utf8"),
        source="env:SPECIFY_HOOK_RUNTIME_COMMAND",
    )


def test_resolve_hook_runtime_spec_prefers_project_venv_python(tmp_path):
    python_bin = tmp_path / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python_bin.parent.mkdir(parents=True)
    python_bin.write_text("", encoding="utf-8")

    resolved = resolve_hook_runtime_spec(tmp_path)

    assert resolved is not None
    assert resolved.argv == (str(python_bin),)
    assert resolved.source == "project-venv"


def test_render_hook_launcher_command_targets_env_scoped_shared_launcher_posix(monkeypatch):
    monkeypatch.setattr(os, "name", "posix", raising=False)

    command = render_hook_launcher_command(
        "claude",
        "session-start",
        project_dir_env_var="CLAUDE_PROJECT_DIR",
    )

    assert command == '"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook claude session-start'


def test_render_hook_launcher_command_targets_env_scoped_shared_launcher_windows(monkeypatch):
    monkeypatch.setattr(os, "name", "nt", raising=False)

    command = render_hook_launcher_command(
        "gemini",
        "before-tool",
        project_dir_env_var="GEMINI_PROJECT_DIR",
    )

    assert command == '"$env:GEMINI_PROJECT_DIR"/.specify/bin/specify-hook.cmd gemini before-tool'


def test_render_hook_launcher_command_can_target_powershell_surface_from_posix(monkeypatch):
    monkeypatch.setattr(os, "name", "posix", raising=False)

    command = render_hook_launcher_command(
        "claude",
        "session-start",
        project_dir_env_var="CLAUDE_PROJECT_DIR",
        script_type="ps",
    )

    assert command == '"$env:CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook.cmd claude session-start'


def test_install_shared_hook_launcher_assets_writes_all_runtime_files(tmp_path):
    created = install_shared_hook_launcher_assets(tmp_path)
    relpaths = sorted(path.relative_to(tmp_path).as_posix() for path in created)

    assert relpaths == [
        ".specify/bin/specify-hook",
        ".specify/bin/specify-hook.cmd",
        ".specify/bin/specify-hook.py",
    ]

    posix_launcher = tmp_path / ".specify" / "bin" / "specify-hook"
    assert posix_launcher.exists()
    if os.name != "nt":
        assert posix_launcher.stat().st_mode & stat.S_IXUSR
