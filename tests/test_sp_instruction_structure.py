from pathlib import Path

import yaml

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = PROJECT_ROOT / "templates" / "commands"


def _load_frontmatter(path: Path) -> dict:
    content = read_template(path.relative_to(PROJECT_ROOT).as_posix())
    parts = content.split("---", 2)
    return yaml.safe_load(parts[1])


def test_shared_sp_command_templates_use_trigger_descriptions():
    command_files = sorted(COMMANDS_DIR.glob("*.md"))
    assert command_files

    for path in command_files:
        frontmatter = _load_frontmatter(path)
        description = frontmatter.get("description", "")
        assert isinstance(description, str)
        assert description.startswith("Use when"), f"{path.name} should use trigger-oriented descriptions"


def test_shared_sp_command_templates_expose_workflow_contract_summary():
    command_files = sorted(COMMANDS_DIR.glob("*.md"))
    assert command_files

    for path in command_files:
        content = read_template(path.relative_to(PROJECT_ROOT).as_posix())
        assert "## Workflow Contract Summary" in content, f"{path.name} missing summary shell"
        assert "routing metadata only" in content.lower(), f"{path.name} should distinguish summary from full contract"


def test_shared_sp_command_templates_store_workflow_contract_fields_in_frontmatter():
    command_files = sorted(COMMANDS_DIR.glob("*.md"))
    assert command_files

    required_keys = (
        "when_to_use",
        "primary_objective",
        "primary_outputs",
        "default_handoff",
    )

    for path in command_files:
        frontmatter = _load_frontmatter(path)
        workflow_contract = frontmatter.get("workflow_contract")
        assert isinstance(workflow_contract, dict), f"{path.name} missing workflow_contract frontmatter"
        for key in required_keys:
            value = workflow_contract.get(key)
            assert isinstance(value, str) and value.strip(), (
                f"{path.name} workflow_contract.{key} should be a non-empty string"
            )


def test_shared_sp_command_templates_expose_common_navigation_sections():
    command_files = sorted(COMMANDS_DIR.glob("*.md"))
    assert command_files

    required_headings = (
        "## Objective",
        "## Process",
        "## Output Contract",
        "## Guardrails",
    )

    for path in command_files:
        content = read_template(path.relative_to(PROJECT_ROOT).as_posix())
        for heading in required_headings:
            assert heading in content, f"{path.name} missing common section {heading}"
