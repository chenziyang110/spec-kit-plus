from pathlib import Path

from specify_cli.integrations.base import IntegrationBase


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_template(path: str) -> str:
    template_path = PROJECT_ROOT / path
    raw = template_path.read_text(encoding="utf-8")
    return IntegrationBase.render_template_content(raw, template_path=template_path)


def read_command_with_references(command_name: str) -> str:
    """Return a command template plus its split reference contracts."""
    parts = [read_template(f"templates/commands/{command_name}.md")]
    references_dir = PROJECT_ROOT / "templates" / "command-references" / command_name
    if references_dir.exists():
        for reference_path in sorted(references_dir.glob("*.md")):
            relative_path = reference_path.relative_to(PROJECT_ROOT).as_posix()
            parts.append(read_template(relative_path))
    return "\n\n".join(parts)


def read_skill_with_references(skill_path: Path) -> str:
    """Return a generated SKILL.md plus rendered reference sidecars."""
    parts = [skill_path.read_text(encoding="utf-8")]
    references_dir = skill_path.parent / "references"
    if references_dir.exists():
        for reference_path in sorted(references_dir.rglob("*.md")):
            parts.append(reference_path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)
