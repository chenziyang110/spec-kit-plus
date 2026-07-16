from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADVANCED = ROOT / "templates" / "advanced-skills"
CLASSIC_COMMANDS = ROOT / "templates" / "commands"


def _skill(name: str) -> str:
    content = (ADVANCED / name / "SKILL.md").read_text(encoding="utf-8")
    return " ".join(content.split())


def test_spx_deep_research_preserves_durable_stage_and_refusal_gates() -> None:
    content = _skill("spx-deep-research")
    classic = (CLASSIC_COMMANDS / "deep-research.md").read_text(encoding="utf-8")

    for required in (
        "workflow-state.md",
        "active_command: sp-deep-research",
        "phase_mode: research-only",
        "allowed_artifact_writes",
        "Not needed",
        "reverse coverage",
        "before_deep_research",
        "after_deep_research",
    ):
        assert required in content
    assert "tests, migrations, production configuration, or build tooling" in content
    assert "refuse the handoff" in content
    assert "**Status**: Not needed" in classic
    assert "**Status**: Not needed" in content
    assert "hook validate-artifacts --command deep-research" in content


def test_spx_research_keeps_generic_web_research_out_of_feature_artifacts() -> None:
    content = _skill("spx-research").lower()

    assert "generic web research" in content
    assert "external/web research skill" in content
    assert "do not create feature artifacts" in content


def test_spx_design_preserves_design_state_support_artifacts_and_final_review() -> None:
    content = _skill("spx-design")

    for required in (
        ".specify/design/design-state.md",
        ".specify/design/references.md",
        ".specify/design/options.md",
        ".specify/design/review.md",
        "active_command: sp-design",
        "phase_mode: design-only",
        "allowed_writes",
    ):
        assert required in content
    assert "Ask the user to review the written `DESIGN.md`" in content


def test_spx_map_scan_persists_unavailable_worker_recovery() -> None:
    content = _skill("spx-map-scan")

    for required in (
        "subagent_blocked",
        "recovery_condition",
        "prepared queue",
        "canonical workbench",
        "Do not replace the missing worker with leader bulk reads",
    ):
        assert required in content


def test_spx_prd_scan_preserves_resume_freshness_and_classification_state() -> None:
    content = _skill("spx-prd-scan")

    for required in (
        "active_command: sp-prd-scan",
        "scan_status",
        "accepted_packet_results",
        "rejected_packet_results",
        "failed_readiness_checks",
        "fresh",
        "targeted-stale",
        "full-stale",
        "ui | service | mixed",
    ):
        assert required in content


def test_spx_prd_build_consumes_semantic_status_and_preserves_build_state() -> None:
    content = _skill("spx-prd-build")

    for required in (
        "status: ready | blocked",
        "readiness: ready-to-build | complete | blocked",
        "active_command: sp-prd-build",
        "build_status",
        "failed_reverse_coverage_checks",
        "ui | service | mixed",
        "classification-aware",
    ):
        assert required in content


def test_spx_prd_compatibility_route_propagates_child_blockers() -> None:
    content = _skill("spx-prd")

    assert "If scan blocks, stop" in content
    assert "If build blocks, stop" in content
    assert "never report the compatibility route complete" in content
