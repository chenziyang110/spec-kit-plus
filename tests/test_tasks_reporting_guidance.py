from .template_utils import read_template


def _read(path: str) -> str:
    return read_template(path)


def test_tasks_command_scopes_strategy_to_current_ready_batch():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "current ready batch" in lowered
    assert "not automatically to the entire feature or task graph" in lowered
    assert "feature delivery shape" in lowered
    assert "current ready batch strategy" in lowered
    assert "reason code" in lowered
    assert "future or later-phase batch is parallelizable" in lowered
    assert "current ready batch" in lowered
    assert "instead of collapsing the entire feature into a blanket `single-lane` label" in lowered
    assert "if the current ready batch strategy is `single-lane` but later batches are parallelizable" in lowered


def test_tasks_template_distinguishes_feature_shape_from_batch_strategy():
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "### Feature Delivery Shape" in content
    assert "serial phases with intra-phase parallel batches" in lowered
    assert "### Current Ready Batch Strategy" in content
    assert "next executable batch only" in lowered
    assert "`single-lane`" in content
    assert "`native-multi-agent`" in content
    assert "`sidecar-runtime`" in content
    assert "`no-safe-batch`" in content
    assert "`native-supported`" in content
    assert "`native-missing`" in content
    assert "`fallback`" in content
    assert "do not use the current batch execution strategy as a blanket label for the whole feature" in lowered
