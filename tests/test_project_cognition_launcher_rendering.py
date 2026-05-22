import json
from pathlib import Path

from specify_cli.launcher import render_project_launcher_placeholders


def test_project_cognition_subcommand_renders_to_direct_binary_without_config(tmp_path: Path):
    rendered = render_project_launcher_placeholders(
        tmp_path,
        "{{specify-subcmd:project-cognition validate-build --format json}}",
    )

    assert rendered == "project-cognition validate-build --format json"


def test_non_project_cognition_subcommand_keeps_specify_launcher_behavior(tmp_path: Path):
    rendered = render_project_launcher_placeholders(
        tmp_path,
        "{{specify-subcmd:learning start --command plan --format json}}",
    )

    assert rendered == "specify learning start --command plan --format json"


def test_project_cognition_subcommand_ignores_persisted_specify_launcher(tmp_path: Path):
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

    rendered = render_project_launcher_placeholders(
        tmp_path,
        "{{specify-subcmd:project-cognition status --format json}}",
    )

    assert rendered == "project-cognition status --format json"
