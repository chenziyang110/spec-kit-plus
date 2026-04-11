import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "commands"
PRIMARY_TUI_SURFACES = ("specify", "clarify", "spec-extend", "explain")
ASCII_CARD_HEADER_RE = re.compile(r"(?m)^\s*\+--")
ASCII_CARD_LINE_RE = re.compile(r"(?m)^\s*\| .+\|\s*$")
ASCII_CARD_FOOTER_RE = re.compile(r"(?m)^\s*\+-{10,}\+?\s*$")


def _read_template(name: str) -> str:
    return (TEMPLATE_DIR / f"{name}.md").read_text(encoding="utf-8")


def _assert_contains_any(text: str, *needles: str) -> None:
    assert any(needle in text for needle in needles), f"Expected one of: {needles}"


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
    lowered = _read_template("explain").lower()

    _assert_contains_any(lowered, "stage header", "stage title")
    _assert_contains_any(lowered, "status block", "status section")
    _assert_contains_any(lowered, "explanation block", "explanation section")
    _assert_contains_any(lowered, "risk block", "risk section")
    _assert_contains_any(lowered, "next-step block", "next step block", "next-step section")
    assert "status card" not in lowered
    assert "open-risk panel" not in lowered
    assert "next-step panel" not in lowered


def test_clarify_signals_compatibility_mode_visually():
    lowered = _read_template("clarify").lower()

    assert "spec-extend" in lowered
    assert "compatibility mode" in lowered
    _assert_contains_any(lowered, "main path", "not the main path")
    _assert_contains_any(lowered, "stage header", "stage title")
    _assert_contains_any(lowered, "status block", "compatibility status")
    assert re.search(r"open (question )?blocks?", lowered)
