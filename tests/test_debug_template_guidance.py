from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _assert_tier_roles(content: str) -> None:
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in content
    fast_smoke_index = content.index("fast smoke")
    focused_index = content.index("focused", fast_smoke_index)
    full_index = content.index("full", focused_index)

    fast_smoke_context = content[fast_smoke_index : fast_smoke_index + 180]
    focused_context = content[focused_index : focused_index + 220]
    full_context = content[full_index : full_index + 220]

    assert "cheapest" in fast_smoke_context or "early signal" in fast_smoke_context
    assert "accepting the fix" in focused_context or "acceptance" in focused_context
    assert "regression risk" in full_context or "broader regression" in full_context


def test_debug_template_documents_capability_aware_investigation() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in content
    assert "the leader orchestrates:" in content
    assert "before dispatch, every subagent lane needs a task contract" in content
    assert "structured handoff" in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "observer framing" in content
    assert "compressed observer framing" in content
    assert "full observer framing" in content
    assert "think subagent must not read source files" in content
    assert "think subagent must not inspect logs" in content
    assert "think subagent must not read test files" in content
    assert "the think subagent uses only the user report plus the current system map" in content
    assert "primary suspected loop" in content
    assert "alternative cause candidates" in content
    assert "recommended first probe" in content
    assert "transition memo" in content
    assert "automatically continue into evidence investigation" in content
    assert "skip the observer framing stage" not in content
    assert "hard gate" in content
    assert "think subagent" in content
    assert "observer_framing_completed" in content
    assert "no source-code reads, test reads, log reads, or repro commands are allowed" in content
    assert "compressed framing still requires the full observer framing section" in content
    assert "you are not the default evidence worker for every lane" in content
    assert "route, integrate, and decide rather than manually performing every lane sequentially" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "learning start --command debug --format json" in content
    assert "capture-learning --command debug" in content or "learning capture --command debug" in content
    assert "project-map hard gate" in content
    assert "must pass an atlas gate before" in content
    assert "read `project-handbook.md`" in content
    assert "atlas.entry" in content
    assert "atlas.index.status" in content
    assert "atlas.index.atlas" in content
    assert "if the active session is `awaiting_human_verify`" in content
    assert "start a linked follow-up session" in content
    assert "record the parent/child relationship" in content
    assert "return to the parent session to finish the original human verification" in content
    assert "same_issue" in content
    assert "derived_issue" in content
    assert "unrelated_issue" in content
    assert "full framing: at least 3 candidates" in content
    assert "compressed framing: at least 2 candidates" in content
    assert "contrarian candidate" in content
    assert "project-map freshness helper" in content
    assert "freshness is `missing` or `stale`" in content
    assert "freshness is `possibly_stale`" in content
    assert "must_refresh_topics" in content
    assert "review_topics" in content
    assert "before observer framing moves into reproduction, logs, tests, or source-code" in content
    assert "truth ownership" in content
    assert "read whichever of `architecture.md`, `workflows.md`, `integrations.md`, `testing.md`, and `operations.md` map to the failing area" in content
    assert "if the handbook navigation system is missing" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before root-cause analysis continues" in content
    assert "task-relevant coverage is insufficient" in content
    assert "ownership or placement guidance" in content
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in content
    assert "capability-aware investigation" in content
    assert "find truth ownership before chasing symptoms" in content
    assert "control state is not observation state" in content
    assert "debug the loop, not just the point" in content
    assert "escalate diagnostics when the loop is still ambiguous" in content
    assert "execution_model: subagent-mandatory" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "one-subagent" in content
    assert "parallel-subagents" in content
    assert "native-subagents" in content
    assert "dispatch that single subagent only when the leader has already recorded enough context, probe intent, and evidence expectations to preserve quality" in content
    assert 'choose_subagent_dispatch(command_name="debug"' in content
    assert "leader-led" in content
    assert "debug file" in content
    assert "evidence-gathering" in content or "evidence-gathering tasks" in content
    assert "existing logs" in content
    assert "logs are a first-class evidence source" in content
    assert "append it to `evidence` with `source_type: log`" in content
    assert "observability as insufficient" in content
    assert "diagnostic logging" in content or "instrumentation" in content
    assert "truth ownership map" in content
    assert "control state" in content
    assert "observation state" in content
    assert "closed loop" in content
    assert "execution intent" in content
    assert "success evidence" in content
    assert "decisive signals" in content
    assert "alternative_hypotheses_considered" in content
    assert "alternative_hypotheses_ruled_out" in content
    assert "investigation contract" in content
    assert "candidate queue" in content
    assert "related risk targets" in content
    assert "root-cause mode" in content
    assert "second stage must consume the candidate queue" in content
    assert "root_cause_confidence" in content
    assert "fix_scope" in content
    assert "loop_restoration_proof" in content
    assert "owning_layer" in content
    assert "broken_control_state" in content
    assert "failure_mechanism" in content
    assert "loop_break" in content
    assert "decisive_signal" in content
    assert "rejected surface fixes" in content
    assert "if automated verification or human verification fails repeatedly" in content
    assert ".planning/debug/[slug].research.md" in content
    assert "debug-local research checkpoint" in content
    assert "dispatches bounded evidence-gathering subagents" in content
    assert "durable team workflow" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-scan` followed by `/sp-map-build` before moving to `awaiting_human_verify` or `resolved`" in content
    assert "git-baseline freshness in `.specify/project-map/index/status.json` as the truth source" in content
    assert "complete-refresh" in content
    assert "successful-refresh finalizer" in content
    assert "if a full refresh can be completed now" in content
    assert "otherwise use" in content
    assert "manual override/fallback" in content
    assert "highest-signal" in content
    assert "write a failing automated repro test before changing production code" in content
    assert "do not modify production behavior until the red state is proven" in content
    assert "if no reliable automated test surface exists for the failing behavior" in content
    assert "add the missing harness first or route through `/sp-test-scan`" in content
    _assert_tier_roles(content)
    assert "record which plausible causes were considered and which were ruled out" in content
    assert "surface-only" in content
    assert "cannot satisfy the debug contract" in content
    assert "loop restoration proof" in content
    assert "optional expanded observer" in content
    assert "recommend enabling expanded observer" in content
    assert "user can agree or decline" in content or "user can decline" in content
    assert "phenomenon_only" in content
    assert "log investigation plan" in content
    assert "logs are a first-class evidence source" in content
    assert "existing logs" in content
    assert "do not enter fixing" in content or "cannot directly enter fixing" in content


def test_debug_template_uses_stage_and_protocol_structure() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "## role" in content
    assert "## operating principles" in content
    assert "## session lifecycle" in content
    assert "## investigation protocol" in content
    assert "stage 1: observer framing" in content
    assert "stage 2: transition memo" in content
    assert "observer gate" in content
    assert "stage 3: reproduction gate" in content
    assert "stage 4: log review" in content
    assert "required framing before hypothesis" in content
    assert "stage 5: observability assessment" in content
    assert "stage 6: hypothesis formation" in content
    assert "stage 7: experiment loop" in content
    assert "stage 8: root cause confirmation" in content
    assert "## fix and verify protocol" in content
    assert "## checkpoint protocol" in content


def test_debug_template_keeps_shared_guidance_integration_neutral() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "spawn_agent" not in content
    assert "wait_agent" not in content
    assert "close_agent" not in content
    assert "specify team" not in content


def test_debug_thinker_template_documents_expanded_observer_runtime_log_outputs() -> None:
    content = read_template("templates/worker-prompts/debug-thinker.md").lower()

    assert "expanded observer" in content
    assert "expanded_observer:" in content
    assert "dimension_scan" in content
    assert "candidate_board" in content
    assert "top_candidates" in content
    assert "log investigation plan" in content
    assert "existing_log_targets" in content
    assert "candidate_signal_map" in content
    assert "log_sufficiency_judgment" in content
    assert "missing_observability" in content
    assert "instrumentation_targets" in content
    assert "instrumentation_style" in content
    assert "user_request_packet" in content
    assert "light_scores" in content
    assert "engineering_scores" in content
    assert "likelihood" in content
    assert "impact_radius" in content
    assert "falsifiability" in content
    assert "log_observability" in content
    assert "cross_layer_span" in content
    assert "indirect_causality_risk" in content
    assert "evidence_gap" in content
    assert "investigation_cost" in content
    assert "logs are a first-class evidence source" in content
    assert "existing logs" in content
    assert "recommended_log_probe" in content


def test_debug_session_template_captures_control_plane_debugging_fields() -> None:
    content = (PROJECT_ROOT / "templates" / "debug.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "observer_mode:" in content
    assert "observer_framing_completed:" in content
    assert "skip_observer_reason:" in content
    assert "true only after observer framing and transition memo are both written" in content
    assert "## Observer Framing" in content
    assert "## Transition Memo" in content
    assert "primary_suspected_loop:" in content
    assert "alternative_cause_candidates:" in content
    assert "recommended_first_probe:" in content
    assert "## Truth Ownership" in content
    assert "## Suggested Evidence Lanes" in content
    assert "## Control State" in content
    assert "## Observation State" in content
    assert "## Closed Loop" in content
    assert "## Execution Intent" in content
    assert "## Evidence" in content
    assert "## Investigation Contract" in content
    assert "primary_candidate_id:" in content
    assert "candidate_queue:" in content
    assert "related_risk_targets:" in content
    assert "investigation_mode:" in content
    assert "source_type: log" in content
    assert "source_ref:" in content
    assert "summary:" in content
    assert "owning_layer:" in content
    assert "broken_control_state:" in content
    assert "failure_mechanism:" in content
    assert "loop_break:" in content
    assert "decisive_signal:" in content
    assert "validation_results" in content
    assert "decisive_signals" in content
    assert "rejected_surface_fixes" in content
    assert "alternative_hypotheses_considered" in content
    assert "alternative_hypotheses_ruled_out" in content
    assert "root_cause_confidence:" in content
    assert "fix_scope:" in content
    assert "loop_restoration_proof:" in content
    assert "framing_gate_passed:" in content
    assert "waiting_on_child_human_followup:" in content
    assert "human_verification_outcome:" in content
    assert "no source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`" in lowered
