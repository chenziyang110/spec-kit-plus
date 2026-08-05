import json
from pathlib import Path

import pytest

from specify_cli.learning_policy import parse_learning_policy
from specify_cli.learnings import build_learning_entry, sanitize_agent_text


FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "project_learning_assessment_v1.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "case",
    FIXTURE["text_cases"],
    ids=lambda case: case["id"],
)
def test_python_learning_redaction_matches_shared_contract(
    case: dict[str, object],
) -> None:
    policy = parse_learning_policy(case.get("policy") or {})

    sanitized, labels = sanitize_agent_text(str(case["input"]), policy=policy)

    assert labels == case["expected_labels"]
    if "expected_output" in case:
        assert sanitized == case["expected_output"]
    assert all(value in sanitized for value in case["expected_contains"])
    assert all(value not in sanitized for value in case["forbidden_contains"])


@pytest.mark.parametrize(
    "case",
    FIXTURE["assessment_cases"],
    ids=lambda case: case["id"],
)
def test_python_learning_assessment_matches_shared_contract(
    case: dict[str, object],
) -> None:
    policy = parse_learning_policy(case.get("policy") or {})

    entry = build_learning_entry(
        command_name="debug",
        learning_type=str(case["learning_type"]),
        summary=str(case["summary"]),
        evidence=str(case["evidence"]),
        signal_strength=str(case["signal_strength"]),
        recommended_action=str(case["recommended_action"]),
        trigger_signals=case["trigger_signals"],
        assessment_source=str(case["source"]),
        assessment_occurrences=int(case["occurrences"]),
        policy=policy,
    )

    assert entry.learning_value_tier == case["expected_value_tier"]
    assert entry.learning_value_reason_codes == case["expected_reason_codes"]
    assert entry.assessment_decision == case["expected_decision"]
    assert entry.assessment_payload() is not None
