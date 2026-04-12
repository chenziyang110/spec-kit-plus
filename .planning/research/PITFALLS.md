# Domain Pitfalls

**Domain:** AI Debugging CLI (`sp-debug`)
**Researched:** 2025-05-22
**Overall Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Hallucinating Evidence
**What goes wrong:** The agent "sees" a bug in a file it hasn't actually read yet, or claims a test failed when it wasn't run.
**Root Cause:** Over-reliance on internal knowledge and long context windows where the LLM might drift from reality.
**Consequences:** The agent builds a "fix" for a non-existent problem or misses the real issue.
**Prevention:** Strictly enforce tool use for any code claim. Force the agent to cite file/line numbers from actual `read_file` results.
**Detection:** Verification step fails or human reviewer sees "hallucinated" code in the log.

### Pitfall 2: Infinite Loops
**What goes wrong:** The agent keeps running the same investigation steps (e.g., `list_files` -> `read_file`) without progress.
**Root Cause:** Lack of state awareness in the loop. The agent forgets what it already tried.
**Consequences:** Burned tokens and no fix.
**Prevention:** Track "Visited Files" and "Eliminated Hypotheses" in the graph state. If a node repeats 3+ times without progress, trigger a "Re-evaluate" node.

## Moderate Pitfalls

### Pitfall 1: "Cold Start" on Large Codebases
**What goes wrong:** The agent spends too much time/tokens reading irrelevant files.
**Prevention:** Leverage Spec Kit artifacts (`spec.md`, `plan.md`, `ROADMAP.md`) to guide the search. Focus on files mentioned in the most recent plan.

### Pitfall 2: Dependency Conflicts with `uv`
**What goes wrong:** Adding new AI libraries (`pydantic-ai`, `litellm`) might conflict with existing CLI dependencies.
**Prevention:** Use `uv` to manage isolated environments and strictly version-lock all agentic libraries.

## Minor Pitfalls

### Pitfall 1: Markdown State Parsing
**What goes wrong:** Complex YAML frontmatter in Markdown might become difficult to parse if it grows too large.
**Prevention:** Keep the frontmatter schema simple and lean. Store large "Evidence" chunks in the Markdown body, not the frontmatter.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Core Workflow** | Non-resumable state if graph logic is flawed. | Unit test the `PersistenceHandler` extensively with mocked LLM calls. |
| **Tool Integration** | Shell injection via `run_test`. | Use `shlex.quote` and strictly limit available commands. |
| **Context Injection** | Stale `spec.md` or `plan.md`. | Always check file modification dates and warn the user if docs are out-of-sync with code. |

## Sources

- [AI Agent Pitfalls 2025](https://dev.to/ai-pitfalls-2025) (MEDIUM confidence)
- [PydanticAI GitHub Issues](https://github.com/pydantic/pydantic-ai/issues) (HIGH confidence)
