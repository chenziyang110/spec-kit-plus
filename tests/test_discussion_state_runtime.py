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


def _write_confirmed_handoff(runtime, project: Path, slug: str) -> tuple[Path, str]:
    workspace = project / ".specify" / "discussions" / slug
    json_path = workspace / "handoff-to-specify.json"
    source_contract = f".specify/discussions/{slug}/handoff-to-specify.json"
    payload = {
        "version": 4,
        "handoff_kind": "discussion_requirement_contract",
        "status": "draft",
        "entry_source": "sp-discussion",
        "discussion_slug": slug,
        "source_contract": source_contract,
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
    written = runtime.write_handoff(project, slug, payload)
    review_digest = written["review_digest"]
    return json_path, review_digest


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
    assert markdown.count("# Discussion State:") == 1


def test_legacy_markdown_state_migrates_to_typed_shape(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    workspace = project / ".specify" / "discussions" / "legacy-review"
    workspace.mkdir(parents=True)
    (workspace / "discussion-state.md").write_text(
        "\n".join(
            [
                "# Discussion State: Legacy",
                "- slug: `legacy-review`",
                "- status: active",
                "- summary: 'Legacy review summary'",
                "- updated_at: 2026-07-10T00:00:00Z",
                "- current_stage: handoff-review",
                "- current_decision_frame: Review the migrated contract",
                "- handoff_review_status: draft",
                "- quality_gate_status: draft",
                "- handoff_to_specify: [not written]",
                "- handoff_to_specify_json: none",
                "- handoff_consumption_status: not_consumed",
                "- consumed_at: none",
                "- consumed_by_feature_dir: none",
                "- next_command: none",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = runtime.discussion_status(project, "legacy-review")["discussion"]

    assert payload["slug"] == "legacy-review"
    assert payload["summary"] == "Legacy review summary"
    assert payload["lifecycle_phase"] == "review"
    assert payload["turn_packet"]["current_decision_frame"] == "Review the migrated contract"
    assert payload["handoff"]["contract_path"] is None
    assert runtime._legacy_phase("context-grounding", "active") == "ground"
    assert runtime._legacy_phase("handoff-ready", "handoff-ready") == "ready"
    assert runtime._legacy_phase("anything", "completed") == "closed"


def test_legacy_json_state_drops_duplicate_handoff_path_fields(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "legacy-json", "Legacy JSON")
    state_path = Path(initialized["workspace_path"]) / "discussion-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["handoff"].pop("contract_path")
    state["handoff"]["markdown_path"] = ".specify/discussions/legacy-json/handoff-to-specify.md"
    state["handoff"]["json_path"] = ".specify/discussions/legacy-json/handoff-to-specify.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    payload = runtime.discussion_status(project, "legacy-json")["discussion"]

    assert payload["handoff"]["contract_path"].endswith("handoff-to-specify.json")
    assert "markdown_path" not in payload["handoff"]
    assert "json_path" not in payload["handoff"]


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
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])

    validation = runtime.validate_handoff(project, initialized["slug"])
    ready = runtime.mark_ready(project, initialized["slug"])

    assert validation["valid"] is True
    assert validation["review_digest"] == review_digest
    assert ready["discussion"]["status"] == "handoff-ready"
    assert ready["discussion"]["lifecycle_phase"] == "ready"
    handoff = json.loads(json_path.read_text(encoding="utf-8"))
    assert handoff["status"] == "handoff-ready"


def test_review_digest_ignores_confirmation_metadata_but_tracks_protected_changes(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Digest", "Digest behavior")
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["quality_gate"]["user_confirmed_at"] = "2030-01-01T00:00:00Z"
    payload["quality_gate"]["self_reviewed_at"] = "2030-01-01T00:00:01Z"
    payload["quality_gate"]["status"] = "draft"

    assert runtime.compute_review_digest(payload) == review_digest

    payload["handoff_goal"] = "A materially changed protected goal."
    assert runtime.compute_review_digest(payload) != review_digest


def test_write_handoff_persists_only_agent_contract(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Rendered Handoff", "Rendered handoff")
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["review_digest"] == review_digest
    assert payload["quality_gate"]["confirmed_digest"] == review_digest
    assert payload["source_contract"] == json_path.relative_to(project).as_posix()
    assert not json_path.with_suffix(".md").exists()


def test_validate_handoff_rejects_missing_json_and_stale_confirmation(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Invalid Handoff", "Invalid handoff")
    json_path, _digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    original = json_path.read_text(encoding="utf-8")
    json_path.unlink()

    missing = runtime.validate_handoff(project, initialized["slug"])

    assert missing["valid"] is False
    assert "missing_handoff_json" in missing["error_codes"]

    json_path.write_text(original, encoding="utf-8")
    handoff = json.loads(json_path.read_text(encoding="utf-8"))
    handoff["handoff_goal"] = "Changed after approval."
    json_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")

    stale = runtime.validate_handoff(project, initialized["slug"])

    assert stale["valid"] is False
    assert "review_digest_mismatch" in stale["error_codes"]


def test_mark_consumed_requires_matching_downstream_evidence(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Consumption", "Consumption integrity")
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    runtime.mark_ready(project, initialized["slug"])
    feature_dir = project / ".specify" / "features" / "001-consumption"
    brainstorming = feature_dir / "brainstorming"
    brainstorming.mkdir(parents=True)
    (brainstorming / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "entry_source": "sp-discussion",
                "discussion_slug": initialized["slug"],
                "source_contract": str(json_path.relative_to(project).as_posix()),
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


def test_mark_consumed_requires_quick_status_to_bind_paths_and_digest(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Quick consumption", "Quick consumption integrity")
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    runtime.mark_ready(project, initialized["slug"])
    quick_dir = project / ".planning" / "quick" / "001-quick-consumption"
    quick_dir.mkdir(parents=True)
    status_path = quick_dir / "STATUS.md"
    status_path.write_text(
        f"source_discussion_slug: {initialized['slug']}\nreview_digest: {review_digest}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="source contract"):
        runtime.mark_consumed(project, initialized["slug"], str(quick_dir.relative_to(project)))

    status_path.write_text(
        "\n".join(
            [
                f"source_discussion_slug: {initialized['slug']}",
                f"source_contract: {json_path.relative_to(project).as_posix()}",
                f"review_digest: {review_digest}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    consumed = runtime.mark_consumed(project, initialized["slug"], str(quick_dir.relative_to(project)))

    assert consumed["discussion"]["consumption"]["evidence_path"].endswith("STATUS.md")


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


def test_runtime_main_dispatches_complete_lifecycle(runtime, tmp_path: Path, monkeypatch, capsys):
    project = _setup_project(tmp_path)

    def call(mode: str, slug: str = "", value: str = "", include_all: str = "false"):
        monkeypatch.setattr(
            runtime.sys,
            "argv",
            ["discussion-state.py", str(project), mode, slug, value, include_all],
        )
        assert runtime.main() == 0
        return json.loads(capsys.readouterr().out)

    initialized = call("init", "dispatcher", "Dispatcher lifecycle")
    slug = initialized["slug"]
    assert call("list")["discussions"][0]["slug"] == slug
    assert call("status", slug)["discussion"]["slug"] == slug
    assert call("resume-context", slug)["turn_packet"]["discussion_slug"] == slug
    checkpoint = call(
        "checkpoint",
        slug,
        json.dumps({"summary": "Dispatch checkpoint", "lifecycle_phase": "prepare"}),
    )
    assert checkpoint["discussion"]["lifecycle_phase"] == "prepare"

    json_path, _digest = _write_confirmed_handoff(runtime, project, slug)
    written = call("write-handoff", slug, str(json_path))
    assert written["review_digest"]
    assert call("validate-handoff", slug)["valid"] is True
    assert call("mark-ready", slug)["discussion"]["status"] == "handoff-ready"

    feature_dir = project / ".specify" / "features" / "001-dispatcher"
    evidence_dir = feature_dir / "brainstorming"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "discussion_slug": slug,
                "source_contract": json_path.relative_to(project).as_posix(),
                "review_digest": written["review_digest"],
            }
        ),
        encoding="utf-8",
    )
    consumed = call("mark-consumed", slug, feature_dir.relative_to(project).as_posix())
    assert consumed["discussion"]["lifecycle_phase"] == "consumed"
    assert call("archive", slug)["discussion"]["archived"] is True

    second = call("init", "closed-dispatcher", "Closed dispatcher")
    assert call("close", second["slug"], "abandoned")["discussion"]["status"] == "abandoned"
    assert call("archive", second["slug"])["discussion"]["archived"] is True
    assert call("rebuild-index")["version"] == 2
    assert len(call("list", include_all="true")["discussions"]) == 2

    monkeypatch.setattr(
        runtime.sys,
        "argv",
        ["discussion-state.py", str(project), "unknown-mode", "", "", "false"],
    )
    with pytest.raises(ValueError, match="unknown mode"):
        runtime.main()


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
    assert handoff_schema["properties"]["coverage_status"]["enum"] == [
        "not_started",
        "in_progress",
        "complete",
        "blocked_by_handoff_integrity",
    ]
    assert any("if" in rule and "then" in rule for rule in handoff_schema["allOf"])
