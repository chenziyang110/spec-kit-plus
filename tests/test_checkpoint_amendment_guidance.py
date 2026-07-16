import re
from pathlib import Path

import pytest

from .template_utils import read_command_with_references


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCED_SKILLS = PROJECT_ROOT / "templates" / "advanced-skills"


def _advanced_skill_with_references(skill_name: str) -> str:
    skill_dir = ADVANCED_SKILLS / skill_name
    paths = [skill_dir / "SKILL.md", *sorted((skill_dir / "references").glob("*.md"))]
    return "\n\n".join(path.read_text(encoding="utf-8") for path in paths)


def _normalized(content: str) -> str:
    return re.sub(r"\s+", " ", content.lower())


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(read_command_with_references("quick"), id="classic-quick"),
        pytest.param(_advanced_skill_with_references("spx-quick"), id="advanced-quick"),
    ],
)
def test_quick_checkpoint_amendment_explains_material_scope_change_first(
    content: str,
) -> None:
    normalized = _normalized(content)

    assert "quick checkpoint amendment" in normalized
    assert "do not reopen confirmation" in normalized
    assert "same confirmed outcome" in normalized
    assert "before presenting the amendment" in normalized
    assert "why the previous confirmation no longer covers" in normalized
    assert "consequence of omitting" in normalized
    assert "current mutation state" in normalized
    assert "only after that explanation" in normalized
    assert "only the changed rows or decisions" in normalized
    assert "do not repeat the full initial quick checkpoint" in normalized
    assert "understanding_confirmed: false" in normalized


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(read_command_with_references("debug"), id="classic-debug"),
        pytest.param(_advanced_skill_with_references("spx-debug"), id="advanced-debug"),
    ],
)
def test_debug_checkpoint_amendment_explains_boundary_change_without_reapproving_causal_work(
    content: str,
) -> None:
    normalized = _normalized(content)

    assert "debug checkpoint amendment" in normalized
    assert "do not reopen confirmation" in normalized
    assert "same causal chain" in normalized
    assert "hypothesis" in normalized
    assert "before presenting the amendment" in normalized
    assert "why the previous confirmation no longer covers" in normalized
    assert "consequence of omitting" in normalized
    assert "current mutation state" in normalized
    assert "only after that explanation" in normalized
    assert "only the changed rows or decisions" in normalized
    assert "do not repeat the full initial debug checkpoint" in normalized
    assert "understanding_confirmed: false" in normalized
