# Artifact explanation

Use this reference when the user asks what a spec, plan, task set, workflow
state, cognition map, or handbook means.

Resolve the active feature or lane before guessing. Prefer the project's
prerequisite script with paths-only JSON; when branch context is ambiguous, use
`specify lane resolve --command explain --ensure-worktree`.

Read the most downstream artifact that directly answers the question, then only
its authoritative inputs:

- execution question: tasks and task index, then plan, then spec;
- architecture question: plan contract and plan, then relevant research or
  contracts;
- requirement question: spec contract and spec, plus confirmed discussion/UI
  inputs when referenced;
- repository-current question: live source/tests/runtime, using artifacts only
  as intent or historical context;
- cognition question: status/Compass output plus live evidence, never the graph
  alone.

Explain relationships and consequences rather than paraphrasing every section.
On same-topic follow-ups, reuse still-current evidence and read only the delta.
If an expected artifact is absent, say which layer is missing and answer only
to the confidence supported by the remaining sources.
