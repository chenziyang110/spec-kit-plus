import json

import specify_cli
from specify_cli.launcher import (
    SpecifyLauncherSpec,
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
