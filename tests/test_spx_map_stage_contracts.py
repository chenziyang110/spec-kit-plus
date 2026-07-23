from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADVANCED_SKILLS = ROOT / "templates" / "advanced-skills"


def _normalized(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8").lower())


def test_shared_cognition_recovery_is_a_handoff_not_implicit_execution() -> None:
    content = _normalized(ADVANCED_SKILLS / "_shared" / "project-cognition.md")

    assert "recommend the matching maintenance skill" in content
    assert "do not invoke `$spx-map-rebuild` or `$spx-map-update`" in content
    assert "a recovery handoff is not authorization to execute another workflow" in content


def test_independent_map_stages_preserve_explicit_stop_boundaries() -> None:
    scan = _normalized(ADVANCED_SKILLS / "spx-map-scan" / "SKILL.md")
    build = _normalized(ADVANCED_SKILLS / "spx-map-build" / "SKILL.md")
    update = _normalized(ADVANCED_SKILLS / "spx-map-update" / "SKILL.md")

    for skill in (scan, build, update):
        assert "this invocation authorizes only this workflow stage" in skill

    assert "do not invoke `$spx-map-build`" in scan
    assert "do not invoke `$spx-map-scan`" in build
    assert "do not invoke `$spx-map-rebuild`" in update


def test_spx_map_scan_requires_runtime_result_skeleton_partial_acceptance_and_explicit_force_abandon() -> None:
    scan = _normalized(ADVANCED_SKILLS / "spx-map-scan" / "SKILL.md")
    gates = _normalized(
        ADVANCED_SKILLS / "spx-map-scan" / "references" / "scan-gates.md"
    )
    worker = _normalized(
        ADVANCED_SKILLS / "spx-map-scan" / "references" / "scan-worker.md"
    )

    assert "use `--force` only after explicitly abandoning the old workbench" in scan
    assert "accepted and pending results are discarded" in scan
    assert "copy the supplied json skeleton" in worker
    assert "write only the designated packet-local pending result" in worker
    assert "keep worker-authored `acceptance` at `partial`" in worker
    assert "the runtime derives `pass` only after `scan-accept` validates the full result" in worker
    assert "do not self-declare `acceptance: pass`" in worker
    assert "`scan-status status=ok` is workbench control health, not completion" in gates
    assert "`stage_state=validation_required`" in gates
    assert "`completion_allowed=false`" in gates
    assert "`completion_gate=validate_scan`" in gates
    assert "`status=ok` and `readiness=scan_ready`" in gates
    assert "evidence-integrity blockers" in gates
    assert "`bypass_allowed=false`" in gates
    assert "`error_classification=scan_evidence_integrity`" in gates
    assert "do not call them harmless format issues" in gates
    assert "`error_classification=scan_workbench_contract`" in gates
    assert "`recovery_action`, `recovery_detail`, and `recovery_argv`" in gates
    assert "back up a legacy or incompatible workbench" in gates
    assert "never hand-edit queue json or write a normalization script" in gates
    assert "`workbench/accepted-submissions/`" in gates
    assert "`workbench/acceptance-receipts/<packet-id>.json`" in gates
    assert "never hand-author, copy, normalize, or repair" in gates


def test_spx_map_build_stops_on_validate_scan_block_and_uses_runtime_only_build_chain() -> None:
    build = _normalized(ADVANCED_SKILLS / "spx-map-build" / "SKILL.md")
    gates = _normalized(
        ADVANCED_SKILLS / "spx-map-build" / "references" / "build-gates.md"
    )

    for content in (build, gates):
        assert "validate-scan" in content
        assert "build-from-scan" in content
        assert "validate-build" in content
        assert "compass" in content
        assert "mapbuildpacket" not in content
        assert (
            "do not write normalize/rebuild helper scripts" in content
            or "normalize/rebuild helper script" not in content
        )

    assert "if it is incomplete, stop" in build
    assert "if `validate-scan` returns `status=blocked`, stop" in gates
    assert "do not proceed to `build-from-scan`" in gates
    assert "do not say the format issues are harmless" in gates
    assert "`stage_state=validation_required`" in gates
    assert "`completion_gate=validate_build`" in gates
    assert "`error_classification=build_integrity`" in gates
    assert "`bypass_allowed=false`" in gates
    assert "`workbench/acceptance-receipts/<packet-id>.json`" in gates
    assert "never hand-author or normalize either receipt layer" in gates


def test_map_update_has_deterministic_validation_and_freshness_closeout() -> None:
    skill = _normalized(ADVANCED_SKILLS / "spx-map-update" / "SKILL.md")
    gates = _normalized(
        ADVANCED_SKILLS / "spx-map-update" / "references" / "update-gates.md"
    )

    for required in (
        "specify-runtime cognition validate-build --format json",
        "specify-runtime cognition complete-refresh --format json",
        "specify-runtime cognition record-refresh --reason map-update --format json",
    ):
        assert required in skill

    assert "`result_state=ready` or `result_state=no_op` requires" in gates
    assert "`status=ok` and `readiness=query_ready`" in gates
    assert "matching validation receipt" in gates
    assert "not an ordinary closeout branch" in gates
    assert "never call `complete-refresh`" in gates


def test_non_orchestrator_support_skills_stop_before_followup_workflows() -> None:
    for skill_name in (
        "spx-analyze",
        "spx-checklist",
        "spx-constitution",
        "spx-design",
        "spx-discussion",
        "spx-fast",
        "spx-prd-scan",
        "spx-quick",
        "spx-team",
    ):
        content = _normalized(ADVANCED_SKILLS / skill_name / "SKILL.md")
        assert "this invocation authorizes only this workflow stage" in content
        assert "do not invoke another workflow in this run" in content
