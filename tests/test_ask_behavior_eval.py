import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = PROJECT_ROOT / "tests" / "fixtures" / "ask_behavior" / "same_topic_zip_protocol.json"


def _load_eval_case() -> dict:
    return json.loads(EVAL_PATH.read_text(encoding="utf-8"))


def _as_text(lines: list[str]) -> str:
    return "\n".join(lines)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def _has_all(text: str, terms: list[str]) -> bool:
    normalized = _normalize(text)
    return all(term.lower() in normalized for term in terms)


def _grade_answer(answer: str, case: dict) -> dict[str, bool]:
    grader = case["grader"]
    route_text = answer.split("已证明", 1)[0]
    normalized = _normalize(answer)

    return {
        "route_before_proof": _has_all(route_text, grader["required_route_terms"]),
        "same_topic_reuse": _has_all(answer, grader["required_reuse_terms"]),
        "alias_normalization": _has_all(answer, grader["required_user_terms"])
        and _has_all(answer, grader["required_project_terms"]),
        "proof_layers": _has_all(answer, grader["required_sections"]),
        "protocol_boundary": _has_all(answer, grader["required_protocol_terms"]),
        "no_unqualified_hard_claims": not any(
            forbidden.lower() in normalized for forbidden in grader["forbidden_terms"]
        ),
    }


def test_sp_ask_followup_protocol_behavior_eval_passes_good_transcript() -> None:
    case = _load_eval_case()

    results = _grade_answer(_as_text(case["good_transcript"]), case)

    assert all(results.values()), results


def test_sp_ask_followup_protocol_behavior_eval_rejects_bad_transcript() -> None:
    case = _load_eval_case()

    results = _grade_answer(_as_text(case["bad_transcript"]), case)

    assert not all(results.values())
    assert results["no_unqualified_hard_claims"] is False
    assert results["proof_layers"] is False
    assert results["same_topic_reuse"] is False


def test_sp_ask_prompt_covers_followup_protocol_eval_anchors() -> None:
    case = _load_eval_case()
    prompt = (
        PROJECT_ROOT / "templates" / "command-partials" / "ask" / "shell.md"
    ).read_text(encoding="utf-8")
    normalized_prompt = _normalize(prompt)

    missing = [
        anchor
        for anchor in case["prompt_contract_anchors"]
        if anchor.lower() not in normalized_prompt
    ]

    assert missing == []
