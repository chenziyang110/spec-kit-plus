from pathlib import Path
from typing import Union
from pydantic_graph import BaseNode, Graph, GraphRunContext, End
from .schema import (
    DebugGraphState,
    DebugStatus,
    EliminatedEntry,
    EvidenceEntry,
    SuggestedEvidenceLane,
    ValidationCheck,
)
from .persistence import MarkdownPersistenceHandler, build_handoff_report
from .context import ContextLoader
from .utils import run_command, edit_file, read_file
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
        
        # 1. Instantiate ContextLoader and find the active feature context.
        loader = ContextLoader()
        
        # 2. Populate ctx.state.context and ctx.state.recently_modified if not already set.
        if not ctx.state.context.feature_id:
            feature_dir = loader.find_active_feature()
            if feature_dir:
                ctx.state.context = loader.load_feature_context(feature_dir)
        
        if not ctx.state.recently_modified:
            ctx.state.recently_modified = loader.get_recent_git_changes()

        # 3. Add logic to ensure ctx.state.symptoms.expected and ctx.state.symptoms.actual are populated.
        if not ctx.state.symptoms.expected or not ctx.state.symptoms.actual:
            return _await_input(
                ctx.state,
                "Collect expected and actual behavior before continuing.",
            )
        
        # 4. Implement "Reproduction First" gate in GatheringNode
        if not ctx.state.symptoms.reproduction_verified:
            return _await_input(
                ctx.state,
                "Reproduction not verified. Please create a reproduction script and run it to verify the bug. Update symptoms.reproduction_verified to True once confirmed.",
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
        readiness_gaps = _root_cause_readiness_gaps(ctx.state)
        if readiness_gaps:
            return _await_input(
                ctx.state,
                _root_cause_checklist_message(ctx.state, stage="fixing"),
            )
        # If fix is applied, move to verifying
        if ctx.state.resolution.fix:
            return VerifyingNode()
        
        return _await_input(
            ctx.state,
            "Root cause identified. Please propose a fix and update resolution.fix.",
        )

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

        # If verification passed, move to resolved.
        ctx.state.resolution.verification = "success"
        return ResolvedNode()

    def _handle_failed_verification(
        self,
        state: DebugGraphState,
        persistence: MarkdownPersistenceHandler | None,
    ) -> Union['InvestigatingNode', 'AwaitingHumanNode']:
        state.resolution.verification = "failed"
        state.resolution.fail_count += 1
        research_path: Path | None = None
        if state.resolution.fail_count >= 2 and persistence:
            research_path = persistence.save_research_checkpoint(state)
        if state.resolution.fix and state.resolution.fix not in state.resolution.rejected_surface_fixes:
            state.resolution.rejected_surface_fixes.append(state.resolution.fix)
        if state.resolution.fail_count > 2:
            if research_path is not None:
                state.current_focus.next_action = (
                    f"Repeated verification failed. Review `{research_path.as_posix()}` "
                    "before attempting another fix loop."
                )
            return AwaitingHumanNode()
        if state.resolution.fail_count >= 2:
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
        report_builder = ctx.deps.build_handoff_report if ctx.deps else build_handoff_report
        ctx.state.resolution.report = report_builder(ctx.state)
        if ctx.state.resolution.fail_count >= 2 and ctx.deps:
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
