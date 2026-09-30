"""Scenario-first source contracts for both independently authored profiles."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROFILES = [ROOT / "templates/commands/e2e.md", ROOT / "templates/advanced-skills/spx-e2e/SKILL.md"]


@pytest.mark.parametrize("path", PROFILES)
def test_both_profiles_design_before_optional_automation(path):
    body = path.read_text(encoding="utf-8").lower()
    assert body.index("e2e_scenarios.py check") < body.index("e2e_coverage.py plan")
    for requirement in ("desktop", "mobile", "visual-model", "error guessing", "boundary value",
                        "event-sequence", "assumptions", "checkpoints", "independent", "cleanup",
                        "planning-only", "oracle gap", "book_sha256", "e2e_scenarios.py schema"):
        assert requirement in body, (path, requirement)


@pytest.mark.parametrize("path", PROFILES)
def test_client_visual_execution_does_not_require_an_automation_harness(path):
    body = path.read_text(encoding="utf-8").lower()
    assert "e2e_scenarios.py audit" in body
    assert "screenshot is not proof" in body or "screenshot is visual evidence, not" in body
    assert "blocked" in body and "readback" in body
    assert "not_run" in body and "flaky" in body
    assert "pending-human-review" in body
    assert "not attestation" in body or "not an assertion that the model" in body
    assert "cannot override a failed native audit" in body


def test_advanced_design_reference_is_local_and_explicitly_loaded():
    skill = PROFILES[1]
    body = skill.read_text(encoding="utf-8")
    assert "Read `references/scenario-design.md` before authoring" in body
    reference = (skill.parent / "references/scenario-design.md").read_text(encoding="utf-8")
    assert "not-applicable" in reference
    assert "event/checkpoint" in reference
    assert "TOCTOU" in reference
