from pathlib import Path
from typing import Union
from pydantic_graph import BaseNode, Graph, GraphRunContext, End
from .schema import DebugGraphState, DebugStatus, EliminatedEntry, EvidenceEntry
from .persistence import MarkdownPersistenceHandler, build_handoff_report
from .context import ContextLoader
from .utils import run_command, edit_file, read_file
import functools


def _await_input(state: DebugGraphState, message: str) -> End:
    state.current_focus.next_action = message
    return End("Awaiting more debugging input")


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

def persist(func):
    @functools.wraps(func)
    async def wrapper(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]):
        # Update BEFORE taking action
        if ctx.deps:
            ctx.deps.save(ctx.state)
        
        result = await func(self, ctx)
        
        # Update AFTER taking action
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
            prioritized = []
            if ctx.state.context.modified_files:
                prioritized.extend(ctx.state.context.modified_files)
            if ctx.state.recently_modified:
                # Add recently modified git files that aren't already in the list
                for f in ctx.state.recently_modified:
                    if f not in prioritized:
                        prioritized.append(f)
            
            if prioritized:
                ctx.state.current_focus.next_action = f"Prioritizing files from recent history: {', '.join(prioritized[:5])}. Please generate a hypothesis based on these files."

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
            
            prioritized = []
            if ctx.state.context.modified_files:
                prioritized.extend(ctx.state.context.modified_files)
            if ctx.state.recently_modified:
                for file_path in ctx.state.recently_modified:
                    if file_path not in prioritized:
                        prioritized.append(file_path)
            if prioritized:
                ctx.state.current_focus.next_action = (
                    f"Prioritizing files from recent history: {', '.join(prioritized[:5])}. "
                    "Please generate a hypothesis based on these files."
                )
            return End("Awaiting more debugging input")

        # If root cause is found, move to fixing.
        if ctx.state.resolution.root_cause:
            return FixingNode()
        
        return End("Awaiting more debugging input")

class FixingNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['VerifyingNode', End]:
        ctx.state.status = DebugStatus.FIXING
        ctx.state.current_node_id = "FixingNode"
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
        
        # 1. Run reproduction command
        repro_cmd = ctx.state.symptoms.reproduction_command
        if repro_cmd:
            output = run_command(repro_cmd)
            command_failed = _command_failed(output)
            _record_verification_evidence(
                ctx.state,
                repro_cmd,
                output,
                success=not command_failed,
            )
            if command_failed:
                return self._handle_failed_verification(ctx.state)

        # 2. Run feature directory tests
        test_targets = _resolve_test_targets(ctx.state)
        if test_targets:
            test_cmd = f"pytest {' '.join(test_targets)}"
            output = run_command(test_cmd)
            command_failed = _command_failed(output)
            _record_verification_evidence(
                ctx.state,
                test_cmd,
                output,
                success=not command_failed,
            )
            if command_failed:
                return self._handle_failed_verification(ctx.state)

        # If verification passed, move to resolved.
        ctx.state.resolution.verification = "success"
        return ResolvedNode()

    def _handle_failed_verification(self, state: DebugGraphState) -> Union['InvestigatingNode', 'AwaitingHumanNode']:
        state.resolution.verification = "failed"
        state.resolution.fail_count += 1
        if state.resolution.fail_count > 2:
            return AwaitingHumanNode()
        return InvestigatingNode()

class AwaitingHumanNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['VerifyingNode', End]:
        ctx.state.status = DebugStatus.AWAITING_HUMAN
        ctx.state.current_node_id = "AwaitingHumanNode"
        report_builder = ctx.deps.build_handoff_report if ctx.deps else build_handoff_report
        ctx.state.resolution.report = report_builder(ctx.state)
        ctx.state.current_focus.next_action = "Autonomous verification exhausted. Review the session summary and continue manually."
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
