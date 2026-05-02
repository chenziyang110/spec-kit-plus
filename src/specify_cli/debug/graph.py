from pathlib import Path
from typing import Union
from pydantic_graph import BaseNode, Graph, GraphRunContext, End
from .schema import (
    DebugGraphState,
    DebugStatus,
    EliminatedEntry,
    EvidenceEntry,
    ObserverCauseCandidate,
    SuggestedEvidenceLane,
    ValidationCheck,
)
from .persistence import MarkdownPersistenceHandler, build_handoff_report
from .context import ContextLoader
from .utils import run_command, edit_file, read_file
from .think_agent import build_think_subagent_prompt
import functools
from specify_cli.verification import (
    ValidationResult as SharedValidationResult,
    run_verification_commands,
    verification_passed,
)

__all__ = ["run_command", "edit_file", "read_file"]
ValidationResult = SharedValidationResult


def _await_input(state: DebugGraphState, message: str) -> End:
    state.current_focus.next_action = message
    return End("Awaiting more debugging input")


def _debug_profile(state: DebugGraphState) -> str:
    haystacks = [
        state.trigger,
        state.symptoms.expected,
        state.symptoms.actual,
        state.symptoms.errors,
        state.current_focus.hypothesis,
        state.current_focus.next_action,
        state.resolution.fix,
        state.resolution.root_cause.display_text() if state.resolution.root_cause else None,
        state.resolution.root_cause.owning_layer if state.resolution.root_cause else None,
        state.resolution.root_cause.broken_control_state if state.resolution.root_cause else None,
        " ".join(state.control_state),
        " ".join(state.observation_state),
    ]
    text = " ".join(part.lower() for part in haystacks if part)

    if any(token in text for token in ("scheduler", "slot", "queue", "admission", "running set", "activecount", "waitingqueue", "runningorder")):
        return "scheduler-admission"
    if any(token in text for token in ("cache", "snapshot", "stale", "polling", "task table", "event stream", "projection drift")):
        return "cache-snapshot"
    if any(token in text for token in ("ui", "display", "render", "status sync", "projection", "view model", "frontend")):
        return "ui-projection"
    return "general"


def _refresh_diagnostic_profile(state: DebugGraphState) -> None:
    state.diagnostic_profile = _debug_profile(state)


def _build_suggested_evidence_lanes(state: DebugGraphState) -> list[SuggestedEvidenceLane]:
    profile = _debug_profile(state)
    if profile == "scheduler-admission":
        return [
            SuggestedEvidenceLane(
                name="queue-snapshot",
                focus="waiting and promotion flow",
                evidence_to_collect=[
                    "queue contents before the decision",
                    "queue contents after the decision",
                    "promotion ordering evidence",
                ],
                join_goal="Decide whether queue state and promotion order are consistent.",
            ),
            SuggestedEvidenceLane(
                name="ownership-set-trace",
                focus="running or admitted ownership",
                evidence_to_collect=[
                    "running/admitted set before slot release",
                    "running/admitted set after slot release",
                    "ownership handoff trace",
                ],
                join_goal="Decide whether the owning scheduler state released and reassigned correctly.",
            ),
            SuggestedEvidenceLane(
                name="resource-counter-trace",
                focus="slot accounting",
                evidence_to_collect=[
                    "active slot counters",
                    "admission counters",
                    "counter changes across the decision boundary",
                ],
                join_goal="Decide whether resource accounting matches the scheduler sets.",
            ),
        ]
    if profile == "cache-snapshot":
        return [
            SuggestedEvidenceLane(
                name="authoritative-state-trace",
                focus="control-plane truth",
                evidence_to_collect=[
                    "authoritative control state",
                    "time of control-state mutation",
                ],
                join_goal="Establish the ground-truth state before comparing projections.",
            ),
            SuggestedEvidenceLane(
                name="snapshot-drift-trace",
                focus="cache or snapshot divergence",
                evidence_to_collect=[
                    "cached or snapshot state",
                    "snapshot write timestamp",
                    "drift from authoritative state",
                ],
                join_goal="Decide whether stale snapshot data exists and where it diverged.",
            ),
            SuggestedEvidenceLane(
                name="refresh-path-trace",
                focus="invalidation and refresh",
                evidence_to_collect=[
                    "cache invalidation events",
                    "refresh-path trace",
                    "missed refresh conditions",
                ],
                join_goal="Decide whether the system failed to invalidate or refresh on time.",
            ),
        ]
    if profile == "ui-projection":
        return [
            SuggestedEvidenceLane(
                name="source-truth-trace",
                focus="publish-time source state",
                evidence_to_collect=[
                    "source-of-truth state at publish time",
                    "control-layer state used to publish",
                ],
                join_goal="Establish whether the owning layer was already wrong before projection.",
            ),
            SuggestedEvidenceLane(
                name="projection-transform-trace",
                focus="transform and publish boundary",
                evidence_to_collect=[
                    "transformed view-model state",
                    "publish/subscription boundary trace",
                    "projection mapping inputs and outputs",
                ],
                join_goal="Decide whether the bug was introduced during projection.",
            ),
            SuggestedEvidenceLane(
                name="render-output-trace",
                focus="observed UI output",
                evidence_to_collect=[
                    "rendered or polled output",
                    "timing of UI observation",
                    "difference from published state",
                ],
                join_goal="Decide whether the final observation drifted after publish.",
            ),
        ]
    return [
        SuggestedEvidenceLane(
            name="control-state-trace",
            focus="owning decision layer",
            evidence_to_collect=[
                "owning decision-layer state",
                "decision inputs and outputs",
            ],
            join_goal="Establish the control-plane truth.",
        ),
        SuggestedEvidenceLane(
            name="observation-trace",
            focus="observable projection",
            evidence_to_collect=[
                "external projection state",
                "timing of observation",
            ],
            join_goal="Establish what the user-facing layer observed.",
        ),
        SuggestedEvidenceLane(
            name="boundary-trace",
            focus="control-to-observation boundary",
            evidence_to_collect=[
                "handoff trace between control state and projection",
                "where the boundary may have broken",
            ],
            join_goal="Decide where control truth diverged from observation.",
        ),
    ]


def _refresh_lane_plan(state: DebugGraphState) -> None:
    state.suggested_evidence_lanes = _build_suggested_evidence_lanes(state)


def _strong_low_level_evidence_present(state: DebugGraphState) -> tuple[bool, str | None]:
    haystacks = [
        state.trigger,
        state.symptoms.errors,
        state.symptoms.reproduction_command,
        state.current_focus.next_action,
    ]
    text = " ".join(part.lower() for part in haystacks if part)
    if state.symptoms.reproduction_command:
        return True, "user supplied an explicit reproduction command"
    if any(token in text for token in ("traceback", "stack trace", "panic:", "segfault", ".py:", "exception", "line ")):
        return True, "user supplied strong low-level failure evidence"
    return False, None


def _observer_candidates_for_profile(profile: str) -> list[ObserverCauseCandidate]:
    if profile == "scheduler-admission":
        return [
            ObserverCauseCandidate(
                candidate="scheduler ownership state never released correctly",
                why_it_fits="The symptom pattern matches queues, slots, or running/admitted state drifting out of sync.",
                map_evidence="Scheduler/admission problems usually live in the truth-owning control plane rather than in UI projections.",
                would_rule_out="A verified scheduler state transition showing ownership releases and reassignments are correct.",
            ),
            ObserverCauseCandidate(
                candidate="resource counters or slot accounting are stale",
                why_it_fits="Admission bugs often come from counters disagreeing with ownership sets.",
                map_evidence="Resource allocation sits in the control-state path of the closed loop.",
                would_rule_out="Counter traces that stay consistent with queue and running-set changes.",
            ),
            ObserverCauseCandidate(
                candidate="promotion handoff between waiting and running is broken",
                why_it_fits="The user-visible symptom can occur when the queue changes but the next runnable task never crosses the boundary.",
                map_evidence="Promotion is the boundary where control decisions become state transitions.",
                would_rule_out="A clean promotion trace from waiting to running with matching external observation.",
            ),
        ]
    if profile == "cache-snapshot":
        return [
            ObserverCauseCandidate(
                candidate="authoritative state is correct but snapshot invalidation is stale",
                why_it_fits="Users often report old state persisting when snapshots are not refreshed after control-plane changes.",
                map_evidence="Snapshot/cache layers are observation layers, not truth owners.",
                would_rule_out="Evidence that the authoritative state itself is wrong before any snapshot is written.",
            ),
            ObserverCauseCandidate(
                candidate="snapshot refresh path is not triggered on the relevant control-plane event",
                why_it_fits="The symptom fits a valid state transition with no matching refresh boundary call.",
                map_evidence="Refresh paths sit at the boundary between control state and observation state.",
                would_rule_out="A verified refresh trace showing the event reliably triggers cache refresh.",
            ),
            ObserverCauseCandidate(
                candidate="observer is reading the wrong projection layer",
                why_it_fits="Some stale-state reports come from a secondary table, cache, or event stream rather than the primary snapshot.",
                map_evidence="Project maps often expose multiple observation layers for the same underlying state.",
                would_rule_out="Evidence that every projection layer agrees and still shows the wrong value.",
            ),
        ]
    if profile == "ui-projection":
        return [
            ObserverCauseCandidate(
                candidate="projection transform is wrong even though source-of-truth is healthy",
                why_it_fits="UI-only symptoms often emerge when source state is correct but the transformation layer drops or rewrites fields.",
                map_evidence="Projection is an observation concern, not usually the primary truth owner.",
                would_rule_out="Evidence that the source-of-truth state is already wrong before transformation.",
            ),
            ObserverCauseCandidate(
                candidate="published source state is stale before the UI receives it",
                why_it_fits="The screen can be correct relative to what it received, while the publish boundary already carried stale data.",
                map_evidence="UI bugs often sit at the publish boundary rather than in rendering itself.",
                would_rule_out="A publish trace showing correct source state entering the projection layer.",
            ),
            ObserverCauseCandidate(
                candidate="render/polling timing causes a stale observation window",
                why_it_fits="Transient stale output often comes from observation timing rather than stable state corruption.",
                map_evidence="Polling and render timing live in observation state, not control state.",
                would_rule_out="Evidence that the wrong value persists even after a stable post-update observation window.",
            ),
        ]
    return [
        ObserverCauseCandidate(
            candidate="owning layer truth is wrong",
            why_it_fits="The user-visible symptom may be a direct effect of a broken control-plane decision.",
            map_evidence="Truth ownership should be established before blaming projections or caches.",
            would_rule_out="Evidence that the owning layer state is correct and the bug only appears downstream.",
        ),
        ObserverCauseCandidate(
            candidate="boundary contract between control state and observation is broken",
            why_it_fits="Many bugs come from a correct decision never being published or translated correctly.",
            map_evidence="Closed-loop breaks frequently happen at handoff boundaries.",
            would_rule_out="A clean handoff trace with correct downstream observation.",
        ),
        ObserverCauseCandidate(
            candidate="observation layer is stale or reading the wrong source",
            why_it_fits="The user may be seeing the wrong projection even if control state is healthy.",
            map_evidence="Observation layers are allowed to drift unless refresh/invalidation works correctly.",
            would_rule_out="Evidence that all observation layers agree and still reflect a control-plane failure.",
        ),
    ]


# Deprecated: use think subagent via build_think_subagent_prompt() instead.
# Kept for backward compatibility and testing.
def _populate_observer_framing(state: DebugGraphState) -> None:
    if state.observer_framing_completed:
        return

    profile = _debug_profile(state)
    compressed, reason = _strong_low_level_evidence_present(state)
    state.observer_mode = "compressed" if compressed else "full"
    state.skip_observer_reason = reason if compressed else None

    profile_summary = {
        "scheduler-admission": "The issue most likely lives in a scheduler/admission control loop rather than only in a projection layer.",
        "cache-snapshot": "The issue most likely involves stale observation state, snapshot invalidation, or cache refresh rather than immediate business logic alone.",
        "ui-projection": "The issue most likely sits in a UI/projection boundary, publish step, or render/poll observation layer.",
        "general": "The issue needs an outsider pass to identify the likely truth owner and failure boundary before evidence collection begins.",
    }[profile]

    first_probe = {
        "scheduler-admission": "Verify queue, slot, and ownership-set transitions before reading implementation details.",
        "cache-snapshot": "Compare authoritative state versus snapshot/refresh boundaries before chasing code-level fixes.",
        "ui-projection": "Check whether the source-of-truth state is already wrong before blaming the render layer.",
        "general": "Start by validating the owning layer and the first control-to-observation handoff.",
    }[profile]

    state.observer_framing.summary = profile_summary
    state.observer_framing.primary_suspected_loop = profile
    state.observer_framing.suspected_owning_layer = {
        "scheduler-admission": "scheduler/admission control",
        "cache-snapshot": "authoritative state + snapshot boundary",
        "ui-projection": "publish/projection boundary",
        "general": "truth-owning control layer",
    }[profile]
    state.observer_framing.suspected_truth_owner = state.observer_framing.suspected_owning_layer
    state.observer_framing.recommended_first_probe = first_probe
    state.observer_framing.missing_questions = [
        "What exact user-visible symptom persists if we ignore implementation details and only describe the workflow break?",
    ]
    state.observer_framing.alternative_cause_candidates = _observer_candidates_for_profile(profile)

    state.transition_memo.first_candidate_to_test = (
        state.observer_framing.alternative_cause_candidates[0].candidate
        if state.observer_framing.alternative_cause_candidates
        else None
    )
    state.transition_memo.why_first = "It best matches the current outsider framing and offers the narrowest first evidence probe."
    state.transition_memo.evidence_unlock = ["reproduction", "logs", "code", "tests", "instrumentation"]
    state.transition_memo.carry_forward_notes = [
        "Do not discard the observer framing when code-level evidence appears.",
        "Treat later hypotheses as confirmations or eliminations of observer candidates, not as a fresh unframed search.",
    ]
    state.observer_framing_completed = True


def _prioritized_file_prompt(state: DebugGraphState) -> str | None:
    prioritized: list[str] = []
    if state.context.modified_files:
        prioritized.extend(state.context.modified_files)
    if state.recently_modified:
        for file_path in state.recently_modified:
            if file_path not in prioritized:
                prioritized.append(file_path)
    if not prioritized:
        return None
    return (
        f"Prioritizing files from recent history: {', '.join(prioritized[:5])}. "
        "Please generate a hypothesis based on these files."
    )


def _closed_loop_gaps(state: DebugGraphState) -> list[str]:
    gaps: list[str] = []
    if not state.closed_loop.input_event:
        gaps.append("input event")
    if not state.closed_loop.control_decision:
        gaps.append("control decision")
    if not state.closed_loop.resource_allocation:
        gaps.append("resource allocation")
    if not state.closed_loop.state_transition:
        gaps.append("state transition")
    if not state.closed_loop.external_observation:
        gaps.append("external observation")
    if not state.closed_loop.break_point:
        gaps.append("suspected loop break point")
    return gaps


def _root_cause_readiness_gaps(state: DebugGraphState) -> list[str]:
    _sync_resolution_coverage(state)
    gaps: list[str] = []
    if not state.resolution.root_cause:
        gaps.append("confirmed root cause")
    else:
        if not state.resolution.root_cause.summary:
            gaps.append("root cause summary")
        if not state.resolution.root_cause.owning_layer:
            gaps.append("root cause owning layer")
        if not state.resolution.root_cause.broken_control_state:
            gaps.append("broken control state")
        if not state.resolution.root_cause.failure_mechanism:
            gaps.append("failure mechanism")
        if not state.resolution.root_cause.loop_break:
            gaps.append("closed-loop break")
        if not state.resolution.root_cause.decisive_signal:
            gaps.append("primary decisive signal")
    if not state.truth_ownership:
        gaps.append("truth ownership map")
    if not state.control_state:
        gaps.append("control state inventory")
    if not state.observation_state:
        gaps.append("observation state inventory")
    gaps.extend(_closed_loop_gaps(state))
    if not state.resolution.decisive_signals:
        gaps.append("decisive signals")
    candidate_count = len(state.observer_framing.alternative_cause_candidates)
    if candidate_count:
        required_considered = min(2, candidate_count)
        if len(state.resolution.alternative_hypotheses_considered) < required_considered:
            gaps.append("alternative hypothesis coverage")
        if candidate_count > 1 and not state.resolution.alternative_hypotheses_ruled_out:
            gaps.append("ruled-out alternative causes")
    if state.resolution.root_cause_confidence != "confirmed":
        gaps.append("root cause confidence set to confirmed")
    return gaps


def _format_checklist(title: str, items: list[str], *, intro: str | None = None) -> str:
    lines = [title]
    if intro:
        lines.append(intro)
    for item in items:
        lines.append(f"- [ ] {item}")
    return "\n".join(lines)


def _root_cause_checklist_message(state: DebugGraphState, *, stage: str) -> str:
    gaps = _root_cause_readiness_gaps(state)
    if not gaps:
        return ""
    title = (
        "Root cause candidate recorded, but fixing is blocked until the control-plane framing is complete."
        if stage == "investigating"
        else "Fixing is blocked until the root cause is confirmed at the ownership/control-loop level."
    )
    return _format_checklist(
        title,
        gaps,
        intro="Fill in the missing items below before advancing:",
    )


def _fix_scope_readiness_gaps(state: DebugGraphState) -> list[str]:
    gaps = _root_cause_readiness_gaps(state)
    if not state.resolution.fix_scope:
        gaps.append("fix scope classification")
    elif state.resolution.fix_scope == "surface-only":
        gaps.append("replace the surface-only fix with an owning-layer or boundary fix")
    return gaps


def _fix_scope_checklist_message(state: DebugGraphState) -> str:
    return _format_checklist(
        "Fixing is blocked until the proposed change is classified as a root-cause fix rather than a surface-only patch. Surface-only fixes cannot satisfy the debug contract.",
        _fix_scope_readiness_gaps(state),
        intro="Fill in the missing items below before advancing:",
    )


def _post_verification_readiness_gaps(state: DebugGraphState) -> list[str]:
    gaps: list[str] = []
    if not state.resolution.fix_scope:
        gaps.append("fix scope classification")
    elif state.resolution.fix_scope == "surface-only":
        gaps.append("surface-only fixes cannot satisfy the debug contract")
    if not state.resolution.loop_restoration_proof:
        gaps.append("loop restoration proof")
    return gaps


def _post_verification_checklist_message(state: DebugGraphState) -> str:
    return _format_checklist(
        "Verification passed, but the session cannot move to resolved until the full loop-restoration proof is recorded.",
        _post_verification_readiness_gaps(state),
        intro="Record the remaining closure evidence below before marking the issue resolved:",
    )


def _profile_specific_items(state: DebugGraphState) -> list[str]:
    profile = _debug_profile(state)
    if profile == "scheduler-admission":
        return [
            "Capture queue contents before and after the decision point",
            "Capture running/admitted ownership sets before and after slot release",
            "Capture resource counters such as active slots or admission counts",
            "Trace the promotion handoff from waiting to running",
        ]
    if profile == "cache-snapshot":
        return [
            "Capture the authoritative control state and the cached/snapshot state side by side",
            "Record when the snapshot was written versus when control state changed",
            "Trace any cache invalidation or refresh path",
            "Prove whether stale data is driving control decisions or only display",
        ]
    if profile == "ui-projection":
        return [
            "Capture source-of-truth state at publish time",
            "Capture the projected UI/view-model state after transformation",
            "Trace the publish/subscription boundary or polling boundary",
            "Prove whether the bug is in projection only or in the owning control layer",
        ]
    return [
        "Capture the owning decision-layer state directly",
        "Capture the external projection state separately",
        "Trace the boundary where control state becomes observable state",
    ]


def _diagnostic_escalation_message(state: DebugGraphState) -> str:
    root_cause = (
        state.resolution.root_cause.display_text()
        if state.resolution.root_cause
        else "Current hypothesis"
    )
    profile = _debug_profile(state)
    profile_intro = {
        "scheduler-admission": "Detected profile: scheduler/admission. Focus on queues, ownership sets, and resource accounting.",
        "cache-snapshot": "Detected profile: cache/snapshot drift. Focus on authoritative state versus stale projections.",
        "ui-projection": "Detected profile: UI projection. Focus on source-of-truth versus published/rendered state.",
        "general": "Detected profile: general control-plane issue. Focus on decisive state at the owning layer.",
    }[profile]
    return _format_checklist(
        f"{root_cause} did not hold under verification. Stop layering local fixes and add decisive instrumentation for the control plane.",
        [
            "Capture ownership sets at the decision layer",
            * _profile_specific_items(state),
            "Trace the exact decision-boundary handoff",
            "Update truth_ownership with the owning layer evidence",
            "Update control_state and observation_state separately",
            "Update closed_loop.break_point with the suspected broken link",
            "Record resolution.decisive_signals before proposing another fix",
        ],
        intro=f"Collect these signals before retrying:\n{profile_intro}",
    )


def _research_checkpoint_message(state: DebugGraphState, research_path: Path) -> str:
    return _format_checklist(
        "Repeated verification failed. Stop iterating on local fixes and do focused research before the next code change.",
        [
            f"Review `{research_path.as_posix()}`",
            "Answer the open research questions with repository evidence or primary sources",
            "Update the debug session with the strongest new fact",
            "Replace or explicitly reject the current root-cause draft before another fix",
        ],
        intro="Use the research checkpoint to break the loop instead of retrying the same fix shape.",
    )


def _command_failed(output: str) -> bool:
    normalized = output.upper()
    return (
        "FAIL" in normalized
        or "ERROR" in normalized
        or "TRACEBACK" in normalized
        or "COMMAND EXITED WITH CODE" in normalized
    )


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = value.strip()
        if text and text not in seen:
            ordered.append(text)
            seen.add(text)
    return ordered


def _framing_gate_count_requirement(state: DebugGraphState) -> int:
    return 2 if state.observer_mode == "compressed" else 3


def _framing_gate_diversity_gaps(state: DebugGraphState) -> list[str]:
    shapes = {
        candidate.failure_shape
        for candidate in state.observer_framing.alternative_cause_candidates
        if candidate.failure_shape
    }
    if len(shapes) >= 2:
        return []
    return ["candidate diversity across at least 2 failure shapes or truth-owner families"]


def _framing_gate_gaps(state: DebugGraphState) -> list[str]:
    candidates = state.observer_framing.alternative_cause_candidates
    gaps: list[str] = []
    required_count = _framing_gate_count_requirement(state)
    if len(candidates) < required_count:
        gaps.append(f"at least {required_count} alternative cause candidates")
    if not state.observer_framing.contrarian_candidate:
        gaps.append("contrarian candidate")
    for index, candidate in enumerate(candidates, start=1):
        if not candidate.failure_shape:
            gaps.append(f"candidate {index} failure_shape")
        if not candidate.would_rule_out:
            gaps.append(f"candidate {index} would_rule_out")
        if not candidate.recommended_first_probe:
            gaps.append(f"candidate {index} recommended_first_probe")
    gaps.extend(_framing_gate_diversity_gaps(state))
    return _unique_strings(gaps)


def _sync_resolution_coverage(state: DebugGraphState) -> None:
    considered = list(state.resolution.alternative_hypotheses_considered)
    ruled_out = list(state.resolution.alternative_hypotheses_ruled_out)

    if state.resolution.root_cause and state.resolution.root_cause.summary:
        considered.append(state.resolution.root_cause.summary)

    if state.current_focus.hypothesis:
        considered.append(state.current_focus.hypothesis)

    for entry in state.eliminated:
        considered.append(entry.hypothesis)
        ruled_out.append(entry.hypothesis)

    state.resolution.alternative_hypotheses_considered = _unique_strings(considered)
    state.resolution.alternative_hypotheses_ruled_out = _unique_strings(ruled_out)


def _resolve_test_targets(state: DebugGraphState) -> list[str]:
    explicit_targets: list[str] = []
    seen: set[str] = set()

    for path in [*state.resolution.files_changed, *state.context.modified_files]:
        normalized = path.replace("\\", "/")
        if normalized.startswith("tests/") and normalized not in seen:
            explicit_targets.append(normalized)
            seen.add(normalized)

    if explicit_targets:
        return explicit_targets

    if Path("tests").exists():
        return ["tests"]

    return []


def _record_verification_evidence(
    state: DebugGraphState,
    command: str,
    output: str,
    *,
    success: bool,
) -> None:
    result = "passed" if success else "failed"
    fix_summary = state.resolution.fix or "No fix recorded"
    state.evidence.append(
        EvidenceEntry(
            checked=command,
            found=output,
            implication=f"Verification {result} while validating fix: {fix_summary}",
        )
    )


def _debug_verification_runner(command: str) -> tuple[int, str]:
    output = run_command(command)
    return (1, output) if _command_failed(output) else (0, output)


def _refresh_execution_intent(state: DebugGraphState, commands: list[str]) -> None:
    if not state.execution_intent.outcome:
        state.execution_intent.outcome = (
            state.resolution.fix
            or "Verify the current fix against the recorded reproduction"
        )
    if not state.execution_intent.constraints:
        state.execution_intent.constraints = [
            "Do not mark resolved without verification evidence",
            "If verification fails, return to investigating instead of layering more fixes blindly",
        ]
    if not state.execution_intent.success_signals:
        state.execution_intent.success_signals = [f"{command} passes" for command in commands]

def persist(func):
    @functools.wraps(func)
    async def wrapper(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]):
        # Update BEFORE taking action
        _refresh_diagnostic_profile(ctx.state)
        _refresh_lane_plan(ctx.state)
        if ctx.deps:
            ctx.deps.save(ctx.state)
        
        result = await func(self, ctx)
        
        # Update AFTER taking action
        _refresh_diagnostic_profile(ctx.state)
        _refresh_lane_plan(ctx.state)
        if ctx.deps:
            ctx.deps.save(ctx.state)
        
        return result
    return wrapper

class GatheringNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['InvestigatingNode', End]:
        ctx.state.status = DebugStatus.GATHERING
        ctx.state.current_node_id = "GatheringNode"
        
        # 1. Load context
        loader = ContextLoader()

        if not ctx.state.context.feature_id:
            feature_dir = loader.find_active_feature()
            if feature_dir:
                ctx.state.context = loader.load_feature_context(feature_dir)

        if not ctx.state.recently_modified:
            ctx.state.recently_modified = loader.get_recent_git_changes()

        # 2. Observer Framing — dispatch to think subagent for isolated reasoning
        if not ctx.state.observer_framing_completed:
            prompt = build_think_subagent_prompt(ctx.state)
            ctx.state.think_subagent_prompt = prompt
            return _await_input(
                ctx.state,
                "Observer framing needed. Spawn a think subagent with think_subagent_prompt. "
                "Wait for its structured result, then parse the YAML block after '---' and populate "
                "observer_framing, transition_memo, and alternative_cause_candidates fields. "
                "Set observer_framing_completed=True and continue.",
            )

        framing_gaps = _framing_gate_gaps(ctx.state)
        if framing_gaps:
            ctx.state.framing_gate_passed = False
            return _await_input(
                ctx.state,
                _format_checklist(
                    "Observer framing is complete in form but not yet sufficient to enter investigation.",
                    framing_gaps,
                    intro="Fill in the missing framing items below before reproduction or code reads:",
                ),
            )
        ctx.state.framing_gate_passed = True

        # 3. Gate checks
        if not ctx.state.symptoms.expected or not ctx.state.symptoms.actual:
            return _await_input(
                ctx.state,
                "Observer framing complete. Collect expected and actual behavior before continuing into evidence investigation.",
            )

        if not ctx.state.symptoms.reproduction_verified:
            return _await_input(
                ctx.state,
                "Observer framing complete. Reproduction not verified. Please create a reproduction script and run it to verify the bug. Update symptoms.reproduction_verified to True once confirmed.",
            )

        return InvestigatingNode()

class InvestigatingNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['FixingNode', End]:
        ctx.state.status = DebugStatus.INVESTIGATING
        ctx.state.current_node_id = "InvestigatingNode"
        
        # 1. Update next_action to prioritize recently modified files if no focus is set
        if not ctx.state.current_focus.hypothesis and not ctx.state.current_focus.next_action:
            prioritized_prompt = _prioritized_file_prompt(ctx.state)
            if prioritized_prompt:
                ctx.state.current_focus.next_action = prioritized_prompt

        # 2. Hypothesis Elimination logic
        # If next_action starts with "Eliminate:", move current focus to eliminated list
        if ctx.state.current_focus.next_action and ctx.state.current_focus.next_action.startswith("Eliminate:"):
            evidence = ctx.state.current_focus.next_action[len("Eliminate:"):].strip()
            if ctx.state.current_focus.hypothesis:
                ctx.state.eliminated.append(EliminatedEntry(
                    hypothesis=ctx.state.current_focus.hypothesis,
                    evidence=evidence or "No evidence provided."
                ))
            # Reset current focus for next hypothesis
            ctx.state.current_focus.hypothesis = None
            ctx.state.current_focus.test = None
            ctx.state.current_focus.expecting = None
            ctx.state.current_focus.next_action = None
            
            if len(ctx.state.eliminated) >= 2 and not ctx.state.resolution.decisive_signals:
                ctx.state.current_focus.next_action = _diagnostic_escalation_message(ctx.state)
            else:
                prioritized_prompt = _prioritized_file_prompt(ctx.state)
                if prioritized_prompt:
                    ctx.state.current_focus.next_action = prioritized_prompt
            return End("Awaiting more debugging input")

        # If root cause is found, move to fixing.
        if ctx.state.resolution.root_cause:
            readiness_gaps = _root_cause_readiness_gaps(ctx.state)
            if readiness_gaps:
                return _await_input(
                    ctx.state,
                    _root_cause_checklist_message(ctx.state, stage="investigating"),
                )
            return FixingNode()
        
        return End("Awaiting more debugging input")

class FixingNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['VerifyingNode', End]:
        ctx.state.status = DebugStatus.FIXING
        ctx.state.current_node_id = "FixingNode"
        if not ctx.state.resolution.fix:
            return _await_input(
                ctx.state,
                "Root cause identified. Please propose a fix and update resolution.fix.",
            )
        readiness_gaps = _fix_scope_readiness_gaps(ctx.state)
        if readiness_gaps:
            return _await_input(
                ctx.state,
                _fix_scope_checklist_message(ctx.state),
            )
        return VerifyingNode()

class VerifyingNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['ResolvedNode', 'InvestigatingNode', 'AwaitingHumanNode', End]:
        ctx.state.status = DebugStatus.VERIFYING
        ctx.state.current_node_id = "VerifyingNode"

        commands: list[str] = []
        repro_cmd = ctx.state.symptoms.reproduction_command
        if repro_cmd:
            commands.append(repro_cmd)
        test_targets = _resolve_test_targets(ctx.state)
        if test_targets:
            commands.append(f"pytest {' '.join(test_targets)}")

        _refresh_execution_intent(ctx.state, commands)
        validation_results = run_verification_commands(
            commands,
            runner=_debug_verification_runner,
            stop_on_failure=True,
        )
        ctx.state.resolution.validation_results = [
            ValidationCheck(command=result.command, status=result.status, output=result.output)
            for result in validation_results
        ]
        for result in validation_results:
            _record_verification_evidence(
                ctx.state,
                result.command,
                result.output,
                success=result.status == "passed",
            )
        if validation_results and not verification_passed(validation_results):
            return self._handle_failed_verification(ctx.state, ctx.deps)

        completion_gaps = _post_verification_readiness_gaps(ctx.state)
        if completion_gaps:
            ctx.state.resolution.verification = "success"
            return _await_input(
                ctx.state,
                _post_verification_checklist_message(ctx.state),
            )

        # If verification passed, move to resolved.
        ctx.state.resolution.verification = "success"
        ctx.state.resolution.human_verification_outcome = "pending"
        return AwaitingHumanNode()

    def _handle_failed_verification(
        self,
        state: DebugGraphState,
        persistence: MarkdownPersistenceHandler | None,
    ) -> Union['InvestigatingNode', 'AwaitingHumanNode']:
        state.resolution.verification = "failed"
        previous_failures = state.resolution.agent_fail_count or state.resolution.fail_count
        state.resolution.agent_fail_count = previous_failures + 1
        state.resolution.fail_count = state.resolution.agent_fail_count
        research_path: Path | None = None
        if state.resolution.agent_fail_count >= 2 and persistence:
            research_path = persistence.save_research_checkpoint(state)
        if state.resolution.fix and state.resolution.fix not in state.resolution.rejected_surface_fixes:
            state.resolution.rejected_surface_fixes.append(state.resolution.fix)
        if state.resolution.agent_fail_count > 2:
            if research_path is not None:
                state.current_focus.next_action = (
                    f"Repeated verification failed. Review `{research_path.as_posix()}` "
                    "before attempting another fix loop."
                )
            return AwaitingHumanNode()
        if state.resolution.agent_fail_count >= 2:
            state.current_focus.hypothesis = None
            state.current_focus.test = None
            state.current_focus.expecting = None
            if research_path is not None:
                state.current_focus.next_action = _research_checkpoint_message(state, research_path)
            else:
                state.current_focus.next_action = _diagnostic_escalation_message(state)
        return InvestigatingNode()

class AwaitingHumanNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['VerifyingNode', End]:
        ctx.state.status = DebugStatus.AWAITING_HUMAN
        ctx.state.current_node_id = "AwaitingHumanNode"
        if ctx.state.resolution.human_verification_outcome == "passed":
            return ResolvedNode()
        report_builder = ctx.deps.build_handoff_report if ctx.deps else build_handoff_report
        ctx.state.resolution.report = report_builder(ctx.state)
        if ctx.state.resolution.agent_fail_count >= 2 and ctx.deps:
            research_path = ctx.deps.save_research_checkpoint(ctx.state)
            if ctx.state.parent_slug:
                ctx.state.current_focus.next_action = (
                    f"Repeated verification failed for this follow-up issue. Review "
                    f"`{research_path.as_posix()}` and, after confirming the outcome, return to parent session "
                    f"`{ctx.state.parent_slug}`."
                )
            else:
                ctx.state.current_focus.next_action = (
                    f"Repeated verification failed. Review `{research_path.as_posix()}` before another fix loop."
                )
        elif ctx.state.parent_slug:
            ctx.state.current_focus.next_action = (
                f"Autonomous verification exhausted for this follow-up issue. "
                f"After confirming it, return to parent session `{ctx.state.parent_slug}`."
            )
        else:
            ctx.state.current_focus.next_action = (
                "Autonomous verification exhausted. Review the session summary and continue manually."
            )
        return End("Awaiting Human Review")

class ResolvedNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> End:
        ctx.state.status = DebugStatus.RESOLVED
        ctx.state.current_node_id = "ResolvedNode"
        return End("Resolved")

debug_graph = Graph(
    nodes=[
        GatheringNode,
        InvestigatingNode,
        FixingNode,
        VerifyingNode,
        AwaitingHumanNode,
        ResolvedNode,
    ]
)

async def run_debug_session(
    state: DebugGraphState,
    persistence: MarkdownPersistenceHandler,
    *,
    resumed: bool = False,
):
    """
    Runs the debug investigation loop until it reaches an end state or requires human input.
    """
    if resumed and state.current_node_id == "VerifyingNode":
        state.status = DebugStatus.AWAITING_HUMAN
        state.current_node_id = "AwaitingHumanNode"
        state.resolution.human_verification_outcome = "pending"
        state.current_focus.next_action = (
            "Confirm persisted verification commands before resuming automated execution."
        )
        state.resolution.report = (
            "## Resume Confirmation Required\n\n"
            "- Verification commands loaded from disk are not executed automatically.\n"
            "- Review and reconfirm the persisted reproduction command before continuing.\n"
        )
        persistence.save(state)
        return

    # If we are resuming, we need to find the correct starting node
    start_node = GatheringNode
    if state.current_node_id:
        if state.current_node_id in debug_graph.node_defs:
            start_node = debug_graph.node_defs[state.current_node_id].node
    
    await debug_graph.run(start_node(), state=state, deps=persistence)
