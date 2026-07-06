from specify_cli.artifacts import (
    ARTIFACT_REGISTRY,
    audit_fixed_cost,
    get_artifact_kind,
    validate_registry,
)


def test_registry_contains_first_rollout_kinds():
    assert set(ARTIFACT_REGISTRY) == {"quick-status", "plan-contract"}

    quick_status = get_artifact_kind("quick-status")
    assert quick_status.workflow == "sp-quick"
    assert quick_status.allowed_output_paths == (".planning/quick/*/STATUS.md",)
    assert "current_focus" in quick_status.agent_fill_required
    assert quick_status.fill_targets["current_focus"]["anchor"] == (
        "agent-fill:current_focus"
    )

    plan_contract = get_artifact_kind("plan-contract")
    assert plan_contract.workflow == "sp-plan"
    assert plan_contract.allowed_output_paths == (
        "specs/*/plan-contract.json",
        ".specify/features/*/plan-contract.json",
    )
    assert plan_contract.validator == "json"


def test_validate_registry_reports_no_errors_for_first_rollout():
    assert validate_registry() == []


def test_audit_reports_fixed_savings_and_registry_metadata():
    audit = audit_fixed_cost()

    assert audit["status"] == "ok"
    assert audit["candidate_count"] == 2

    candidates = {candidate["kind"]: candidate for candidate in audit["candidates"]}

    quick_status = candidates["quick-status"]
    assert quick_status["recommendation"] == "scaffold"
    assert quick_status["fixed_bytes"] > 1000
    assert quick_status["estimated_token_savings"] == quick_status["fixed_bytes"] // 4
    assert quick_status["quality_risk"] == "low"
    assert quick_status["fill_targets"]["current_focus"]["type"] == "markdown_anchor"

    plan_contract = candidates["plan-contract"]
    assert plan_contract["recommendation"] == "builder"
    assert plan_contract["fixed_bytes"] > 500
    assert plan_contract["downstream_consumers"] == ["sp-tasks", "sp-analyze"]
