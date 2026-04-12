# Architecture Patterns

**Domain:** AI Debugging CLI (`sp-debug`)
**Researched:** 2025-05-22
**Overall Confidence:** HIGH

## Recommended Architecture

The system should be built as a **Finite State Machine (FSM)** using `pydantic-graph`. This allows for explicit, type-safe transitions between the different stages of the "Scientific Method".

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **CLI (Typer)** | Entry point, argument parsing, session initialization. | Workflow Manager |
| **Workflow Manager (pydantic-graph)** | Managing state, executing nodes, handling persistence. | Agent, File System |
| **Agent (PydanticAI)** | Reasoning, tool calling, structured output. | Workflow Manager, LLM |
| **Context Provider** | Loading and parsing Spec Kit artifacts. | Workflow Manager |
| **Persistence Handler** | Serializing/Deserializing state to Markdown. | Workflow Manager, File System |

### Data Flow

1.  **Initialize:** CLI loads the `session_id`. If it exists, the `Persistence Handler` restores the graph state and message history from the Markdown file.
2.  **Context Loading:** `Context Provider` reads `spec.md`, `plan.md`, etc., and injects them into the agent's system prompt.
3.  **The Loop (Gather -> Investigate -> Fix -> Verify):**
    *   **Gather:** Agent uses tools to explore symptoms.
    *   **Investigate:** Agent forms and tests hypotheses (evidence).
    *   **Fix:** Agent proposes a targeted code change.
    *   **Verify:** Agent runs tests to confirm the fix.
4.  **Save:** After each node transition, the `Persistence Handler` updates the Markdown file with new findings and updated state.

## Patterns to Follow

### Pattern 1: State-Aware Graph Nodes
Each node in the `pydantic-graph` should be small and focused. Transitions are based on the outcome of the agent's task.

```python
from pydantic_graph import BaseNode, GraphRunContext, End

@dataclass
class InvestigateNode(BaseNode[DebugState]):
    async def run(self, ctx: GraphRunContext[DebugState]) -> 'FixNode | GatherNode':
        # logic to determine if we have enough evidence for a fix
        if ctx.state.has_root_cause:
            return FixNode()
        return GatherNode()
```

### Pattern 2: Markdown "Single Source of Truth"
The Markdown file (`.planning/debug/[slug].md`) acts as both the user-readable log and the machine-parsable state.

```markdown
---
session_id: bug-123
current_node: InvestigateNode
hypotheses: [...]
eliminated: [...]
---
# Investigation Log: [slug]

## Symptoms
...
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Stateless Agents
**What:** Running the agent in a loop without persisting the graph state.
**Why bad:** If the CLI crashes, the agent loses its "train of thought" and has to re-read files and re-run tests.
**Instead:** Use `pydantic-graph` with a `PersistenceHandler` that saves after every node.

### Anti-Pattern 2: Prompt Overloading
**What:** Shoving the entire codebase into the prompt.
**Why bad:** High cost and noise. LLMs perform better with relevant context.
**Instead:** Use Spec Kit artifacts (`spec.md`, `plan.md`) as the starting point, and only read specific source files based on the investigation.

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| **LLM Token Costs** | Low impact. | Moderate. | High (use caching). |
| **Session Persistence** | Local file system is fine. | Cloud storage may be needed. | Centralized DB with E2EE. |
| **Performance** | Instant. | Depends on LLM latency. | Requires distributed queues. |

## Sources

- [PydanticAI Graph Documentation](https://ai.pydantic.dev/graph/) (HIGH confidence)
- [Clean Architecture for AI Agents](https://medium.com/p/clean-agentic-architecture-2025) (MEDIUM confidence)
