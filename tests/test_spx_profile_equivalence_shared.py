import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCED_SKILLS = PROJECT_ROOT / "templates" / "advanced-skills"


def test_advanced_profile_optimizes_expression_not_classic_workflow_semantics() -> None:
    surface_map = json.loads(
        (ADVANCED_SKILLS / "_shared" / "surface-map.json").read_text(
            encoding="utf-8"
        )
    )
    policy = " ".join(surface_map["optimization_policy"]).lower()

    assert "no hard word or token ceiling" in policy
    assert "triggered outputs" in policy
    assert "state ownership" in policy
    assert "resume" in policy
    assert "failure recovery" in policy
    assert "implementation strategy" in policy


def test_advanced_profile_has_no_hard_prompt_length_limits() -> None:
    forbidden = re.compile(
        r"(?:under|at most|maximum|max)\s+\d+\s+(?:words?|tokens?)"
        r"|\b\d+[- ](?:word|token)\s+(?:limit|budget|maximum)",
        re.IGNORECASE,
    )

    violations = []
    for path in ADVANCED_SKILLS.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".json", ".yaml"}:
            continue
        if forbidden.search(path.read_text(encoding="utf-8")):
            violations.append(path.relative_to(PROJECT_ROOT).as_posix())

    assert violations == []


def test_advanced_profile_budget_policy_is_user_visible() -> None:
    for relative in ("README.md", "PROJECT-HANDBOOK.md", "AGENTS.md"):
        content = " ".join(
            (PROJECT_ROOT / relative).read_text(encoding="utf-8").lower().split()
        )
        assert "no hard word or token ceiling" in content, relative


def test_advanced_cognition_reference_preserves_semantic_claim_gates_compactly() -> None:
    cognition = " ".join(
        (ADVANCED_SKILLS / "_shared" / "project-cognition.md")
        .read_text(encoding="utf-8")
        .lower()
        .split()
    )

    for required in (
        "semantic-audit --input",
        "semantic-audit-resume --input",
        "semantic-audit-input.json",
        "semantic-audit-output.json",
        "workflow_authorization",
        "claim-specific passed verification",
        "claim_ready",
        "does not authorize source edits",
    ):
        assert required in cognition

    assert "missing, stale, or inconsistent" in cognition
    assert "keep the final claim blocked" in cognition


def test_advanced_shared_contract_keeps_state_and_delegation_ownership() -> None:
    cognition = " ".join(
        (ADVANCED_SKILLS / "_shared" / "project-cognition.md")
        .read_text(encoding="utf-8")
        .lower()
        .split()
    )

    assert "create or resume it before substantive work" in cognition
    assert "delegation remains optional" in cognition
    assert "leader owns canonical artifacts" in cognition
    assert "worker results are evidence" in cognition
    assert "validate every join" in cognition
    assert "do not duplicate runtime events" in cognition
