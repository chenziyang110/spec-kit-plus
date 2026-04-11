from pathlib import Path
import re


def _read_clarify_template() -> str:
    template_path = Path(__file__).resolve().parents[1] / "templates" / "commands" / "clarify.md"
    return template_path.read_text(encoding="utf-8")


def test_clarify_template_is_compatibility_bridge_to_spec_extend():
    content = _read_clarify_template()
    lowered = content.lower()

    assert "spec-extend" in lowered
    assert re.search(r"(route|recommend|redirect).{0,80}spec-extend", content, re.IGNORECASE | re.DOTALL)


def test_clarify_template_preserves_alignment_updates_during_migration():
    content = _read_clarify_template()

    assert "alignment.md" in content
    assert "adding newly provided requirements or constraints" in content
    assert "Update the alignment decision before reporting" in content
    assert "write the updated alignment report" in content.lower()
    assert "recommended next command" in content.lower()
