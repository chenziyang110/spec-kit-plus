---
description: "Use when executing implementation plans, working on independent tasks, or when asked to dispatch subagents. Enforces the use of sp-tasks and sp-implement over manual subagent management."
---

# Task-Driven Execution (Spec Kit Plus)

In the Spec Kit Plus ecosystem, we do not manually dispatch ad-hoc subagents for implementation. Instead, we rely on the formal `sp-tasks` and `sp-implement` workflows to maintain state, context isolation, and verification.

## The Process

1. **Task Generation (`sp-tasks`)**: If you have a plan but no discrete tasks, do not improvise. Use `sp-tasks` to break the plan down into independent, executable units within the `.specify/` state surface.
2. **Task Execution (`sp-implement`)**: Once tasks are defined, use `sp-implement` to execute them. The `sp-implement` workflow is designed to provide the necessary context isolation and step-by-step verification that subagents would otherwise provide.
3. **Verification**: Each `sp-implement` cycle naturally incorporates spec compliance and code quality reviews based on the project's explicit rules.

## Routing Rules

- If the user asks to "execute the plan" or "start building" -> Route to `sp-implement` (or `sp-tasks` if tasks are not yet generated).
- If the user asks to "dispatch an agent" for a specific task -> Route to `sp-fast`, `sp-quick`, or `sp-implement` depending on the scope.
- **Do not** use `invoke_agent` or manually orchestrate subagents for code changes when an `sp-*` workflow applies.

## Red Flags

- Starting implementation without a finalized plan and tasks.
- Trying to execute multiple complex tasks in a single unstructured session instead of using `sp-implement` iteratively.
- Ignoring the `.specify/` state surface in favor of chat memory.
