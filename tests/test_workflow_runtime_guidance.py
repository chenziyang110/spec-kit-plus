from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLASSIC_STAGES = ("specify", "plan", "tasks", "implement", "accept")
ADVANCED_STAGES = ("discussion", *CLASSIC_STAGES)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_classic_stage_handoff_uses_the_deterministic_workflow_cli() -> None:
    shared = _read("templates/command-partials/common/agent-phase-handoff.md")
    compact_shared = " ".join(shared.split())

    for command in (
        "workflow show",
        "workflow enter",
        "workflow transition",
        "workflow next",
        "workflow block",
        "workflow resolve",
        "workflow closeout",
        "workflow reopen",
    ):
        assert command in shared
    assert "Do not author or advance `workflow-runtime.json` by hand" in compact_shared
    assert "`workflow-state.md` remains the rich workflow-owned evidence" in compact_shared
    assert "destination command owns the returned transition" in compact_shared
    assert ".specify/templates/workflow-blocker-template.md" in shared
    assert "Human Action Guide" in shared
    for field in (
        "exact cause",
        "attempted recovery",
        "unblock criteria",
        "exact resume",
    ):
        assert field in shared.lower()

    include = "{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}"
    for stage in CLASSIC_STAGES:
        assert include in _read(f"templates/commands/{stage}.md")


def test_advanced_required_stages_read_one_compact_workflow_runtime_reference() -> None:
    surface_map = json.loads(
        _read("templates/advanced-skills/_shared/surface-map.json")
    )
    assert "_shared/workflow-runtime.md" in surface_map["shared_references"]

    runtime = _read("templates/advanced-skills/_shared/workflow-runtime.md")
    compact_runtime = " ".join(runtime.split())
    assert "workflow transition" in runtime
    assert "validates the completed source-stage artifacts" in compact_runtime
    assert "exit `10`" in runtime

    for stage in ADVANCED_STAGES:
        content = _read(f"templates/advanced-skills/spx-{stage}/SKILL.md")
        assert "Read `references/workflow-runtime.md`" in content


def test_advanced_required_stages_do_not_ask_models_to_rebuild_runtime_state() -> None:
    forbidden = (
        "Create or resume runtime-owned `workflow-state.md`",
        "using the installed workflow-state template only when absent",
        "create or resume task-generation state",
    )
    for stage in ADVANCED_STAGES:
        content = _read(f"templates/advanced-skills/spx-{stage}/SKILL.md")
        for phrase in forbidden:
            assert phrase not in content


def test_runtime_state_is_separate_from_auxiliary_and_learning_state() -> None:
    classic = _read("templates/command-partials/common/agent-phase-handoff.md")
    advanced = _read("templates/advanced-skills/_shared/workflow-runtime.md")
    learning = _read("templates/advanced-skills/_shared/project-learning.md")

    for content in (classic, advanced):
        assert "workflow-runtime.json" in content
        assert "workflow-state.md" in content
        assert "must not overwrite" in content.lower()
    assert "## Learning Triggers" in learning
    assert "workflow-state.md" in learning


def test_auto_routes_canonical_features_from_structured_runtime_argv_first() -> None:
    classic = _read("templates/commands/auto.md")
    advanced = _read("templates/advanced-skills/spx-auto/references/routing-contract.md")

    for content in (classic, advanced):
        lowered = content.lower()
        assert "workflow show" in content
        assert "workflow next" in content
        assert "next_argv" in content
        assert "workflow-runtime.json" in content
        assert content.index("workflow show") < content.index("workflow-state.md")
        assert "active `accept`" in lowered
        assert "workflow closeout" in lowered
        assert "current accept owner" in lowered


def test_auxiliary_workflows_guard_the_runtime_without_owning_it() -> None:
    surfaces = {
        "clarify": (
            _read("templates/commands/clarify.md"),
            _read("templates/advanced-skills/spx-clarify/SKILL.md"),
            "specify",
        ),
        "deep-research": (
            _read("templates/commands/deep-research.md"),
            _read("templates/advanced-skills/spx-deep-research/SKILL.md"),
            "specify",
        ),
        "analyze": (
            _read("templates/commands/analyze.md"),
            _read("templates/advanced-skills/spx-analyze/SKILL.md"),
            "tasks or implement",
        ),
    }

    for classic, advanced, expected_owner in surfaces.values():
        for content in (classic, advanced):
            lowered = content.lower()
            assert "workflow show" in lowered
            assert "workflow-runtime.json" in lowered
            assert "must not write" in lowered
            assert expected_owner in lowered
            assert "typed owner handoff" in lowered


def test_auxiliary_spx_skills_do_not_call_rich_state_runtime_owned() -> None:
    for name in ("clarify", "deep-research", "analyze"):
        content = _read(f"templates/advanced-skills/spx-{name}/SKILL.md")
        assert "runtime-owned `workflow-state.md`" not in content


def test_auxiliary_workflows_do_not_call_rich_state_the_required_stage_authority() -> None:
    surfaces = (
        "templates/commands/clarify.md",
        "templates/commands/deep-research.md",
        "templates/advanced-skills/spx-clarify/SKILL.md",
        "templates/advanced-skills/spx-deep-research/SKILL.md",
    )
    forbidden = (
        "stage-state source of truth",
        "source of truth for phase",
        "runtime-owned `workflow-state.md`",
    )
    for relative in surfaces:
        content = _read(relative).lower()
        for phrase in forbidden:
            assert phrase.lower() not in content, relative


def test_analyze_reopens_invalidated_required_stages_through_the_runtime() -> None:
    classic = _read("templates/commands/analyze.md")
    advanced = _read("templates/advanced-skills/spx-analyze/SKILL.md")

    for content in (classic, advanced):
        lowered = content.lower()
        assert "workflow reopen" in lowered
        assert "--expected-revision" in content
        assert "--reason" in content
        assert "--evidence" in content
        assert "--invalidated-artifact" in content
        assert "clarify" in lowered and "deep-research" in lowered
        assert "reopen `specify`" in lowered
        assert "accept route-repair" in lowered
        assert "status: completed" in lowered
        assert "reopen `implement`" in lowered


def test_human_guidance_teaches_complete_then_transition_and_split_state() -> None:
    for relative in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
        "docs/quickstart.md",
    ):
        content = _read(relative)
        assert "workflow-runtime.json" in content, relative
        assert "workflow complete-stage" in content, relative
        assert "workflow transition --to <stage>" in content, relative
        assert content.index("workflow complete-stage") < content.index(
            "workflow transition --to <stage>"
        ), relative


def test_acceptance_repair_and_implement_closeout_name_the_correct_state_owner() -> None:
    accept_surfaces = (
        _read("templates/command-partials/accept/shell.md"),
        _read("templates/advanced-skills/spx-accept/references/acceptance-contract.md"),
    )
    for content in accept_surfaces:
        assert "clarify" in content.lower()
        assert "must not write" in content.lower()
        assert "workflow-runtime.json" in content
        assert "acceptance-owned" in content.lower()
        assert "rich" in content.lower()
        assert "must not write the canonical feature\n`workflow-state.md`" not in content

    main_implement = _read("templates/advanced-skills/spx-implement/SKILL.md")
    assert "`workflow-runtime.json`\nis the required phase gate" in main_implement
    assert "rich `workflow-state.md` is resume, evidence" in main_implement
    assert "`workflow-state.md` is the phase gate" not in main_implement

    implement_surfaces = (
        _read("templates/command-partials/implement/shell.md"),
        _read("templates/advanced-skills/spx-implement/references/execution-contract.md"),
    )
    for content in implement_surfaces:
        assert "complete-stage" in content
        assert "workflow-runtime.json" in content
        assert "does not update" in content.lower()
        assert "rich `workflow-state.md`" in content


def test_skills_renderer_no_longer_reintroduces_manual_specify_state_authoring() -> None:
    renderer = _read("src/specify_cli/integrations/base.py")

    assert "workflow enter --command specify" in renderer
    assert "create or resume sparse `WORKFLOW_STATE_FILE`" not in renderer


def test_plan_and_accept_resolve_then_gate_before_their_first_owned_write() -> None:
    classic_plan = _read("templates/commands/plan.md")
    advanced_plan = _read("templates/advanced-skills/spx-plan/SKILL.md")
    classic_accept = _read("templates/commands/accept.md")
    advanced_accept = _read("templates/advanced-skills/spx-accept/SKILL.md")

    for content in (classic_plan, advanced_plan):
        assert "Resolve `FEATURE_DIR` without creating `plan.md`" in content
        assert "Only after the transition succeeds" in content
        assert content.index("Resolve `FEATURE_DIR` without creating `plan.md`") < content.index(
            "Only after the transition succeeds"
        )
    for content in (classic_accept, advanced_accept):
        assert "Transition from" in content
        assert content.index("Transition from") < content.index("accept prepare")


def test_classic_required_stages_do_not_rebuild_workflow_state_by_prompt() -> None:
    content = "\n".join(
        _read(relative)
        for relative in (
            "templates/commands/plan.md",
            "templates/commands/tasks.md",
            "templates/command-partials/accept/shell.md",
        )
    )
    assert "create or resume `workflow-state.md`" not in content
    assert "create or resume `WORKFLOW_STATE_FILE`" not in content
    assert "Create or resume runtime-owned `workflow-state.md`" not in content


def test_classic_preimplementation_stages_forbid_downstream_owned_outputs() -> None:
    specify = _read("templates/commands/specify.md")
    plan = _read("templates/commands/plan.md")
    tasks = _read("templates/commands/tasks.md")

    assert "Do not create `plan-contract.json`, `plan.md`" in specify
    assert "Do not create `tasks.md` or `task-index.json`" in plan
    assert "Do not edit production source or tests" in tasks
    assert "enter or resume `specify` through the deterministic workflow runtime" in specify
    for stage, content in (("specify", specify), ("plan", plan), ("tasks", tasks)):
        assert f"hook validate-artifacts --command {stage}" in content
