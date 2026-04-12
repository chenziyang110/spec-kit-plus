from typing import Union, TypeVar, Any, Callable
from pydantic_graph import BaseNode, Graph, GraphRunContext, End
from .schema import DebugGraphState, DebugStatus, EliminatedEntry
from .persistence import MarkdownPersistenceHandler
from .context import ContextLoader
import functools

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
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['InvestigatingNode', 'GatheringNode', End]:
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
            return self
        
        # 4. Implement "Reproduction First" gate in GatheringNode
        if not ctx.state.symptoms.reproduction_verified:
            return self

        return InvestigatingNode()

class InvestigatingNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['FixingNode', 'InvestigatingNode', End]:
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
            
            # Return self to trigger another run (which will apply prioritization)
            return self

        # If root cause is found, move to fixing.
        if ctx.state.resolution.root_cause:
            return FixingNode()
        
        # In this autonomous loop, we return self to wait for agent tool calls
        # which will eventually populate root_cause or eliminate hypotheses.
        return self

class FixingNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['VerifyingNode', End]:
        ctx.state.status = DebugStatus.FIXING
        ctx.state.current_node_id = "FixingNode"
        # If fix is applied, move to verifying
        if ctx.state.resolution.fix:
            return VerifyingNode()
        return End("Fix not applied")

class VerifyingNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['ResolvedNode', 'InvestigatingNode', End]:
        ctx.state.status = DebugStatus.VERIFYING
        ctx.state.current_node_id = "VerifyingNode"
        # If verification passed, move to resolved. Otherwise back to investigation.
        if ctx.state.resolution.verification:
            return ResolvedNode()
        return InvestigatingNode()

class AwaitingHumanNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['VerifyingNode', End]:
        ctx.state.status = DebugStatus.AWAITING_HUMAN
        ctx.state.current_node_id = "AwaitingHumanNode"
        return End("Awaiting human input (placeholder)")

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

async def run_debug_session(state: DebugGraphState, persistence: MarkdownPersistenceHandler):
    """
    Runs the debug investigation loop until it reaches an end state or requires human input.
    """
    # If we are resuming, we need to find the correct starting node
    start_node = GatheringNode
    if state.current_node_id:
        if state.current_node_id in debug_graph.node_defs:
            start_node = debug_graph.node_defs[state.current_node_id].node
    
    await debug_graph.run(start_node(), state=state, deps=persistence)
