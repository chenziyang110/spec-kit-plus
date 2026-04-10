from pathlib import Path


def test_clarify_template_requires_at_least_five_questions():
    template_path = Path(__file__).resolve().parents[1] / "templates" / "commands" / "clarify.md"
    content = template_path.read_text(encoding="utf-8")

    assert "asking at least 5 highly targeted clarification questions" in content
    assert "candidate clarification questions (minimum 5)." in content
    assert "you have asked at least 5 questions" in content
    assert "Ask at least 5 total questions" in content
    assert "Default to concise clarification turns" in content
    assert "Do not restate the full current understanding after every answer" in content
    assert "Save the full synthesis for the final clarification report" in content
    assert "question-card format" in content.lower()
    assert "[ RECOMMENDED ]" in content
    assert "Reply naturally, for example:" in content
    assert '选 C' in content
    assert "Recorded: C - Normalize first" in content
