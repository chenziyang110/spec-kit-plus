import json
from pathlib import Path

import pytest

from specify_cli.hooks import artifact_validation


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _triggered_spec_contract() -> dict[str, object]:
    return {
        "acceptance_criteria": [
            "The Finder request completes successfully.",
            "A password-required result remains recoverable through retry or cancel.",
        ],
        "entrypoint_outcome_contract": {
            "triggered": True,
            "trigger_reasons": ["new-entrypoint-over-existing-operation"],
            "inventory_complete": True,
            "inventory_evidence_refs": [
                "src/archive/extract_result.py",
                "src/app/existing_extract_consumer.py",
                "tests/integration/test_existing_extract.py",
            ],
            "learning_context": {
                "operation_owners": ["ArchiveExtractor"],
                "consumer_owners": ["FinderRequestCoordinator"],
                "outcomes": ["password-required"],
            },
            "learning_search_refs": [
                "learning list --command specify --context operation_owner=ArchiveExtractor"
            ],
            "learning_candidate_refs": ["archive.password-bridge"],
            "learning_dispositions": [
                {
                    "learning_ref": "archive.password-bridge",
                    "disposition": "applied",
                    "match_basis": ["operation_owner", "recoverable outcome"],
                    "rationale": "The existing recovery lesson applies to the reused operation.",
                    "requirement_refs": [
                        "spec-contract.json#/acceptance_criteria/1"
                    ],
                    "consequence_refs": ["CA-002"],
                    "evidence_refs": ["src/app/existing_extract_consumer.py"],
                    "deferral_ref": None,
                }
            ],
            "result_inventory": [
                {
                    "outcome_id": "OUT-SUCCESS",
                    "entrypoint_id": "EP-FINDER",
                    "operation": "extract",
                    "result_family": "success",
                    "classification": "terminal-success",
                    "reachable": True,
                    "material": True,
                    "evidence_refs": ["src/archive/extract_result.py#success"],
                },
                {
                    "outcome_id": "OUT-PASSWORD",
                    "entrypoint_id": "EP-FINDER",
                    "operation": "extract",
                    "result_family": "password-required",
                    "classification": "recoverable-user-input",
                    "reachable": True,
                    "material": True,
                    "evidence_refs": [
                        "src/archive/extract_result.py#password-required"
                    ],
                },
            ],
            "outcome_dispositions": [
                {
                    "outcome_id": "OUT-SUCCESS",
                    "disposition": "preserve",
                    "observable_behavior": "The Finder request completes successfully.",
                    "acceptance_refs": [
                        "spec-contract.json#/acceptance_criteria/0"
                    ],
                    "consequence_refs": ["CA-001"],
                    "rationale": "Preserve the existing successful extraction behavior.",
                    "deferral_ref": None,
                },
                {
                    "outcome_id": "OUT-PASSWORD",
                    "disposition": "adapt",
                    "observable_behavior": (
                        "The request remains recoverable while the user supplies a password."
                    ),
                    "acceptance_refs": [
                        "spec-contract.json#/acceptance_criteria/1"
                    ],
                    "consequence_refs": ["CA-002"],
                    "rationale": "The background entrypoint must escalate required interaction.",
                    "deferral_ref": None,
                },
            ],
        }
    }


def _triggered_plan_contract() -> dict[str, object]:
    return {
        "consequence_gate": {
            "triggered": True,
            "trigger_reason": "A new entrypoint reuses an existing operation.",
            "status": "ready",
            "stand_down_reason": None,
        },
        "consequence_analysis": {
            "affected_object_map": [
                {"object": "Finder request", "reason": "It survives recovery."}
            ],
            "state_behavior_matrix": [
                {"state": "awaiting-user-input", "behavior": "Retain the request."}
            ],
            "dependency_impact": [
                {"surface": "password prompt", "impact": "The host must activate."}
            ],
            "recovery_and_validation": [
                {"validation": "Exercise success and password-required outcomes."}
            ],
            "coverage_gaps": [{"gap": "none", "decision": "Both outcomes mapped."}],
        },
        "consequence_obligations": [
            {
                "obligation_id": "CA-001",
                "claim": "Preserve successful Finder extraction.",
                "affected_objects": ["Finder request"],
                "owner": "sp-plan",
                "latest_resolve_phase": "plan",
                "status": "open",
                "stop_and_reopen_condition": "Success has no executable design.",
            },
            {
                "obligation_id": "CA-002",
                "claim": "Escalate password-required extraction to recoverable input.",
                "affected_objects": ["Finder request", "password prompt"],
                "owner": "sp-plan",
                "latest_resolve_phase": "plan",
                "status": "open",
                "stop_and_reopen_condition": "Recovery semantics are incomplete.",
            },
        ],
        "operational_consequence_decisions": [
            {
                "decision_id": "OCD-001",
                "consequence_obligation_ids": ["CA-001"],
                "decision": "Route successful extraction to the terminal response.",
                "producer_result_ref": "ArchiveExtractor.Result.success",
                "consumer_owner": "FinderRequestCoordinator",
                "state_transition": "running -> completed",
                "interaction_owner": "FinderRequestCoordinator",
                "interaction_policy": "No interaction is needed for terminal success.",
                "request_retention": "Retain the request through terminal completion.",
                "retry_identity": "Not applicable for terminal success.",
                "cancel_behavior": "Not applicable after terminal completion.",
                "validation_refs": [
                    "tests/integration/test_finder_extract.py::test_success"
                ],
            },
            {
                "decision_id": "OCD-002",
                "consequence_obligation_ids": ["CA-002"],
                "decision": "Retain the request while collecting and retrying a password.",
                "producer_result_ref": "ArchiveExtractor.Result.passwordRequired",
                "consumer_owner": "FinderRequestCoordinator",
                "state_transition": "running -> awaiting-user-input -> retrying",
                "interaction_owner": "Application password prompt",
                "interaction_policy": "Reveal and activate the host window",
                "request_retention": "Retain request identity and destination",
                "retry_identity": "Retry the same request UUID",
                "cancel_behavior": "Cancel the retained request without extraction",
                "security_constraints": [
                    "Do not persist or log the plaintext password"
                ],
                "validation_refs": [
                    "tests/integration/test_finder_extract.py::test_password_prompt"
                ],
            },
        ],
    }


def _triggered_task_index() -> dict[str, object]:
    return {
        "official_entrypoints": [
            {
                "id": "EP-FINDER",
                "command": "Use Finder's Extract context-menu action",
                "ready_signal": "The host application can receive the request",
            }
        ],
        "tasks": [
            {"task_id": "T001", "consequence_obligation_ids": ["CA-001"]},
            {"task_id": "T002", "consequence_obligation_ids": ["CA-002"]},
        ],
        "consequence_obligation_refs": ["CA-001", "CA-002"],
        "system_review_scenarios": [
            {
                "id": "SR-SUCCESS",
                "kind": "interaction",
                "title": "Extract an unencrypted archive from Finder",
                "required": True,
                "entrypoint_id": "EP-FINDER",
                "preconditions": ["An unencrypted archive exists."],
                "actions": ["Invoke Extract from Finder."],
                "expected_results": ["Extraction completes."],
                "required_evidence": ["runtime_diagnostics"],
            },
            {
                "id": "SR-PASSWORD",
                "kind": "interaction",
                "title": "Recover an encrypted archive from Finder",
                "required": True,
                "entrypoint_id": "EP-FINDER",
                "preconditions": ["An encrypted archive exists."],
                "actions": ["Invoke Extract and enter the password."],
                "expected_results": ["The prompt appears and extraction retries."],
                "required_evidence": ["runtime_diagnostics", "visual_capture"],
            },
        ],
        "review_obligations": [
            {
                "id": "RO-SUCCESS",
                "kind": "consequence",
                "source_ref": "CA-001",
                "surface": "Finder successful extraction",
                "required": True,
                "scenario_ids": ["SR-SUCCESS"],
                "consequence_obligation_ids": ["CA-001"],
            },
            {
                "id": "RO-PASSWORD",
                "kind": "consequence",
                "source_ref": "CA-002",
                "surface": "Finder password recovery",
                "required": True,
                "scenario_ids": ["SR-PASSWORD"],
                "consequence_obligation_ids": ["CA-002"],
            },
        ],
    }


def _write_triggered_contract_chain(feature_dir: Path) -> None:
    _write_json(feature_dir / "spec-contract.json", _triggered_spec_contract())
    _write_json(feature_dir / "plan-contract.json", _triggered_plan_contract())
    _write_json(feature_dir / "task-index.json", _triggered_task_index())


def test_spec_blocks_material_reachable_outcome_without_disposition(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "001-outcome-gap"
    payload = _triggered_spec_contract()
    contract = payload["entrypoint_outcome_contract"]
    assert isinstance(contract, dict)
    dispositions = contract["outcome_dispositions"]
    assert isinstance(dispositions, list)
    contract["outcome_dispositions"] = [dispositions[0]]
    _write_json(feature_dir / "spec-contract.json", payload)

    errors = artifact_validation._validate_spec_entrypoint_outcome_contract(feature_dir)

    assert any(
        "OUT-PASSWORD" in error and "disposition" in error.lower() for error in errors
    )


@pytest.mark.parametrize(
    ("artifact", "field"),
    [
        ("spec", "acceptance_refs"),
        ("spec", "consequence_refs"),
        ("plan", "interaction_policy"),
        ("plan", "request_retention"),
        ("plan", "cancel_behavior"),
    ],
)
def test_recoverable_user_input_requires_recovery_and_acceptance_contract(
    tmp_path: Path, artifact: str, field: str
) -> None:
    feature_dir = tmp_path / "specs" / f"002-recoverable-{artifact}-{field}"
    spec = _triggered_spec_contract()
    plan = _triggered_plan_contract()
    if artifact == "spec":
        contract = spec["entrypoint_outcome_contract"]
        assert isinstance(contract, dict)
        dispositions = contract["outcome_dispositions"]
        assert isinstance(dispositions, list)
        password_disposition = dispositions[1]
        assert isinstance(password_disposition, dict)
        password_disposition[field] = []
    else:
        decisions = plan["operational_consequence_decisions"]
        assert isinstance(decisions, list)
        password_decision = decisions[1]
        assert isinstance(password_decision, dict)
        password_decision.pop(field)
    _write_json(feature_dir / "spec-contract.json", spec)
    _write_json(feature_dir / "plan-contract.json", plan)

    validator = (
        artifact_validation._validate_spec_entrypoint_outcome_contract
        if artifact == "spec"
        else artifact_validation._validate_plan_entrypoint_outcome_contract
    )
    errors = validator(feature_dir)

    assert any("OUT-PASSWORD" in error and field in error for error in errors)


def test_complete_triggered_spec_outcome_contract_is_valid(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "003-complete-spec"
    _write_json(feature_dir / "spec-contract.json", _triggered_spec_contract())

    assert (
        artifact_validation._validate_spec_entrypoint_outcome_contract(feature_dir)
        == []
    )


def test_spec_requires_disposition_for_each_contextual_learning_candidate(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "003-learning-disposition"
    payload = _triggered_spec_contract()
    contract = payload["entrypoint_outcome_contract"]
    assert isinstance(contract, dict)
    contract["learning_dispositions"] = []
    _write_json(feature_dir / "spec-contract.json", payload)

    errors = artifact_validation._validate_spec_entrypoint_outcome_contract(feature_dir)

    assert any(
        "archive.password-bridge" in error and "learning" in error.lower()
        for error in errors
    )


def test_plan_does_not_require_operational_design_when_no_outcome_is_active(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "003-no-active-outcomes"
    payload = _triggered_spec_contract()
    contract = payload["entrypoint_outcome_contract"]
    assert isinstance(contract, dict)
    inventory = contract["result_inventory"]
    dispositions = contract["outcome_dispositions"]
    assert isinstance(inventory, list)
    assert isinstance(dispositions, list)
    for item in inventory:
        assert isinstance(item, dict)
        item["reachable"] = False
        item["material"] = False
    for item in dispositions:
        assert isinstance(item, dict)
        item.update(
            {
                "disposition": "not_applicable",
                "evidence_refs": ["src/archive/extract_result.py"],
            }
        )
    _write_json(feature_dir / "spec-contract.json", payload)
    _write_json(
        feature_dir / "plan-contract.json",
        {
            "consequence_obligations": [],
            "operational_consequence_decisions": [],
        },
    )

    assert (
        artifact_validation._validate_plan_entrypoint_outcome_contract(feature_dir)
        == []
    )


@pytest.mark.parametrize(
    ("mutate", "expected_terms"),
    [
        (
            lambda contract: contract.update({"learning_context": {}}),
            ("learning_context", "non-empty"),
        ),
        (
            lambda contract: contract.update({"learning_search_refs": []}),
            ("learning_search_refs", "non-empty"),
        ),
        (
            lambda contract: contract["learning_dispositions"][0].update(
                {"requirement_refs": [], "consequence_refs": []}
            ),
            ("archive.password-bridge", "requirement", "consequence"),
        ),
        (
            lambda contract: contract["learning_dispositions"][0].update(
                {
                    "disposition": "not_applicable",
                    "evidence_refs": [],
                }
            ),
            ("archive.password-bridge", "evidence_refs"),
        ),
        (
            lambda contract: contract["learning_dispositions"][0].update(
                {"disposition": "deferred", "deferral_ref": None}
            ),
            ("archive.password-bridge", "deferral_ref"),
        ),
    ],
)
def test_spec_validates_contextual_learning_disposition_rules(
    tmp_path: Path,
    mutate: object,
    expected_terms: tuple[str, ...],
) -> None:
    feature_dir = tmp_path / "specs" / "003-learning-rules"
    payload = _triggered_spec_contract()
    contract = payload["entrypoint_outcome_contract"]
    assert isinstance(contract, dict)
    assert callable(mutate)
    mutate(contract)
    _write_json(feature_dir / "spec-contract.json", payload)

    errors = artifact_validation._validate_spec_entrypoint_outcome_contract(feature_dir)

    assert any(all(term in error for term in expected_terms) for error in errors)


def test_spec_rejects_learning_disposition_for_unknown_candidate(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "003-learning-unknown"
    payload = _triggered_spec_contract()
    contract = payload["entrypoint_outcome_contract"]
    assert isinstance(contract, dict)
    dispositions = contract["learning_dispositions"]
    assert isinstance(dispositions, list)
    dispositions.append(
        {
            "learning_ref": "archive.unrelated-lesson",
            "disposition": "not_applicable",
            "match_basis": ["manual search"],
            "rationale": "This candidate does not concern extraction.",
            "requirement_refs": [],
            "consequence_refs": [],
            "evidence_refs": ["src/archive/extract_result.py"],
            "deferral_ref": None,
        }
    )
    _write_json(feature_dir / "spec-contract.json", payload)

    errors = artifact_validation._validate_spec_entrypoint_outcome_contract(feature_dir)

    assert any(
        "archive.unrelated-lesson" in error and "unknown" in error
        for error in errors
    )


def test_complete_triggered_outcome_contract_chain_is_valid(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "004-complete-chain"
    _write_triggered_contract_chain(feature_dir)

    assert (
        artifact_validation._validate_plan_entrypoint_outcome_contract(feature_dir)
        == []
    )
    assert (
        artifact_validation._validate_tasks_entrypoint_outcome_contract(feature_dir)
        == []
    )


@pytest.mark.parametrize(
    ("mutation", "expected_fragment"),
    [
        ("omit-outcome", "OUT-PASSWORD"),
        ("missing-owner", "consumer_owner"),
        ("missing-retry-policy", "retry_identity"),
    ],
)
def test_plan_covers_active_spec_outcomes_with_technical_strategy(
    tmp_path: Path, mutation: str, expected_fragment: str
) -> None:
    feature_dir = tmp_path / "specs" / f"004-plan-{mutation}"
    spec = _triggered_spec_contract()
    plan = _triggered_plan_contract()
    decisions = plan["operational_consequence_decisions"]
    assert isinstance(decisions, list)
    if mutation == "omit-outcome":
        plan["operational_consequence_decisions"] = [decisions[0]]
    elif mutation == "missing-owner":
        assert isinstance(decisions[0], dict)
        decisions[0].pop("consumer_owner")
    else:
        assert isinstance(decisions[1], dict)
        decisions[1].pop("retry_identity")
    _write_json(feature_dir / "spec-contract.json", spec)
    _write_json(feature_dir / "plan-contract.json", plan)

    errors = artifact_validation._validate_plan_entrypoint_outcome_contract(feature_dir)

    assert any(expected_fragment in error for error in errors)


@pytest.mark.parametrize(
    ("mutation", "expected_fragment"),
    [
        ("missing-task", "CA-002"),
        ("missing-review", "CA-002"),
        ("unknown-review", "SR-UNKNOWN"),
    ],
)
def test_task_index_maps_each_plan_outcome_to_tasks_and_system_review(
    tmp_path: Path, mutation: str, expected_fragment: str
) -> None:
    feature_dir = tmp_path / "specs" / f"005-tasks-{mutation}"
    _write_triggered_contract_chain(feature_dir)
    task_index = _triggered_task_index()
    tasks = task_index["tasks"]
    review_obligations = task_index["review_obligations"]
    assert isinstance(tasks, list)
    assert isinstance(review_obligations, list)
    if mutation == "missing-task":
        task_index["tasks"] = [tasks[0]]
    elif mutation == "missing-review":
        task_index["review_obligations"] = [review_obligations[0]]
    else:
        password_review = review_obligations[1]
        assert isinstance(password_review, dict)
        password_review["scenario_ids"] = ["SR-UNKNOWN"]
    _write_json(feature_dir / "task-index.json", task_index)

    errors = artifact_validation._validate_tasks_entrypoint_outcome_contract(
        feature_dir
    )

    assert any(expected_fragment in error for error in errors)


def test_untriggered_contract_requires_only_an_explicit_stand_down(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "006-untriggered"
    _write_json(
        feature_dir / "spec-contract.json",
        {
            "entrypoint_outcome_contract": {
                "triggered": False,
                "stand_down_reason": (
                    "No entrypoint, reused operation, or consumer ownership changed."
                ),
            }
        },
    )
    _write_json(
        feature_dir / "plan-contract.json",
        {},
    )
    _write_json(
        feature_dir / "task-index.json",
        {
            "tasks": [],
            "system_review_scenarios": [],
            "review_obligations": [],
        },
    )

    assert (
        artifact_validation._validate_spec_entrypoint_outcome_contract(feature_dir)
        == []
    )
    assert (
        artifact_validation._validate_plan_entrypoint_outcome_contract(feature_dir)
        == []
    )
    assert (
        artifact_validation._validate_tasks_entrypoint_outcome_contract(feature_dir)
        == []
    )


def test_specify_planning_ready_contract_requires_explicit_outcome_gate(
    tmp_path: Path,
) -> None:
    feature_dir = tmp_path / "specs" / "007-missing-outcome-gate"
    template_path = (
        Path(__file__).parents[2] / "templates" / "spec-contract-template.json"
    )
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    payload.pop("entrypoint_outcome_contract", None)
    payload["status"] = "planning-ready"
    payload["target_need"] = "Deliver a verifiable behavior."
    payload["acceptance_criteria"] = ["The behavior is verifiable."]
    _write_json(feature_dir / "spec-contract.json", payload)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

    errors = artifact_validation._validate_spec_contract_artifacts(feature_dir)

    assert any("entrypoint_outcome_contract" in error for error in errors)


@pytest.mark.parametrize(
    ("command_name", "validator_name", "other_validators"),
    [
        (
            "plan",
            "_validate_plan_entrypoint_outcome_contract",
            (
                "_validate_plan_consumes_deep_research",
                "_validate_plan_consequence_contract",
                "_validate_plan_ui_contract",
                "_validate_plan_human_acceptance_contract",
            ),
        ),
        (
            "tasks",
            "_validate_tasks_entrypoint_outcome_contract",
            (
                "_validate_tasks_consequence_contract",
                "_validate_tasks_ui_contract",
                "_validate_tasks_human_acceptance_contract",
            ),
        ),
    ],
)
def test_artifact_hook_runs_entrypoint_outcome_continuity_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command_name: str,
    validator_name: str,
    other_validators: tuple[str, ...],
) -> None:
    feature_dir = tmp_path / "specs" / f"008-{command_name}-hook"
    feature_dir.mkdir(parents=True)
    (feature_dir / f"{command_name}.md").write_text(
        f"# {command_name}\n", encoding="utf-8"
    )
    (feature_dir / "workflow-state.md").write_text(
        "# Workflow State\n", encoding="utf-8"
    )
    if command_name == "plan":
        _write_json(feature_dir / "plan-contract.json", {})
    sentinel = f"{command_name} entrypoint outcome sentinel"
    monkeypatch.setattr(
        artifact_validation,
        validator_name,
        lambda _feature_dir: [sentinel],
    )
    for other_validator in other_validators:
        monkeypatch.setattr(
            artifact_validation,
            other_validator,
            lambda _feature_dir: [],
        )

    result = artifact_validation.validate_artifacts_hook(
        tmp_path,
        {"command_name": command_name, "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert sentinel in result.errors


def test_machine_templates_seed_one_outcome_gate_and_reuse_consequence_chain() -> None:
    template_dir = Path(__file__).parents[2] / "templates"
    spec_contract = json.loads(
        (template_dir / "spec-contract-template.json").read_text(encoding="utf-8")
    )
    plan_contract = json.loads(
        (template_dir / "plan-contract-template.json").read_text(encoding="utf-8")
    )
    task_index = json.loads(
        (template_dir / "task-index-template.json").read_text(encoding="utf-8")
    )

    assert spec_contract["entrypoint_outcome_contract"] == {
        "triggered": False,
        "trigger_reasons": [],
        "stand_down_reason": None,
        "inventory_complete": False,
        "inventory_evidence_refs": [],
        "learning_context": {},
        "learning_search_refs": [],
        "learning_candidate_refs": [],
        "learning_dispositions": [],
        "result_inventory": [],
        "outcome_dispositions": [],
    }
    assert "consequence_gate" in plan_contract
    assert "consequence_analysis" in plan_contract
    assert plan_contract["consequence_obligations"] == []
    assert plan_contract["operational_consequence_decisions"] == []
    assert "entrypoint_outcome_contract" not in plan_contract
    assert "entrypoint_outcome_contract" not in task_index
    assert "consequence_obligation_refs" in task_index
    assert "review_obligations" in task_index
    assert "system_review_scenarios" in task_index
