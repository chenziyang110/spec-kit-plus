import pytest
from pydantic_graph import GraphRunContext

import specify_cli.debug.graph as graph_module
from specify_cli.debug.graph import (
    AwaitingHumanNode,
    FixingNode,
    GatheringNode,
    InvestigatingNode,
    ResolvedNode,
    VerifyingNode,
)
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import (
    CausalMapCandidate,
    DebugGraphState,
    DebugStatus,
    LogReadiness,
    ObserverExpansionStatus,
    ProjectRuntimeProfile,
    SymptomShape,
)


def _populate_valid_dual_observer_state(state: DebugGraphState, *, mode: str = "full") -> None:
    state.causal_map_completed = True
    state.contract_generation_completed = True
    state.observer_framing_completed = True
    state.observer_mode = mode
    if mode == "compressed":
        state.skip_observer_reason = "Strong low-level evidence present"
    state.causal_map.symptom_anchor = "Caller output is missing the final token"
    state.causal_map.closed_loop_path = [
        "parse request",
        "compute token bounds",
        "token list update",
        "projection publish",
        "caller output render",
    ]
    state.causal_map.break_edges = ["compute token bounds -> token list update"]
    state.causal_map.bypass_paths = ["stale projection cache serves a truncated token list"]
    state.causal_map.family_coverage = ["truth_owner_logic", "projection_render"]
    state.causal_map.candidates = [
        CausalMapCandidate(
            candidate_id="cand-parser-boundary",
            family="truth_owner_logic",
            candidate="Parser upper bound excludes final token",
            falsifier="Raw parser output already contains final token",
            recommended_first_probe="Run parser repro and inspect raw output",
        ),
        CausalMapCandidate(
            candidate_id="cand-projection-boundary",
            family="projection_render",
            candidate="Projection layer drops final token",
            falsifier="Projection input already lacks final token",
            recommended_first_probe="Compare parser output and rendered output",
        ),
    ]
    if mode != "compressed":
        state.causal_map.family_coverage.append("config_flag_env")
        state.causal_map.candidates.append(
            CausalMapCandidate(
                candidate_id="cand-config-gate",
                family="config_flag_env",
                candidate="Configuration gate trims final token",
                falsifier="Relevant parsing flag is disabled",
                recommended_first_probe="Inspect active parsing flags",
            )
        )
    state.causal_map.adjacent_risk_targets = [
        {
            "target": "projection-boundary",
            "reason": "Nearest-neighbor token family risk",
            "family": "projection_render",
            "scope": "nearest-neighbor",
            "falsifier": "Rendered output always matches projection payload",
        }
    ]

@pytest.mark.asyncio
async def test_gathering_to_investigating():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.expected = "Expected parser output"
    state.symptoms.actual = "Actual parser output"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.observer_framing.primary_suspected_loop = "general"
    state.observer_framing.summary = "General truth-owner issue"
    state.observer_framing.suspected_owning_layer = "parser"
    state.observer_framing.suspected_truth_owner = "parser"
    state.observer_framing.recommended_first_probe = "Check parser boundary"
    state.observer_framing.contrarian_candidate = "Projection layer rewrites parser output"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(
            candidate="Parser upper bound excludes final token",
            failure_shape="truth_owner_logic",
            would_rule_out="Parser output already contains final token",
            recommended_first_probe="Run parser repro and inspect output",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Projection layer drops final token",
            failure_shape="projection_render",
            would_rule_out="Projection input already lacks final token",
            recommended_first_probe="Compare parser output and rendered output",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Configuration gate trims final token",
            failure_shape="config_flag_env",
            would_rule_out="Relevant parsing flag is disabled",
            recommended_first_probe="Inspect active parsing flags",
        ),
    ]
    state.transition_memo.first_candidate_to_test = "Verify queue transitions"
    state.transition_memo.why_first = "Best matches the current evidence."
    state.transition_memo.evidence_unlock = ["reproduction", "code"]
    state.investigation_contract.primary_candidate_id = "cand-parser-boundary"
    state.investigation_contract.candidate_queue = [
        {
            "candidate_id": "cand-parser-boundary",
            "candidate": "Parser upper bound excludes final token",
            "family": "truth_owner_logic",
            "status": "pending",
        },
        {
            "candidate_id": "cand-projection-boundary",
            "candidate": "Projection layer drops final token",
            "family": "projection_render",
            "status": "pending",
        },
        {
            "candidate_id": "cand-config-gate",
            "candidate": "Configuration gate trims final token",
            "family": "config_flag_env",
            "status": "pending",
        },
    ]
    state.transition_memo.first_candidate_to_test = "cand-parser-boundary"
    ctx = GraphRunContext(state=state, deps=None)
    node = GatheringNode()

    result = await node.run(ctx)
    assert isinstance(result, InvestigatingNode)
    assert state.status == DebugStatus.GATHERING
    assert state.observer_framing_completed is True
    assert state.observer_mode == "full"
    assert state.observer_framing.primary_suspected_loop is not None
    assert state.transition_memo.first_candidate_to_test is not None


@pytest.mark.asyncio
async def test_gathering_node_uses_compressed_observer_framing_for_strong_low_level_evidence():
    state = DebugGraphState(trigger="Traceback in parser.py line 42", slug="test-slug")
    state.symptoms.expected = "Expected parser output"
    state.symptoms.actual = "Actual parser output"
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state, mode="compressed")
    state.observer_framing.summary = "Parser boundary issue"
    state.observer_framing.primary_suspected_loop = "general"
    state.observer_framing.suspected_owning_layer = "parser"
    state.observer_framing.suspected_truth_owner = "parser"
    state.observer_framing.recommended_first_probe = "Verify queue transitions"
    state.observer_framing.contrarian_candidate = "Projection layer rewrites parser output"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(
            candidate="Parser upper bound excludes final token",
            failure_shape="truth_owner_logic",
            would_rule_out="Parser output already contains final token",
            recommended_first_probe="Run parser repro and inspect output",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Projection layer drops final token",
            failure_shape="projection_render",
            would_rule_out="Projection input already lacks final token",
            recommended_first_probe="Compare parser output and rendered output",
        ),
    ]
    state.transition_memo.first_candidate_to_test = "Parser upper bound excludes final token"
    state.transition_memo.why_first = "Matches the explicit low-level evidence."
    state.transition_memo.evidence_unlock = ["reproduction", "code"]
    state.investigation_contract.primary_candidate_id = "cand-parser-boundary"
    state.investigation_contract.candidate_queue = [
        {
            "candidate_id": "cand-parser-boundary",
            "candidate": "Parser upper bound excludes final token",
            "family": "truth_owner_logic",
            "status": "pending",
        },
        {
            "candidate_id": "cand-projection-boundary",
            "candidate": "Projection layer drops final token",
            "family": "projection_render",
            "status": "pending",
        },
    ]
    state.transition_memo.first_candidate_to_test = "cand-parser-boundary"
    ctx = GraphRunContext(state=state, deps=None)
    node = GatheringNode()

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert state.observer_framing_completed is True
    assert state.observer_mode == "compressed"
    assert state.skip_observer_reason is not None
    assert state.observer_framing.recommended_first_probe is not None


@pytest.mark.asyncio
async def test_gathering_blocks_when_full_framing_has_fewer_than_three_candidates():
    state = DebugGraphState(trigger="queue stuck", slug="test-slug")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.observer_framing.summary = "Scheduler boundary issue"
    state.observer_framing.primary_suspected_loop = "scheduler-admission"
    state.observer_framing.suspected_owning_layer = "scheduler"
    state.observer_framing.suspected_truth_owner = "scheduler"
    state.observer_framing.recommended_first_probe = "Compare queue and ownership sets"
    state.observer_framing.contrarian_candidate = "UI projection layer is stale"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(candidate="A", failure_shape="truth_owner_logic"),
        graph_module.ObserverCauseCandidate(candidate="B", failure_shape="truth_owner_logic"),
    ]
    state.causal_map.family_coverage = ["truth_owner_logic"]
    state.transition_memo.first_candidate_to_test = "A"
    state.transition_memo.why_first = "best fit"
    state.transition_memo.evidence_unlock = ["reproduction"]
    ctx = GraphRunContext(state=state, deps=None)

    result = await GatheringNode().run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "at least 3" in (state.current_focus.next_action or "")


@pytest.mark.asyncio
async def test_gathering_blocks_when_candidate_diversity_is_fake():
    state = DebugGraphState(trigger="queue stuck", slug="test-slug")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.observer_framing.summary = "Scheduler boundary issue"
    state.observer_framing.primary_suspected_loop = "scheduler-admission"
    state.observer_framing.suspected_owning_layer = "scheduler"
    state.observer_framing.suspected_truth_owner = "scheduler"
    state.observer_framing.recommended_first_probe = "Compare queue and ownership sets"
    state.observer_framing.contrarian_candidate = "Same family paraphrase"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(candidate="A", failure_shape="truth_owner_logic"),
        graph_module.ObserverCauseCandidate(candidate="B", failure_shape="truth_owner_logic"),
        graph_module.ObserverCauseCandidate(candidate="C", failure_shape="truth_owner_logic"),
    ]
    state.causal_map.family_coverage = ["truth_owner_logic", "truth_owner_logic", "truth_owner_logic"]
    state.transition_memo.first_candidate_to_test = "A"
    state.transition_memo.why_first = "best fit"
    state.transition_memo.evidence_unlock = ["reproduction"]
    ctx = GraphRunContext(state=state, deps=None)

    result = await GatheringNode().run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "diversity" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_gathering_blocks_when_transition_candidate_is_missing_from_queue():
    state = DebugGraphState(trigger="queue stuck", slug="test-slug")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.observer_framing.summary = "Scheduler boundary issue"
    state.observer_framing.primary_suspected_loop = "scheduler-admission"
    state.observer_framing.suspected_owning_layer = "scheduler"
    state.observer_framing.suspected_truth_owner = "scheduler"
    state.observer_framing.recommended_first_probe = "Compare queue and ownership sets"
    state.observer_framing.contrarian_candidate = "UI projection layer is stale"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(
            candidate="A",
            failure_shape="truth_owner_logic",
            would_rule_out="authoritative state is already correct",
            recommended_first_probe="inspect authoritative state",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="B",
            failure_shape="projection_render",
            would_rule_out="rendered view matches publish payload",
            recommended_first_probe="compare publish and render",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="C",
            failure_shape="config_flag_env",
            would_rule_out="flag is disabled in repro",
            recommended_first_probe="inspect active flags",
        ),
    ]
    state.transition_memo.first_candidate_to_test = "cand-missing"
    state.transition_memo.why_first = "best fit"
    state.transition_memo.evidence_unlock = ["reproduction"]
    state.investigation_contract.candidate_queue = [
        {"candidate_id": "cand-a", "candidate": "A", "family": "truth_owner_logic"},
        {"candidate_id": "cand-b", "candidate": "B", "family": "projection_render"},
    ]
    ctx = GraphRunContext(state=state, deps=None)

    result = await GatheringNode().run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "first candidate" in (state.current_focus.next_action or "").lower()
    assert "candidate queue" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_gathering_requests_contract_subagent_after_causal_map() -> None:
    state = DebugGraphState(trigger="queue stuck", slug="test-slug")
    state.causal_map_completed = True
    state.causal_map.family_coverage = [
        "truth_owner_logic",
        "cache_snapshot",
        "projection_render",
    ]
    state.causal_map.candidates = [
        CausalMapCandidate(
            candidate_id="cand-slot-ownership",
            family="truth_owner_logic",
            candidate="Scheduler does not clear slot ownership on release",
        )
    ]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert state.contract_subagent_prompt is not None
    assert "contract subagent" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_gathering_classifies_runtime_phenomenon_and_suggests_expanded_observer() -> None:
    state = DebugGraphState(trigger="UI occasionally shows stale order status after retry", slug="runtime-phenomenon")
    state.symptoms.expected = "Order status updates to completed after retry"
    state.symptoms.actual = "UI keeps showing processing with no precise failure location"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.observer_framing.summary = "Cross-layer symptom still needs runtime narrowing"
    state.observer_framing.primary_suspected_loop = "ui-projection"
    state.observer_framing.suspected_owning_layer = "publish/projection boundary"
    state.observer_framing.suspected_truth_owner = "backend order state"
    state.observer_framing.recommended_first_probe = "Correlate browser output with backend publish events"
    state.observer_framing.contrarian_candidate = "Backend truth owner never transitions to completed"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(
            candidate="Projection layer serves stale order state",
            failure_shape="projection_render",
            would_rule_out="Published payload already contains the stale value",
            recommended_first_probe="Compare published payload and rendered state",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Backend publish boundary emits stale status",
            failure_shape="truth_owner_logic",
            would_rule_out="Backend truth owner shows the correct completed status before publish",
            recommended_first_probe="Check backend status transition and publish output",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Retry worker misses refresh event",
            failure_shape="queue_async",
            would_rule_out="Refresh event is present in worker/job traces for the repro window",
            recommended_first_probe="Check retry worker completion and refresh emission logs",
        ),
    ]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert isinstance(result, InvestigatingNode)
    assert state.project_runtime_profile == ProjectRuntimeProfile.FULL_STACK_WEB_APP
    assert state.symptom_shape == SymptomShape.PHENOMENON_ONLY
    assert state.observer_expansion_status == ObserverExpansionStatus.SUGGESTED
    assert state.observer_expansion_reason is not None
    assert "runtime" in state.observer_expansion_reason


@pytest.mark.asyncio
async def test_gathering_suggests_expanded_observer_for_runtime_cross_layer_case() -> None:
    state = DebugGraphState(trigger="Status badge stays stale while worker marks job complete", slug="runtime-cross-layer")
    state.symptoms.expected = "Completed jobs disappear from the queue badge"
    state.symptoms.actual = "Worker reports completion but UI badge still shows the job"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.observer_framing.summary = "Symptom appears in UI but truth owner may live in worker/backend boundaries"
    state.observer_framing.primary_suspected_loop = "scheduler-admission"
    state.observer_framing.suspected_owning_layer = "queue worker publish boundary"
    state.observer_framing.suspected_truth_owner = "queue worker"
    state.observer_framing.recommended_first_probe = "Compare worker completion and badge refresh boundaries"
    state.observer_framing.contrarian_candidate = "UI badge polls the wrong projection"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(
            candidate="Worker completion never emits queue-clear event",
            failure_shape="truth_owner_logic",
            would_rule_out="Worker completion traces show the queue-clear event emitted reliably",
            recommended_first_probe="Inspect worker completion and publish traces",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Projection refresh misses the queue-clear event",
            failure_shape="projection_render",
            would_rule_out="Projection refresh logs show the clear event arriving and being applied",
            recommended_first_probe="Compare worker publish trace and projection refresh trace",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Queue badge reads a stale cache layer",
            failure_shape="cache_snapshot",
            would_rule_out="Badge projection and cache both refresh to the new state in the repro window",
            recommended_first_probe="Compare cache invalidation and badge read paths",
        ),
    ]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert isinstance(result, InvestigatingNode)
    assert state.project_runtime_profile == ProjectRuntimeProfile.WORKER_QUEUE_CRON
    assert state.observer_expansion_status == ObserverExpansionStatus.SUGGESTED
    assert state.observer_expansion_reason == "runtime_cross_layer_symptom"


@pytest.mark.asyncio
async def test_gathering_suggests_expanded_observer_after_two_failed_rounds() -> None:
    state = DebugGraphState(trigger="Intermittent runtime state drift after retry", slug="runtime-not-converging")
    state.symptoms.expected = "Retry restores consistent state"
    state.symptoms.actual = "State remains inconsistent after two attempted investigation rounds"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.project_runtime_profile = ProjectRuntimeProfile.FULL_STACK_WEB_APP
    state.current_focus.hypothesis = "Projection cache is stale"
    state.eliminated = [
        {"hypothesis": "Projection cache is stale", "evidence": "Cache refresh fired but symptom persisted"},
        {"hypothesis": "Retry worker never completed", "evidence": "Worker completion event is present"},
    ]
    state.observer_framing.summary = "Two runtime probes have not converged on a single owning-layer cause"
    state.observer_framing.primary_suspected_loop = "cache-snapshot"
    state.observer_framing.suspected_owning_layer = "publish/cache boundary"
    state.observer_framing.suspected_truth_owner = "backend retry state"
    state.observer_framing.recommended_first_probe = "Expand candidate surface before another local probe"
    state.observer_framing.contrarian_candidate = "Retry never updates the truth owner"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(candidate="Projection cache is stale", failure_shape="cache_snapshot", would_rule_out="Cache state matches backend truth owner", recommended_first_probe="Compare cache and backend state"),
        graph_module.ObserverCauseCandidate(candidate="Retry never updates the truth owner", failure_shape="truth_owner_logic", would_rule_out="Backend truth owner update is recorded", recommended_first_probe="Inspect retry state transitions"),
        graph_module.ObserverCauseCandidate(candidate="Async refresh misses retry completion", failure_shape="queue_async", would_rule_out="Async refresh executes after retry completion", recommended_first_probe="Inspect async refresh flow"),
    ]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert isinstance(result, InvestigatingNode)
    assert state.observer_expansion_status == ObserverExpansionStatus.SUGGESTED
    assert state.observer_expansion_reason == "hypothesis_not_converging"


@pytest.mark.asyncio
async def test_gathering_leaves_non_runtime_session_outside_runtime_expansion_scope() -> None:
    state = DebugGraphState(trigger="Refactor parser helper for readability", slug="non-runtime")
    state.symptoms.expected = "Helper returns the same computed token list"
    state.symptoms.actual = "Refactor task only; no runtime repro or symptom investigation"
    state.symptoms.errors = "mypy reports incompatible return type"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.observer_framing.summary = "Static typing issue with no runtime evidence surface"
    state.observer_framing.primary_suspected_loop = "general"
    state.observer_framing.suspected_owning_layer = "parser helper"
    state.observer_framing.suspected_truth_owner = "parser helper"
    state.observer_framing.recommended_first_probe = "Fix the type mismatch directly"
    state.observer_framing.contrarian_candidate = "Signature drift in the caller"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(candidate="Parser helper returns the wrong type", failure_shape="truth_owner_logic", would_rule_out="Helper return type matches the annotation", recommended_first_probe="Check helper signature"),
        graph_module.ObserverCauseCandidate(candidate="Caller expects the wrong type alias", failure_shape="projection_render", would_rule_out="Caller type alias matches helper output", recommended_first_probe="Check caller typing"),
        graph_module.ObserverCauseCandidate(candidate="Shared type alias drifted", failure_shape="config_flag_env", would_rule_out="Shared alias still matches the contract", recommended_first_probe="Inspect shared type alias"),
    ]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert isinstance(result, InvestigatingNode)
    assert state.project_runtime_profile is None
    assert state.observer_expansion_status == ObserverExpansionStatus.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_gathering_keeps_generic_request_command_words_out_of_runtime_scope() -> None:
    state = DebugGraphState(
        trigger="Refactor request command builder for the database response fixture script",
        slug="non-runtime-generic-runtime-words",
    )
    state.symptoms.expected = "Refactor preserves the same helper output"
    state.symptoms.actual = "This is a static cleanup task touching request helper naming and database fixture script naming only"
    state.symptoms.errors = "ruff reports import ordering changes only"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.observer_framing.summary = "Static refactor task with generic nouns but no runtime evidence surface"
    state.observer_framing.primary_suspected_loop = "general"
    state.observer_framing.suspected_owning_layer = "helper naming and module structure"
    state.observer_framing.suspected_truth_owner = "helper naming and module structure"
    state.observer_framing.recommended_first_probe = "Apply the refactor without changing behavior"
    state.observer_framing.contrarian_candidate = "Shared helper signature drift"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(
            candidate="Helper refactor changes import shape",
            failure_shape="truth_owner_logic",
            would_rule_out="Import graph stays identical after the rename",
            recommended_first_probe="Inspect helper imports",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Shared helper signature drift",
            failure_shape="projection_render",
            would_rule_out="Shared signature remains unchanged",
            recommended_first_probe="Inspect helper signature",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Formatting-only edits are incomplete",
            failure_shape="config_flag_env",
            would_rule_out="Formatter and linter report clean output",
            recommended_first_probe="Run formatter and linter",
        ),
    ]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert isinstance(result, InvestigatingNode)
    assert state.project_runtime_profile is None
    assert state.observer_expansion_status == ObserverExpansionStatus.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_gathering_ignores_runtime_like_feature_slug_for_static_task() -> None:
    state = DebugGraphState(trigger="Rename helper constants for clarity", slug="non-runtime-feature-slug")
    state.context.feature_id = "rename-worker-queue-helpers"
    state.symptoms.expected = "Static rename keeps helper outputs unchanged"
    state.symptoms.actual = "This is a naming cleanup with no runtime repro or production symptom"
    state.symptoms.errors = "ruff reports unused import cleanup only"
    state.symptoms.reproduction_verified = True
    _populate_valid_dual_observer_state(state)
    state.observer_framing.summary = "Static rename task; the feature slug happens to contain unrelated infrastructure words"
    state.observer_framing.primary_suspected_loop = "general"
    state.observer_framing.suspected_owning_layer = "helper naming and module structure"
    state.observer_framing.suspected_truth_owner = "helper naming and module structure"
    state.observer_framing.recommended_first_probe = "Apply the rename without changing behavior"
    state.observer_framing.contrarian_candidate = "Shared helper references are incomplete"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(
            candidate="Rename misses one helper import",
            failure_shape="truth_owner_logic",
            would_rule_out="All helper imports are updated consistently",
            recommended_first_probe="Inspect helper imports",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Shared helper constant references are incomplete",
            failure_shape="projection_render",
            would_rule_out="All helper references use the renamed constant",
            recommended_first_probe="Inspect helper references",
        ),
        graph_module.ObserverCauseCandidate(
            candidate="Formatter-only cleanup is incomplete",
            failure_shape="config_flag_env",
            would_rule_out="Formatter and linter report clean output",
            recommended_first_probe="Run formatter and linter",
        ),
    ]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert isinstance(result, InvestigatingNode)
    assert state.project_runtime_profile is None
    assert state.observer_expansion_status == ObserverExpansionStatus.NOT_APPLICABLE

@pytest.mark.asyncio
async def test_investigating_to_fixing():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.log_readiness = LogReadiness.SUFFICIENT_EXISTING_LOGS
    state.resolution.root_cause = {
        "summary": "Scheduler kept stale running ownership after slot release",
        "owning_layer": "scheduler",
        "broken_control_state": "running set",
        "failure_mechanism": "released slot did not clear admitted ownership before promotion",
        "loop_break": "resource allocation -> state transition",
        "decisive_signal": "running set stayed non-empty while promotion should have occurred",
    }
    state.truth_ownership = [{"layer": "scheduler", "owns": "running set"}]
    state.control_state = ["running_set"]
    state.observation_state = ["task_table"]
    state.closed_loop.input_event = "task completion"
    state.closed_loop.control_decision = "promote next queued task"
    state.closed_loop.resource_allocation = "release and reassign slot"
    state.closed_loop.state_transition = "waiting task becomes admitted"
    state.closed_loop.external_observation = "UI shows running"
    state.closed_loop.break_point = "promotion stage"
    state.resolution.decisive_signals = ["running_set empty while task_table still showed running"]
    state.resolution.alternative_hypotheses_considered = [
        "Scheduler kept stale running ownership after slot release",
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.investigation_contract.primary_candidate_id = "cand-scheduler-ownership"
    state.investigation_contract.candidate_queue = [
        {
            "candidate_id": "cand-scheduler-ownership",
            "candidate": "Scheduler kept stale running ownership after slot release",
            "family": "truth_owner_logic",
            "status": "confirmed",
        },
        {
            "candidate_id": "cand-resource-counters",
            "candidate": "Resource counters or slot accounting are stale",
            "family": "projection_render",
            "status": "ruled_out",
        },
    ]
    state.investigation_contract.related_risk_targets = [
        {
            "target": "promotion-boundary",
            "reason": "Nearest-neighbor risk for scheduler promotion",
            "scope": "nearest-neighbor",
            "status": "checked",
        }
    ]
    ctx = GraphRunContext(state=state, deps=None)
    node = InvestigatingNode()
    
    result = await node.run(ctx)
    assert isinstance(result, FixingNode)
    assert state.status == DebugStatus.INVESTIGATING

@pytest.mark.asyncio
async def test_fixing_to_verifying():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.log_readiness = LogReadiness.SUFFICIENT_EXISTING_LOGS
    state.resolution.root_cause = {
        "summary": "Scheduler kept stale running ownership after slot release",
        "owning_layer": "scheduler",
        "broken_control_state": "running set",
        "failure_mechanism": "released slot did not clear admitted ownership before promotion",
        "loop_break": "resource allocation -> state transition",
        "decisive_signal": "running set stayed non-empty while promotion should have occurred",
    }
    state.truth_ownership = [{"layer": "scheduler", "owns": "running set"}]
    state.control_state = ["running_set"]
    state.observation_state = ["task_table"]
    state.closed_loop.input_event = "task completion"
    state.closed_loop.control_decision = "promote next queued task"
    state.closed_loop.resource_allocation = "release and reassign slot"
    state.closed_loop.state_transition = "waiting task becomes admitted"
    state.closed_loop.external_observation = "UI shows running"
    state.closed_loop.break_point = "promotion stage"
    state.resolution.decisive_signals = ["running_set empty while task_table still showed running"]
    state.resolution.alternative_hypotheses_considered = [
        "Scheduler kept stale running ownership after slot release",
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.alternative_hypotheses_ruled_out = [
        "Resource counters or slot accounting are stale",
    ]
    state.resolution.root_cause_confidence = "confirmed"
    state.resolution.fix = "Applied fix"
    state.resolution.fix_scope = "truth-owner"
    ctx = GraphRunContext(state=state, deps=None)
    node = FixingNode()
    
    result = await node.run(ctx)
    assert isinstance(result, VerifyingNode)
    assert state.status == DebugStatus.FIXING

@pytest.mark.asyncio
async def test_verifying_to_resolved_on_success(monkeypatch):
    seen: list[str] = []

    def fake_run_verification_commands(commands, *, runner=None, stop_on_failure=False):
        seen.extend(commands)
        return [
            graph_module.ValidationResult(command=command, status="passed", output="PASS")
            for command in commands
        ]

    monkeypatch.setattr(graph_module, "run_verification_commands", fake_run_verification_commands)

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph.py"]
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = [
        "Repro now shows the scheduler releases ownership and the UI reflects the promoted task.",
    ]
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()

    result = await node.run(ctx)
    assert isinstance(result, AwaitingHumanNode)
    assert state.resolution.verification == "success"
    assert seen == ["python tests/repro.py", "pytest tests/test_debug_graph.py"]
    assert [item.command for item in state.resolution.validation_results] == seen
    assert state.status == DebugStatus.VERIFYING


@pytest.mark.asyncio
async def test_awaiting_human_node_resolves_when_user_already_confirmed():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.status = DebugStatus.AWAITING_HUMAN
    state.resolution.human_verification_outcome = "passed"
    ctx = GraphRunContext(state=state, deps=None)

    result = await AwaitingHumanNode().run(ctx)

    assert isinstance(result, ResolvedNode)

@pytest.mark.asyncio
async def test_verifying_to_investigating_on_failure(monkeypatch):
    calls = []

    def mock_run(_cmd: str) -> str:
        calls.append(_cmd)
        return "PASS" if len(calls) == 1 else "FAIL"

    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph.py"]
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()

    result = await node.run(ctx)
    assert isinstance(result, InvestigatingNode)
    assert state.resolution.verification == "failed"
    assert state.resolution.fail_count == 1
    assert state.status == DebugStatus.VERIFYING


@pytest.mark.asyncio
async def test_investigating_blocks_fixing_without_control_plane_framing():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.resolution.root_cause = {"summary": "Found it"}
    ctx = GraphRunContext(state=state, deps=None)
    node = InvestigatingNode()

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "fixing is blocked" in (state.current_focus.next_action or "").lower()
    assert "truth ownership map" in (state.current_focus.next_action or "").lower()
    assert "- [ ] truth ownership map" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_investigating_blocks_fixing_without_alternative_hypothesis_coverage():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.observer_framing.alternative_cause_candidates = [
        {"candidate": "Scheduler kept stale running ownership after slot release"},
        {"candidate": "Resource counters or slot accounting are stale"},
    ]
    state.resolution.root_cause = {
        "summary": "Scheduler kept stale running ownership after slot release",
        "owning_layer": "scheduler",
        "broken_control_state": "running set",
        "failure_mechanism": "released slot did not clear admitted ownership before promotion",
        "loop_break": "resource allocation -> state transition",
        "decisive_signal": "running set stayed non-empty while promotion should have occurred",
    }
    state.truth_ownership = [{"layer": "scheduler", "owns": "running set"}]
    state.control_state = ["running_set"]
    state.observation_state = ["task_table"]
    state.closed_loop.input_event = "task completion"
    state.closed_loop.control_decision = "promote next queued task"
    state.closed_loop.resource_allocation = "release and reassign slot"
    state.closed_loop.state_transition = "waiting task becomes admitted"
    state.closed_loop.external_observation = "UI shows running"
    state.closed_loop.break_point = "promotion stage"
    state.resolution.decisive_signals = ["running_set empty while task_table still showed running"]
    state.resolution.root_cause_confidence = "confirmed"
    ctx = GraphRunContext(state=state, deps=None)
    node = InvestigatingNode()

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "alternative hypothesis" in (state.current_focus.next_action or "").lower()
    assert "ruled-out" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_verifying_second_failure_requests_diagnostic_escalation(monkeypatch):
    calls = []

    def mock_run(_cmd: str) -> str:
        calls.append(_cmd)
        return "FAIL"

    monkeypatch.setattr(graph_module, "run_command", mock_run)

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Normalize UI status"
    state.resolution.fail_count = 1
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert state.resolution.fail_count == 2
    assert "decisive instrumentation" in (state.current_focus.next_action or "").lower()
    assert "control plane" in (state.current_focus.next_action or "").lower()
    assert "detected profile: ui projection" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture ownership sets at the decision layer" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture source-of-truth state at publish time" in (state.current_focus.next_action or "").lower()
    assert "Normalize UI status" in state.resolution.rejected_surface_fixes


@pytest.mark.asyncio
async def test_verifying_second_failure_writes_research_checkpoint_when_persistence_available(monkeypatch, tmp_path):
    monkeypatch.setattr(graph_module, "run_command", lambda _cmd: "FAIL")

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Normalize UI status"
    state.resolution.fail_count = 1
    handler = MarkdownPersistenceHandler(tmp_path)
    ctx = GraphRunContext(state=state, deps=handler)
    node = VerifyingNode()

    result = await node.run(ctx)

    research_path = tmp_path / "test-slug.research.md"
    assert isinstance(result, InvestigatingNode)
    assert research_path.exists()
    assert "Debug Research: test-slug" in research_path.read_text(encoding="utf-8")
    assert "review" in (state.current_focus.next_action or "").lower()
    assert "research" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_scheduler_admission_profile_gets_targeted_diagnostic_checklist(monkeypatch):
    monkeypatch.setattr(graph_module, "run_command", lambda _cmd: "FAIL")

    state = DebugGraphState(trigger="scheduler queue stuck after slot release", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Normalize queue status"
    state.resolution.fail_count = 1
    state.control_state = ["running set", "activeCount"]
    ctx = GraphRunContext(state=state, deps=None)
    node = VerifyingNode()

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert "detected profile: scheduler/admission" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture queue contents before and after the decision point" in (state.current_focus.next_action or "").lower()
    assert "- [ ] capture running/admitted ownership sets before and after slot release" in (state.current_focus.next_action or "").lower()
