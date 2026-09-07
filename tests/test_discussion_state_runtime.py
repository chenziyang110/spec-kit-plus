import importlib.util
import json
from contextlib import contextmanager
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


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
    template_dir = tmp_path / ".specify" / "templates"
    template_dir.mkdir()
    (template_dir / "discussion-handoff-template.json").write_text(
        (PROJECT_ROOT / "templates" / "discussion-handoff-template.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    return tmp_path


def _complete_checkpoint_payload(project: Path) -> dict:
    return {
        "summary": "Requirement contract is ready for deterministic handoff.",
        "lifecycle_phase": "prepare",
        "requirements_snapshot": {
            "target_need": "A compact and reliable discussion workflow.",
            "actors": ["agent", "user"],
            "scenarios": ["resume a discussion after compaction"],
            "constraints": ["Human replies remain human-centered."],
            "success_criteria": ["Invalid handoffs cannot become ready."],
            "design_direction": ["Typed backstage with a natural frontstage."],
            "optimal_solution_approach": ["Use a shared runtime and schema-driven handoff."],
            "scope": {
                "in": ["discussion workflow"],
                "out": ["implementation planning"],
                "deferred": [],
            },
        },
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
        # Pure-conversation legacy fixture. Material-backed handoffs are tested
        # through the native runtime, which alone can issue reading receipts.
        "source_materials": [],
        "blocking_unknowns": [],
        "soft_unknowns": [],
        "conflicts": [],
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
        "truth_pass_status": "complete",
        "verified_project_facts": ["discussion runtime writes checkpoint state"],
        "evidence_checked": ["scripts/shared/discussion-state.py"],
        "advice_confidence": "high",
    }


def _reviewable_handoff_payload(slug: str, recommended_consumer: str = "sp-specify") -> dict:
    return {
        "handoff_goal": "Make discussion state deterministic and agent-efficient.",
        "consumer_eligibility": {
            "sp-specify": {
                "status": "ready" if recommended_consumer == "sp-specify" else "blocked",
                "reason": "Requirement contract is complete.",
            },
            "sp-quick": {
                "status": "ready" if recommended_consumer == "sp-quick" else "blocked",
                "reason": "The selected consumer owns this exact lineage.",
            },
        },
        "recommended_consumer": recommended_consumer,
        "quality_gate": {
            "status": "self_reviewed",
            "self_reviewed_at": "2026-07-10T00:00:00Z",
            "user_review_required": True,
            "user_confirmed_at": None,
            "confirmed_digest": None,
            "blocked_reasons": [],
        },
        "discussion_slug": slug,
    }


def _write_confirmed_handoff(
    runtime,
    project: Path,
    slug: str,
    *,
    recommended_consumer: str = "sp-specify",
) -> tuple[Path, str]:
    workspace = project / ".specify" / "discussions" / slug
    json_path = workspace / "handoff-to-specify.json"
    resolved_checkpoint = runtime.resolve_discussion(project, "continue", slug)
    runtime.checkpoint_discussion(
        project,
        slug,
        _complete_checkpoint_payload(project),
        expected_state_sha256=resolved_checkpoint["binding"]["state_sha256"],
    )
    payload = _reviewable_handoff_payload(slug, recommended_consumer)
    resolved = runtime.resolve_discussion(project, "continue", slug)
    written = runtime.write_handoff(
        project,
        slug,
        payload,
        expected_state_sha256=resolved["binding"]["state_sha256"],
    )
    review_digest = written["review_digest"]
    runtime.confirm_handoff(project, slug, review_digest)
    return json_path, review_digest


def test_initialize_discussion_creates_minimal_typed_state(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)

    payload = runtime.initialize_discussion(project, "Agent Friendly Discussion", "Agent-friendly discussion")

    workspace = Path(payload["workspace_path"])
    state = json.loads((workspace / "discussion-state.json").read_text(encoding="utf-8"))
    markdown = (workspace / "discussion-state.md").read_text(encoding="utf-8")
    assert payload["slug"] == "agent-friendly-discussion"
    assert state["version"] == 3
    assert state["status_family"] == "discussion"
    assert state["status"] == "active"
    assert state["lifecycle_phase"] == "explore"
    assert state["turn_packet"]["persistence_mode"] == "frontstage-only"
    assert (workspace / "discussion-log.jsonl").is_file()
    assert not (workspace / "requirements.md").exists()
    assert "## Forbidden Actions" not in markdown
    assert markdown.count("# Discussion State:") == 1


def test_initialize_discussion_sets_topic_ownership_anchor(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)

    payload = runtime.initialize_discussion(project, "Checkout Decisions", "Checkout decisions")

    workspace = Path(payload["workspace_path"])
    state = json.loads((workspace / "discussion-state.json").read_text(encoding="utf-8"))
    ownership = state["turn_packet"]["topic_ownership"]
    assert ownership["anchor"] == "checkout-decisions"
    assert ownership["owned_scope"] == ["Checkout decisions"]
    assert ownership["routed_topics"] == []


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
            "user_goal": "Ship durable discussion recovery.",
            "confirmed_decisions": ["Keep machine state backstage."],
            "current_recommendation": "Use typed state.",
            "context_boundary": {"status": "in-progress", "current_project_root": "repo-root"},
            "open_questions": ["What is the handoff consumer?"],
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
    assert state["turn_packet"]["user_goal"] == "Ship durable discussion recovery."
    assert state["turn_packet"]["confirmed_decisions"] == ["Keep machine state backstage."]
    assert state["turn_packet"]["context_boundary"]["status"] == "in-progress"
    assert state["turn_packet"]["open_questions"] == ["What is the handoff consumer?"]
    assert state["turn_packet"]["current_recommendation"] == "Use typed state."
    assert events[-1]["kind"] == "durable-checkpoint"
    assert events[-1]["version"] == 2
    assert events[-1]["snapshot_sha256"] == state["latest_checkpoint"]["snapshot_sha256"]
    assert "Human frontstage" in events[-1]["summary"]


def test_checkpoint_records_full_semantic_snapshot(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Semantic Snapshot", "Semantic snapshot")

    payload = runtime.checkpoint_discussion(
        project,
        initialized["slug"],
        {
            "summary": "Material, target, and advice state are durable.",
            "lifecycle_phase": "ground",
            "requirements_snapshot": {
                "target_need": "Preserve user-provided discussion material.",
                "success_criteria": ["Checkpoint can reconstruct the decision."],
            },
            "implementation_target": {
                "actual_project": "spec-kit-plus",
                "target_root": str(project.resolve()),
                "target_paths": ["templates/commands/discussion.md"],
            },
            "source_materials": [
                {
                    "id": "MAT-001",
                    "material_type": "user_note",
                    "locator": "chat:turn-1",
                    "inspection_status": "inspected",
                    "summary": "User asked whether discussion clarifies intent and records materials.",
                    "claims": ["Discussion must record user-provided material."],
                    "coverage_gaps": [],
                    "sensitivity": "safe",
                }
            ],
            "blocking_unknowns": [],
            "soft_unknowns": ["Exact prose can stay compact."],
            "conflicts": [],
            "downstream_instructions": {
                "planning_constraints": ["Carry MAT-001 forward."],
            },
            "discussion_decision_digest": {
                "locked_direction": ["Use a source material ledger."],
            },
            "must_preserve": [
                {
                    "id": "MP-001",
                    "type": "requirement",
                    "claim": "Preserve material ledger",
                    "source": "chat",
                    "downstream_requirement": "Plan sees material provenance",
                    "blocking_level": "hard",
                    "owner": "sp-discussion",
                    "latest_resolve_phase": "ground",
                    "status": "active",
                }
            ],
            "verified_project_facts": ["discussion runtime writes checkpoint state"],
            "evidence_checked": ["scripts/shared/discussion-state.py"],
            "advice_confidence": "high",
        },
    )

    event = payload["event"]
    checkpoint = payload["discussion"]["latest_checkpoint"]
    assert payload["turn_packet"]["version"] == 2
    assert event["version"] == 2
    assert event["snapshot_sha256"] == checkpoint["snapshot_sha256"]
    assert payload["turn_packet"]["source_materials"][0]["id"] == "MAT-001"
    assert "source_materials" in event["changed_fields"]


def test_state_markdown_summarizes_semantics_without_restricted_material(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Restricted Material", "Restricted material")
    workspace = Path(initialized["workspace_path"])

    runtime.checkpoint_discussion(
        project,
        initialized["slug"],
        {
            **_complete_checkpoint_payload(project),
            "requirements_snapshot": {
                **_complete_checkpoint_payload(project)["requirements_snapshot"],
                "target_need": "Clarify a sensitive user-provided goal.",
            },
            "source_materials": [
                {
                    "id": "MAT-001",
                    "material_type": "private_note",
                    "locator": "secret://do-not-render",
                    "inspection_status": "inspected",
                    "summary": "Do not render this restricted summary.",
                    "claims": ["Sensitive note was inspected."],
                    "coverage_gaps": [],
                    "sensitivity": "restricted",
                }
            ],
            "source_evidence": [
                {
                    "source_type": "discussion",
                    "evidence_status": "verified",
                    "source": "chat",
                    "claim": "Sensitive note was inspected.",
                    "material_id": "MAT-001",
                }
            ],
        },
    )

    markdown = (workspace / "discussion-state.md").read_text(encoding="utf-8")

    assert "## Requirements Snapshot" in markdown
    assert "Clarify a sensitive user-provided goal." in markdown
    assert "MAT-001(inspected) [restricted]" in markdown
    assert "snapshot_sha256:" in markdown
    assert "secret://do-not-render" not in markdown
    assert "Do not render this restricted summary." not in markdown


def test_checkpoint_persists_topic_ownership(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Topic Ownership", "Topic ownership")

    payload = runtime.checkpoint_discussion(
        project,
        initialized["slug"],
        {
            "summary": "Route side topics without polluting this discussion.",
            "topic_ownership": {
                "anchor": "topic-ownership",
                "owned_scope": ["primary checkout requirement"],
                "routed_topics": [
                    {
                        "topic": "billing export",
                        "route": "branch_new",
                        "target_slug": "billing-export",
                    }
                ],
            },
        },
    )

    ownership = payload["discussion"]["turn_packet"]["topic_ownership"]
    assert ownership["anchor"] == "topic-ownership"
    assert ownership["routed_topics"][0]["route"] == "branch_new"


def test_checkpoint_rejects_foreign_topic_owner_slug(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Owned Topic", "Owned topic")

    with pytest.raises(ValueError, match="owner_slug must match discussion slug"):
        runtime.checkpoint_discussion(
            project,
            initialized["slug"],
            {
                "summary": "Reject cross-discussion topic ownership.",
                "topic_ownership": {
                    "owner_slug": "other-discussion",
                    "anchor": initialized["slug"],
                    "owned_scope": ["owned topic"],
                    "routed_topics": [],
                },
            },
        )


def test_checkpoint_helper_uses_expected_state_sha_before_mutating(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    first = runtime.initialize_discussion(project, "First Active", "First active")
    runtime.initialize_discussion(project, "Second Active", "Second active")
    resolved = runtime.resolve_discussion(project, "continue", first["slug"])
    expected_sha = resolved["binding"]["state_sha256"]
    stale_sha = "0" * 64 if expected_sha != "0" * 64 else "1" * 64

    with pytest.raises(ValueError, match="expected-state-sha256|state sha|stale"):
        runtime.checkpoint_discussion(
            project,
            first["slug"],
            {"summary": "Reject a stale checkpoint write."},
            expected_state_sha256=stale_sha,
        )

    checkpointed = runtime.checkpoint_discussion(
        project,
        first["slug"],
        {"summary": "Accept the resolver-bound checkpoint write."},
        expected_state_sha256=expected_sha,
    )

    assert checkpointed["discussion"]["summary"] == "Accept the resolver-bound checkpoint write."


def test_write_handoff_helper_uses_expected_state_sha_before_mutating(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    first = runtime.initialize_discussion(project, "First Handoff", "First handoff")
    runtime.initialize_discussion(project, "Second Handoff", "Second handoff")
    resolved = runtime.resolve_discussion(project, "continue", first["slug"])
    runtime.checkpoint_discussion(
        project,
        first["slug"],
        _complete_checkpoint_payload(project),
        expected_state_sha256=resolved["binding"]["state_sha256"],
    )
    resolved = runtime.resolve_discussion(project, "continue", first["slug"])
    expected_sha = resolved["binding"]["state_sha256"]
    stale_sha = "f" * 64 if expected_sha != "f" * 64 else "e" * 64
    workspace = Path(first["workspace_path"])
    handoff_payload = _reviewable_handoff_payload(first["slug"])
    handoff_payload["handoff_goal"] = "Write only when the focus binding is current."

    with pytest.raises(ValueError, match="expected-state-sha256|state sha|stale"):
        runtime.write_handoff(
            project,
            first["slug"],
            handoff_payload,
            expected_state_sha256=stale_sha,
        )
    assert not (workspace / "handoff-to-specify.json").exists()

    written = runtime.write_handoff(
        project,
        first["slug"],
        handoff_payload,
        expected_state_sha256=expected_sha,
    )

    assert written["review_digest"]
    assert (workspace / "handoff-to-specify.json").is_file()


def test_write_handoff_requires_current_semantic_checkpoint(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "No Checkpoint", "No checkpoint")

    with pytest.raises(ValueError, match="missing_semantic_checkpoint"):
        runtime.write_handoff(
            project,
            initialized["slug"],
            _reviewable_handoff_payload(initialized["slug"]),
        )


def test_write_handoff_rejects_checkpoint_with_empty_core_requirements(
    runtime, tmp_path: Path
):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(
        project, "Incomplete Requirements", "Incomplete requirements"
    )
    runtime.checkpoint_discussion(
        project,
        initialized["slug"],
        {"summary": "A savepoint exists, but the requirement contract is incomplete."},
    )

    with pytest.raises(ValueError, match="missing_requirements"):
        runtime.write_handoff(
            project,
            initialized["slug"],
            _reviewable_handoff_payload(initialized["slug"]),
        )


def test_write_handoff_allows_no_material_when_user_supplied_none(
    runtime, tmp_path: Path
):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(
        project, "No Supplied Material", "No supplied material"
    )
    checkpoint_payload = _complete_checkpoint_payload(project)
    checkpoint_payload["source_materials"] = []
    checkpoint_payload["source_evidence"] = [
        {
            "source_type": "user_confirmation",
            "evidence_status": "confirmed",
            "source": "discussion",
            "claim": "The user supplied no external material for this topic.",
        }
    ]
    runtime.checkpoint_discussion(project, initialized["slug"], checkpoint_payload)

    written = runtime.write_handoff(
        project,
        initialized["slug"],
        _reviewable_handoff_payload(initialized["slug"]),
    )
    payload = json.loads(Path(written["json_path"]).read_text(encoding="utf-8"))

    assert payload["source_materials"] == []


def test_source_material_digest_uses_cross_runtime_canonical_json(runtime):
    material = {
        "id": "MAT-001",
        "material_type": "user_note",
        "locator": "https://example.test/a?x=1&y=2",
        "summary": "Use <safe> reference",
        "inspection_status": "inspected",
        "claims": ["A & B"],
        "coverage_gaps": [],
        "sensitivity": "safe",
    }

    assert (
        runtime._material_digest(material)
        == "43dbbb0c92e0d1fc7f66430bf2d280417906aef09e12d43d670e36d910519aa2"
    )


def test_legacy_helper_cannot_claim_material_readiness(runtime, tmp_path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "material-owner", "Material owner")
    changes = _complete_checkpoint_payload(project)
    changes["source_materials"] = [{
        "id": "MAT-001", "material_type": "user_note", "locator": "chat:note",
        "inspection_status": "inspected", "summary": "Claims to have read everything.",
        "claims": ["A requirement near the end."], "coverage_gaps": [], "sensitivity": "safe",
    }]
    runtime.checkpoint_discussion(project, initialized["slug"], changes)

    with pytest.raises(ValueError, match="native.*runtime|specify-runtime discussion"):
        runtime.write_handoff(project, initialized["slug"], _reviewable_handoff_payload(initialized["slug"]))


@pytest.mark.parametrize("field", ["reading", "source_requirements"])
def test_legacy_checkpoint_cannot_author_native_material_proof(runtime, tmp_path, field):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "proof-owner", "Proof owner")
    changes = _complete_checkpoint_payload(project)
    if field == "reading":
        changes["source_materials"] = [{
            "id": "MAT-001", "material_type": "user_note", "locator": "chat:note",
            "inspection_status": "inspected", "summary": "Forged receipt.",
            "claims": ["Read."], "coverage_gaps": [], "sensitivity": "safe",
            "reading": {"version": 1, "delivered_unit_ids": ["U0001-forged"]},
        }]
    else:
        changes["requirements_snapshot"]["source_requirements"] = [{"id": "REQ-001"}]

    with pytest.raises(ValueError, match="native.*runtime|specify-runtime discussion"):
        runtime.checkpoint_discussion(project, initialized["slug"], changes)


def test_legacy_checkpoint_cannot_remove_a_registered_material(runtime, tmp_path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "keep-material", "Keep material")
    runtime.checkpoint_discussion(project, initialized["slug"], {"source_materials": [{
        "id": "MAT-001", "material_type": "user_note", "locator": "chat:note",
        "inspection_status": "pending", "summary": "Needs full reading.",
        "claims": ["A requirement near the end."], "coverage_gaps": ["unread"], "sensitivity": "safe",
    }]})

    with pytest.raises(ValueError, match="cannot be silently removed"):
        runtime.checkpoint_discussion(project, initialized["slug"], {"source_materials": []})


def test_legacy_reader_can_inspect_native_material_before_extraction(runtime, tmp_path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "native-read-only", "Native read only")
    workspace = project / ".specify" / "discussions" / initialized["slug"]
    state, _ = runtime._load_state(workspace)
    # Simulate the native owner's persisted import, before semantic extraction.
    state["turn_packet"]["source_materials"] = [{
        "id": "MAT-1000", "material_type": "text", "locator": "notes.txt",
        "inspection_status": "pending", "summary": "Imported; extraction pending.",
        "claims": [], "coverage_gaps": [], "sensitivity": "safe", "reading": {"version": 1},
    }]
    runtime._persist_state(workspace, state)

    result = runtime.discussion_status(project, initialized["slug"])
    assert result["discussion"]["turn_packet"]["source_materials"][0]["claims"] == []
    with pytest.raises(ValueError, match="native runtime"):
        runtime.checkpoint_discussion(project, initialized["slug"], {"summary": "Compatibility write"})


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"advice_confidence": "certain"}, "advice_confidence"),
        ({"source_evidence": "not-a-list"}, "source_evidence"),
        (
            {
                "source_evidence": [
                    {
                        "source_type": "discussion",
                        "evidence_status": "verified",
                        "source": "",
                        "claim": "A claim without a source must not persist.",
                    }
                ]
            },
            "source_evidence",
        ),
    ],
)
def test_checkpoint_rejects_invalid_semantic_shapes(
    runtime, tmp_path: Path, changes: dict, message: str
):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Invalid Semantic Shape", "Invalid semantic shape")

    with pytest.raises(ValueError, match=message):
        runtime.checkpoint_discussion(project, initialized["slug"], changes)


def test_legacy_state_nested_semantics_receive_v3_defaults(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Legacy Nested State", "Legacy nested state")
    state_path = Path(initialized["workspace_path"]) / "discussion-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["version"] = 2
    state["turn_packet"]["version"] = 1
    state["turn_packet"]["requirements_snapshot"] = {"target_need": "Preserve a partial legacy snapshot."}
    state_path.write_text(json.dumps(state), encoding="utf-8")

    resumed = runtime.resume_context(project, initialized["slug"])
    requirements = resumed["turn_packet"]["requirements_snapshot"]

    assert resumed["turn_packet"]["version"] == 2
    assert requirements["target_need"] == "Preserve a partial legacy snapshot."
    assert requirements["actors"] == []
    assert requirements["non_goals"] == []
    assert requirements["scope"] == {"in": [], "out": [], "deferred": []}


def test_resolved_unknowns_and_conflicts_do_not_fake_open_counts(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Resolved Readiness", "Resolved readiness")
    checkpoint_payload = _complete_checkpoint_payload(project)
    checkpoint_payload["blocking_unknowns"] = [
        {
            "id": "UQ-001",
            "question": "Which target owns the change?",
            "owner": "user",
            "status": "resolved",
            "latest_resolve_phase": "prepare",
            "resolution_evidence": "The user selected spec-kit-plus.",
        }
    ]
    checkpoint_payload["conflicts"] = [
        {
            "id": "CF-001",
            "claim": "Two target roots were proposed.",
            "status": "resolved",
            "resolution": "Use the active repository.",
            "resolution_evidence": "The target boundary was locked.",
        }
    ]
    runtime.checkpoint_discussion(project, initialized["slug"], checkpoint_payload)

    written = runtime.write_handoff(
        project,
        initialized["slug"],
        _reviewable_handoff_payload(initialized["slug"]),
    )
    payload = json.loads(Path(written["json_path"]).read_text(encoding="utf-8"))
    handoff_schema = json.loads(
        (PROJECT_ROOT / "templates" / "discussion-handoff-schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload["hard_unknown_count"] == 0
    assert payload["open_conflict_count"] == 0
    Draft202012Validator(handoff_schema).validate(payload)
    markdown = (
        project
        / ".specify"
        / "discussions"
        / initialized["slug"]
        / "discussion-state.md"
    ).read_text(encoding="utf-8")
    assert "blocking_unknown_count: 0" in markdown
    assert "open_conflict_count: 0" in markdown


def test_checkpoint_rejects_unknown_fields(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Unknown fields", "Unknown checkpoint fields")

    try:
        runtime.checkpoint_discussion(
            project,
            initialized["slug"],
            {"summary": "x", "not_a_real_field": True},
        )
        raise AssertionError("expected unknown checkpoint fields to fail")
    except ValueError as exc:
        assert "unknown fields" in str(exc)
        assert "not_a_real_field" in str(exc)


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


def test_validate_handoff_rechecks_snapshot_materials_and_counts(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Readiness Semantics", "Readiness semantics")
    checkpoint_payload = {
        **_complete_checkpoint_payload(project),
        "source_evidence": [
                {
                    "source_type": "discussion",
                    "evidence_status": "verified",
                    "source": "chat",
                    "claim": "Handoff readiness must be semantic.",
                    "material_id": "MAT-001",
                }
            ],
        "source_materials": [
                {
                    "id": "MAT-001",
                    "material_type": "user_note",
                    "locator": "chat:turn-1",
                    "inspection_status": "pending",
                    "summary": "User supplied a note.",
                    "claims": ["The note must be read."],
                    "coverage_gaps": ["not inspected"],
                    "sensitivity": "safe",
                }
            ],
    }
    runtime.checkpoint_discussion(project, initialized["slug"], checkpoint_payload)
    handoff_payload = _reviewable_handoff_payload(initialized["slug"])
    handoff_payload["handoff_goal"] = "Preserve semantic readiness."

    with pytest.raises(ValueError, match="source_materials|draft is invalid"):
        runtime.write_handoff(project, initialized["slug"], handoff_payload)

    checkpoint_payload["source_materials"][0]["inspection_status"] = "inspected"
    checkpoint_payload["source_materials"][0]["coverage_gaps"] = []
    runtime.checkpoint_discussion(project, initialized["slug"], checkpoint_payload)
    with pytest.raises(ValueError, match="native runtime"):
        runtime.write_handoff(project, initialized["slug"], handoff_payload)

    # Preserve the separate stale-checkpoint assertion on a conversation-only
    # session; do not erase the registered material to bypass its native owner.
    project = tmp_path / "snapshot-case"
    project.mkdir()
    _setup_project(project)
    initialized = runtime.initialize_discussion(project, "Snapshot Semantics", "Snapshot semantics")
    runtime.checkpoint_discussion(project, initialized["slug"], _complete_checkpoint_payload(project))
    handoff_payload = _reviewable_handoff_payload(initialized["slug"])
    written = runtime.write_handoff(project, initialized["slug"], handoff_payload)
    runtime.confirm_handoff(project, initialized["slug"], written["review_digest"])
    runtime.checkpoint_discussion(
        project,
        initialized["slug"],
        {"summary": "State changed", "soft_unknowns": ["new soft unknown"]},
    )

    stale = runtime.validate_handoff(project, initialized["slug"])

    assert stale["valid"] is False
    assert "discussion_snapshot_digest_mismatch" in stale["error_codes"]


def test_draft_validation_and_digest_confirmation_are_separate_transitions(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Review first", "Review before confirmation")
    json_path, _old_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["quality_gate"].update(
        {
            "status": "self_reviewed",
            "self_reviewed_at": "2026-07-22T00:00:00Z",
            "user_confirmed_at": None,
            "confirmed_digest": None,
        }
    )

    written = runtime.write_handoff(project, initialized["slug"], payload)
    review_digest = written["review_digest"]
    draft_validation = runtime.validate_handoff(
        project,
        initialized["slug"],
        validation_mode="draft",
    )
    ready_validation = runtime.validate_handoff(
        project,
        initialized["slug"],
        validation_mode="ready",
    )

    assert draft_validation["valid"] is True
    assert ready_validation["valid"] is False
    assert "handoff_not_user_confirmed" in ready_validation["error_codes"]

    confirmation = runtime.confirm_handoff(project, initialized["slug"], review_digest)
    confirmed_payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert confirmation["review_digest"] == review_digest
    assert confirmed_payload["quality_gate"]["status"] == "user_confirmed"
    assert confirmed_payload["quality_gate"]["confirmed_digest"] == review_digest
    assert confirmed_payload["quality_gate"]["user_confirmed_at"]
    assert runtime.validate_handoff(
        project,
        initialized["slug"],
        validation_mode="ready",
    )["valid"] is True


def test_semantic_handoff_write_invalidates_earlier_confirmation(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Changed draft", "Changed draft")
    json_path, _review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    runtime.write_handoff(project, initialized["slug"], payload)
    rewritten = json.loads(json_path.read_text(encoding="utf-8"))

    assert rewritten["quality_gate"]["status"] == "self_reviewed"
    assert rewritten["quality_gate"]["confirmed_digest"] is None
    assert rewritten["quality_gate"]["user_confirmed_at"] is None


def test_confirm_handoff_rejects_a_stale_review_digest(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Stale digest", "Stale digest")
    json_path, old_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["handoff_goal"] = "A materially revised handoff goal."

    rewritten = runtime.write_handoff(project, initialized["slug"], payload)

    assert rewritten["review_digest"] != old_digest
    with pytest.raises(ValueError, match="does not match the current handoff"):
        runtime.confirm_handoff(project, initialized["slug"], old_digest)


def test_confirm_handoff_retry_does_not_reopen_a_ready_discussion(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Confirm retry", "Confirm retry")
    _json_path, review_digest = _write_confirmed_handoff(
        runtime, project, initialized["slug"]
    )
    runtime.mark_ready(project, initialized["slug"])

    retried = runtime.confirm_handoff(project, initialized["slug"], review_digest)

    assert retried["discussion"]["status"] == "handoff-ready"
    assert retried["discussion"]["lifecycle_phase"] == "ready"
    assert retried["discussion"]["next_command"] == "sp-specify"


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
    assert "design_context" not in payload
    assert isinstance(payload["discussion_decision_digest"]["design_context"], dict)
    assert not json_path.with_suffix(".md").exists()


def test_write_handoff_carries_topic_ownership_owner_slug(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Owned Handoff", "Owned handoff")
    workspace = Path(initialized["workspace_path"])
    state_path = workspace / "discussion-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["turn_packet"]["topic_ownership"] = {
        "anchor": "owned-handoff",
        "owned_scope": ["owned handoff"],
        "routed_topics": [
            {
                "topic": "billing export",
                "route": "branch_new",
                "target_slug": "billing-export",
            }
        ],
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")

    json_path, _review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["topic_ownership"]["owner_slug"] == initialized["slug"]
    assert payload["topic_ownership"]["routed_topics"][0]["target_slug"] == "billing-export"


def test_runtime_topic_ownership_artifacts_match_published_schemas(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(
        project, "Schema Bound Topic", "Schema-bound topic"
    )
    runtime.checkpoint_discussion(
        project,
        initialized["slug"],
        {
            "summary": "Keep side topics pointer-only.",
            "topic_ownership": {
                "anchor": initialized["slug"],
                "owned_scope": ["schema-bound topic"],
                "routed_topics": [
                    {
                        "topic": "billing export",
                        "route": "branch_new",
                        "target_slug": "billing-export",
                    }
                ],
            },
        },
    )
    handoff_path, _digest = _write_confirmed_handoff(
        runtime, project, initialized["slug"]
    )

    state_schema = json.loads(
        (PROJECT_ROOT / "templates" / "discussion-state-schema.json").read_text(
            encoding="utf-8"
        )
    )
    handoff_schema = json.loads(
        (PROJECT_ROOT / "templates" / "discussion-handoff-schema.json").read_text(
            encoding="utf-8"
        )
    )
    state = json.loads(
        (Path(initialized["workspace_path"]) / "discussion-state.json").read_text(
            encoding="utf-8"
        )
    )
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))

    Draft202012Validator(state_schema).validate(state)
    Draft202012Validator(handoff_schema).validate(handoff)


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
    resolved = runtime.resolve_discussion(project, "sp-specify", initialized["slug"])
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
                "state_sha256": resolved["binding"]["state_sha256"],
                "recommended_consumer": "sp-specify",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    consumed = runtime.mark_consumed(project, initialized["slug"], str(feature_dir.relative_to(project)))

    assert consumed["discussion"]["status"] == "completed"
    assert consumed["discussion"]["consumption"]["status"] == "consumed"
    assert consumed["discussion"]["consumption"]["consumer_path"] == feature_dir.relative_to(project).as_posix()
    assert consumed["discussion"]["consumption"]["source_contract"] == json_path.relative_to(project).as_posix()
    assert consumed["discussion"]["consumption"]["review_digest"] == review_digest
    assert consumed["discussion"]["consumption"]["state_sha256"] == resolved["binding"]["state_sha256"]
    assert consumed["discussion"]["consumption"]["recommended_consumer"] == "sp-specify"


def test_direct_mutation_helpers_acquire_the_shared_lock(
    runtime, tmp_path: Path, monkeypatch
):
    project = _setup_project(tmp_path)
    ready = runtime.initialize_discussion(project, "Direct Lock", "Direct lock")
    _json_path, review_digest = _write_confirmed_handoff(
        runtime, project, ready["slug"]
    )
    entered: list[Path] = []

    @contextmanager
    def tracked_lock(project_root: Path):
        entered.append(Path(project_root).resolve())
        yield

    monkeypatch.setattr(runtime, "_discussion_mutation_lock", tracked_lock)

    runtime.confirm_handoff(project, ready["slug"], review_digest)
    runtime.mark_ready(project, ready["slug"])
    closable = runtime.initialize_discussion(project, "Closable", "Closable")
    runtime.close_discussion(project, closable["slug"], "abandoned")
    runtime.archive_discussion(project, closable["slug"])
    runtime.rebuild_index(project)

    assert entered == [project.resolve()] * 6


def test_mark_consumed_requires_source_not_already_consumed(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Already Consumed", "Already consumed")
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    runtime.mark_ready(project, initialized["slug"])
    resolved = runtime.resolve_discussion(project, "sp-specify", initialized["slug"])
    state_path = Path(initialized["workspace_path"]) / "discussion-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["consumption"]["status"] = "consumed"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    feature_dir = project / ".specify" / "features" / "001-already-consumed"
    brainstorming = feature_dir / "brainstorming"
    brainstorming.mkdir(parents=True)
    (brainstorming / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "entry_source": "sp-discussion",
                "discussion_slug": initialized["slug"],
                "source_contract": json_path.relative_to(project).as_posix(),
                "review_digest": review_digest,
                "state_sha256": resolved["binding"]["state_sha256"],
                "recommended_consumer": "sp-specify",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not_consumed|already consumed"):
        runtime.mark_consumed(project, initialized["slug"], str(feature_dir.relative_to(project)))


def test_mark_consumed_requires_current_source_handoff_ready_valid(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Stale Source", "Stale source")
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    runtime.mark_ready(project, initialized["slug"])
    resolved = runtime.resolve_discussion(project, "sp-specify", initialized["slug"])
    handoff = json.loads(json_path.read_text(encoding="utf-8"))
    handoff["handoff_goal"] = "Changed after the ready validation."
    json_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")
    feature_dir = project / ".specify" / "features" / "001-stale-source"
    brainstorming = feature_dir / "brainstorming"
    brainstorming.mkdir(parents=True)
    (brainstorming / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "entry_source": "sp-discussion",
                "discussion_slug": initialized["slug"],
                "source_contract": json_path.relative_to(project).as_posix(),
                "review_digest": review_digest,
                "state_sha256": resolved["binding"]["state_sha256"],
                "recommended_consumer": "sp-specify",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="handoff|ready|digest"):
        runtime.mark_consumed(project, initialized["slug"], str(feature_dir.relative_to(project)))


@pytest.mark.parametrize(
    ("state_field", "state_value"),
    [
        ("contract_path", ".specify/discussions/other/handoff-to-specify.json"),
        ("review_digest", "1" * 64),
        ("recommended_consumer", "sp-quick"),
    ],
)
def test_mark_consumed_requires_state_and_handoff_lineage_to_match(
    runtime,
    tmp_path: Path,
    state_field: str,
    state_value: str,
):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Lineage Drift", "Lineage drift")
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    runtime.mark_ready(project, initialized["slug"])
    resolved = runtime.resolve_discussion(project, "sp-specify", initialized["slug"])
    state_path = Path(initialized["workspace_path"]) / "discussion-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["handoff"][state_field] = state_value
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    feature_dir = project / ".specify" / "features" / f"001-lineage-drift-{state_field}"
    brainstorming = feature_dir / "brainstorming"
    brainstorming.mkdir(parents=True)
    (brainstorming / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "entry_source": "sp-discussion",
                "discussion_slug": initialized["slug"],
                "source_contract": json_path.relative_to(project).as_posix(),
                "review_digest": review_digest,
                "state_sha256": resolved["binding"]["state_sha256"],
                "recommended_consumer": "sp-specify",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="handoff|lineage|source|review|consumer"):
        runtime.mark_consumed(project, initialized["slug"], str(feature_dir.relative_to(project)))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("state_sha256", "0" * 64),
        ("recommended_consumer", "sp-quick"),
    ],
)
def test_mark_consumed_rejects_mismatched_consumer_lineage_fields(
    runtime,
    tmp_path: Path,
    field: str,
    value: str,
):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Evidence Lineage", "Evidence lineage")
    json_path, review_digest = _write_confirmed_handoff(runtime, project, initialized["slug"])
    runtime.mark_ready(project, initialized["slug"])
    resolved = runtime.resolve_discussion(project, "sp-specify", initialized["slug"])
    evidence_payload = {
        "entry_source": "sp-discussion",
        "discussion_slug": initialized["slug"],
        "source_contract": json_path.relative_to(project).as_posix(),
        "review_digest": review_digest,
        "state_sha256": resolved["binding"]["state_sha256"],
        "recommended_consumer": "sp-specify",
    }
    evidence_payload[field] = value
    feature_dir = project / ".specify" / "features" / f"001-evidence-lineage-{field}"
    brainstorming = feature_dir / "brainstorming"
    brainstorming.mkdir(parents=True)
    (brainstorming / "handoff-to-specify.json").write_text(
        json.dumps(evidence_payload) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=field):
        runtime.mark_consumed(project, initialized["slug"], str(feature_dir.relative_to(project)))


def test_mark_consumed_requires_quick_status_to_bind_paths_and_digest(runtime, tmp_path: Path):
    project = _setup_project(tmp_path)
    initialized = runtime.initialize_discussion(project, "Quick consumption", "Quick consumption integrity")
    json_path, review_digest = _write_confirmed_handoff(
        runtime,
        project,
        initialized["slug"],
        recommended_consumer="sp-quick",
    )
    runtime.mark_ready(project, initialized["slug"])
    resolved = runtime.resolve_discussion(project, "sp-quick", initialized["slug"])
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
                f"state_sha256: {resolved['binding']['state_sha256']}",
                "recommended_consumer: sp-quick",
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
    written = call("write-handoff-json", slug, json_path.read_text(encoding="utf-8"))
    assert written["review_digest"]
    assert call("validate-handoff", slug, "draft")["valid"] is True
    assert call("confirm-handoff", slug, written["review_digest"])["review_digest"] == written[
        "review_digest"
    ]
    assert call("validate-handoff", slug, "ready")["valid"] is True
    assert call("mark-ready", slug)["discussion"]["status"] == "handoff-ready"
    resolved = runtime.resolve_discussion(project, "sp-specify", slug)

    feature_dir = project / ".specify" / "features" / "001-dispatcher"
    evidence_dir = feature_dir / "brainstorming"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "handoff-to-specify.json").write_text(
        json.dumps(
            {
                "discussion_slug": slug,
                "source_contract": json_path.relative_to(project).as_posix(),
                "review_digest": written["review_digest"],
                "state_sha256": resolved["binding"]["state_sha256"],
                "recommended_consumer": "sp-specify",
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

    Draft202012Validator.check_schema(state_schema)
    Draft202012Validator.check_schema(handoff_schema)
    assert state_schema["properties"]["version"]["const"] == 3
    assert handoff_schema["properties"]["version"]["const"] == 5
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
