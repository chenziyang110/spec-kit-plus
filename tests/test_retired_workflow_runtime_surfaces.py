from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from specify_cli import SKILL_DESCRIPTIONS, app
from specify_cli.learnings import KNOWN_COMMANDS, normalize_command_name


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_retired_workflow_aliases_are_absent_from_public_python_surfaces() -> None:
    assert "prd" not in SKILL_DESCRIPTIONS
    assert "research" not in SKILL_DESCRIPTIONS
    assert "sp-prd" not in KNOWN_COMMANDS
    assert normalize_command_name("sp-research") == "sp-research"

    result = CliRunner().invoke(app, ["prd", "--help"])
    assert result.exit_code != 0

    init_source = _read("src/specify_cli/__init__.py")
    launcher_source = _read("src/specify_cli/launcher.py")
    assert "_display_cmd('prd')" not in init_source
    assert '        "prd",\n' not in launcher_source


def test_new_prd_state_writers_use_only_the_scan_workflow_identity() -> None:
    python_helper = _read("scripts/shared/prd-state.py")
    go_helper = _read("tools/specify-runtime/script_domains.go")
    python_hook = _read("src/specify_cli/hooks/state_validation.py")
    go_hook = _read("tools/specify-runtime/hook.go")

    assert 'active_command = "sp-prd"' not in python_helper
    assert 'activeCommand = "sp-prd"' not in go_helper
    assert '"prd": ("sp-prd", "analysis-only")' not in python_hook
    assert '"prd":           {"sp-prd", "analysis-only"}' not in go_hook


def test_go_runtime_no_longer_advertises_or_validates_retired_workflow_ids() -> None:
    learning = _read("tools/specify-runtime/learning.go")
    validation = _read("tools/specify-runtime/prd_validation.go")

    assert '"sp-prd"' not in learning
    assert 'raw == "sp-research"' not in learning
    assert 'stage != "prd"' not in validation
    assert 'case "prd":' not in validation
