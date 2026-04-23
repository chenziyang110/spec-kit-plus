from datetime import date
from pathlib import Path

from specify_cli import ensure_constitution_from_template
from specify_cli.learnings import ensure_learning_memory_from_templates


def _seed_constitution_template(project_path: Path) -> None:
    source_template = Path(__file__).resolve().parents[1] / "templates" / "constitution-template.md"
    target_template = project_path / ".specify" / "templates" / "constitution-template.md"
    target_template.parent.mkdir(parents=True, exist_ok=True)
    target_template.write_text(source_template.read_text(encoding="utf-8"), encoding="utf-8")


def _seed_learning_templates(project_path: Path) -> None:
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    target_root = project_path / ".specify" / "templates"
    target_root.mkdir(parents=True, exist_ok=True)
    for name in ("project-rules-template.md", "project-learnings-template.md"):
        source_template = templates_root / name
        target_template = target_root / name
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
    assert "Encoding Preservation" in content
    assert "preserve the file's existing character encoding and BOM behavior" in content
    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/" in content
    assert ".specify/project-map/status.json" in content
    assert "progressive disclosure" in content.lower()
    assert "generate it before structural work" in content
    assert "[PROJECT_NAME]" not in content
    assert "[RATIFICATION_DATE]" not in content
    assert "**Version**: 1.1.0" in content
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


def test_ensure_learning_memory_from_templates_materializes_defaults(tmp_path):
    project_path = tmp_path / "demo-project"
    project_path.mkdir()
    _seed_learning_templates(project_path)

    ensure_learning_memory_from_templates(project_path)

    rules_path = project_path / ".specify" / "memory" / "project-rules.md"
    learnings_path = project_path / ".specify" / "memory" / "project-learnings.md"

    assert rules_path.exists()
    assert learnings_path.exists()
    assert "Project Rules" in rules_path.read_text(encoding="utf-8")
    assert "Project Learnings" in learnings_path.read_text(encoding="utf-8")
    assert "Shared defaults that later `sp-xxx` workflows should follow" in rules_path.read_text(encoding="utf-8")
    assert "Confirmed project learnings that are reusable" in learnings_path.read_text(encoding="utf-8")


def test_ensure_learning_memory_from_templates_preserves_existing_files(tmp_path):
    project_path = tmp_path / "existing-project"
    project_path.mkdir()
    _seed_learning_templates(project_path)

    memory_dir = project_path / ".specify" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    rules_path = memory_dir / "project-rules.md"
    learnings_path = memory_dir / "project-learnings.md"
    rules_path.write_text("# Custom Rules\n", encoding="utf-8")
    learnings_path.write_text("# Custom Learnings\n", encoding="utf-8")

    ensure_learning_memory_from_templates(project_path)

    assert rules_path.read_text(encoding="utf-8") == "# Custom Rules\n"
    assert learnings_path.read_text(encoding="utf-8") == "# Custom Learnings\n"
