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
        "workflow closeout",
    ):
        assert command in shared
    assert "Do not author or advance `workflow-state.md` by hand" in compact_shared
    assert "destination command owns the transition" in compact_shared
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
