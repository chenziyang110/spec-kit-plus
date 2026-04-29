from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_specify_plan_tasks_analyze_templates_reference_shared_hook_helpers() -> None:
    specify = read_template("templates/commands/specify.md")
    plan = read_template("templates/commands/plan.md")
    tasks = read_template("templates/commands/tasks.md")
    analyze = read_template("templates/commands/analyze.md")

    assert "specify hook preflight --command specify" in specify
    assert "specify hook validate-state --command specify" in specify
    assert "specify hook validate-artifacts --command specify" in specify
    assert "specify hook checkpoint --command specify" in specify

    assert "specify hook preflight --command plan" in plan
    assert "specify hook validate-state --command plan" in plan
    assert "specify hook validate-artifacts --command plan" in plan
    assert "specify hook checkpoint --command plan" in plan

    assert "specify hook preflight --command tasks" in tasks
    assert "specify hook validate-state --command tasks" in tasks
    assert "specify hook validate-artifacts --command tasks" in tasks
    assert "specify hook checkpoint --command tasks" in tasks

    assert "specify hook preflight --command analyze" in analyze
    assert "specify hook validate-state --command analyze" in analyze
    assert "specify hook validate-artifacts --command analyze" in analyze
    assert "specify hook checkpoint --command analyze" in analyze


def test_execution_templates_reference_state_checkpoint_and_delegation_hook_helpers() -> None:
    implement = read_template("templates/commands/implement.md")
    quick = read_template("templates/commands/quick.md")
    debug = read_template("templates/commands/debug.md")
    fast = read_template("templates/commands/fast.md")

    assert "specify hook preflight --command implement" in implement
    assert "specify hook validate-state --command implement" in implement
    assert "specify hook validate-session-state --command implement" in implement
    assert "specify hook validate-packet --packet-file <packet-json>" in implement
    assert "specify hook validate-result --packet-file <packet-json> --result-file <result-json>" in implement
    assert "specify hook monitor-context --command implement" in implement
    assert "specify hook checkpoint --command implement" in implement
    assert "specify hook mark-dirty --reason" in implement

    assert "specify hook preflight --command quick" in quick
    assert "specify hook validate-state --command quick" in quick
    assert "specify hook validate-session-state --command quick" in quick
    assert "specify hook monitor-context --command quick" in quick
    assert "specify hook checkpoint --command quick" in quick
    assert "specify hook render-statusline --command quick" in quick

    assert "specify hook preflight --command debug" in debug
    assert "specify hook validate-session-state --command debug" in debug
    assert "specify hook monitor-context --command debug" in debug
    assert "specify hook checkpoint --command debug" in debug
    assert "specify hook render-statusline --command debug" in debug
    assert "specify hook validate-prompt --prompt-text" in debug

    assert "specify hook validate-prompt --prompt-text" in fast
    assert "specify hook validate-read-path --target-path" in fast


def test_map_build_template_references_refresh_hook_helpers() -> None:
    content = read_template("templates/commands/map-build.md")

    assert "specify hook checkpoint --command map-build" in content
    assert "specify hook complete-refresh" in content
