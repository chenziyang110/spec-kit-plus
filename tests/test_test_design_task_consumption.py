from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli import task_authoring
from specify_cli.execution.packet_compiler import compile_worker_task_packet
from specify_cli.execution.packet_validator import PacketValidationError


ROOT = Path(__file__).resolve().parents[1]
AUDIT_CORE_CHECK_IDS = (
    "obligation_accounting",
    "traceability",
    "oracle_quality",
    "harness_feasibility",
    "data_readiness",
    "evidence_freshness",
    "risk_dimensions",
    "contradictions",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    feature = project / "specs" / "001-test-design"
    feature.mkdir(parents=True)

    templates = project / ".specify" / "templates"
    templates.mkdir(parents=True)
    (templates / "task-index-template.json").write_text(
        _read("templates/task-index-template.json"),
        encoding="utf-8",
    )
    (templates / "task-packet-template.json").write_text(
        _read("templates/task-packet-template.json"),
        encoding="utf-8",
    )

    memory_dir = project / ".specify" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "constitution.md").write_text(
        "# Constitution\n\n- Preserve authored test design inputs.\n",
        encoding="utf-8",
    )

    (feature / "spec-contract.json").write_text(
        json.dumps(
            {
                "status": "planning-ready",
                "acceptance": [{"id": "AC-001"}],
                "source_revision": 6,
            }
        ),
        encoding="utf-8",
    )
    (feature / "plan-contract.json").write_text(
        json.dumps(
            {
                "status": "ready",
                "acceptance_refs": [],
                "source_revision": 7,
            }
        ),
        encoding="utf-8",
    )
    (feature / "plan.md").write_text(
        "\n".join(
            [
                "# Plan",
                "",
                "## Required Implementation References",
                "- docs/test-design.md",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return project, feature


def _invoke(project: Path, args: list[str]):
    old_cwd = Path.cwd()
    try:
        os.chdir(project)
        return CliRunner().invoke(app, args)
    finally:
        os.chdir(old_cwd)


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def _write_json(path: Path, payload: object) -> bytes:
    raw = _json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _publish_evidence(project: Path) -> str:
    object_raw = b'{"proof":"publish contract observed"}\n'
    object_sha256 = _sha256(object_raw)
    created_at = "2026-08-10T00:00:00Z"
    scope = "test-design"
    source = "test-design fixture"
    provenance = "deterministic local verification"
    identity_seed = "\0".join(
        (created_at, scope, "", "", source, provenance)
    ).encode("utf-8")
    evidence_id = "evd-" + _sha256(identity_seed)[:24]
    record_ref = f".specify/evidence/records/{evidence_id}.json"
    object_ref = (
        ".specify/evidence/objects/sha256/"
        f"{object_sha256[:2]}/{object_sha256}"
    )
    object_path = project / object_ref
    object_path.parent.mkdir(parents=True, exist_ok=True)
    object_path.write_bytes(object_raw)
    _write_json(
        project / record_ref,
        {
            "schema_version": "spec-kit-evidence-v1",
            "evidence_id": evidence_id,
            "status": "ready",
            "sha256": object_sha256,
            "size": len(object_raw),
            "mime": "application/json",
            "scope": scope,
            "source": source,
            "provenance": provenance,
            "object_ref": object_ref,
            "record_ref": record_ref,
            "created_at": created_at,
        },
    )
    return record_ref


def _source_fingerprint(project: Path, artifact_root: str) -> str:
    source_ref = "specs/001-test-design/plan.md"
    source_digest = _sha256((project / source_ref).read_bytes())
    payload = {
        "artifact_root": artifact_root,
        "excluded_paths": [],
        "included_paths": [source_ref],
        "risk_dimensions": ["functional"],
        "source_refs": [source_ref],
        "sources": [{"ref": source_ref, "sha256": source_digest}],
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(raw)


def _test_design_bundle(
    *, with_data: bool, evidence_ref: str
) -> tuple[dict[str, object], ...]:
    case_ids = ["TC-001", "TC-002"]
    data_refs = ["TD-001"] if with_data else []
    universe = {
        "version": 1,
        "artifact": "test-universe",
        "feature_ref": "specs/001-test-design",
        "obligations": [
            {
                "obligation_id": "TO-001",
                "title": "Publish behavior is complete",
                "source_refs": ["REQ-001"],
                "capability_refs": ["CAP-001"],
                "scenario_refs": ["SCN-001"],
                "dimension": "functional",
                "risk_tier": "critical",
                "applicability": "applicable",
                "rationale": "The publish flow is inside the frozen scope.",
                "required_evidence_classes": ["system"],
                "test_case_ids": case_ids,
                "gap_refs": [],
                "invalidation_triggers": ["The publish contract changes"],
            }
        ],
        "capabilities": [
            {
                "capability_id": "CAP-001",
                "title": "Evidence-backed publishing",
                "requirement_refs": ["REQ-001"],
                "obligation_ids": ["TO-001"],
                "test_case_ids": case_ids,
                "scenario_ids": ["SCN-001"],
            }
        ],
        "scenarios": [
            {
                "scenario_id": "SCN-001",
                "title": "Publish from the official entrypoint",
                "capability_refs": ["CAP-001"],
                "obligation_refs": ["TO-001"],
                "test_case_ids": case_ids,
                "coverage_refs": ["COV-001", "COV-002"],
            }
        ],
        "test_cases": [],
    }
    catalog = {"version": 1, "artifact": "test-catalog", "cases": []}
    coverage = {"version": 1, "artifact": "coverage-matrix", "rows": []}
    for index, case_id in enumerate(case_ids, start=1):
        coverage_id = f"COV-{index:03d}"
        universe["test_cases"].append(
            {
                "test_case_id": case_id,
                "title": f"Publish contract case {index}",
                "kind": "review" if index == 1 else "integration",
                "obligation_refs": ["TO-001"],
                "capability_refs": ["CAP-001"],
                "scenario_refs": ["SCN-001"],
                "data_refs": data_refs,
                "coverage_refs": [coverage_id],
            }
        )
        catalog["cases"].append(
            {
                "test_case_id": case_id,
                "title": f"Publish contract case {index}",
                "objective": "Prove the authored publish behavior.",
                "status": "approved",
                "stage": "review" if index == 1 else "integration",
                "priority": "p0",
                "risk_tags": ["publish"],
                "requirement_refs": ["REQ-001"],
                "obligation_refs": ["TO-001"],
                "capability_refs": ["CAP-001"],
                "scenario_refs": ["SCN-001"],
                "test_data_refs": data_refs,
                "automation_target": "hybrid",
                "owner_stage": "review",
                "environment": ["isolated review runtime"],
                "entrypoint_refs": ["publish entrypoint"],
                "verification_method": "runtime-diagnostics",
                "preconditions": ["The isolated project is ready."],
                "roles_permissions": ["publisher role"],
                "configuration": ["publishing enabled"],
                "steps": ["Open the entrypoint.", "Publish the item."],
                "expected_results": [
                    "The publish surface is ready.",
                    "The item is published exactly once.",
                ],
                "variants": {
                    "positive": "covered",
                    "negative": "covered",
                    "boundary": "covered",
                    "state": "covered",
                    "permission": "covered",
                    "concurrency": "covered",
                    "timing": "not_applicable",
                    "recovery": "covered",
                    "compatibility": "not_applicable",
                },
                "cleanup_reset": "Delete the synthetic item.",
                "idempotency": "Repeated publication is a no-op.",
                "side_effect_boundary": "Only the synthetic item may change.",
                "pass_criteria": ["The item is published exactly once."],
                "evidence_requirements": ["runtime_diagnostics"],
                "freshness_rule": "Evidence matches the source fingerprint.",
                "invalidation_triggers": ["The publish contract changes"],
                "flake_risks": [],
                "residual_risk": "none",
            }
        )
        coverage["rows"].append(
            {
                "coverage_id": coverage_id,
                "requirement_ref": "REQ-001",
                "obligation_ref": "TO-001",
                "capability_ref": "CAP-001",
                "scenario_ref": "SCN-001",
                "test_case_ref": case_id,
                "test_data_refs": data_refs,
                "evidence_refs": [evidence_ref],
                "acceptance_refs": ["HA-001"],
                "gap_refs": [],
                "status": "covered",
            }
        )

    datasets: list[dict[str, object]] = []
    if with_data:
        datasets.append(
            {
                "test_data_id": "TD-001",
                "name": "Publish synthetic seed",
                "kind": "synthetic",
                "sensitivity": "sanitized",
                "contains_pii": False,
                "source": "generated",
                "disposition": "generate",
                "readiness": "ready",
                "provenance_refs": [],
                "format": "json",
                "schema_ref": "publish-item-schema.json",
                "volume": "one item",
                "relationships": ["item belongs to a synthetic tenant"],
                "constraints": ["non-production identifiers only"],
                "license": "project-generated",
                "usage_limits": "isolated environments only",
                "fixed_seed": "42",
                "distribution": "one deterministic record",
                "edge_partitions": ["draft state"],
                "checksum": "sha256 generated with the fixture",
                "allowed_usage": ["review", "automated test"],
                "environment_refs": ["isolated review runtime"],
                "snapshot_binding": "current source fingerprint",
                "refresh_policy": "regenerate when the schema changes",
                "cleanup_reset": "delete the synthetic item",
                "oracle_binding": "published exactly once",
                "limitations": [],
                "residual_risk": "none",
                "generation_recipe": "Generate one item with fixed seed 42.",
                "applicable_test_case_ids": case_ids,
                "applicable_scenario_ids": ["SCN-001"],
                "hygiene": {
                    "classification_reason": "Synthetic records only",
                    "sanitization_status": "not_required",
                    "retention_policy": "ephemeral",
                },
            }
        )
    data_manifest = {
        "version": 1,
        "artifact": "test-data-manifest",
        "datasets": datasets,
    }
    return universe, catalog, data_manifest, coverage


def _publish_test_design_handoff(
    project: Path,
    feature: Path,
    *,
    with_data: bool = True,
    with_deferred_gap: bool = False,
) -> dict[str, object]:
    test_design = feature / "test-design"
    test_design.mkdir()
    artifact_root = "specs/001-test-design/test-design"
    fingerprint = _source_fingerprint(project, artifact_root)
    evidence_ref = _publish_evidence(project)
    universe, catalog, data_manifest, coverage = _test_design_bundle(
        with_data=with_data,
        evidence_ref=evidence_ref,
    )
    deferred_gap = {
        "gap_id": "GAP-001",
        "category": "coverage",
        "severity": "low",
        "disposition": "deferred",
        "source_refs": ["REQ-001"],
        "affected_obligation_refs": ["TO-001"],
        "coverage_refs": [row["coverage_id"] for row in coverage["rows"]],
        "affected_test_case_refs": [],
        "affected_test_data_refs": [],
        "owner": "test-design leader",
        "residual_risk": "The declared behavior remains deferred.",
        "next_action": "Implement the deferred behavior in a later revision.",
        "unblock_criteria": "The deferred behavior has executable coverage.",
    }
    if with_deferred_gap:
        universe["obligations"][0]["applicability"] = "deferred"
        universe["obligations"][0]["gap_refs"] = ["GAP-001"]
        for row in coverage["rows"]:
            row["status"] = "deferred"
            row["gap_refs"] = ["GAP-001"]
    gaps = {
        "schema_version": "spec-kit-test-design-gaps-v1",
        "status": "qualified" if with_deferred_gap else "clear",
        "gaps": [deferred_gap] if with_deferred_gap else [],
    }
    bundle_payloads = {
        "test-universe.json": universe,
        "test-catalog.json": catalog,
        "test-data-manifest.json": data_manifest,
        "coverage-matrix.json": coverage,
        "test-gaps.json": gaps,
    }
    bundle_digests = {
        name: _sha256(_write_json(test_design / name, payload))
        for name, payload in bundle_payloads.items()
    }
    discovery_ref = "lane-results/LANE-001.json"
    discovery_result = {
        "lane_id": "LANE-001",
        "attempt_id": "ATTEMPT-001",
        "status": "success",
        "inspected_paths": ["specs/001-test-design/plan.md"],
        "evidence_refs": [evidence_ref],
        "obligation_results": [
            {
                "obligation_id": "TO-001",
                "status": "gap" if with_deferred_gap else "covered",
                "evidence_refs": [evidence_ref],
                "gap_refs": ["GAP-001"] if with_deferred_gap else [],
                "summary": "The publish obligation is accounted for.",
            }
        ],
        "checks": [],
        "candidate_cases": [],
        "data_requirements": [],
        "contradictions": [],
        "unknowns": [],
        "gaps": [deferred_gap] if with_deferred_gap else [],
        "findings": [],
        "summary": "Discovery covered the frozen obligation.",
    }
    discovery_raw = _write_json(test_design / discovery_ref, discovery_result)
    audit_read_paths = [
        f"{artifact_root}/test-universe.json",
        f"{artifact_root}/test-catalog.json",
        f"{artifact_root}/test-data-manifest.json",
        f"{artifact_root}/coverage-matrix.json",
        f"{artifact_root}/test-gaps.json",
    ]
    audit_result = {
        "lane_id": "AUDIT-001",
        "attempt_id": "ATTEMPT-002",
        "status": "success",
        "inspected_paths": audit_read_paths,
        "evidence_refs": [evidence_ref],
        "obligation_results": [
            {
                "obligation_id": "TO-001",
                "status": "gap" if with_deferred_gap else "covered",
                "evidence_refs": [evidence_ref],
                "gap_refs": ["GAP-001"] if with_deferred_gap else [],
                "summary": "The frozen obligation is fully accounted for.",
            }
        ],
        "checks": [
            {
                "check_id": check_id,
                "status": "passed",
                "evidence_refs": [evidence_ref],
                "affected_obligation_refs": ["TO-001"],
                "finding_refs": [],
                "summary": f"{check_id} passed against registered evidence.",
            }
            for check_id in AUDIT_CORE_CHECK_IDS
        ],
        "candidate_cases": [],
        "data_requirements": [],
        "contradictions": [],
        "unknowns": [],
        "gaps": [],
        "findings": [],
        "summary": "The current bundle is internally consistent.",
    }
    audit_ref = "lane-results/AUDIT-001.json"
    audit_raw = _write_json(test_design / audit_ref, audit_result)
    audit_digest = _sha256(audit_raw)
    manifest = {
        "version": 1,
        "artifact": "test-design-lane-manifest",
        "generation_id": "tdg-" + fingerprint[:16],
        "status": "accepted",
        "leader_id": "leader-1",
        "synthesis_owner_id": "leader-1",
        "synthesis_artifact_digests": bundle_digests,
        "lanes": [
            {
                "lane_id": "LANE-001",
                "kind": "discovery",
                "title": "Publish obligation discovery",
                "state": "accepted",
                "obligation_ids": ["TO-001"],
                "read_paths": ["specs/001-test-design/plan.md"],
                "questions": ["What behavior must publishing preserve?"],
                "worker_id": "discovery-worker",
                "attempt_id": "ATTEMPT-001",
                "attempt_number": 1,
                "checkpoint_sequence": 1,
                "checkpoint_ref": "lane-checkpoints/LANE-001.json",
                "result_ref": discovery_ref,
                "result_sha256": _sha256(discovery_raw),
                "yield_history": [],
            },
            {
                "lane_id": "AUDIT-001",
                "kind": "audit",
                "title": "Independent bundle audit",
                "state": "accepted",
                "obligation_ids": ["TO-001"],
                "read_paths": audit_read_paths,
                "questions": ["Is the bundle complete and current?"],
                "worker_id": "independent-auditor",
                "attempt_id": "ATTEMPT-002",
                "attempt_number": 1,
                "checkpoint_sequence": 0,
                "checkpoint_ref": None,
                "result_ref": audit_ref,
                "result_sha256": audit_digest,
                "source_fingerprint": fingerprint,
                "artifact_digests": bundle_digests,
                "yield_history": [],
            }
        ],
    }
    _write_json(test_design / "lane-manifest.json", manifest)
    state = {
        "schema_version": "spec-kit-test-design-state-v1",
        "revision": 9,
        "scope": "feature",
        "mode": "feature",
        "feature_dir": "specs/001-test-design",
        "artifact_root": artifact_root,
        "status": "complete",
        "phase": "handed-off",
        "claim_status": (
            "qualified_with_declared_gaps"
            if with_deferred_gap
            else "complete_against_frozen_scope"
        ),
        "source": {
            "query": "publish test design",
            "source_refs": ["specs/001-test-design/plan.md"],
            "included_paths": ["specs/001-test-design/plan.md"],
            "excluded_paths": [],
            "risk_dimensions": ["functional"],
            "fingerprint": fingerprint,
        },
        "lanes": {
            "manifest_ref": "lane-manifest.json",
            "accepted_result_refs": [discovery_ref, audit_ref],
        },
        "audit": {
            "status": "accepted",
            "lane_id": "AUDIT-001",
            "result_ref": audit_ref,
        },
        "blockers": [],
    }
    state_raw = _write_json(test_design / "test-state.json", state)
    artifact_digests = {
        "state": _sha256(state_raw),
        "universe": bundle_digests["test-universe.json"],
        "catalog": bundle_digests["test-catalog.json"],
        "data_manifest": bundle_digests["test-data-manifest.json"],
        "coverage_matrix": bundle_digests["coverage-matrix.json"],
        "gaps": bundle_digests["test-gaps.json"],
        "audit_result": audit_digest,
    }
    handoff = {
        "schema_version": "spec-kit-test-design-handoff-v1",
        "source_fingerprint": fingerprint,
        "state_revision": 9,
        "claim_status": (
            "qualified_with_declared_gaps"
            if with_deferred_gap
            else "complete_against_frozen_scope"
        ),
        "artifact_refs": {
            "state": "test-state.json",
            "universe": "test-universe.json",
            "catalog": "test-catalog.json",
            "data_manifest": "test-data-manifest.json",
            "coverage_matrix": "coverage-matrix.json",
        },
        "artifact_digests": artifact_digests,
        "test_case_refs": [
            "test-catalog.json#/cases/TC-001",
            "test-catalog.json#/cases/TC-002",
        ],
        "test_data_refs": (
            ["test-data-manifest.json#/datasets/TD-001"] if with_data else []
        ),
        "gap_ref": "test-gaps.json",
        "audit_result_ref": audit_ref,
        "next_command": "/sp.tasks",
    }
    handoff_raw = _write_json(test_design / "handoff-to-tasks.json", handoff)
    assert handoff_raw
    return task_authoring._verify_published_test_design_handoff(project, feature)


def _publish_plan_test_design_projection_binding(
    project: Path,
    feature: Path,
    handoff: dict[str, object],
) -> dict[str, object]:
    feature_ref = feature.relative_to(project).as_posix()
    artifact_root = str(handoff["artifact_root"])
    publication_ref = f"{artifact_root}/test-design-publication.json"
    publication = handoff["publication_payload"]
    publication_raw = task_authoring._go_json_bytes(publication, pretty=True)
    (project / publication_ref).write_bytes(publication_raw)
    publication_sha256 = _sha256(publication_raw)

    basis_ref = f"{feature_ref}/spec-contract.json"
    basis_sha256 = _sha256((feature / "spec-contract.json").read_bytes())
    selection = {
        "obligation_refs": ["test-universe.json#/obligations/TO-001"],
        "test_case_refs": handoff["test_case_refs"],
        "test_data_refs": handoff["test_data_refs"],
        "coverage_refs": [
            "coverage-matrix.json#/rows/COV-001",
            "coverage-matrix.json#/rows/COV-002",
        ],
        "gap_refs": (
            ["test-gaps.json#/gaps/GAP-001"]
            if handoff["claim_status"] == "qualified_with_declared_gaps"
            else []
        ),
    }
    selection_sha256 = task_authoring._canonical_json_sha256(selection)
    projection_id = "tdproj-" + task_authoring._canonical_json_sha256(
        {
            "consumer": "plan",
            "basis_ref": basis_ref,
            "selection_sha256": selection_sha256,
        }
    )[:24]
    projection_ref = f"{artifact_root}/projections/{projection_id}.json"
    projection = {
        "schema_version": "spec-kit-test-design-projection-v1",
        "projection_id": projection_id,
        "publication_ref": publication_ref,
        "publication_sha256": publication_sha256,
        "consumer": "plan",
        "basis_ref": basis_ref,
        "basis_sha256": basis_sha256,
        "scope": "feature",
        "artifact_root": artifact_root,
        "source_fingerprint": handoff["source_fingerprint"],
        "state_revision": handoff["state_revision"],
        "claim_status": handoff["claim_status"],
        "selection": selection,
        "selection_sha256": selection_sha256,
        "forbidden_claims": publication["forbidden_claims"],
        "test_execution_status": "not_executed_by_test_design",
    }
    projection_raw = task_authoring._go_json_bytes(projection, pretty=True)
    projection_path = project / projection_ref
    projection_path.parent.mkdir(parents=True, exist_ok=True)
    projection_path.write_bytes(projection_raw)
    return {
        "publication_ref": publication_ref,
        "publication_sha256": publication_sha256,
        "projection_ref": projection_ref,
        "projection_sha256": _sha256(projection_raw),
        "source_fingerprint": handoff["source_fingerprint"],
        "state_revision": handoff["state_revision"],
    }


def _reseal_audit_result(feature: Path, audit_result: dict[str, object]) -> None:
    test_design = feature / "test-design"
    audit_ref = "lane-results/AUDIT-001.json"
    audit_raw = _write_json(test_design / audit_ref, audit_result)
    audit_sha256 = _sha256(audit_raw)
    manifest_path = test_design / "lane-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit_lane = next(
        lane for lane in manifest["lanes"] if lane["lane_id"] == "AUDIT-001"
    )
    audit_lane["result_sha256"] = audit_sha256
    _write_json(manifest_path, manifest)
    handoff_path = test_design / "handoff-to-tasks.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["artifact_digests"]["audit_result"] = audit_sha256
    _write_json(handoff_path, handoff)


def _all_test_design_refs_task() -> dict[str, object]:
    return _task(
        case_refs=[
            "test-catalog.json#/cases/TC-001",
            "test-catalog.json#/cases/TC-002",
        ],
        data_refs=["test-data-manifest.json#/datasets/TD-001"],
    )


def _task(
    *,
    case_refs: list[str],
    data_refs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": "T001",
        "objective": "Implement the tested publish flow",
        "dependencies": [],
        "expected_write_scope": ["src/publish.py"],
        "required_refs": ["docs/test-design.md"],
        "acceptance": ["Publish flow matches the authored test design"],
        "verification": ["pytest tests/unit/test_publish.py -q"],
        "test_case_refs": case_refs,
        "test_data_refs": data_refs or [],
    }


def _build(
    project: Path,
    feature: Path,
    task: dict[str, object],
    **root_fields: object,
):
    definition = {
        "title": "Test design consumption",
        "source_revision": 7,
        "tasks": [task],
        **root_fields,
    }
    return _invoke(
        project,
        [
            "tasks",
            "build",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--definition-json",
            json.dumps(definition),
            "--format",
            "json",
        ],
    )


def _set_task_status(feature: Path, status: str) -> None:
    task_index_path = feature / "task-index.json"
    task_index = json.loads(task_index_path.read_text(encoding="utf-8"))
    task_index["tasks"][0]["status"] = status
    _write_json(task_index_path, task_index)


def test_tasks_surfaces_treat_optional_test_design_handoff_as_authoritative_input() -> (
    None
):
    classic = _read("templates/commands/tasks.md").lower()
    advanced = _read("templates/advanced-skills/spx-tasks/SKILL.md").lower()

    for content in (classic, advanced):
        assert "test-design handoff" in content
        assert "authoritative input" in content
        assert "test_case_refs" in content
        assert "test_data_refs" in content

    packet_template = json.loads(_read("templates/task-packet-template.json"))
    assert packet_template["test_design_handoff_ref"] is None
    assert packet_template["test_design_handoff_sha256"] is None
    assert packet_template["test_design_source_fingerprint"] is None
    assert packet_template["test_design_state_revision"] is None
    assert packet_template["test_design_artifact_digests"] == {}


def test_tasks_build_binds_current_test_design_handoff_and_preserves_refs(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    expected = _publish_test_design_handoff(project, feature)
    task = _task(
        case_refs=[
            "test-catalog.json#/cases/TC-001",
            "test-catalog.json#/cases/TC-002",
        ],
        data_refs=["test-data-manifest.json#/datasets/TD-001"],
    )
    result = _build(project, feature, task)

    assert result.exit_code == 0, result.output
    task_index = json.loads((feature / "task-index.json").read_text(encoding="utf-8"))
    authored_task = task_index["tasks"][0]
    assert authored_task["test_case_refs"] == [
        "test-catalog.json#/cases/TC-001",
        "test-catalog.json#/cases/TC-002",
    ]
    assert authored_task["test_data_refs"] == [
        "test-data-manifest.json#/datasets/TD-001",
    ]
    assert task_index["test_design_handoff_ref"] == expected["ref"]
    assert task_index["test_design_handoff_sha256"] == expected["sha256"]
    assert (
        task_index["test_design_source_fingerprint"]
        == expected["source_fingerprint"]
    )
    assert task_index["test_design_state_revision"] == expected["state_revision"]
    assert (
        task_index["test_design_artifact_digests"]
        == expected["artifact_digests"]
    )
    tasks_markdown = (feature / "tasks.md").read_text(encoding="utf-8")
    assert (
        "| test_case_refs | `test-catalog.json#/cases/TC-001`, "
        "`test-catalog.json#/cases/TC-002` |"
    ) in tasks_markdown
    assert (
        "| test_data_refs | `test-data-manifest.json#/datasets/TD-001` |"
        in tasks_markdown
    )

    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output
    handed_off = _invoke(
        project,
        [
            "tasks",
            "handoff",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--target",
            "implement",
            "--format",
            "json",
        ],
    )
    assert handed_off.exit_code == 0, handed_off.output
    task_handoff = json.loads(
        (feature / "handoff-to-implement.json").read_text(encoding="utf-8")
    )
    assert task_handoff["test_design_handoff_ref"] == expected["ref"]
    assert task_handoff["test_design_handoff_sha256"] == expected["sha256"]
    assert (
        task_handoff["test_design_source_fingerprint"]
        == expected["source_fingerprint"]
    )
    assert task_handoff["test_design_state_revision"] == 9


def test_tasks_build_rejects_test_refs_without_a_handoff(tmp_path: Path) -> None:
    project, feature = _project(tmp_path)

    result = _build(
        project,
        feature,
        _task(case_refs=["test-catalog.json#/cases/TC-001"]),
    )

    assert result.exit_code == 10
    assert "require a current test-design/handoff-to-tasks.json" in result.output


def test_tasks_build_rejects_foreign_case_and_data_refs(tmp_path: Path) -> None:
    for name, case_refs, data_refs, expected in (
        (
            "case",
            ["test-catalog.json#/cases/TC-404"],
            [],
            "test_case_ref",
        ),
        (
            "data",
            ["test-catalog.json#/cases/TC-001"],
            ["test-data-manifest.json#/datasets/TD-404"],
            "test_data_ref",
        ),
    ):
        project, feature = _project(tmp_path / name)
        _publish_test_design_handoff(project, feature)

        result = _build(
            project,
            feature,
            _task(case_refs=case_refs, data_refs=data_refs),
        )

        assert result.exit_code == 10
        assert expected in result.output
        assert "not a member of the test-design handoff" in result.output


def test_tasks_build_rejects_an_existing_unhanded_test_design_root(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    test_design = feature / "test-design"
    test_design.mkdir()
    _write_json(
        test_design / "test-state.json",
        {
            "schema_version": "spec-kit-test-design-state-v1",
            "revision": 1,
            "status": "active",
            "phase": "scoped",
        },
    )

    result = _build(project, feature, _task(case_refs=[]))

    assert result.exit_code == 10
    assert "workspace exists without a current" in result.output


@pytest.mark.parametrize("decision", ["selected", "required"])
def test_tasks_build_rejects_a_plan_selected_test_design_without_feature_handoff(
    tmp_path: Path,
    decision: str,
) -> None:
    project, feature = _project(tmp_path)
    plan_contract = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    plan_contract["test_design_gate"] = {
        "decision": decision,
        "reason_refs": ["spec-contract.json#/acceptance/AC-001"],
        "projection_binding": {
            "publication_ref": None,
            "publication_sha256": None,
            "projection_ref": None,
            "projection_sha256": None,
            "source_fingerprint": None,
            "state_revision": None,
        },
    }
    _write_json(feature / "plan-contract.json", plan_contract)

    result = _build(project, feature, _task(case_refs=[]))

    assert result.exit_code == 10
    assert "test-design" in result.output.lower()
    assert decision in result.output.lower()
    assert "handoff-to-tasks.json" in result.output


def test_tasks_build_allows_an_explicitly_unselected_test_design_without_root(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    plan_contract = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    plan_contract["test_design_gate"] = {
        "decision": "not_selected",
        "reason_refs": [],
        "projection_binding": {
            "publication_ref": None,
            "publication_sha256": None,
            "projection_ref": None,
            "projection_sha256": None,
            "source_fingerprint": None,
            "state_revision": None,
        },
    }
    _write_json(feature / "plan-contract.json", plan_contract)

    result = _build(project, feature, _task(case_refs=[]))

    assert result.exit_code == 0, result.output


def test_tasks_build_rejects_an_unknown_plan_test_design_gate_decision(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    plan_contract = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    plan_contract["test_design_gate"] = {
        "decision": "sometimes",
        "reason_refs": [],
        "projection_binding": {
            "publication_ref": None,
            "publication_sha256": None,
            "projection_ref": None,
            "projection_sha256": None,
            "source_fingerprint": None,
            "state_revision": None,
        },
    }
    _write_json(feature / "plan-contract.json", plan_contract)

    result = _build(project, feature, _task(case_refs=[]))

    assert result.exit_code == 10
    assert "test_design_gate.decision" in result.output


def test_tasks_build_rejects_conflicting_plan_test_design_gate_paths(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    root_plan = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    root_plan["test_design_gate"] = {
        "decision": "not_selected",
        "reason_refs": [],
        "projection_binding": {
            "publication_ref": None,
            "publication_sha256": None,
            "projection_ref": None,
            "projection_sha256": None,
            "source_fingerprint": None,
            "state_revision": None,
        },
    }
    _write_json(feature / "plan-contract.json", root_plan)
    nested_plan = dict(root_plan)
    nested_plan["test_design_gate"] = {
        **root_plan["test_design_gate"],
        "decision": "required",
    }
    _write_json(feature / "plan" / "plan-contract.json", nested_plan)

    result = _build(project, feature, _task(case_refs=[]))

    assert result.exit_code == 10
    assert "conflicting plan-contract test_design_gate decisions" in result.output


def test_tasks_build_rejects_a_partial_plan_projection_binding(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    plan_contract = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    plan_contract["test_design_gate"] = {
        "decision": "selected",
        "reason_refs": ["spec-contract.json#/acceptance/AC-001"],
        "projection_binding": {
            "publication_ref": "test-design/test-design-publication.json",
            "publication_sha256": None,
            "projection_ref": None,
            "projection_sha256": None,
            "source_fingerprint": None,
            "state_revision": None,
        },
    }
    _write_json(feature / "plan-contract.json", plan_contract)

    result = _build(project, feature, _task(case_refs=[]))

    assert result.exit_code == 10
    assert "entirely null or entirely populated" in result.output


def test_tasks_build_allows_a_current_populated_plan_projection_binding(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    handoff = _publish_test_design_handoff(project, feature)
    projection_binding = _publish_plan_test_design_projection_binding(
        project, feature, handoff
    )
    plan_contract = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    plan_contract["test_design_gate"] = {
        "decision": "selected",
        "reason_refs": ["spec-contract.json#/acceptance/AC-001"],
        "projection_binding": projection_binding,
    }
    _write_json(feature / "plan-contract.json", plan_contract)

    result = _build(project, feature, _all_test_design_refs_task())

    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (
            lambda binding: binding.__setitem__(
                "publication_ref", ".specify/test-design/test-design-publication.json"
            ),
            "publication_ref is foreign or stale",
        ),
        (
            lambda binding: binding.__setitem__("publication_sha256", "0" * 64),
            "publication_sha256 is stale",
        ),
        (
            lambda binding: binding.__setitem__(
                "projection_ref",
                ".specify/features/foreign/test-design/projections/tdproj-foreign.json",
            ),
            "projection_ref is foreign or stale",
        ),
        (
            lambda binding: binding.__setitem__("projection_sha256", "0" * 64),
            "projection_sha256 is stale",
        ),
        (
            lambda binding: binding.__setitem__("source_fingerprint", "0" * 64),
            "projection_binding.source_fingerprint is stale",
        ),
        (
            lambda binding: binding.__setitem__("state_revision", 404),
            "state_revision is stale",
        ),
    ],
)
def test_tasks_build_rejects_stale_or_foreign_populated_plan_projection_binding(
    tmp_path: Path,
    mutator,
    expected: str,
) -> None:
    project, feature = _project(tmp_path)
    handoff = _publish_test_design_handoff(project, feature)
    projection_binding = _publish_plan_test_design_projection_binding(
        project, feature, handoff
    )
    mutator(projection_binding)
    plan_contract = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    plan_contract["test_design_gate"] = {
        "decision": "selected",
        "reason_refs": ["spec-contract.json#/acceptance/AC-001"],
        "projection_binding": projection_binding,
    }
    _write_json(feature / "plan-contract.json", plan_contract)

    result = _build(project, feature, _all_test_design_refs_task())

    assert result.exit_code == 10
    assert expected in result.output


def test_tasks_build_rejects_projection_binding_with_stale_projection_consumer_or_basis(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    handoff = _publish_test_design_handoff(project, feature)
    projection_binding = _publish_plan_test_design_projection_binding(
        project, feature, handoff
    )
    projection_path = project / projection_binding["projection_ref"]
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    projection["consumer"] = "quick"
    _write_json(projection_path, projection)
    projection_binding["projection_sha256"] = _sha256(projection_path.read_bytes())
    plan_contract = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    plan_contract["test_design_gate"] = {
        "decision": "selected",
        "reason_refs": ["spec-contract.json#/acceptance/AC-001"],
        "projection_binding": projection_binding,
    }
    _write_json(feature / "plan-contract.json", plan_contract)

    wrong_consumer = _build(project, feature, _all_test_design_refs_task())

    assert wrong_consumer.exit_code == 10
    assert "must target the plan consumer" in wrong_consumer.output

    projection_binding = _publish_plan_test_design_projection_binding(
        project, feature, handoff
    )
    projection_path = project / projection_binding["projection_ref"]
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    projection["basis_ref"] = "specs/foreign/spec-contract.json"
    _write_json(projection_path, projection)
    projection_binding["projection_sha256"] = _sha256(projection_path.read_bytes())
    plan_contract["test_design_gate"]["projection_binding"] = projection_binding
    _write_json(feature / "plan-contract.json", plan_contract)

    wrong_basis = _build(project, feature, _all_test_design_refs_task())

    assert wrong_basis.exit_code == 10
    assert "basis_ref must target the current feature spec-contract.json" in wrong_basis.output


@pytest.mark.parametrize(
    "mutator",
    [
        lambda projection: projection.__setitem__(
            "projection_id", "tdproj-" + "f" * 24
        ),
        lambda projection: projection["selection"].__setitem__(
            "test_case_refs", []
        ),
        lambda projection: projection.__setitem__(
            "selection_sha256", "0" * 64
        ),
        lambda projection: projection.__setitem__(
            "forbidden_claims", ["tests_executed"]
        ),
    ],
)
def test_tasks_build_rejects_resealed_noncanonical_plan_projection(
    tmp_path: Path,
    mutator,
) -> None:
    project, feature = _project(tmp_path)
    handoff = _publish_test_design_handoff(project, feature)
    projection_binding = _publish_plan_test_design_projection_binding(
        project, feature, handoff
    )
    projection_path = project / projection_binding["projection_ref"]
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    mutator(projection)
    projection_raw = task_authoring._go_json_bytes(projection, pretty=True)
    projection_path.write_bytes(projection_raw)
    projection_binding["projection_sha256"] = _sha256(projection_raw)
    plan_contract = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    plan_contract["test_design_gate"] = {
        "decision": "selected",
        "reason_refs": ["spec-contract.json#/acceptance/AC-001"],
        "projection_binding": projection_binding,
    }
    _write_json(feature / "plan-contract.json", plan_contract)

    result = _build(project, feature, _all_test_design_refs_task())

    assert result.exit_code == 10
    assert "non-canonical" in result.output


def test_tasks_build_rejects_resealed_noncanonical_test_design_publication(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    handoff = _publish_test_design_handoff(project, feature)
    projection_binding = _publish_plan_test_design_projection_binding(
        project, feature, handoff
    )
    publication_path = project / projection_binding["publication_ref"]
    publication = json.loads(publication_path.read_text(encoding="utf-8"))
    publication["forbidden_claims"] = ["tests_executed"]
    publication_raw = task_authoring._go_json_bytes(publication, pretty=True)
    publication_path.write_bytes(publication_raw)
    projection_binding["publication_sha256"] = _sha256(publication_raw)

    projection_path = project / projection_binding["projection_ref"]
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    projection["publication_sha256"] = projection_binding["publication_sha256"]
    projection_raw = task_authoring._go_json_bytes(projection, pretty=True)
    projection_path.write_bytes(projection_raw)
    projection_binding["projection_sha256"] = _sha256(projection_raw)
    plan_contract = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    plan_contract["test_design_gate"] = {
        "decision": "selected",
        "reason_refs": ["spec-contract.json#/acceptance/AC-001"],
        "projection_binding": projection_binding,
    }
    _write_json(feature / "plan-contract.json", plan_contract)

    result = _build(project, feature, _all_test_design_refs_task())

    assert result.exit_code == 10
    assert "publication is stale, non-canonical" in result.output


def test_tasks_build_rejects_conflicting_plan_test_design_gate_bindings(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    handoff = _publish_test_design_handoff(project, feature)
    root_binding = _publish_plan_test_design_projection_binding(
        project, feature, handoff
    )
    nested_binding = dict(root_binding)
    nested_binding["projection_sha256"] = "d" * 64
    root_plan = json.loads(
        (feature / "plan-contract.json").read_text(encoding="utf-8")
    )
    root_plan["test_design_gate"] = {
        "decision": "selected",
        "reason_refs": ["spec-contract.json#/acceptance/AC-001"],
        "projection_binding": root_binding,
    }
    _write_json(feature / "plan-contract.json", root_plan)
    nested_plan = dict(root_plan)
    nested_plan["test_design_gate"] = {
        **root_plan["test_design_gate"],
        "projection_binding": nested_binding,
    }
    _write_json(feature / "plan" / "plan-contract.json", nested_plan)

    result = _build(project, feature, _all_test_design_refs_task())

    assert result.exit_code == 10
    assert "conflicting plan-contract test_design_gate bindings" in result.output


def test_test_design_evidence_record_identity_and_rfc3339_are_verified(
    tmp_path: Path,
) -> None:
    for name, mutation, expected in (
        (
            "metadata",
            lambda record: record.update({"source": "forged source"}),
            "identity is forged",
        ),
        (
            "created-at",
            lambda record: record.update({"created_at": "not-a-time"}),
            "created_at is not RFC3339",
        ),
    ):
        project, feature = _project(tmp_path / name)
        _publish_test_design_handoff(project, feature)
        record_path = next(
            (project / ".specify" / "evidence" / "records").glob("evd-*.json")
        )
        record = json.loads(record_path.read_text(encoding="utf-8"))
        mutation(record)
        _write_json(record_path, record)

        result = _build(project, feature, _all_test_design_refs_task())

        assert result.exit_code == 10
        assert expected in result.output


def test_tasks_build_rejects_empty_or_self_owned_audit(tmp_path: Path) -> None:
    empty_project, empty_feature = _project(tmp_path / "empty")
    _publish_test_design_handoff(empty_project, empty_feature)
    audit_path = (
        empty_feature / "test-design" / "lane-results" / "AUDIT-001.json"
    )
    empty_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    empty_audit["evidence_refs"] = []
    empty_audit["obligation_results"] = []
    empty_audit["checks"] = []
    _reseal_audit_result(empty_feature, empty_audit)

    empty_result = _build(
        empty_project, empty_feature, _all_test_design_refs_task()
    )

    assert empty_result.exit_code == 10
    assert "audit result" in empty_result.output

    self_project, self_feature = _project(tmp_path / "self")
    _publish_test_design_handoff(self_project, self_feature)
    manifest_path = self_feature / "test-design" / "lane-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit_lane = next(
        lane for lane in manifest["lanes"] if lane["lane_id"] == "AUDIT-001"
    )
    audit_lane["worker_id"] = manifest["leader_id"]
    _write_json(manifest_path, manifest)

    self_result = _build(
        self_project, self_feature, _all_test_design_refs_task()
    )

    assert self_result.exit_code == 10
    assert "worker is not independent" in self_result.output


def test_audit_passed_core_check_requires_verified_evidence(tmp_path: Path) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature)
    audit_path = feature / "test-design" / "lane-results" / "AUDIT-001.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit["checks"][0]["evidence_refs"] = []
    _reseal_audit_result(feature, audit)

    result = _build(project, feature, _all_test_design_refs_task())

    assert result.exit_code == 10
    assert "passed status requires verified evidence" in result.output


@pytest.mark.parametrize(
    ("canonical_gaps", "expected_error"),
    [
        ({}, "references missing canonical gap GAP-001"),
        (
            {
                "GAP-001": {
                    "disposition": "resolved",
                    "affected_obligation_refs": ["TO-001"],
                }
            },
            "references inactive canonical gap GAP-001",
        ),
        (
            {
                "GAP-001": {
                    "disposition": "deferred",
                    "affected_obligation_refs": ["TO-002"],
                }
            },
            "canonical gap GAP-001 does not affect TO-001",
        ),
    ],
)
def test_audit_obligation_gap_refs_require_active_matching_canonical_gap(
    tmp_path: Path,
    canonical_gaps: dict[str, dict[str, object]],
    expected_error: str,
) -> None:
    obligation_results = [
        {
            "obligation_id": "TO-001",
            "status": "gap",
            "evidence_refs": [],
            "gap_refs": ["GAP-001"],
            "summary": "The obligation is accounted for by a declared gap.",
        }
    ]

    with pytest.raises(task_authoring.TaskAuthoringError, match=expected_error):
        task_authoring._validate_test_design_audit_obligations(
            tmp_path,
            obligation_results,
            lane_id="AUDIT-001",
            obligation_ids={"TO-001"},
            canonical_gaps=canonical_gaps,
        )


def test_tasks_accepts_qualified_handoff_with_canonical_deferred_audit_gap(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature, with_deferred_gap=True)

    result = _build(project, feature, _all_test_design_refs_task())

    assert result.exit_code == 0, result.output


def test_claim_classification_does_not_qualify_not_applicable_or_recipe_ready() -> (
    None
):
    universe, catalog, data_manifest, coverage = _test_design_bundle(
        with_data=True,
        evidence_ref=".specify/evidence/records/evd-000000000000000000000000.json",
    )
    coverage["rows"][0]["status"] = "not_applicable"
    data_manifest["datasets"][0]["readiness"] = "recipe-ready"
    gaps = {
        "schema_version": "spec-kit-test-design-gaps-v1",
        "status": "clear",
        "gaps": [],
    }

    assert (
        task_authoring._classify_test_design_claim(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
            gaps=gaps,
        )
        == "complete_against_frozen_scope"
    )


def test_gap_matrix_and_qualified_claim_require_real_bidirectional_gaps() -> None:
    evidence_ref = ".specify/evidence/records/evd-000000000000000000000000.json"
    universe, catalog, data_manifest, coverage = _test_design_bundle(
        with_data=True,
        evidence_ref=evidence_ref,
    )
    gaps = {
        "schema_version": "spec-kit-test-design-gaps-v1",
        "status": "clear",
        "gaps": [],
    }
    coverage["rows"][0]["status"] = "partial"
    with pytest.raises(task_authoring.TaskAuthoringError, match="requires gap_refs"):
        task_authoring._validate_test_design_gap_links_and_qualifiers(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
            gaps=gaps,
        )

    universe, catalog, data_manifest, coverage = _test_design_bundle(
        with_data=True,
        evidence_ref=evidence_ref,
    )
    coverage["rows"][0]["status"] = "not_applicable"
    with pytest.raises(task_authoring.TaskAuthoringError, match="applicable obligation"):
        task_authoring._validate_test_design_gap_links_and_qualifiers(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
            gaps=gaps,
        )

    universe, catalog, data_manifest, coverage = _test_design_bundle(
        with_data=True,
        evidence_ref=evidence_ref,
    )
    catalog["cases"][0]["variants"]["negative"] = "deferred"
    with pytest.raises(task_authoring.TaskAuthoringError, match="deferred variant"):
        task_authoring._validate_test_design_gap_links_and_qualifiers(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
            gaps=gaps,
        )

    universe, catalog, data_manifest, coverage = _test_design_bundle(
        with_data=True,
        evidence_ref=evidence_ref,
    )
    data_manifest["datasets"][0]["readiness"] = "evidence-needed"
    with pytest.raises(
        task_authoring.TaskAuthoringError,
        match="affected_test_data_refs",
    ):
        task_authoring._validate_test_design_gap_links_and_qualifiers(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
            gaps=gaps,
        )

    universe, catalog, data_manifest, coverage = _test_design_bundle(
        with_data=True,
        evidence_ref=evidence_ref,
    )
    catalog["cases"][0]["variants"]["negative"] = "deferred"
    universe["obligations"][0]["gap_refs"] = ["GAP-001"]
    declared_gaps = {
        "schema_version": "spec-kit-test-design-gaps-v1",
        "status": "qualified",
        "gaps": [
            {
                "gap_id": "GAP-001",
                "category": "coverage",
                "severity": "low",
                "disposition": "deferred",
                "source_refs": ["REQ-001"],
                "affected_obligation_refs": ["TO-001"],
                "coverage_refs": [],
                "affected_test_case_refs": ["TC-001"],
                "affected_test_data_refs": [],
                "owner": "test-design leader",
                "residual_risk": "Deferred negative variant remains.",
                "next_action": "Implement the deferred variant later.",
                "unblock_criteria": "The variant is implemented.",
            }
        ],
    }
    task_authoring._validate_test_design_gap_links_and_qualifiers(
        universe=universe,
        catalog=catalog,
        data_manifest=data_manifest,
        coverage_matrix=coverage,
        gaps=declared_gaps,
    )


def test_gap_matrix_rejects_missing_or_inconsistent_active_coverage_gap() -> None:
    evidence_ref = ".specify/evidence/records/evd-000000000000000000000000.json"
    universe, catalog, data_manifest, coverage = _test_design_bundle(
        with_data=True,
        evidence_ref=evidence_ref,
    )
    coverage["rows"][0]["status"] = "partial"
    coverage["rows"][0]["gap_refs"] = ["GAP-404"]
    empty_gaps = {
        "schema_version": "spec-kit-test-design-gaps-v1",
        "status": "qualified",
        "gaps": [],
    }
    with pytest.raises(task_authoring.TaskAuthoringError, match="missing gap GAP-404"):
        task_authoring._validate_test_design_gap_links_and_qualifiers(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
            gaps=empty_gaps,
        )

    universe["obligations"][0]["gap_refs"] = ["GAP-001"]
    coverage["rows"][0]["gap_refs"] = ["GAP-001"]
    inconsistent_gaps = {
        "schema_version": "spec-kit-test-design-gaps-v1",
        "status": "qualified",
        "gaps": [
            {
                "gap_id": "GAP-001",
                "category": "coverage",
                "severity": "medium",
                "disposition": "deferred",
                "source_refs": ["REQ-001"],
                "affected_obligation_refs": ["TO-001"],
                "coverage_refs": ["COV-001"],
                "affected_test_case_refs": [],
                "affected_test_data_refs": [],
                "owner": "test-design leader",
                "residual_risk": "Partial coverage remains.",
                "next_action": "Complete the missing coverage.",
                "unblock_criteria": "The coverage row is covered.",
            }
        ],
    }
    with pytest.raises(task_authoring.TaskAuthoringError, match="inconsistent"):
        task_authoring._validate_test_design_gap_links_and_qualifiers(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
            gaps=inconsistent_gaps,
        )


def test_gap_matrix_rejects_applicable_obligation_without_coverage() -> None:
    evidence_ref = ".specify/evidence/records/evd-000000000000000000000000.json"
    universe, catalog, data_manifest, coverage = _test_design_bundle(
        with_data=True,
        evidence_ref=evidence_ref,
    )
    coverage["rows"] = []
    gaps = {
        "schema_version": "spec-kit-test-design-gaps-v1",
        "status": "clear",
        "gaps": [],
    }

    with pytest.raises(
        task_authoring.TaskAuthoringError,
        match="applicable obligation TO-001 is absent from the coverage matrix",
    ):
        task_authoring._validate_test_design_gap_links_and_qualifiers(
            universe=universe,
            catalog=catalog,
            data_manifest=data_manifest,
            coverage_matrix=coverage,
            gaps=gaps,
        )


def test_tasks_upsert_revalidates_tampered_test_design_artifacts(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature)
    task = _task(
        case_refs=[
            "test-catalog.json#/cases/TC-001",
            "test-catalog.json#/cases/TC-002",
        ],
        data_refs=["test-data-manifest.json#/datasets/TD-001"],
    )
    built = _build(project, feature, task)
    assert built.exit_code == 0, built.output
    catalog_path = feature / "test-design" / "test-catalog.json"
    catalog_path.write_bytes(catalog_path.read_bytes() + b" ")

    result = _invoke(
        project,
        [
            "tasks",
            "upsert",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--task-json",
            json.dumps(task),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 10
    assert "test-design handoff is stale or invalid" in result.output
    assert "stale" in result.output


def test_tasks_finalize_rejects_stale_sources(tmp_path: Path) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature)
    built = _build(
        project,
        feature,
        _task(
            case_refs=[
                "test-catalog.json#/cases/TC-001",
                "test-catalog.json#/cases/TC-002",
            ],
            data_refs=["test-data-manifest.json#/datasets/TD-001"],
        ),
    )
    assert built.exit_code == 0, built.output
    (feature / "plan.md").write_text("# Changed plan\n", encoding="utf-8")

    result = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 10
    assert "test-design sources are stale" in result.output


def test_tasks_finalize_requires_all_handoff_refs_to_be_consumed(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature)
    built = _build(
        project,
        feature,
        _task(
            case_refs=["test-catalog.json#/cases/TC-001"],
            data_refs=["test-data-manifest.json#/datasets/TD-001"],
        ),
    )
    assert built.exit_code == 0, built.output

    result = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 10
    assert "TC-002" in result.output
    assert "is not consumed by any task" in result.output


def test_tasks_finalize_allows_an_empty_handoff_data_set(tmp_path: Path) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature, with_data=False)
    built = _build(
        project,
        feature,
        _task(
            case_refs=[
                "test-catalog.json#/cases/TC-001",
                "test-catalog.json#/cases/TC-002",
            ]
        ),
    )
    assert built.exit_code == 0, built.output

    result = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output


def test_tasks_handoff_revalidates_the_accepted_audit_result(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature)
    built = _build(
        project,
        feature,
        _task(
            case_refs=[
                "test-catalog.json#/cases/TC-001",
                "test-catalog.json#/cases/TC-002",
            ],
            data_refs=["test-data-manifest.json#/datasets/TD-001"],
        ),
    )
    assert built.exit_code == 0, built.output
    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output
    audit_path = feature / "test-design" / "lane-results" / "AUDIT-001.json"
    audit_path.write_bytes(audit_path.read_bytes() + b" ")

    result = _invoke(
        project,
        [
            "tasks",
            "handoff",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--target",
            "implement",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 10
    assert "audit" in result.output.lower()
    assert "stale" in result.output.lower() or "digest" in result.output.lower()


def test_test_design_binding_fields_are_runtime_owned_and_cannot_be_bypassed(
    tmp_path: Path,
) -> None:
    authored_project, authored_feature = _project(tmp_path / "authored")
    _publish_test_design_handoff(authored_project, authored_feature)
    authored = _build(
        authored_project,
        authored_feature,
        _task(
            case_refs=[
                "test-catalog.json#/cases/TC-001",
                "test-catalog.json#/cases/TC-002",
            ],
            data_refs=["test-data-manifest.json#/datasets/TD-001"],
        ),
        test_design_handoff_sha256="0" * 64,
    )
    assert authored.exit_code == 10
    assert "test_design_handoff_sha256 is CLI-owned" in authored.output

    project, feature = _project(tmp_path / "patched")
    _publish_test_design_handoff(project, feature)
    task = _task(
        case_refs=[
            "test-catalog.json#/cases/TC-001",
            "test-catalog.json#/cases/TC-002",
        ],
        data_refs=["test-data-manifest.json#/datasets/TD-001"],
    )
    built = _build(project, feature, task)
    assert built.exit_code == 0, built.output
    protected_patch = _invoke(
        project,
        [
            "tasks",
            "set-root",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--patch-json",
            json.dumps({"test_design_state_revision": 404}),
            "--format",
            "json",
        ],
    )
    assert protected_patch.exit_code == 10
    assert "CLI-owned" in protected_patch.output

    task_index_path = feature / "task-index.json"
    task_index = json.loads(task_index_path.read_text(encoding="utf-8"))
    task_index["test_design_handoff_sha256"] = "0" * 64
    _write_json(task_index_path, task_index)
    bypass = _invoke(
        project,
        [
            "tasks",
            "set-root",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--patch-json",
            json.dumps({"semantic_delta": ["bounded update"]}),
            "--format",
            "json",
        ],
    )
    assert bypass.exit_code == 10
    assert "test-design binding is stale" in bypass.output


def test_jit_worker_packet_carries_test_design_refs_to_implement(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    expected = _publish_test_design_handoff(project, feature)
    built = _build(
        project,
        feature,
        _task(
            case_refs=[
                "test-catalog.json#/cases/TC-001",
                "test-catalog.json#/cases/TC-002",
            ],
            data_refs=["test-data-manifest.json#/datasets/TD-001"],
        ),
    )
    assert built.exit_code == 0, built.output
    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output

    packet = compile_worker_task_packet(
        project_root=project,
        feature_dir=feature,
        task_id="T001",
    )

    assert packet.test_case_refs == [
        "test-catalog.json#/cases/TC-001",
        "test-catalog.json#/cases/TC-002",
    ]
    assert packet.test_data_refs == [
        "test-data-manifest.json#/datasets/TD-001",
    ]
    assert packet.test_design_handoff_ref == expected["ref"]
    assert packet.test_design_handoff_sha256 == expected["sha256"]
    assert (
        packet.test_design_source_fingerprint
        == expected["source_fingerprint"]
    )
    assert packet.test_design_state_revision == expected["state_revision"]
    assert packet.test_design_artifact_digests == expected["artifact_digests"]


@pytest.mark.parametrize(
    ("field", "foreign_ref"),
    [
        ("test_case_refs", "test-catalog.json#/cases/TC-999"),
        ("test_data_refs", "test-data-manifest.json#/datasets/TD-999"),
    ],
)
def test_jit_worker_packet_rejects_foreign_test_design_refs_in_tasks_projection(
    tmp_path: Path,
    field: str,
    foreign_ref: str,
) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature)
    built = _build(project, feature, _all_test_design_refs_task())
    assert built.exit_code == 0, built.output
    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output
    tasks_path = feature / "tasks.md"
    rows = tasks_path.read_text(encoding="utf-8").splitlines()
    for index, row in enumerate(rows):
        if row.startswith(f"| {field} |"):
            rows[index] = row.rsplit(" |", 1)[0] + f", `{foreign_ref}` |"
            break
    else:
        raise AssertionError(f"tasks.md has no {field} projection")
    tasks_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    with pytest.raises(
        PacketValidationError,
        match=rf"tasks\.md {field} contains foreign canonical refs",
    ):
        compile_worker_task_packet(
            project_root=project,
            feature_dir=feature,
            task_id="T001",
        )


def test_jit_worker_packet_keeps_null_binding_without_test_design(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    built = _build(project, feature, _task(case_refs=[]))
    assert built.exit_code == 0, built.output
    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output

    packet = compile_worker_task_packet(
        project_root=project,
        feature_dir=feature,
        task_id="T001",
    )

    assert packet.test_design_handoff_ref is None
    assert packet.test_design_handoff_sha256 is None
    assert packet.test_design_source_fingerprint is None
    assert packet.test_design_state_revision is None
    assert packet.test_design_artifact_digests == {}


def test_jit_worker_packet_rejects_unhanded_test_design_started_after_finalize(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    built = _build(project, feature, _task(case_refs=[]))
    assert built.exit_code == 0, built.output
    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output
    test_design = feature / "test-design"
    test_design.mkdir()
    _write_json(
        test_design / "test-state.json",
        {
            "schema_version": "spec-kit-test-design-state-v1",
            "revision": 1,
            "status": "active",
            "phase": "scoped",
        },
    )

    with pytest.raises(PacketValidationError, match="workspace exists without"):
        compile_worker_task_packet(
            project_root=project,
            feature_dir=feature,
            task_id="T001",
        )


def test_jit_worker_packet_rejects_tamper_after_tasks_handoff(
    tmp_path: Path,
) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature)
    built = _build(
        project,
        feature,
        _task(
            case_refs=[
                "test-catalog.json#/cases/TC-001",
                "test-catalog.json#/cases/TC-002",
            ],
            data_refs=["test-data-manifest.json#/datasets/TD-001"],
        ),
    )
    assert built.exit_code == 0, built.output
    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output
    handed_off = _invoke(
        project,
        [
            "tasks",
            "handoff",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--target",
            "implement",
            "--format",
            "json",
        ],
    )
    assert handed_off.exit_code == 0, handed_off.output
    catalog_path = feature / "test-design" / "test-catalog.json"
    catalog_path.write_bytes(catalog_path.read_bytes() + b" ")

    with pytest.raises(PacketValidationError, match="test-design binding is invalid"):
        compile_worker_task_packet(
            project_root=project,
            feature_dir=feature,
            task_id="T001",
        )


@pytest.mark.parametrize(
    "not_started_status",
    ["pending", "ready", "deferred"],
)
def test_jit_worker_packet_rejects_source_drift_before_execution_starts(
    tmp_path: Path,
    not_started_status: str,
) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature)
    built = _build(project, feature, _all_test_design_refs_task())
    assert built.exit_code == 0, built.output
    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output
    _set_task_status(feature, not_started_status)
    (feature / "plan.md").write_text("# Changed plan\n", encoding="utf-8")

    with pytest.raises(PacketValidationError, match="test-design sources are stale"):
        compile_worker_task_packet(
            project_root=project,
            feature_dir=feature,
            task_id="T001",
        )


@pytest.mark.parametrize(
    "started_status",
    ["in_progress", "implemented", "accepted", "blocked", "failed"],
)
def test_jit_worker_packet_uses_bound_test_design_after_execution_starts(
    tmp_path: Path,
    started_status: str,
) -> None:
    project, feature = _project(tmp_path)
    expected = _publish_test_design_handoff(project, feature)
    built = _build(project, feature, _all_test_design_refs_task())
    assert built.exit_code == 0, built.output
    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output
    _set_task_status(feature, started_status)
    (feature / "plan.md").write_text("# Changed plan\n", encoding="utf-8")

    packet = compile_worker_task_packet(
        project_root=project,
        feature_dir=feature,
        task_id="T001",
    )

    assert packet.test_design_handoff_sha256 == expected["sha256"]
    assert (
        packet.test_design_source_fingerprint
        == expected["source_fingerprint"]
    )
    assert packet.test_design_artifact_digests == expected["artifact_digests"]


@pytest.mark.parametrize(
    ("tamper_target", "expected_error"),
    [
        ("test-catalog.json", "lane-manifest synthesis artifacts are stale"),
        (
            "handoff-to-tasks.json",
            "task-index test-design binding is stale",
        ),
    ],
)
def test_jit_worker_packet_rejects_canonical_test_design_tamper_after_start(
    tmp_path: Path,
    tamper_target: str,
    expected_error: str,
) -> None:
    project, feature = _project(tmp_path)
    _publish_test_design_handoff(project, feature)
    built = _build(project, feature, _all_test_design_refs_task())
    assert built.exit_code == 0, built.output
    finalized = _invoke(
        project,
        [
            "tasks",
            "finalize",
            "--feature-dir",
            str(feature.relative_to(project)),
            "--format",
            "json",
        ],
    )
    assert finalized.exit_code == 0, finalized.output
    _set_task_status(feature, "in_progress")
    (feature / "plan.md").write_text("# Changed plan\n", encoding="utf-8")
    target = feature / "test-design" / tamper_target
    target.write_bytes(target.read_bytes() + b" ")

    with pytest.raises(PacketValidationError, match=expected_error):
        compile_worker_task_packet(
            project_root=project,
            feature_dir=feature,
            task_id="T001",
        )
