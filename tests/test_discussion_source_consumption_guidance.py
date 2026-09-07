"""Installed source-consumption contracts and their durable schema shapes."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ("discussion-state-schema.json", "discussion-handoff-schema.json")
UNIT = "U0001-" + "a" * 12


def _schema(name):
    return json.loads((ROOT / "templates" / name).read_text(encoding="utf-8"))


def _validator(schema_name, definition):
    schema = _schema(schema_name)
    assert definition in schema["$defs"]
    return Draft202012Validator(
        {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}
    )


@pytest.mark.parametrize("agent", ["codex", "claude"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_installed_discussion_reads_complete_source_consumption_contract(
    tmp_path, agent, profile
):
    integration = get_integration(agent)
    manifest = IntegrationManifest(agent, tmp_path)
    integration.setup(tmp_path, manifest, parsed_options={"workflow_profile": profile})
    name = "sp-discussion" if profile == "classic" else "spx-discussion"
    skill_dir = integration.skills_dest(tmp_path) / name
    entry = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "references/source-material-consumption.md" in entry
    reference = (skill_dir / "references/source-material-consumption.md").read_text(
        encoding="utf-8"
    )
    compact = " ".join(reference.lower().split())
    for contract in (
        "discussion import-material",
        "discussion read-material",
        "--expected-state-sha256",
        "delivered_unit_ids",
        "reading_progress.next_unit_id",
        "unit_dispositions",
        "source_requirements",
        "first-party",
        "commit",
        "pagination",
        "truncation",
        "utf-8",
        "minimal_live_reads",
        "reverse review",
        "negations",
        "corrections",
        "independent",
        "not proof of understanding",
        "discard",
        "readable context",
        "2000",
        "transport boundary",
        "adjacent units",
    ):
        assert contract in compact, contract
    assert "{{specify-subcmd:" not in reference


@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_source_requirement_dispositions_require_real_explanations(schema_name):
    validator = _validator(schema_name, "sourceRequirement")
    base = {
        "id": "REQ-001",
        "statement": "Only the record owner may cancel a pending export.",
        "source_refs": [{"material_id": "MAT-001", "unit_id": UNIT, "locator": "notes.txt:42"}],
        "disposition": "in_scope",
        "acceptance_hint": "Another user cannot cancel it; its owner can.",
    }
    validator.validate(base)
    missing_acceptance = copy.deepcopy(base)
    del missing_acceptance["acceptance_hint"]
    assert list(validator.iter_errors(missing_acceptance))
    for disposition in ("context", "duplicate", "deferred", "out_of_scope", "unresolved"):
        value = {**base, "disposition": disposition}
        assert list(validator.iter_errors(value)), disposition
        value["reason"] = "The source explicitly narrows this release."
        if disposition in {"deferred", "out_of_scope"}:
            assert list(validator.iter_errors(value))
            value.update(decision_source="notes.txt:44, user correction", reopen_condition="Reopen if export sharing is requested.")
        if disposition == "duplicate":
            assert list(validator.iter_errors(value))
            value["duplicate_of"] = "REQ-002"
        validator.validate(value)


@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_reading_and_unit_disposition_shapes_are_explicit(schema_name):
    reading = {
        "version": 1,
        "content_sha256": "a" * 64,
        "snapshot_ref": ".specify/discussions/example/materials/MAT-001/source.txt",
        "source_path": "C:/source/notes.txt",
        "units": [{"id": UNIT, "start_rune": 0, "end_rune": 40, "sha256": "a" * 64}],
        "delivered_unit_ids": [UNIT],
    }
    validator = _validator(schema_name, "sourceReading")
    validator.validate(reading)
    malformed = copy.deepcopy(reading)
    malformed["units"][0]["start_rune"] = -1
    assert list(validator.iter_errors(malformed))
    validator = _validator(schema_name, "sourceUnitDisposition")
    validator.validate({"unit_id": UNIT, "disposition": "requirements", "requirement_ids": ["REQ-001"]})
    assert list(validator.iter_errors({"unit_id": UNIT, "disposition": "requirements", "requirement_ids": []}))
    assert list(validator.iter_errors({"unit_id": UNIT, "disposition": "context", "requirement_ids": []}))
    validator.validate({"unit_id": UNIT, "disposition": "context", "requirement_ids": [], "reason": "Meeting attendance only; no product rule."})


def test_source_consumption_schema_definitions_stay_in_sync():
    state, handoff = (_schema(name) for name in SCHEMAS)
    for name in ("sourceReading", "sourceUnitDisposition", "sourceRequirement"):
        assert state["$defs"][name] == handoff["$defs"][name]
    for schema, properties, requirement_key in (
        (state, state["properties"]["turn_packet"]["properties"], "requirements_snapshot"),
        (handoff, handoff["properties"], "agent_requirement_contract"),
    ):
        material = properties["source_materials"]["items"]["properties"]
        assert material["reading"]["readOnly"] is True
        assert material["unit_dispositions"]["items"]["$ref"] == "#/$defs/sourceUnitDisposition"
        assert material["claims"].get("minItems", 0) == 0
        assert properties[requirement_key]["properties"]["source_requirements"]["items"]["$ref"] == "#/$defs/sourceRequirement"


@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_source_material_ids_extend_beyond_999(schema_name):
    schema = _schema(schema_name)
    properties = schema["properties"]
    if "turn_packet" in properties:
        properties = properties["turn_packet"]["properties"]
    material = {
        "id": "MAT-1000",
        "material_type": "repository-file",
        "locator": "repo@commit:docs/behavior.md",
        "summary": "The thousandth first-party source file.",
        "inspection_status": "pending",
        "claims": [],
        "coverage_gaps": [],
        "sensitivity": "safe",
        "material_digest": "a" * 64,
    }
    validator = Draft202012Validator(
        {**properties["source_materials"]["items"], "$defs": schema["$defs"]}
    )
    validator.validate(material)
    _validator(schema_name, "sourceRequirement").validate(
        {
            "id": "REQ-1000",
            "statement": "Permission checks also apply to exported records.",
            "source_refs": [{"material_id": "MAT-1000", "unit_id": UNIT, "locator": "docs/behavior.md:9"}],
            "disposition": "in_scope",
            "acceptance_hint": "An export excludes records the actor cannot read.",
        }
    )
    Draft202012Validator(properties["source_evidence"]["items"]).validate(
        {
            "source_type": "repository-file",
            "evidence_status": "verified",
            "source": "repo@commit:docs/behavior.md:9",
            "claim": "Export permission rule is explicit.",
            "material_id": "MAT-1000",
        }
    )


def test_delivered_source_units_replay_without_reopening_or_mutation():
    paths = (
        "command-references/discussion/source-material-consumption.md",
        "advanced-skills/spx-discussion/references/source-material-consumption.md",
    )
    for path in paths:
        text = " ".join((ROOT / "templates" / path).read_text(encoding="utf-8").lower().split())
        for contract in (
            "replayed: true",
            "replayed: false",
            "ready, consumed, closed, or archived",
            "without reopening",
            "no state/log writes",
            "unchanged state hash",
            "optional for replay",
            "confirmed snapshot",
            "normal product-source edits",
            "tampering",
        ):
            assert contract in text, (path, contract)
        assert "each successful read returns" not in text
    downstream = (ROOT / "templates/command-references/discussion/downstream-consumption.md").read_text(encoding="utf-8")
    assert "discussion read-material" in downstream
    assert "replayed: true" in downstream
    assert "content_sha256" in downstream


@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_specify_binds_source_intent_before_compiling_the_specification(profile):
    reference, entry = {
        "classic": ("command-references/specify/discussion-handoff-validation.md", "commands/specify.md"),
        "advanced": ("advanced-skills/spx-specify/references/discussion-handoff.md", "advanced-skills/spx-specify/SKILL.md"),
    }[profile]
    content = " ".join((ROOT / "templates" / reference).read_text(encoding="utf-8").lower().split())
    for contract in (
        "before compiling",
        "bind-consumer",
        "--intake",
        "status: pending",
        "all five lineage fields",
        "cannot be consumed",
        "without --intake",
        "must not delete",
        "no additional human approval",
    ):
        assert contract in content, (reference, contract)
    entry_content = " ".join((ROOT / "templates" / entry).read_text(encoding="utf-8").lower().split())
    assert "before compiling" in entry_content
    assert "--intake" in entry_content


@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_consumers_keep_source_requirements_through_real_acceptance_refs(profile):
    paths = {
        "classic": [
            "command-references/specify/discussion-handoff-validation.md",
            "command-references/plan/plan-contract-fields.md",
            "command-references/tasks/plan-intake.md",
            "command-references/implement/task-intake-and-tracker.md",
            "command-references/quick/handoff-consumption.md",
        ],
        "advanced": [
            "advanced-skills/spx-specify/references/discussion-handoff.md",
            "advanced-skills/spx-plan/references/planning-contract.md",
            "advanced-skills/spx-tasks/references/task-graph-contract.md",
            "advanced-skills/spx-implement/references/execution-contract.md",
            "advanced-skills/spx-quick/references/task-contract.md",
        ],
    }[profile]
    texts = [(ROOT / "templates" / path).read_text(encoding="utf-8") for path in paths]
    for text in texts[:3]:
        assert "source_requirement_coverage" in text
        assert "acceptance_refs" in text
    assert "source_requirement_refs" in texts[3]
    assert "source_requirements" in texts[4]
    assert "readiness" in texts[4]
    assert "confirmation" in texts[4]


@pytest.mark.parametrize("name", ["spec-contract-template.json", "plan-contract-template.json", "task-index-template.json"])
def test_phase_templates_expose_source_coverage(name):
    assert _schema(name)["source_requirement_coverage"] == []
