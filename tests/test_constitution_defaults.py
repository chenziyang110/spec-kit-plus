from datetime import date
from pathlib import Path

from specify_cli import ensure_constitution_from_template


def _seed_constitution_template(project_path: Path) -> None:
    source_template = Path(__file__).resolve().parents[1] / "templates" / "constitution-template.md"
    target_template = project_path / ".specify" / "templates" / "constitution-template.md"
    target_template.parent.mkdir(parents=True, exist_ok=True)
    target_template.write_text(source_template.read_text(encoding="utf-8"), encoding="utf-8")


def test_ensure_constitution_from_template_materializes_defaults(tmp_path):
    project_path = tmp_path / "demo-project"
    project_path.mkdir()
    _seed_constitution_template(project_path)

    ensure_constitution_from_template(project_path)

    constitution_path = project_path / ".specify" / "memory" / "constitution.md"
    content = constitution_path.read_text(encoding="utf-8")

    assert constitution_path.exists()
    assert "# demo-project Constitution" in content
    assert "### I. Specification-First Delivery" in content
    assert "### III. Test-Backed Changes (NON-NEGOTIABLE)" in content
    assert "### VII. No Unrequested Fallbacks" in content
    assert "Honor Explicit Technology Choices" in content
    assert "Fallbacks Require Consent" in content
    assert "项目技术文档.md" in content
    assert "generate it before structural work" in content
    assert "[PROJECT_NAME]" not in content
    assert "[RATIFICATION_DATE]" not in content
    assert "**Version**: 1.0.0" in content
    assert f"**Ratified**: {date.today().isoformat()}" in content


def test_ensure_constitution_from_template_preserves_existing_constitution(tmp_path):
    project_path = tmp_path / "existing-project"
    project_path.mkdir()
    _seed_constitution_template(project_path)

    constitution_path = project_path / ".specify" / "memory" / "constitution.md"
    constitution_path.parent.mkdir(parents=True, exist_ok=True)
    constitution_path.write_text("# Custom Constitution\n", encoding="utf-8")

    ensure_constitution_from_template(project_path)

    assert constitution_path.read_text(encoding="utf-8") == "# Custom Constitution\n"
