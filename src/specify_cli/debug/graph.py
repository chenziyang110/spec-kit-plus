from typing import Union, TypeVar, Any, Callable
from pydantic_graph import BaseNode, Graph, GraphRunContext, End
from .schema import DebugGraphState, DebugStatus
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

        return InvestigatingNode()

class InvestigatingNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['FixingNode', End]:
        ctx.state.status = DebugStatus.INVESTIGATING
        ctx.state.current_node_id = "InvestigatingNode"
        # If root cause is found, move to fixing. Otherwise it might stay here or end.
        if ctx.state.resolution.root_cause:
            return FixingNode()
        return End("Investigation incomplete")

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
