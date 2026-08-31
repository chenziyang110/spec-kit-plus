from pathlib import Path
import re

from .template_utils import read_skill_with_references, read_template


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_quick_checkpoint_docs_consume_stage_and_confirm_views_without_immediate_show() -> None:
    content = (
        PROJECT_ROOT / "templates" / "command-references" / "quick" / "intake-and-checkpoint.md"
    ).read_text(encoding="utf-8").lower()

    assert "stage a structured" in content or "stage the structured" in content
    assert "returned `views.decision`" in content
    assert "returned `views.delivery`" in content
    assert "quick checkpoint-show <quick-id> --view decision" not in content
    assert "quick checkpoint-show <quick-id> --view delivery" not in content


def test_spx_quick_guidance_prefers_returned_checkpoint_views_for_primary_flow() -> None:
    skill = read_skill_with_references(PROJECT_ROOT / "templates" / "advanced-skills" / "spx-quick" / "SKILL.md").lower()

    assert "returned `views.decision`" in skill
    assert "returned `views.delivery`" in skill
    assert "quick checkpoint-show <id> --view decision" not in skill
    assert "quick checkpoint-show <id> --view delivery" not in skill
    assert "quick checkpoint-show <id> --view pulse" in skill


def test_runtime_artifact_boundary_prefers_batched_reads_and_writes_with_fallbacks() -> None:
    for relative in (
        "templates/command-partials/common/runtime-artifact-boundary.md",
        "templates/advanced-skills/_shared/runtime-artifact-boundary.md",
    ):
        content = read_template(relative).lower()
        assert "artifact.show-many" in content
        assert "artifact.patch-batch" in content
        assert "older runtimes fall back" in content
        assert "single `artifact show`" in content or "single `artifact show` calls" in content
        assert "one leased `artifact patch` per target update" in content


def test_workflow_runtime_prefers_ensure_with_show_enter_fallback() -> None:
    for relative in (
        "templates/command-partials/common/agent-phase-handoff.md",
        "templates/advanced-skills/_shared/workflow-runtime.md",
    ):
        content = read_template(relative).lower()
        assert "workflow.ensure" in content
        assert "idempotent show-or-enter" in content
        assert "workflow show" in content
        assert "workflow enter --command specify" in content
        assert "older runtimes fall back" in content


def test_debug_guidance_aggregates_same_checkpoint_session_updates() -> None:
    for relative in (
        "templates/command-references/debug/reproduction-and-evidence.md",
        "templates/command-references/debug/hypothesis-and-root-cause.md",
        "templates/command-references/debug/fix-gate.md",
        "templates/command-references/debug/regression-validation-and-closeout.md",
        "templates/advanced-skills/spx-debug/references/investigation-contract.md",
    ):
        content = read_template(relative).lower()
        assert "artifact.patch-batch" in content
        assert "same-checkpoint" in content
        assert "older runtimes" in content


def test_execution_workflows_use_guarded_current_worktree_path_without_process_fallback() -> None:
    for relative in (
        "templates/commands/fast.md",
        "templates/commands/debug.md",
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/advanced-skills/spx-fast/SKILL.md",
        "templates/advanced-skills/spx-debug/SKILL.md",
        "templates/advanced-skills/spx-quick/SKILL.md",
        "templates/advanced-skills/spx-implement/SKILL.md",
        "templates/command-partials/common/execution-bootstrap.md",
        "templates/advanced-skills/_shared/execution-bootstrap.md",
    ):
        content = " ".join(read_template(relative).lower().split())
        assert "execution guard" in content, relative
        assert "execution complete" in content, relative
        assert "current worktree" in content, relative
        assert "run launch" not in content, relative
        assert "run create" not in content and "run supervise" not in content, relative


def test_large_atomic_artifact_batches_use_in_memory_utf8_stdin() -> None:
    for relative in (
        "templates/command-partials/common/runtime-artifact-boundary.md",
        "templates/advanced-skills/_shared/runtime-artifact-boundary.md",
    ):
        content = " ".join(read_template(relative).lower().split())
        for token in (
            "--input-json -",
            "stdin",
            "utf-8",
            "memory",
            "windows",
            "one prepared lease for one atomic patch-batch",
            "32 operations",
            "256 kib",
            "json_pointer",
            "do not write a temporary authoring file",
            "split only when a runtime bound",
            "fresh lease",
        ):
            assert token in content, (relative, token)
        assert "not mean argv-only" in content


def test_design_discovery_uses_stable_scopes_and_preserves_missing_design_gates() -> None:
    for relative in (
        "templates/command-partials/common/design-intelligence.md",
        "templates/advanced-skills/_shared/ui-quality-gate.md",
        "templates/command-partials/specify/shell.md",
        "templates/advanced-skills/spx-specify/references/ui-and-handoffs.md",
        "templates/command-references/quick/packetized-work.md",
        "templates/advanced-skills/spx-quick/SKILL.md",
    ):
        content = " ".join(read_template(relative).lower().split())
        assert "stable path-like" in content, relative
        assert "whole brief" in content and "--scope" in content, relative
        assert "registered metadata" in content, relative
        assert "legitimate discovery absence" in content, relative
        assert "approved design" in content and "risk note" in content, relative
        assert "approval" in content and "registration" in content, relative


def test_unchanged_learning_and_cognition_intake_is_reused_without_weakening_refresh() -> None:
    for relative in (
        "templates/command-partials/common/learning-layer.md",
        "templates/advanced-skills/_shared/project-learning.md",
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/advanced-skills/_shared/project-cognition.md",
        "templates/passive-skills/spec-kit-project-learning/SKILL.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    ):
        content = " ".join(read_template(relative).lower().split())
        assert "reuse one" in content or "reuse this learning intake" in content, relative
        assert "unchanged" in content and "intake" in content, relative
        assert "preparatory" in content, relative
        assert "refresh" in content and "scope" in content, relative
        assert "freshness/generation" in content, relative
        assert "resume/recovery" in content, relative
        assert "mutation-closeout" in content, relative


def test_project_cognition_gate_uses_bounded_capability_checks_instead_of_relisting() -> None:
    content = read_template(
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md"
    ).lower()

    assert "api ensure" in content
    assert "capability_set_sha256" in content
    assert "api pack" in content
    assert "older runtimes" in content and "api list --format json" in content
    assert "do not repeat" in content


def test_high_frequency_quick_and_accept_updates_prefer_same_checkpoint_batches() -> None:
    for relative in (
        "templates/commands/quick.md",
        "templates/command-references/quick/packetized-work.md",
        "templates/command-references/quick/workspace-state.md",
        "templates/advanced-skills/spx-quick/SKILL.md",
        "templates/command-partials/accept/shell.md",
        "templates/advanced-skills/spx-accept/SKILL.md",
        "templates/command-partials/design/shell.md",
        "templates/advanced-skills/spx-design/SKILL.md",
    ):
        content = read_template(relative).lower()
        assert "artifact patch-batch" in content, relative
        assert "same-checkpoint" in content, relative
        assert "older runtime" in content and "artifact patch" in content, relative


def test_fresh_lease_per_section_is_legacy_fallback_only() -> None:
    roots = (
        PROJECT_ROOT / "templates" / "commands",
        PROJECT_ROOT / "templates" / "command-partials",
        PROJECT_ROOT / "templates" / "command-references",
        PROJECT_ROOT / "templates" / "advanced-skills",
    )
    pattern = re.compile(r"fresh (?:leased )?(?:`artifact patch` )?lease per (?:changed )?section")

    for root in roots:
        for path in root.rglob("*.md"):
            content = path.read_text(encoding="utf-8").lower()
            for match in pattern.finditer(content):
                nearby = content[max(0, match.start() - 180) : match.end()]
                assert "older runtime" in nearby, path.relative_to(PROJECT_ROOT)
