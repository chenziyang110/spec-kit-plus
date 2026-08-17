import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_spec_and_plan_contracts_bind_runtime_owned_deep_research() -> None:
    spec = json.loads(_read("templates/spec-contract-template.json"))
    plan = json.loads(_read("templates/plan-contract-template.json"))

    assert spec["feasibility_gate"] == {
        "decision": "not_selected",
        "capability_refs": [],
        "reason_refs": [],
    }
    assert plan["deep_research_binding"] == {
        "decision": "not_selected",
        "handoff_ref": None,
        "handoff_sha256": None,
        "source_spec_sha256": None,
        "state_revision": None,
        "claim_status": None,
        "handoff_ids": [],
    }


def test_classic_and_advanced_prompts_use_runtime_research_lifecycle() -> None:
    classic = _read("templates/commands/deep-research.md")
    advanced = _read("templates/advanced-skills/spx-deep-research/SKILL.md")
    plan = _read("templates/commands/plan.md")
    advanced_plan = _read("templates/advanced-skills/spx-plan/SKILL.md")

    for content in (classic, advanced):
        for command in (
            "deep-research init",
            "deep-research track-prepare",
            "deep-research track-lease",
            "deep-research track-submit",
            "deep-research track-accept",
            "deep-research synthesize",
            "deep-research audit-prepare",
            "deep-research audit-accept",
            "deep-research validate",
            "deep-research publish",
        ):
            assert command in content
        assert "research-evidence/" in content
        assert "deep-research.md" in content
        assert "derived" in content.lower()
        assert "Exa" not in content
        assert "Firecrawl" not in content

    for content in (plan, advanced_plan):
        assert "deep_research_binding" in content
        assert "deep-research verify-handoff" in content
        assert "source_spec_sha256" in content
        assert "handoff_sha256" in content


def test_deep_research_allowed_writes_include_evidence_and_runtime_state() -> None:
    classic = _read("templates/commands/deep-research.md")
    advanced = _read("templates/advanced-skills/spx-deep-research/SKILL.md")

    for content in (classic, advanced):
        assert "research-evidence/" in content
        assert "research/state.json" in content
        assert "research/track-manifest.json" in content
        assert "research/handoff-to-plan.json" in content

