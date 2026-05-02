import json

import specify_cli
from specify_cli.launcher import (
    SpecifyLauncherSpec,
    load_project_specify_launcher,
    project_specify_subcommand,
    render_project_launcher_placeholders,
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
