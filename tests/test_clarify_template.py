from pathlib import Path


def test_clarify_template_requires_at_least_five_questions():
    template_path = Path(__file__).resolve().parents[1] / "templates" / "commands" / "clarify.md"
    content = template_path.read_text(encoding="utf-8")

    assert "asking at least 5 highly targeted clarification questions" in content
    assert "candidate clarification questions (minimum 5)." in content
    assert "you have asked at least 5 questions" in content
    assert "Ask at least 5 total questions" in content
