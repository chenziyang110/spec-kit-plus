from datetime import date
from pathlib import Path
import shutil

from specify_cli import build_constitution_template_for_profile, ensure_constitution_from_template
from specify_cli.learnings import ensure_learning_memory_from_templates


def _compact(text: str) -> str:
    return " ".join(text.split())


def _seed_constitution_template(project_path: Path) -> None:
    source_template = Path(__file__).resolve().parents[1] / "templates" / "constitution-template.md"
    target_template = project_path / ".specify" / "templates" / "constitution-template.md"
    target_template.parent.mkdir(parents=True, exist_ok=True)
    target_template.write_text(source_template.read_text(encoding="utf-8"), encoding="utf-8")


def _seed_constitution_profile_assets(project_path: Path) -> None:
    source_assets = Path(__file__).resolve().parents[1] / "templates" / "constitution"
    target_assets = project_path / ".specify" / "templates" / "constitution"
    target_assets.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_assets, target_assets, dirs_exist_ok=True)


def _seed_learning_templates(project_path: Path) -> None:
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    target_root = project_path / ".specify" / "templates"
    target_root.mkdir(parents=True, exist_ok=True)
    for name in (
        "project-rules-template.md",
        "project-learnings-template.md",
        "project-learnings-index-template.md",
        "project-learning-detail-template.md",
    ):
        source_template = templates_root / name
        target_template = target_root / name
        target_template.write_text(source_template.read_text(encoding="utf-8"), encoding="utf-8")


def test_ensure_constitution_from_template_materializes_defaults(tmp_path):
    project_path = tmp_path / "demo-project"
    project_path.mkdir()
    _seed_constitution_template(project_path)
    _seed_constitution_profile_assets(project_path)

    ensure_constitution_from_template(project_path)

    constitution_path = project_path / ".specify" / "memory" / "constitution.md"
    content = constitution_path.read_text(encoding="utf-8")
    compact_content = _compact(content)

    assert constitution_path.exists()
    assert "# demo-project Constitution" in content
    assert "### I. Specification-First Delivery" in content
    assert "### III. Test-Backed Changes (NON-NEGOTIABLE)" in content
    assert "### VII. No Unrequested Fallbacks" in content
    assert "Honor Explicit Technology Choices" in content
    assert "Fallbacks Require Consent" in content
    assert "Encoding Preservation" in content
    assert "preserve the file's existing character encoding and BOM behavior" in content
    assert ".specify/project-cognition/status.json" in content
    assert "workflow-appropriate cognition query bundles" in content
    assert "advisory project cognition index" in content
    assert "Map points, code proves" in content
    assert "Project Cognition Before Existing-System Judgment" in content
    assert "agents MUST query project cognition before broad source inspection" in compact_content
    assert "query result MUST guide routing, minimal live reads" in compact_content
    assert "Legacy handbook" in content
    assert "project-map exports" in content
    assert "compatibility surfaces only" in content
    assert "map-update" in content
    assert "map-scan" in content
    assert "map-build" in content
    assert "Maintain `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md` as the primary runtime atlas" not in content
    assert "Recommend `map-update`" in content
    assert "recommend `map-scan` followed by `map-build` only when the user" in compact_content
    assert "[PROJECT_NAME]" not in content
    assert "[RATIFICATION_DATE]" not in content
    assert "**Version**: 1.2.0" in content
    assert f"**Ratified**: {date.today().isoformat()}" in content


def test_product_constitution_profile_matches_shipped_template():
    repo_root = Path(__file__).resolve().parents[1]
    template_path = repo_root / "templates" / "constitution-template.md"
    expected = template_path.read_text(encoding="utf-8")
    built, profile = build_constitution_template_for_profile("product", repo_root)

    assert profile["id"] == "product"
    assert expected == built


def test_ensure_constitution_from_template_materializes_library_profile(tmp_path):
    project_path = tmp_path / "library-project"
    project_path.mkdir()
    _seed_constitution_template(project_path)
    _seed_constitution_profile_assets(project_path)

    ensure_constitution_from_template(project_path, constitution_profile="library")

    template_path = project_path / ".specify" / "templates" / "constitution-template.md"
    constitution_path = project_path / ".specify" / "memory" / "constitution.md"
    template_content = template_path.read_text(encoding="utf-8")
    content = constitution_path.read_text(encoding="utf-8")
    compact_content = _compact(content)

    assert "# library-project Constitution" in content
    assert "### IV. Stable Public Surface" in content
    assert "Public APIs, configuration keys, CLI flags, and file formats MUST" in content
    assert "SemVer and Release Discipline" in content
    assert "Examples and Upgrade Paths" in content
    assert "Project Cognition Before Existing-System Judgment" in content
    assert "existing project truth" in content
    assert "query result MUST guide routing, minimal live reads" in compact_content
    assert ".specify/project-cognition/status.json" not in content
    assert "# [PROJECT_NAME] Constitution" in template_content
    assert "Stable Public Surface" in template_content
    assert "[PROJECT_NAME]" not in content
    assert "**Version**: 1.1.0" in content
    assert f"**Ratified**: {date.today().isoformat()}" in content


def test_ensure_constitution_from_template_materializes_minimal_profile(tmp_path):
    project_path = tmp_path / "minimal-project"
    project_path.mkdir()
    _seed_constitution_template(project_path)
    _seed_constitution_profile_assets(project_path)

    ensure_constitution_from_template(project_path, constitution_profile="minimal")

    constitution_path = project_path / ".specify" / "memory" / "constitution.md"
    content = constitution_path.read_text(encoding="utf-8")

    assert "# minimal-project Constitution" in content
    assert "Project Cognition Before Existing-System Judgment" in content
    assert "scope boundaries" in content
    assert ".specify/project-cognition/status.json" not in content
    assert "**Version**: 1.1.0" in content


def test_ensure_constitution_from_template_materializes_regulated_profile(tmp_path):
    project_path = tmp_path / "regulated-project"
    project_path.mkdir()
    _seed_constitution_template(project_path)
    _seed_constitution_profile_assets(project_path)

    ensure_constitution_from_template(project_path, constitution_profile="regulated")

    constitution_path = project_path / ".specify" / "memory" / "constitution.md"
    content = constitution_path.read_text(encoding="utf-8")

    assert "# regulated-project Constitution" in content
    assert "Project Cognition Before Existing-System Judgment" in content
    assert "trust boundaries" in content
    assert "control impact" in content
    assert ".specify/project-cognition/status.json" not in content
    assert "**Version**: 1.1.0" in content


def test_ensure_constitution_from_template_preserves_existing_constitution(tmp_path):
    project_path = tmp_path / "existing-project"
    project_path.mkdir()
    _seed_constitution_template(project_path)
    _seed_constitution_profile_assets(project_path)

    constitution_path = project_path / ".specify" / "memory" / "constitution.md"
    constitution_path.parent.mkdir(parents=True, exist_ok=True)
    constitution_path.write_text("# Custom Constitution\n", encoding="utf-8")

    ensure_constitution_from_template(project_path, constitution_profile="regulated")

    assert constitution_path.read_text(encoding="utf-8") == "# Custom Constitution\n"


def test_ensure_constitution_from_template_preserves_custom_template(tmp_path):
    project_path = tmp_path / "custom-template-project"
    project_path.mkdir()
    _seed_constitution_profile_assets(project_path)

    template_path = project_path / ".specify" / "templates" / "constitution-template.md"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(
        "# Custom Constitution Template\n\n- MUST keep this custom template\n",
        encoding="utf-8",
    )

    ensure_constitution_from_template(project_path, constitution_profile="library")

    constitution_path = project_path / ".specify" / "memory" / "constitution.md"
    assert template_path.read_text(encoding="utf-8") == (
        "# Custom Constitution Template\n\n- MUST keep this custom template\n"
    )
    assert constitution_path.read_text(encoding="utf-8") == (
        "# Custom Constitution Template\n\n- MUST keep this custom template\n"
    )


def test_ensure_learning_memory_from_templates_materializes_defaults(tmp_path):
    project_path = tmp_path / "demo-project"
    project_path.mkdir()
    _seed_learning_templates(project_path)

    ensure_learning_memory_from_templates(project_path)

    rules_path = project_path / ".specify" / "memory" / "project-rules.md"
    learnings_path = project_path / ".specify" / "memory" / "project-learnings.md"
    index_path = project_path / ".specify" / "memory" / "learnings" / "INDEX.md"

    assert rules_path.exists()
    assert learnings_path.exists()
    assert index_path.exists()
    assert "Project Rules" in rules_path.read_text(encoding="utf-8")
    assert "Project Learnings" in learnings_path.read_text(encoding="utf-8")
    index_content = index_path.read_text(encoding="utf-8")
    assert "Project Learning Index" in index_content
    assert "Open only the linked detail documents" in index_content
    assert "trigger_signals" in index_content
    assert "Shared defaults that later `sp-xxx` workflows should follow" in rules_path.read_text(encoding="utf-8")
    learnings_content = learnings_path.read_text(encoding="utf-8")
    assert "Compatibility summary for older generated projects" in learnings_content
    assert ".specify/memory/learnings/INDEX.md" in learnings_content


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
