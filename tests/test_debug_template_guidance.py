from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_debug_template_documents_capability_aware_investigation() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "debug.md").read_text(encoding="utf-8").lower()

    assert "capability-aware investigation" in content
    assert "parallel workers" in content
    assert "subagents" in content
    assert "native delegation surface" in content
    assert "leader-led" in content
    assert "debug file" in content
    assert "evidence-gathering" in content or "evidence-gathering tasks" in content


def test_debug_template_keeps_shared_guidance_integration_neutral() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "debug.md").read_text(encoding="utf-8").lower()

    assert "spawn_agent" not in content
    assert "wait_agent" not in content
    assert "close_agent" not in content
    assert "specify team" not in content
