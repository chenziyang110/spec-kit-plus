from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _json(relative: str) -> dict[str, object]:
    return json.loads(_read(relative))


def test_classic_and_advanced_test_design_surfaces_define_the_same_boundary() -> None:
    classic = _read("templates/commands/test-design.md").lower()
    advanced = _read("templates/advanced-skills/spx-test-design/SKILL.md").lower()
    worker = _read("templates/worker-prompts/test-design-worker.md").lower()
    assert ".specify/templates/worker-prompts/test-design-worker.md" in classic

    for content in (classic, advanced):
        assert "project-baseline" in content
        assert "incremental-update" in content
        assert "test_design" in content
        assert "complete_against_frozen_scope" in content
        assert "absolutely_complete" in content
        assert "do not" in content or "never" in content
        assert "specify-runtime test-design init" in content
        assert "specify-runtime test-design universe-build" in content
        assert "specify-runtime test-design lane-prepare" in content
        assert "specify-runtime test-design lane-lease" in content
        assert "specify-runtime test-design lane-checkpoint" in content
        assert "specify-runtime test-design lane-yield" in content
        assert "specify-runtime test-design lane-accept" in content
        assert "specify-runtime test-design gap-reconcile" in content
        assert "specify-runtime test-design synthesize" in content
        assert "specify-runtime test-design audit-prepare" in content
        assert "specify-runtime test-design validate" in content
        assert "specify-runtime test-design handoff" in content
        assert "--expected-revision" in content
        assert "sp-tasks" in content or "spx-tasks" in content
        assert "sp-deep-research" in content or "spx-deep-research" in content
        assert "specify-runtime evidence register" in content
        assert "specify-runtime evidence import" in content

    assert "leader" in classic
    assert "leader" in advanced
    assert "read-only" in worker
    assert "candidate_cases" in worker
    assert "data_requirements" in worker
    assert "contradictions" in worker
    assert "unknowns" in worker
    assert "must not accept" in worker or "never accept" in worker


def test_classic_test_design_references_separate_truth_selection_from_runtime_mutation() -> None:
    contract = _read(
        "templates/command-references/test-design/test-design-contract.md"
    ).lower()
    worker = _read(
        "templates/command-references/test-design/worker-contract.md"
    ).lower()
    combined = " ".join((contract + "\n" + worker).split())

    assert "leader selects the accepted truth" in combined
    assert "targeted `artifact patch`" in combined
    assert "`gap-reconcile`" in combined
    assert "workers never write canonical artifacts" in combined
    assert "`synthesize` validates" in combined
    assert "does not automatically materialize worker proposals" in combined
    assert "only the runtime may merge accepted results" not in worker


def test_classic_synthesize_is_a_validator_and_state_transition_not_a_renderer() -> None:
    classic = " ".join(_read("templates/commands/test-design.md").lower().split())

    assert "rendered views" not in classic
    assert "validates the canonical bundle and accepted evidence" in classic
    assert "records artifact digests" in classic
    assert "advances runtime state" in classic


def test_test_design_material_contract_has_one_explicit_resolution_disposition() -> None:
    schema = _json("templates/test-data-manifest-schema.json")
    dataset = schema["$defs"]["dataset"]
    required = set(dataset["required"])
    properties = dataset["properties"]

    assert {"disposition", "readiness", "provenance_refs"} <= required
    assert set(properties["disposition"]["enum"]) == {
        "reuse",
        "generate",
        "search",
        "request",
        "block",
        "defer",
    }
    assert {
        "ready",
        "recipe-ready",
        "evidence-needed",
        "human-input-required",
        "blocked",
        "deferred",
    } <= set(properties["readiness"]["enum"])

    for field in (
        "format",
        "schema_ref",
        "volume",
        "relationships",
        "constraints",
        "license",
        "usage_limits",
        "fixed_seed",
        "distribution",
        "edge_partitions",
        "checksum",
        "allowed_usage",
        "environment_refs",
        "snapshot_binding",
        "refresh_policy",
        "cleanup_reset",
        "oracle_binding",
        "limitations",
        "residual_risk",
    ):
        assert field in properties


def test_test_universe_has_a_stable_obligation_denominator() -> None:
    universe = _json("templates/test-universe-schema.json")
    obligation = universe["$defs"]["obligation"]

    assert "obligations" in universe["required"]
    assert {
        "obligation_id",
        "title",
        "source_refs",
        "capability_refs",
        "scenario_refs",
        "dimension",
        "risk_tier",
        "applicability",
        "rationale",
        "required_evidence_classes",
        "test_case_ids",
        "gap_refs",
        "invalidation_triggers",
    } <= set(obligation["required"])
    assert obligation["properties"]["obligation_id"]["$ref"] == "#/$defs/obligation_id"
    assert "obligation_ids" in universe["$defs"]["capability"]["required"]
    assert "obligation_refs" in universe["$defs"]["scenario"]["required"]
    assert "obligation_refs" in universe["$defs"]["test_case"]["required"]


def test_test_catalog_schema_carries_the_professional_case_contract() -> None:
    catalog = _json("templates/test-catalog-schema.json")
    case = catalog["$defs"]["test_case"]
    required = set(case["required"])

    assert {
        "objective",
        "status",
        "risk_tags",
        "obligation_refs",
        "automation_target",
        "owner_stage",
        "environment",
        "entrypoint_refs",
        "preconditions",
        "roles_permissions",
        "configuration",
        "steps",
        "expected_results",
        "variants",
        "cleanup_reset",
        "idempotency",
        "side_effect_boundary",
        "evidence_requirements",
        "freshness_rule",
        "invalidation_triggers",
        "flake_risks",
        "residual_risk",
    } <= required

    coverage = _json("templates/coverage-matrix-schema.json")
    assert {"obligation_ref", "gap_refs"} <= set(coverage["$defs"]["row"]["required"])


def test_lane_gap_handoff_and_task_bindings_are_content_addressed() -> None:
    lane = _json("templates/test-design-lane-result-schema.json")
    assert {"obligation_results", "checks"} <= set(lane["required"])

    gaps = _json("templates/test-design-gaps-schema.json")
    gap_required = set(gaps["properties"]["gaps"]["items"]["required"])
    assert "affected_obligation_refs" in gap_required

    handoff = _json("templates/test-design-handoff-schema.json")
    assert {"state_revision", "artifact_digests"} <= set(handoff["required"])

    task_index = _json("templates/task-index-template.json")
    for field in (
        "test_design_handoff_ref",
        "test_design_handoff_sha256",
        "test_design_source_fingerprint",
        "test_design_state_revision",
        "test_design_artifact_digests",
    ):
        assert field in task_index


def test_audit_checks_require_evidence_for_pass_and_findings_for_failure() -> None:
    schema = _json("templates/test-design-lane-result-schema.json")
    audit_check = {
        "check_id": "traceability",
        "status": "passed",
        "evidence_refs": [
            ".specify/evidence/records/evd-" + "a" * 24 + ".json"
        ],
        "affected_obligation_refs": ["TO-001"],
        "finding_refs": [],
        "summary": "Traceability was checked against the frozen denominator.",
    }
    validator = Draft202012Validator(
        {"$schema": schema["$schema"], "$defs": schema["$defs"], **schema["$defs"]["audit_check"]}
    )

    assert validator.is_valid(audit_check)
    assert not validator.is_valid({**audit_check, "evidence_refs": []})

    for status in ("finding", "blocked"):
        failing = {
            **audit_check,
            "status": status,
            "evidence_refs": [],
            "finding_refs": ["FINDING-001"],
        }
        assert validator.is_valid(failing)
        assert not validator.is_valid({**failing, "finding_refs": []})


def test_test_design_is_planning_only_in_both_cognition_registries() -> None:
    registry = _json("templates/artifacts/project-cognition-workflow-registry.json")
    policy = registry["workflows"]["test-design"]

    assert policy["mode"] == "no_closeout"
    assert policy["canonical_workflow"] is None

    go_registry = _read("tools/specify-runtime/internal/workflowregistry/registry.go")
    assert '"test-design"' in go_registry
    assert "ModeNoCloseout" in go_registry


def test_advanced_surface_map_declares_test_design_as_one_to_one_counterpart() -> None:
    surface_map = _json("templates/advanced-skills/_shared/surface-map.json")
    contract = surface_map["skills"]["spx-test-design"]

    assert contract["absorbs"] == ["test-design"]
    assert contract["assets"] == []
    assert contract["references"] == [
        "spx-test-design/references/test-design-contract.md",
        "spx-test-design/references/worker-contract.md",
    ]


def test_spx_test_design_has_valid_user_interface_metadata() -> None:
    metadata = yaml.safe_load(
        _read("templates/advanced-skills/spx-test-design/agents/openai.yaml")
    )

    assert metadata["interface"]["display_name"] == "SPX Test Design"
    assert 25 <= len(metadata["interface"]["short_description"]) <= 64
    assert "$spx-test-design" in metadata["interface"]["default_prompt"]
    assert metadata["policy"]["allow_implicit_invocation"] is False


def test_test_design_phase2_runtime_schemas_and_templates_are_packaged() -> None:
    pyproject = _read("pyproject.toml")
    for name in (
        "test-design-state-schema.json",
        "test-design-gaps-schema.json",
        "test-design-lane-result-schema.json",
        "test-design-handoff-schema.json",
    ):
        path = ROOT / "templates" / name
        assert path.is_file(), name
        assert f'"templates/{name}"' in pyproject

    artifact_registry = _json("templates/workflow-artifact-registry.json")
    test_design = next(
        item
        for item in artifact_registry["artifacts"]
        if item["id"] == "feature_test_design_artifacts"
    )
    registered = "\n".join(test_design["path_patterns"])
    for artifact_name in (
        "test-state.json",
        "test-gaps.json",
        "lane-manifest.json",
        "handoff-to-tasks.json",
    ):
        assert artifact_name in registered


def test_test_design_runtime_results_and_handoff_history_are_show_list_only() -> None:
    artifact_registry = _json("templates/workflow-artifact-registry.json")
    runtime_history = next(
        item
        for item in artifact_registry["artifacts"]
        if item["id"] == "test_design_runtime_history"
    )

    assert {
        "**/test-design/lane-results/*.json",
        "**/test-design/lane-results/checkpoints/*.json",
        "**/test-design/handoff-history/*.json",
    } <= set(runtime_history["path_patterns"])
    assert set(runtime_history["owner_cli"]) == {
        "specify-runtime test-design",
        "specify-runtime artifact show",
        "specify-runtime artifact list",
    }
    joined = " ".join(runtime_history["owner_cli"]).lower()
    assert "patch" not in joined
    assert "submit" not in joined
    assert "delete" not in joined
    assert "immutable" in " ".join(runtime_history["safe_instruction_patterns"]).lower()


def test_test_design_phase2_canonical_scaffolds_match_runtime_schemas() -> None:
    pairs = (
        ("test-design-state-schema.json", "artifacts/test-state.json"),
        ("test-design-gaps-schema.json", "artifacts/test-gaps.json"),
        ("test-design-lane-result-schema.json", "artifacts/test-design-lane-result.json"),
        ("test-design-handoff-schema.json", "artifacts/test-design-handoff.json"),
    )

    for schema_name, scaffold_name in pairs:
        schema = _json(f"templates/{schema_name}")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(_json(f"templates/{scaffold_name}"))


def test_test_design_is_documented_as_optional_between_plan_and_tasks() -> None:
    docs = "\n".join(
        (
            _read("README.md"),
            _read("PROJECT-HANDBOOK.md"),
            _read("templates/project-handbook-template.md"),
        )
    ).lower()

    assert "sp-test-design" in docs
    assert "spx-test-design" in docs
    assert "optional" in docs or "可选" in docs
    assert "plan" in docs and "tasks" in docs


def test_auto_routing_resumes_selected_test_design_before_tasks() -> None:
    classic = _read("templates/commands/auto.md").lower()
    passive = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()
    advanced = _read(
        "templates/advanced-skills/spx-auto/references/routing-contract.md"
    ).lower()

    for content in (classic, passive, advanced):
        assert "test-design" in content
        assert "stale" in content
        assert "handoff" in content
        assert "tasks" in content


def test_test_design_is_registered_in_cli_discovery_and_extension_names() -> None:
    cli = _read("src/specify_cli/__init__.py")
    extensions = _read("src/specify_cli/extensions.py")

    assert '"test-design": "Use when' in cli
    assert '@app.command("test-design", help=SKILL_DESCRIPTIONS["test-design"])' in cli
    assert '("test-design", "optional test universe' in cli
    assert '"test-design",' in extensions
