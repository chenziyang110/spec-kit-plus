from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _json(relative: str) -> dict[str, object]:
    return json.loads(_read(relative))


def test_classic_and_advanced_test_design_surfaces_define_the_same_boundary() -> None:
    classic = _read("templates/commands/test-design.md").lower()
    advanced = _read("templates/advanced-skills/spx-test-design/SKILL.md").lower()
    worker = _read("templates/worker-prompts/test-design-worker.md").lower()

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
        assert "specify-runtime test-design synthesize" in content
        assert "specify-runtime test-design audit-prepare" in content
        assert "specify-runtime test-design validate" in content
        assert "specify-runtime test-design handoff" in content
        assert "sp-tasks" in content or "spx-tasks" in content

    assert "leader" in classic
    assert "leader" in advanced
    assert "read-only" in worker
    assert "candidate_cases" in worker
    assert "data_requirements" in worker
    assert "contradictions" in worker
    assert "unknowns" in worker
    assert "must not accept" in worker or "never accept" in worker


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

