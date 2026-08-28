from __future__ import annotations

import json
import re
from pathlib import Path

from specify_cli.design import lint_design_preview_file


REPO_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_TEMPLATE = REPO_ROOT / "templates" / "design-preview-template.html"


def _manifest(content: str) -> dict[str, object]:
    match = re.search(
        r'<script\b(?=[^>]*\bid="design-preview-manifest")[^>]*>(.*?)</script>',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    assert match is not None
    payload = json.loads(match.group(1))
    assert isinstance(payload, dict)
    return payload


def _configured_seed() -> str:
    content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")
    content = content.replace(
        'data-preview-status="scaffold"',
        'data-preview-status="candidate"',
    )
    content = re.sub(r"__[A-Z0-9_]+__", "Configured design content", content)
    manifest = _manifest(content)
    manifest["configured"] = True
    review = manifest["review"]
    assert isinstance(review, dict)
    review["status"] = "candidate"
    review["approved_direction"] = None
    directions = manifest["directions"]
    assert isinstance(directions, list) and len(directions) == 1
    direction = directions[0]
    assert isinstance(direction, dict)
    direction["dials"] = {
        "variance": 6,
        "motion": 4,
        "density": 7,
        "inference_reason": "Confirmed operator workspace with dense daily use",
    }
    direction["aesthetic_family"] = "operational-editorial"
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2)
    return re.sub(
        r'(<script\b(?=[^>]*\bid="design-preview-manifest")[^>]*>).*?(</script>)',
        lambda match: f"{match.group(1)}\n{rendered}\n  {match.group(2)}",
        content,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )


def test_preview_template_is_one_iterative_concept_per_round() -> None:
    content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")
    manifest = _manifest(content)

    assert content.count("data-direction-id=") == 1
    assert 'data-direction-id="direction-main"' in content
    assert 'data-direction-id="direction-b"' not in content
    assert 'data-direction-id="direction-c"' not in content
    assert '"id": "direction-b"' not in content
    assert '"id": "direction-c"' not in content
    assert len(manifest["directions"]) == 1

    schema = json.loads(
        (REPO_ROOT / "templates" / "design-preview-manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["properties"]["directions"]["minItems"] == 1
    assert schema["properties"]["directions"]["maxItems"] == 1


def test_ready_lint_rejects_an_unfinished_prototype_seed(tmp_path: Path) -> None:
    preview = tmp_path / "round-01.html"
    preview.write_text(_configured_seed(), encoding="utf-8")

    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(item.code == "preview-unfinished-prototype" for item in diagnostics)


def test_design_workflows_require_collaborative_single_concept_iteration() -> None:
    classic = (
        REPO_ROOT / "templates" / "command-partials" / "design" / "shell.md"
    ).read_text(encoding="utf-8")
    advanced = (
        REPO_ROOT / "templates" / "advanced-skills" / "spx-design" / "SKILL.md"
    ).read_text(encoding="utf-8")
    combined = f"{classic}\n{advanced}".lower()

    for phrase in (
        "one high-impact design question at a time",
        "single concept",
        "same direction",
        "new immutable round",
        "explicit approval",
        "do not advance past an unanswered question",
        "professional reference package bundled with `sp-design`",
    ):
        assert phrase in combined

    assert "exactly three" not in combined
    assert "three-direction" not in combined


def test_design_brief_persists_dialogue_and_stage_state() -> None:
    brief = (REPO_ROOT / "templates" / "design-brief-template.md").read_text(
        encoding="utf-8"
    )

    for marker in (
        "active_command: sp-design",
        "phase_mode: design-only",
        "current_stage: context-intake",
        "active_question:",
        "feedback_history:",
        "prototype_rounds:",
    ):
        assert marker in brief


def test_professional_ui_skill_routes_dialogue_craft_and_platform_guidance() -> None:
    references_root = REPO_ROOT / "templates" / "command-references" / "design"
    reference_index = (references_root / "INDEX.md").read_text(encoding="utf-8")
    skill = (
        REPO_ROOT / "templates" / "command-partials" / "design" / "shell.md"
    ).read_text(encoding="utf-8")

    expected_references = {
        "discovery-dialogue.md",
        "prototype-craft.md",
        "critique-loop.md",
        "platform-web.md",
        "platform-apple.md",
        "platform-windows.md",
        "platform-android.md",
    }
    for name in expected_references:
        assert (references_root / name).is_file()
        assert name in skill
        assert name in reference_index

    advanced_root = REPO_ROOT / "templates" / "advanced-skills" / "spx-design"
    advanced = (advanced_root / "SKILL.md").read_text(encoding="utf-8")
    for name in ("studio-loop.md", "platform-guidance.md"):
        assert (advanced_root / "references" / name).is_file()
        assert name in advanced
