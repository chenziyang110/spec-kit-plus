import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import pytest

import specify_cli
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import (
    bind_project_launcher_payload,
    HookRuntimeSpec,
    SPECIFY_PROJECT_LAUNCHER_POSIX,
    SPECIFY_PROJECT_LAUNCHER_WINDOWS,
    SPECIFY_RUNTIME_ID,
    current_environment_specify_launcher_spec,
    diagnose_project_runtime_compatibility,
    install_shared_hook_launcher_assets,
    SpecifyLauncherSpec,
    load_project_specify_launcher,
    project_specify_subcommand,
    rebind_unbound_specify_runtime_cognition_calls,
    rebind_source_bound_specify_launchers,
    rebind_unbound_specify_runtime_calls,
    render_claude_hook_launcher,
    render_hook_launcher_command,
    render_command,
    render_project_launcher_placeholders,
    resolve_specify_launcher_spec,
    resolve_hook_runtime_spec,
    resolve_runtime_launcher_argv,
    runtime_launcher_is_compatible,
    write_project_specify_launcher_config,
)
from specify_cli import launcher as launcher_module

TEST_SPECIFY_COMMIT = "a" * 40
TEST_SPECIFY_SOURCE = (
    "git+https://github.com/chenziyang110/spec-kit-plus.git@"
    f"{TEST_SPECIFY_COMMIT}"
)
TEST_SPECIFY_COMMAND = f"uvx --from {TEST_SPECIFY_SOURCE} specify"
TEST_UPDATED_SPECIFY_SOURCE = (
    "git+https://github.com/chenziyang110/spec-kit-plus.git@" + "b" * 40
)


def _write_pinned_launcher_config(project_root):
    pinned_command = TEST_SPECIFY_COMMAND
    config_path = project_root / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": pinned_command,
                    "argv": [
                        "uvx",
                        "--from",
                        TEST_SPECIFY_SOURCE,
                        "specify",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    return pinned_command


def test_agent_payload_argv_and_derived_commands_bind_from_nested_cwd(tmp_path):
    project = tmp_path / "project 项目 & $literal"
    nested = project / "nested" / "work"
    nested.mkdir(parents=True)
    _write_pinned_launcher_config(project)
    feature = project / ".specify" / "features" / "001 space 项目&$"
    original_argv = [
        "specify",
        "workflow",
        "transition",
        "--feature-dir",
        str(feature),
        "--to",
        "accept",
    ]
    original_command = render_command(tuple(original_argv))
    payload = {
        "next_argv": original_argv,
        "resume": {
            "argv": list(original_argv),
            "command": original_command,
            "instruction": f"Run the exact resume command: {original_command}",
        },
        "metadata": {"command": ["specify", "workflow", "transition"]},
    }

    bound = bind_project_launcher_payload(payload, nested)

    launcher = load_project_specify_launcher(project)
    assert launcher is not None
    expected_argv = [*launcher.argv, *original_argv[1:]]
    expected_command = render_command(tuple(expected_argv))
    assert bound["next_argv"] == expected_argv
    assert bound["resume"]["argv"] == expected_argv
    assert bound["resume"]["command"] == expected_command
    assert bound["resume"]["instruction"] == (
        f"Run the exact resume command: {expected_command}"
    )
    assert bound["metadata"]["command"] == ["specify", "workflow", "transition"]


def test_agent_payload_binding_stops_at_an_unconfigured_nested_project(tmp_path):
    outer = tmp_path / "outer"
    inner = outer / "examples" / "inner"
    nested = inner / "src"
    nested.mkdir(parents=True)
    _write_pinned_launcher_config(outer)
    (inner / ".specify").mkdir()
    payload = {"next_argv": ["specify", "workflow", "show"]}

    bound = bind_project_launcher_payload(payload, nested)

    assert bound == payload


def test_write_project_specify_launcher_config_preserves_existing_keys(tmp_path):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"notify": "legacy notify"}), encoding="utf-8")

    written = write_project_specify_launcher_config(
        tmp_path,
        SpecifyLauncherSpec(
            command=TEST_SPECIFY_COMMAND,
            argv=(
                "uvx",
                "--from",
                TEST_SPECIFY_SOURCE,
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
        TEST_SPECIFY_SOURCE,
        "specify",
    ]


def test_write_project_specify_launcher_config_skips_unbound_path_launcher(tmp_path):
    written = write_project_specify_launcher_config(
        tmp_path,
        SpecifyLauncherSpec(command="specify", argv=("specify",)),
    )

    assert written is None
    assert not (tmp_path / ".specify" / "config.json").exists()


def test_non_explicit_write_preserves_foreign_launcher_record(monkeypatch, tmp_path):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    original = {
        "specify_launcher": {
            "command": "foreign-specify",
            "argv": ["foreign-specify"],
            "runtime_id": "another/vendor",
            "kind": "managed",
            "source": "foreign",
        }
    }
    config_path.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(
        "specify_cli.launcher.resolve_specify_launcher_spec",
        current_environment_specify_launcher_spec,
    )

    written = write_project_specify_launcher_config(tmp_path)

    assert written == config_path
    assert json.loads(config_path.read_text(encoding="utf-8")) == original
    assert not (tmp_path / ".specify" / "scripts" / "shared").exists()


def test_machine_binding_config_rebuilds_untrusted_command_and_argv(
    monkeypatch,
    tmp_path,
):
    state_dir = tmp_path / "bindings"
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", str(state_dir))
    binding_id = "a" * 32
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "pwsh -Command INJECTED_SECOND_COMMAND",
                    "argv": ["pwsh", "-Command", "INJECTED_SECOND_COMMAND"],
                    "source": "machine_binding",
                    "kind": "machine_binding",
                    "runtime_id": SPECIFY_RUNTIME_ID,
                    "binding_id": binding_id,
                }
            }
        ),
        encoding="utf-8",
    )

    launcher = load_project_specify_launcher(tmp_path)
    bound = bind_project_launcher_payload(
        {"next_argv": ["specify", "workflow", "show"]},
        tmp_path,
    )

    assert launcher == launcher_module.project_local_specify_launcher_spec(binding_id)
    assert "INJECTED" not in launcher.command
    assert "INJECTED" not in json.dumps(bound)
    assert bound["next_argv"] == [*launcher.argv, "workflow", "show"]


def test_source_bound_config_rebuilds_command_and_rejects_argv_injection(tmp_path):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    trusted_argv = [
        "uvx",
        "--from",
        TEST_SPECIFY_SOURCE,
        "specify",
    ]
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "pwsh -Command INJECTED_SECOND_COMMAND",
                    "argv": trusted_argv,
                    "source": "git",
                    "kind": "source_bound",
                    "runtime_id": SPECIFY_RUNTIME_ID,
                }
            }
        ),
        encoding="utf-8",
    )

    trusted = load_project_specify_launcher(tmp_path)
    assert trusted is not None
    assert trusted.argv == tuple(trusted_argv)
    assert trusted.command == render_command(tuple(trusted_argv))
    assert "INJECTED" not in trusted.command

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["specify_launcher"]["argv"] = [
        "pwsh",
        "-Command",
        "INJECTED_SECOND_COMMAND",
    ]
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_project_specify_launcher(tmp_path) is None


@pytest.mark.parametrize(
    "commit_id",
    ("a" * 7, "a" * 39, "a" * 41, "a" * 63),
)
def test_source_bound_config_rejects_non_full_commit_ids(
    tmp_path,
    commit_id,
):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    source = (
        "git+https://github.com/chenziyang110/spec-kit-plus.git@" + commit_id
    )
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": f"uvx --from {source} specify",
                    "argv": ["uvx", "--from", source, "specify"],
                    "source": "git",
                    "kind": "source_bound",
                    "runtime_id": SPECIFY_RUNTIME_ID,
                }
            }
        ),
        encoding="utf-8",
    )

    assert load_project_specify_launcher(tmp_path) is None


def test_runtime_config_rebuilds_untrusted_command(tmp_path):
    binary_name = "specify-runtime.exe" if os.name == "nt" else "specify-runtime"
    binary = tmp_path / binary_name
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "runtime_launcher": {
                    "command": "pwsh -Command INJECTED_SECOND_COMMAND",
                    "argv": [str(binary)],
                }
            }
        ),
        encoding="utf-8",
    )

    launcher = launcher_module.load_runtime_launcher(tmp_path)

    assert launcher is not None
    assert launcher.argv == (str(binary),)
    assert launcher.command == render_command((str(binary),))
    assert "INJECTED" not in launcher.command


def test_resolve_specify_launcher_binds_normal_install_to_current_interpreter(
    monkeypatch,
):
    class _InstalledDistribution:
        @staticmethod
        def read_text(filename):
            assert filename == "direct_url.json"
            return None

    monkeypatch.setattr(
        "specify_cli.launcher.importlib_metadata.distribution",
        lambda name: _InstalledDistribution(),
    )
    monkeypatch.setattr(
        "specify_cli.launcher.sys.executable",
        "C:/current-specify-env/python.exe",
    )

    launcher = resolve_specify_launcher_spec()

    assert launcher.argv == (
        "C:/current-specify-env/python.exe",
        "-m",
        "specify_cli",
    )
    assert "specify" not in launcher.argv[:1]


def test_resolve_specify_launcher_never_persists_authenticated_direct_url(
    monkeypatch,
):
    secret = "REVIEW_SECRET_DO_NOT_PERSIST"

    class _InstalledDistribution:
        @staticmethod
        def read_text(filename):
            assert filename == "direct_url.json"
            return json.dumps(
                {
                    "url": f"https://oauth2:{secret}@example.invalid/spec-kit-plus.git",
                    "vcs_info": {"vcs": "git", "commit_id": "abc123"},
                }
            )

    monkeypatch.setattr(
        "specify_cli.launcher.importlib_metadata.distribution",
        lambda name: _InstalledDistribution(),
    )
    monkeypatch.setattr(
        "specify_cli.launcher.sys.executable",
        "C:/current-specify-env/python.exe",
    )
    monkeypatch.setattr("specify_cli.launcher.shutil.which", lambda name: "C:/uvx.exe")

    launcher = resolve_specify_launcher_spec()

    assert launcher.kind == "local_environment"
    assert secret not in launcher.command
    assert all(secret not in item for item in launcher.argv)


@pytest.mark.parametrize(
    ("url", "commit_id"),
    (
        ("https://example.invalid/spec-kit-plus&calc.git", "a" * 40),
        ("https://[malformed/spec-kit-plus.git", "a" * 40),
        ("https://example.invalid/spec-kit-plus.git", "abc123&calc"),
        ("https://example.invalid/spec-kit-plus.git?token=secret", "a" * 40),
    ),
)
def test_resolve_specify_launcher_rejects_unsafe_source_metadata(
    monkeypatch,
    url,
    commit_id,
):
    class _InstalledDistribution:
        @staticmethod
        def read_text(filename):
            assert filename == "direct_url.json"
            return json.dumps(
                {
                    "url": url,
                    "vcs_info": {"vcs": "git", "commit_id": commit_id},
                }
            )

    monkeypatch.setattr(
        "specify_cli.launcher.importlib_metadata.distribution",
        lambda name: _InstalledDistribution(),
    )
    monkeypatch.setattr("specify_cli.launcher.shutil.which", lambda name: "C:/uvx.exe")

    launcher = resolve_specify_launcher_spec()

    assert launcher.kind == "local_environment"
    assert "uvx" not in launcher.argv


def test_resolve_specify_launcher_accepts_clean_commit_pinned_source(monkeypatch):
    commit_id = "a" * 40

    class _InstalledDistribution:
        @staticmethod
        def read_text(filename):
            assert filename == "direct_url.json"
            return json.dumps(
                {
                    "url": "https://github.com/chenziyang110/spec-kit-plus.git",
                    "vcs_info": {"vcs": "git", "commit_id": commit_id},
                }
            )

    monkeypatch.setattr(
        "specify_cli.launcher.importlib_metadata.distribution",
        lambda name: _InstalledDistribution(),
    )
    monkeypatch.setattr("specify_cli.launcher.shutil.which", lambda name: "C:/uvx.exe")

    launcher = resolve_specify_launcher_spec()

    assert launcher.kind == "source_bound"
    assert launcher.argv == (
        "uvx",
        "--from",
        f"git+https://github.com/chenziyang110/spec-kit-plus.git@{commit_id}",
        "specify",
    )


def test_normal_install_persists_portable_wrapper_and_local_binding(
    monkeypatch,
    tmp_path,
):
    project = tmp_path / "project"
    state_dir = tmp_path / "local bindings 项目"
    project.mkdir()
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", str(state_dir))
    local_launcher = current_environment_specify_launcher_spec()

    written = write_project_specify_launcher_config(project, local_launcher)

    assert written == project / ".specify" / "config.json"
    config_text = written.read_text(encoding="utf-8")
    config = json.loads(config_text)
    binding_id = config["specify_launcher"]["binding_id"]
    persisted_argv = config["specify_launcher"]["argv"]
    if os.name == "nt":
        assert persisted_argv[1:7] == [
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
        ]
        assert Path(persisted_argv[0]).name.lower() == "powershell.exe"
        assert Path(persisted_argv[-2]) == state_dir / "dispatch.ps1"
        assert persisted_argv[-1] == binding_id
        wrapper_relative = SPECIFY_PROJECT_LAUNCHER_WINDOWS
    else:
        assert persisted_argv == [str(state_dir / "dispatch"), binding_id]
        wrapper_relative = SPECIFY_PROJECT_LAUNCHER_POSIX
    assert sys.executable not in config_text
    assert config["specify_launcher"]["runtime_id"] == SPECIFY_RUNTIME_ID
    wrapper = project / wrapper_relative
    assert wrapper.is_file()
    wrapper_text = wrapper.read_text(encoding="utf-8")
    assert "integration repair" in wrapper_text
    rendered = render_project_launcher_placeholders(
        project,
        "Run `{{specify-subcmd:learning start --command ask --format json}}`.",
    )
    assert f'{config["specify_launcher"]["command"]} learning start ' in rendered
    assert sys.executable not in rendered

    binding_dir = state_dir / binding_id
    binding_path = binding_dir / "binding.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    assert binding["runtime_id"] == SPECIFY_RUNTIME_ID
    assert Path(binding["entry_argv"][0]) == Path(os.path.abspath(sys.executable))
    expected_import_root = Path(launcher_module.__file__).resolve().parent.parent
    assert Path(binding["package_import_root"]) == expected_import_root
    assert len(binding["package_init_sha256"]) == 64
    assert len(binding["package_launcher_sha256"]) == 64

    execution_env = {
        **os.environ,
        "PATH": "",
        "SPECIFY_PROJECT_LAUNCHER_STATE_DIR": str(state_dir),
    }
    execution_env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [*persisted_argv, "--runtime-id"],
        cwd=project,
        env=execution_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == SPECIFY_RUNTIME_ID

    moved_project = tmp_path / "moved project 项目"
    shutil.move(project, moved_project)
    nested = moved_project / "nested" / "working-directory"
    nested.mkdir(parents=True)
    moved_result = subprocess.run(
        [*persisted_argv, "--runtime-id"],
        cwd=nested,
        env=execution_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    assert moved_result.returncode == 0, moved_result.stderr
    assert moved_result.stdout.strip() == SPECIFY_RUNTIME_ID

    shutil.rmtree(binding_dir)
    issue_codes = {
        issue["code"] for issue in diagnose_project_runtime_compatibility(moved_project)
    }
    assert "broken-project-launcher" in issue_codes
    missing_result = subprocess.run(
        [*persisted_argv, "--runtime-id"],
        cwd=moved_project,
        env=execution_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    assert missing_result.returncode == 2
    assert "specify_cli integration repair" in missing_result.stderr
    repair_command = render_command(
        (
            binding["entry_argv"][0],
            "-m",
            "specify_cli",
            "integration",
            "repair",
        )
    )
    assert repair_command in missing_result.stderr
    assert "git+..." not in missing_result.stderr
    assert "__SPECIFY_" not in missing_result.stderr


def test_failed_machine_probe_does_not_leave_project_half_installed(
    monkeypatch,
    tmp_path,
):
    project = tmp_path / "project"
    state_dir = tmp_path / "bindings"
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", str(state_dir))
    original_probe = launcher_module._machine_binding_probe
    probe_calls = 0

    def fail_once(binding_id):
        nonlocal probe_calls
        probe_calls += 1
        return False if probe_calls == 1 else original_probe(binding_id)

    monkeypatch.setattr(launcher_module, "_machine_binding_probe", fail_once)

    with pytest.raises(RuntimeError, match="project launcher and configuration were not changed"):
        write_project_specify_launcher_config(
            project,
            current_environment_specify_launcher_spec(),
        )

    wrapper = launcher_module._project_launcher_destination(project)
    assert not wrapper.exists()
    assert not (project / ".specify" / "config.json").exists()

    written = write_project_specify_launcher_config(
        project,
        current_environment_specify_launcher_spec(),
    )
    assert written is not None
    assert wrapper.is_file()
    assert load_project_specify_launcher(project) is not None


@pytest.mark.skipif(os.name == "nt", reason="POSIX venv interpreter symlink contract")
def test_machine_binding_preserves_symlinked_venv_interpreter(monkeypatch, tmp_path):
    interpreter = Path(sys.executable)
    if not interpreter.is_symlink():
        pytest.skip("the active Python interpreter is not a venv symlink")
    state_dir = tmp_path / "bindings"
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", str(state_dir))

    config_path = write_project_specify_launcher_config(
        tmp_path / "project",
        current_environment_specify_launcher_spec(),
    )

    assert config_path is not None
    config = json.loads(config_path.read_text(encoding="utf-8"))
    binding_path = state_dir / config["specify_launcher"]["binding_id"] / "binding.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    assert binding["entry_argv"][0] == os.path.abspath(str(interpreter))
    assert binding["entry_argv"][0] != str(interpreter.resolve())


def test_relative_binding_state_override_is_frozen_for_nested_cwd(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", "relative-bindings")
    project = tmp_path / "project"
    nested = project / "nested" / "cwd"
    nested.mkdir(parents=True)

    config_path = write_project_specify_launcher_config(
        project,
        current_environment_specify_launcher_spec(),
    )
    assert config_path is not None
    launcher = load_project_specify_launcher(project)
    assert launcher is not None
    dispatch = Path(launcher.argv[-2] if os.name == "nt" else launcher.argv[0])
    assert dispatch.is_absolute()
    assert dispatch.parent == (tmp_path / "relative-bindings").resolve()

    result = subprocess.run(
        [*launcher.argv, "--runtime-id"],
        cwd=nested,
        env={
            **os.environ,
            "SPECIFY_PROJECT_LAUNCHER_STATE_DIR": "different-relative-value",
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == SPECIFY_RUNTIME_ID


@pytest.mark.skipif(os.name != "nt", reason="PowerShell command rendering contract")
def test_windows_rendered_launcher_quotes_shell_metacharacters_in_state_path(
    monkeypatch,
    tmp_path,
):
    state_dir = tmp_path / "bindings&$literal"
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", str(state_dir))
    project = tmp_path / "project"

    config_path = write_project_specify_launcher_config(
        project,
        current_environment_specify_launcher_spec(),
    )
    assert config_path is not None
    launcher = load_project_specify_launcher(project)
    assert launcher is not None
    assert f"'{state_dir.resolve()}\\dispatch.ps1'" in launcher.command

    result = subprocess.run(
        [
            launcher_module._windows_powershell_executable(),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"{launcher.command} --runtime-id",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == SPECIFY_RUNTIME_ID


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell forwarding contract")
def test_windows_machine_binding_forwards_metacharacters_without_reparse(tmp_path):
    binding_id = "a" * 32
    state_dir = tmp_path / "bindings"
    binding_dir = state_dir / binding_id
    binding_dir.mkdir(parents=True)
    capture = binding_dir / "capture.py"
    capture.write_text(
        "import json, sys\nprint(json.dumps(sys.argv[1:], ensure_ascii=False))\n",
        encoding="utf-8",
    )
    invoke = binding_dir / "invoke.ps1"
    invoke.write_text(
        launcher_module._binding_invoke_source(sys.executable, capture),
        encoding="utf-8",
    )
    dispatch = state_dir / "dispatch.ps1"
    dispatch.write_text(
        launcher_module._binding_dispatch_source(
            render_command(
                (sys.executable, "-m", "specify_cli", "integration", "repair")
            )
        ),
        encoding="utf-8",
    )
    secret_name = "SPX_REVIEW_SECRET"
    literal_secret = f"%{secret_name}%"
    forwarded = (literal_secret, "safe&ver", "space value", "项目")
    env = {
        **os.environ,
        secret_name: "EXPANDED & Write-Output SECOND_COMMAND_RAN",
        "SPECIFY_PROJECT_LAUNCHER_STATE_DIR": str(state_dir),
    }

    result = subprocess.run(
        [
            launcher_module._windows_powershell_executable(),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(dispatch),
            binding_id,
            *forwarded,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == list(forwarded)
    assert "SECOND_COMMAND_RAN" not in result.stdout


def test_posix_binding_dispatch_uses_only_shell_builtins_for_its_own_path(
    monkeypatch,
):
    monkeypatch.setattr(launcher_module.os, "name", "posix")

    source = launcher_module._binding_dispatch_source(
        "python -m specify_cli integration repair"
    )

    assert "dirname" not in source
    assert 'script_dir=${script_path%/*}' in source
    assert 'state_root=$(CDPATH= cd "$script_dir" && pwd -P)' in source


def test_normal_init_preserves_modified_project_launcher(monkeypatch, tmp_path):
    state_dir = tmp_path / "bindings"
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", str(state_dir))
    write_project_specify_launcher_config(tmp_path, current_environment_specify_launcher_spec())
    launcher = load_project_specify_launcher(tmp_path)
    assert launcher is not None
    wrapper_relative = (
        SPECIFY_PROJECT_LAUNCHER_WINDOWS
        if os.name == "nt"
        else SPECIFY_PROJECT_LAUNCHER_POSIX
    )
    wrapper = tmp_path / wrapper_relative
    wrapper.write_text("user modification\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="preserved"):
        write_project_specify_launcher_config(
            tmp_path,
            current_environment_specify_launcher_spec(),
        )

    assert wrapper.read_text(encoding="utf-8") == "user modification\n"
    assert load_project_specify_launcher(tmp_path) == launcher


def test_equal_content_project_launcher_symlink_is_rejected(monkeypatch, tmp_path):
    state_dir = tmp_path / "bindings"
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", str(state_dir))
    write_project_specify_launcher_config(
        tmp_path,
        current_environment_specify_launcher_spec(),
    )
    launcher = load_project_specify_launcher(tmp_path)
    assert launcher is not None
    wrapper = launcher_module._project_launcher_destination(tmp_path)
    external = tmp_path.parent / f"{tmp_path.name}-external-launcher"
    external.write_text(wrapper.read_text(encoding="utf-8"), encoding="utf-8")
    wrapper.unlink()
    try:
        wrapper.symlink_to(external)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    assert not launcher_module.project_specify_launcher_is_available(
        tmp_path,
        launcher,
    )
    with pytest.raises(RuntimeError, match="cannot inspect existing project launcher"):
        write_project_specify_launcher_config(
            tmp_path,
            current_environment_specify_launcher_spec(),
        )
    assert external.read_text(encoding="utf-8") != ""


def test_machine_binding_identity_mismatch_fails_closed_with_recovery(
    monkeypatch,
    tmp_path,
):
    state_dir = tmp_path / "bindings"
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", str(state_dir))
    config_path = write_project_specify_launcher_config(
        tmp_path,
        current_environment_specify_launcher_spec(),
    )
    assert config_path is not None
    config = json.loads(config_path.read_text(encoding="utf-8"))
    binding_id = config["specify_launcher"]["binding_id"]
    entry = state_dir / binding_id / "binding-entry.py"
    content = entry.read_text(encoding="utf-8").replace(
        f"EXPECTED_RUNTIME_ID = {SPECIFY_RUNTIME_ID!r}",
        "EXPECTED_RUNTIME_ID = 'wrong/runtime'",
    )
    entry.write_text(content, encoding="utf-8")

    launcher = load_project_specify_launcher(tmp_path)
    assert launcher is not None
    assert any(
        issue["code"] == "broken-project-launcher"
        for issue in diagnose_project_runtime_compatibility(tmp_path)
    )
    result = subprocess.run(
        [*launcher.argv, "--runtime-id"],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": "",
            "SPECIFY_PROJECT_LAUNCHER_STATE_DIR": str(state_dir),
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    assert result.returncode == 2
    assert "incompatible" in result.stderr
    assert "specify_cli integration repair" in result.stderr
    binding = json.loads(
        (state_dir / binding_id / "binding.json").read_text(encoding="utf-8")
    )
    repair_command = render_command(
        (
            binding["entry_argv"][0],
            "-m",
            "specify_cli",
            "integration",
            "repair",
        )
    )
    assert repair_command in result.stderr
    assert "git+..." not in result.stderr


def test_machine_binding_probe_rejects_tampered_dispatch(monkeypatch, tmp_path):
    state_dir = tmp_path / "bindings"
    monkeypatch.setenv("SPECIFY_PROJECT_LAUNCHER_STATE_DIR", str(state_dir))
    config_path = write_project_specify_launcher_config(
        tmp_path,
        current_environment_specify_launcher_spec(),
    )
    assert config_path is not None
    launcher = load_project_specify_launcher(tmp_path)
    assert launcher is not None
    binding = json.loads(
        (state_dir / launcher.binding_id / "binding.json").read_text(encoding="utf-8")
    )
    invoke = Path(binding["invoke_path"])
    invoke.write_text(
        "Write-Output 'TAMPERED_DISPATCH'\n" if os.name == "nt" else "#!/bin/sh\necho TAMPERED_DISPATCH\n",
        encoding="utf-8",
    )

    assert not launcher_module.project_specify_launcher_is_available(
        tmp_path,
        launcher,
    )
    assert any(
        issue["code"] == "broken-project-launcher"
        for issue in diagnose_project_runtime_compatibility(tmp_path)
    )


def test_shared_infra_writes_source_bound_launcher_config(monkeypatch, tmp_path):
    launcher = SpecifyLauncherSpec(
        command=TEST_SPECIFY_COMMAND,
        argv=(
            "uvx",
            "--from",
            TEST_SPECIFY_SOURCE,
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
                    "command": TEST_SPECIFY_COMMAND,
                    "argv": [
                        "uvx",
                        "--from",
                        TEST_SPECIFY_SOURCE,
                        "specify",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    launcher = load_project_specify_launcher(tmp_path)

    assert launcher == SpecifyLauncherSpec(
        command=TEST_SPECIFY_COMMAND,
        argv=(
            "uvx",
            "--from",
            TEST_SPECIFY_SOURCE,
            "specify",
        ),
        source="git",
        kind="source_bound",
        runtime_id=SPECIFY_RUNTIME_ID,
    )


def test_project_specify_subcommand_uses_project_launcher_config(tmp_path):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": TEST_SPECIFY_COMMAND,
                    "argv": [
                        "uvx",
                        "--from",
                        TEST_SPECIFY_SOURCE,
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
        TEST_SPECIFY_SOURCE,
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
                    "command": TEST_SPECIFY_COMMAND,
                    "argv": [
                        "uvx",
                        "--from",
                        TEST_SPECIFY_SOURCE,
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

    assert f"`{TEST_SPECIFY_COMMAND}`" in rendered
    assert (
        f"`{TEST_SPECIFY_COMMAND} hook validate-state --command plan`"
        in rendered
    )


def test_render_project_launcher_rebinds_bare_project_cognition_calls(tmp_path):
    config_dir = tmp_path / ".specify"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "runtime_launcher": {
                    "command": "C:/trusted/specify-runtime.exe",
                    "argv": ["C:/trusted/specify-runtime.exe"],
                }
            }
        ),
        encoding="utf-8",
    )

    rendered = render_project_launcher_placeholders(
        tmp_path,
        "Run `specify-runtime cognition generate-ignore --format json`.\n\n"
        "```bash\nspecify-runtime cognition scan-set --format json\n```\n",
    )

    assert "`C:/trusted/specify-runtime.exe cognition generate-ignore --format json`" in rendered
    assert "C:/trusted/specify-runtime.exe cognition scan-set --format json" in rendered
    assert "`specify-runtime cognition generate-ignore" not in rendered


def test_render_project_launcher_placeholders_without_project_launcher_avoids_bare_cognition_command(tmp_path):
    rendered = render_project_launcher_placeholders(
        tmp_path,
        'Run `{{specify-subcmd:specify-runtime cognition query --intent implement --query-plan "<query_plan_json>" --format json}}`.',
    )

    assert "specify specify-runtime cognition query" not in rendered
    assert "SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE:specify-runtime cognition" in rendered
    assert "specify-runtime cognition query --intent implement" in rendered
    assert "(requires specify-runtime" not in rendered


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
    broken = next(issue for issue in issues if issue["code"] == "broken-project-launcher")
    assert "..." not in broken["repair"]
    assert "<agent>" not in broken["repair"]


def test_diagnose_project_runtime_compatibility_reports_missing_cognition_launcher(
    tmp_path,
):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "python -m specify_cli",
                    "argv": ["python", "-m", "specify_cli"],
                }
            }
        ),
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    missing = next(
        issue
        for issue in issues
        if issue["code"] == "missing-specify-runtime-launcher"
    )
    assert "integration repair" in missing["repair"]
    assert "specify cognition" in missing["repair"]
    assert "do not" in missing["repair"].lower()


def test_runtime_launcher_resolves_project_relative_binary(
    monkeypatch,
    tmp_path,
):
    binary_name = "specify-runtime.exe" if os.name == "nt" else "specify-runtime"
    binary = tmp_path / ".specify" / "bin" / binary_name
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    if os.name != "nt":
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config_path = tmp_path / ".specify" / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime_launcher": {
                    "command": f".specify/bin/{binary_name}",
                    "argv": [f".specify/bin/{binary_name}"],
                }
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def compatible(argv, *, cwd=None):
        captured["argv"] = argv
        captured["cwd"] = cwd
        return True

    monkeypatch.setattr(
        "specify_cli.specify_runtime.launcher_supports_required_commands",
        compatible,
    )

    resolved = resolve_runtime_launcher_argv(tmp_path)

    assert resolved == (str(binary),)
    assert runtime_launcher_is_compatible(tmp_path) is True
    assert captured == {"argv": (str(binary),), "cwd": tmp_path}


def test_missing_relative_cognition_launcher_does_not_fall_back_to_path(
    monkeypatch,
    tmp_path,
):
    binary_name = "specify-runtime.exe" if os.name == "nt" else "specify-runtime"
    path_candidate = tmp_path / "malicious-path" / binary_name
    path_candidate.parent.mkdir()
    path_candidate.write_text("malicious", encoding="utf-8")
    if os.name != "nt":
        path_candidate.chmod(path_candidate.stat().st_mode | stat.S_IXUSR)
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "runtime_launcher": {
                    "command": binary_name,
                    "argv": [binary_name],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        launcher_module.shutil,
        "which",
        lambda _entry: str(path_candidate),
    )

    assert resolve_runtime_launcher_argv(tmp_path) is None
    assert any(
        issue["code"] == "broken-specify-runtime-launcher"
        for issue in diagnose_project_runtime_compatibility(tmp_path)
    )


def test_diagnose_project_runtime_compatibility_rejects_corrupt_runtime_binary(
    tmp_path,
):
    binary_name = "specify-runtime.exe" if os.name == "nt" else "specify-runtime"
    binary = tmp_path / ".specify" / "bin" / binary_name
    binary.parent.mkdir(parents=True)
    binary.write_text("not an executable", encoding="utf-8")
    if os.name != "nt":
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    (tmp_path / ".specify" / "config.json").write_text(
        json.dumps(
            {
                "runtime_launcher": {
                    "command": str(binary),
                    "argv": [str(binary)],
                }
            }
        ),
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(
        issue["code"] == "broken-specify-runtime-launcher" for issue in issues
    )


def test_diagnose_project_runtime_compatibility_reports_stale_generated_skill_launcher(tmp_path):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": f"uvx --from {TEST_UPDATED_SPECIFY_SOURCE} specify",
                    "argv": [
                        "uvx",
                        "--from",
                        TEST_UPDATED_SPECIFY_SOURCE,
                        "specify",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    skill_path = tmp_path / ".codex" / "skills" / "sp-debug" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "Run `uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git@old123 specify learning start --command debug --format json`.\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(issue["code"] == "stale-generated-specify-launcher" for issue in issues)
    stale = next(issue for issue in issues if issue["code"] == "stale-generated-specify-launcher")
    assert ".codex/skills/sp-debug/SKILL.md" in stale["summary"]
    assert "integration repair" in stale["repair"]


@pytest.mark.parametrize(
    ("skill_name", "runtime_call"),
    (
        ("spx-discussion", "specify discussion list --json"),
        ("spx-implement", "specify implement resume-audit --format json"),
    ),
)
def test_diagnose_project_runtime_compatibility_reports_bare_generated_skill_launcher(
    tmp_path,
    skill_name,
    runtime_call,
):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    pinned_command = TEST_SPECIFY_COMMAND
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": pinned_command,
                    "argv": [
                        "uvx",
                        "--from",
                        TEST_SPECIFY_SOURCE,
                        "specify",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    skill_path = tmp_path / ".codex" / "skills" / skill_name / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        f"Run `{runtime_call}`.\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    codes = {issue["code"] for issue in issues}
    assert "unbound-generated-specify-launcher" in codes
    misbound = next(
        issue
        for issue in issues
        if issue["code"] == "unbound-generated-specify-launcher"
    )
    assert f".codex/skills/{skill_name}/SKILL.md" in misbound["summary"]
    assert pinned_command in misbound["repair"]


def test_diagnose_project_runtime_compatibility_ignores_non_executable_specify_mentions(
    tmp_path,
):
    config_path = tmp_path / ".specify" / "config.json"
    config_path.parent.mkdir(parents=True)
    pinned_command = TEST_SPECIFY_COMMAND
    config_path.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": pinned_command,
                    "argv": [
                        "uvx",
                        "--from",
                        TEST_SPECIFY_SOURCE,
                        "specify",
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    skill_path = tmp_path / ".codex" / "skills" / "spx-discussion" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "Specify discussion behavior in plain language.\n\n"
        "Do not probe `specify cognition` or invent the unsupported "
        "`specify create-feature` command.\n\n"
        "The literal `specify discussion list --json` is documentation-only, "
        "not an executable instruction.\n\n"
        "```python\n"
        "def specify(value):\n"
        "    return value\n"
        "```\n\n"
        f"Run `{pinned_command} discussion list --json`.\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    codes = {issue["code"] for issue in issues}
    assert "unbound-generated-specify-launcher" not in codes


@pytest.mark.parametrize(
    "guidance_root",
    (".claude/skills", ".mimocode/commands"),
)
def test_runtime_diagnostics_inspect_all_supported_generated_guidance_roots(
    tmp_path,
    guidance_root,
):
    _write_pinned_launcher_config(tmp_path)
    command_path = tmp_path / guidance_root / "spx-discussion.md"
    command_path.parent.mkdir(parents=True)
    command_path.write_text(
        "Run `specify discussion list --json`.\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    issue = next(
        item
        for item in issues
        if item["code"] == "unbound-generated-specify-launcher"
    )
    assert f"{guidance_root}/spx-discussion.md" in issue["summary"]


@pytest.mark.parametrize("integration_key", ("claude", "cursor-agent", "copilot"))
def test_real_integration_addenda_do_not_emit_bare_specify_commands(
    tmp_path,
    integration_key,
):
    project = tmp_path / integration_key
    pinned = _write_pinned_launcher_config(project)
    integration = get_integration(integration_key)
    assert integration is not None
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )

    issues = diagnose_project_runtime_compatibility(project)

    assert not any(
        issue["code"] == "unbound-generated-specify-launcher"
        for issue in issues
    ), (integration_key, pinned, issues)
    unresolved = [
        path.relative_to(project).as_posix()
        for path in project.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".md", ".toml"}
        and (
            "{{specify-subcmd:" in path.read_text(encoding="utf-8")
            or "{{specify-cli}}" in path.read_text(encoding="utf-8")
        )
    ]
    assert unresolved == [], (integration_key, unresolved)


def test_runtime_diagnostics_ignore_documentation_only_shell_fence(tmp_path):
    _write_pinned_launcher_config(tmp_path)
    skill_path = tmp_path / ".codex" / "skills" / "spx-discussion" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "Documentation-only example:\n"
        "```bash\n"
        "specify discussion list --json\n"
        "```\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert not any(
        issue["code"] == "unbound-generated-specify-launcher"
        for issue in issues
    )


def test_runtime_diagnostics_do_not_leak_negative_context_across_paragraphs(tmp_path):
    _write_pinned_launcher_config(tmp_path)
    skill_path = tmp_path / ".codex" / "skills" / "spx-discussion" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "Do not run an unpinned Specify command during discovery.\n\n"
        "Run `specify discussion list --json` to resume.\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(
        issue["code"] == "unbound-generated-specify-launcher"
        for issue in issues
    )


def test_launcher_rebinding_scopes_negative_language_to_each_inline_command():
    pinned = "uvx --from git+https://example.test/spec-kit-plus.git@new specify"
    content = (
        "Verify with `specify --help`, then continue; "
        "do not call `specify lane register`.\n"
    )

    rebound, count = rebind_unbound_specify_runtime_calls(content, pinned)

    assert count == 1
    assert f"`{pinned} --help`" in rebound
    assert "do not call `specify lane register`" in rebound


def test_project_cognition_rebinding_covers_inline_and_shell_fence_calls():
    pinned = "C:/trusted/specify-runtime.exe"
    content = (
        "Run `specify-runtime cognition generate-ignore --format json`.\n\n"
        "```bash\n"
        "specify-runtime cognition scan-set --format json\n"
        "```\n\n"
        "Do not run `specify-runtime cognition mark-dirty`.\n"
    )

    rebound, count = rebind_unbound_specify_runtime_cognition_calls(
        content,
        pinned,
    )

    assert count == 2
    assert f"`{pinned} cognition generate-ignore --format json`" in rebound
    assert f"{pinned} cognition scan-set --format json" in rebound
    assert "Do not run `specify-runtime cognition mark-dirty`" in rebound


def test_runtime_diagnostics_ignore_workflow_arrow_notation(tmp_path):
    _write_pinned_launcher_config(tmp_path)
    skill_path = tmp_path / ".codex" / "skills" / "workflow" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "The feature workflow is `specify -> plan -> tasks -> implement`.\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert not any(
        issue["code"] == "unbound-generated-specify-launcher"
        for issue in issues
    )


def test_launcher_rebinding_uses_same_executable_detection_contract():
    pinned = SpecifyLauncherSpec(
        command="uvx --from git+https://example.test/spec-kit-plus.git@new specify",
        argv=(
            "uvx",
            "--from",
            "git+https://example.test/spec-kit-plus.git@new",
            "specify",
        ),
    )
    content = (
        "Run `specify discussion list --json`.\n\n"
        "Documentation-only example:\n"
        "```bash\n"
        "specify check\n"
        "```\n\n"
        "```bash\n"
        "specify learning list --format json\n"
        "```\n\n"
        "The workflow is `specify -> plan`.\n"
        "Run `uvx --from git+https://example.test/spec-kit-plus.git@old specify check`.\n"
    )

    rebound, source_count = rebind_source_bound_specify_launchers(content, pinned)
    rebound, bare_count = rebind_unbound_specify_runtime_calls(
        rebound,
        pinned.command,
    )

    assert source_count == 1
    assert bare_count == 2
    assert f"`{pinned.command} discussion list --json`" in rebound
    assert f"{pinned.command} learning list --format json" in rebound
    assert "Documentation-only example:\n```bash\nspecify check" in rebound
    assert "`specify -> plan`" in rebound
    assert "@old" not in rebound


def test_runtime_diagnostics_inspect_root_context_managed_block(tmp_path):
    _write_pinned_launcher_config(tmp_path)
    (tmp_path / "AGENTS.md").write_text(
        "# User rules\n\n"
        "<!-- SPEC-KIT:BEGIN -->\n"
        "Run `specify learning start --command ask --format json`.\n"
        "<!-- SPEC-KIT:END -->\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    issue = next(
        item
        for item in issues
        if item["code"] == "unbound-generated-specify-launcher"
    )
    assert "AGENTS.md" in issue["summary"]


def test_runtime_diagnostics_ignore_user_commands_outside_managed_block(tmp_path):
    pinned_command = _write_pinned_launcher_config(tmp_path)
    (tmp_path / "AGENTS.md").write_text(
        "# User rules\n\n"
        "Run `specify check` for my custom PATH workflow.\n\n"
        "<!-- SPEC-KIT:BEGIN -->\n"
        f"Run `{pinned_command} learning start --command ask --format json`.\n"
        "<!-- SPEC-KIT:END -->\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert not any(
        issue["code"] == "unbound-generated-specify-launcher"
        for issue in issues
    )


def test_runtime_diagnostics_warn_when_learning_index_missing(tmp_path):
    project = tmp_path
    skill_dir = project / ".specify" / "templates" / "passive-skills" / "spec-kit-project-learning"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "Learning Reflex\n.specify/memory/learnings/INDEX.md\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(project)

    codes = [issue["code"] for issue in issues]
    assert "missing-learning-index" in codes


def test_diagnose_project_runtime_compatibility_reports_stale_powershell_resolver(tmp_path):
    common_path = tmp_path / ".specify" / "scripts" / "powershell" / "common.ps1"
    common_path.parent.mkdir(parents=True)
    common_path.write_text(
        "function Get-FeaturePathsEnv { $featureDir = Get-FeatureDir -RepoRoot $repoRoot -Branch $currentBranch }\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(issue["code"] == "stale-powershell-feature-resolver" for issue in issues)
    stale = next(issue for issue in issues if issue["code"] == "stale-powershell-feature-resolver")
    assert "..." not in stale["repair"]
    assert "<agent>" in stale["repair"]


def test_diagnose_project_runtime_compatibility_reports_stale_feature_root_contract(tmp_path):
    bash_common = tmp_path / ".specify" / "scripts" / "bash" / "common.sh"
    bash_common.parent.mkdir(parents=True)
    bash_common.write_text('get_feature_dir() { echo "$1/specs/$2"; }\n', encoding="utf-8")

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(issue["code"] == "stale-feature-root-contract" for issue in issues)
    stale = next(issue for issue in issues if issue["code"] == "stale-feature-root-contract")
    assert ".specify/features/" in stale["summary"]
    assert "specify integration repair" in stale["repair"]


def test_diagnose_project_runtime_compatibility_reports_workflow_contract_drift(tmp_path):
    common_path = tmp_path / ".specify" / "scripts" / "powershell" / "common.ps1"
    common_path.parent.mkdir(parents=True)
    common_path.write_text(
        "function Find-FeatureDirByPrefix {}\nFind-FeatureDirByPrefix -RepoRoot $repoRoot -BranchName $currentBranch\n",
        encoding="utf-8",
    )

    analyze_path = tmp_path / ".specify" / "templates" / "commands" / "analyze.md"
    analyze_path.parent.mkdir(parents=True)
    analyze_path.write_text(
        "Run scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks\n",
        encoding="utf-8",
    )

    learning_path = tmp_path / ".specify" / "templates" / "passive-skills" / "spec-kit-project-learning" / "SKILL.md"
    learning_path.parent.mkdir(parents=True)
    learning_path.write_text(
        "specify hook review-learning --command analyze --origin-artifact plan.md\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)
    codes = {issue["code"] for issue in issues}

    assert "stale-analyze-lane-routing-template" in codes
    assert "stale-review-learning-command-surface" in codes


def test_diagnose_project_runtime_compatibility_reports_stale_claude_shell_hook_commands(tmp_path):
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

    assert any(issue["code"] == "stale-claude-managed-hook-command" for issue in issues)


def test_diagnose_project_runtime_compatibility_reports_stale_claude_cmd_launcher_commands(tmp_path):
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
                                    "command": '"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook.cmd claude session-start',
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

    assert any(issue["code"] == "stale-claude-managed-hook-command" for issue in issues)


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


def test_diagnose_project_runtime_compatibility_reports_stale_claude_node_launchers(tmp_path):
    launcher_variants = [
        {
            "type": "command",
            "command": "node",
            "args": [
                "${CLAUDE_PROJECT_DIR}/.specify/bin/specify-hook.mjs",
                "claude",
                "session-start",
            ],
        },
        {
            "type": "command",
            "command": "node",
            "args": [
                '"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook.mjs',
                "claude",
                "session-start",
            ],
        },
        {
            "type": "command",
            "command": 'node ".specify/bin/specify-hook.mjs" claude session-start',
        },
    ]

    for hook in launcher_variants:
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps({"hooks": {"SessionStart": [{"hooks": [hook]}]}}),
            encoding="utf-8",
        )

        issues = diagnose_project_runtime_compatibility(tmp_path)

        assert any(issue["code"] == "stale-claude-managed-hook-command" for issue in issues), hook


def test_diagnose_project_runtime_compatibility_accepts_current_claude_node_launcher(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"hooks": {"SessionStart": [{"hooks": [render_claude_hook_launcher("session-start")]}]}}),
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert not any(issue["code"] == "stale-claude-managed-hook-command" for issue in issues)


def test_diagnose_project_runtime_compatibility_reports_codex_claude_hook_artifacts(tmp_path):
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True)
    hooks_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PostToolUse": [
                        {
                            "matcher": "Bash|Edit|Write|MultiEdit|Task",
                            "hooks": [
                                render_claude_hook_launcher("post-tool-session-state")
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert any(issue["code"] == "codex-claude-hook-artifact" for issue in issues)


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

    assert command == '"$GEMINI_PROJECT_DIR"/.specify/bin/specify-hook.cmd gemini before-tool'


def test_render_hook_launcher_command_can_target_powershell_surface_from_posix(monkeypatch):
    monkeypatch.setattr(os, "name", "posix", raising=False)

    command = render_hook_launcher_command(
        "claude",
        "session-start",
        project_dir_env_var="CLAUDE_PROJECT_DIR",
        script_type="ps",
    )

    assert command == '"$CLAUDE_PROJECT_DIR"/.specify/bin/specify-hook.cmd claude session-start'


def test_render_claude_hook_launcher_uses_single_command_string():
    hook = render_claude_hook_launcher("session-start")

    assert hook["type"] == "command"
    assert hook["command"].startswith('node -e "')
    assert hook["command"].endswith('" specify-hook claude session-start')
    assert "specify-hook.mjs" in hook["command"]
    assert "args" not in hook
    assert "${CLAUDE_PROJECT_DIR}" not in json.dumps(hook)
    assert "$CLAUDE_PROJECT_DIR" not in json.dumps(hook)
    assert "$env:CLAUDE_PROJECT_DIR" not in json.dumps(hook)


def test_render_claude_hook_launcher_command_runs_from_project_root_without_shell_env(tmp_path):
    if shutil.which("node") is None:
        return

    project = tmp_path / "project"
    launcher = project / ".specify" / "bin" / "specify-hook.mjs"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        "\n".join(
            [
                "import { readFileSync } from 'node:fs';",
                "const stdin = readFileSync(0, 'utf8');",
                "console.log(JSON.stringify({",
                "  argv: process.argv.slice(2),",
                "  cwd: process.cwd(),",
                "  stdin: JSON.parse(stdin)",
                "}));",
            ]
        ),
        encoding="utf-8",
    )

    hook = render_claude_hook_launcher("session-start")
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)

    result = subprocess.run(
        hook["command"],
        input=json.dumps({"cwd": str(project), "hook_event_name": "SessionStart"}),
        text=True,
        capture_output=True,
        cwd=project,
        env=env,
        shell=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["argv"] == ["claude", "session-start"]
    assert payload["cwd"] == str(project)
    assert payload["stdin"]["cwd"] == str(project)


def test_render_claude_hook_launcher_command_discovers_project_root_from_nested_cwd(tmp_path):
    if shutil.which("node") is None:
        return

    project = tmp_path / "project"
    nested_cwd = project / "apps" / "web"
    nested_cwd.mkdir(parents=True)
    launcher = project / ".specify" / "bin" / "specify-hook.mjs"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        "\n".join(
            [
                "import { readFileSync } from 'node:fs';",
                "import { dirname, resolve } from 'node:path';",
                "import { fileURLToPath } from 'node:url';",
                "const stdin = readFileSync(0, 'utf8');",
                "const scriptRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');",
                "console.log(JSON.stringify({",
                "  argv: process.argv.slice(2),",
                "  cwd: process.cwd(),",
                "  scriptRoot,",
                "  stdin: JSON.parse(stdin)",
                "}));",
            ]
        ),
        encoding="utf-8",
    )

    hook = render_claude_hook_launcher("stop-monitor")
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)

    result = subprocess.run(
        hook["command"],
        input=json.dumps({"cwd": str(nested_cwd), "hook_event_name": "Stop"}),
        text=True,
        capture_output=True,
        cwd=nested_cwd,
        env=env,
        shell=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["argv"] == ["claude", "stop-monitor"]
    assert payload["cwd"] == str(nested_cwd)
    assert payload["scriptRoot"] == str(project)
    assert payload["stdin"]["cwd"] == str(nested_cwd)


def test_plain_node_hook_command_would_execute_hook_payload_as_javascript(tmp_path):
    if shutil.which("node") is None:
        return

    result = subprocess.run(
        ["node"],
        input=json.dumps({"cwd": str(tmp_path), "hook_event_name": "SessionStart"}),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode != 0
    assert "[stdin]:1" in result.stderr


def test_install_shared_hook_launcher_assets_writes_all_runtime_files(tmp_path):
    created = install_shared_hook_launcher_assets(tmp_path)
    relpaths = sorted(path.relative_to(tmp_path).as_posix() for path in created)

    assert relpaths == [
        ".specify/bin/specify-hook",
        ".specify/bin/specify-hook.cmd",
        ".specify/bin/specify-hook.mjs",
        ".specify/bin/specify-hook.py",
    ]

    posix_launcher = tmp_path / ".specify" / "bin" / "specify-hook"
    assert posix_launcher.exists()
    if os.name != "nt":
        assert posix_launcher.stat().st_mode & stat.S_IXUSR
