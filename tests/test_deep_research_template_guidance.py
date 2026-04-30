from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _assert_mandatory_subagent_guidance(content: str) -> None:
    lowered = content.lower()
    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in lowered
    assert "the leader orchestrates:" in lowered
    assert "before dispatch, every subagent lane needs a task contract" in lowered
    assert "structured handoff" in lowered
    assert "execution_model: subagent-mandatory" in lowered
    assert "dispatch_shape: one-subagent | parallel-subagents" in lowered
    assert "execution_surface: native-subagents" in lowered


def test_deep_research_template_requires_mandatory_subagent_guidance() -> None:
    _assert_mandatory_subagent_guidance(_read("templates/commands/deep-research.md"))


def test_deep_research_template_defines_complete_research_contract() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()

    assert "sp-deep-research" in content
    assert "FEATURE_DIR/deep-research.md" in content
    assert "FEATURE_DIR/research-spikes/" in content
    assert "workflow-state.md" in content
    assert "Workflow Phase Lock" in content
    assert "Multi-Agent Research Orchestration" in content
    assert "Traceability and Evidence Quality Contract" in content
    assert "track" in lowered
    assert "question" in lowered
    assert "finding" in lowered
    assert "confidence: high | medium | low" in lowered
    assert "planning_implications" in lowered
    assert "residual_risks" in lowered
    assert "rejected_options" in lowered
    assert "evidence quality rubric" in lowered
    assert "repo-evidence" in content
    assert "runnable-spike" in content
    assert "enough-to-plan" in content
    assert "constrained-but-plannable" in content
    assert "blocked" in content
    assert "not-viable" in content
    assert "user-decision-required" in content
    assert "Planning Handoff" in content
    assert "CAP-001" in content
    assert "TRK-001" in content
    assert "EVD-001" in content
    assert "SPK-001" in content
    assert "Planning Traceability Index" in content


def test_deep_research_template_has_readiness_refusal_rules() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()
    assert "readiness refusal" in lowered
    assert "gap report" in lowered
    assert "refuse handoff" in lowered or "handoff refused" in lowered


def test_deep_research_template_has_reverse_coverage_validation() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()
    assert "reverse coverage validation" in lowered
    assert "every cap" in lowered
    assert "every ph" in lowered


def test_deep_research_template_has_readiness_checklist() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()
    assert "Planning Handoff Readiness Checklist" in content
    assert "exit status" in lowered
    assert "Reverse Coverage Validation passed" in content or "reverse coverage" in lowered
    assert "Readiness Refusal Rules all PASS" in content or "readiness refusal" in lowered


def test_deep_research_template_has_capability_cards() -> None:
    content = _read("templates/commands/deep-research.md")
    assert "Capability Card" in content
    assert "Purpose" in content
    assert "Truth lives" in content
    assert "Entry points" in content
    assert "Key contracts" in content
    assert "Change propagation" in content


def test_deep_research_template_has_research_exclusions() -> None:
    content = _read("templates/commands/deep-research.md")
    assert "Research Exclusions" in content
    assert "Revisit Condition" in content


def test_deep_research_template_has_contradiction_resolution_log() -> None:
    content = _read("templates/commands/deep-research.md")
    assert "Contradiction Resolution Log" in content
    assert "Priority Basis" in content


def test_deep_research_template_has_evidence_packet_acceptance() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()
    assert "evidence packet acceptance" in lowered
    assert "paths_read" in lowered


def test_deep_research_template_has_preset_research_dimensions() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()
    assert "preset research dimension" in lowered or "permissions / auth boundary" in lowered


def test_deep_research_template_consumes_spec_capabilities() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()
    assert "spec.md" in lowered
    assert "capability decomposition" in lowered or "spec capability" in lowered


def test_deep_research_template_consumes_alignment_status() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()
    assert "needed before plan" in lowered
    assert "feasibility" in lowered


def test_deep_research_template_has_entry_source_distinction() -> None:
    content = _read("templates/commands/deep-research.md")
    assert "entry_source" in content
    assert "full-research" in content or "supplement-research" in content


def test_deep_research_template_has_ph_consumption_contract() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()
    assert "mandatory" in lowered
    assert "user-decision" in content


def test_deep_research_template_has_differential_evidence_analysis() -> None:
    content = _read("templates/commands/deep-research.md")
    assert "Differential Evidence Analysis" in content
    assert "OVERTURNED" in content


def test_deep_research_template_has_stale_claims_handling() -> None:
    content = _read("templates/commands/deep-research.md")
    assert "stale-needs-revalidation" in content


def test_deep_research_shell_partial_defines_guardrails() -> None:
    content = _read("templates/command-partials/deep-research/shell.md")
    lowered = content.lower()
    assert "guardrails" in lowered
    assert "Do not edit production source files" in content
    assert "Locked Decisions" in content or "locked decision" in lowered
