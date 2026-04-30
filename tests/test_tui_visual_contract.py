import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "commands"
PRIMARY_TUI_SURFACES = ("specify", "clarify", "explain")
ASCII_CARD_HEADER_RE = re.compile(r"(?m)^\s*\+--")
ASCII_CARD_LINE_RE = re.compile(r"(?m)^\s*\| .+\|\s*$")
ASCII_CARD_FOOTER_RE = re.compile(r"(?m)^\s*\+-{10,}\+?\s*$")


def _read_template(name: str) -> str:
    return (TEMPLATE_DIR / f"{name}.md").read_text(encoding="utf-8")


def _assert_contains_any(text: str, *needles: str) -> None:
    assert any(needle in text for needle in needles), f"Expected one of: {needles}"


def _extract_section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text)
    assert match, f"Missing section: {heading}"
    return match.group(1)


def _bullet_lines(text: str) -> list[str]:
    return [match.group(1).strip().lower() for match in re.finditer(r"(?m)^\s*-\s+(.+)$", text)]


def _assert_bullet_contains(bullets: list[str], needle: str) -> None:
    assert any(needle in bullet for bullet in bullets), f"Expected bullet containing: {needle}"


def test_primary_template_surfaces_do_not_use_right_side_card_framing():
    for surface in PRIMARY_TUI_SURFACES:
        content = _read_template(surface)

        assert not ASCII_CARD_HEADER_RE.search(content), (
            f"{surface} still defines an ASCII card header"
        )
        assert not ASCII_CARD_LINE_RE.search(content), (
            f"{surface} still uses a right-side pipe border"
        )
        assert not ASCII_CARD_FOOTER_RE.search(content), (
            f"{surface} still defines an ASCII box footer"
        )


def test_specify_uses_open_question_block_structure():
    lowered = _read_template("specify").lower()

    assert re.search(r"open (question )?blocks?", lowered)
    _assert_contains_any(lowered, "stage header", "stage title")
    _assert_contains_any(lowered, "question header", "question title")
    _assert_contains_any(lowered, "prompt", "question stem")
    _assert_contains_any(lowered, "recommendation", "recommended item", "[ recommended ]")
    _assert_contains_any(lowered, "reply instruction", "reply guidance", "response instruction")
    assert "example" in lowered
    assert "options" in lowered
    assert "question-card format" not in lowered
    assert "boxed card" not in lowered


def test_explain_requires_stage_status_risk_and_next_step_blocks():
    content = _read_template("explain")
    lowered = content.lower()
    outline = _extract_section(content, "Outline").lower()
    tui_requirements = _extract_section(content, "TUI Requirements").lower()
    tui_blocks = _bullet_lines(tui_requirements)

    _assert_bullet_contains(tui_blocks, "stage header")
    _assert_bullet_contains(tui_blocks, "status block")
    _assert_bullet_contains(tui_blocks, "explanation block")
    _assert_bullet_contains(tui_blocks, "risk block")
    _assert_bullet_contains(tui_blocks, "next-step block")
    assert "stage-aware" in tui_requirements
    assert re.search(r"`specify`: explain .*everyday terms", tui_requirements)
    assert re.search(r"`plan`: explain .*implementation approach", tui_requirements)
    assert re.search(r"`tasks`: explain .*concrete work", tui_requirements)
    assert re.search(r"`implement`: explain .*progress.*current scope.*active risks", tui_requirements)
    assert "choose_subagent_dispatch" in lowered
    assert "leader-inline-fallback" in lowered
    assert "supporting artifact cross-check" in outline
    assert "before rendering the final explanation" in outline
    assert "open or risky" in outline
    assert "next stage will do" in outline
    assert "status card" not in lowered
    assert "open-risk panel" not in lowered
    assert "next-step panel" not in lowered
