# Research Summary: sp-debug

**Domain:** AI Debugging CLI (`spec-kit-plus`)
**Researched:** 2025-05-22
**Overall Confidence:** HIGH

## Executive Summary

The research concludes that building a systematic, resumable debugging workflow (`sp-debug`) for `spec-kit-plus` is best achieved using a "Graph-as-Workflow" architecture. In 2025, the standard stack for such a Python-based agentic CLI is **PydanticAI** combined with **pydantic-graph** and **LiteLLM**. 

The core of the "Scientific Method" (Gather -> Investigate -> Fix -> Verify) will be managed as a Finite State Machine, where each step is a type-safe node in the graph. State persistence will be handled via a custom **Markdown-based Persistence Handler**, ensuring that investigation logs are human-readable while allowing the agent to perfectly resume after any interruption. 

By leveraging existing Spec Kit artifacts (`spec.md`, `plan.md`, `ROADMAP.md`), the debugger avoids the common "cold start" problem, instantly focusing on relevant files and recent changes.

## Key Findings

**Stack:** Python 3.11+, PydanticAI (Agent), pydantic-graph (Workflow), LiteLLM (Claude 3.5 Sonnet), and Markdown (State).
**Architecture:** FSM (Finite State Machine) using pydantic-graph with explicit "Investigation" and "Verification" nodes.
**Critical Pitfall:** Hallucinating evidence and infinite loops are the primary risks; mitigated by strict tool-use enforcement and state-aware loop detection.

## Implications for Roadmap

Based on research, the suggested phase structure for implementing `sp-debug`:

1.  **Phase 1: Workflow Foundation** - Build the `pydantic-graph` skeleton and Markdown state persistence.
    *   Addresses: Resumability, Investigation Log.
    *   Avoids: Loss of state on CLI crash.
2.  **Phase 2: Context & Reasoning** - Integrate Spec Kit artifact loading and PydanticAI agent logic.
    *   Addresses: Context Injection, Scientific Method logic.
    *   Avoids: "Cold start" on large repos.
3.  **Phase 3: Tool Execution & Verification** - Implement secure tools for file reading, test execution, and code modification.
    *   Addresses: Capability to actually fix bugs.
    *   Avoids: Manual human-in-the-loop for simple fixes.
4.  **Phase 4: Observability & Refinement** - Add Logfire tracing and advanced hypothesis tracking.
    *   Addresses: Developer transparency, complex bug resolution.

**Phase ordering rationale:**
- Persistence and the basic graph structure are the highest risk/value components and must be established first to ensure the "resumability" promise. Context injection follows to provide the "intelligence" required for meaningful investigation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PydanticAI/Graph is the current 2025 industry standard. |
| Features | HIGH | Table stakes are well-understood in the ecosystem. |
| Architecture | HIGH | Graph-based state machines are a proven pattern for complex agents. |
| Pitfalls | MEDIUM | Hallucination is a persistent risk for all LLM apps in 2025. |

## Gaps to Address

- **Large Context Performance:** Need to test how the agent handles repos where `spec.md` and `plan.md` themselves are extremely large.
- **Model Switching:** Rationale for when to switch from Claude to GPT-4o for cost optimization vs. quality.
