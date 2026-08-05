from pathlib import Path

from specify_cli.integrations.base import IntegrationBase


PROJECT_ROOT = Path(__file__).resolve().parent.parent


QUICK_CHECKPOINT_CARD_MARKERS = (
    "quick delivery checkpoint",
    "checkpoint-stage",
    "checkpoint-confirm",
    "checkpoint-show",
    "packet-compile",
    "item-start",
    "item-accept",
    "confirmation_digest",
    "delivery map",
    "decision checkpoint",
    "q1",
    "reconfirmation trigger",
)


DEBUG_CHECKPOINT_CARD_ROWS = (
    "| reported problem |",
    "| expected behavior |",
    "| occurrence conditions |",
    "| investigation boundary |",
    "| fix authority |",
    "| assumptions to correct |",
    "| reconfirmation trigger |",
)


UI_CONFIRMATION_CARD_ROWS = (
    "| confirmation purpose |",
    "| user and primary job |",
    "| design basis and source material |",
    "| target experience |",
    "| structure and visible change |",
    "| interaction, states, and adaptation |",
    "| design boundaries |",
    "| acceptance evidence |",
)


def assert_quick_checkpoint_card_shape(content: str) -> None:
    lowered = content.lower()

    assert "## quick delivery checkpoint" in lowered or "quick delivery checkpoint" in lowered
    for marker in QUICK_CHECKPOINT_CARD_MARKERS:
        assert marker in lowered, marker
    assert "delivery map" in lowered
    assert "pulse" in lowered
    assert "reply with `confirm`/`确认`" in lowered
    assert (
        "freeform prose" in lowered
        or "prose bullets or partial field lists are not sufficient" in lowered
        or "bullet-only confirmations do not satisfy this gate" in lowered
        or "do not hand-author a freeform two-column" in lowered
        or "do not hand-author a two-column" in lowered
    )
    # Decision surface is multi-column / runtime-rendered; do not require the
    # legacy two-column approval table for Quick.
    assert "subagent count" in lowered or "subagent" in lowered
    assert "never" in lowered and ("digest" in lowered or "confirmation_digest" in lowered)


def assert_debug_checkpoint_card_shape(content: str) -> None:
    lowered = content.lower()

    assert "## debug checkpoint" in lowered
    assert "| decision to confirm | current understanding |" in lowered
    for row in DEBUG_CHECKPOINT_CARD_ROWS:
        assert row in lowered
    assert "reply with `confirm`/`确认`" in lowered


def assert_ui_confirmation_card_shape(content: str) -> None:
    lowered = content.lower()

    assert "## ui confirmation" in lowered
    assert "| decision to confirm | ui proposal or target baseline |" in lowered
    for row in UI_CONFIRMATION_CARD_ROWS:
        assert row in lowered
    assert "single confirmation covers both" in lowered


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
