from .template_utils import read_command_with_references, read_template


def _read(path: str) -> str:
    if path == "templates/commands/tasks.md":
        return read_command_with_references("tasks")
    return read_template(path)


def test_tasks_command_scopes_strategy_to_current_ready_batch():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "current ready batch" in lowered
    assert "feature delivery shape" in lowered
    assert "packet compilation target only the current ready batch" in lowered
    assert "delegate only isolated decomposition lanes" in lowered
    assert "bounded reads/writes, forbidden drift, authoritative refs, done condition" in lowered


def test_tasks_template_distinguishes_feature_shape_from_batch_strategy():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "feature delivery shape" in lowered
    assert "current ready batch" in lowered
    assert "execution_model: adaptive" in content
    assert "execution_mode: light | standard | heavy" in content
    assert "workflow_status: ready | blocked" in content
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface: leader-inline | native-subagents | none" in content
    assert "capability_degraded: false | true" in content
    assert "blocked_reason: required when blocked" in content
    assert "packet compilation target only the current ready batch" in lowered


def test_tasks_template_makes_parallel_tasks_jit_packet_ready_for_leaders():
    content = _read("templates/tasks-template.md")
    lowered = content.lower()

    assert "for each `[p]` task or explicit parallel batch" in lowered
    assert "objective, write set, required references, forbidden drift, validation command, and done condition" in lowered
    assert "leader can compile a bounded subagent execution packet" in lowered
    assert "## Delegated Lane Integration" in content
    assert "task-generation/lane-manifest.json" in content
    assert "task-generation/handoffs/" in content
    assert "record each accepted result's consumer once in the manifest" in lowered
    assert "do not create separate evidence-index and checkpoint logs" in lowered


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
    assert "Task Contract Mapping" in content
    assert "task-index.json" in content
    assert "DP1" in content
    assert "DP2" in content
    assert "DP3" in content


def test_tasks_command_requires_persisted_task_generation_handoffs():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "one lane manifest plus lane results" in lowered
    assert "delegated decomposition only: one lane manifest plus lane results" in lowered
    assert "consume every accepted task-generation lane result" in lowered
    assert "do not create separate evidence-index and checkpoint logs" in lowered


def test_tasks_command_requires_writable_delegated_task_generation_lanes():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "artifact-writing delegated lanes must use writable" in lowered
    assert "execution-capable native subagents" in lowered
    assert "read-only explorer, reviewer, or diagnostic lane" in lowered
    assert "one result per lane under `task-generation/handoffs/`" in lowered
    assert "must include the exact expected handoff path" in lowered
    assert "re-dispatch with a writable lane" in lowered


def test_tasks_command_consumes_upstream_planning_evidence():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "primary authority: `plan-contract.json`" in lowered
    assert "read conditional plan/spec views only through a required ref or stale condition" in lowered
    assert "do not revalidate discussion/specification gates" in lowered


def test_tasks_command_makes_packet_outputs_mode_sensitive():
    content = _read("templates/commands/tasks.md")

    assert "Light: compact `tasks.md`" in content
    assert "Standard/heavy: canonical `task-index.json` plus rendered `tasks.md`" in content
    assert "renders and validates only the current packet" in content
    assert "do not copy the schema into `tasks.md` or pre-generate all packets" in content
