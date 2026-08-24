from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]

PUBLICATION_SCHEMA = "templates/test-design-publication-schema.json"
PROJECTION_SCHEMA = "templates/test-design-projection-schema.json"
PUBLICATION_EXAMPLE = "templates/artifacts/test-design-publication.json"
PROJECTION_EXAMPLE = "templates/artifacts/test-design-projection.json"

PROJECTION_BINDING_FIELDS = {
    "publication_ref",
    "publication_sha256",
    "projection_ref",
    "projection_sha256",
    "source_fingerprint",
    "state_revision",
}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _json(relative: str) -> dict[str, object]:
    return json.loads(_read(relative))


def _normalized(*relative_paths: str) -> str:
    return " ".join(
        "\n".join(_read(path).lower() for path in relative_paths).split()
    )


def _assert_projection_binding(binding: object) -> None:
    assert isinstance(binding, Mapping)
    assert PROJECTION_BINDING_FIELDS <= set(binding)
    for field in PROJECTION_BINDING_FIELDS:
        assert binding[field] is None, field


@pytest.mark.parametrize(
    ("schema_path", "example_path", "required_fields"),
    (
        (
            PUBLICATION_SCHEMA,
            PUBLICATION_EXAMPLE,
            {
                "schema_version",
                "publication_id",
                "source_fingerprint",
                "state_revision",
                "claim_status",
                "artifact_refs",
                "artifact_digests",
                "obligation_refs",
                "test_case_refs",
                "test_data_refs",
                "coverage_refs",
                "gap_ref",
                "gap_refs",
                "audit_result_ref",
                "forbidden_claims",
                "test_execution_status",
            },
        ),
        (
            PROJECTION_SCHEMA,
            PROJECTION_EXAMPLE,
            {
                "schema_version",
                "projection_id",
                "publication_ref",
                "publication_sha256",
                "consumer",
                "basis_ref",
                "basis_sha256",
                "source_fingerprint",
                "state_revision",
                "selection",
                "selection_sha256",
                "forbidden_claims",
                "test_execution_status",
            },
        ),
    ),
)
def test_publication_and_projection_examples_validate_against_draft_2020_12(
    schema_path: str,
    example_path: str,
    required_fields: set[str],
) -> None:
    schema_file = ROOT / schema_path
    example_file = ROOT / example_path

    assert schema_file.is_file(), schema_path
    assert example_file.is_file(), example_path

    schema = _json(schema_path)
    example = _json(example_path)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert required_fields <= set(schema["required"])
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)


def test_publication_and_projection_contracts_are_packaged() -> None:
    pyproject = _read("pyproject.toml")

    for schema_path in (PUBLICATION_SCHEMA, PROJECTION_SCHEMA):
        assert f'"{schema_path}"' in pyproject

    assert (
        '"templates/artifacts" = "specify_cli/core_pack/templates/artifacts"'
        in pyproject
    )
    for example_path in (PUBLICATION_EXAMPLE, PROJECTION_EXAMPLE):
        assert (ROOT / example_path).is_file(), example_path


def test_publication_and_projection_registry_is_runtime_owned_and_show_list_only() -> (
    None
):
    registry = _json("templates/workflow-artifact-registry.json")
    entries = [
        entry
        for entry in registry["artifacts"]
        if isinstance(entry, Mapping)
        and any(
            "test-design" in str(pattern).lower()
            and any(token in str(pattern).lower() for token in ("publication", "projection"))
            for pattern in entry.get("path_patterns", [])
        )
    ]

    patterns = " ".join(
        str(pattern).lower()
        for entry in entries
        for pattern in entry.get("path_patterns", [])
    )
    owners = {
        str(owner).lower()
        for entry in entries
        for owner in entry.get("owner_cli", [])
    }
    joined_owners = " ".join(sorted(owners))

    assert "publication" in patterns
    assert "projection" in patterns
    assert "specify-runtime test-design publish" in owners
    assert "specify-runtime test-design projection-build" in owners
    assert "specify-runtime artifact show" in owners
    assert "specify-runtime artifact list" in owners
    for forbidden in (
        "artifact patch",
        "artifact submit",
        "artifact delete",
        "artifact scaffold",
    ):
        assert forbidden not in joined_owners


def test_plan_contract_records_gate_decision_and_content_addressed_projection() -> None:
    plan = _json("templates/plan-contract-template.json")
    gate = plan["test_design_gate"]

    assert isinstance(gate, Mapping)
    assert gate["decision"] == "not_selected"
    _assert_projection_binding(gate["projection_binding"])

    plan_surfaces = _normalized(
        "templates/commands/plan.md",
        "templates/command-references/plan/plan-contract-fields.md",
        "templates/advanced-skills/spx-plan/SKILL.md",
        "templates/advanced-skills/spx-plan/references/planning-contract.md",
    )
    for decision in ("not_selected", "selected", "required"):
        assert decision in plan_surfaces
    assert "projection_binding" in plan_surfaces


def test_quick_status_records_the_equivalent_optional_projection_binding() -> None:
    status = _normalized("templates/artifacts/quick-status.md")

    assert "test_design_gate:" in status
    assert "decision: not_selected" in status
    assert "projection_binding:" in status
    for field in PROJECTION_BINDING_FIELDS:
        assert f"{field}:" in status

    quick_surfaces = _normalized(
        "templates/commands/quick.md",
        "templates/command-references/quick/intake-and-checkpoint.md",
        "templates/advanced-skills/spx-quick/SKILL.md",
        "templates/advanced-skills/spx-quick/references/task-contract.md",
    )
    for decision in ("not_selected", "selected", "required"):
        assert decision in quick_surfaces
    assert "projection_binding" in quick_surfaces


@pytest.mark.parametrize(
    "surface",
    (
        "templates/commands/test-design.md",
        "templates/advanced-skills/spx-test-design/SKILL.md",
    ),
)
def test_test_design_is_an_independent_producer_with_published_projections(
    surface: str,
) -> None:
    content = _normalized(surface)

    assert "independent producer" in content
    assert "specify-runtime test-design publish" in content
    assert "specify-runtime test-design projection-build" in content
    assert "specify-runtime test-design projection-verify" in content
    assert "plan" in content
    assert any(
        wording in content
        for wording in (
            "does not require a completed plan",
            "does not require plan completion",
            "without a completed plan",
            "without plan completion",
        )
    )


CONSUMER_SURFACES = {
    "plan": (
        "templates/commands/plan.md",
        "templates/command-references/plan/plan-contract-fields.md",
        "templates/advanced-skills/spx-plan/SKILL.md",
        "templates/advanced-skills/spx-plan/references/planning-contract.md",
    ),
    "quick": (
        "templates/commands/quick.md",
        "templates/command-references/quick/intake-and-checkpoint.md",
        "templates/advanced-skills/spx-quick/SKILL.md",
        "templates/advanced-skills/spx-quick/references/task-contract.md",
    ),
    "tasks": (
        "templates/commands/tasks.md",
        "templates/command-references/tasks/plan-intake.md",
        "templates/advanced-skills/spx-tasks/SKILL.md",
        "templates/advanced-skills/spx-tasks/references/task-graph-contract.md",
    ),
    "implement": (
        "templates/commands/implement.md",
        "templates/command-references/implement/task-intake-and-tracker.md",
        "templates/command-references/implement/subagent-worker-contract.md",
        "templates/advanced-skills/spx-implement/SKILL.md",
        "templates/advanced-skills/spx-implement/references/execution-contract.md",
        "templates/advanced-skills/spx-implement/references/worker-contract.md",
    ),
    "review": (
        "templates/commands/review.md",
        "templates/command-references/review/system-scenario-contract.md",
        "templates/command-references/review/final-claim-and-handoff.md",
        "templates/advanced-skills/spx-review/SKILL.md",
        "templates/advanced-skills/spx-review/references/review-contract.md",
        "templates/advanced-skills/spx-review/references/worker-contract.md",
    ),
}


@pytest.mark.parametrize("consumer", tuple(CONSUMER_SURFACES))
def test_both_profiles_define_read_only_verified_projection_consumers(
    consumer: str,
) -> None:
    content = _normalized(*CONSUMER_SURFACES[consumer])

    assert "test-design" in content
    assert "read-only" in content
    assert "canonical" in content
    assert "must not" in content or "never" in content
    if consumer == "implement":
        assert "task packet" in content
        assert "test_case_refs" in content
        assert "test_data_refs" in content
    else:
        assert "projection" in content
        assert "specify-runtime test-design projection-verify" in content


def test_projection_basis_is_stable_and_consumer_specific() -> None:
    producer = _normalized(
        "templates/commands/test-design.md",
        "templates/advanced-skills/spx-test-design/SKILL.md",
    )
    assert "spec-contract.json" in producer
    assert ".planning/quick/<id>/confirmation.json" in producer
    assert "plan-contract.json" in producer
    assert "implementation-handoff.json" in producer

    plan = _normalized(*CONSUMER_SURFACES["plan"])
    assert "spec-contract.json" in plan
    assert "self-hashing" in plan

    quick = _normalized(*CONSUMER_SURFACES["quick"])
    assert ".planning/quick/<id>/confirmation.json" in quick
    assert "status.md basis" not in quick


@pytest.mark.parametrize(
    "surface",
    (
        "templates/commands/implement.md",
        "templates/advanced-skills/spx-implement/SKILL.md",
    ),
)
def test_implement_consumes_only_its_verified_task_packet_subset(surface: str) -> None:
    content = _normalized(surface)

    assert "task packet" in content
    assert "subset" in content
    assert "test_case_refs" in content
    assert "test_data_refs" in content
    assert "binding" in content
    assert any(
        wording in content
        for wording in (
            "only the task packet subset",
            "only its task packet subset",
            "consume only the task packet",
            "consumes only the task packet",
        )
    )


@pytest.mark.parametrize(
    "surface",
    (
        "templates/commands/review.md",
        "templates/advanced-skills/spx-review/SKILL.md",
    ),
)
def test_review_treats_test_design_as_input_not_pass_evidence(surface: str) -> None:
    content = _normalized(surface)

    assert "test design" in content or "test-design" in content
    assert any(
        wording in content
        for wording in (
            "test design is not pass evidence",
            "test-design is not pass evidence",
            "test design does not prove the implementation passes",
            "test-design does not prove the implementation passes",
        )
    )
    assert "fresh" in content
    assert "real entrypoint" in content or "real-entrypoint" in content


@pytest.mark.parametrize(
    "surface",
    (
        "templates/commands/auto.md",
        "templates/advanced-skills/spx-auto/references/routing-contract.md",
    ),
)
def test_auto_routes_every_selected_required_or_unfresh_gate_to_test_design(
    surface: str,
) -> None:
    content = _normalized(surface)

    for state in ("selected", "required", "active", "stale"):
        assert state in content
    assert "test-design" in content
    assert "specify-runtime test-design status" in content
    assert any(
        wording in content
        for wording in (
            "no root",
            "without a root",
            "root does not exist",
            "no feature root",
        )
    )
    assert "tasks" in content


@pytest.mark.parametrize(
    "document",
    (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
    ),
)
def test_docs_present_independent_test_design_and_keep_the_optional_formal_path(
    document: str,
) -> None:
    content = _normalized(document)

    assert "test-design" in content
    assert "independent producer" in content
    assert any(
        wording in content
        for wording in (
            "does not require a completed plan",
            "does not require plan completion",
            "without a completed plan",
            "without plan completion",
        )
    )
    assert "publish" in content
    assert "projection" in content
    assert "optional" in content
    assert "plan" in content
    assert "tasks" in content
    assert re.search(r"plan.{0,160}(?:optional|\[).*test-design.{0,160}tasks", content)
