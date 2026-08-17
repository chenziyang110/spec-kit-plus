import json
from pathlib import Path

from specify_cli.execution.result_handoff import FEATURE_LANE_RESULT_DIRECTORIES
from specify_cli.extensions import CORE_COMMAND_NAMES, _FALLBACK_CORE_COMMAND_NAMES
from specify_cli.hooks.artifact_validation import (
    DIRECTORY_REQUIRED_ARTIFACTS,
    FILE_REQUIRED_ARTIFACTS,
    REQUIRED_ARTIFACTS,
)
from specify_cli.hooks.state_validation import EXPECTED_WORKFLOW_STATE
from specify_cli.integrations.base import IntegrationBase
from specify_cli.orchestration.adapters import FIRST_RELEASE_WORKFLOW_COMMANDS
from specify_cli.orchestration.models import _ORDINARY_SP_COMMANDS


ROOT = Path(__file__).resolve().parents[1]


def test_clarify_templates_and_profile_membership_are_removed() -> None:
    removed_paths = (
        "templates/commands/clarify.md",
        "templates/command-partials/clarify",
        "templates/command-references/clarify",
        "templates/advanced-skills/spx-clarify",
        "tests/fixtures/command-reference-coverage/clarify.json",
    )
    assert not [path for path in removed_paths if (ROOT / path).exists()]

    classic_commands = {
        path.stem for path in (ROOT / "templates" / "commands").glob("*.md")
    }
    advanced_skills = {
        path.name
        for path in (ROOT / "templates" / "advanced-skills").glob("spx-*")
        if path.is_dir()
    }
    surface_map = json.loads(
        (ROOT / "templates" / "advanced-skills" / "_shared" / "surface-map.json").read_text(
            encoding="utf-8"
        )
    )

    assert "clarify" not in classic_commands
    assert "spx-clarify" not in advanced_skills
    assert "spx-clarify" not in surface_map["skills"]


def test_clarify_is_absent_from_python_runtime_registries() -> None:
    registries = (
        CORE_COMMAND_NAMES,
        _FALLBACK_CORE_COMMAND_NAMES,
        IntegrationBase.COMMAND_REFERENCE_WORKFLOWS,
        FEATURE_LANE_RESULT_DIRECTORIES,
        FILE_REQUIRED_ARTIFACTS,
        DIRECTORY_REQUIRED_ARTIFACTS,
        REQUIRED_ARTIFACTS,
        EXPECTED_WORKFLOW_STATE,
        FIRST_RELEASE_WORKFLOW_COMMANDS,
        _ORDINARY_SP_COMMANDS,
    )
    assert all("clarify" not in registry for registry in registries)
