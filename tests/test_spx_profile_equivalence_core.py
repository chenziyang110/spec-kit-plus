from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADVANCED = ROOT / "templates" / "advanced-skills"
CLASSIC_COMMANDS = ROOT / "templates" / "commands"


def _text(skill: str, *references: str) -> str:
    paths = [ADVANCED / skill / "SKILL.md"]
    paths.extend(ADVANCED / skill / "references" / name for name in references)
    return re.sub(
        r"\s+",
        " ",
        "\n".join(path.read_text(encoding="utf-8") for path in paths).lower(),
    )


def test_spx_auto_preserves_authoritative_resume_routing() -> None:
    content = _text("spx-auto", "routing-contract.md")

    assert "`feature_dir/workflow.json` is the primary required-stage phase lock" in content
    assert "specify-runtime workflow show" in content
    assert "specify-runtime workflow next" in content
    assert "structured `next_argv`" in content
    assert "`workflow-state.md` remains rich workflow-owned" in content
    assert "reconcile" in content
    assert "exactly one unique safe candidate" in content
    assert "`uncertain`" in content and "stop" in content
    assert "upstream gate" in content and "implementation" in content
    assert "auto_default_recommendation" in content
    assert "scope reduction" in content and "destructive" in content


def test_spx_accept_preserves_classic_human_acceptance_boundary() -> None:
    spx = _text("spx-accept", "acceptance-contract.md")
    classic = (CLASSIC_COMMANDS / "accept.md").read_text(encoding="utf-8").lower()

    for content in (spx, classic):
        assert "human-acceptance.json" in content
        assert "implementation-summary.md" in content
        assert "no useful" in content or "no prior context" in content
        assert "one" in content and "step" in content
        assert "do not edit" in content or "must not edit" in content
        assert "human" in content and "pass" in content
        assert "implement" in content
        assert "review" in content
        assert "unknown mechanism" in content
        assert "diagnostic packet" in content
        assert "debug" not in content

    assert "technical completion is not human product acceptance" in _text(
        "spx-implement"
    )


def test_spx_optional_feature_stages_separate_runtime_and_rich_resume_state() -> None:
    expected = {
        "spx-clarify": ("clarify", "planning-only"),
        "spx-analyze": ("analyze", "analysis-only"),
    }

    for skill, (command, phase) in expected.items():
        content = _text(skill)
        assert "`feature_dir/workflow.json` is cli-owned" in content, skill
        assert "must not write it" in content, skill
        assert "specify-runtime workflow show" in content, skill
        assert "typed owner handoff" in content, skill
        assert "rich workflow-owned `workflow-state.md`" in content, skill
        assert f"`phase_mode: {phase}`" in content, skill
        assert "source revision" in content, skill
        assert "target boundary" in content, skill
        assert "blocker" in content and "next route" in content, skill
        assert (
            f"hook validate-state --command {command} --feature-dir <feature-dir> "
            "--autofix --format json"
        ) in content, skill


def test_spx_discussion_preserves_truth_consequence_and_ui_handoff_inputs() -> None:
    content = _text("spx-discussion", "discussion-contract.md")

    assert "discussion write-handoff <slug> --input <draft-json-path> --json" in content
    assert "discussion validate-handoff <slug> --json" in content
    assert "references/consequence-gate.md" in content
    assert "truth pass" in content
    assert "target_project_root" in content
    assert "verified_project_facts" in content
    assert "consequence obligations" in content
    assert "original ui reference" in content
    assert "deferred ui" in content


def test_spx_specify_fails_closed_on_handoff_and_artifact_validation() -> None:
    content = _text("spx-specify", "discussion-handoff.md")

    assert "discussion validate-handoff <slug> --json" in content
    assert "status: handoff-ready" in content
    assert "planning_gate_status: ready" in content
    assert "quality_gate.status: user_confirmed" in content
    assert "quality_gate.confirmed_digest" in content
    assert "review_digest" in content
    assert "zero hard unknowns" in content
    assert "zero open conflicts" in content
    assert "target project root" in content
    assert (
        "hook validate-artifacts --command specify --feature-dir <feature-dir> "
        "--format json"
    ) in content
    assert "fail closed" in content


def test_spx_plan_requires_ready_input_and_conditional_design_outputs() -> None:
    content = _text("spx-plan", "planning-contract.md")
    classic = (CLASSIC_COMMANDS / "plan.md").read_text(encoding="utf-8").lower()

    assert "require `spec-contract.json`" in content
    assert "status: planning-ready" in content
    assert "ready transition" in content
    assert "zero hard unknowns" in content
    assert "zero open conflicts" in content
    for artifact in ("`research.md`", "`data-model.md`", "`contracts/`", "`quickstart.md`"):
        assert artifact in content
    assert "update-agent-context" in content
    assert (
        "hook validate-artifacts --command plan --feature-dir <feature-dir> "
        "--format json"
    ) in content
    assert "deep-research `ph-###` traceability" in classic
    assert "deep-research.md" in content
    assert "deep research traceability matrix" in content
    for column in (
        "plan decision",
        "handoff id",
        "evidence / spike id",
        "evidence quality",
        "plan action",
    ):
        assert column in content


def test_spx_clarify_preserves_classic_evidence_surfaces_and_runtime_gate() -> None:
    content = _text("spx-clarify", "clarification-contract.md")
    classic = (CLASSIC_COMMANDS / "clarify.md").read_text(encoding="utf-8").lower()

    for artifact in (
        "alignment.md",
        "context.md",
        "references.md",
        "clarification/handoffs/",
        "clarification/evidence-index.json",
        "clarification/checkpoints.ndjson",
    ):
        assert artifact in classic
        assert artifact in content
    assert (
        "hook validate-artifacts --command clarify --feature-dir <feature-dir> "
        "--format json"
    ) in content


def test_spx_tasks_preserves_execution_and_recovery_contracts() -> None:
    content = _text("spx-tasks", "task-graph-contract.md")

    assert "check-prerequisites.sh --json" in content
    assert "keep implementation blocked" in content
    assert "ready transition to `sp-tasks`" in content
    assert "locked target boundary" in content
    assert "zero unresolved planning blockers" in content
    for field in (
        "required refs",
        "forbidden drift",
        "packet mode",
        "stop/reopen",
        "failure recovery",
    ):
        assert field in content
    for join_field in ("validation target", "command or concrete check", "pass condition"):
        assert join_field in content
    assert (
        "hook validate-artifacts --command tasks --feature-dir <feature-dir> "
        "--format json"
    ) in content


def test_spx_analyze_preserves_constitution_and_durable_gate_ledger() -> None:
    content = _text("spx-analyze", "analysis-gate.md")

    assert ".specify/memory/constitution.md" in content
    assert "highest local authority" in content
    for field in (
        "gate_status: cleared | blocked",
        "gate_cycle",
        "highest_invalid_stage",
        "blocker_bundle",
        "finding attribution",
        "next route",
    ):
        assert field in content
    assert "complete blocker bundle" in content


def test_spx_checklist_preserves_append_only_identity_and_traceability() -> None:
    content = _text("spx-checklist", "checklist-contract.md")

    assert "append-only" in content
    assert "never delete, replace, or renumber" in content
    assert "next unused `chk###`" in content
    assert "deduplicate" in content
    assert "traceability" in content
    assert "requirement or gap" in content
