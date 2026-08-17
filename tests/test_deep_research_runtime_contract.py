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
            "deep-research status",
            "deep-research track-prepare",
            "deep-research track-lease",
            "deep-research track-submit",
            "deep-research track-reject",
            "deep-research track-accept",
            "deep-research track-yield",
            "deep-research synthesize",
            "deep-research audit-prepare",
            "deep-research audit-accept",
            "deep-research validate",
            "deep-research publish",
            "deep-research verify-handoff",
            "deep-research not-needed",
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
        assert "research/rejections/" in content
        assert "research/handoff-to-plan.json" in content


def test_deep_research_runtime_has_exclusive_registry_ownership() -> None:
    registry = json.loads(_read("templates/workflow-artifact-registry.json"))
    by_id = {artifact["id"]: artifact for artifact in registry["artifacts"]}
    runtime = by_id["feature_deep_research_runtime"]

    assert "**/research/rejections/*.json" in runtime["path_patterns"]
    assert "deep-research track-reject" in runtime["safe_instruction_patterns"]
    assert "research_evidence_artifacts" not in by_id
    assert "**/research/handoffs/*.json" not in by_id["stage_lane_results"][
        "path_patterns"
    ]
    assert "research/handoffs/" not in by_id["stage_lane_results"]["path_hints"]
