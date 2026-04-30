from .template_utils import read_template


def _read(path: str) -> str:
    return read_template(path)


def test_tasks_command_scopes_strategy_to_current_ready_batch():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "current ready batch" in lowered
    assert "not automatically to the entire feature or task graph" in lowered
    assert "feature delivery shape" in lowered
    assert "current ready batch" in lowered
    assert "reason code" in lowered
    assert "future or later-phase batch is parallelizable" in lowered
    assert "current ready batch" in lowered
    assert "instead of implying that the full feature has no meaningful parallelism" in lowered
    assert "if the current ready batch uses `leader-inline-fallback` but later batches are parallelizable" in lowered
    assert "maximize safe native-subagent throughput" in lowered
    assert "dispatch-ready lane packet" in lowered
    assert "required references, forbidden drift, validation command, and done condition" in lowered


def test_tasks_template_distinguishes_feature_shape_from_batch_strategy():
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "### Feature Delivery Shape" in content
    assert "serial phases with intra-phase parallel batches" in lowered
    assert "### Current Ready Batch Dispatch" in content
    assert "next executable batch only" in lowered
    assert "`execution_model: subagents-first`" in content
    assert "`dispatch_shape: one-subagent | parallel-subagents | leader-inline-fallback`" in content
    assert "`execution_surface: native-subagents | managed-team | leader-inline`" in content
    assert "`safe-one-subagent`" in content
    assert "`safe-parallel-subagents`" in content
    assert "`managed-team-supported`" in content
    assert "`no-safe-delegated-lane`" in content
    assert "`runtime-no-subagents`" in content
    assert "do not use the current batch execution strategy as a blanket label for the whole feature" in lowered


def test_tasks_template_makes_parallel_tasks_packet_ready_for_leaders():
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "for each `[p]` task or explicit parallel batch" in lowered
    assert "objective, write set, required references, forbidden drift, validation command, and done condition" in lowered
    assert "leader can compile a bounded subagent execution packet" in lowered
