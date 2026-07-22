from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


def test_workflow_routing_references_cognition_gate_and_project_learning_roles() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "spec-kit-project-cognition-gate" in content
    assert "spec-kit-project-map-gate" not in content
    assert "spec-kit-project-learning" in content
    assert "sp-test-scan" not in content
    assert "sp-test-build" not in content
    assert "{{invoke:test}}" not in content
    assert "sp-auto" in content
    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "peer\n  workflow path to `sp-specify`" in content or "peer workflow path to `sp-specify`" in content
    assert "do not automatically hand off to planning" in content
    assert "default generated path is `sp-specify -> sp-plan -> sp-tasks -> sp-implement -> sp-review -> sp-accept`" in content
    assert "sp-deep-research" in content
    assert "implementation chain" in content or "implementation-chain" in content
    assert "planning handoff" in content
    assert "route into the right active `sp-*` workflow" in content
    assert "brownfield advisory navigation layer" in content
    assert "learning-start" in content
    assert "learning-capture" in content
    assert "recommended next step" in content or "continue without naming the exact workflow" in content
    assert "passing the json path or discussion slug" in content
    assert "handoff-to-specify.json" in content
    assert "exactly one unconsumed `handoff-ready` discussion" in content
    assert "before feature creation" in content


def test_workflow_routing_distinguishes_embedded_task_review_from_system_review() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    lowered = content.lower()

    assert "default generated path is `sp-specify -> sp-plan -> sp-tasks -> sp-implement -> sp-review -> sp-accept`" in lowered
    assert "event-triggered task review remains embedded" in lowered
    assert "mandatory public `sp-review`" in lowered
    assert "parallel joins" in lowered
    assert "validation failure" in lowered
    assert "review-window" in lowered
    assert "repair task-layer defects there" in lowered
    assert "{{invoke:implement}}" in content
    assert "sp-review" in content
    assert "real entrypoints" in lowered


def test_workflow_routing_distinguishes_command_route_from_product_scope() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()
    paragraphs = [" ".join(paragraph.split()) for paragraph in content.split("\n\n")]
    product_scope_terms = (
        "minimization",
        "minimize",
        "smaller",
        "mvp",
        "pilot",
        "prototype",
        "scope reduction",
        "reduce scope",
        "shrink scope",
    )

    assert any(
        ("workflow" in paragraph or "command" in paragraph)
        and any(term in paragraph for term in ("route", "routing", "recommend", "recommendation", "selection"))
        for paragraph in paragraphs
    )
    assert any(
        "product" in paragraph
        and "scope" in paragraph
        and ("workflow" in paragraph or "route" in paragraph or "command" in paragraph)
        and any(term in paragraph for term in product_scope_terms)
        for paragraph in paragraphs
    )
    assert "confirmed" in content
    assert "user" in content


def test_project_to_prd_routes_existing_project_prd_extraction() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md").lower()

    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "deprecated" in content
    assert "current-state prd suite" in content
    assert "repository evidence" in content
    assert "evidence, inference, and unknown" in content
    assert ".specify/prd-runs/<run-id>/workflow-state.md" in content
    assert "do not automatically hand off to `sp-plan`" in content


def test_project_to_prd_mentions_depth_aware_reconstruction() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md").lower()

    assert "capability triage" in content
    assert "targeted evidence harvest" in content
    assert "critical capabilities" in content
    assert "depth-aware" in content


def test_project_to_prd_mentions_heavy_reconstruction_contract() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md")
    lowered = content.lower()

    assert "heavy reconstruction" in lowered
    assert "L4 Reconstruction-Ready" in content
    assert "subagent-mandatory" in content
    assert "config-contracts.json" in content
    assert "second repository scan" in lowered
    assert "critical evidence" in lowered


def test_project_to_prd_skill_routes_to_prd_scan_then_prd_build() -> None:
    content = _read("templates/passive-skills/project-to-prd/SKILL.md")
    lowered = content.lower()

    assert "sp-prd-scan" in content
    assert "sp-prd-build" in content
    assert "deprecated" in lowered


def test_workflow_routing_uses_prd_scan_then_prd_build_as_canonical_prd_flow() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "sp-prd-scan -> sp-prd-build" in content
    assert "{{invoke:prd-scan}} -> {{invoke:prd-build}}" in content
    assert "deprecated compatibility alias" in content


def test_ui_design_passive_skill_requires_design_md_before_ui_work() -> None:
    content = _read("templates/passive-skills/spec-kit-ui-design/SKILL.md")
    lowered = content.lower()

    assert "DESIGN.md" in content
    assert "design.md" in lowered
    assert "sp-design" in content
    assert "web" in lowered
    assert "mobile" in lowered
    assert "desktop" in lowered
    assert "tui" in lowered
    assert "cli" in lowered
    assert "platform-appropriate evidence" in lowered
    assert "generic one-off styling" in lowered


def test_ui_design_passive_skill_requires_subagent_for_ui_reference_input() -> None:
    content = _read("templates/passive-skills/spec-kit-ui-design/SKILL.md")
    lowered = content.lower()

    assert "ui reference input" in lowered
    assert "ui-reference-artifact" in content
    assert "choose_ui_reference_lane_dispatch" in content
    assert "ui-reference-notes.md" in content
    assert "ui-brief.md" in content
    assert "ui-target.html" in content
    assert "pending-human-review" in content
    assert "must not claim" in lowered


def test_workflow_routing_recommends_design_for_high_risk_ui() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    lowered = content.lower()

    assert "sp-design" in content
    assert "{{invoke:design}}" in content
    assert "high-risk ui" in lowered
    assert "new product ui" in lowered
    assert "redesign or rebrand" in lowered
    assert "small ui work" in lowered
    assert "soft risk" in lowered


def test_frontend_design_is_subordinate_to_design_md() -> None:
    content = _read("templates/passive-skills/frontend-design/SKILL.md")
    lowered = content.lower()

    assert "design.md" in lowered
    assert "subordinate" in lowered
    assert "sp-design" in content
    assert "do not invent unrelated bold aesthetics" in lowered


def test_webapp_testing_requires_visual_evidence() -> None:
    content = _read("templates/passive-skills/webapp-testing/SKILL.md")
    lowered = content.lower()

    assert "viewport screenshot" in lowered
    assert "layout overflow" in lowered
    assert "visual regression-friendly" in lowered
    assert "sp-implement" in content


def test_workflow_routing_mentions_heavy_prd_reconstruction_contract() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    lowered = content.lower()

    assert "heavy reconstruction" in lowered
    assert "L4 Reconstruction-Ready" in content
    assert "subagent-mandatory" in content
    assert "config-contracts.json" in content
    assert "must not reread the repository" in lowered
    assert "critical evidence gaps" in lowered


def test_workflow_routing_forces_route_selection_before_any_action() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "1% chance" in content
    assert "before any response or action" in content
    assert "clarifying question" in content
    assert "file read" in content
    assert "shell command" in content
    assert "red flags" in content


def test_subagent_driven_development_prefers_native_dispatch_contract() -> None:
    content = _read("templates/passive-skills/subagent-driven-development/SKILL.md").lower()

    assert "native subagents" in content
    assert "validated `workertaskpacket`" in content
    assert "must not dispatch from raw task text" in content
    assert "structured handoff" in content
    assert "single task reviewer" in content
    assert "event-triggered review" in content
    assert "task lifecycle record" in content
    assert "`sp-teams` only" in content
    assert "we do not manually dispatch ad-hoc subagents" not in content


def test_dispatching_parallel_agents_uses_current_runtime_before_external_sessions() -> None:
    content = _read("templates/passive-skills/dispatching-parallel-agents/SKILL.md").lower()

    assert "2+ independent lanes" in content
    assert "current runtime" in content
    assert "native subagents" in content
    assert "write-set" in content
    assert "structured handoff" in content
    assert "separate terminal" in content
    assert "advise the user to run multiple parallel instances" not in content


def test_generated_passive_skill_files_do_not_reference_uninstalled_superpowers_names() -> None:
    offenders = []
    passive_root = PROJECT_ROOT / "templates" / "passive-skills"

    for path in sorted(passive_root.rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        if "superpowers:" in content:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_project_cognition_gate_references_routing_and_learning_roles() -> None:
    content = _read("templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md").lower()

    assert "spec-kit-workflow-routing" in content
    assert "spec-kit-project-learning" in content
    assert "spec-kit-project-map-gate" not in content
    assert "route selection" in content
    assert "shared memory capture layer" in content
    assert "launcher-backed project cognition query planning flow" in content
    assert "specify-runtime cognition lexicon" in content
    assert "alias catalog" in content
    assert "semantic_intake" in content
    assert "facet coverage" in content
    assert "query_plan" in content
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "task-local project" in content
    assert "raw graph json artifacts as obsolete runtime surfaces" in content
    assert "returned map terms" not in content
    assert "advisory navigation surface" in content
    assert "legacy project-map exports are not evidence for current project behavior" in content
    assert "read `debug-handbook.md`" not in content
    assert "read `build-handbook.md`" not in content
    assert "advisory navigation" in content
    assert "sp-map-update" in content
    assert "sp-map-scan" in content
    assert "sp-map-build" in content


def test_project_learning_focuses_on_memory_triggers_storage_and_promotion() -> None:
    content = _read("templates/passive-skills/spec-kit-project-learning/SKILL.md").lower()

    assert "only agent-facing read surface" in content
    assert "do not parse" in content
    assert "learning start --command <classic-command-name> --format json" in content
    assert "learning list" in content
    assert "learning show" in content
    assert "show_argv" in content
    assert "user corrects" in content
    assert "workflow state failed to preserve information" in content
    assert "cognition coverage" in content
    assert "consume-only" in content
    assert "consume-capture" in content
    assert "reading never changes lifecycle state" in content
    assert "problem, action, avoid, success criteria, exceptions" in content
    assert "hook review-learning --command <command-name>" not in content
    assert "{{specify-subcmd:hook capture-learning" not in content
    assert "testing-state.md" not in content
    assert "durable workflow state" in content


def test_subagent_implementer_prompt_defers_heavy_tdd_to_feature_epoch() -> None:
    content = _read("templates/passive-skills/subagent-driven-development/implementer-prompt.md").lower()

    assert "workflow-owned validation" in content
    assert "accepted change-set" in content and "baseline epoch ref" in content
    assert "cheap task checks" in content and "test impact" in content
    assert "do not run a test suite" in content
    assert "per txx" in content
