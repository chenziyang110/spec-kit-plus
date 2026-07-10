import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _read_tree(relative_dir: str) -> str:
    root = PROJECT_ROOT / relative_dir
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.md"))
    )


def test_common_phase_transition_is_compact_agent_only_json() -> None:
    schema = json.loads(
        _read("templates/agent-phase-transition-schema.json")
    )
    template = json.loads(
        _read("templates/agent-phase-transition-template.json")
    )

    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "version",
        "status",
        "source_ref",
        "semantic_delta",
        "required_refs",
        "blockers",
        "next_action",
    ]
    assert set(template) == set(schema["required"]) | {"recovery"}
    assert template["semantic_delta"] == []
    assert template["required_refs"] == []
    assert template["blockers"] == []
    assert "summary" not in template
    assert "reviewer_guide" not in template


def test_discussion_handoff_is_json_only_agent_contract() -> None:
    command = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    combined = f"{command}\n{shell}".lower()

    assert "agent-only" in combined
    assert "handoff-to-specify.json" in combined
    assert "handoff-to-specify.md" not in combined
    assert "markdown/json" not in combined
    assert "human-readable rendering" not in combined


def test_specify_compiles_confirmed_discussion_contract_by_semantic_delta() -> None:
    command = _read("templates/commands/specify.md")
    shell = _read("templates/command-partials/specify/shell.md")
    combined = f"{command}\n{shell}".lower()

    assert "compile mode" in combined
    assert "semantic_delta" in combined
    assert "spec-contract.json" in combined
    assert "do not repeat user review" in combined
    assert "source_handoff_md" not in combined
    assert "markdown/json pair" not in combined


def test_plan_consumes_spec_contract_and_generates_only_triggered_artifacts() -> None:
    command = _read("templates/commands/plan.md")
    shell = _read("templates/command-partials/plan/shell.md")
    detail = _read("templates/command-references/plan/data-model-contracts-and-quickstart.md")
    combined = f"{command}\n{shell}\n{detail}".lower()

    assert "spec-contract.json" in combined
    assert "context capsule" in combined
    assert "semantic_delta" in combined
    assert "research.md" in combined and "conditional" in combined
    assert "quickstart.md" in combined and "conditional" in combined
    assert "research.md (required)" not in combined
    assert "quickstart.md (required)" not in combined


def test_tasks_use_one_cognition_intake_and_compile_worker_packets_just_in_time() -> None:
    command = _read("templates/commands/tasks.md")
    shell = _read("templates/command-partials/tasks/shell.md")
    references = _read_tree("templates/command-references/tasks")
    combined = f"{command}\n{shell}\n{references}".lower()

    assert combined.count("project-cognition compass --intent plan") == 1
    assert "task-index.json as the canonical task graph" in combined
    assert "just in time" in combined
    assert "do not pre-generate a full worker packet for every task" in combined
    assert "leader-direct" in combined
    assert "delegated" in combined


def test_implement_reviews_on_drift_events_and_uses_one_task_lifecycle_record() -> None:
    command = _read("templates/commands/implement.md")
    shell = _read("templates/command-partials/implement/shell.md")
    review = _read("templates/command-references/implement/join-point-review.md")
    combined = f"{command}\n{shell}\n{review}".lower()

    assert "event-triggered" in combined
    assert "task lifecycle record" in combined
    assert "task-briefs/" not in review
    assert "review-packages/" not in review
    assert "ledger.json" not in review
    assert "after every phase, parallel batch, pipeline stage" not in review
    assert "validation failure" in combined
    assert "write-scope drift" in combined


def test_stage_contract_templates_reference_shared_policy_instead_of_copying_it() -> None:
    plan_contract = json.loads(_read("templates/plan-contract-template.json"))
    task_index = json.loads(_read("templates/task-index-template.json"))
    task_packet = json.loads(_read("templates/task-packet-template.json"))
    implementation_state = json.loads(
        _read("templates/implement-execution-state-template.json")
    )

    assert "complete_first_scope_preservation" in plan_contract
    for payload in (task_index, task_packet, implementation_state):
        assert "complete_first_scope_preservation" not in payload
        assert payload["policy_refs"] == ["plan-contract.json#/complete_first_scope_preservation"]


def test_agent_only_transition_assets_are_packaged() -> None:
    pyproject = _read("pyproject.toml")

    assert '"templates/agent-phase-transition-schema.json"' in pyproject
    assert '"templates/agent-phase-transition-template.json"' in pyproject
    assert '"templates/spec-contract-template.json"' in pyproject

