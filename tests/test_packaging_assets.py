from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_wheel_force_include_bundles_passive_skills() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/passive-skills" = "specify_cli/core_pack/passive-skills"' in pyproject


def test_wheel_force_include_bundles_workflow_state_template() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        '"templates/workflow-state-template.md" = '
        '"specify_cli/core_pack/templates/workflow-state-template.md"'
    ) in pyproject
