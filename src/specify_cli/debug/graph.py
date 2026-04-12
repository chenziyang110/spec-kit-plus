from typing import Union
from pydantic_graph import BaseNode, Graph, GraphRunContext, End
from .schema import DebugGraphState, DebugStatus

class GatheringNode(BaseNode[DebugGraphState]):
    async def run(self, ctx: GraphRunContext[DebugGraphState]) -> Union['InvestigatingNode', End]:
        ctx.state.status = DebugStatus.GATHERING
        ctx.state.current_node_id = "GatheringNode"
        # In a real implementation, it would gather symptoms and then move to investigation
        return InvestigatingNode()

class InvestigatingNode(BaseNode[DebugGraphState]):
    async def run(self, ctx: GraphRunContext[DebugGraphState]) -> Union['FixingNode', End]:
        ctx.state.status = DebugStatus.INVESTIGATING
        ctx.state.current_node_id = "InvestigatingNode"
        # If root cause is found, move to fixing. Otherwise it might stay here or end.
        if ctx.state.resolution.root_cause:
            return FixingNode()
        return End("Investigation incomplete")

class FixingNode(BaseNode[DebugGraphState]):
    async def run(self, ctx: GraphRunContext[DebugGraphState]) -> Union['VerifyingNode', End]:
        ctx.state.status = DebugStatus.FIXING
        ctx.state.current_node_id = "FixingNode"
        # If fix is applied, move to verifying
        if ctx.state.resolution.fix:
            return VerifyingNode()
        return End("Fix not applied")

class VerifyingNode(BaseNode[DebugGraphState]):
    async def run(self, ctx: GraphRunContext[DebugGraphState]) -> Union['ResolvedNode', 'InvestigatingNode', End]:
        ctx.state.status = DebugStatus.VERIFYING
        ctx.state.current_node_id = "VerifyingNode"
        # If verification passed, move to resolved. Otherwise back to investigation.
        if ctx.state.resolution.verification:
            return ResolvedNode()
        return InvestigatingNode()

class AwaitingHumanNode(BaseNode[DebugGraphState]):
    async def run(self, ctx: GraphRunContext[DebugGraphState]) -> Union['VerifyingNode', End]:
        ctx.state.status = DebugStatus.AWAITING_HUMAN
        ctx.state.current_node_id = "AwaitingHumanNode"
        return End("Awaiting human input (placeholder)")

class ResolvedNode(BaseNode[DebugGraphState]):
    async def run(self, ctx: GraphRunContext[DebugGraphState]) -> End:
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
