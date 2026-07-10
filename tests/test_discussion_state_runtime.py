import importlib.util
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / "scripts" / "shared" / "discussion-state.py"


@pytest.fixture()
def runtime():
    assert RUNTIME_PATH.is_file(), "shared discussion runtime is required"
    spec = importlib.util.spec_from_file_location("discussion_state_runtime_for_tests", RUNTIME_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _setup_project(tmp_path: Path) -> Path:
    (tmp_path / ".specify").mkdir()
    return tmp_path


def _write_confirmed_handoff(runtime, project: Path, slug: str) -> tuple[Path, Path, str]:
    workspace = project / ".specify" / "discussions" / slug
    markdown_path = workspace / "handoff-to-specify.md"
    json_path = workspace / "handoff-to-specify.json"
    source_markdown = f".specify/discussions/{slug}/handoff-to-specify.md"
    source_json = f".specify/discussions/{slug}/handoff-to-specify.json"
    payload = {
        "version": 3,
        "handoff_kind": "discussion_requirement_contract",
        "status": "draft",
        "entry_source": "sp-discussion",
        "discussion_slug": slug,
        "source_handoff": source_markdown,
        "source_handoff_json": source_json,
        "handoff_goal": "Make discussion state deterministic and agent-efficient.",
        "agent_requirement_contract": {
            "target_need": "A compact and reliable discussion workflow.",
            "constraints": ["Human replies remain human-centered."],
            "success_criteria": ["Invalid handoffs cannot become ready."],
            "design_direction": ["Typed backstage with a natural frontstage."],
            "optimal_solution_approach": ["Use a shared runtime and schema-driven handoff."],
            "scope": {"in": ["discussion workflow"], "out": ["implementation planning"], "deferred": []},
        },
        "consumer_eligibility": {
            "sp-specify": {"status": "ready", "reason": "Requirement contract is complete."},
            "sp-quick": {"status": "blocked", "reason": "Specification is required first."},
        },
        "recommended_consumer": "sp-specify",
        "context_boundary": {
            "status": "locked",
            "current_project_root": str(project.resolve()),
            "current_project_roles": [
                {
                    "role": "implementation_target",
                    "scope": "spec-kit-plus",
                    "evidence_source": "live repository",
                    "notes": "Active repository is the target.",
                }
            ],
            "target_project_root": str(project.resolve()),
            "target_project_roles": [
                {
                    "role": "implementation_target",
                    "scope": "spec-kit-plus",
                    "evidence_source": "live repository",
                    "notes": "Same as current project.",
                }
            ],
            "reference_projects": [],
            "external_systems": [],
            "path_status": "target-read-confirmed",
            "boundary_confidence": "high",
        },
        "implementation_target": {
            "actual_project": "spec-kit-plus",
            "target_root": str(project.resolve()),
            "target_paths": ["templates/commands/discussion.md"],
            "required_target_paths_to_verify": [],
        },
        "source_evidence": [
            {
                "source_type": "live_code_evidence",
                "evidence_status": "proven",
                "source": "templates/commands/discussion.md",
                "claim": "sp-discussion is a generated workflow contract.",
            }
        ],
        "blocking_unknowns": [],
        "soft_unknowns": [],
        "downstream_instructions": {
            "settled_decisions": ["Separate human frontstage from agent backstage."],
            "preserved_assumptions": [],
            "conflicts_requiring_return": [],
            "capability_map": [],
            "dependencies": [],
            "planning_constraints": ["Do not expose state machinery to humans."],
            "deferred_scope": [],
            "reopen_conditions": [],
        },
        "quality_gate": {
            "status": "user_confirmed",
            "self_reviewed_at": "2026-07-10T00:00:00Z",
            "user_review_required": True,
            "user_confirmed_at": "2026-07-10T00:01:00Z",
            "confirmed_digest": None,
            "blocked_reasons": [],
        },
        "discussion_decision_digest": {
            "locked_direction": ["Layered agent-native architecture."],
            "rejected_alternatives": ["Prompt-only enforcement."],
            "accepted_tradeoffs": ["A small shared runtime is justified."],
            "experience_commitments": ["Replies are written for humans."],
            "review_criteria_carried_forward": ["Human and agent surfaces stay separate."],
            "must_not_dilute": ["Critical gates are deterministic."],
        },
        "must_preserve": [
            {
                "id": "MP-001",
                "type": "decision",
                "claim": "Human replies remain human-centered.",
                "source": "user confirmation",
                "downstream_requirement": "Keep machine state backstage.",
                "blocking_level": "hard",
                "owner": "sp-specify",
                "latest_resolve_phase": "specify",
                "status": "confirmed",
            }
        ],
        "conflicts": [],
        "coverage_status": "complete",
        "planning_gate_status": "ready",
        "hard_unknown_count": 0,
        "open_conflict_count": 0,
        "review_digest": None,
    }
    review_digest = runtime.compute_review_digest(payload)
    payload["review_digest"] = review_digest
    payload["quality_gate"]["confirmed_digest"] = review_digest
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(
        "\n".join(
            [
                "# Discussion Handoff",
                "",
                f"- discussion_slug: {slug}",
                f"- review_digest: {review_digest}",
                "- handoff_goal: Make discussion state deterministic and agent-efficient.",
                "",
                "## Handoff Reviewer Guide",
                "",
                "Approve only when the goal, boundary, and Must-Preserve items are correct.",
                "",
                "## Must-Preserve Ledger",
                "",
                "- MP-001: Human replies remain human-centered.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return markdown_path, json_path, review_digest


def test_initialize_discussion_creates_minimal_typed_state(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)

    payload = runtime.initialize_discussion(project, "Agent Friendly Discussion", "Agent-friendly discussion")

    workspace = Path(payload["workspace_path"])
    state = json.loads((workspace / "discussion-state.json").read_text(encoding="utf-8"))
    markdown = (workspace / "discussion-state.md").read_text(encoding="utf-8")
    assert payload["slug"] == "agent-friendly-discussion"
    assert state["version"] == 2
    assert state["status_family"] == "discussion"
    assert state["status"] == "active"
    assert state["lifecycle_phase"] == "explore"
    assert state["turn_packet"]["persistence_mode"] == "frontstage-only"
    assert (workspace / "discussion-log.jsonl").is_file()
    assert not (workspace / "requirements.md").exists()
    assert "## Forbidden Actions" not in markdown
    assert len(markdown.splitlines()) < 70


def test_initialize_discussion_uses_collision_safe_slug(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)

    first = runtime.initialize_discussion(project, "Agent Workflow", "Agent workflow")
    second = runtime.initialize_discussion(project, "Agent Workflow", "Agent workflow follow-up")

    assert first["slug"] == "agent-workflow"
    assert second["slug"] == "agent-workflow-2"


def test_read_only_list_status_and_resume_do_not_rewrite_index_or_state(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Recovery", "Recovery behavior")
    workspace = Path(initialized["workspace_path"])
    index_path = project / ".specify" / "discussions" / "index.json"
    state_path = workspace / "discussion-state.json"
    index_before = index_path.read_bytes()
    state_before = state_path.read_bytes()

    listed = runtime.list_discussions(project, include_all=False)
    status = runtime.discussion_status(project, initialized["slug"])
    resume = runtime.resume_context(project, initialized["slug"])

    assert listed["discussions"][0]["slug"] == initialized["slug"]
    assert status["discussion"]["lifecycle_phase"] == "explore"
    assert resume["turn_packet"]["discussion_slug"] == initialized["slug"]
    assert index_path.read_bytes() == index_before
    assert state_path.read_bytes() == state_before


def test_checkpoint_updates_typed_state_and_compact_event_log(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Checkpoint", "Checkpoint behavior")

    payload = runtime.checkpoint_discussion(
        project,
        initialized["slug"],
        {
            "summary": "Human frontstage and agent backstage are separated.",
            "lifecycle_phase": "decide",
            "confirmed_decisions": ["Keep machine state backstage."],
            "current_recommendation": "Use typed state.",
        },
    )

    workspace = Path(initialized["workspace_path"])
    state = json.loads((workspace / "discussion-state.json").read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in (workspace / "discussion-log.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert payload["discussion"]["lifecycle_phase"] == "decide"
    assert state["turn_packet"]["confirmed_decisions"] == ["Keep machine state backstage."]
    assert events[-1]["kind"] == "durable-checkpoint"
    assert "Human frontstage" in events[-1]["summary"]


def test_validate_and_mark_ready_require_exact_confirmed_digest(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Handoff", "Handoff integrity")
    _markdown, json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])

    validation = runtime.validate_handoff(project, initialized["slug"])
    ready = runtime.mark_ready(project, initialized["slug"])

    assert validation["valid"] is True
    assert validation["review_digest"] == review_digest
    assert ready["discussion"]["status"] == "handoff-ready"
    assert ready["discussion"]["lifecycle_phase"] == "ready"
    handoff = json.loads(json_path.read_text(encoding="utf-8"))
    assert handoff["status"] == "handoff-ready"


def test_validate_handoff_rejects_missing_markdown_and_stale_confirmation(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Invalid Handoff", "Invalid handoff")
    markdown_path, json_path, _digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    markdown_path.unlink()

    missing = runtime.validate_handoff(project, initialized["slug"])

    assert missing["valid"] is False
    assert "missing_handoff_markdown" in missing["error_codes"]

    markdown_path.write_text("# Restored\n", encoding="utf-8")
    handoff = json.loads(json_path.read_text(encoding="utf-8"))
    handoff["handoff_goal"] = "Changed after approval."
    json_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")

    stale = runtime.validate_handoff(project, initialized["slug"])

    assert stale["valid"] is False
    assert "review_digest_mismatch" in stale["error_codes"]


def test_mark_consumed_requires_matching_downstream_evidence(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Consumption", "Consumption integrity")
    markdown_path, json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    runtime.mark_ready(project, initialized["slug"])
    feature_dir = project / ".specify" / "features" / "001-consumption"
    brainstorming = feature_dir / "brainstorming"
    brainstorming.mkdir(parents=True)
    (brainstorming / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "entry_source": "sp-discussion",
                "discussion_slug": initialized["slug"],
                "source_handoff": str(markdown_path.relative_to(project).as_posix()),
                "source_handoff_json": str(json_path.relative_to(project).as_posix()),
                "review_digest": review_digest,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    consumed = runtime.mark_consumed(project, initialized["slug"], str(feature_dir.relative_to(project)))

    assert consumed["discussion"]["status"] == "completed"
    assert consumed["discussion"]["consumption"]["status"] == "consumed"
    assert consumed["discussion"]["consumption"]["consumer_path"] == feature_dir.relative_to(project).as_posix()


def test_mark_consumed_rejects_missing_mismatched_and_escaping_targets(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Rejected Consumption", "Rejected consumption")
    _write_confirmed_handoff(runtime, project, initialized["slug"])
    runtime.mark_ready(project, initialized["slug"])

    with pytest.raises(ValueError, match="consumer evidence"):
        runtime.mark_consumed(project, initialized["slug"], ".specify/features/missing")

    outside = tmp_path.parent / "outside-feature"
    outside.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="inside the project root"):
        runtime.mark_consumed(project, initialized["slug"], str(outside))


def test_discussion_templates_define_typed_state_and_consumer_neutral_handoff():
    state_schema = json.loads((PROJECT_ROOT / "templates" / "discussion-state-schema.json").read_text(encoding="utf-8"))
    handoff_schema = json.loads(
        (PROJECT_ROOT / "templates" / "discussion-handoff-schema.json").read_text(encoding="utf-8")
    )
    handoff_template = json.loads(
        (PROJECT_ROOT / "templates" / "discussion-handoff-template.json").read_text(encoding="utf-8")
    )

    assert state_schema["properties"]["lifecycle_phase"]["enum"] == [
        "explore",
        "ground",
        "decide",
        "prepare",
        "review",
        "ready",
        "consumed",
        "closed",
    ]
    assert "planning_constraints" in handoff_schema["properties"]["downstream_instructions"]["properties"]
    assert "recommended_sequence" not in handoff_template["downstream_instructions"]
    assert "candidate_id" not in handoff_template
    assert handoff_template["handoff_kind"] == "discussion_requirement_contract"
