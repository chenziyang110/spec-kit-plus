"""Contract-level behavior checks for sp-discussion clarification and handoff."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "discussion_behavior"
    / "clarify_material_conflict_checkpoint_handoff.json"
)


def _compact(lines: list[str]) -> str:
    return re.sub(r"\s+", " ", "\n".join(lines)).lower()


def _accepted_by_fixture(text: str, required_terms: list[str]) -> bool:
    return all(term.lower() in text for term in required_terms)


def _grade_transcript(lines: list[str], fixture: dict) -> dict[str, bool]:
    text = _compact(lines)
    groups = {
        "clarification": ["actors", "scenarios", "success criteria"],
        "materials": ["source_materials", "mat-001", "mat-002", "material coverage"],
        "correction": ["conflict", "web", "non_goals", "unknown"],
        "checkpoint_resume": ["checkpoint", "latest_checkpoint.snapshot_sha256", "resume"],
        "handoff_integrity": ["selected consumer", "agent_requirement_contract", "discussion_snapshot_digest"],
    }
    results = {
        name: all(term in text for term in terms) for name, terms in groups.items()
    }
    results["complete_contract"] = _accepted_by_fixture(
        text, fixture["required_good_terms"]
    )
    return results


def test_discussion_behavior_fixture_accepts_complete_clarification_transcript() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    results = _grade_transcript(fixture["good_transcript"], fixture)

    assert all(results.values()), results


def test_discussion_behavior_fixture_rejects_missing_material_unknown_and_premature_handoff() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    required_terms = fixture["required_good_terms"]

    for name, bad_transcript in fixture["bad_transcripts"].items():
        results = _grade_transcript(bad_transcript, fixture)
        assert not all(results.values()), (name, results, required_terms)


def test_discussion_behavior_prompt_contains_fixture_guardrails() -> None:
    content = "\n".join(
        [
            (ROOT / "templates" / "commands" / "discussion.md").read_text(encoding="utf-8"),
            (
                ROOT
                / "templates"
                / "command-references"
                / "discussion"
                / "handoff-contract.md"
            ).read_text(encoding="utf-8"),
            (
                ROOT
                / "templates"
                / "command-references"
                / "discussion"
                / "handoff-review-and-repair.md"
            ).read_text(encoding="utf-8"),
            (
                ROOT
                / "templates"
                / "advanced-skills"
                / "spx-discussion"
                / "references"
                / "discussion-contract.md"
            ).read_text(encoding="utf-8"),
        ]
    ).lower()

    for required in (
        "source_materials",
        "mat-###",
        "material coverage",
        "unknowns/conflicts",
        "latest_checkpoint.snapshot_sha256",
        "missing_semantic_checkpoint",
        "agent_requirement_contract",
        "discussion_snapshot_digest",
    ):
        assert required in content


def test_discussion_consumers_require_v5_snapshot_and_material_coverage() -> None:
    paths = [
        ROOT / "templates" / "command-references" / "quick" / "handoff-consumption.md",
        ROOT / "templates" / "command-references" / "specify" / "discussion-handoff-validation.md",
        ROOT / "templates" / "advanced-skills" / "spx-quick" / "SKILL.md",
        ROOT / "templates" / "advanced-skills" / "spx-specify" / "references" / "discussion-handoff.md",
    ]

    for path in paths:
        content = path.read_text(encoding="utf-8").lower()
        assert "v5" in content or "version: 5" in content, path
        assert "discussion_snapshot_digest" in content, path
        assert "source material" in content or "source_materials" in content, path
        assert "source_evidence.material_id" in content, path
