import json
import os
from pathlib import Path

import pytest

from specify_cli.launcher import (
    render_command,
    render_project_launcher_placeholders,
    write_runtime_launcher_config,
)
from specify_cli.specify_runtime import project_runtime_launcher_arg


@pytest.mark.parametrize(
    "runtime_args",
    (
        ("api", "handshake", "--format", "json"),
        ("artifact", "show", "--kind", "spec", "--format", "json"),
        ("discussion", "list", "--json"),
        ("learning", "start", "--command", "plan", "--format", "json"),
        ("result", "path", "--command", "implement"),
        ("cognition", "status", "--format", "json"),
        ("validate", "spec", "--path", "feature/spec.md", "--format", "json"),
        ("version",),
        ("workflow", "status", "--format", "json"),
    ),
)
def test_unified_runtime_subcommand_renders_recoverable_marker_without_config(
    tmp_path: Path,
    runtime_args: tuple[str, ...],
):
    command = " ".join(("specify-runtime", *runtime_args))
    rendered = render_project_launcher_placeholders(
        tmp_path,
        f"{{{{specify-subcmd:{command}}}}}",
    )

    assert rendered == f"SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE:{command}"
    assert "(" not in rendered


def test_agent_learning_subcommand_never_falls_back_to_specify_launcher(tmp_path: Path):
    rendered = render_project_launcher_placeholders(
        tmp_path,
        "{{specify-subcmd:specify-runtime learning start --command plan --format json}}",
    )

    assert rendered == (
        "SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE:"
        "specify-runtime learning start --command plan --format json"
    )


@pytest.mark.parametrize(
    "runtime_args",
    (
        ("api", "handshake", "--format", "json"),
        ("artifact", "show", "--kind", "spec", "--format", "json"),
        ("discussion", "list", "--json"),
        ("learning", "start", "--command", "plan", "--format", "json"),
        ("result", "path", "--command", "implement"),
        ("cognition", "status", "--format", "json"),
        ("validate", "spec", "--path", "feature/spec.md", "--format", "json"),
        ("version",),
        ("workflow", "status", "--format", "json"),
    ),
)
def test_unified_runtime_subcommands_use_persisted_binary(
    tmp_path: Path,
    runtime_args: tuple[str, ...],
):
    binary = tmp_path / ".specify" / "bin" / "specify-runtime"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    write_runtime_launcher_config(tmp_path, binary)

    command = " ".join(("specify-runtime", *runtime_args))
    rendered = render_project_launcher_placeholders(
        tmp_path,
        f"{{{{specify-subcmd:{command}}}}}",
    )

    assert rendered == render_command((project_runtime_launcher_arg(), *runtime_args))


@pytest.mark.parametrize(
    "namespace",
    ("workflow", "artifact", "cognition", "discussion", "learning", "result"),
)
def test_unified_runtime_subcommand_ignores_persisted_specify_launcher(
    tmp_path: Path,
    namespace: str,
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

    rendered = render_project_launcher_placeholders(
        tmp_path,
        f"{{{{specify-subcmd:specify-runtime {namespace} status --format json}}}}",
    )

    assert rendered == (
        "SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE:"
        f"specify-runtime {namespace} status --format json"
    )


def test_project_cognition_compass_subcommand_uses_persisted_binary(tmp_path: Path):
    binary = tmp_path / ".specify" / "bin" / "specify-runtime"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    write_runtime_launcher_config(tmp_path, binary)

    rendered = render_project_launcher_placeholders(
        tmp_path,
        '{{specify-subcmd:specify-runtime cognition compass --intent debug --query="$ARGUMENTS" --format json}}',
    )

    query_arg = '--query="$ARGUMENTS"' if os.name == "nt" else "--query=$ARGUMENTS"
    assert rendered == render_command(
        (
            project_runtime_launcher_arg(),
            "cognition",
            "compass",
            "--intent",
            "debug",
            query_arg,
            "--format",
            "json",
        )
    )


def test_project_cognition_expand_subcommand_uses_persisted_binary(tmp_path: Path):
    binary = tmp_path / ".specify" / "bin" / "specify-runtime"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    write_runtime_launcher_config(tmp_path, binary)

    rendered = render_project_launcher_placeholders(
        tmp_path,
        "{{specify-subcmd:specify-runtime cognition expand --id exp-qf-test --section raw_candidates --format json}}",
    )

    assert rendered == (
        f"{project_runtime_launcher_arg()} cognition expand "
        "--id exp-qf-test --section raw_candidates --format json"
    )
