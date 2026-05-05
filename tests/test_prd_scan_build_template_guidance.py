from pathlib import Path

import yaml

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _content(path: str) -> str:
    return read_template(path)


def _frontmatter(path: str) -> dict:
    parts = _content(path).split("---", 2)
    return yaml.safe_load(parts[1])


def test_prd_scan_template_defines_reconstruction_scan_contract() -> None:
    content = _content("templates/commands/prd-scan.md")
    frontmatter = _frontmatter("templates/commands/prd-scan.md")
    contract = frontmatter["workflow_contract"]
    lowered = content.lower()

    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert ".specify/prd-runs/<run-id>/prd-scan.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/artifact-contracts.json" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/reconstruction-checklist.json" in contract["primary_outputs"]
    assert "read-only reconstruction investigation" in lowered
    assert "must not write `master/master-pack.md`" in content
    assert "must not write `exports/**`" in content
    assert "capability" in lowered
    assert "artifact" in lowered
    assert "boundary" in lowered
    assert "`Evidence`" in content
    assert "`Inference`" in content
    assert "`Unknown`" in content
    assert "`critical`" in content
    assert "`high`" in content
    assert "`standard`" in content
    assert "`auxiliary`" in content
    assert "reconstruction-ready" in content
    assert "blocked-by-gap" in content
    assert "artifact-contracts.json" in content
    assert "reconstruction-checklist.json" in content
    assert "Capability Triage Gate" in content
    assert "Critical Depth Gate" in content
    assert "High Capability Gate" in content
    assert "Evidence Label Gate" in content
    assert "producer-consumer" in lowered
    assert "failure behavior" in lowered


def test_prd_scan_template_preserves_tiers_and_labeling_contract() -> None:
    content = _content("templates/commands/prd-scan.md")
    lowered = content.lower()

    assert "labeling semantics" in lowered
    assert "assign each capability a tier" in lowered
    assert "capture stronger reconstruction detail" in lowered
    assert "must have more than path-only evidence" in lowered
    assert "must be assigned `critical`, `high`, `standard`, or `auxiliary`" in content


def test_prd_scan_template_mentions_subagent_execution_markers() -> None:
    content = _content("templates/commands/prd-scan.md")

    assert "execution_model: subagent-mandatory" in content
    assert "PrdScanPacket" in content


def test_prd_scan_template_mentions_reconstruction_evidence_levels() -> None:
    content = _content("templates/commands/prd-scan.md")

    assert "L1 Exists" in content
    assert "L2 Surface" in content
    assert "L3 Behavioral" in content
    assert "L4 Reconstruction-Ready" in content


def test_prd_scan_template_mentions_reconstruction_family_labels() -> None:
    content = _content("templates/commands/prd-scan.md")

    assert "Main Capability Chains" in content
    assert "External Entrypoints and Command Surfaces" in content
    assert "State Machines and Flow Control" in content
    assert "Data and Persistence Contracts" in content
    assert "Configuration and Behavior Switches" in content
    assert "Protocol and Boundary Contracts" in content
    assert "Error Semantics and Recovery Behavior" in content
    assert "Verification and Regression Entrypoints" in content


def test_prd_scan_template_mentions_reconstruction_artifact_filenames() -> None:
    content = _content("templates/commands/prd-scan.md")

    assert "entrypoint-ledger.json" in content
    assert "config-contracts.json" in content
    assert "protocol-contracts.json" in content
    assert "state-machines.json" in content
    assert "error-semantics.json" in content
    assert "verification-surfaces.json" in content


def test_prd_build_template_refuses_incomplete_scan_packages() -> None:
    content = _content("templates/commands/prd-build.md")
    frontmatter = _frontmatter("templates/commands/prd-build.md")
    contract = frontmatter["workflow_contract"]
    lowered = content.lower()

    assert "sp-prd-build" in content
    assert "sp-prd-scan" in content
    assert ".specify/prd-runs/<run-id>/workflow-state.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/exports/prd.md" in contract["primary_outputs"]
    assert ".specify/prd-runs/<run-id>/exports/reconstruction-appendix.md" in contract["primary_outputs"]
    assert "must not become a second repository scan" in lowered
    assert "must not silently fill critical evidence gaps" in lowered
    assert "No New Facts Gate" in content
    assert "Artifact Landing Gate" in content
    assert "Field-Level Coverage Gate" in content
    assert "Inference Ceiling Gate" in content
    assert "Evidence Label Gate" in content
    assert "Classification Export Gate" in content
    assert "`Evidence`" in content
    assert "`Inference`" in content
    assert "`Unknown`" in content
    assert "`ui`" in content
    assert "`service`" in content
    assert "`mixed`" in content
    assert "reverse coverage validation" in lowered


def test_prd_build_template_preserves_label_and_classification_semantics() -> None:
    content = _content("templates/commands/prd-build.md")
    lowered = content.lower()

    assert "preserve `Evidence`, `Inference`, and `Unknown` labels" in content
    assert "project classification" in lowered
    assert "classification-aware export semantics" in lowered
    assert "preserve `Evidence`, `Inference`, and `Unknown` handling" in content
    assert "must not strip `Evidence`, `Inference`, or `Unknown` labels" in content
    assert "fixed export set" in lowered


def test_prd_build_template_mentions_reconstruction_packet_evidence_intake() -> None:
    content = _content("templates/commands/prd-build.md")

    assert "packet evidence intake" in content.lower()
    assert "mandatory subagents" in content.lower() or "execution_model: subagent-mandatory" in content


def test_prd_build_template_mentions_reconstruction_export_filenames() -> None:
    content = _content("templates/commands/prd-build.md")

    assert "exports/config-contracts.md" in content
    assert "exports/protocol-contracts.md" in content
    assert "exports/state-machines.md" in content
    assert "exports/error-semantics.md" in content
    assert "exports/verification-surface.md" in content
    assert "exports/reconstruction-risks.md" in content


def test_prd_build_template_mentions_reconstruction_readiness_gate_names() -> None:
    content = _content("templates/commands/prd-build.md")

    assert "Critical Unknown Refusal Gate" in content
    assert "Traceability Gate" in content
    assert "Reconstruction Readiness Gate" in content


def test_prd_scan_template_defines_state_dispatch_and_packet_contracts() -> None:
    content = _content("templates/commands/prd-scan.md")
    lowered = content.lower()

    assert "project map state protocol" not in lowered
    assert "prd run state protocol" in lowered
    assert 'choose_subagent_dispatch(command_name="prd-scan"' in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "`subagent-blocked`" in content or "subagent-blocked" in content
    assert "accepted_packet_results" in content
    assert "rejected_packet_results" in content
    assert "failed_readiness_checks" in content
    assert "PrdScanPacket" in content
    assert "lane_id" in content
    assert "mode: read_only" in content
    assert "required_reads" in content
    assert "excluded_paths" in content
    assert "required_questions" in content
    assert "expected_outputs" in content
    assert "contract_targets" in content
    assert "forbidden_actions" in content
    assert "result_handoff_path" in content
    assert "join_points" in content
    assert "minimum_verification" in content
    assert "blocked_conditions" in content
    assert "reported_status" in content
    assert "paths_read" in content
    assert "evidence_refs" in content
    assert "recommended_contract_updates" in content
    assert "unknowns" in content
    assert "before freezing ledgers and machine-readable contracts" in content
    assert "before declaring the package ready for `sp-prd-build`" in content
    assert "idle subagent output is not an accepted scan result" in lowered
    assert "smallest safe repair" in lowered


def test_prd_build_template_defines_bundle_only_dispatch_and_traceability_contracts() -> None:
    content = _content("templates/commands/prd-build.md")
    lowered = content.lower()

    assert 'choose_subagent_dispatch(command_name="prd-build"' in content
    assert "prd run state protocol" in lowered
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "`subagent-blocked`" in content or "subagent-blocked" in content
    assert "PrdBuildPacket" in content
    assert "lane_id" in content
    assert "mode: bundle_only" in content
    assert "packet_scope" in content
    assert "required_scan_inputs" in content
    assert "required_contract_files" in content
    assert "required_worker_results" in content
    assert "expected_exports" in content
    assert "traceability_targets" in content
    assert "forbidden_actions" in content
    assert "minimum_verification" in content
    assert "result_handoff_path" in content
    assert "reported_status" in content
    assert "bundle_inputs_read" in content
    assert "traceability_findings" in content
    assert "export_landing_findings" in content
    assert "recommended_repairs" in content
    assert "before writing `master/master-pack.md`" in content
    assert "before writing or finalizing `exports/**`" in content
    assert "before reverse coverage / traceability validation" in content
    assert "accepted_packet_results" in content
    assert "rejected_packet_results" in content
    assert "failed_readiness_checks" in content
    assert "failed_reverse_coverage_checks" in content
    assert "report completion" in lowered
    assert "must not become a second repository scan" in lowered
    assert "must not reread the repository" in lowered or "new repository facts" in lowered
    assert "smallest safe repair" in lowered
