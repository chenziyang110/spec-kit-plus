# Feature Landscape: `sp-debug`

**Domain:** AI-Driven Bug Fixing / Systematic Debugging
**Researched:** 2026-04-12

## Table Stakes

Features users expect in a professional-grade debugging agent. Missing these would make the tool feel unreliable or "toy-like."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Reproduction First** | The scientific method requires proof. Fixes without proof are guesses. | Med | CLI must guide the agent to create a failing test/script first. |
| **State Persistence** | Long debugging sessions shouldn't be lost if the user restarts their shell. | Low | Markdown-based logging of hypotheses, evidence, and results. |
| **Context Awareness** | The agent must read `spec.md`, `plan.md`, `constitution.md` automatically. | Low | Leveraging existing Spec Kit artifacts. |
| **Human-in-the-Loop** | Critical code changes should be approved by a human developer. | Med | Approval gates before applying `write_file` changes. |
| **Resumability** | The ability to resume an interrupted session from the last successful step. | Med | Needs a robust "Session Selection" mechanism when starting `sp-debug`. |

## Differentiators

Features that set `sp-debug` apart from basic coding assistants like Aider.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Scientific Method Loop** | Guarantees systematic progress vs. the "shotgun approach" of typical AI fixes. | Med | Structured progression: Gather -> Investigate -> Fix -> Verify. |
| **Automatic Context Pruning** | Only inject relevant snippets of artifacts to keep the context window focused. | High | Intelligent selection of which Spec/Plan sections matter for the current bug. |
| **State Snapshotting** | Ability to "rollback" to a previous hypothesis if a branch of investigation fails. | Med | Linked to git commits or separate markdown snapshots. |
| **Evidence Extraction** | Automatically parsing tool outputs and summarizing the "nuggets" of proof. | Med | Reduces context window pollution. |

## Anti-Features

Features to explicitly NOT build to avoid bloat and stay within scope.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **General Refactoring** | Scope creep; debugging should be minimal and surgical. | Flag large changes for human review; keep fixes focused. |
| **Feature Implementation** | `sp-debug` is for *fixing*, not *building*. | Use the standard `specify implement` workflow for new features. |
| **Multi-Repo Debugging** | Increases complexity and token costs exponentially. | Focus on the local repository context. |

## Feature Dependencies

```mermaid
Reproduction script -> Hypothesis testing -> Fix implementation -> Regression testing
```

## MVP Recommendation

Prioritize:
1.  **Reproduction First:** Force the creation of a failing test.
2.  **Scientific Loop:** Implement the Gather -> Investigate -> Fix -> Verify progression.
3.  **State Persistence:** Basic `.planning/debug/[slug].md` with resumability.

Defer:
-   **Advanced Context Pruning:** Use full artifacts initially until context limits become a problem.
-   **Multi-Agent Coordination:** Stick to a single "Scientific Debugger" agent first.

## Sources

- [gsd-debug architecture reference](https://github.com/get-shit-done)
- [Aider Feature List](https://aider.chat)
- `spec-kit-plus` Project Charter
