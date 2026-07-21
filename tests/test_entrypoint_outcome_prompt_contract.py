from pathlib import Path


ROOT = Path(__file__).parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _assert_contains_all(relative_path: str, *terms: str) -> None:
    content = _read(relative_path).lower()
    for term in terms:
        assert term.lower() in content, f"{relative_path} is missing {term!r}"


def test_classic_specify_discovers_live_entrypoint_outcomes_without_archive_authority() -> (
    None
):
    _assert_contains_all(
        "templates/command-partials/common/senior-consequence-analysis-gate.md",
        "new or changed entry point",
        "result/error definitions",
        "existing consumers",
        "entrypoint_outcome_contract",
    )
    _assert_contains_all(
        "templates/command-references/specify/semantic-traceability.md",
        "entrypoint_outcome_contract",
        "recoverable-user-input",
        "inventory_evidence_refs",
        "outcome_dispositions",
        "learning_context",
        "learning_candidate_refs",
        "learning_dispositions",
        "spec-contract.json#/acceptance_criteria/N",
        "archived specifications",
        "lineage or provenance",
        "current live evidence",
    )
    _assert_contains_all(
        "templates/command-references/specify/self-review-and-quality-gates.md",
        "planning-ready",
        "entrypoint_outcome_contract",
        "zero uncovered",
        "zero undisposed Learning candidates",
    )


def test_classic_plan_tasks_reuse_existing_consequence_and_review_chain() -> None:
    _assert_contains_all(
        "templates/command-references/plan/plan-contract-fields.md",
        "operational_consequence_decisions",
        "producer_result_ref",
        "consumer_owner",
        "interaction_policy",
        "request_retention",
        "retry_identity",
        "cancel_behavior",
    )
    _assert_contains_all(
        "templates/command-references/tasks/must-preserve-ledger.md",
        "entrypoint outcome",
        "consequence_obligation_ids",
        "review_obligations",
        "system_review_scenarios",
    )


def test_classic_implement_and_review_use_stage_specific_gap_routing() -> None:
    for path in (
        "templates/command-references/implement/join-point-review.md",
        "templates/command-references/review/repair-and-revalidation.md",
    ):
        _assert_contains_all(
            path,
            "implementation_gap",
            "traceability_gap",
            "upstream_truth_gap",
        )
    _assert_contains_all(
        "templates/command-references/implement/join-point-review.md",
        "reopen the owning upstream workflow",
    )
    _assert_contains_all(
        "templates/command-references/review/repair-and-revalidation.md",
        "remain in Review",
        "Only a proven",
    )


def test_advanced_profile_preserves_the_same_outcome_contract() -> None:
    _assert_contains_all(
        "templates/advanced-skills/_shared/consequence-gate.md",
        "new or changed entry point",
        "result/error definitions",
        "entrypoint_outcome_contract",
    )
    _assert_contains_all(
        "templates/advanced-skills/spx-specify/references/requirements-contract.md",
        "entrypoint_outcome_contract",
        "recoverable-user-input",
        "archived specifications",
        "lineage or provenance",
        "current live evidence",
        "learning_context",
        "learning_candidate_refs",
        "learning_dispositions",
        "spec-contract.json#/acceptance_criteria/N",
    )
    _assert_contains_all(
        "templates/advanced-skills/spx-plan/references/planning-contract.md",
        "operational_consequence_decisions",
        "producer_result_ref",
        "request_retention",
        "retry_identity",
    )
    _assert_contains_all(
        "templates/advanced-skills/spx-tasks/references/task-graph-contract.md",
        "entrypoint outcome",
        "review_obligations",
        "system_review_scenarios",
    )
    for path in (
        "templates/advanced-skills/spx-implement/references/execution-contract.md",
        "templates/advanced-skills/spx-review/references/review-contract.md",
    ):
        _assert_contains_all(
            path,
            "implementation_gap",
            "traceability_gap",
            "upstream_truth_gap",
        )


def test_project_facing_spec_and_plan_render_outcome_dispositions() -> None:
    for path in (
        "templates/spec-template.md",
        "templates/advanced-skills/spx-specify/assets/spec.md",
    ):
        _assert_contains_all(
            path,
            "Entrypoint Outcome Dispositions",
            "Contextual Learning Dispositions",
            "Learning ref",
            "CA-###",
        )
    for path in (
        "templates/plan-template.md",
        "templates/advanced-skills/spx-plan/assets/plan.md",
    ):
        _assert_contains_all(
            path,
            "Operational Entrypoint Outcome Design",
            "request retention",
            "retry identity",
            "cancel behavior",
        )


def test_learning_guidance_runs_contextual_recall_from_live_owners() -> None:
    for path in (
        "templates/command-partials/common/learning-layer.md",
        "templates/advanced-skills/_shared/project-learning.md",
        "templates/passive-skills/spec-kit-project-learning/SKILL.md",
    ):
        _assert_contains_all(
            path,
            "--context operation_owner=",
            "consumer_owner",
            "current code",
            "tests",
            "archived specifications",
            "do not auto-apply",
            "applied",
            "not_applicable",
            "deferred",
            "silently ignore",
        )


def test_default_context_loading_denies_archived_spec_authority() -> None:
    for path in (
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/advanced-skills/_shared/project-cognition.md",
    ):
        _assert_contains_all(
            path,
            "archived specifications",
            "excluded from default discovery",
            "lineage or provenance",
            "current live evidence",
        )
