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
    assert "existing logs" in content
    assert "observability as insufficient" in content
    assert "diagnostic logging" in content or "instrumentation" in content


def test_debug_template_uses_stage_and_protocol_structure() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "debug.md").read_text(encoding="utf-8").lower()

    assert "## role" in content
    assert "## operating principles" in content
    assert "## session lifecycle" in content
    assert "## investigation protocol" in content
    assert "stage 1: symptom intake" in content
    assert "stage 2: reproduction gate" in content
    assert "stage 3: log review" in content
    assert "stage 4: observability assessment" in content
    assert "stage 5: hypothesis formation" in content
    assert "stage 6: experiment loop" in content
    assert "stage 7: root cause confirmation" in content
    assert "## fix and verify protocol" in content
    assert "## checkpoint protocol" in content


def test_debug_template_keeps_shared_guidance_integration_neutral() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "debug.md").read_text(encoding="utf-8").lower()

    assert "spawn_agent" not in content
    assert "wait_agent" not in content
    assert "close_agent" not in content
    assert "specify team" not in content
