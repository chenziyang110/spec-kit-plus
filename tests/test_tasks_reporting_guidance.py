from .template_utils import read_command_with_references, read_template


def _read(path: str) -> str:
    if path == "templates/commands/tasks.md":
        return read_command_with_references("tasks")
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
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "feature delivery shape" in lowered
    assert "serial phases with intra-phase parallel batches" in lowered
    assert "current ready batch" in lowered
    assert "current ready batch**, not automatically to the entire feature or task graph" in lowered
    assert "execution_model: adaptive" in content
    assert "execution_mode: light | standard | heavy" in content
    assert "workflow_status: ready | blocked" in content
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface: leader-inline | native-subagents | none" in content
    assert "capability_degraded: false | true" in content
    assert "blocked_reason: required when blocked" in content
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


def test_tasks_template_keeps_agent_roles_out_of_checklist_rows():
    content = _read("templates/tasks-template.md")
    checklist_lines = [line for line in content.splitlines() if line.startswith("- [ ] T")]

    assert checklist_lines
    assert not any("[Agent:" in line for line in checklist_lines)
    assert "## Format: `[ID] [P?] [Story?] Description`" in content
    assert "Agent roles belong in the task contract matrix and task packet JSON" in content


def test_tasks_template_includes_analyze_remediation_mapping_and_self_audit():
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "## Analyze Remediation Mapping" in content
    assert "| Finding ID | Disposition | Task/Section Evidence | Notes |" in content
    assert "resolved" in lowered
    assert "deferred" in lowered
    assert "not_applicable" in content
    assert "escalated" in lowered
    assert "## Implementation-Readiness Task Self-Audit" in content
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
    assert "mark the handoff as `integrated`, assigned to a refinement checkpoint" in lowered
    assert "recorded in `user_confirmed_deferrals` with confirmation source" in lowered
    assert "without an explicit consuming task, packet field, dependency edge, refinement checkpoint" in lowered
    assert "do not synthesize `tasks.md` from chat-only delegated lane results" in lowered


def test_tasks_command_requires_writable_delegated_task_generation_lanes():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "artifact-writing delegated lanes must use writable" in lowered
    assert "execution-capable native subagents" in lowered
    assert "read-only explorer, reviewer, or diagnostic lane" in lowered
    assert "task-generation/handoffs/<lane-id>.json" in content
    assert "must include the exact expected handoff path" in lowered
    assert "re-dispatch with a writable lane" in lowered


def test_tasks_command_consumes_upstream_planning_evidence():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "planning/evidence-index.json and accepted planning/handoffs/*.json" in content
    assert "Read `planning/evidence-index.json` and all accepted `planning/handoffs/*.json`" in content
    assert "accepted planning lane contributions as upstream planning inputs" in lowered


def test_tasks_command_makes_packet_outputs_mode_sensitive():
    content = _read("templates/commands/tasks.md")

    assert (
        "Emit `handoff-to-tasks.json`, `task-index.json`, and per-task packet JSON under "
        "`task-packets/` when standard/heavy mode uses delegated task-generation lanes or downstream "
        "delegated implementation needs packets; in light mode, emit only the minimum light-mode "
        "`tasks.md` contract unless `task-index.json` is useful."
    ) in content
    assert (
        "When delegated task-generation handoffs exist, include references in `handoff-to-tasks.json` "
        "and `task-index.json` to the accepted `task-generation/handoffs/<lane-id>.json` files"
    ) in content
    assert (
        "Emit `handoff-to-tasks.json`, `task-index.json`, and per-task packet JSON under "
        "`task-packets/` alongside `tasks.md`."
    ) not in content
