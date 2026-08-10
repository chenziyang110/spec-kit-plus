"""Schema, validation, and deterministic rendering for test-intelligence artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


_SCHEMA_RELATIVE = {
    "test-universe": Path("test-universe-schema.json"),
    "test-catalog": Path("test-catalog-schema.json"),
    "test-data-manifest": Path("test-data-manifest-schema.json"),
    "coverage-matrix": Path("coverage-matrix-schema.json"),
}


class TestIntelligenceValidationError(ValueError):
    """Raised when test-intelligence artifacts fail schema or bundle validation."""

    __test__ = False


def _schema_candidates(relative: Path) -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    return (
        here.parents[2] / "templates" / relative,
        here.parent / "core_pack" / "templates" / relative,
    )


def _load_schema(name: str) -> dict[str, Any]:
    relative = _SCHEMA_RELATIVE[name]
    for candidate in _schema_candidates(relative):
        if not candidate.is_file():
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError(f"schema is not a JSON object: {candidate}")
        return payload
    raise RuntimeError(
        "packaged test-intelligence schema is missing "
        f"(looked in: {', '.join(str(path) for path in _schema_candidates(relative))})"
    )


def load_test_universe_schema() -> dict[str, Any]:
    """Load the packaged Test Universe JSON Schema."""

    return _load_schema("test-universe")


def load_test_catalog_schema() -> dict[str, Any]:
    """Load the packaged Test Catalog JSON Schema."""

    return _load_schema("test-catalog")


def load_test_data_manifest_schema() -> dict[str, Any]:
    """Load the packaged Test Data Manifest JSON Schema."""

    return _load_schema("test-data-manifest")


def load_coverage_matrix_schema() -> dict[str, Any]:
    """Load the packaged Coverage Matrix JSON Schema."""

    return _load_schema("coverage-matrix")


def _validate_schema_payload(
    payload: dict[str, Any],
    *,
    schema: dict[str, Any],
    label: str,
) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if not errors:
        return
    first = errors[0]
    path = "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}"
        for part in first.absolute_path
    )
    raise TestIntelligenceValidationError(
        f"{label} failed schema validation at {path}: {first.message}"
    )


def _sorted_strings(values: Iterable[object]) -> list[str]:
    return sorted(str(value) for value in values)


def _scenario_coverage_refs(scenario: dict[str, Any]) -> list[str]:
    if "coverage_refs" in scenario:
        return _sorted_strings(scenario["coverage_refs"])
    if "coverage_ref" in scenario:
        return [str(scenario["coverage_ref"])]
    return []


def _require_unique_ids(
    items: Iterable[dict[str, Any]],
    *,
    id_key: str,
    label: str | None = None,
) -> dict[str, dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for item in items:
        stable_id = str(item[id_key])
        if stable_id in seen:
            detail = label or id_key
            raise TestIntelligenceValidationError(f"duplicate {stable_id} in {detail}")
        seen[stable_id] = item
    return seen


def _sorted_items(
    items: Iterable[dict[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: str(item.get(key, "")))


def _format_refs(values: Iterable[object]) -> list[str]:
    rendered = _sorted_strings(values)
    if not rendered:
        return ["- None."]
    return [f"- `{value}`" for value in rendered]


def _format_text_bullets(values: Iterable[object]) -> list[str]:
    rendered = [str(value) for value in values]
    if not rendered:
        return ["- None."]
    return [f"- {value}" for value in rendered]


def _format_numbered_steps(values: Iterable[object]) -> list[str]:
    rendered = [str(value) for value in values]
    if not rendered:
        return ["- None."]
    return [f"{index}. {value}" for index, value in enumerate(rendered, start=1)]


def validate_test_intelligence_bundle(
    *,
    universe: dict[str, Any],
    catalog: dict[str, Any],
    data_manifest: dict[str, Any],
    coverage_matrix: dict[str, Any],
) -> None:
    """Validate one coherent test-intelligence bundle across all four artifacts."""

    _validate_schema_payload(
        universe,
        schema=load_test_universe_schema(),
        label="test-universe",
    )
    _validate_schema_payload(
        catalog,
        schema=load_test_catalog_schema(),
        label="test-catalog",
    )
    _validate_schema_payload(
        data_manifest,
        schema=load_test_data_manifest_schema(),
        label="test-data-manifest",
    )
    _validate_schema_payload(
        coverage_matrix,
        schema=load_coverage_matrix_schema(),
        label="coverage-matrix",
    )

    obligations = _require_unique_ids(
        universe.get("obligations", []),
        id_key="obligation_id",
        label="test-universe obligations",
    )
    capabilities = _require_unique_ids(
        universe.get("capabilities", []),
        id_key="capability_id",
        label="test-universe capabilities",
    )
    scenarios = _require_unique_ids(
        universe.get("scenarios", []),
        id_key="scenario_id",
        label="test-universe scenarios",
    )
    universe_cases = _require_unique_ids(
        universe.get("test_cases", []),
        id_key="test_case_id",
        label="test-universe test_cases",
    )
    catalog_cases = _require_unique_ids(
        catalog.get("cases", []),
        id_key="test_case_id",
        label="test-catalog cases",
    )
    datasets = _require_unique_ids(
        data_manifest.get("datasets", []),
        id_key="test_data_id",
        label="test-data-manifest datasets",
    )
    coverage_rows = _require_unique_ids(
        coverage_matrix.get("rows", []),
        id_key="coverage_id",
        label="coverage-matrix rows",
    )

    if set(universe_cases) != set(catalog_cases):
        raise TestIntelligenceValidationError(
            "test-universe and test-catalog must declare the same test_case_id set"
        )

    for obligation_id, obligation in obligations.items():
        for capability_id in obligation["capability_refs"]:
            if capability_id not in capabilities:
                raise TestIntelligenceValidationError(
                    f"{obligation_id} references missing capability {capability_id}"
                )
            if obligation_id not in capabilities[capability_id]["obligation_ids"]:
                raise TestIntelligenceValidationError(
                    f"{obligation_id} is missing the reverse capability link from {capability_id}"
                )
        for scenario_id in obligation["scenario_refs"]:
            if scenario_id not in scenarios:
                raise TestIntelligenceValidationError(
                    f"{obligation_id} references missing scenario {scenario_id}"
                )
            if obligation_id not in scenarios[scenario_id]["obligation_refs"]:
                raise TestIntelligenceValidationError(
                    f"{obligation_id} is missing the reverse scenario link from {scenario_id}"
                )
        for case_id in obligation["test_case_ids"]:
            if case_id not in universe_cases:
                raise TestIntelligenceValidationError(
                    f"{obligation_id} references missing test case {case_id}"
                )
            if obligation_id not in universe_cases[case_id]["obligation_refs"]:
                raise TestIntelligenceValidationError(
                    f"{obligation_id} is missing the reverse test-case link from {case_id}"
                )
            if obligation_id not in catalog_cases[case_id]["obligation_refs"]:
                raise TestIntelligenceValidationError(
                    f"{obligation_id} is missing the catalog link from {case_id}"
                )
        if obligation["applicability"] == "applicable" and not any(
            str(row["obligation_ref"]) == obligation_id
            for row in coverage_rows.values()
        ):
            raise TestIntelligenceValidationError(
                f"{obligation_id} is applicable but has no coverage-matrix accounting row"
            )

    for capability_id, capability in capabilities.items():
        for obligation_id in capability["obligation_ids"]:
            if obligation_id not in obligations:
                raise TestIntelligenceValidationError(
                    f"{capability_id} references missing obligation {obligation_id}"
                )
            if capability_id not in obligations[obligation_id]["capability_refs"]:
                raise TestIntelligenceValidationError(
                    f"{capability_id} is missing the reverse obligation link from {obligation_id}"
                )
        for scenario_id in capability["scenario_ids"]:
            if scenario_id not in scenarios:
                raise TestIntelligenceValidationError(
                    f"{capability_id} references missing scenario {scenario_id} in test-universe"
                )
            if capability_id not in scenarios[scenario_id]["capability_refs"]:
                raise TestIntelligenceValidationError(
                    f"{capability_id} is missing the reverse scenario link from {scenario_id}"
                )
        for case_id in capability["test_case_ids"]:
            if case_id not in universe_cases:
                raise TestIntelligenceValidationError(
                    f"{capability_id} references missing test case {case_id} in test-universe"
                )
            if capability_id not in universe_cases[case_id]["capability_refs"]:
                raise TestIntelligenceValidationError(
                    f"{capability_id} is missing the reverse test case link from {case_id}"
                )

    for scenario_id, scenario in scenarios.items():
        for obligation_id in scenario["obligation_refs"]:
            if obligation_id not in obligations:
                raise TestIntelligenceValidationError(
                    f"{scenario_id} references missing obligation {obligation_id}"
                )
            if scenario_id not in obligations[obligation_id]["scenario_refs"]:
                raise TestIntelligenceValidationError(
                    f"{scenario_id} is missing the reverse obligation link from {obligation_id}"
                )
        for capability_id in scenario["capability_refs"]:
            if capability_id not in capabilities:
                raise TestIntelligenceValidationError(
                    f"{scenario_id} references missing capability {capability_id} in test-universe"
                )
            capability = capabilities[capability_id]
            if scenario_id not in capability["scenario_ids"]:
                raise TestIntelligenceValidationError(
                    f"{scenario_id} is missing the reverse capability link from {capability_id}"
                )
        for case_id in scenario["test_case_ids"]:
            if case_id not in universe_cases:
                raise TestIntelligenceValidationError(
                    f"{scenario_id} references missing test case {case_id} in test-universe"
                )
            case = universe_cases[case_id]
            if scenario_id not in case["scenario_refs"]:
                raise TestIntelligenceValidationError(
                    f"{scenario_id} is missing the reverse test case link from {case_id}"
                )
        coverage_refs = _scenario_coverage_refs(scenario)
        for coverage_id in coverage_refs:
            if coverage_id not in coverage_rows:
                raise TestIntelligenceValidationError(
                    f"{scenario_id} references missing coverage row {coverage_id} in coverage-matrix"
                )
            if coverage_rows[coverage_id]["scenario_ref"] != scenario_id:
                raise TestIntelligenceValidationError(
                    f"{scenario_id} coverage row {coverage_id} does not point back to the same scenario"
                )

    for case_id, universe_case in universe_cases.items():
        catalog_case = catalog_cases[case_id]
        if _sorted_strings(universe_case["obligation_refs"]) != _sorted_strings(
            catalog_case["obligation_refs"]
        ):
            raise TestIntelligenceValidationError(
                f"{case_id} obligation_refs differ between test-universe and test-catalog"
            )
        for obligation_id in universe_case["obligation_refs"]:
            if obligation_id not in obligations:
                raise TestIntelligenceValidationError(
                    f"{case_id} references missing obligation {obligation_id}"
                )
            if case_id not in obligations[obligation_id]["test_case_ids"]:
                raise TestIntelligenceValidationError(
                    f"{case_id} is missing the reverse obligation link from {obligation_id}"
                )
        if len(catalog_case["steps"]) != len(catalog_case["expected_results"]):
            raise TestIntelligenceValidationError(
                f"{case_id} must have one observable expected result per ordered step"
            )
        for data_id in catalog_case["test_data_refs"]:
            if data_id not in datasets:
                raise TestIntelligenceValidationError(
                    f"{case_id} references missing dataset {data_id} in test-data-manifest"
                )
            dataset = datasets[data_id]
            if case_id not in dataset["applicable_test_case_ids"]:
                raise TestIntelligenceValidationError(
                    f"{case_id} is missing the reverse dataset link from {data_id} in test-data-manifest"
                )
            for scenario_id in universe_case["scenario_refs"]:
                if scenario_id not in dataset["applicable_scenario_ids"]:
                    raise TestIntelligenceValidationError(
                        f"{case_id} dataset {data_id} is missing scenario applicability for {scenario_id} in test-data-manifest"
                    )
        for capability_id in universe_case["capability_refs"]:
            if capability_id not in capabilities:
                raise TestIntelligenceValidationError(
                    f"{case_id} references missing capability {capability_id} in test-universe"
                )
            if case_id not in capabilities[capability_id]["test_case_ids"]:
                raise TestIntelligenceValidationError(
                    f"{case_id} is missing the reverse capability link from {capability_id}"
                )
        for scenario_id in universe_case["scenario_refs"]:
            if scenario_id not in scenarios:
                raise TestIntelligenceValidationError(
                    f"{case_id} references missing scenario {scenario_id} in test-universe"
                )
            if case_id not in scenarios[scenario_id]["test_case_ids"]:
                raise TestIntelligenceValidationError(
                    f"{case_id} is missing the reverse scenario link from {scenario_id}"
                )
        for coverage_id in universe_case["coverage_refs"]:
            if coverage_id not in coverage_rows:
                raise TestIntelligenceValidationError(
                    f"{case_id} references missing coverage row {coverage_id} in coverage-matrix"
                )
            if coverage_rows[coverage_id]["test_case_ref"] != case_id:
                raise TestIntelligenceValidationError(
                    f"{case_id} coverage row {coverage_id} does not point back to the same test case"
                )
        if _sorted_strings(universe_case["capability_refs"]) != _sorted_strings(
            catalog_case["capability_refs"]
        ):
            raise TestIntelligenceValidationError(
                f"{case_id} capability_refs differ between test-universe and test-catalog"
            )
        if _sorted_strings(universe_case["scenario_refs"]) != _sorted_strings(
            catalog_case["scenario_refs"]
        ):
            raise TestIntelligenceValidationError(
                f"{case_id} scenario_refs differ between test-universe and test-catalog"
            )
        if _sorted_strings(universe_case["data_refs"]) != _sorted_strings(
            catalog_case["test_data_refs"]
        ):
            raise TestIntelligenceValidationError(
                f"{case_id} data refs differ between test-universe and test-catalog"
            )

    for coverage_id, row in coverage_rows.items():
        case_id = str(row["test_case_ref"])
        if case_id not in catalog_cases:
            raise TestIntelligenceValidationError(
                f"{coverage_id} references missing test case {case_id} in test-catalog"
            )
        universe_case = universe_cases[case_id]
        obligation_id = str(row["obligation_ref"])
        if obligation_id not in obligations:
            raise TestIntelligenceValidationError(
                f"{coverage_id} references missing obligation {obligation_id}"
            )
        obligation = obligations[obligation_id]
        status = str(row["status"])
        gap_refs = _sorted_strings(row["gap_refs"])
        unknown_gap_refs = sorted(
            set(gap_refs) - set(_sorted_strings(obligation["gap_refs"]))
        )
        if unknown_gap_refs:
            raise TestIntelligenceValidationError(
                f"{coverage_id} gap_refs are not linked from {obligation_id}: "
                + ", ".join(unknown_gap_refs)
            )
        applicability = str(obligation["applicability"])
        if status == "covered" and applicability != "applicable":
            raise TestIntelligenceValidationError(
                f"{coverage_id} cannot be covered when {obligation_id} is {applicability}"
            )
        if status == "not_applicable" and applicability != "not_applicable":
            raise TestIntelligenceValidationError(
                f"{coverage_id} cannot be not_applicable when {obligation_id} is {applicability}"
            )
        if applicability == "not_applicable" and status != "not_applicable":
            raise TestIntelligenceValidationError(
                f"{coverage_id} must be not_applicable because {obligation_id} is not_applicable"
            )
        if case_id not in obligation["test_case_ids"]:
            raise TestIntelligenceValidationError(
                f"{coverage_id} obligation {obligation_id} does not link test case {case_id}"
            )
        if obligation_id not in universe_case["obligation_refs"]:
            raise TestIntelligenceValidationError(
                f"{coverage_id} obligation {obligation_id} is absent from {case_id}"
            )
        capability_id = str(row["capability_ref"])
        if capability_id not in capabilities:
            raise TestIntelligenceValidationError(
                f"{coverage_id} references missing capability {capability_id} in test-universe"
            )
        capability = capabilities[capability_id]
        scenario_id = str(row["scenario_ref"])
        if scenario_id not in scenarios:
            raise TestIntelligenceValidationError(
                f"{coverage_id} references missing scenario {scenario_id} in test-universe"
            )
        scenario = scenarios[scenario_id]
        if capability_id not in obligation["capability_refs"]:
            raise TestIntelligenceValidationError(
                f"{coverage_id} capability {capability_id} is not linked from {obligation_id}"
            )
        if scenario_id not in obligation["scenario_refs"]:
            raise TestIntelligenceValidationError(
                f"{coverage_id} scenario {scenario_id} is not linked from {obligation_id}"
            )
        if coverage_id not in _scenario_coverage_refs(scenario):
            raise TestIntelligenceValidationError(
                f"{coverage_id} is missing the reverse scenario coverage link from {scenario_id}"
            )
        if coverage_id not in universe_case["coverage_refs"]:
            raise TestIntelligenceValidationError(
                f"{coverage_id} is missing the reverse test case coverage link from {case_id}"
            )
        if (
            capability_id not in scenario["capability_refs"]
            or capability_id not in universe_case["capability_refs"]
        ):
            raise TestIntelligenceValidationError(
                f"{coverage_id} points to capability {capability_id} that is not linked from both {scenario_id} and {case_id}"
            )
        if (
            scenario_id not in capability["scenario_ids"]
            or case_id not in capability["test_case_ids"]
        ):
            raise TestIntelligenceValidationError(
                f"{coverage_id} points to capability {capability_id} without the matching reverse links"
            )
        requirement_ref = str(row["requirement_ref"])
        if requirement_ref not in _sorted_strings(capability["requirement_refs"]):
            raise TestIntelligenceValidationError(
                f"{coverage_id} requirement_ref {requirement_ref} is not declared by capability {capability_id}"
            )
        if requirement_ref not in _sorted_strings(catalog_cases[case_id]["requirement_refs"]):
            raise TestIntelligenceValidationError(
                f"{coverage_id} requirement_ref {requirement_ref} is not declared by catalog case {case_id}"
            )
        for data_id in row["test_data_refs"]:
            if data_id not in datasets:
                raise TestIntelligenceValidationError(
                    f"{coverage_id} references missing dataset {data_id} in test-data-manifest"
                )
            dataset = datasets[data_id]
            if data_id not in catalog_cases[case_id]["test_data_refs"]:
                raise TestIntelligenceValidationError(
                    f"{coverage_id} dataset {data_id} is absent from catalog case {case_id}"
                )
            if data_id not in universe_case["data_refs"]:
                raise TestIntelligenceValidationError(
                    f"{coverage_id} dataset {data_id} is absent from universe case {case_id}"
                )
            if case_id not in dataset["applicable_test_case_ids"]:
                raise TestIntelligenceValidationError(
                    f"{coverage_id} dataset {data_id} is not applicable to test case {case_id} in test-data-manifest"
                )
            if scenario_id not in dataset["applicable_scenario_ids"]:
                raise TestIntelligenceValidationError(
                    f"{coverage_id} dataset {data_id} is not applicable to scenario {scenario_id} in test-data-manifest"
                )

    for data_id, dataset in datasets.items():
        for case_id in dataset["applicable_test_case_ids"]:
            if case_id not in catalog_cases:
                raise TestIntelligenceValidationError(
                    f"{data_id} references missing test case {case_id} in test-catalog"
                )
            if data_id not in catalog_cases[case_id]["test_data_refs"]:
                raise TestIntelligenceValidationError(
                    f"{data_id} is not linked back from catalog case {case_id}"
                )
            if data_id not in universe_cases[case_id]["data_refs"]:
                raise TestIntelligenceValidationError(
                    f"{data_id} is not linked back from universe case {case_id}"
                )
        for scenario_id in dataset["applicable_scenario_ids"]:
            if scenario_id not in scenarios:
                raise TestIntelligenceValidationError(
                    f"{data_id} references missing scenario {scenario_id} in test-universe"
                )
            if not any(
                data_id in universe_cases[case_id]["data_refs"]
                for case_id in scenarios[scenario_id]["test_case_ids"]
            ):
                raise TestIntelligenceValidationError(
                    f"{data_id} has no linked test case for scenario {scenario_id}"
                )


def render_test_universe_markdown(universe: dict[str, Any]) -> str:
    """Render a deterministic Markdown view of canonical ``test-universe.json``."""

    _validate_schema_payload(
        universe,
        schema=load_test_universe_schema(),
        label="test-universe",
    )
    lines = [
        "# Test Universe",
        "",
        "`test-universe.json` is canonical. This Markdown is a deterministic view of the frozen obligation denominator and its capability, scenario, and test-case graph.",
        "",
        "## Obligations",
    ]
    obligations = _sorted_items(universe.get("obligations", []), "obligation_id")
    if not obligations:
        lines.extend(["", "- No `TO-*` rows recorded."])
    else:
        for obligation in obligations:
            lines.extend(
                [
                    "",
                    f"### {obligation['obligation_id']} — {obligation['title']}",
                    "",
                    f"- Dimension: `{obligation['dimension']}`",
                    f"- Risk Tier: `{obligation['risk_tier']}`",
                    f"- Applicability: `{obligation['applicability']}`",
                    f"- Rationale: {obligation['rationale']}",
                    "",
                    "#### Source Refs",
                    "",
                    *_format_refs(obligation["source_refs"]),
                    "",
                    "#### Required Evidence Classes",
                    "",
                    *_format_refs(obligation["required_evidence_classes"]),
                    "",
                    "#### Capability Refs",
                    "",
                    *_format_refs(obligation["capability_refs"]),
                    "",
                    "#### Scenario Refs",
                    "",
                    *_format_refs(obligation["scenario_refs"]),
                    "",
                    "#### Test Case Refs",
                    "",
                    *_format_refs(obligation["test_case_ids"]),
                    "",
                    "#### Gap Refs",
                    "",
                    *_format_refs(obligation["gap_refs"]),
                    "",
                    "#### Invalidation Triggers",
                    "",
                    *_format_text_bullets(obligation["invalidation_triggers"]),
                ]
            )

    lines.extend(["", "## Capabilities"])
    capabilities = _sorted_items(universe.get("capabilities", []), "capability_id")
    if not capabilities:
        lines.extend(["", "- No `CAP-*` rows recorded."])
    else:
        for capability in capabilities:
            lines.extend(
                [
                    "",
                    f"### {capability['capability_id']} — {capability['title']}",
                    "",
                    "#### Requirement Refs",
                    "",
                    *_format_refs(capability["requirement_refs"]),
                    "",
                    "#### Obligation Refs",
                    "",
                    *_format_refs(capability["obligation_ids"]),
                    "",
                    "#### Scenario Refs",
                    "",
                    *_format_refs(capability["scenario_ids"]),
                    "",
                    "#### Test Case Refs",
                    "",
                    *_format_refs(capability["test_case_ids"]),
                ]
            )

    lines.extend(["", "## Scenarios"])
    scenarios = _sorted_items(universe.get("scenarios", []), "scenario_id")
    if not scenarios:
        lines.extend(["", "- No `SCN-*` rows recorded."])
    else:
        for scenario in scenarios:
            lines.extend(
                [
                    "",
                    f"### {scenario['scenario_id']} — {scenario['title']}",
                    "",
                    "#### Capability Refs",
                    "",
                    *_format_refs(scenario["capability_refs"]),
                    "",
                    "#### Obligation Refs",
                    "",
                    *_format_refs(scenario["obligation_refs"]),
                    "",
                    "#### Test Case Refs",
                    "",
                    *_format_refs(scenario["test_case_ids"]),
                    "",
                    "#### Coverage Refs",
                    "",
                    *_format_refs(_scenario_coverage_refs(scenario)),
                ]
            )

    lines.extend(["", "## Test Cases"])
    cases = _sorted_items(universe.get("test_cases", []), "test_case_id")
    if not cases:
        lines.extend(["", "- No `TC-*` rows recorded."])
    else:
        for case in cases:
            lines.extend(
                [
                    "",
                    f"### {case['test_case_id']} — {case['title']}",
                    "",
                    f"- Kind: `{case['kind']}`",
                    "",
                    "#### Obligation Refs",
                    "",
                    *_format_refs(case["obligation_refs"]),
                    "",
                    "#### Capability Refs",
                    "",
                    *_format_refs(case["capability_refs"]),
                    "",
                    "#### Scenario Refs",
                    "",
                    *_format_refs(case["scenario_refs"]),
                    "",
                    "#### Test Data Refs",
                    "",
                    *_format_refs(case["data_refs"]),
                    "",
                    "#### Coverage Refs",
                    "",
                    *_format_refs(case["coverage_refs"]),
                ]
            )
    return "\n".join(lines) + "\n"


def render_test_catalog_markdown(catalog: dict[str, Any]) -> str:
    """Render a deterministic Markdown view of canonical ``test-catalog.json``."""

    _validate_schema_payload(
        catalog,
        schema=load_test_catalog_schema(),
        label="test-catalog",
    )
    lines = [
        "# Test Catalog",
        "",
        "`test-catalog.json` is canonical. This Markdown is a deterministic view of the current catalog of `TC-*` cases, their traceability, and their executable proof contract.",
    ]
    cases = _sorted_items(catalog.get("cases", []), "test_case_id")
    if not cases:
        lines.extend(["", "## Cases", "", "- No `TC-*` rows recorded."])
        return "\n".join(lines) + "\n"
    for case in cases:
        lines.extend(
            [
                "",
                f"## {case['test_case_id']} — {case['title']}",
                "",
                f"- Status: `{case['status']}`",
                f"- Stage: `{case['stage']}`",
                f"- Priority: `{case['priority']}`",
                f"- Automation Target: `{case['automation_target']}`",
                f"- Owner Stage: `{case['owner_stage']}`",
                f"- Verification Method: `{case['verification_method']}`",
                "",
                "### Risk Tags",
                "",
                *_format_refs(case["risk_tags"]),
                "",
                "### Requirement Refs",
                "",
                *_format_refs(case["requirement_refs"]),
                "",
                "### Obligation Refs",
                "",
                *_format_refs(case["obligation_refs"]),
                "",
                "### Capability Refs",
                "",
                *_format_refs(case["capability_refs"]),
                "",
                "### Scenario Refs",
                "",
                *_format_refs(case["scenario_refs"]),
                "",
                "### Test Data Refs",
                "",
                *_format_refs(case["test_data_refs"]),
                "",
                "### Environment",
                "",
                *_format_text_bullets(case["environment"]),
                "",
                "### Entrypoint Refs",
                "",
                *_format_refs(case["entrypoint_refs"]),
            ]
        )
        lines.extend(["", "### Objective", "", f"- {case['objective']}"])
        lines.extend(
            ["", "### Preconditions", "", *_format_text_bullets(case["preconditions"])]
        )
        lines.extend(
            ["", "### Roles and Permissions", "", *_format_text_bullets(case["roles_permissions"])]
        )
        lines.extend(
            ["", "### Configuration", "", *_format_text_bullets(case["configuration"])]
        )
        lines.extend(
            ["", "### Steps", "", *_format_numbered_steps(case["steps"])]
        )
        lines.extend(
            ["", "### Expected Results", "", *_format_numbered_steps(case["expected_results"])]
        )
        lines.extend(
            ["", "### Pass Criteria", "", *_format_text_bullets(case["pass_criteria"])]
        )
        lines.extend(
            [
                "",
                "### Variant Dispositions",
                "",
                *[
                    f"- {name}: `{case['variants'][name]}`"
                    for name in sorted(case["variants"])
                ],
                "",
                "### Evidence Requirements",
                "",
                *_format_refs(case["evidence_requirements"]),
                "",
                "### Lifecycle and Isolation",
                "",
                f"- Cleanup / Reset: {case['cleanup_reset']}",
                f"- Idempotency: {case['idempotency']}",
                f"- Side-Effect Boundary: {case['side_effect_boundary']}",
                f"- Freshness Rule: {case['freshness_rule']}",
                f"- Residual Risk: {case['residual_risk']}",
                "",
                "#### Invalidation Triggers",
                "",
                *_format_text_bullets(case["invalidation_triggers"]),
                "",
                "#### Flake Risks",
                "",
                *_format_text_bullets(case["flake_risks"]),
            ]
        )
    return "\n".join(lines) + "\n"


def render_test_data_manifest_markdown(data_manifest: dict[str, Any]) -> str:
    """Render a deterministic Markdown view of canonical ``test-data-manifest.json``."""

    _validate_schema_payload(
        data_manifest,
        schema=load_test_data_manifest_schema(),
        label="test-data-manifest",
    )
    lines = [
        "# Test Data Manifest",
        "",
        "`test-data-manifest.json` is canonical. This Markdown is a deterministic view of test datasets, data hygiene, and scenario applicability.",
    ]
    datasets = _sorted_items(data_manifest.get("datasets", []), "test_data_id")
    if not datasets:
        lines.extend(["", "## Datasets", "", "- No `TD-*` rows recorded."])
        return "\n".join(lines) + "\n"
    for dataset in datasets:
        hygiene = dataset["hygiene"]
        lines.extend(
            [
                "",
                f"## {dataset['test_data_id']} — {dataset['name']}",
                "",
                f"- Kind: `{dataset['kind']}`",
                f"- Sensitivity: `{dataset['sensitivity']}`",
                f"- Contains PII: `{str(dataset['contains_pii']).lower()}`",
                f"- Source: `{dataset['source']}`",
                f"- Disposition: `{dataset['disposition']}`",
                f"- Readiness: `{dataset['readiness']}`",
                "",
                "### Provenance Refs",
                "",
                *_format_refs(dataset["provenance_refs"]),
                "",
                "### Applicable Test Cases",
                "",
                *_format_refs(dataset["applicable_test_case_ids"]),
                "",
                "### Applicable Scenarios",
                "",
                *_format_refs(dataset["applicable_scenario_ids"]),
                "",
                "### Data Hygiene",
                "",
                f"- Classification Reason: {hygiene['classification_reason']}",
                f"- Sanitization Status: `{hygiene['sanitization_status']}`",
                f"- Retention Policy: `{hygiene['retention_policy']}`",
            ]
        )
        for key, title in (
            ("format", "Format"),
            ("schema_ref", "Schema Ref"),
            ("volume", "Volume"),
            ("license", "License"),
            ("usage_limits", "Usage Limits"),
            ("fixed_seed", "Fixed Seed"),
            ("distribution", "Distribution"),
            ("checksum", "Checksum"),
            ("snapshot_binding", "Snapshot Binding"),
            ("refresh_policy", "Refresh Policy"),
            ("cleanup_reset", "Cleanup / Reset"),
            ("oracle_binding", "Oracle Binding"),
            ("residual_risk", "Residual Risk"),
        ):
            if dataset.get(key) is not None:
                lines.append(f"- {title}: {dataset[key]}")
        for key, title in (
            ("relationships", "Relationships"),
            ("constraints", "Constraints"),
            ("edge_partitions", "Edge Partitions"),
            ("allowed_usage", "Allowed Usage"),
            ("environment_refs", "Environment Refs"),
            ("limitations", "Limitations"),
        ):
            if key in dataset:
                lines.extend(["", f"### {title}", "", *_format_text_bullets(dataset[key])])
        for key, title in (
            ("generation_recipe", "Generation Recipe"),
            ("request_instructions", "Request Instructions"),
            ("blocker_reason", "Blocker Reason"),
            ("unblock_criteria", "Unblock Criteria"),
        ):
            if dataset.get(key):
                lines.extend(["", f"### {title}", "", str(dataset[key])])
    return "\n".join(lines) + "\n"


def render_coverage_matrix_markdown(coverage_matrix: dict[str, Any]) -> str:
    """Render a deterministic Markdown view of canonical ``coverage-matrix.json``."""

    _validate_schema_payload(
        coverage_matrix,
        schema=load_coverage_matrix_schema(),
        label="coverage-matrix",
    )
    lines = [
        "# Coverage Matrix",
        "",
        "`coverage-matrix.json` is canonical. This Markdown is a deterministic view, not the source of truth, for `COV-*` rows that map requirements to `TC-*`, `TD-*`, evidence, and acceptance coverage.",
    ]
    rows = _sorted_items(coverage_matrix.get("rows", []), "coverage_id")
    if not rows:
        lines.extend(["", "## Coverage Rows", "", "- No `COV-*` rows recorded."])
        return "\n".join(lines) + "\n"
    for row in rows:
        lines.extend(
            [
                "",
                f"## {row['coverage_id']}",
                "",
                f"- Requirement Ref: `{row['requirement_ref']}`",
                f"- Obligation Ref: `{row['obligation_ref']}`",
                f"- Capability Ref: `{row['capability_ref']}`",
                f"- Scenario Ref: `{row['scenario_ref']}`",
                f"- Test Case Ref: `{row['test_case_ref']}`",
                f"- Status: `{row['status']}`",
                "",
                "### Test Data Refs",
                "",
                *_format_refs(row["test_data_refs"]),
                "",
                "### Evidence Refs",
                "",
                *_format_refs(row["evidence_refs"]),
                "",
                "### Acceptance Refs",
                "",
                *_format_refs(row["acceptance_refs"]),
                "",
                "### Gap Refs",
                "",
                *_format_refs(row["gap_refs"]),
            ]
        )
    return "\n".join(lines) + "\n"
