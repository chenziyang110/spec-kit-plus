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
    assert "if later batches are parallelizable but the current batch is not" in lowered
    assert "current ready batch" in lowered
    assert "if later batches are parallelizable but the current batch is not, state that explicitly" in lowered
    assert "if later batches are parallelizable but the current batch is not" in lowered
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
    assert "`execution_model: subagent-mandatory`" in content
    assert "`dispatch_shape: one-subagent | parallel-subagents | subagent-blocked`" in content
    assert "`execution_surface: native-subagents`" in content
    assert "`safe-one-subagent`" in content
    assert "`safe-parallel-subagents`" in content
    assert "`no-safe-delegated-lane`" in content
    assert "`runtime-no-subagents`" in content
    assert "do not use the current batch execution strategy as a blanket label for the whole feature" in lowered


def test_tasks_template_makes_parallel_tasks_packet_ready_for_leaders():
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "for each `[p]` task or explicit parallel batch" in lowered
    assert "objective, write set, required references, forbidden drift, validation command, and done condition" in lowered
    assert "leader can compile a bounded subagent execution packet" in lowered
    assert "## Task-Generation Evidence Index" in content
    assert "task-generation/evidence-index.json" in content
    assert "task-generation/checkpoints.ndjson" in content
    assert "task-generation/handoffs/" in content
    assert "Every accepted task-generation handoff must have a consumer recorded" in content
    assert "task ID, packet field, dependency edge, write-set decision" in content


def test_tasks_template_includes_analyze_remediation_mapping_and_self_audit():
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "## Analyze Remediation Mapping" in content
    assert "| Finding ID | Disposition | Task/Section Evidence | Notes |" in content
    assert "resolved" in lowered
    assert "deferred" in lowered
    assert "not_applicable" in content
    assert "escalated" in lowered
    assert "## Analyze-Compatible Task Self-Audit" in content
    assert "buildable `FR-*`" in content
    assert "Task Guardrail Index" in content
    assert "DP1" in content
    assert "DP2" in content
    assert "DP3" in content


def test_tasks_command_requires_persisted_task_generation_handoffs():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "task-generation/handoffs/<lane-id>.json" in content
    assert "task-generation/evidence-index.json" in content
    assert "task-generation/checkpoints.ndjson" in content
    assert "persist a `task_generation_checkpoint` record" in lowered
    assert "persist the lane's structured handoff" in lowered
    assert "consume `task-generation/evidence-index.json` before final task synthesis" in lowered
    assert "mark the handoff as `integrated`, `deferred`, or `blocked`" in lowered
    assert "without an explicit consuming task, packet field, dependency edge, deferral, escalation, or blocker reason" in lowered
    assert "do not synthesize `tasks.md` from chat-only lane results" in lowered


def test_tasks_command_consumes_upstream_planning_evidence():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "planning/evidence-index.json and accepted planning/handoffs/*.json" in content
    assert "Read `planning/evidence-index.json` and all accepted `planning/handoffs/*.json`" in content
    assert "accepted planning lane contributions as upstream planning inputs" in lowered
