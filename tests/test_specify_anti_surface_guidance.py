from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_specify_template_blocks_surface_only_release_patterns() -> None:
    content = _read("templates/commands/specify.md")

    assert "anti-surface warning signs" in content
    assert '"simple", "intuitive", "robust", or "clean"' in content
    assert "boundary conditions, failure behavior, or affected neighboring workflow remain unclear" in content
    assert "there is still no acceptance proof for how success will be judged" in content
    assert "conflict with the current owning module or existing repository pattern" in content
    assert "Do not release `Aligned: ready for plan` when the current understanding still depends on taste words" in content
    assert "implicit defaults" in content
    assert "untested assumptions" in content
    assert "boundary handling, compatibility impact, or acceptance proof" in content
    assert '"make it more intuitive"' in content
    assert '"handle permissions normally"' in content
    assert '"keep it compatible"' in content
    assert '"show an error if something goes wrong"' in content
    assert '"use the existing pattern"' in content
    assert '"it should feel fast"' in content
    assert '"just validate the data properly"' in content
    assert '"admins can handle the special cases"' in content
    assert "\"don't break existing clients\"" in content
    assert "convert the vague intent into concrete behavior, edge handling, compatibility scope, or acceptance evidence" in content
    assert "vague success standard" in content
    assert "vague data rule" in content
    assert "vague permission boundary" in content
    assert "vague compatibility claim" in content
    assert '"fast", "smooth", "easy", "clear", or "works well"' in content
    assert '"valid", "clean", "normalized", or "properly formatted"' in content
    assert '"normal permissions", "admin behavior", or "authorized users"' in content
    assert '"keep compatibility" or "don\'t break clients"' in content


def test_specify_skill_mirror_blocks_surface_only_release_patterns() -> None:
    for candidate in (".codex/skills/sp-specify/SKILL.md", ".agents/skills/sp-specify/SKILL.md"):
        path = PROJECT_ROOT / candidate
        if path.exists():
            content = path.read_text(encoding="utf-8")
            break
    else:
        raise AssertionError("Missing Codex sp-specify skill mirror")

    assert "anti-surface warning signs" in content
    assert '"simple", "intuitive", "robust", or "clean"' in content
    assert "boundary conditions, failure behavior, or affected neighboring workflow remain unclear" in content
    assert "there is still no acceptance proof for how success will be judged" in content
    assert "conflict with the current owning module or existing repository pattern" in content
    assert "Do not release `Aligned: ready for plan` when the current understanding still depends on taste words" in content
    assert '"make it more intuitive"' in content
    assert '"handle permissions normally"' in content
    assert '"keep it compatible"' in content
    assert '"show an error if something goes wrong"' in content
    assert '"use the existing pattern"' in content
    assert '"it should feel fast"' in content
    assert '"just validate the data properly"' in content
    assert '"admins can handle the special cases"' in content
    assert "\"don't break existing clients\"" in content
    assert "vague success standard" in content
    assert "vague data rule" in content
    assert "vague permission boundary" in content
    assert "vague compatibility claim" in content
